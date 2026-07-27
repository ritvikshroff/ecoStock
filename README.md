# ecoStock 🥬

> Zero Waste-to-Landfill Intelligence Platform for Supermarkets

---

## What This Does
ecoStock tracks perishable inventory by **expiry date** (not arrival date), auto-discounts near-expiry items, forecasts demand to prevent overstock, and automatically routes unsalable stock to food banks / B2B buyers / composting.

---

## Project Structure

```
ecostock/
│
├── main.py                     ← Entry point. Run this to start the server.
│
├── requirements.txt            ← All Python packages needed
├── .env.example                ← Copy this to .env and fill in your values
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
    │   └── models.py           ← Database tables (8 tables defined here)
    │
    ├── schemas/                ← [NEXT] Pydantic request/response shapes
    ├── services/               ← [NEXT] Core business logic (FEFO engine, etc.)
    ├── api/
    │   └── routes/             ← [NEXT] API endpoints
    └── utils/                  ← [NEXT] Helper functions
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

## Build Phases

| Phase | What We're Building | Status |
|-------|---------------------|--------|
| ✅ 0 | Project Scaffold + DB Models | Done |
| 🔜 1 | Schemas + FEFO Engine Service | Next |
| ⬜ 2 | Dynamic Pricing Engine | Pending |
| ⬜ 3 | Predictive Reorder Engine | Pending |
| ⬜ 4 | Secondary Routing Engine | Pending |
| ⬜ 5 | Auth + API Routes | Pending |
| ⬜ 6 | Dashboard + Alerts | Pending |
