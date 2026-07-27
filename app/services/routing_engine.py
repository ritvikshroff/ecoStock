# ============================================================
# app/services/routing_engine.py
# ============================================================
# PURPOSE:
#   Secondary Routing Engine — manages the diversion of
#   near-expiry or unsalable stock to secondary channels:
#   - Food banks (donation)
#   - B2B buyers (restaurants, bakeries, hotels)
#   - Composting facilities
#
#   Features:
#   - Intelligent route suggestion based on product category
#   - Partner matching (which food bank / B2B buyer gets what)
#   - Value recovery estimation (revenue from B2B, tax benefits from donations)
#   - Dispatch confirmation workflow
#   - Diversion analytics and reporting
# ============================================================

from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple
from math import ceil

from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc

from app.models.models import (
    InventoryBatch, Product, BatchStatus, ProductCategory,
    SecondaryRoute, RouteType, Alert, AlertType
)
from app.core.config import settings


# ── Route priority rules per category ──────────────────────
# Some categories are better suited for certain routes
#   food_bank: dairy, produce, bakery (fresh, nutritious)
#   b2b: produce, meat, bakery (commercial kitchens need these)
#   composting: produce, bakery (organic waste)

CATEGORY_ROUTE_PRIORITY = {
    ProductCategory.DAIRY:     ["food_bank", "b2b_buyer", "composting"],
    ProductCategory.PRODUCE:   ["food_bank", "b2b_buyer", "composting"],
    ProductCategory.BAKERY:    ["food_bank", "b2b_buyer", "composting"],
    ProductCategory.MEAT:      ["b2b_buyer", "food_bank"],
    ProductCategory.FROZEN:    ["food_bank", "b2b_buyer", "composting"],
    ProductCategory.BEVERAGES: ["food_bank", "b2b_buyer"],
    ProductCategory.DELI:      ["food_bank", "b2b_buyer", "composting"],
    ProductCategory.OTHER:     ["b2b_buyer", "composting"],
}

# ── Value recovery estimates ───────────────────────────────
# Percentage of original value recovered through each route
# Food bank: ~15% (tax benefit + goodwill value)
# B2B: ~40% (discounted sale price)
# Composting: ~5% (avoided disposal cost)

ROUTE_VALUE_RECOVERY = {
    "food_bank":  0.15,   # Tax benefit / CSR value
    "b2b_buyer":  0.40,   # Discounted wholesale
    "composting": 0.05,   # Avoided landfill cost
}

# ── Default partners per route type ────────────────────────
DEFAULT_PARTNERS = {
    "food_bank": [
        {"name": "Feeding India", "contact": "feedingindia@ngo.org"},
        {"name": "Akshaya Patra", "contact": "dispatch@akshayapatra.org"},
        {"name": "No Food Waste", "contact": "coordinator@nofoodwaste.org"},
    ],
    "b2b_buyer": [
        {"name": "Hotel Grand Kitchen", "contact": "purchasing@grandhotel.com"},
        {"name": "Campus Cafeteria Co.", "contact": "orders@campusfood.com"},
        {"name": "Baker's Delight", "contact": "supply@bakersdelight.com"},
    ],
    "composting": [
        {"name": "Green Earth Composting", "contact": "pickup@greenearth.org"},
        {"name": "Urban Waste Solutions", "contact": "compost@urbanwaste.com"},
    ],
}


