# ============================================================
# app/schemas/schemas.py
# ============================================================
# PURPOSE:
#   Pydantic models for API request/response validation.
#   These define the shape of data that flows in/out of the API.
# ============================================================

from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


# ── Auth Schemas ──────────────────────────────────────────

class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Data stored inside the JWT token"""
    user_id: Optional[int] = None
    role: Optional[str] = None


class UserCreate(BaseModel):
    """Request body for creating a new user"""
    full_name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., max_length=150)
    password: str = Field(..., min_length=6, max_length=100)
    role: Optional[str] = "floor_staff"
    store_id: Optional[int] = None


class UserResponse(BaseModel):
    """Response body for user data (never exposes password)"""
    id: int
    full_name: str
    email: str
    role: str
    store_id: Optional[int] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    """Request body for login"""
    email: str
    password: str


# ── Store Schemas ─────────────────────────────────────────

class StoreCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    location: Optional[str] = None


class StoreResponse(BaseModel):
    id: int
    name: str
    location: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Product Schemas ───────────────────────────────────────

class ProductCreate(BaseModel):
    sku: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)
    category: str = Field(...)  # One of: dairy, produce, bakery, meat, frozen, beverages, deli, other
    brand: Optional[str] = None
    unit: str = "unit"
    base_price: float = Field(..., gt=0)
    cost_price: Optional[float] = None
    typical_shelf_life_days: int = 7
    discount_trigger_threshold: float = 0.7


class ProductResponse(BaseModel):
    id: int
    sku: str
    name: str
    category: str
    brand: Optional[str] = None
    unit: str
    base_price: float
    cost_price: Optional[float] = None
    typical_shelf_life_days: int
    discount_trigger_threshold: float
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Inventory Batch Schemas ───────────────────────────────

class InventoryBatchCreate(BaseModel):
    product_id: int
    store_id: int
    batch_number: Optional[str] = None
    barcode: Optional[str] = None
    manufacture_date: Optional[date] = None
    expiry_date: date
    received_date: date
    initial_quantity: float = Field(..., gt=0)
    current_quantity: float = Field(..., gt=0)
    current_price: float = Field(..., gt=0)
    storage_location: Optional[str] = None


class InventoryBatchResponse(BaseModel):
    id: int
    product_id: int
    store_id: int
    batch_number: Optional[str] = None
    barcode: Optional[str] = None
    manufacture_date: Optional[date] = None
    expiry_date: date
    received_date: date
    initial_quantity: float
    current_quantity: float
    current_price: float
    discount_percentage: float
    status: str
    storage_location: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── FEFO Engine Schemas ───────────────────────────────────

class FEFOScanResult(BaseModel):
    """Result of scanning inventory for FEFO compliance"""
    batch_id: int
    product_name: str
    sku: str
    expiry_date: date
    days_until_expiry: int
    current_quantity: float
    status: str
    current_price: float
    suggested_action: str  # "sell_now", "discount", "flag_for_routing", "ok"


class DiscountSuggestion(BaseModel):
    """Suggested discount for a batch"""
    batch_id: int
    product_name: str
    days_until_expiry: int
    suggested_discount_pct: float
    suggested_price: float
    reason: str


# ── Alert Schemas ─────────────────────────────────────────

class AlertResponse(BaseModel):
    id: int
    store_id: int
    assigned_to: Optional[int] = None
    alert_type: str
    batch_id: Optional[int] = None
    title: str
    message: str
    priority: int
    is_read: bool
    is_resolved: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Dynamic Pricing Schemas ────────────────────────────────

class PricingSuggestion(BaseModel):
    """Suggested price adjustment for a batch"""
    batch_id: int
    product_name: str
    category: str
    current_price: float
    suggested_price: float
    discount_pct: float
    days_until_expiry: int
    strategy: str  # "time_decay", "elasticity", "loss_leader", "bundle"
    reason: str
    expected_revenue_recovery: float
    urgency: str  # "low", "medium", "high", "critical"


class BatchPriceUpdate(BaseModel):
    """Manual price update for a batch"""
    batch_id: int
    new_price: float = Field(..., gt=0)
    reason: Optional[str] = None


class BundleSuggestion(BaseModel):
    """Suggested product bundle"""
    bundle_name: str
    product_ids: list[int]
    product_names: list[str]
    original_total: float
    bundle_price: float
    savings: float
    reason: str


# ── Predictive Reorder Schemas ────────────────────────────

class ReorderSuggestion(BaseModel):
    """Suggested reorder for a product"""
    product_id: int
    product_name: str
    sku: str
    category: str
    current_stock: float
    avg_daily_sales: float
    days_of_stock_remaining: float
    suggested_order_qty: float
    reorder_point: float
    safety_stock: float
    lead_time_days: int
    forecast_confidence: float  # 0.0 to 1.0
    season_factor: float
    priority: str  # "low", "medium", "high", "critical"
    reason: str


class ReorderAction(BaseModel):
    """Action a reorder suggestion"""
    reorder_id: int
    action: str = "approve"  # "approve" or "dismiss"
    actual_order_qty: Optional[float] = None


class DemandForecast(BaseModel):
    """Demand forecast for a product"""
    product_id: int
    product_name: str
    forecast_next_7_days: float
    forecast_next_14_days: float
    forecast_next_30_days: float
    confidence: float
    trend: str  # "increasing", "stable", "decreasing"


# ── Secondary Routing Schemas ─────────────────────────────

class RouteSuggestion(BaseModel):
    """Suggested routing for a batch"""
    batch_id: int
    product_name: str
    quantity: float
    unit: str
    expiry_date: date
    days_until_expiry: int
    suggested_routes: list[str]  # e.g., ["food_bank", "b2b_buyer", "composting"]
    recommended_route: str
    estimated_value_recovery: float
    reason: str
    urgency: str  # "low", "medium", "high", "critical"


class RouteDispatch(BaseModel):
    """Execute a routing dispatch"""
    batch_id: int
    route_type: str  # "food_bank", "b2b_buyer", "composting"
    partner_name: str = Field(..., min_length=1)
    partner_contact: Optional[str] = None
    quantity_dispatched: float = Field(..., gt=0)
    value_recovered: float = 0.0
    note: Optional[str] = None


class RouteHistoryResponse(BaseModel):
    """Response for a routing dispatch record"""
    id: int
    batch_id: int
    route_type: str
    partner_name: Optional[str] = None
    partner_contact: Optional[str] = None
    quantity_dispatched: float
    dispatch_date: Optional[datetime] = None
    confirmed: bool
    value_recovered: float
    note: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Generic Response Schemas ──────────────────────────────

class MessageResponse(BaseModel):
    """Simple message response"""
    message: str
    detail: Optional[str] = None


class PaginatedResponse(BaseModel):
    """Wrapper for paginated list responses"""
    items: List
    total: int
    page: int
    page_size: int


# ── Order Schemas ──────────────────────────────────────────

class OrderItemBase(BaseModel):
    product_id: int
    quantity: float = Field(..., gt=0)


class OrderItemCreate(OrderItemBase):
    pass


class OrderItemResponse(OrderItemBase):
    id: int
    order_id: int
    unit_price: float
    total_price: float
    product_name: Optional[str] = None

    class Config:
        from_attributes = True


class OrderBase(BaseModel):
    store_id: Optional[int] = None
    shipping_address: Optional[str] = None


class OrderCreate(OrderBase):
    items: List[OrderItemCreate]


class OrderResponse(OrderBase):
    id: int
    order_number: str
    customer_id: int
    status: str
    total_amount: float
    created_at: datetime
    items: List[OrderItemResponse] = []

    class Config:
        from_attributes = True


class OrderStatusUpdate(BaseModel):
    status: str

