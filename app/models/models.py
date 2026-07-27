# ============================================================
# app/models/models.py
# ============================================================
# PURPOSE:
#   Defines ALL database tables for ecoStock as Python classes.
#   SQLAlchemy translates these classes into actual SQL tables.
#
# EACH CLASS = ONE TABLE IN POSTGRESQL
#
# TABLE OVERVIEW:
#   User          → staff accounts (manager / floor staff)
#   Store         → supermarket store locations
#   Product       → master product catalog (SKU level)
#   InventoryBatch→ actual stock on hand (batch + expiry level) ← FEFO lives here
#   PriceHistory  → tracks every auto-discount the system applies
#   SecondaryRoute→ logs of food bank / B2B / composting dispatches
#   Alert         → notifications sent to staff
#   ReorderLog    → predicted reorder quantities from the forecast engine
# ============================================================

import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Float, Boolean,
    DateTime, Date, ForeignKey, Enum, Text
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


# ============================================================
# ENUMS — Fixed choice lists (like dropdowns in a form)
# ============================================================

class UserRole(str, enum.Enum):
    """Who can do what in ecoStock"""
    ADMIN           = "admin"           # Full access
    STORE_MANAGER   = "store_manager"   # Can override discount thresholds
    FLOOR_STAFF     = "floor_staff"     # Can only complete tasks

class ProductCategory(str, enum.Enum):
    """
    Category matters because each has a different decay curve.
    Dairy spoils faster than canned goods — the FEFO engine uses this.
    """
    DAIRY       = "dairy"
    PRODUCE     = "produce"       # Leafy greens, fruits, vegetables
    BAKERY      = "bakery"
    MEAT        = "meat"
    FROZEN      = "frozen"
    BEVERAGES   = "beverages"
    DELI        = "deli"
    OTHER       = "other"

class BatchStatus(str, enum.Enum):
    """The lifecycle state of an inventory batch"""
    ACTIVE          = "active"          # On shelf, being sold normally
    DISCOUNTED      = "discounted"      # Auto-markdown applied
    FLAGGED         = "flagged"         # Near expiry, awaiting routing
    DONATED         = "donated"         # Sent to food bank
    SOLD_B2B        = "sold_b2b"        # Sold to restaurant/bakery buyer
    COMPOSTED       = "composted"       # Sent to composting
    EXPIRED_WASTED  = "expired_wasted"  # Did not make it (landfill — we want 0 of these)
    SOLD            = "sold"            # Fully sold before expiry (ideal)

class RouteType(str, enum.Enum):
    """What secondary channel was used for diversion"""
    FOOD_BANK   = "food_bank"
    B2B_BUYER   = "b2b_buyer"
    COMPOSTING  = "composting"

class AlertType(str, enum.Enum):
    """What kind of notification was sent"""
    ROTATION_NEEDED     = "rotation_needed"     # Move older stock to front
    MARKDOWN_APPLIED    = "markdown_applied"    # Price dropped automatically
    FOOD_BANK_DISPATCH  = "food_bank_dispatch"  # Send to food bank now
    REORDER_SUGGESTED   = "reorder_suggested"   # Time to reorder this SKU


# ============================================================
# TABLE 1: users
# ============================================================

class User(Base):
    __tablename__ = "users"

    # ── Primary Key ───────────────────────────────────────
    id          = Column(Integer, primary_key=True, index=True)

    # ── User Info ─────────────────────────────────────────
    full_name   = Column(String(100), nullable=False)
    email       = Column(String(150), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)   # NEVER store plain text

    # ── Role & Access ─────────────────────────────────────
    role        = Column(Enum(UserRole), default=UserRole.FLOOR_STAFF)
    store_id    = Column(Integer, ForeignKey("stores.id"), nullable=True)
    is_active   = Column(Boolean, default=True)

    # ── Timestamps ────────────────────────────────────────
    created_at  = Column(DateTime, server_default=func.now())  # Auto-set on insert
    updated_at  = Column(DateTime, onupdate=func.now())        # Auto-set on update

    # ── Relationships ─────────────────────────────────────
    store       = relationship("Store", back_populates="staff")


