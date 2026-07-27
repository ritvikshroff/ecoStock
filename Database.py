# ============================================================
# app/db/database.py
# ============================================================
# PURPOSE:
#   Sets up the connection to PostgreSQL using SQLAlchemy.
#   Every database operation in the project goes through here.
#
# KEY CONCEPTS:
#   - engine      → the actual connection to Postgres
#   - SessionLocal → a "session" is like a transaction with the DB
#   - Base        → all our database models (tables) inherit from this
#   - get_db()    → a FastAPI "dependency" that gives each API request
#                   its own DB session, then closes it when done
# ============================================================

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


# ── Step 1: Create the Engine ─────────────────────────────
# The engine is SQLAlchemy's interface to the actual database.
# `pool_pre_ping=True` means: test connection before using it
#  (prevents errors if Postgres was restarted)

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    # How many connections to keep open at once (tune for production)
    pool_size=10,
    max_overflow=20,
)


# ── Step 2: Create Session Factory ────────────────────────
# SessionLocal is a "factory" — calling SessionLocal() gives
# you a new database session (transaction).
#
# autocommit=False → we manually commit (safer, more control)
# autoflush=False  → we manually flush (prevents premature queries)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# ── Step 3: Create Base Class ─────────────────────────────
# All our database models (Product, Inventory, etc.) will
# inherit from this Base. SQLAlchemy uses it to track what
# tables exist and generate SQL.

Base = declarative_base()


# ── Step 4: DB Dependency for FastAPI ─────────────────────
# This function is used as a FastAPI "dependency injection".
# FastAPI calls this automatically for every API request.
#
# HOW IT WORKS:
#   1. Opens a DB session
#   2. Gives it to the route handler (via `db` parameter)
#   3. After the request finishes → closes the session
#
# USAGE in a route:
#   from app.db.database import get_db
#   from sqlalchemy.orm import Session
#   from fastapi import Depends
#
#   @router.get("/items")
#   def get_items(db: Session = Depends(get_db)):
#       return db.query(Product).all()

def get_db():
    """
    Yields a database session for a single request.
    Always closes the session after the request, even if it crashes.
    """
    db = SessionLocal()
    try:
        yield db          # ← give the session to the route handler
    finally:
        db.close()        # ← always runs, even if an error occurred