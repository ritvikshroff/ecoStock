# ============================================================
# app/api/routes/routing.py
# ============================================================
# PURPOSE:
#   Secondary Routing API endpoints.
#   Manages food bank / B2B / composting dispatches.
# ============================================================

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.routing_engine import RoutingEngine
from app.schemas.schemas import (
    RouteSuggestion, RouteDispatch, RouteHistoryResponse, MessageResponse
)

router = APIRouter()


@router.get("/suggestions", response_model=List[RouteSuggestion])
def get_routing_suggestions(
    store_id: Optional[int] = None,
    max_days: int = Query(3, description="Max days until expiry to include"),
    db: Session = Depends(get_db)
):
    """Get routing suggestions for near-expiry batches."""
    engine = RoutingEngine(db)
    return engine.scan_for_routing(store_id=store_id, max_days_to_expiry=max_days)


@router.post("/dispatch", response_model=MessageResponse)
def dispatch_batch(
    dispatch_data: RouteDispatch,
    db: Session = Depends(get_db)
):
    """Execute a routing dispatch for a batch."""
    engine = RoutingEngine(db)
    result = engine.dispatch_batch(
        batch_id=dispatch_data.batch_id,
        route_type=dispatch_data.route_type,
        partner_name=dispatch_data.partner_name,
        partner_contact=dispatch_data.partner_contact,
        quantity=dispatch_data.quantity_dispatched,
        value_recovered=dispatch_data.value_recovered,
        note=dispatch_data.note,
    )

    if "error" in result:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])

    return MessageResponse(
        message=result["message"],
        detail=(
            f"Route: {result['route_type']} | "
            f"Partner: {result['partner_name']} | "
            f"Qty: {result['quantity_dispatched']} | "
            f"Value: ₹{result['value_recovered']:.2f}"
        )
    )


@router.post("/confirm/{route_id}", response_model=MessageResponse)
def confirm_dispatch(route_id: int, db: Session = Depends(get_db)):
    """Confirm that a dispatch was received by the partner."""
    engine = RoutingEngine(db)
    result = engine.confirm_dispatch(route_id)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return MessageResponse(message=result["message"])


@router.get("/history", response_model=List[RouteHistoryResponse])
def get_routing_history(
    store_id: Optional[int] = None,
    route_type: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get routing/dispatch history."""
    engine = RoutingEngine(db)
    return engine.get_routing_history(
        store_id=store_id,
        route_type=route_type,
        limit=limit
    )


@router.get("/stats")
def get_routing_stats(
    store_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get routing analytics and diversion statistics."""
    engine = RoutingEngine(db)
    return engine.get_routing_stats(store_id=store_id)


@router.get("/health")
def routing_health(db: Session = Depends(get_db)):
    """Check routing engine health."""
    engine = RoutingEngine(db)
    stats = engine.get_routing_stats()

    return {
        "status": "healthy",
        "total_dispatches": stats["total_dispatches"],
        "total_diverted": stats["total_quantity_diverted"],
        "total_value_recovered": stats["total_value_recovered"],
        "landfill_waste_avoided_kg": stats["landfill_waste_avoided_kg"],
    }

