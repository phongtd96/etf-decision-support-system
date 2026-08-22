# DSS Methodology

The final Decision Support System uses SMART, the Simple Multi-Attribute Rating Technique. SMART was selected because it is transparent, easy to explain in an academic project, and suitable for combining multiple ETF evaluation criteria with different units.

## Why SMART

SMART is appropriate because:

- it is simple and maintainable;
- each criterion has a visible weight;
- raw values, normalized utilities, and weighted contributions can be shown to users;
- sensitivity analysis can be performed by changing only the weight vector.

Alternatives considered include AHP, TOPSIS, rule-based scoring, and machine-learning prediction. AHP would add pairwise-comparison complexity. TOPSIS is useful but less direct for explaining weighted contribution to a final score. ML was tested but did not outperform the corrected majority-class baseline.

## Criteria

| Criterion | Type | Reason |
|---|---|---|
| Technical Momentum | Benefit | Higher technical momentum is preferred. |
| Return 20D | Benefit | Higher recent return is preferred. |
| Volatility 20D | Cost | Lower volatility is preferred. |
| Max Drawdown 60D | Cost | Lower drawdown is preferred. |
| Average Volume 20D | Benefit | Higher liquidity is preferred. |

## Benefit and Cost Normalization

For a benefit criterion:

```text
utility = (value - min_value) / (max_value - min_value)
```

For a cost criterion:

```text
utility = (max_value - value) / (max_value - min_value)
```

Utilities are normalized across the same ETF universe and the same as-of date.

## Equal Values

If all ETFs have the same value for a criterion:

```text
max_value == min_value
```

then each ETF receives:

```text
utility = 0.5
```

This avoids division by zero and treats the criterion as neutral for that comparison.

## Weights

Default Balanced weights:

| Criterion | Weight |
|---|---:|
| Technical Momentum | 0.30 |
| Return 20D | 0.25 |
| Volatility 20D | 0.20 |
| Max Drawdown 60D | 0.15 |
| Average Volume 20D | 0.10 |

Weights sum to 1.0.

## SMART Score

For ETF `i` and criterion `j`:

```text
SMART_score_i = sum(utility_ij * weight_j * 100)
```

The final score is clamped to the 0-100 range and rounded for display.

## Ranking and Tie-Breaking

ETFs are ranked by:

1. SMART score descending;
2. symbol ascending if scores are equal.

This makes the result deterministic.

## Explainability

The API returns:

- raw criterion values;
- normalized utilities;
- criterion weights;
- weighted contributions;
- deterministic backend reasons.

The frontend displays these values in tables and charts so users can see how the SMART score is constructed.

## Sensitivity Analysis

Sensitivity analysis uses the same raw criteria and normalized utilities, then applies different predefined weight profiles. This isolates the effect of changing decision-maker preferences.

### Balanced

| Criterion | Weight |
|---|---:|
| Technical Momentum | 0.30 |
| Return 20D | 0.25 |
| Volatility 20D | 0.20 |
| Max Drawdown 60D | 0.15 |
| Average Volume 20D | 0.10 |

### Growth

| Criterion | Weight |
|---|---:|
| Technical Momentum | 0.35 |
| Return 20D | 0.35 |
| Volatility 20D | 0.10 |
| Max Drawdown 60D | 0.10 |
| Average Volume 20D | 0.10 |

### Risk-Averse

| Criterion | Weight |
|---|---:|
| Technical Momentum | 0.20 |
| Return 20D | 0.15 |
| Volatility 20D | 0.30 |
| Max Drawdown 60D | 0.25 |
| Average Volume 20D | 0.10 |

Rank change is calculated as:

```text
rank_change = balanced_rank - scenario_rank
```

Positive means the ETF moved upward. Negative means it moved downward.
