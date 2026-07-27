# ============================================================
# app/services/pricing_engine.py
# ============================================================
# PURPOSE:
#   Dynamic Pricing Engine — the brains behind smart markdowns.
#   Goes beyond simple FEFO discounting to use:
#   - Category-based decay curves (dairy decays faster than frozen)
#   - Price elasticity of demand estimates
#   - Loss-leader detection & prevention
#   - Bundle suggestions for near-expiry items
#   - Optimal revenue recovery calculations
# ============================================================

from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple
from math import exp

from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc

from app.models.models import (
    InventoryBatch, Product, BatchStatus,
    PriceHistory, ProductCategory, Alert, AlertType
)
from app.core.config import settings


# ── Category Decay Curves ──────────────────────────────────
# Each category has a different "decay profile":
#   - Dairy: spoils fast, steep discount curve
#   - Meat: very fast decay, deep discounts needed
#   - Produce: moderate decay
#   - Bakery: fast decay, but still sellable day-of
#   - Frozen: slow decay, gentle discounts
#   - Beverages: moderate decay
#   - Deli: fast decay
#   - Other: moderate
#
# Each curve defines (days_remaining, discount_pct) tiers
# specific to that category.

CATEGORY_DECAY_CURVES = {
    ProductCategory.DAIRY:     [(2, 40.0), (1, 60.0)],
    ProductCategory.MEAT:      [(2, 45.0), (1, 65.0)],
    ProductCategory.PRODUCE:   [(3, 25.0), (2, 40.0), (1, 55.0)],
    ProductCategory.BAKERY:    [(2, 35.0), (1, 55.0)],
    ProductCategory.FROZEN:    [(7, 15.0), (5, 25.0), (3, 35.0), (1, 50.0)],
    ProductCategory.BEVERAGES: [(5, 20.0), (3, 30.0), (1, 45.0)],
    ProductCategory.DELI:      [(2, 35.0), (1, 50.0)],
    ProductCategory.OTHER:     [(5, 15.0), (3, 25.0), (1, 40.0)],
}

# Default curve (if category not found)
DEFAULT_DECAY_CURVE = [(3, 20.0), (2, 35.0), (1, 50.0)]

# Price elasticity estimates per category (how much does demand change with price)
# Higher absolute value = more sensitive to price changes
CATEGORY_ELASTICITY = {
    ProductCategory.DAIRY:     -1.8,  # Very elastic — people switch brands
    ProductCategory.MEAT:      -1.5,  # Elastic
    ProductCategory.PRODUCE:   -1.2,  # Moderately elastic
    ProductCategory.BAKERY:    -1.6,  # Elastic
    ProductCategory.FROZEN:    -0.8,  # Inelastic — convenience matters
    ProductCategory.BEVERAGES: -1.0,  # Unit elastic
    ProductCategory.DELI:      -1.4,  # Elastic
    ProductCategory.OTHER:     -1.0,  # Unit elastic
}

DEFAULT_ELASTICITY = -1.0


