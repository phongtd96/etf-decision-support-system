from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from app.ml.features import FEATURE_COLUMNS, MLDatasetError

RANDOM_STATE = 42


@dataclass(frozen=True)
class ModelEvaluation:
    model: str
    accuracy: float
    balanced_accuracy: float
    precision: float
    recall: float
    f1: float
    roc_auc: float
    confusion_matrix: list[list[int]]


@dataclass(frozen=True)
class MajorityBaseline:
    majority_class: int
    majority_baseline_accuracy: float


def build_models(random_state: int = RANDOM_STATE) -> dict[str, Any]:
    return {
        "Logistic Regression": Pipeline(
            steps=[
                ("scaler", StandardScaler()),
                (
                    "classifier",
                    LogisticRegression(max_iter=1000, random_state=random_state),
                ),
            ]
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=100,
            max_depth=5,
            random_state=random_state,
        ),
        "XGBoost": XGBClassifier(
            n_estimators=100,
            max_depth=3,
            learning_rate=0.05,
            objective="binary:logistic",
            eval_metric="logloss",
            random_state=random_state,
        ),
    }


def train_model(model: Any, train_df: pd.DataFrame) -> Any:
    validate_training_frame(train_df)
    model.fit(train_df[FEATURE_COLUMNS], train_df["target"])
    return model


def train_models(
    train_df: pd.DataFrame,
    random_state: int = RANDOM_STATE,
) -> dict[str, Any]:
    return {
        name: train_model(model, train_df)
        for name, model in build_models(random_state=random_state).items()
    }


def evaluate_model(model_name: str, model: Any, test_df: pd.DataFrame) -> ModelEvaluation:
    validate_training_frame(test_df)

    y_true = test_df["target"]
    y_pred = model.predict(test_df[FEATURE_COLUMNS])
    y_probability = predict_positive_probability(model, test_df)

    return ModelEvaluation(
        model=model_name,
        accuracy=accuracy_score(y_true, y_pred),
        balanced_accuracy=balanced_accuracy_score(y_true, y_pred),
        precision=precision_score(y_true, y_pred, zero_division=0),
        recall=recall_score(y_true, y_pred, zero_division=0),
        f1=f1_score(y_true, y_pred, zero_division=0),
        roc_auc=safe_roc_auc_score(y_true, y_probability),
        confusion_matrix=confusion_matrix(y_true, y_pred, labels=[0, 1]).tolist(),
    )


def compare_models(models: dict[str, Any], test_df: pd.DataFrame) -> pd.DataFrame:
    rows = [evaluate_model(name, model, test_df).__dict__ for name, model in models.items()]
    comparison = pd.DataFrame(rows)
    metric_columns = [
        "accuracy",
        "balanced_accuracy",
        "precision",
        "recall",
        "f1",
        "roc_auc",
    ]
    comparison[metric_columns] = comparison[metric_columns].round(4)
    return comparison.sort_values("roc_auc", ascending=False).reset_index(drop=True)


def evaluate_models_per_etf(models: dict[str, Any], test_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for symbol, group in test_df.groupby("symbol"):
        for model_name, model in models.items():
            evaluation = evaluate_model(model_name, model, group)
            rows.append(
                {
                    "symbol": symbol,
                    "model": model_name,
                    "accuracy": round(evaluation.accuracy, 4),
                    "f1": round(evaluation.f1, 4),
                }
            )
    return pd.DataFrame(rows).sort_values(["symbol", "model"]).reset_index(drop=True)


def majority_baseline_accuracy(train_df: pd.DataFrame, test_df: pd.DataFrame) -> MajorityBaseline:
    validate_training_frame(test_df)

    majority_class = int(test_df["target"].mode().iloc[0])
    baseline_predictions = np.full(shape=len(test_df), fill_value=majority_class)
    return MajorityBaseline(
        majority_class=majority_class,
        majority_baseline_accuracy=accuracy_score(test_df["target"], baseline_predictions),
    )


def predict_positive_probability(model: Any, df: pd.DataFrame) -> np.ndarray:
    probabilities = model.predict_proba(df[FEATURE_COLUMNS])[:, 1]
    return np.clip(probabilities, 0, 1)


def feature_importance_mapping(model_name: str, model: Any) -> pd.DataFrame:
    if model_name == "Logistic Regression":
        classifier = model.named_steps["classifier"]
        values = classifier.coef_[0]
        column_name = "coefficient"
    elif model_name in {"Random Forest", "XGBoost"}:
        values = model.feature_importances_
        column_name = "importance"
    else:
        raise MLDatasetError(f"Unsupported model for feature importance: {model_name}")

    importance = pd.DataFrame({"feature": FEATURE_COLUMNS, column_name: values})
    sort_column = column_name
    importance["abs_value"] = importance[sort_column].abs()
    return (
        importance.sort_values("abs_value", ascending=False)
        .drop(columns=["abs_value"])
        .reset_index(drop=True)
    )


def safe_roc_auc_score(y_true: pd.Series, y_probability: np.ndarray) -> float:
    if y_true.nunique() < 2:
        return float("nan")
    return roc_auc_score(y_true, y_probability)


def validate_training_frame(df: pd.DataFrame) -> None:
    required_columns = [*FEATURE_COLUMNS, "target"]
    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        raise MLDatasetError(f"Missing required columns: {missing_columns}")
    if df.empty:
        raise MLDatasetError("Training/evaluation data is empty.")