# ============================================================
# TABLE 2: stores
# ============================================================

class Store(Base):
    __tablename__ = "stores"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(150), nullable=False)
    location    = Column(String(255))
    is_active   = Column(Boolean, default=True)
    created_at  = Column(DateTime, server_default=func.now())

    # ── Relationships ─────────────────────────────────────
    staff       = relationship("User", back_populates="store")
    products    = relationship("InventoryBatch", back_populates="store")


# ============================================================
# TABLE 3: products  (Master Catalog — one row per SKU)
# ============================================================

class Product(Base):
    __tablename__ = "products"

    id              = Column(Integer, primary_key=True, index=True)

    # ── Product Identity ──────────────────────────────────
    sku             = Column(String(50), unique=True, nullable=False, index=True)
    name            = Column(String(200), nullable=False)
    category        = Column(Enum(ProductCategory), nullable=False)
    brand           = Column(String(100))
    unit            = Column(String(20), default="unit")  # "kg", "litre", "unit"

    # ── Pricing ───────────────────────────────────────────
    base_price      = Column(Float, nullable=False)       # Normal selling price
    cost_price      = Column(Float)                       # What the store paid

    # ── FEFO Engine Config (per product) ──────────────────
    # How many days of shelf life this product typically has
    typical_shelf_life_days = Column(Integer, default=7)

    # At what % of shelf life used should we start discounting?
    # e.g. 0.7 = start discounting when 70% of shelf life is gone
    discount_trigger_threshold = Column(Float, default=0.7)

    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime, server_default=func.now())

    # ── Relationships ─────────────────────────────────────
    batches         = relationship("InventoryBatch", back_populates="product")


# ============================================================
# TABLE 4: inventory_batches  ← THE HEART OF THE FEFO ENGINE
# ============================================================
# Each row = one physical batch of stock received on a specific date.
# The FEFO engine queries this table to find what expires soonest.

class InventoryBatch(Base):
    __tablename__ = "inventory_batches"

    id              = Column(Integer, primary_key=True, index=True)

    # ── Foreign Keys ──────────────────────────────────────
    product_id      = Column(Integer, ForeignKey("products.id"), nullable=False)
    store_id        = Column(Integer, ForeignKey("stores.id"), nullable=False)

    # ── Batch Identity ────────────────────────────────────
    batch_number    = Column(String(100), index=True)         # From supplier
    barcode         = Column(String(100), index=True)

    # ── Dates ─────────────────────────────────────────────
    manufacture_date    = Column(Date, nullable=True)
    expiry_date         = Column(Date, nullable=False)        # THE most important field
    received_date       = Column(Date, nullable=False)        # When it arrived at store

    # ── Quantity ──────────────────────────────────────────
    initial_quantity    = Column(Float, nullable=False)       # How much we received
    current_quantity    = Column(Float, nullable=False)       # How much is left

    # ── Pricing (can change as auto-discounts apply) ───────
    current_price       = Column(Float, nullable=False)       # Live price (changes with markdown)
    discount_percentage = Column(Float, default=0.0)          # Current % off

    # ── Status ────────────────────────────────────────────
    status              = Column(Enum(BatchStatus), default=BatchStatus.ACTIVE)

    # ── Tracking ──────────────────────────────────────────
    storage_location    = Column(String(100))                 # Aisle / shelf location
    temperature_log     = Column(Text)                        # JSON string of IoT readings

    created_at          = Column(DateTime, server_default=func.now())
    updated_at          = Column(DateTime, onupdate=func.now())

    # ── Relationships ─────────────────────────────────────
    product     = relationship("Product", back_populates="batches")
    store       = relationship("Store", back_populates="products")
    price_logs  = relationship("PriceHistory", back_populates="batch")
    routes      = relationship("SecondaryRoute", back_populates="batch")


# ============================================================
# TABLE 5: price_history  (Audit log of every markdown)
# ============================================================

