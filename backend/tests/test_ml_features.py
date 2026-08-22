from datetime import date, timedelta

import pandas as pd

from app.ml.features import (
    FEATURE_COLUMNS,
    build_ml_dataset,
    purged_chronological_split,
    validate_purged_split,
)


def synthetic_source_data(row_count: int = 12) -> pd.DataFrame:
    rows = []
    start = date(2022, 1, 1)

    for index in range(row_count):
        rows.append(
            {
                "symbol": "AAA",
                "date": start + timedelta(days=index),
                "close": 100 + index,
                "volume": 1000 + index * 10,
                "sma_20": 95 + index,
                "sma_50": 90 + index,
                "rsi_14": 55,
                "macd": 1.5,
                "macd_signal": 1.0,
                "volatility_20": 0.2,
            }
        )

    for index in range(row_count):
        rows.append(
            {
                "symbol": "BBB",
                "date": start + timedelta(days=index),
                "close": 200 - index,
                "volume": 2000 - index * 10,
                "sma_20": 205 - index,
                "sma_50": 210 - index,
                "rsi_14": 45,
                "macd": -1.5,
                "macd_signal": -1.0,
                "volatility_20": 0.25,
            }
        )

    return pd.DataFrame(rows)


def test_future_return_5d_calculation() -> None:
    dataset = build_ml_dataset(synthetic_source_data())
    first_aaa = dataset.loc[dataset["symbol"] == "AAA"].iloc[0]

    assert first_aaa["date"].date() == date(2022, 1, 2)
    assert first_aaa["future_return_5d"] == (106 / 101) - 1


def test_binary_target_generation() -> None:
    dataset = build_ml_dataset(synthetic_source_data())

    assert set(dataset.loc[dataset["symbol"] == "AAA", "target"]) == {1}
    assert set(dataset.loc[dataset["symbol"] == "BBB", "target"]) == {0}


def test_last_5_rows_do_not_receive_fake_targets() -> None:
    dataset = build_ml_dataset(synthetic_source_data())

    assert dataset["date"].max().date() == date(2022, 1, 7)
    assert date(2022, 1, 8) not in set(dataset["date"].dt.date)


def test_daily_return_calculated_within_etf() -> None:
    dataset = build_ml_dataset(synthetic_source_data())
    first_bbb = dataset.loc[dataset["symbol"] == "BBB"].iloc[0]

    assert first_bbb["daily_return"] == (199 / 200) - 1


def test_volume_change_calculated_within_etf() -> None:
    dataset = build_ml_dataset(synthetic_source_data())
    first_bbb = dataset.loc[dataset["symbol"] == "BBB"].iloc[0]

    assert first_bbb["volume_change"] == (1990 / 2000) - 1


def test_no_cross_etf_leakage() -> None:
    shuffled = synthetic_source_data().sample(frac=1, random_state=42)
    dataset = build_ml_dataset(shuffled)
    first_aaa = dataset.loc[dataset["symbol"] == "AAA"].iloc[0]
    first_bbb = dataset.loc[dataset["symbol"] == "BBB"].iloc[0]

    assert first_aaa["daily_return"] == (101 / 100) - 1
    assert first_bbb["daily_return"] == (199 / 200) - 1


def test_feature_columns_do_not_include_target_or_future_return() -> None:
    assert "future_return_5d" not in FEATURE_COLUMNS
    assert "target" not in FEATURE_COLUMNS
    assert "target_date" not in FEATURE_COLUMNS


def test_output_contains_no_missing_required_features() -> None:
    dataset = build_ml_dataset(synthetic_source_data())

    assert not dataset[FEATURE_COLUMNS].isna().any().any()


def test_chronological_ordering_is_preserved() -> None:
    dataset = build_ml_dataset(synthetic_source_data().sample(frac=1, random_state=11))

    for _, group in dataset.groupby("symbol"):
        assert group["date"].is_monotonic_increasing


def test_5_period_purge_behavior() -> None:
    dataset = build_ml_dataset(synthetic_source_data())

    train_df, test_df, purged_df = purged_chronological_split(
        dataset,
        test_start_date="2022-01-06",
        horizon=5,
    )

    assert set(purged_df.loc[purged_df["symbol"] == "AAA", "date"].dt.date) == {
        date(2022, 1, 2),
        date(2022, 1, 3),
        date(2022, 1, 4),
        date(2022, 1, 5),
    }
    assert train_df.empty
    assert test_df["date"].min().date() == date(2022, 1, 6)


def test_training_target_horizon_does_not_cross_test_start() -> None:
    dataset = build_ml_dataset(synthetic_source_data(row_count=20))
    train_df, test_df, _ = purged_chronological_split(
        dataset,
        test_start_date="2022-01-12",
        horizon=5,
    )

    validate_purged_split(train_df, test_df, test_start_date="2022-01-12")
    assert (train_df["target_date"] < pd.Timestamp("2022-01-12")).all()


def test_purge_operates_within_each_etf_correctly() -> None:
    dataset = build_ml_dataset(synthetic_source_data())

    _, _, purged_df = purged_chronological_split(
        dataset,
        test_start_date="2022-01-07",
        horizon=5,
    )

    purged_counts = purged_df.groupby("symbol").size().to_dict()
    assert purged_counts == {"AAA": 5, "BBB": 5}


def test_purged_split_has_no_train_test_overlap() -> None:
    dataset = build_ml_dataset(synthetic_source_data())

    train_df, test_df, _ = purged_chronological_split(
        dataset,
        test_start_date="2022-01-07",
        horizon=5,
    )

    train_keys = set(zip(train_df["symbol"], train_df["date"]))
    test_keys = set(zip(test_df["symbol"], test_df["date"]))
    assert train_keys.isdisjoint(test_keys)


def test_purged_split_preserves_chronological_ordering() -> None:
    dataset = build_ml_dataset(synthetic_source_data().sample(frac=1, random_state=19))

    train_df, test_df, purged_df = purged_chronological_split(
        dataset,
        test_start_date="2022-01-07",
        horizon=5,
    )

    for frame in [train_df, test_df, purged_df]:
        for _, group in frame.groupby("symbol"):
            assert group["date"].is_monotonic_increasing


def test_later_inception_etf_remains_valid_in_purged_split() -> None:
    base = synthetic_source_data()
    late_start = date(2022, 1, 4)
    late_rows = []
    for index in range(9):
        late_rows.append(
            {
                "symbol": "LATE",
                "date": late_start + timedelta(days=index),
                "close": 300 + index,
                "volume": 3000 + index * 10,
                "sma_20": 295 + index,
                "sma_50": 290 + index,
                "rsi_14": 52,
                "macd": 1.0,
                "macd_signal": 0.9,
                "volatility_20": 0.22,
            }
        )
    dataset = build_ml_dataset(pd.concat([base, pd.DataFrame(late_rows)]))

    train_df, test_df, _ = purged_chronological_split(
        dataset,
        test_start_date="2022-01-07",
        horizon=5,
    )

    assert "LATE" in set(test_df["symbol"])
    assert set(train_df["symbol"]).issubset({"AAA", "BBB", "LATE"})
    for frame in [train_df, test_df]:
        for _, group in frame.groupby("symbol"):
            assert group["date"].is_monotonic_increasing
