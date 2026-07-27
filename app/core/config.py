# ============================================================
# app/core/config.py
# ============================================================
# PURPOSE:
#   This file reads your .env file and turns it into a Python
#   object called `settings`. Every other file in the project
#   imports from here to get config values.
#
# HOW IT WORKS:
#   Pydantic's BaseSettings automatically reads environment
#   variables or .env file values into typed Python fields.
# ============================================================

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """
    All configuration for ecoStock lives here.
    Values are auto-loaded from your .env file.
    """

    # ── App Info ──────────────────────────────────────────
    APP_NAME: str = "ecoStock"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # ── Database ──────────────────────────────────────────
    DATABASE_URL: str = Field(
        default="postgresql://postgres:password@localhost:5432/ecostock_db",
        description="Full PostgreSQL connection string"
    )

    # ── Redis ─────────────────────────────────────────────
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for task queues"
    )

    # ── Security ──────────────────────────────────────────
    SECRET_KEY: str = Field(
        default="change-this-secret-key",
        description="Used to sign JWT tokens — MUST be changed in production"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ── Business Logic ────────────────────────────────────
    # These control WHEN the FEFO engine fires alerts

    DISCOUNT_ALERT_DAYS: int = Field(
        default=3,
        description="Days before expiry to start auto-discounting"
    )

    FOOD_BANK_ALERT_HOURS: int = Field(
        default=24,
        description="Hours before expiry to trigger food bank routing"
    )

    # Discount tiers: list of (days_remaining, discount_percentage)
    # Read from env as "3:20,2:35,1:50" and parsed below
    DISCOUNT_TIERS_RAW: str = Field(
        default="3:20,2:35,1:50",
        alias="DISCOUNT_TIERS"
    )

    @property
    def DISCOUNT_TIERS(self) -> list[tuple[int, float]]:
        """
        Converts "3:20,2:35,1:50" → [(3, 20.0), (2, 35.0), (1, 50.0)]
        So the FEFO engine can look up: "3 days left → 20% off"
        """
        tiers = []
        for pair in self.DISCOUNT_TIERS_RAW.split(","):
            days, discount = pair.strip().split(":")
            tiers.append((int(days), float(discount)))
        # Sort by days descending: [3 days, 2 days, 1 day]
        return sorted(tiers, key=lambda x: x[0], reverse=True)

    # ── Pydantic Config ───────────────────────────────────
    class Config:
        env_file = ".env"           # Read from .env file
        env_file_encoding = "utf-8"
        extra = "ignore"            # Ignore any extra env vars we don't define


# ── Singleton ─────────────────────────────────────────────
# Create ONE instance that the whole app imports.
# Usage in any other file:
#   from app.core.config import settings
#   print(settings.DATABASE_URL)

settings = Settings()

