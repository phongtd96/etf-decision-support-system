from __future__ import annotations

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine


FEATURE_COLUMNS = [
    "daily_return",
    "volume_change",
    "close_to_sma20",
    "close_to_sma50",
    "rsi_14",
    "macd",
    "macd_signal",
    "volatility_20",
    "macd_histogram",
]

REQUIRED_SOURCE_COLUMNS = [
    "symbol",
    "date",
    "close",
    "volume",
    "sma_20",
    "sma_50",
    "rsi_14",
    "macd",
    "macd_signal",
    "volatility_20",
]


class MLDatasetError(ValueError):
    pass


def load_ml_source_data(engine: Engine) -> pd.DataFrame:
    query = text(
        """
        SELECT
            e.symbol,
            ph.date,
            ph.close,
            ph.volume,
            ti.sma_20,
            ti.sma_50,
            ti.rsi_14,
            ti.macd,
            ti.macd_signal,
            ti.volatility_20
        FROM price_history AS ph
        JOIN etfs AS e ON e.id = ph.etf_id
        JOIN technical_indicators AS ti
            ON ti.etf_id = ph.etf_id
            AND ti.date = ph.date
        ORDER BY e.symbol, ph.date
        """
    )

    with engine.connect() as connection:
        return pd.read_sql(query, connection)


def build_ml_dataset(source_df: pd.DataFrame, horizon_days: int = 5) -> pd.DataFrame:
    if horizon_days <= 0:
        raise MLDatasetError("horizon_days must be positive.")

    missing_columns = [
        column for column in REQUIRED_SOURCE_COLUMNS if column not in source_df.columns
    ]
    if missing_columns:
        raise MLDatasetError(f"Missing required columns: {missing_columns}")

    dataset = source_df[REQUIRED_SOURCE_COLUMNS].copy()
    dataset["date"] = pd.to_datetime(dataset["date"], errors="coerce")

    numeric_columns = [
        "close",
        "volume",
        "sma_20",
        "sma_50",
        "rsi_14",
        "macd",
        "macd_signal",
        "volatility_20",
    ]
    for column in numeric_columns:
        dataset[column] = pd.to_numeric(dataset[column], errors="coerce")

    if dataset["date"].isna().any():
        raise MLDatasetError("Invalid dates found in ML source data.")

    dataset = dataset.sort_values(["symbol", "date"]).reset_index(drop=True)

    grouped = dataset.groupby("symbol", group_keys=False)
    dataset["daily_return"] = grouped["close"].pct_change()
    dataset["volume_change"] = grouped["volume"].pct_change()
    dataset["close_to_sma20"] = dataset["close"] / dataset["sma_20"] - 1
    dataset["close_to_sma50"] = dataset["close"] / dataset["sma_50"] - 1
    dataset["macd_histogram"] = dataset["macd"] - dataset["macd_signal"]

    # Leakage safety:
    # Only future_close uses a negative shift, and it is used solely to create
    # future_return_5d and target. It is never included in FEATURE_COLUMNS.
    dataset["future_close"] = grouped["close"].shift(-horizon_days)
    dataset["target_date"] = grouped["date"].shift(-horizon_days)
    dataset["future_return_5d"] = dataset["future_close"] / dataset["close"] - 1
    dataset["target"] = (dataset["future_return_5d"] > 0).astype(int)

    dataset = dataset.drop(columns=["future_close"])

    output_columns = [
        "symbol",
        "date",
        *FEATURE_COLUMNS,
        "future_return_5d",
        "target",
        "target_date",
    ]
    dataset = dataset[output_columns]

    dataset = dataset.replace([np.inf, -np.inf], np.nan)
    dataset = dataset.dropna(subset=[*FEATURE_COLUMNS, "future_return_5d", "target"])
    dataset["target"] = dataset["target"].astype(int)

    return dataset.sort_values(["symbol", "date"]).reset_index(drop=True)


def purged_chronological_split(
    df: pd.DataFrame,
    test_start_date: str | pd.Timestamp,
    horizon: int = 5,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if horizon <= 0:
        raise MLDatasetError("horizon must be positive.")

    required_columns = ["symbol", "date", "target_date"]
    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        raise MLDatasetError(f"Missing required columns: {missing_columns}")

    dataset = df.copy()
    dataset["date"] = pd.to_datetime(dataset["date"], errors="coerce")
    dataset["target_date"] = pd.to_datetime(dataset["target_date"], errors="coerce")
    test_start = pd.Timestamp(test_start_date)

    if dataset[["date", "target_date"]].isna().any().any():
        raise MLDatasetError("Invalid dates found in ML dataset.")

    dataset = dataset.sort_values(["symbol", "date"]).reset_index(drop=True)

    # Purge safety:
    # Train rows must be before the test period, and their t+horizon target date
    # must also be before the test period. This removes boundary rows by trading
    # observation order, not by subtracting calendar days.
    train_candidates = dataset.loc[dataset["date"] < test_start].copy()
    test_df = dataset.loc[dataset["date"] >= test_start].copy()
    purge_mask = train_candidates["target_date"] >= test_start
    purged_df = train_candidates.loc[purge_mask].copy()
    train_df = train_candidates.loc[~purge_mask].copy()

    return (
        train_df.sort_values(["symbol", "date"]).reset_index(drop=True),
        test_df.sort_values(["symbol", "date"]).reset_index(drop=True),
        purged_df.sort_values(["symbol", "date"]).reset_index(drop=True),
    )


def validate_purged_split(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    test_start_date: str | pd.Timestamp,
) -> None:
    if train_df.empty or test_df.empty:
        raise MLDatasetError("Train and test splits must both contain rows.")

    test_start = pd.Timestamp(test_start_date)
    train_dates = pd.to_datetime(train_df["date"])
    train_target_dates = pd.to_datetime(train_df["target_date"])
    test_dates = pd.to_datetime(test_df["date"])

    train_keys = set(zip(train_df["symbol"], train_dates))
    test_keys = set(zip(test_df["symbol"], test_dates))
    if train_keys & test_keys:
        raise MLDatasetError("Train and test splits contain overlapping rows.")

    if train_dates.max() >= test_dates.min():
        raise MLDatasetError("Train dates must end before test dates begin.")

    if (train_target_dates >= test_start).any():
        raise MLDatasetError("A train target horizon crosses into the test period.")

    for _, group in train_df.groupby("symbol"):
        if not group["date"].is_monotonic_increasing:
            raise MLDatasetError("Train rows are not chronologically sorted.")

    for _, group in test_df.groupby("symbol"):
        if not group["date"].is_monotonic_increasing:
            raise MLDatasetError("Test rows are not chronologically sorted.")
