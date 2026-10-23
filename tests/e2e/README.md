# ecoStock – Selenium test suite (10 tests)

| ID | Type | What it proves |
|----|------|----------------|
| BB-01 | Black box | Landing page → Manager portal, 4 KPIs render |
| BB-02 | Black box | Role switcher swaps the sidebar per persona |
| BB-03 | Black box | Shopper reserves item → pickup code → reservation listed → impact counter rises |
| BB-04 | Black box | Routing form rejects empty / 0 / non-numeric / over-stock quantity |
| BB-05 | Black box | NGO accepts donation → manifest → confirms receipt |
| WB-01 | White box | Inventory order == `fefoSort()` (expiry ASC, batch-no tie-break) |
| WB-02 | White box | Markdown panel boundary: exactly `0 ≤ daysToExpiry ≤ 3` |
| WB-03 | White box | 35 % of ₹320 = ₹208 in state + DOM, ESL sync `idle→syncing→synced`, invalid tier throws, change reaches storefront |
| WB-04 | White box | Dispatch conserves stock (−10), adds history + donation lot, waste KPI +10 kg, no double count |
| WB-05 | White box | Bid below reserve rejected with no state change; winning bid allocates lot + manifest; NGO cannot bid |

White-box tests read the app's internal store through `window.__ECOSTOCK__` and call the
real `lib/logic.js` functions inside the browser.

## Run it (live demo for the examiner)

```bash
pip install -r tests/e2e/requirements.txt
pytest tests/e2e                 # visible Chrome, ~0.9 s pause per step, elements highlighted
pytest tests/e2e --delay 2       # slower, easier to follow
pytest tests/e2e -m blackbox     # or: -m whitebox
pytest tests/e2e --headless      # CI, no window
```

The suite builds and starts the Next.js server itself (first run: `npm install` + build).
Chrome and the matching chromedriver are resolved automatically by Selenium Manager.
Env overrides: `BASE_URL`, `CHROME_BIN`, `CHROMEDRIVER_PATH`.