class PricingEngine:
    """
    Dynamic pricing engine that goes beyond simple tier-based discounts.
    Uses category-specific decay curves, elasticity modeling, and
    revenue optimization to suggest the best prices.
    """

    def __init__(self, db: Session):
        self.db = db

    # ============================================================
    # HELPER: Get decay curve for a product category
    # ============================================================

    def _get_decay_curve(self, category: ProductCategory) -> list[tuple[int, float]]:
        """Returns the discount tiers appropriate for this category."""
        return CATEGORY_DECAY_CURVES.get(category, DEFAULT_DECAY_CURVE)

    def _get_elasticity(self, category: ProductCategory) -> float:
        """Returns the price elasticity for this category."""
        return CATEGORY_ELASTICITY.get(category, DEFAULT_ELASTICITY)

    # ============================================================
    # STRATEGY 1: Time-based Decay Pricing
    # ============================================================

    def time_decay_price(self, batch: InventoryBatch) -> Tuple[float, float, str]:
        """
        Calculates price based on category-specific decay curve.
        Different categories decay at different rates.

        Returns:
            Tuple of (discount_pct, suggested_price, reason)
        """
        today = date.today()
        days_until_expiry = (batch.expiry_date - today).days
        product = batch.product

        if not product:
            return 0.0, batch.current_price, "No product data"

        curve = self._get_decay_curve(product.category)

        # Find the matching tier
        discount_pct = 0.0
        for tier_days, tier_discount in curve:
            if days_until_expiry <= tier_days:
                discount_pct = tier_discount
                break

        # If days_until_expiry is beyond all tiers, no discount
        if discount_pct == 0.0 and days_until_expiry > 0:
            # Maybe a small early-bird? No, we only discount near expiry.
            return 0.0, batch.current_price, "Still fresh — no discount needed"

        suggested_price = round(batch.current_price * (1 - discount_pct / 100), 2)
        reason = (
            f"Time-decay ({product.category.value}): {days_until_expiry}d left, "
            f"{discount_pct:.0f}% off per category curve"
        )

        return discount_pct, suggested_price, reason

    # ============================================================
    # STRATEGY 2: Elasticity-based Optimal Pricing
    # ============================================================

    def elasticity_price(self, batch: InventoryBatch) -> Tuple[float, float, str, float]:
        """
        Uses price elasticity to find the revenue-maximizing price.
        More elastic categories → deeper discounts needed to sell.

        Returns:
            Tuple of (discount_pct, suggested_price, reason, expected_revenue)
        """
        today = date.today()
        days_until_expiry = (batch.expiry_date - today).days
        product = batch.product

        if not product or days_until_expiry <= 0:
            return 0.0, batch.current_price, "Expired or no data", 0.0

        elasticity = self._get_elasticity(product.category)

        # The closer to expiry, the more we need to drop price
        # We use the shelf life as a normalization factor
        shelf_life = product.typical_shelf_life_days or 7
        life_remaining_ratio = max(0.01, days_until_expiry / shelf_life)

        # Elasticity-optimized discount:
        # More elastic → steeper discount needed
        # Less elastic → gentler discount (people will buy anyway)
        elasticity_factor = abs(elasticity)  # 0.8 to 1.8
        urgency_factor = 1.0 - life_remaining_ratio  # 0 (fresh) to 0.99 (expiring)

        # Base discount from urgency
        base_discount = urgency_factor * 60.0  # Max 60% off

        # Adjust for elasticity: elastic goods need more discount
        if elasticity_factor > 1.3:
            elasticity_multiplier = 1.2  # 20% more discount
        elif elasticity_factor > 1.0:
            elasticity_multiplier = 1.0
        else:
            elasticity_multiplier = 0.85  # Less discount for inelastic goods

        discount_pct = round(base_discount * elasticity_multiplier, 1)
        discount_pct = min(discount_pct, 70.0)  # Cap at 70%
        discount_pct = max(discount_pct, 0.0)

        suggested_price = round(batch.current_price * (1 - discount_pct / 100), 2)

        # Expected revenue = price * expected_quantity_sold
        # At lower prices, more units sell (elasticity model)
        price_ratio = suggested_price / (product.base_price or suggested_price)
        quantity_multiplier = (1.0 / price_ratio) ** abs(elasticity)
        expected_units_sold = min(batch.current_quantity * quantity_multiplier, batch.current_quantity)
        expected_revenue = round(suggested_price * expected_units_sold, 2)

        current_revenue = batch.current_price * batch.current_quantity
        if current_revenue > 0:
            revenue_ratio = expected_revenue / current_revenue
        else:
            revenue_ratio = 0

        reason = (
            f"Elasticity ({product.category.value}, ε={elasticity:.1f}): "
            f"{life_remaining_ratio:.0%} life remaining, "
            f"{discount_pct:.0f}% off → {revenue_ratio:.0%}x revenue recovery"
        )

        return discount_pct, suggested_price, reason, expected_revenue

    # ============================================================
    # STRATEGY 3: Loss-Leader Detection
    # ============================================================

    def detect_loss_leader(self, batch: InventoryBatch) -> Tuple[bool, str]:
        """
        Detects if a batch is at risk of becoming a loss leader.
        A loss leader is when the selling price is below cost price.
        This function warns against excessive discounting.

        Returns:
            Tuple of (is_loss_leader, warning_message)
        """
        product = batch.product
        if not product or not product.cost_price:
            return False, "No cost data available"

        if product.cost_price <= 0:
            return False, "No cost data available"

        # Check current price vs cost
        if batch.current_price < product.cost_price:
            loss_per_unit = product.cost_price - batch.current_price
            total_loss = loss_per_unit * batch.current_quantity
            return (
                True,
                f"⚠️ LOSS LEADER: Selling ₹{loss_per_unit:.2f} below cost. "
                f"Projected loss: ₹{total_loss:.2f} on {batch.current_quantity} units."
            )

        # Check if any suggested discount would make it a loss leader
        margin = batch.current_price - product.cost_price
        margin_pct = (margin / product.cost_price) * 100

        if margin_pct < 10:
            return (
                True,
                f"⚠️ THIN MARGIN: Only {margin_pct:.0f}% margin (₹{margin:.2f}/unit). "
                f"Further discounting would cause losses."
            )

        return False, "Healthy margin — no loss leader risk"

    # ============================================================
    # STRATEGY 4: Bundle Suggestions
    # ============================================================

    def suggest_bundles(self, store_id: Optional[int] = None) -> List[dict]:
        """
        Suggests product bundles for near-expiry items.
        Pairs expiring items with complementary full-price items.

        Returns:
            List of bundle suggestions
        """
        today = date.today()
        suggestions = []

        # Find near-expiry batches (1-3 days left)
        query = self.db.query(InventoryBatch).join(Product).filter(
            InventoryBatch.store_id == store_id if store_id else True,
            InventoryBatch.status.in_([BatchStatus.ACTIVE, BatchStatus.DISCOUNTED]),
            InventoryBatch.expiry_date <= today + timedelta(days=3),
            InventoryBatch.expiry_date > today,
            InventoryBatch.current_quantity > 0,
        )

        expiring_batches = query.all()

        for batch in expiring_batches:
            product = batch.product
            if not product:
                continue

            days_left = (batch.expiry_date - today).days

            # Find complementary products in the same store
            # that are fresh (not expiring)
            complementary = self.db.query(Product).filter(
                Product.is_active == True,
                Product.id != product.id,
                Product.category.in_([
                    ProductCategory.BEVERAGES,
                    ProductCategory.DAIRY,
                    ProductCategory.BAKERY,
                ])
            ).order_by(func.random()).limit(3).all()

            if complementary:
                # Create a bundle: expiring item + fresh complementary item
                for comp in complementary:
                    # Find a fresh batch of the complementary product
                    comp_batch = self.db.query(InventoryBatch).filter(
                        InventoryBatch.product_id == comp.id,
                        InventoryBatch.store_id == batch.store_id,
                        InventoryBatch.status == BatchStatus.ACTIVE,
                        InventoryBatch.current_quantity > 0,
                    ).first()

                    if comp_batch:
                        bundle_discount = min(15.0 + days_left * 5, 30.0)  # 20-30% off bundle
                        original_total = batch.current_price + (comp_batch.current_price * 0.5)
                        bundle_price = round(original_total * (1 - bundle_discount / 100), 2)
                        savings = round(original_total - bundle_price, 2)

                        suggestions.append({
                            "bundle_name": f"{product.name} + {comp.name} Deal",
                            "product_ids": [product.id, comp.id],
                            "product_names": [product.name, comp.name],
                            "original_total": round(original_total, 2),
                            "bundle_price": bundle_price,
                            "savings": savings,
                            "reason": (
                                f"Bundle expiring {product.name} ({days_left}d left) "
                                f"with fresh {comp.name}. Save ₹{savings:.0f}!"
                            ),
                        })

        return suggestions[:10]  # Return top 10 bundles

    # ============================================================
    # GET ALL PRICINGS SUGGESTIONS FOR A STORE
    # ============================================================

    def get_pricing_suggestions(
        self, store_id: Optional[int] = None
    ) -> List[dict]:
        """
        Gets comprehensive pricing suggestions for all batches.
        Combines time-decay and elasticity strategies.

        Returns:
            List of pricing suggestions with strategy metadata
        """
        today = date.today()

        query = self.db.query(InventoryBatch).join(Product).filter(
            InventoryBatch.store_id == store_id if store_id else True,
            InventoryBatch.status.in_([BatchStatus.ACTIVE, BatchStatus.DISCOUNTED]),
            InventoryBatch.current_quantity > 0,
        )

        suggestions = []

        for batch in query.all():
            product = batch.product
            if not product:
                continue

            days_until_expiry = (batch.expiry_date - today).days

            # Skip expired batches
            if days_until_expiry <= 0:
                continue

            # Get time-decay suggestion
            _, time_price, time_reason = self.time_decay_price(batch)
            time_discount_pct = round(
                (1 - time_price / batch.current_price) * 100, 1
            ) if batch.current_price > 0 else 0

            # Get elasticity suggestion
            _, elas_price, elas_reason, expected_revenue = self.elasticity_price(batch)
            elas_discount_pct = round(
                (1 - elas_price / batch.current_price) * 100, 1
            ) if batch.current_price > 0 else 0

            # Check loss leader risk
            is_loss_leader, loss_warning = self.detect_loss_leader(batch)

            # Determine which strategy to recommend
            if days_until_expiry <= 1:
                # Critical — use deepest discount
                suggested_price = min(time_price, elas_price)
                strategy = "time_decay"
                reason = f"CRITICAL: {days_until_expiry}d left. Maximum markdown recommended."
                urgency = "critical"
            elif days_until_expiry <= 3:
                # Use elasticity-based for better revenue recovery
                suggested_price = elas_price
                strategy = "elasticity"
                reason = elas_reason
                urgency = "high"
            elif days_until_expiry <= 5:
                suggested_price = elas_price
                strategy = "elasticity"
                reason = elas_reason
                urgency = "medium"
            else:
                suggested_price = time_price
                strategy = "time_decay"
                reason = time_reason
                urgency = "low"

            discount_pct = round(
                (1 - suggested_price / batch.current_price) * 100, 1
            ) if batch.current_price > 0 else 0

            # If loss leader, cap the discount
            if is_loss_leader and product.cost_price:
                # Don't go below cost + 10% margin
                min_price = round(product.cost_price * 1.1, 2)
                if suggested_price < min_price:
                    suggested_price = min_price
                    discount_pct = round(
                        (1 - suggested_price / batch.current_price) * 100, 1
                    ) if batch.current_price > 0 else 0
                    reason = f"Loss-leader prevention: price capped at ₹{min_price:.2f} (cost + 10%)"

            suggestions.append({
                "batch_id": batch.id,
                "product_name": product.name,
                "category": product.category.value,
                "current_price": batch.current_price,
                "suggested_price": suggested_price,
                "discount_pct": discount_pct,
                "days_until_expiry": days_until_expiry,
                "strategy": strategy,
                "reason": reason,
                "expected_revenue_recovery": round(expected_revenue, 2) if strategy == "elasticity" else 0.0,
                "urgency": urgency,
                "loss_leader_warning": loss_warning if is_loss_leader else None,
                "quantity": batch.current_quantity,
                "cost_price": product.cost_price,
            })

        # Sort by urgency (critical first)
        urgency_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        suggestions.sort(key=lambda x: urgency_order.get(x["urgency"], 99))

        return suggestions

    # ============================================================
    # APPLY PRICING SUGGESTIONS
    # ============================================================

    def apply_pricing(self, store_id: Optional[int] = None) -> List[dict]:
        """
        Applies the pricing suggestions to actual batches.
        Creates price history entries and alerts.

        Returns:
            List of applied pricing actions
        """
        suggestions = self.get_pricing_suggestions(store_id=store_id)
        applied = []

        for s in suggestions:
            if s["urgency"] in ("critical", "high") and s["discount_pct"] > 5:
                batch = self.db.query(InventoryBatch).filter(
                    InventoryBatch.id == s["batch_id"]
                ).first()

                if not batch:
                    continue

                old_price = batch.current_price
                old_status = batch.status

                # Update the batch
                batch.current_price = s["suggested_price"]
                batch.discount_percentage = s["discount_pct"]
                batch.status = BatchStatus.DISCOUNTED

                # Log price change
                price_log = PriceHistory(
                    batch_id=batch.id,
                    old_price=old_price,
                    new_price=s["suggested_price"],
                    discount_pct=s["discount_pct"],
                    days_to_expiry=s["days_until_expiry"],
                    triggered_by="pricing_engine",
                    note=f"Dynamic pricing ({s['strategy']}): {s['reason']}"
                )
                self.db.add(price_log)

                # Create alert
                alert = Alert(
                    store_id=batch.store_id,
                    alert_type=AlertType.MARKDOWN_APPLIED,
                    batch_id=batch.id,
                    title=f"💰 Dynamic Price: {s['product_name']}",
                    message=(
                        f"Price reduced from ₹{old_price:.2f} to ₹{s['suggested_price']:.2f} "
                        f"({s['discount_pct']:.0f}% off). Strategy: {s['strategy']}. "
                        f"{s['days_until_expiry']} days until expiry."
                    ),
                    priority=1 if s["urgency"] == "critical" else 2
                )
                self.db.add(alert)

                applied.append({
                    "batch_id": batch.id,
                    "product_name": s["product_name"],
                    "old_price": old_price,
                    "new_price": s["suggested_price"],
                    "discount_pct": s["discount_pct"],
                    "strategy": s["strategy"],
                    "urgency": s["urgency"],
                })

        self.db.commit()
        return applied