class RoutingEngine:
    """
    Secondary routing engine — diverts near-expiry stock
    away from landfills and into productive secondary channels.
    """

    def __init__(self, db: Session):
        self.db = db

    # ============================================================
    # HELPER: Get best route for a product category
    # ============================================================

    def _get_route_priority(self, category: ProductCategory) -> list[str]:
        """Returns the priority-ordered route list for a category."""
        return CATEGORY_ROUTE_PRIORITY.get(category, ["food_bank", "b2b_buyer", "composting"])

    def _get_value_recovery(self, route_type: str, base_price: float,
                            quantity: float) -> float:
        """Estimates the value recovered through a given route."""
        recovery_pct = ROUTE_VALUE_RECOVERY.get(route_type, 0.1)
        return round(base_price * quantity * recovery_pct, 2)

    # ============================================================
    # SUGGEST: Best route for a batch
    # ============================================================

    def suggest_route(self, batch: InventoryBatch) -> dict:
        """
        Determines the best routing option for a batch.

        Returns:
            Dict with route suggestion details
        """
        product = batch.product
        if not product:
            return {
                "batch_id": batch.id,
                "product_name": "Unknown",
                "suggested_routes": ["composting"],
                "recommended_route": "composting",
                "estimated_value_recovery": 0.0,
                "reason": "Unknown product — default to composting",
            }

        today = date.today()
        days_until_expiry = (batch.expiry_date - today).days
        route_priority = self._get_route_priority(product.category)

        # Determine urgency
        if days_until_expiry <= 0:
            urgency = "critical"
            # Expired items go to composting
            recommended_route = "composting"
            reason = f"EXPIRED: Batch expired {abs(days_until_expiry)} days ago. Must compost."
        elif days_until_expiry <= 1:
            urgency = "high"
            # Very near expiry — food bank (fastest distribution)
            recommended_route = route_priority[0] if route_priority else "food_bank"
            reason = f"URGENT: Only {days_until_expiry} day(s) left. Fastest route needed: {recommended_route}."
        elif days_until_expiry <= 3:
            urgency = "medium"
            # Can choose the best option
            recommended_route = route_priority[0] if route_priority else "food_bank"
            alternative = route_priority[1] if len(route_priority) > 1 else "composting"
            reason = (
                f"{days_until_expiry} days until expiry. "
                f"Recommended: {recommended_route}. Alternative: {alternative}."
            )
        else:
            urgency = "low"
            recommended_route = route_priority[0] if route_priority else "food_bank"
            reason = f"{days_until_expiry} days until expiry. Can use any route. Best fit: {recommended_route}."

        # Find a suggested partner
        partners = DEFAULT_PARTNERS.get(recommended_route, [{"name": "General Partner", "contact": ""}])
        suggested_partner = partners[0] if partners else {"name": "Unknown", "contact": ""}

        # Value recovery
        value_recovery = self._get_value_recovery(
            recommended_route, product.base_price, batch.current_quantity
        )

        return {
            "batch_id": batch.id,
            "product_name": product.name,
            "quantity": batch.current_quantity,
            "unit": product.unit,
            "expiry_date": batch.expiry_date,
            "days_until_expiry": days_until_expiry,
            "suggested_routes": route_priority,
            "recommended_route": recommended_route,
            "suggested_partner": suggested_partner,
            "estimated_value_recovery": value_recovery,
            "reason": reason,
            "urgency": urgency,
        }

    # ============================================================
    # SCAN: Get routing suggestions for all at-risk batches
    # ============================================================

    def scan_for_routing(self, store_id: Optional[int] = None,
                         max_days_to_expiry: int = 3) -> List[dict]:
        """
        Scans inventory and returns routing suggestions for
        all batches near expiry.

        Returns:
            List of route suggestions sorted by urgency
        """
        today = date.today()
        threshold_date = today + timedelta(days=max_days_to_expiry)

        batches = self.db.query(InventoryBatch).join(Product).filter(
            InventoryBatch.store_id == store_id if store_id else True,
            InventoryBatch.status.in_([BatchStatus.ACTIVE, BatchStatus.DISCOUNTED, BatchStatus.FLAGGED]),
            InventoryBatch.expiry_date <= threshold_date,
            InventoryBatch.current_quantity > 0,
        ).order_by(InventoryBatch.expiry_date.asc()).all()

        suggestions = []
        for batch in batches:
            suggestion = self.suggest_route(batch)
            suggestions.append(suggestion)

        return suggestions

    # ============================================================
    # DISPATCH: Execute a routing dispatch
    # ============================================================

    def dispatch_batch(self, batch_id: int, route_type: str,
                       partner_name: str, partner_contact: Optional[str] = None,
                       quantity: Optional[float] = None,
                       value_recovered: float = 0.0,
                       note: Optional[str] = None) -> dict:
        """
        Executes a dispatch for a batch — sends it to a secondary channel.

        Creates:
            - SecondaryRoute record
            - Alert notification
            - Updates batch status

        Returns:
            Dict with dispatch details
        """
        batch = self.db.query(InventoryBatch).filter(
            InventoryBatch.id == batch_id
        ).first()

        if not batch:
            return {"error": "Batch not found"}

        if not quantity:
            quantity = batch.current_quantity

        product = batch.product
        product_name = product.name if product else "Unknown"

        # Map route type string to enum
        route_map = {
            "food_bank": RouteType.FOOD_BANK,
            "b2b_buyer": RouteType.SOLD_B2B,
            "composting": RouteType.COMPOSTING,
        }
        route_enum = route_map.get(route_type)
        if not route_enum:
            return {"error": f"Invalid route type: {route_type}"}

        # Create the route record
        route = SecondaryRoute(
            batch_id=batch.id,
            route_type=route_enum,
            partner_name=partner_name,
            partner_contact=partner_contact,
            quantity_dispatched=quantity,
            dispatch_date=datetime.utcnow(),
            value_recovered=value_recovered,
            note=note or f"Dispatched via {route_type} to {partner_name}",
        )
        self.db.add(route)

        # Update batch status
        if route_type == "food_bank":
            batch.status = BatchStatus.DONATED
        elif route_type == "b2b_buyer":
            batch.status = BatchStatus.SOLD_B2B
        elif route_type == "composting":
            batch.status = BatchStatus.COMPOSTED

        # Reduce the quantity
        batch.current_quantity = max(0, batch.current_quantity - quantity)

        # Create alert
        route_labels = {
            "food_bank": "🚛 Donated to Food Bank",
            "b2b_buyer": "🏪 Sold to B2B Buyer",
            "composting": "🌱 Sent to Composting",
        }
        alert = Alert(
            store_id=batch.store_id,
            alert_type=AlertType.FOOD_BANK_DISPATCH,
            batch_id=batch.id,
            title=f"{route_labels.get(route_type, '📦 Dispatched')}: {product_name}",
            message=(
                f"{quantity} {product.unit if product else 'units'} of {product_name} "
                f"dispatched to {partner_name}. "
                f"Value recovered: ₹{value_recovered:.2f}."
            ),
            priority=2,
        )
        self.db.add(alert)

        self.db.commit()
        self.db.refresh(route)

        return {
            "id": route.id,
            "batch_id": batch.id,
            "product_name": product_name,
            "route_type": route_type,
            "partner_name": partner_name,
            "quantity_dispatched": quantity,
            "value_recovered": value_recovered,
            "new_batch_status": batch.status.value,
            "message": f"Route dispatch complete: {product_name} → {partner_name} ({route_type})",
        }

    # ============================================================
    # CONFIRM: Confirm receipt of a dispatched batch
    # ============================================================

    def confirm_dispatch(self, route_id: int) -> dict:
        """
        Confirms that a dispatched batch was received by the partner.

        Returns:
            Dict with confirmation details
        """
        route = self.db.query(SecondaryRoute).filter(
            SecondaryRoute.id == route_id
        ).first()

        if not route:
            return {"error": "Route not found"}

        route.confirmed = True

        self.db.commit()

        return {
            "id": route.id,
            "batch_id": route.batch_id,
            "confirmed": True,
            "message": f"Dispatch #{route.id} confirmed. Partner has received the shipment.",
        }

    # ============================================================
    # HISTORY: Get routing history
    # ============================================================

    def get_routing_history(self, store_id: Optional[int] = None,
                            route_type: Optional[str] = None,
                            limit: int = 50) -> List[dict]:
        """
        Returns routing/dispatch history.

        Returns:
            List of dispatch records
        """
        query = self.db.query(SecondaryRoute).join(
            InventoryBatch, SecondaryRoute.batch_id == InventoryBatch.id
        )

        if store_id:
            query = query.filter(InventoryBatch.store_id == store_id)

        if route_type:
            query = query.filter(SecondaryRoute.route_type == route_type)

        query = query.order_by(SecondaryRoute.created_at.desc()).limit(limit)

        results = []
        for route in query.all():
            batch = route.batch
            product = batch.product if batch else None

            results.append({
                "id": route.id,
                "batch_id": route.batch_id,
                "product_name": product.name if product else "Unknown",
                "route_type": route.route_type.value if route.route_type else "unknown",
                "partner_name": route.partner_name,
                "partner_contact": route.partner_contact,
                "quantity_dispatched": route.quantity_dispatched,
                "dispatch_date": route.dispatch_date,
                "confirmed": route.confirmed,
                "value_recovered": route.value_recovered,
                "note": route.note,
                "created_at": route.created_at,
            })

        return results

    # ============================================================
    # ANALYTICS: Get routing statistics
    # ============================================================

    def get_routing_stats(self, store_id: Optional[int] = None) -> dict:
        """
        Returns analytics on routing performance.

        Returns:
            Dict with routing statistics
        """
        query = self.db.query(SecondaryRoute).join(
            InventoryBatch, SecondaryRoute.batch_id == InventoryBatch.id
        )
        if store_id:
            query = query.filter(InventoryBatch.store_id == store_id)

        all_routes = query.all()

        total_dispatches = len(all_routes)
        total_quantity = sum(r.quantity_dispatched for r in all_routes)
        total_value_recovered = sum(r.value_recovered for r in all_routes)
        confirmed_count = sum(1 for r in all_routes if r.confirmed)

        # Breakdown by route type
        by_type = {}
        for r in all_routes:
            rt = r.route_type.value if r.route_type else "unknown"
            if rt not in by_type:
                by_type[rt] = {"count": 0, "quantity": 0.0, "value": 0.0}
            by_type[rt]["count"] += 1
            by_type[rt]["quantity"] += r.quantity_dispatched
            by_type[rt]["value"] += r.value_recovered

        return {
            "total_dispatches": total_dispatches,
            "total_quantity_diverted": round(total_quantity, 1),
            "total_value_recovered": round(total_value_recovered, 2),
            "confirmed_rate": round(confirmed_count / total_dispatches * 100, 1) if total_dispatches > 0 else 0,
            "breakdown_by_route": by_type,
            "landfill_waste_avoided_kg": round(total_quantity * 0.5, 1),  # Approx 0.5kg per unit
        }

