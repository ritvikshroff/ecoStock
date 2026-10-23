# ecoStock frontend (Next.js 14 + Tailwind + Lucide)

```bash
cd frontend
npm install
cp .env.example .env.local   # NEXT_PUBLIC_API_URL, defaults to http://localhost:8000
npm run dev                  # http://localhost:3000
```

Three role-based portals: `/manager`, `/consumer`, `/partner` (landing page at `/`).
State lives in `src/context/StoreContext.js` (mock data). Each mutation is also mirrored,
best-effort, to the FastAPI backend via `src/lib/api.js`; if the API is unreachable the navbar
shows "Mock data mode" and everything keeps working. Pure business rules (FEFO, markdown tiers,
CO₂ factor, validation) are in `src/lib/logic.js`.

Tests: see `../tests/e2e/README.md`.
