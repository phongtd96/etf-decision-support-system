# Demo Evidence Checklist

Use this checklist to collect screenshots for the final report and presentation. Each item lists what should be visible, why it matters academically, and where it fits in the report.

## A. Infrastructure

| Screenshot | What should be visible | Why it matters academically | Recommended report section |
|---|---|---|---|
| Docker PostgreSQL healthy | `docker compose ps` showing `postgres` running and healthy | Demonstrates reproducible local infrastructure | System Implementation |
| Alembic migration state | `alembic current` or successful `alembic upgrade head` output | Shows schema versioning and migration discipline | Database Design |
| Database tables | PostgreSQL table list showing `etfs`, `price_history`, `technical_indicators`, `predictions`, `recommendations` | Confirms implemented relational schema | Database Design |

## B. Data

| Screenshot | What should be visible | Why it matters academically | Recommended report section |
|---|---|---|---|
| ETF records | Five ETF symbols: `E1VFVN30`, `FUEVFVND`, `FUEVN100`, `FUEDCMID`, `FUESSVFL` | Proves the project scope is loaded into the database | Data Collection |
| Price history coverage | Row counts and min/max dates per ETF | Shows historical data availability | Data Collection |
| Data source | `price_history.data_source = VCI` | Documents the selected primary data source | Data Collection |
| Duplicate check | Query result showing no duplicate `(etf_id, date)` records | Demonstrates data integrity | Data Quality |
| EDA notebook | `notebooks/01_etf_eda.ipynb` summary tables and plots | Provides evidence of exploratory data analysis | Exploratory Data Analysis |

## C. Technical Analysis

| Screenshot | What should be visible | Why it matters academically | Recommended report section |
|---|---|---|---|
| Indicator table data | `technical_indicators` rows with SMA20, SMA50, RSI14, MACD, volatility20 | Shows derived analytical features | Technical Analysis |
| `GET /api/analysis/{symbol}` | JSON with indicators, technical score, technical signal, reasons | Proves backend technical analysis API works | API Implementation |
| Technical ranking | `GET /api/analysis/ranking` response | Shows ETF-level technical comparison | Technical Analysis |

## D. DSS

| Screenshot | What should be visible | Why it matters academically | Recommended report section |
|---|---|---|---|
| `GET /api/dss/ranking` | SMART methodology, weights, ranking items, criteria details | Confirms final DSS API | Decision Support Method |
| SMART criteria and weights | Table showing 30%, 25%, 20%, 15%, 10% criteria | Documents the decision model | Decision Support Method |
| Dashboard ranking | Frontend dashboard ranking chart and table | Demonstrates end-user DSS output | User Interface |
| ETF SMART breakdown | ETF detail page criterion contribution table/chart | Shows explainability of the SMART score | Explainability |
| Why this ranking | Backend reasons shown on ETF detail page | Shows transparent decision-support explanations | Explainability |

## E. Sensitivity Analysis

| Screenshot | What should be visible | Why it matters academically | Recommended report section |
|---|---|---|---|
| Sensitivity page | Balanced, Growth, Risk-Averse profile cards | Shows alternative decision-maker preferences | Sensitivity Analysis |
| Scenario ranking comparison | Score chart and ranking comparison table | Demonstrates effect of changing weights | Sensitivity Analysis |
| Rank changes | Example movement such as `FUEVN100` under Risk-Averse preferences if present | Shows ranking robustness or sensitivity | Sensitivity Analysis |

## F. ML Experiment

| Screenshot | What should be visible | Why it matters academically | Recommended report section |
|---|---|---|---|
| Dataset construction | `notebooks/02_ml_dataset.ipynb` showing dataset shape and feature columns | Shows ML dataset preparation | Machine Learning Experiment |
| Purged chronological split | Train/test date ranges and purged rows | Demonstrates leakage prevention | Machine Learning Experiment |
| Model comparison metrics | `notebooks/03_ml_model_comparison.ipynb` model metric table | Shows experimental results | Machine Learning Experiment |
| Baseline comparison | Correct majority baseline `0.5273` versus model accuracies | Justifies excluding ML from final DSS | Machine Learning Experiment |
| ML exclusion evidence | Documentation or notebook conclusion stating weak out-of-sample performance | Shows honest research conclusion | Discussion |

## G. System UI

| Screenshot | What should be visible | Why it matters academically | Recommended report section |
|---|---|---|---|
| Dashboard | Summary cards, SMART chart, ranking table | Shows main user workflow | User Interface |
| ETF Detail | Price chart, indicators, SMART score, contribution chart, reasons | Shows drill-down analysis | User Interface |
| Compare | ETF selectors, SMART score comparison, normalized utility chart | Shows comparative decision support | User Interface |
| Sensitivity | Profile cards, score chart, stability summary | Shows preference-based analysis | User Interface |

## H. Testing

| Screenshot | What should be visible | Why it matters academically | Recommended report section |
|---|---|---|---|
| Pytest result | Backend tests passing | Demonstrates backend correctness checks | Testing |
| Frontend build result | `npm run build` success | Demonstrates frontend TypeScript/build validity | Testing |
| Smoke test | `scripts/smoke_test.sh` passing | Demonstrates end-to-end API availability | Acceptance Testing |

## Evidence Notes

- Keep screenshots dated or grouped by demo run.
- Avoid showing real secrets from `backend/.env`.
- Prefer browser screenshots for UI pages and terminal screenshots for reproducibility evidence.
- Use the same ETF symbol, such as `E1VFVN30`, across several screenshots to make the report easier to follow.
