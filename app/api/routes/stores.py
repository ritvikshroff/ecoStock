# ============================================================
# app/api/routes/stores.py
# ============================================================
# PURPOSE:
#   Store management endpoints — CRUD for supermarket locations.
# ============================================================

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import Store
from app.schemas.schemas import StoreCreate, StoreResponse

router = APIRouter()


@router.post("/stores", response_model=StoreResponse, status_code=status.HTTP_201_CREATED)
def create_store(store_data: StoreCreate, db: Session = Depends(get_db)):
    """Register a new store location."""
    store = Store(name=store_data.name, location=store_data.location)
    db.add(store)
    db.commit()
    db.refresh(store)
    return store


@router.get("/stores", response_model=List[StoreResponse])
def list_stores(db: Session = Depends(get_db)):
    """List all active stores."""
    return db.query(Store).filter(Store.is_active == True).all()


@router.get("/stores/{store_id}", response_model=StoreResponse)
def get_store(store_id: int, db: Session = Depends(get_db)):
    """Get a single store by ID."""
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    return store

