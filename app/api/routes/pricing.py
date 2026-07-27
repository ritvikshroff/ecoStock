# ============================================================
# app/api/routes/pricing.py
# ============================================================
# PURPOSE:
#   Dynamic Pricing API endpoints.
#   Provides access to the Dynamic Pricing Engine's suggestions
#   and allows applying/reviewing price changes.
# ============================================================

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.pricing_engine import PricingEngine
from app.schemas.schemas import (
    PricingSuggestion, BatchPriceUpdate, BundleSuggestion, MessageResponse
)

router = APIRouter()


@router.get("/suggestions", response_model=List[PricingSuggestion])
def get_pricing_suggestions(
    store_id: Optional[int] = None,
    urgency: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get dynamic pricing suggestions for all batches."""
    engine = PricingEngine(db)
    suggestions = engine.get_pricing_suggestions(store_id=store_id)

    if urgency:
        suggestions = [s for s in suggestions if s["urgency"] == urgency]

    return suggestions


@router.get("/suggestions/{batch_id}", response_model=PricingSuggestion)
def get_batch_pricing_suggestion(
    batch_id: int,
    db: Session = Depends(get_db)
):
    """Get pricing suggestion for a specific batch."""
    engine = PricingEngine(db)
    suggestions = engine.get_pricing_suggestions()
    for s in suggestions:
        if s["batch_id"] == batch_id:
            return s
    raise HTTPException(status_code=404, detail="Batch not found")


@router.post("/apply", response_model=MessageResponse)
def apply_pricing(
    store_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Apply dynamic pricing suggestions to critical/high urgency batches."""
    engine = PricingEngine(db)
    applied = engine.apply_pricing(store_id=store_id)

    if not applied:
        return MessageResponse(
            message="No pricing changes needed",
            detail="All batches already at optimal prices."
        )

    return MessageResponse(
        message=f"Applied dynamic pricing to {len(applied)} batches",
        detail=" | ".join(
            [f"{a['product_name']}: ₹{a['old_price']:.2f}→₹{a['new_price']:.2f} ({a['strategy']})"
             for a in applied[:5]]
        )
    )


@router.get("/bundles", response_model=List[BundleSuggestion])
def get_bundle_suggestions(
    store_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get product bundle suggestions for near-expiry items."""
    engine = PricingEngine(db)
    return engine.suggest_bundles(store_id=store_id)


@router.get("/health")
def pricing_health(db: Session = Depends(get_db)):
    """Check pricing engine health and stats."""
    engine = PricingEngine(db)
    suggestions = engine.get_pricing_suggestions()

    urgency_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for s in suggestions:
        urgency_counts[s["urgency"]] = urgency_counts.get(s["urgency"], 0) + 1

    return {
        "status": "healthy",
        "total_analyzed": len(suggestions),
        "needs_attention": urgency_counts["critical"] + urgency_counts["high"],
        "urgency_breakdown": urgency_counts,
    }

