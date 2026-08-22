from datetime import date, timedelta

import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.ml.features import FEATURE_COLUMNS, purged_chronological_split
from app.ml.training import (
    build_models,
    compare_models,
    evaluate_model,
    feature_importance_mapping,
    majority_baseline_accuracy,
    predict_positive_probability,
    train_models,
)


def training_dataset(row_count: int = 80) -> pd.DataFrame:
    rows = []
    start = date(2022, 1, 1)
    for symbol, offset in [("AAA", 0), ("BBB", 1)]:
        for index in range(row_count):
            target = int((index + offset) % 3 != 0)
            rows.append(
                {
                    "symbol": symbol,
                    "date": pd.Timestamp(start + timedelta(days=index)),
                    "daily_return": 0.001 * (index % 7) + offset * 0.001,
                    "volume_change": 0.002 * (index % 5),
                    "close_to_sma20": 0.01 * target - 0.005,
                    "close_to_sma50": 0.008 * target - 0.004,
                    "rsi_14": 45 + target * 15 + (index % 4),
                    "macd": 0.1 * target - 0.03,
                    "macd_signal": 0.02,
                    "volatility_20": 0.2 + 0.01 * (index % 3),
                    "macd_histogram": 0.1 * target - 0.05,
                    "future_return_5d": 0.01 if target == 1 else -0.01,
                    "target": target,
                    "target_date": pd.Timestamp(start + timedelta(days=index + 5)),
                }
            )
    return pd.DataFrame(rows)


def split_dataset() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    return purged_chronological_split(
        training_dataset(),
        test_start_date="2022-03-01",
        horizon=5,
    )


def test_training_uses_feature_columns_only() -> None:
    train_df, _, _ = split_dataset()
    models = train_models(train_df)

    logistic = models["Logistic Regression"]
    assert logistic.feature_names_in_.tolist() == FEATURE_COLUMNS


def test_purged_rows_are_excluded() -> None:
    train_df, _, purged_df = split_dataset()

    assert not purged_df.empty
    assert set(zip(train_df["symbol"], train_df["date"])).isdisjoint(
        set(zip(purged_df["symbol"], purged_df["date"]))
    )


def test_train_test_separation_is_preserved() -> None:
    train_df, test_df, _ = split_dataset()

    assert train_df["date"].max() < test_df["date"].min()
    assert set(zip(train_df["symbol"], train_df["date"])).isdisjoint(
        set(zip(test_df["symbol"], test_df["date"]))
    )


def test_logistic_regression_pipeline_includes_scaler() -> None:
    model = build_models()["Logistic Regression"]

    assert isinstance(model, Pipeline)
    assert isinstance(model.named_steps["scaler"], StandardScaler)


def test_metrics_contain_expected_fields() -> None:
    train_df, test_df, _ = split_dataset()
    model = train_models(train_df)["Random Forest"]

    evaluation = evaluate_model("Random Forest", model, test_df)

    assert set(evaluation.__dict__) == {
        "model",
        "accuracy",
        "balanced_accuracy",
        "precision",
        "recall",
        "f1",
        "roc_auc",
        "confusion_matrix",
    }


def test_roc_auc_calculation() -> None:
    train_df, test_df, _ = split_dataset()
    model = train_models(train_df)["Logistic Regression"]

    evaluation = evaluate_model("Logistic Regression", model, test_df)

    assert 0 <= evaluation.roc_auc <= 1


def test_majority_baseline_calculation() -> None:
    train_df, test_df, _ = split_dataset()

    baseline = majority_baseline_accuracy(train_df, test_df)

    assert baseline.majority_class in {0, 1}
    assert 0 <= baseline.majority_baseline_accuracy <= 1


def test_majority_baseline_uses_test_majority_class_zero() -> None:
    test_df = training_dataset(row_count=5).iloc[:5].copy()
    test_df["target"] = [0, 0, 0, 1, 1]

    baseline = majority_baseline_accuracy(pd.DataFrame(), test_df)

    assert baseline.majority_class == 0
    assert baseline.majority_baseline_accuracy == 0.6


def test_majority_baseline_uses_test_majority_class_one() -> None:
    test_df = training_dataset(row_count=5).iloc[:5].copy()
    test_df["target"] = [1, 1, 1, 0, 0]

    baseline = majority_baseline_accuracy(pd.DataFrame(), test_df)

    assert baseline.majority_class == 1
    assert baseline.majority_baseline_accuracy == 0.6


def test_prediction_probabilities_are_between_0_and_1() -> None:
    train_df, test_df, _ = split_dataset()
    model = train_models(train_df)["XGBoost"]

    probabilities = predict_positive_probability(model, test_df)

    assert np.all(probabilities >= 0)
    assert np.all(probabilities <= 1)


def test_feature_importance_mapping_matches_feature_columns() -> None:
    train_df, _, _ = split_dataset()
    models = train_models(train_df)

    for model_name, model in models.items():
        mapping = feature_importance_mapping(model_name, model)
        assert set(mapping["feature"]) == set(FEATURE_COLUMNS)
        assert len(mapping) == len(FEATURE_COLUMNS)


def test_deterministic_behavior_with_fixed_random_state() -> None:
    train_df, test_df, _ = split_dataset()

    first = compare_models(train_models(train_df, random_state=7), test_df)
    second = compare_models(train_models(train_df, random_state=7), test_df)

    pd.testing.assert_frame_equal(first, second)
