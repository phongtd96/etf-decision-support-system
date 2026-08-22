# API Documentation

The backend is a FastAPI application. The main local development base URL is:

```text
http://localhost:8000
```

## Health

### `GET /health`

Returns a simple health check.

Response description:

- `status`: `"ok"` when the API is running.

## Technical Analysis

### `GET /api/analysis/{symbol}`

Returns the latest technical analysis for one supported ETF.

Response description:

- `symbol`
- `date`
- `technical_score`
- `technical_signal`: `BULLISH`, `NEUTRAL`, or `BEARISH`
- `indicators`: SMA20, SMA50, RSI14, MACD, MACD signal, volatility20
- `reasons`: deterministic technical explanation strings

### `GET /api/analysis/ranking`

Returns the latest technical ranking for ETFs with available indicator data.

Response description:

- `as_of_date`
- `rankings`: rank, symbol, date, technical score, technical signal

## SMART DSS

### `GET /api/dss/ranking`

Returns the final SMART DSS ranking.

Response description:

- `as_of_date`
- `methodology`: `SMART`
- `weights`
- `rankings`

Each ranking item includes:

- `rank`
- `symbol`
- `smart_score`
- `criteria`: raw value, utility, weight, weighted contribution, criterion type
- `reasons`

### `GET /api/dss/{symbol}`

Returns the SMART DSS detail for one ETF. The backend calculates the full ETF universe first, then returns the selected ETF so normalization remains comparable.

Response description:

- `rank`
- `symbol`
- `smart_score`
- `criteria`
- `reasons`

### `GET /api/dss/sensitivity`

Returns SMART sensitivity analysis for the predefined scenarios:

- `BALANCED`
- `GROWTH`
- `RISK_AVERSE`

Response description:

- `as_of_date`
- `profiles`: scenario weight profiles
- `comparisons`: ETF score/rank under each scenario and rank changes
- `stability_summary`: top ETF stability and rank-change counts

## ETF Price History

### `GET /api/etfs/{symbol}/prices`

Returns chronological daily OHLCV price history for one ETF.

Optional query parameter:

- `days`: positive integer up to `1500`

Example:

```text
GET /api/etfs/E1VFVN30/prices?days=252
```

Response description:

- `symbol`
- `prices`: chronological list of date, open, high, low, close, volume

## Error Behavior

- Unsupported or missing ETFs return `404`.
- Invalid query parameters, such as `days=0`, return FastAPI validation errors.
- Endpoints are read-only for frontend analysis workflows.
