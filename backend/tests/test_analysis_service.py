from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from app.services.analysis_service import (
    INDICATOR_COLUMNS,
    TechnicalIndicatorError,
    calculate_technical_indicators,
    normalize_price_history,
    save_technical_indicators,
)


def synthetic_price_history(row_count: int = 60) -> pd.DataFrame:
    start_date = date(2022, 1, 1)
    return pd.DataFrame(
        {
            "date": [start_date + timedelta(days=index) for index in range(row_count)],
            "close": [100 + index for index in range(row_count)],
        }
    )


def test_sma20_calculation() -> None:
    indicators = calculate_technical_indicators(synthetic_price_history())

    assert indicators.loc[18, "sma_20"] is np.nan or pd.isna(
        indicators.loc[18, "sma_20"]
    )
    assert indicators.loc[19, "sma_20"] == pytest.approx(
        sum(range(100, 120)) / 20
    )


def test_sma50_calculation() -> None:
    indicators = calculate_technical_indicators(synthetic_price_history())

    assert pd.isna(indicators.loc[48, "sma_50"])
    assert indicators.loc[49, "sma_50"] == pytest.approx(
        sum(range(100, 150)) / 50
    )


def test_rsi_values_remain_in_range_when_defined() -> None:
    indicators = calculate_technical_indicators(synthetic_price_history())
    defined_rsi = indicators["rsi_14"].dropna()

    assert not defined_rsi.empty
    assert defined_rsi.between(0, 100).all()


def test_macd_calculation_returns_expected_structure() -> None:
    indicators = calculate_technical_indicators(synthetic_price_history())

    assert list(indicators.columns) == ["date", *INDICATOR_COLUMNS]
    assert "macd" in indicators
    assert "macd_signal" in indicators
    assert len(indicators) == 60


def test_volatility20_is_non_negative_when_defined() -> None:
    indicators = calculate_technical_indicators(synthetic_price_history())
    defined_volatility = indicators["volatility_20"].dropna()

    assert not defined_volatility.empty
    assert (defined_volatility >= 0).all()


def test_input_rows_are_sorted_ascending_before_calculation() -> None:
    price_df = synthetic_price_history().sample(frac=1, random_state=7)

    indicators = calculate_technical_indicators(price_df)

    assert indicators["date"].is_monotonic_increasing


def test_duplicate_dates_raise_clear_error() -> None:
    price_df = synthetic_price_history()
    price_df.loc[1, "date"] = price_df.loc[0, "date"]

    with pytest.raises(TechnicalIndicatorError, match="Duplicate dates"):
        calculate_technical_indicators(price_df)


def test_nan_values_are_preserved_for_insufficient_lookback_periods() -> None:
    indicators = calculate_technical_indicators(synthetic_price_history())

    assert pd.isna(indicators.loc[0, "sma_20"])
    assert pd.isna(indicators.loc[0, "sma_50"])
    assert pd.isna(indicators.loc[0, "rsi_14"])
    assert pd.isna(indicators.loc[0, "volatility_20"])


def test_nan_values_become_none_before_database_upsert() -> None:
    class FakeSession:
        def __init__(self) -> None:
            self.statement = None

        def execute(self, statement: object) -> None:
            self.statement = statement

    class FakeEtf:
        id = 1

    indicators = calculate_technical_indicators(synthetic_price_history(2))
    db_session = FakeSession()

    stats = save_technical_indicators(db_session, FakeEtf(), indicators)
    params = db_session.statement.compile().params

    assert stats.processed_rows == 2
    assert params["sma_20_m0"] is None
    assert params["sma_50_m0"] is None
    assert params["rsi_14_m0"] is None
    assert params["volatility_20_m0"] is None


def test_processed_row_count_is_never_negative() -> None:
    class FakeSession:
        def execute(self, statement: object) -> None:
            return None

    class FakeEtf:
        id = 1

    indicators = calculate_technical_indicators(synthetic_price_history(5))

    stats = save_technical_indicators(FakeSession(), FakeEtf(), indicators)

    assert stats.processed_rows == 5
    assert stats.processed_rows >= 0


def test_normalize_price_history_requires_close_values() -> None:
    price_df = synthetic_price_history()
    price_df.loc[0, "close"] = None

    with pytest.raises(TechnicalIndicatorError, match="Missing close"):
        normalize_price_history(price_df)
