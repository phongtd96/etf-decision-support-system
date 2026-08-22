# Final Demo Script

This script is designed for a 5-7 minute academic project demonstration of the Vietnamese ETF Decision Support System.

## 0:00-0:40 Problem and Project Objective

Good morning/afternoon. This project is the Vietnamese ETF Decision Support System.

The problem is that ETF comparison is multi-dimensional. A user may care about recent return, technical trend, volatility, drawdown risk, and liquidity at the same time. These values have different units and sometimes conflict with each other, so they cannot simply be added together.

The objective of this project is to build a simple, explainable web-based Decision Support System for five Vietnamese domestic ETFs:

- `E1VFVN30`
- `FUEVFVND`
- `FUEVN100`
- `FUEDCMID`
- `FUESSVFL`

This is not an automated trading system and it does not provide financial advice. It supports analysis and comparison for educational purposes.

## 0:40-1:20 System Architecture and Data Pipeline

The system uses a monolithic architecture:

```text
External market data
-> ingestion and validation
-> PostgreSQL
-> technical analysis
-> SMART DSS
-> FastAPI
-> React frontend
```

Historical daily OHLCV data is collected for the five ETFs. The data is validated, stored in PostgreSQL, and then used to calculate technical indicators.

The backend is FastAPI with SQLAlchemy and Alembic. The frontend is React, Vite, TypeScript, Axios, and Recharts.

Machine learning exists as a separate experimental research branch. It is not part of the final SMART score.

## 1:20-2:10 Main Dashboard

Now I open the main dashboard at `/`.

The dashboard shows:

- the number of ETFs;
- the top-ranked ETF;
- the as-of date;
- the methodology, which is SMART.

The SMART ranking is the final DSS ranking. It combines five criteria:

| Criterion | Weight | Type |
|---|---:|---|
| Technical Momentum | 30% | Benefit |
| Return 20D | 25% | Benefit |
| Volatility 20D | 20% | Cost |
| Max Drawdown 60D | 15% | Cost |
| Average Volume 20D | 10% | Benefit |

The latest documented ranking example is:

| Rank | ETF | SMART Score |
|---:|---|---:|
| 1 | E1VFVN30 | 77.85 |
| 2 | FUEVFVND | 66.12 |
| 3 | FUEDCMID | 64.24 |
| 4 | FUESSVFL | 58.89 |
| 5 | FUEVN100 | 36.00 |

These values come from the backend API and may change when the dataset is updated.

## 2:10-3:20 ETF Detail Page

Next I click one ETF, for example `E1VFVN30`, to open `/etf/E1VFVN30`.

This page separates technical analysis from the SMART DSS result.

Technical analysis includes:

- close-price history;
- SMA20 and SMA50;
- RSI14;
- MACD;
- MACD signal;
- volatility20;
- technical score;
- technical signal: `BULLISH`, `NEUTRAL`, or `BEARISH`.

The technical score is not the same as the SMART score. The technical score summarizes technical indicators. The SMART score is a multi-criteria decision-support score using technical momentum, return, risk, and liquidity criteria.

The SMART breakdown shows:

- raw value;
- normalized utility;
- weight;
- weighted contribution.

The contribution chart explains how the final SMART score is constructed. The section "Why this ranking?" displays deterministic backend explanations. These are decision-support explanations, not investment recommendations.

## 3:20-4:10 Compare Page

Now I open `/compare`.

This page allows selecting between 2 and 5 ETFs. It uses `GET /api/dss/ranking` as the source of comparison data.

The first chart compares SMART scores directly. The second chart compares normalized criterion utilities.

This is important because raw values cannot simply be added together. For example:

- return is a percentage;
- volatility is a percentage but is a cost criterion;
- drawdown is also a cost criterion;
- volume is measured in shares;
- technical momentum is a score.

SMART normalizes each criterion into a utility from 0 to 1, then applies weights. This makes the comparison explainable and mathematically consistent.

## 4:10-5:00 Sensitivity Page

Now I open `/sensitivity`.

Sensitivity analysis asks: what happens if the decision-maker changes preferences?

The system provides exactly three predefined profiles:

| Profile | Technical Momentum | Return 20D | Volatility 20D | Max Drawdown 60D | Average Volume 20D |
|---|---:|---:|---:|---:|---:|
| Balanced | 0.30 | 0.25 | 0.20 | 0.15 | 0.10 |
| Growth | 0.35 | 0.35 | 0.10 | 0.10 | 0.10 |
| Risk-Averse | 0.20 | 0.15 | 0.30 | 0.25 | 0.10 |

The system does not recalculate market data separately for each profile. It reuses the same normalized utilities and only changes the weights. This isolates the effect of decision-maker preferences.

The latest documented sensitivity example showed the top ETF remained stable across scenarios, while `FUEVN100` moved from rank 5 to rank 2 under Risk-Averse preferences.

## 5:00-5:40 ML Experiment

Machine learning was tested as a research experiment, not as the final DSS method.

The target was:

```text
target = 1 if the 5-trading-day future return is positive, else 0
```

To reduce leakage, the project used:

- ETF-grouped feature calculations;
- chronological train/test split;
- a 5-period purge gap at the train/test boundary;
- no random split.

The tested models were:

- Logistic Regression;
- Random Forest;
- XGBoost.

The corrected majority-class baseline accuracy was `0.5273`.

Model results:

| Model | Accuracy | Balanced Accuracy | Precision | Recall | F1 | ROC-AUC |
|---|---:|---:|---:|---:|---:|---:|
| Logistic Regression | 0.4727 | 0.4942 | 0.4695 | 0.8885 | 0.6144 | 0.4969 |
| XGBoost | 0.4691 | 0.4870 | 0.4649 | 0.8154 | 0.5922 | 0.4884 |
| Random Forest | 0.4691 | 0.4920 | 0.4684 | 0.9115 | 0.6188 | 0.4721 |

The models did not outperform the corrected baseline and had weak out-of-sample predictive value. Therefore, ML was excluded from the final SMART DSS score.

## 5:40-6:30 Conclusion

In conclusion, this project is a Decision Support System, not an automated trading system.

It supports users by:

- collecting and validating ETF data;
- calculating technical indicators;
- ranking ETFs with transparent SMART criteria;
- explaining why an ETF receives a score;
- comparing ETFs using normalized utilities;
- testing ranking stability through sensitivity analysis;
- documenting ML experiments honestly when they do not improve the final decision method.

The key academic value is explainability. The user can see the data, criteria, weights, utilities, contributions, and sensitivity effects instead of receiving an unexplained prediction or financial recommendation.
