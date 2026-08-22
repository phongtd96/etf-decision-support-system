# Machine Learning Experiment

Machine learning was evaluated as a research module for the Vietnamese ETF Decision Support System. It is not part of the final SMART ranking because the tested models did not demonstrate reliable out-of-sample predictive value.

## Target

The target is positive 5-trading-day future return:

```text
future_return_5d = close[t+5] / close[t] - 1
target = 1 if future_return_5d > 0 else 0
```

## Features

Current `FEATURE_COLUMNS`:

- `daily_return`
- `volume_change`
- `close_to_sma20`
- `close_to_sma50`
- `rsi_14`
- `macd`
- `macd_signal`
- `volatility_20`
- `macd_histogram`

## Leakage Prevention

The ML dataset uses:

- ETF-grouped calculations;
- chronological train/test split;
- 5-period purge gap at the train/test boundary;
- no random split;
- future return used only for target construction, not as a feature.

The purge removes training rows whose target horizon would cross into the test period.

## Models

The tested models were:

- Logistic Regression
- Random Forest
- XGBoost

Hyperparameters were not tuned aggressively because this module is an experiment, not the final DSS method.

## Correct Majority Baseline

The corrected majority-class baseline accuracy is:

```text
0.5273
```

This baseline predicts the most frequent class in the test set.

## Model Results

| Model | Accuracy | Balanced Accuracy | Precision | Recall | F1 | ROC-AUC |
|---|---:|---:|---:|---:|---:|---:|
| Logistic Regression | 0.4727 | 0.4942 | 0.4695 | 0.8885 | 0.6144 | 0.4969 |
| XGBoost | 0.4691 | 0.4870 | 0.4649 | 0.8154 | 0.5922 | 0.4884 |
| Random Forest | 0.4691 | 0.4920 | 0.4684 | 0.9115 | 0.6188 | 0.4721 |

## Conclusion

No tested model demonstrated reliable out-of-sample predictive value. All three models had accuracy below the corrected majority-class baseline and ROC-AUC near or below 0.5.

Therefore, the ML module remains experimental and is not used in the final SMART ranking. The final DSS relies on transparent technical and market criteria through SMART.
