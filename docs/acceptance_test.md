# End-to-End Acceptance Test

This document describes a reproducible end-to-end verification flow for the Vietnamese ETF Decision Support System. It is intended for final project demonstration and submission review.

The flow verifies that PostgreSQL, migrations, data ingestion, technical indicators, FastAPI APIs, and the React frontend work together.

## 1. Preconditions

Required tools:

- Python 3.11
- Docker and Docker Compose
- Node.js and npm
- Git

Repository root:

```bash
cd /path/to/etf-decision-support-system
```

The examples below assume all commands are run from the repository root unless a `cd` command is shown.

## 2. Docker/PostgreSQL Startup

Create `backend/.env` if it does not exist:

```bash
cp backend/.env.example backend/.env
```

Start PostgreSQL:

```bash
docker compose --env-file backend/.env up -d postgres
```

Check container status:

```bash
docker compose ps
```

Expected result:

- `postgres` service is running.
- Health status eventually becomes healthy.

## 3. Environment Configuration

Confirm `backend/.env` contains local development values:

```text
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=etf_user
POSTGRES_PASSWORD=change_me
POSTGRES_DB=etf_dss
```

The real `.env` file must not be committed.

Frontend environment:

```bash
cp frontend/.env.example frontend/.env
```

Expected value:

```text
VITE_API_BASE_URL=http://localhost:8000
```

## 4. Alembic Migration

Install backend dependencies if needed:

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Apply migrations:

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
```

Expected result:

- Tables exist: `etfs`, `price_history`, `technical_indicators`, `predictions`, `recommendations`.
- `price_history` includes `data_source`.

## 5. ETF Seed

From the repository root:

```bash
backend/.venv/bin/python scripts/data/seed_etfs.py
```

Expected result:

- The five supported ETFs exist in the `etfs` table.

## 6. Historical Data Ingestion

From the repository root:

```bash
backend/.venv/bin/python scripts/data/ingest_etfs.py
```

Expected result:

- Historical daily OHLCV records are inserted or updated idempotently.
- `data_source` is reported as `VCI`.
- Running ingestion again should not create duplicate ETF/date rows.

## 7. Technical Indicator Calculation

From the repository root:

```bash
backend/.venv/bin/python scripts/data/calculate_indicators.py
```

Expected result:

- Technical indicators are calculated for available price history.
- The `technical_indicators` table contains rows for the supported ETFs.

## 8. Backend Startup

Start FastAPI:

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

Expected result:

- Backend runs at `http://localhost:8000`.

## 9. Backend Health Check

In a separate terminal:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status":"ok"}
```

## 10. SMART Ranking API Check

```bash
curl -i http://localhost:8000/api/dss/ranking
```

Expected result:

- HTTP `200`.
- Response includes `methodology: "SMART"`.
- Response includes non-empty `rankings`.
- Each ranking item includes criteria details and reasons.

## 11. Sensitivity API Check

```bash
curl -i http://localhost:8000/api/dss/sensitivity
```

Expected result:

- HTTP `200`.
- Response includes `profiles`.
- Profiles include `BALANCED`, `GROWTH`, and `RISK_AVERSE`.
- Response includes `comparisons` and `stability_summary`.

## 12. Frontend Startup

Install dependencies and run Vite:

```bash
cd frontend
npm install
npm run dev
```

Expected result:

- Frontend runs at `http://localhost:5173` or the next available Vite port.

## 13. Dashboard Verification

Open:

```text
http://localhost:5173/
```

Verify:

- Header displays `ETF Decision Support System`.
- Summary cards show ETF count, top-ranked ETF, as-of date, and methodology.
- SMART ranking bar chart is visible.
- Ranking table displays all supported ETFs with SMART score and raw criteria.
- ETF symbols are clickable.

## 14. ETF Detail Verification

Open a valid ETF detail page, for example:

```text
http://localhost:5173/etf/E1VFVN30
```

Verify:

- ETF symbol and as-of date are shown.
- SMART score and rank are shown.
- Technical signal and technical score are shown.
- Price chart displays close price, SMA20, and SMA50.
- Latest technical indicators are displayed.
- SMART breakdown table and contribution chart are displayed.
- `Why this ranking?` reasons are visible.

## 15. Compare Page Verification

Open:

```text
http://localhost:5173/compare
```

Verify:

- ETF selection controls are visible.
- At least two ETFs are required.
- SMART score comparison chart updates based on selected ETFs.
- Normalized utility comparison uses values from `0` to `1`.
- Comparison table shows rank, symbol, SMART score, and raw criteria.

## 16. Sensitivity Page Verification

Open:

```text
http://localhost:5173/sensitivity
```

Verify:

- Methodology explanation is visible.
- Balanced, Growth, and Risk-Averse weight cards are shown.
- Score comparison chart is visible.
- Ranking comparison table shows rank changes.
- Stability summary cards are visible.
- Notable rank changes are described without investment advice.

## 17. Error-State Verification

Backend unavailable:

1. Stop the backend process.
2. Refresh the frontend dashboard.
3. Confirm a user-friendly backend unavailable message is displayed.

Invalid ETF:

```text
http://localhost:5173/etf/UNKNOWN
```

Expected result:

- The detail page shows an error state rather than a blank page.

Invalid API symbol:

```bash
curl -i http://localhost:8000/api/dss/UNKNOWN
```

Expected result:

- HTTP `404`.

## 18. Backend Full Pytest

From the repository root:

```bash
backend/.venv/bin/pytest backend
```

Expected result:

- Full backend test suite passes.

## 19. Frontend Production Build

```bash
cd frontend
npm run build
```

Expected result:

- TypeScript check passes.
- Vite production build succeeds.
- A Recharts-related chunk-size warning is acceptable if the build succeeds.

## 20. Final Acceptance Checklist

Use this checklist for the final project demonstration:

- [ ] PostgreSQL starts successfully with Docker Compose.
- [ ] Alembic migrations apply successfully.
- [ ] ETF seed script completes.
- [ ] Historical data ingestion completes.
- [ ] Technical indicator calculation completes.
- [ ] Backend starts at `http://localhost:8000`.
- [ ] `/health` returns `{"status":"ok"}`.
- [ ] `/api/dss/ranking` returns SMART rankings.
- [ ] `/api/dss/sensitivity` returns three sensitivity profiles.
- [ ] Frontend starts with Vite.
- [ ] Dashboard page displays ranking data.
- [ ] ETF detail page displays charts, indicators, SMART breakdown, and reasons.
- [ ] Compare page works for 2-5 selected ETFs.
- [ ] Sensitivity page displays profile comparison and stability summary.
- [ ] Error states are user-friendly.
- [ ] Backend pytest passes.
- [ ] Frontend production build passes.
- [ ] No database schema changes, SMART formula changes, or ML result changes were made during acceptance testing.
