# ============================================================
# app/api/routes/inventory.py
# ============================================================
# PURPOSE:
#   Inventory management endpoints — CRUD for products and batches,
#   plus FEFO scan, auto-discount, and routing flagging.
# ============================================================

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import (
    Product, InventoryBatch, BatchStatus, ProductCategory
)
from app.schemas.schemas import (
    ProductCreate, ProductResponse,
    InventoryBatchCreate, InventoryBatchResponse,
    FEFOScanResult, MessageResponse
)
from app.services.fefo_engine import FEFOEngine

router = APIRouter()


# ============================================================
# ── PRODUCT ENDPOINTS ──────────────────────────────────────
# ============================================================

@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(product_data: ProductCreate, db: Session = Depends(get_db)):
    """Add a new product to the master catalog."""
    # Check SKU uniqueness
    existing = db.query(Product).filter(Product.sku == product_data.sku).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product with SKU '{product_data.sku}' already exists"
        )

    # Validate category
    valid_categories = [c.value for c in ProductCategory]
    if product_data.category not in valid_categories:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category. Must be one of: {', '.join(valid_categories)}"
        )

    product = Product(**product_data.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.get("/products", response_model=List[ProductResponse])
def list_products(
    category: Optional[str] = None,
    search: Optional[str] = None,
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """List all products, with optional filtering by category or search term."""
    query = db.query(Product)

    if active_only:
        query = query.filter(Product.is_active == True)

    if category:
        query = query.filter(Product.category == category)

    if search:
        query = query.filter(
            Product.name.ilike(f"%{search}%") |
            Product.sku.ilike(f"%{search}%")
        )

    return query.order_by(Product.name).all()


@router.get("/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Get a single product by ID."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


# ============================================================
# ── INVENTORY BATCH ENDPOINTS ──────────────────────────────
# ============================================================

@router.post("/batches", response_model=InventoryBatchResponse, status_code=status.HTTP_201_CREATED)
def create_batch(batch_data: InventoryBatchCreate, db: Session = Depends(get_db)):
    """Receive a new inventory batch (stock arrival)."""
    # Verify product exists
    product = db.query(Product).filter(Product.id == batch_data.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    batch = InventoryBatch(
        product_id=batch_data.product_id,
        store_id=batch_data.store_id,
        batch_number=batch_data.batch_number,
        barcode=batch_data.barcode,
        manufacture_date=batch_data.manufacture_date,
        expiry_date=batch_data.expiry_date,
        received_date=batch_data.received_date,
        initial_quantity=batch_data.initial_quantity,
        current_quantity=batch_data.current_quantity,
        current_price=batch_data.current_price,
        status=BatchStatus.ACTIVE,
        storage_location=batch_data.storage_location,
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch


@router.get("/batches", response_model=List[InventoryBatchResponse])
def list_batches(
    store_id: Optional[int] = None,
    product_id: Optional[int] = None,
    status: Optional[str] = None,
    expiring_soon: bool = False,
    db: Session = Depends(get_db)
):
    """List inventory batches with optional filters."""
    engine = FEFOEngine(db)
    batches = engine.get_fefo_sorted_batches(
        store_id=store_id,
        product_id=product_id,
        status=status,
        limit=200
    )

    if expiring_soon:
        today = date.today()
        batches = [b for b in batches if (b.expiry_date - today).days <= 7]

    return batches


@router.get("/batches/{batch_id}", response_model=InventoryBatchResponse)
def get_batch(batch_id: int, db: Session = Depends(get_db)):
    """Get a single batch by ID."""
    batch = db.query(InventoryBatch).filter(InventoryBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    return batch


# ============================================================
# ── FEFO ENGINE ENDPOINTS ──────────────────────────────────
# ============================================================

@router.get("/fefo/scan", response_model=List[FEFOScanResult])
def fefo_scan_inventory(store_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Scan inventory using FEFO logic — see what needs attention."""
    engine = FEFOEngine(db)
    return engine.scan_inventory(store_id=store_id)


@router.post("/fefo/apply-discounts", response_model=MessageResponse)
def fefo_apply_discounts(store_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Auto-apply discounts to near-expiry batches."""
    engine = FEFOEngine(db)
    applied = engine.apply_auto_discounts(store_id=store_id)

    if not applied:
        return MessageResponse(
            message="No discounts needed",
            detail="All batches are either fresh or already discounted."
        )

    return MessageResponse(
        message=f"Applied discounts to {len(applied)} batches",
        detail=" | ".join(
            [f"{a['product_name']}: ₹{a['old_price']:.2f}→₹{a['new_price']:.2f} ({a['discount_pct']:.0f}% off)"
             for a in applied[:5]]
        )
    )


@router.post("/fefo/flag-routing", response_model=MessageResponse)
def fefo_flag_routing(store_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Flag near-expiry batches for food bank / B2B / composting routing."""
    engine = FEFOEngine(db)
    flagged = engine.flag_for_routing(store_id=store_id)

    if not flagged:
        return MessageResponse(
            message="No batches need routing at this time"
        )

    return MessageResponse(
        message=f"Flagged {len(flagged)} batches for routing",
        detail=" | ".join(
            [f"{f['product_name']}: {f['quantity']} units ({f['days_until_expiry']} days left)"
             for f in flagged[:5]]
        )
    )


@router.post("/fefo/run-pipeline", response_model=MessageResponse)
def fefo_run_pipeline(store_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Run the full FEFO pipeline: scan → discount → flag routing."""
    engine = FEFOEngine(db)
    result = engine.run_full_pipeline(store_id=store_id)
    s = result["summary"]
    return MessageResponse(
        message=f"Pipeline complete: {s['discounts_applied']} discounts, {s['flagged_for_routing']} routing flags",
        detail=f"Scanned {s['total_batches_scanned']} batches total"
    )

