# Vietnamese ETF Data Quality Validation

This folder contains standalone scripts for checking raw ETF data from `vnstock`.

The validation script does not write to PostgreSQL and does not modify any data.
It only downloads daily OHLCV data and reports potential quality issues.

## Validation Rules

For each ETF, the script checks:

- Empty dataset
- Duplicate dates in the `time` column
- Missing values in `open`, `high`, `low`, `close`, and `volume`
- Invalid OHLC relationships:
  - `high < low`
  - `open > high`
  - `open < low`
  - `close > high`
  - `close < low`
- Invalid volume values:
  - negative volume
  - non-numeric volume
- Non-monotonic dates
- Fully duplicate rows

Invalid records are reported clearly. The script does not use forward-fill,
interpolation, or silent row deletion.

## Run

```bash
python scripts/data/validate_vnstock_quality.py
```

## Cross-Source Anomaly Check

Use this script to investigate specific OHLC anomalies against another available
`vnstock` quote source:

```bash
python scripts/data/cross_source_anomaly_check.py
```

The script compares only the affected symbols and dates. It reports source
differences and does not correct or delete any data.
