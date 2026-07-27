# ecoStock 🥬

> Zero Waste-to-Landfill Intelligence Platform for Supermarkets

---

## What This Does
ecoStock tracks perishable inventory by **expiry date** (not arrival date), auto-discounts near-expiry items, forecasts demand to prevent overstock, and automatically routes unsalable stock to food banks / B2B buyers / composting.

---

## Project Structure (Final)

```
ecostock/
│
├── main.py                     ← Entry point. Run this to start the server.
├── quick_test.py               ← Import verification test
├── seed_data.py                ← Database seeder with realistic data
├── requirements.txt            ← All Python packages needed
├── .env.example                ← Copy this to .env and fill in your values
├── TODO.md                     ← Progress tracker
│
└── app/
    ├── core/
    │   ├── config.py           ← All settings (reads from .env)
    │   └── security.py         ← JWT tokens + password hashing
    │
    ├── db/
    │   └── database.py         ← PostgreSQL connection setup
    │
    ├── models/
    │   └── models.py           ← Database tables (8 tables)
    │
    ├── schemas/
    │   └── schemas.py          ← Pydantic request/response models
    │
    ├── services/
    │   ├── fefo_engine.py      ← FEFO: First-Expiry-First-Out core logic
    │   ├── pricing_engine.py   ← Dynamic Pricing: category decay curves, elasticity
    │   ├── reorder_engine.py   ← Predictive Reorder: demand forecasting, safety stock
    │   └── routing_engine.py   ← Secondary Routing: food bank, B2B, composting
    │
    ├── api/routes/
    │   ├── auth.py             ← Register, login, get current user
    │   ├── stores.py           ← Store CRUD
    │   ├── inventory.py        ← Products, batches, FEFO pipeline
    │   ├── alerts.py           ← Alert management (read, resolve)
    │   ├── pricing.py          ← Dynamic pricing suggestions, apply, bundles
    │   ├── reorder.py          ← Reorder suggestions, forecast, approve
    │   └── routing.py          ← Routing suggestions, dispatch, history
    │
    ├── static/
    │   ├── index.html          ← Single-page dashboard app
    │   ├── style.css           ← App styles (mobile-first)
    │   ├── app.js              ← Frontend logic (auth, data loading, UI)
    │   └── favicon.html        ← Favicon
    │
    └── utils/                  ← Reserved for helper functions
```

---

## Setup

### 1. Clone & Install
```bash
git clone <repo>
cd ecostock
pip install -r requirements.txt
```

### 2. Set Up Environment
```bash
cp .env.example .env
# Edit .env with your PostgreSQL credentials
```

### 3. Create PostgreSQL Database
```sql
CREATE DATABASE ecostock_db;
```

### 4. Run the Server
```bash
uvicorn main:app --reload
```

### 5. Open API Playground
```
http://localhost:8000/docs
```

---

## Build Phases (COMPLETED ✅)

| Phase | What We're Building | Status |
|-------|---------------------|--------|
| ✅ 0 | Project Scaffold + DB Models | Done |
| ✅ 1 | Schemas + FEFO Engine Service | Done |
| ✅ 2 | Dynamic Pricing Engine | Done |
| ✅ 3 | Predictive Reorder Engine | Done |
| ✅ 4 | Secondary Routing Engine | Done |
| ✅ 5 | Auth + API Routes | Done |
| ✅ 6 | Dashboard + Alerts | Done |

