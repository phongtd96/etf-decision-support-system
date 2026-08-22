# Vietnamese ETF Decision Support System

A university graduation project that provides a web-based Decision Support System (DSS) for analyzing and comparing Vietnamese domestic ETFs listed on HOSE. The final decision-support method is SMART, a transparent multi-criteria scoring method. Machine learning is included only as an experimental research module and is not used in the final SMART score.

## Project Overview

The system helps users review historical ETF data, technical indicators, SMART ranking, ETF comparison, and sensitivity analysis. It is an academic DSS, not a trading platform, and it does not claim to predict future returns reliably.

## Problem Statement

ETF investors often need to compare funds across return, trend, volatility, drawdown, and liquidity. These criteria have different units and can conflict with each other. The project addresses this by combining normalized criteria into a simple, explainable ranking.

## Objectives

- Collect and validate Vietnamese ETF historical OHLCV data.
- Store ETF data in PostgreSQL using a maintainable monolithic architecture.
- Calculate technical indicators and technical scores.
- Rank ETFs using a transparent SMART decision-support method.
- Provide ETF comparison and SMART sensitivity analysis in a React frontend.
- Experiment with ML models and document why they are excluded from the final DSS score.

## Scope

The initial scope covers five Vietnamese domestic ETFs, daily historical data, technical analysis, SMART scoring, frontend visualization, and research notebooks. It excludes authentication, real-time trading, order execution, portfolio management, and investment recommendations such as BUY/HOLD/SELL.

## Supported ETFs

| Symbol | ETF | Benchmark |
|---|---|---|
| E1VFVN30 | DCVFM VN30 ETF | VN30 |
| FUEVFVND | DCVFMVN Diamond ETF | VN Diamond |
| FUEVN100 | VinaCapital VN100 ETF | VN100 |
| FUEDCMID | DCVFM VN Midcap ETF | VN Midcap |
| FUESSVFL | SSIAM VNFIN Lead ETF | VNFIN Lead |

## Core Features

- Historical ETF data ingestion from VCI through `vnstock`.
- Data quality validation and cross-source anomaly investigation scripts.
- Technical indicators: SMA20, SMA50, RSI14, MACD, MACD signal, volatility20.
- Technical scoring API and ranking API.
- SMART DSS ranking with transparent criteria, utilities, weights, and contributions.
- ETF detail dashboard with price history, SMA overlays, indicators, SMART breakdown, and reasons.
- ETF comparison page using normalized utility values.
- SMART sensitivity analysis for Balanced, Growth, and Risk-Averse profiles.
- ML experiment notebooks and backend utilities for leakage-safe dataset construction.

## System Architecture

The project uses a simple monolithic architecture:

```text
External market data
  -> data ingestion and validation scripts
  -> PostgreSQL
  -> FastAPI services
  -> SMART DSS and technical analysis APIs
  -> React frontend
```

The backend is organized by API routes, schemas, services, models, database configuration, and ML utilities. It does not use microservices, AI agents, RAG, or LLMs.

## Decision-Support Methodology

The final DSS uses SMART: Simple Multi-Attribute Rating Technique. Each ETF receives normalized utilities for five criteria. Each utility is multiplied by a predefined weight, then summed into a score from 0 to 100. ETFs are sorted by SMART score descending, with symbol ascending as a deterministic tie-break.

## SMART Formula

For ETF `i` and criterion `j`:

```text
SMART_score_i = sum(utility_ij * weight_j * 100)
```

Benefit criteria are better when higher. Cost criteria are better when lower. Min-max normalization is used across the ETF universe for the same as-of date.

## Criteria and Weights

| Criterion | Weight | Type |
|---|---:|---|
| Technical Momentum | 30% | Benefit |
| Return 20D | 25% | Benefit |
| Volatility 20D | 20% | Cost |
| Max Drawdown 60D | 15% | Cost |
| Average Volume 20D | 10% | Benefit |

Sensitivity profiles are documented in [docs/dss_methodology.md](docs/dss_methodology.md).

## Data Flow

```text
VCI/vnstock data
  -> scripts/data/ingest_etfs.py
  -> price_history
  -> scripts/data/calculate_indicators.py
  -> technical_indicators
  -> analysis_service.py and dss_service.py
  -> FastAPI endpoints
  -> React dashboard, detail, compare, sensitivity pages
```

## Machine-Learning Experiment

The ML experiment predicts whether the 5-trading-day future return is positive. It uses leakage-safe feature engineering, ETF-grouped calculations, a chronological split, and a 5-period purge gap. Models tested:

