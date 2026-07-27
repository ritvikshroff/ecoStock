# ============================================================
# main.py  ← THE ENTRY POINT OF THE ENTIRE APPLICATION
# ============================================================
# PURPOSE:
#   This is the first file that runs when you start ecoStock.
#   It creates the FastAPI app, registers all routes, and
#   sets up the database tables.
#
# HOW TO RUN:
#   uvicorn main:app --reload
#
#   Then open: http://localhost:8000/docs
#   → This gives you an auto-generated API playground (Swagger UI)
#     where you can test every endpoint without writing any code.
# ============================================================

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import settings
from app.db.database import engine, Base

# ── Import all models so SQLAlchemy knows about them ──────
# Even if we don't use these directly here, SQLAlchemy needs
# to "see" the model classes before it can create the tables.
from app.models import models  # noqa: F401


# ============================================================
# STEP 1: Create all database tables
# ============================================================
# This looks at all the classes in models.py that inherit from
# Base and creates their corresponding tables in PostgreSQL.
#
# NOTE: In production we'd use Alembic migrations instead,
# but for development this is fine.

Base.metadata.create_all(bind=engine)


# ============================================================
# STEP 2: Initialize FastAPI App
# ============================================================

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    ## ecoStock API
    Smart inventory management platform for supermarkets.
    Reduces food waste through FEFO tracking, dynamic pricing,
    demand forecasting, and automated secondary routing.

    ### Modules
    - **FEFO Engine** — Expiry-priority inventory tracking
    - **Pricing Engine** — Automated markdown on near-expiry stock
    - **Reorder Engine** — Demand-based purchase forecasting
    - **Routing Engine** — Food bank / B2B / composting diversion
    """,
    docs_url="/docs",       # Swagger UI at http://localhost:8000/docs
    redoc_url="/redoc",     # ReDoc UI at http://localhost:8000/redoc
)


# ============================================================
# STEP 3: Add CORS Middleware
# ============================================================
# CORS = Cross-Origin Resource Sharing
# This allows the frontend (React/HTML) to call our API.
# Without this, browsers block requests from different origins.

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # In production: specify exact frontend URL
    allow_credentials=True,
    allow_methods=["*"],          # Allow GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],
)


# ============================================================
# STEP 4: Register API Routers
# ============================================================
# Each module gets its own router file.
# All routes are prefixed with /api/v1 for versioning.

from app.api.routes import auth, inventory, stores, alerts

app.include_router(auth.router,      prefix="/api/v1/auth",      tags=["Authentication"])
app.include_router(stores.router,    prefix="/api/v1/stores",    tags=["Stores"])
app.include_router(inventory.router, prefix="/api/v1/inventory", tags=["Inventory (FEFO)"])
app.include_router(alerts.router,    prefix="/api/v1/alerts",    tags=["Alerts"])
# Future modules:
# from app.api.routes import pricing, reorder, routing
# app.include_router(pricing.router,   prefix="/api/v1/pricing",   tags=["Dynamic Pricing"])
# app.include_router(reorder.router,   prefix="/api/v1/reorder",   tags=["Predictive Reorder"])
# app.include_router(routing.router,   prefix="/api/v1/routing",   tags=["Secondary Routing"])


# ============================================================
# STEP 5: Serve Static Frontend
# ============================================================
# A modern single-page-app dashboard served from /static
# Point your browser to http://localhost:8000 to use the app.

STATIC_DIR = Path(__file__).parent / "app" / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", tags=["Frontend"])
def serve_frontend():
    """Serve the ecoStock app dashboard (single-page application)."""
    return FileResponse(str(STATIC_DIR / "index.html"))


# ============================================================
# STEP 6: Health Check Route
# ============================================================
# Always have a health check. Used to verify the server is up.
# Load balancers and monitoring tools ping this endpoint.

# Note: The root "/" now serves the frontend app.
# Health check is at /health

@app.get("/health", tags=["Health"])
def health_check():
    """Health check for monitoring and load balancers."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }
