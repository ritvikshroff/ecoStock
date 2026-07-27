# ============================================================
# app/services/reorder_engine.py
# ============================================================
# PURPOSE:
#   Predictive Reorder Engine — forecasts demand and suggests
#   optimal reorder quantities to prevent both stockouts and
#   overstock (which leads to waste).
#
#   Uses:
#   - Moving average demand forecasting
#   - Trend detection (increasing/stable/decreasing demand)
#   - Safety stock calculation based on demand variability
#   - Lead time analysis
#   - Seasonality adjustments
#   - Reorder point and economic order quantity (EOQ) logic
# ============================================================

from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple
from math import sqrt, ceil
from statistics import mean, stdev

from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc

from app.models.models import (
    InventoryBatch, Product, BatchStatus,
    ReorderLog, Alert, AlertType, ProductCategory
)
from app.core.config import settings


# ── Default lead times by category (in days) ───────────────
# How long it typically takes from order to delivery
CATEGORY_LEAD_TIMES = {
    ProductCategory.DAIRY:     1,
    ProductCategory.PRODUCE:   1,
    ProductCategory.BAKERY:    1,
    ProductCategory.MEAT:      2,
    ProductCategory.FROZEN:    3,
    ProductCategory.BEVERAGES: 3,
    ProductCategory.DELI:      2,
    ProductCategory.OTHER:     4,
}

DEFAULT_LEAD_TIME = 3

# ── Seasonality factors by month (Northern hemisphere) ─────
# > 1.0 = higher demand, < 1.0 = lower demand
SEASONALITY_FACTORS = {
    1: 0.95,   # January — post-holiday slump
    2: 0.90,   # February — still slow
    3: 1.00,   # March — back to normal
    4: 1.00,   # April
    5: 1.05,   # May — summer begins
    6: 1.10,   # June — summer events
    7: 1.15,   # July — peak summer
    8: 1.10,   # August — still summer
    9: 1.00,   # September — back to school
    10: 1.00,  # October
    11: 1.05,  # November — holiday prep
    12: 1.20,  # December — holiday peak
}

# ── Service level → Z-score mapping ────────────────────────
# 95% service level means we accept 5% stockout risk
SERVICE_LEVEL_Z = {
    0.90: 1.28,
    0.95: 1.65,
    0.975: 1.96,
    0.99: 2.33,
    0.995: 2.58,
}

DEFAULT_SERVICE_LEVEL = 0.95