- Logistic Regression
- Random Forest
- XGBoost

## ML Result and Rationale

The corrected majority-class baseline accuracy is `0.5273`. The tested models did not outperform this baseline out of sample. Therefore, ML remains an experimental research module and is not included in the final SMART DSS score.

Detailed metrics are documented in [docs/ml_experiment.md](docs/ml_experiment.md).

## Tech Stack

- Backend: Python 3.11, FastAPI, SQLAlchemy 2.x, Alembic, PostgreSQL 16
- Data: pandas, NumPy, vnstock
- ML experiment: scikit-learn, XGBoost
- Frontend: React, Vite, TypeScript, Axios, Recharts
- Infrastructure: Docker Compose
- Testing: pytest, TypeScript build checks

## Repository Structure

```text
backend/        FastAPI backend, SQLAlchemy models, Alembic, tests
frontend/       React + Vite + TypeScript frontend
scripts/data/   Data ingestion, validation, and indicator scripts
notebooks/      EDA, ML, and DSS sensitivity notebooks
docs/           Project documentation
docker-compose.yml
README.md
```

## Prerequisites

- Python 3.11
- Node.js and npm
- Docker and Docker Compose
- PostgreSQL client tools are optional but useful

## Environment Setup

Create a backend environment file from the example:

```bash
cp backend/.env.example backend/.env
```

Set a local development password in `backend/.env`. Do not commit real `.env` files.

Frontend environment example:

```bash
cp frontend/.env.example frontend/.env
```

`frontend/.env` should usually contain:

```text
VITE_API_BASE_URL=http://localhost:8000
```

## PostgreSQL and Docker Setup

Start PostgreSQL:

```bash
docker compose --env-file backend/.env up -d postgres
```

Stop PostgreSQL:

```bash
docker compose down
```

PostgreSQL data is stored in the named Docker volume `etf_dss_postgres_data`.

## Backend Setup

From the repository root:

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the backend:

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000`.

## Database Migrations

Apply migrations:

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
```

## ETF Data Ingestion

Seed ETF master data if needed:

```bash
backend/.venv/bin/python scripts/data/seed_etfs.py
```

Ingest historical ETF prices:

```bash
backend/.venv/bin/python scripts/data/ingest_etfs.py
```

These commands are run from the repository root.

## Technical Indicator Calculation

After price data exists:

```bash
backend/.venv/bin/python scripts/data/calculate_indicators.py
```

This fills the `technical_indicators` table used by technical analysis and SMART DSS.

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The Vite frontend usually runs at `http://localhost:5173`.

## API Endpoints

Important endpoints:

- `GET /health`
- `GET /api/analysis/{symbol}`
- `GET /api/analysis/ranking`
- `GET /api/dss/ranking`
- `GET /api/dss/{symbol}`
- `GET /api/dss/sensitivity`
- `GET /api/etfs/{symbol}/prices?days=252`

See [docs/api.md](docs/api.md) for details.

## Testing

Backend:

```bash
backend/.venv/bin/pytest backend
```

Frontend build and TypeScript check:

```bash
cd frontend
npm run build
```

## Main Application Pages

- `/` Dashboard: summary cards, SMART ranking chart, ranking table.
- `/etf/:symbol` ETF detail: price history, indicators, SMART breakdown, reasons.
- `/compare` ETF comparison: select 2-5 ETFs and compare scores/utilities.
- `/sensitivity` SMART sensitivity: compare Balanced, Growth, and Risk-Averse profiles.

## Research Notebooks

- `notebooks/01_etf_eda.ipynb`: exploratory data analysis.
- `notebooks/02_ml_dataset.ipynb`: leakage-safe ML dataset preparation.
- `notebooks/03_ml_model_comparison.ipynb`: ML model comparison.
- `notebooks/04_dss_sensitivity.ipynb`: SMART sensitivity analysis.

## Limitations

- The system is based on daily historical data, not real-time market data.
- The ETF universe is limited to five Vietnamese ETFs.
- SMART weights are predefined and not user-customizable yet.
- ML models did not outperform the corrected majority-class baseline.
- The application does not provide trading execution or personalized financial advice.

## Future Work

- Add user-adjustable SMART weights with validation.
- Add more Vietnamese ETFs or fund metadata.
- Add portfolio-level comparison.
- Improve data-source monitoring and scheduled ingestion.
- Explore additional ML features only if justified by out-of-sample performance.
- Add frontend tests and deployment documentation.

## Educational and Financial Disclaimer

This system provides decision-support analysis for educational purposes and does not constitute financial advice. It should not be used as the sole basis for investment decisions.
