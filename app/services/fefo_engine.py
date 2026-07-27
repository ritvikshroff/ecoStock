# ============================================================
# app/services/fefo_engine.py
# ============================================================
# PURPOSE:
#   FEFO = First Expiry, First Out
#   This is the CORE business logic of ecoStock.
#
#   The FEFO engine:
#   1. Scans all inventory batches sorted by expiry date
#   2. Identifies batches that need discounting
#   3. Identifies batches that need routing to food banks
#   4. Suggests optimal pricing based on days until expiry
# ============================================================

from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.models import (
    InventoryBatch, Product, BatchStatus,
    PriceHistory, Alert, AlertType
)
from app.core.config import settings


class FEFOEngine:
    """
    The brain of ecoStock.
    Implements First-Expiry-First-Out logic for inventory management.
    """

    def __init__(self, db: Session):
        self.db = db

    # ============================================================
    # CORE: Get all batches sorted by expiry (FEFO order)
    # ============================================================

    def get_fefo_sorted_batches(
        self,
        store_id: Optional[int] = None,
        product_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[InventoryBatch]:
        """
        Returns inventory batches sorted by expiry date (soonest first).
        This is the FEFO principle: sell what expires first, first.

        Args:
            store_id: Filter by store
            product_id: Filter by product
            status: Filter by batch status
            limit: Max number of results

        Returns:
            List of InventoryBatch objects, sorted by expiry_date ASC
        """
        query = self.db.query(InventoryBatch).join(Product)

        # Filters
        if store_id:
            query = query.filter(InventoryBatch.store_id == store_id)
        if product_id:
            query = query.filter(InventoryBatch.product_id == product_id)
        if status:
            query = query.filter(InventoryBatch.status == status)
        else:
            # Default: only show active/non-wasted batches
            query = query.filter(
                InventoryBatch.status.in_([
                    BatchStatus.ACTIVE,
                    BatchStatus.DISCOUNTED,
                    BatchStatus.FLAGGED
                ])
            )

        # FEFO sort: soonest expiry first
        query = query.order_by(InventoryBatch.expiry_date.asc())

        return query.limit(limit).all()

    # ============================================================
    # SCAN: Identify what needs attention
    # ============================================================

    def scan_inventory(self, store_id: Optional[int] = None) -> List[dict]:
        """
        Scans all inventory and returns a report of what needs action.

        Returns a list of dicts with:
            - batch_id, product_name, sku, expiry_date
            - days_until_expiry, current_quantity, status
            - suggested_action: "sell_now", "discount", "flag_for_routing", "ok"
        """
        today = date.today()
        batches = self.get_fefo_sorted_batches(store_id=store_id, limit=500)
        results = []

        for batch in batches:
            days_until_expiry = (batch.expiry_date - today).days
            product = batch.product

            # Determine suggested action
            if days_until_expiry <= 0:
                suggested_action = "expired"
            elif days_until_expiry <= 1:
                suggested_action = "flag_for_routing"
            elif days_until_expiry <= settings.DISCOUNT_ALERT_DAYS:
                suggested_action = "discount"
            elif days_until_expiry <= 7:
                suggested_action = "sell_now"
            else:
                suggested_action = "ok"

            results.append({
                "batch_id": batch.id,
                "product_name": product.name if product else "Unknown",
                "sku": product.sku if product else "Unknown",
                "expiry_date": batch.expiry_date,
                "days_until_expiry": days_until_expiry,
                "current_quantity": batch.current_quantity,
                "status": batch.status.value,
                "current_price": batch.current_price,
                "suggested_action": suggested_action,
            })

        return results

    # ============================================================
    # PRICING: Calculate optimal discount
    # ============================================================

    def calculate_discount(self, batch: InventoryBatch) -> Tuple[float, float]:
        """
        Calculates the optimal discount for a batch based on days until expiry.

        Uses the DISCOUNT_TIERS from settings:
            e.g., [(3, 20.0), (2, 35.0), (1, 50.0)]
            Means: 3 days left → 20% off, 2 days left → 35% off, 1 day left → 50% off

        Returns:
            Tuple of (discount_percentage, new_price)
        """
        today = date.today()
        days_until_expiry = (batch.expiry_date - today).days

        # Find the matching discount tier
        discount_pct = 0.0
        for tier_days, tier_discount in settings.DISCOUNT_TIERS:
            if days_until_expiry <= tier_days:
                discount_pct = tier_discount
                break

        # Calculate new price
        new_price = round(batch.current_price * (1 - discount_pct / 100), 2)

        return discount_pct, new_price

    # ============================================================
    # APPLY: Auto-apply discounts to near-expiry batches
    # ============================================================

    def apply_auto_discounts(self, store_id: Optional[int] = None) -> List[dict]:
        """
        Automatically applies discounts to batches that need them.
        This is the core auto-pricing feature.

        Returns:
            List of dicts describing what discounts were applied
        """
        today = date.today()
        batches = self.get_fefo_sorted_batches(store_id=store_id)
        applied = []

        for batch in batches:
            days_until_expiry = (batch.expiry_date - today).days

            # Only discount active batches that are within the discount window
            if batch.status not in [BatchStatus.ACTIVE, BatchStatus.DISCOUNTED]:
                continue

            if days_until_expiry > settings.DISCOUNT_ALERT_DAYS:
                continue

            # Calculate and apply discount
            old_price = batch.current_price
            discount_pct, new_price = self.calculate_discount(batch)

            if discount_pct > 0 and new_price < old_price:
                # Update the batch
                old_status = batch.status
                batch.current_price = new_price
                batch.discount_percentage = discount_pct
                batch.status = BatchStatus.DISCOUNTED

                # Log the price change
                price_log = PriceHistory(
                    batch_id=batch.id,
                    old_price=old_price,
                    new_price=new_price,
                    discount_pct=discount_pct,
                    days_to_expiry=days_until_expiry,
                    triggered_by="system",
                    note=f"Auto-discount: {discount_pct:.0f}% off ({days_until_expiry} days to expiry)"
                )
                self.db.add(price_log)

                # Create an alert
                alert = Alert(
                    store_id=batch.store_id,
                    alert_type=AlertType.MARKDOWN_APPLIED,
                    batch_id=batch.id,
                    title=f"💰 Discount Applied: {batch.product.name}",
                    message=(
                        f"Price reduced from ₹{old_price:.2f} to ₹{new_price:.2f} "
                        f"({discount_pct:.0f}% off). {days_until_expiry} days until expiry."
                    ),
                    priority=2
                )
                self.db.add(alert)

                applied.append({
                    "batch_id": batch.id,
                    "product_name": batch.product.name if batch.product else "Unknown",
                    "old_price": old_price,
                    "new_price": new_price,
                    "discount_pct": discount_pct,
                    "days_until_expiry": days_until_expiry,
                    "old_status": old_status.value,
                    "new_status": BatchStatus.DISCOUNTED.value,
                })

        # Commit all changes
        self.db.commit()

        return applied

    # ============================================================
    # ROUTING: Flag batches for food bank / B2B / composting
    # ============================================================

    def flag_for_routing(self, store_id: Optional[int] = None) -> List[dict]:
        """
        Flags batches that are about to expire for secondary routing.
        (Food bank, B2B, or composting)

        Returns:
            List of dicts describing what was flagged
        """
        today = date.today()
        threshold_hours = settings.FOOD_BANK_ALERT_HOURS
        threshold_days = threshold_hours / 24.0

        batches = self.db.query(InventoryBatch).join(Product).filter(
            InventoryBatch.store_id == store_id if store_id else True,
            InventoryBatch.status.in_([BatchStatus.ACTIVE, BatchStatus.DISCOUNTED]),
            InventoryBatch.expiry_date <= today + timedelta(days=threshold_days),
            InventoryBatch.current_quantity > 0,
        ).all()

        flagged = []
        for batch in batches:
            days_until_expiry = (batch.expiry_date - today).days

            # Update status
            batch.status = BatchStatus.FLAGGED

            # Create alert
            alert = Alert(
                store_id=batch.store_id,
                alert_type=AlertType.FOOD_BANK_DISPATCH,
                batch_id=batch.id,
                title=f"🚨 Routing Needed: {batch.product.name}",
                message=(
                    f"Batch expires in {days_until_expiry} days. "
                    f"Quantity: {batch.current_quantity} units. "
                    f"Arrange food bank / B2B / composting dispatch."
                ),
                priority=1  # High priority
            )
            self.db.add(alert)

            flagged.append({
                "batch_id": batch.id,
                "product_name": batch.product.name if batch.product else "Unknown",
                "quantity": batch.current_quantity,
                "days_until_expiry": days_until_expiry,
                "suggested_routes": ["food_bank", "b2b_buyer", "composting"],
            })

        self.db.commit()
        return flagged

    # ============================================================
    # FULL RUN: Execute the complete FEFO pipeline
    # ============================================================

    def run_full_pipeline(self, store_id: Optional[int] = None) -> dict:
        """
        Runs the complete FEFO engine pipeline:
        1. Scan inventory
        2. Apply auto-discounts
        3. Flag for routing

        This is the main function called by the scheduler or API.

        Returns:
            Summary dict of everything that happened
        """
        scan_results = self.scan_inventory(store_id=store_id)
        discounts_applied = self.apply_auto_discounts(store_id=store_id)
        flagged_for_routing = self.flag_for_routing(store_id=store_id)

        return {
            "summary": {
                "total_batches_scanned": len(scan_results),
                "discounts_applied": len(discounts_applied),
                "flagged_for_routing": len(flagged_for_routing),
            },
            "batches_needing_attention": [
                b for b in scan_results
                if b["suggested_action"] in ("discount", "flag_for_routing", "expired")
            ],
            "discounts_applied": discounts_applied,
            "flagged_for_routing": flagged_for_routing,
        }