class PriceHistory(Base):
    __tablename__ = "price_history"

    id              = Column(Integer, primary_key=True, index=True)
    batch_id        = Column(Integer, ForeignKey("inventory_batches.id"), nullable=False)

    # ── What changed ──────────────────────────────────────
    old_price       = Column(Float, nullable=False)
    new_price       = Column(Float, nullable=False)
    discount_pct    = Column(Float, nullable=False)     # e.g. 20.0 = 20% off

    # ── Why it changed ────────────────────────────────────
    days_to_expiry  = Column(Integer)                   # How many days were left when this triggered
    triggered_by    = Column(String(50), default="system")  # "system" or "manager_override"
    note            = Column(String(255))

    created_at      = Column(DateTime, server_default=func.now())

    # ── Relationships ─────────────────────────────────────
    batch           = relationship("InventoryBatch", back_populates="price_logs")


# ============================================================
# TABLE 6: secondary_routes  (Diversion log — food bank / B2B / compost)
# ============================================================

class SecondaryRoute(Base):
    __tablename__ = "secondary_routes"

    id              = Column(Integer, primary_key=True, index=True)
    batch_id        = Column(Integer, ForeignKey("inventory_batches.id"), nullable=False)

    # ── Where it went ─────────────────────────────────────
    route_type      = Column(Enum(RouteType), nullable=False)
    partner_name    = Column(String(200))           # Food bank name / B2B buyer name
    partner_contact = Column(String(200))

    # ── Quantity dispatched ───────────────────────────────
    quantity_dispatched = Column(Float, nullable=False)
    dispatch_date       = Column(DateTime)
    confirmed           = Column(Boolean, default=False)    # Did partner confirm receipt?

    # ── Value recovered ───────────────────────────────────
    # For B2B: actual money received. For donations: $0 (but saves disposal cost)
    value_recovered = Column(Float, default=0.0)

    note            = Column(String(500))
    created_at      = Column(DateTime, server_default=func.now())

    # ── Relationships ─────────────────────────────────────
    batch           = relationship("InventoryBatch", back_populates="routes")


# ============================================================
# TABLE 7: alerts  (Staff notifications)
# ============================================================

class Alert(Base):
    __tablename__ = "alerts"

    id              = Column(Integer, primary_key=True, index=True)

    # ── Who gets it ───────────────────────────────────────
    store_id        = Column(Integer, ForeignKey("stores.id"), nullable=False)
    assigned_to     = Column(Integer, ForeignKey("users.id"), nullable=True)  # Optional

    # ── What it's about ───────────────────────────────────
    alert_type      = Column(Enum(AlertType), nullable=False)
    batch_id        = Column(Integer, ForeignKey("inventory_batches.id"), nullable=True)

    title           = Column(String(200), nullable=False)
    message         = Column(Text, nullable=False)
    priority        = Column(Integer, default=2)    # 1=High, 2=Medium, 3=Low

    # ── Status ────────────────────────────────────────────
    is_read         = Column(Boolean, default=False)
    is_resolved     = Column(Boolean, default=False)
    resolved_at     = Column(DateTime, nullable=True)

    created_at      = Column(DateTime, server_default=func.now())


# ============================================================
# TABLE 8: reorder_logs  (Predictive reorder suggestions)
# ============================================================

class ReorderLog(Base):
    __tablename__ = "reorder_logs"

    id              = Column(Integer, primary_key=True, index=True)
    product_id      = Column(Integer, ForeignKey("products.id"), nullable=False)
    store_id        = Column(Integer, ForeignKey("stores.id"), nullable=False)

    # ── Forecast output ───────────────────────────────────
    suggested_quantity  = Column(Float, nullable=False)   # How much to order
    forecast_confidence = Column(Float)                   # 0.0 to 1.0 confidence score

    # ── Basis of the forecast ─────────────────────────────
    avg_daily_sales     = Column(Float)
    days_of_stock_left  = Column(Float)
    season_factor       = Column(Float, default=1.0)      # >1 = busy season, <1 = slow

    # ── Status ────────────────────────────────────────────
    is_actioned         = Column(Boolean, default=False)  # Did manager place the order?
    actioned_at         = Column(DateTime, nullable=True)

    created_at          = Column(DateTime, server_default=func.now())

