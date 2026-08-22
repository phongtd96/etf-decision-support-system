from datetime import date

import pandas as pd
import pytest

from app.services.data_service import (
    DATA_SOURCE,
    PriceDataValidationError,
    filter_price_date_range,
    normalize_price_data,
    save_price_history,
    validate_price_data,
)


def provider_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "time": "2022-01-05",
                "open": 11.0,
                "high": 12.0,
                "low": 10.5,
                "close": 11.5,
                "volume": 1000,
            },
            {
                "time": "2022-01-04",
                "open": 10.0,
                "high": 11.0,
                "low": 9.5,
                "close": 10.5,
                "volume": 900,
            },
        ]
    )


def provider_dataframe_with_out_of_range_dates() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "time": "2022-01-03",
                "open": 12.0,
                "high": 13.0,
                "low": 11.5,
                "close": 12.5,
                "volume": 1200,
            },
            {
                "time": "2021-12-31",
                "open": 9.0,
                "high": 10.0,
                "low": 8.5,
                "close": 9.5,
                "volume": 800,
            },
            {
                "time": "2022-01-01",
                "open": 10.0,
                "high": 11.0,
                "low": 9.5,
                "close": 10.5,
                "volume": 900,
            },
            {
                "time": "2022-01-02",
                "open": 11.0,
                "high": 12.0,
                "low": 10.5,
                "close": 11.5,
                "volume": 1000,
            },
            {
                "time": "2022-01-04",
                "open": 13.0,
                "high": 14.0,
                "low": 12.5,
                "close": 13.5,
                "volume": 1300,
            },
        ]
    )


def test_normalize_price_data() -> None:
    normalized = normalize_price_data(provider_dataframe())

    assert list(normalized.columns) == [
        "date",
        "open",
        "high",
        "low",
        "close",
        "adjusted_close",
        "volume",
        "data_source",
    ]
    assert normalized.loc[0, "date"] == date(2022, 1, 4)
    assert normalized.loc[1, "date"] == date(2022, 1, 5)
    assert normalized["adjusted_close"].isna().all()
    assert normalized["data_source"].eq(DATA_SOURCE).all()


def test_filter_price_date_range_removes_rows_before_start_date() -> None:
    normalized = normalize_price_data(provider_dataframe_with_out_of_range_dates())

    filtered = filter_price_date_range(normalized, start_date="2022-01-01")

    assert date(2021, 12, 31) not in set(filtered["date"])


def test_filter_price_date_range_retains_rows_equal_to_start_date() -> None:
    normalized = normalize_price_data(provider_dataframe_with_out_of_range_dates())

    filtered = filter_price_date_range(normalized, start_date="2022-01-01")

    assert date(2022, 1, 1) in set(filtered["date"])


def test_filter_price_date_range_removes_rows_after_end_date() -> None:
    normalized = normalize_price_data(provider_dataframe_with_out_of_range_dates())

    filtered = filter_price_date_range(
        normalized,
        start_date="2022-01-01",
        end_date="2022-01-03",
    )

    assert date(2022, 1, 4) not in set(filtered["date"])


def test_filter_price_date_range_retains_rows_equal_to_end_date() -> None:
    normalized = normalize_price_data(provider_dataframe_with_out_of_range_dates())

    filtered = filter_price_date_range(
        normalized,
        start_date="2022-01-01",
        end_date="2022-01-03",
    )

    assert date(2022, 1, 3) in set(filtered["date"])


def test_filter_price_date_range_keeps_later_inception_dates_valid() -> None:
    df = pd.DataFrame(
        [
            {
                "time": "2022-09-29",
                "open": 10.0,
                "high": 10.5,
                "low": 9.8,
                "close": 10.2,
                "volume": 1000,
            },
            {
                "time": "2022-09-30",
                "open": 10.2,
                "high": 10.6,
                "low": 10.0,
                "close": 10.4,
                "volume": 1100,
            },
        ]
    )
    normalized = normalize_price_data(df)

    filtered = filter_price_date_range(normalized, start_date="2022-01-01")

    assert list(filtered["date"]) == [date(2022, 9, 29), date(2022, 9, 30)]
    validate_price_data(filtered)


def test_filter_price_date_range_keeps_dates_sorted_ascending() -> None:
    normalized = normalize_price_data(provider_dataframe_with_out_of_range_dates())

    filtered = filter_price_date_range(
        normalized,
        start_date="2022-01-01",
        end_date="2022-01-03",
    )

    assert list(filtered["date"]) == [
        date(2022, 1, 1),
        date(2022, 1, 2),
        date(2022, 1, 3),
    ]


def test_valid_ohlcv_data_passes_validation() -> None:
    normalized = normalize_price_data(provider_dataframe())

    validate_price_data(normalized)


def test_invalid_ohlc_data_raises_exception() -> None:
    normalized = normalize_price_data(provider_dataframe())
    normalized.loc[0, "close"] = normalized.loc[0, "high"] + 1

    with pytest.raises(PriceDataValidationError, match="Invalid OHLC"):
        validate_price_data(normalized)


def test_negative_volume_raises_exception() -> None:
    normalized = normalize_price_data(provider_dataframe())
    normalized.loc[0, "volume"] = -1

    with pytest.raises(PriceDataValidationError, match="Negative volume"):
        validate_price_data(normalized)


def test_duplicate_dates_are_detected() -> None:
    normalized = normalize_price_data(provider_dataframe())
    normalized.loc[1, "date"] = normalized.loc[0, "date"]

    with pytest.raises(PriceDataValidationError, match="Duplicate dates"):
        validate_price_data(normalized)


def test_missing_ohlcv_values_raise_exception() -> None:
    normalized = normalize_price_data(provider_dataframe())
    normalized.loc[0, "open"] = None

    with pytest.raises(PriceDataValidationError, match="Missing OHLCV"):
        validate_price_data(normalized)


def test_save_price_history_uses_processed_rows_not_rowcount() -> None:
    class FakeResult:
        rowcount = -1

    class FakeSession:
        def __init__(self) -> None:
            self.executed = False

        def execute(self, statement: object) -> FakeResult:
            self.executed = True
            return FakeResult()

    class FakeEtf:
        id = 1

    normalized = normalize_price_data(provider_dataframe())
    db_session = FakeSession()

    stats = save_price_history(db_session, FakeEtf(), normalized)

    assert db_session.executed is True
    assert stats.processed_rows == 2
