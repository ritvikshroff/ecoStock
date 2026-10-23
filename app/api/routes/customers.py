# ============================================================
# app/api/routes/customers.py
# ============================================================
# PURPOSE:
#   Customer-facing endpoints — browse products, place orders, track orders.
# ============================================================

from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session, joinedload
from typing import List
import uuid
from datetime import datetime

from app.db.database import get_db
from app.models.models import User, Order, OrderItem, Product, InventoryBatch
from app.schemas.schemas import (
    OrderCreate, OrderResponse, OrderItemResponse, ProductResponse,
    OrderStatusUpdate, MessageResponse
)
from app.core.security import extract_token, decode_access_token

router = APIRouter(tags=["customer"])


# ── Dependency: Get current customer user ───────────────────

def get_current_customer(authorization: str = Header(default=""), db: Session = Depends(get_db)) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid Authorization header")
    token = authorization.replace("Bearer ", "")
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    user_id = int(payload.get("sub"))
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.role != "customer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Customer access required")
    return user


# ── GET /customer/products — Browse available products ──────

@router.get("/products", response_model=List[ProductResponse])
def list_products(current_user: User = Depends(get_current_customer), db: Session = Depends(get_db)):
    products = db.query(Product).filter(Product.is_active == True).all()
    return products


# ── GET /customer/products/{id} — Get single product ────────

@router.get("/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, current_user: User = Depends(get_current_customer), db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id, Product.is_active == True).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


# ── POST /customer/orders — Place a new order ───────────────

@router.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def place_order(order_data: OrderCreate, current_user: User = Depends(get_current_customer), db: Session = Depends(get_db)):
    # Generate order number
    order_number = "ORD-" + uuid.uuid4().hex[:8].upper()

    total = 0.0
    db_order = Order(
        order_number=order_number,
        customer_id=current_user.id,
        store_id=order_data.store_id,
        shipping_address=order_data.shipping_address,
        status="pending",
        total_amount=0.0,
    )
    db.add(db_order)
    db.flush()

    for item_data in order_data.items:
        product = db.query(Product).filter(Product.id == item_data.product_id, Product.is_active == True).first()
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product {item_data.product_id} not found")
        unit_price = product.base_price
        item_total = unit_price * item_data.quantity
        total += item_total
        db_item = OrderItem(
            order_id=db_order.id,
            product_id=item_data.product_id,
            quantity=item_data.quantity,
            unit_price=unit_price,
            total_price=item_total,
        )
        db.add(db_item)

    db_order.total_amount = total
    db.commit()
    db.refresh(db_order)
    return db_order


# ── GET /customer/orders — List customer's orders ───────────

@router.get("/orders", response_model=List[OrderResponse])
def list_orders(current_user: User = Depends(get_current_customer), db: Session = Depends(get_db)):
    orders = (
        db.query(Order)
        .options(joinedload(Order.items).joinedload(OrderItem.product))
        .filter(Order.customer_id == current_user.id)
        .order_by(Order.created_at.desc())
        .all()
    )
    return orders


# ── GET /customer/orders/{id} — Get single order ────────────

@router.get("/orders/{order_id}", response_model=OrderResponse)
def get_order(order_id: int, current_user: User = Depends(get_current_customer), db: Session = Depends(get_db)):
    order = (
        db.query(Order)
        .options(joinedload(Order.items).joinedload(OrderItem.product))
        .filter(Order.id == order_id, Order.customer_id == current_user.id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


# ── GET /customer/dashboard-stats — Customer dashboard stats ─

@router.get("/dashboard-stats")
def customer_dashboard_stats(current_user: User = Depends(get_current_customer), db: Session = Depends(get_db)):
    orders = db.query(Order).filter(Order.customer_id == current_user.id).all()
    total_orders = len(orders)
    delivered = len([o for o in orders if o.status == "delivered"])
    pending = len([o for o in orders if o.status in ("pending", "confirmed", "packed", "shipped")])
    total_spent = sum(o.total_amount for o in orders if o.status == "delivered")
    return {
        "total_orders": total_orders,
        "delivered": delivered,
        "pending": pending,
        "total_spent": round(total_spent, 2),
    }