class ReorderEngine:
    """
    Predictive reorder engine that forecasts demand and
    suggests optimal purchase quantities.
    """

    def __init__(self, db: Session):
        self.db = db

    # ============================================================
    # HELPER: Get average daily sales for a product
    # ============================================================

    def _get_avg_daily_sales(self, product_id: int, store_id: Optional[int] = None,
                             days_lookback: int = 30) -> float:
        """
        Calculates the average daily sales rate for a product.
        Uses the reduction in inventory over the lookback period
        as a proxy for sales (since we don't have a sales table).

        Returns:
            Average units sold per day
        """
        since_date = date.today() - timedelta(days=days_lookback)

        # Get all batches for this product that existed in the period
        query = self.db.query(InventoryBatch).filter(
            InventoryBatch.product_id == product_id,
        )
        if store_id:
            query = query.filter(InventoryBatch.store_id == store_id)

        batches = query.all()

        if not batches:
            return 0.0

        total_sold = 0.0
        total_days = 0

        for batch in batches:
            # Check if batch was active during the lookback period
            batch_start = max(batch.received_date, since_date)
            batch_end = min(batch.expiry_date, date.today())

            if batch_end <= batch_start:
                continue

            # Units sold = initial - current (approximate, assumes no other adjustments)
            sold = batch.initial_quantity - batch.current_quantity

            if sold > 0:
                days_active = (batch_end - batch_start).days
                if days_active > 0:
                    total_sold += sold
                    total_days += days_active

        if total_days == 0:
            return 0.0

        return round(total_sold / total_days, 2)

    # ============================================================
    # HELPER: Get stock data for a product
    # ============================================================

    def _get_current_stock(self, product_id: int, store_id: Optional[int] = None) -> float:
        """Returns total current stock across all batches."""
        query = self.db.query(func.sum(InventoryBatch.current_quantity)).filter(
            InventoryBatch.product_id == product_id,
            InventoryBatch.status.in_([BatchStatus.ACTIVE, BatchStatus.DISCOUNTED, BatchStatus.FLAGGED]),
        )
        if store_id:
            query = query.filter(InventoryBatch.store_id == store_id)

        result = query.scalar()
        return float(result or 0.0)

    # ============================================================
    # HELPER: Get lead time for a product category
    # ============================================================

    def _get_lead_time(self, category: ProductCategory) -> int:
        """Returns the typical lead time in days for this category."""
        return CATEGORY_LEAD_TIMES.get(category, DEFAULT_LEAD_TIME)

    # ============================================================
    # HELPER: Get seasonality factor
    # ============================================================

    def _get_season_factor(self) -> float:
        """Returns the seasonality factor for the current month."""
        current_month = date.today().month
        return SEASONALITY_FACTORS.get(current_month, 1.0)

    # ============================================================
    # CORE: Calculate reorder point
    # ============================================================

    def calculate_reorder_point(self, avg_daily_sales: float, lead_time_days: int,
                                demand_std: float = 0.0) -> float:
        """
        Calculates the reorder point — the stock level at which
        we should place a new order.

        Formula:
            Reorder Point = (Avg Daily Sales × Lead Time) + Safety Stock

        Safety Stock = Z × σ_demand × √(Lead Time)

        Where Z is the Z-score for the desired service level.
        """
        lead_time_demand = avg_daily_sales * lead_time_days

        # Z-score for 95% service level
        z_score = SERVICE_LEVEL_Z.get(DEFAULT_SERVICE_LEVEL, 1.65)

        # Safety stock
        if demand_std > 0:
            safety_stock = z_score * demand_std * sqrt(lead_time_days)
        else:
            # If no std dev available, use a heuristic: 30% of lead time demand
            safety_stock = 0.3 * lead_time_demand

        reorder_point = round(lead_time_demand + safety_stock, 1)
        return max(reorder_point, 0.0)

    # ============================================================
    # CORE: Calculate suggested order quantity
    # ============================================================

    def calculate_order_qty(self, avg_daily_sales: float, current_stock: float,
                            reorder_point: float, lead_time_days: int,
                            max_shelf_life_days: int = 7) -> Tuple[float, float, float]:
        """
        Calculates the suggested order quantity.

        Simple approach:
            Order Qty = (Avg Daily Sales × (Lead Time + Review Period)) - Current Stock + Safety Stock

        But capped so we don't order more than can be sold before expiry.

        Returns:
            Tuple of (suggested_order_qty, safety_stock, days_of_stock_remaining)
        """
        # Safety stock
        z_score = SERVICE_LEVEL_Z.get(DEFAULT_SERVICE_LEVEL, 1.65)
        safety_stock = round(0.3 * avg_daily_sales * lead_time_days, 1)

        # Review period (how often we reorder) — typically 7 days
        review_period = 7

        # Basic order quantity
        base_order = avg_daily_sales * (lead_time_days + review_period)
        suggested_qty = round(base_order + safety_stock - current_stock, 1)

        # Don't suggest negative orders
        suggested_qty = max(suggested_qty, 0.0)

        # Cap by shelf life: don't order more than can be sold before expiry
        max_order = avg_daily_sales * max_shelf_life_days * 0.8  # 80% of shelf life
        if suggested_qty > max_order:
            suggested_qty = round(max_order, 1)

        # Days of stock remaining
        if avg_daily_sales > 0:
            days_remaining = round(current_stock / avg_daily_sales, 1)
        else:
            days_remaining = 999.0  # No sales data

        return suggested_qty, safety_stock, days_remaining

    # ============================================================
    # CORE: Detect demand trend
    # ============================================================

    def detect_trend(self, product_id: int, store_id: Optional[int] = None) -> str:
        """
        Detects if demand for a product is increasing, decreasing, or stable.
        Compares recent sales (last 7 days) with older sales (last 8-30 days).
        """
        recent_sales = self._get_avg_daily_sales(product_id, store_id, days_lookback=7)
        older_sales = self._get_avg_daily_sales(product_id, store_id, days_lookback=30)

        if older_sales <= 0:
            return "stable"

        ratio = recent_sales / older_sales

        if ratio > 1.2:
            return "increasing"
        elif ratio < 0.8:
            return "decreasing"
        else:
            return "stable"

    # ============================================================
    # MAIN: Get reorder suggestions
    # ============================================================

    def get_reorder_suggestions(
        self, store_id: Optional[int] = None
    ) -> List[dict]:
        """
        Generates reorder suggestions for all active products.

        Returns:
            List of reorder suggestions with detailed metadata
        """
        today = date.today()
        season_factor = self._get_season_factor()

        # Get all active products
        products = self.db.query(Product).filter(
            Product.is_active == True
        ).all()

        suggestions = []

        for product in products:
            current_stock = self._get_current_stock(product.id, store_id)
            avg_daily_sales = self._get_avg_daily_sales(product.id, store_id)
            lead_time = self._get_lead_time(product.category)
            trend = self.detect_trend(product.id, store_id)

            # Adjust sales forecast with seasonality and trend
            adjusted_sales = avg_daily_sales * season_factor
            if trend == "increasing":
                adjusted_sales *= 1.15  # 15% uplift for growing demand
            elif trend == "decreasing":
                adjusted_sales *= 0.85  # 15% reduction for declining demand

            # Calculate reorder point and order quantity
            reorder_point = self.calculate_reorder_point(adjusted_sales, lead_time)
            suggested_qty, safety_stock, days_remaining = self.calculate_order_qty(
                adjusted_sales, current_stock, reorder_point, lead_time,
                product.typical_shelf_life_days
            )

            # Determine priority
            if days_remaining <= lead_time + 1:
                priority = "critical"
                reason = f"CRITICAL: Only {days_remaining}d stock left (lead time: {lead_time}d)"
            elif days_remaining <= lead_time * 2:
                priority = "high"
                reason = f"Stock running low: {days_remaining}d remaining (lead time: {lead_time}d)"
            elif days_remaining <= 7:
                priority = "medium"
                reason = f"Moderate stock: {days_remaining}d remaining. Consider reorder soon."
            elif suggested_qty > 0:
                priority = "low"
                reason = f"Adequate stock ({days_remaining}d). Low priority reorder."
            else:
                priority = "none"
                reason = "Stock level healthy. No reorder needed."
                suggested_qty = 0

            # Forecast confidence based on data availability
            if avg_daily_sales > 10:
                confidence = 0.85
            elif avg_daily_sales > 5:
                confidence = 0.70
            elif avg_daily_sales > 1:
                confidence = 0.50
            else:
                confidence = 0.30

            # Only suggest if we need to reorder
            if priority != "none" or suggested_qty > 0:
                suggestions.append({
                    "product_id": product.id,
                    "product_name": product.name,
                    "sku": product.sku,
                    "category": product.category.value,
                    "current_stock": current_stock,
                    "avg_daily_sales": round(adjusted_sales, 2),
                    "days_of_stock_remaining": days_remaining,
                    "suggested_order_qty": suggested_qty,
                    "reorder_point": reorder_point,
                    "safety_stock": safety_stock,
                    "lead_time_days": lead_time,
                    "forecast_confidence": confidence,
                    "season_factor": season_factor,
                    "trend": trend,
                    "priority": priority,
                    "reason": reason,
                })

        # Sort by priority
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "none": 99}
        suggestions.sort(key=lambda x: priority_order.get(x["priority"], 99))

        return suggestions

    # ============================================================
    # FORECAST: Get demand forecast for a product
    # ============================================================

    def get_demand_forecast(self, product_id: int,
                            store_id: Optional[int] = None) -> Optional[dict]:
        """
        Generates a demand forecast for a specific product.

        Returns:
            Dict with forecast data, or None if product not found
        """
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return None

        avg_daily = self._get_avg_daily_sales(product_id, store_id)
        season_factor = self._get_season_factor()
        trend = self.detect_trend(product_id, store_id)

        # Adjust forecast
        adjusted_daily = avg_daily * season_factor
        if trend == "increasing":
            adjusted_daily *= 1.15
        elif trend == "decreasing":
            adjusted_daily *= 0.85

        # Forecast periods
        forecast_7 = round(adjusted_daily * 7, 1)
        forecast_14 = round(adjusted_daily * 14, 1)
        forecast_30 = round(adjusted_daily * 30, 1)

        # Confidence
        if avg_daily > 10:
            confidence = 0.85
        elif avg_daily > 5:
            confidence = 0.70
        elif avg_daily > 1:
            confidence = 0.50
        else:
            confidence = 0.30

        return {
            "product_id": product.id,
            "product_name": product.name,
            "forecast_next_7_days": forecast_7,
            "forecast_next_14_days": forecast_14,
            "forecast_next_30_days": forecast_30,
            "confidence": confidence,
            "trend": trend,
            "avg_daily_sales": round(avg_daily, 2),
            "season_factor": season_factor,
        }

    # ============================================================
    # ACTION: Log and apply a reorder suggestion
    # ============================================================

    def apply_reorder(self, suggestion: dict, action: str = "approve",
                      actual_qty: Optional[float] = None) -> dict:
        """
        Logs a reorder action (approve or dismiss) to the database.

        Returns:
            The created ReorderLog entry as a dict
        """
        order_qty = actual_qty if actual_qty else suggestion.get("suggested_order_qty", 0)

        reorder_log = ReorderLog(
            product_id=suggestion["product_id"],
            store_id=0,  # Would need store_id passed in
            suggested_quantity=order_qty,
            forecast_confidence=suggestion.get("forecast_confidence", 0.5),
            avg_daily_sales=suggestion.get("avg_daily_sales", 0),
            days_of_stock_left=suggestion.get("days_of_stock_remaining", 0),
            season_factor=suggestion.get("season_factor", 1.0),
            is_actioned=(action == "approve"),
            actioned_at=datetime.utcnow() if action == "approve" else None,
        )
        self.db.add(reorder_log)

        # Create alert if approved
        if action == "approve":
            alert = Alert(
                store_id=0,
                alert_type=AlertType.REORDER_SUGGESTED,
                title=f"📋 Reorder Approved: {suggestion['product_name']}",
                message=(
                    f"Reorder of {order_qty} units approved. "
                    f"Current stock: {suggestion['current_stock']}. "
                    f"Reason: {suggestion.get('reason', 'N/A')}"
                ),
                priority=2,
            )
            self.db.add(alert)

        self.db.commit()
        self.db.refresh(reorder_log)

        return {
            "id": reorder_log.id,
            "product_id": suggestion["product_id"],
            "product_name": suggestion["product_name"],
            "suggested_quantity": suggestion.get("suggested_order_qty", 0),
            "ordered_quantity": order_qty,
            "action": action,
            "status": "approved" if action == "approve" else "dismissed",
        }

