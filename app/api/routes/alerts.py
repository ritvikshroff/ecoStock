# ============================================================
# app/api/routes/alerts.py
# ============================================================
# PURPOSE:
#   Alert management endpoints — view alerts, mark as read/resolved.
# ============================================================

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import Alert
from app.schemas.schemas import AlertResponse, MessageResponse

router = APIRouter()


@router.get("/", response_model=List[AlertResponse])
def list_alerts(
    store_id: Optional[int] = None,
    unresolved: bool = False,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List alerts, with optional filtering."""
    query = db.query(Alert)

    if store_id:
        query = query.filter(Alert.store_id == store_id)

    if unresolved:
        query = query.filter(Alert.is_resolved == False)

    query = query.order_by(Alert.priority.asc(), Alert.created_at.desc())
    return query.limit(limit).all()


@router.patch("/{alert_id}/read", response_model=AlertResponse)
def mark_alert_read(alert_id: int, db: Session = Depends(get_db)):
    """Mark an alert as read."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_read = True
    db.commit()
    db.refresh(alert)
    return alert


@router.patch("/{alert_id}/resolve", response_model=AlertResponse)
def resolve_alert(alert_id: int, db: Session = Depends(get_db)):
    """Mark an alert as resolved."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_resolved = True
    alert.is_read = True
    alert.resolved_at = datetime.utcnow()
    db.commit()
    db.refresh(alert)
    return alert

