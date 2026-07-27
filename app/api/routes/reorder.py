# ============================================================
# app/api/routes/reorder.py
# ============================================================
# PURPOSE:
#   Predictive Reorder API endpoints.
#   Provides demand forecasts and reorder suggestions to
#   help managers stock optimally.
# ============================================================

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.reorder_engine import ReorderEngine
from app.schemas.schemas import (
    ReorderSuggestion, ReorderAction, DemandForecast, MessageResponse
)

router = APIRouter()


@router.get("/suggestions", response_model=List[ReorderSuggestion])
def get_reorder_suggestions(
    store_id: Optional[int] = None,
    priority: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get reorder suggestions for all products."""
    engine = ReorderEngine(db)
    suggestions = engine.get_reorder_suggestions(store_id=store_id)

    if priority:
        suggestions = [s for s in suggestions if s["priority"] == priority]

    return suggestions


@router.get("/forecast/{product_id}", response_model=DemandForecast)
def get_product_forecast(
    product_id: int,
    store_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get demand forecast for a specific product."""
    engine = ReorderEngine(db)
    forecast = engine.get_demand_forecast(product_id, store_id=store_id)

    if not forecast:
        raise HTTPException(status_code=404, detail="Product not found")

    return forecast


@router.post("/action", response_model=MessageResponse)
def take_reorder_action(
    action_data: ReorderAction,
    store_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Approve or dismiss a reorder suggestion."""
    engine = ReorderEngine(db)

    # Find the suggestion
    suggestions = engine.get_reorder_suggestions(store_id=store_id)
    suggestion = None
    for s in suggestions:
        if s["product_id"] == action_data.reorder_id:
            suggestion = s
            break

    if not suggestion:
        raise HTTPException(status_code=404, detail="Reorder suggestion not found for this product")

    # Apply the action
    result = engine.apply_reorder(
        suggestion,
        action=action_data.action,
        actual_qty=action_data.actual_order_qty
    )

    return MessageResponse(
        message=f"Reorder {action_data.action}d: {suggestion['product_name']}",
        detail=(
            f"Status: {result['status']}. "
            f"Suggested: {result['suggested_quantity']} units. "
            f"Ordered: {result['ordered_quantity']} units."
        )
    )


@router.get("/health")
def reorder_health(store_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Check reorder engine health and stats."""
    engine = ReorderEngine(db)
    suggestions = engine.get_reorder_suggestions(store_id=store_id)

    priority_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for s in suggestions:
        priority_counts[s["priority"]] = priority_counts.get(s["priority"], 0) + 1

    return {
        "status": "healthy",
        "total_products_analyzed": len(suggestions),
        "needs_reorder": priority_counts["critical"] + priority_counts["high"],
        "priority_breakdown": priority_counts,
    }

