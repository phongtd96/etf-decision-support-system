from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from app.services.analysis_service import (
    INDICATOR_COLUMNS,
    LatestTechnicalAnalysis,
    TechnicalIndicatorError,
    TechnicalAnalysisNotFoundError,
    TechnicalSignal,
    calculate_technical_indicators,
    get_latest_technical_analysis,
    get_technical_ranking,
    map_score_to_signal,
    normalize_price_history,
    save_technical_indicators,
    score_technical_indicators,
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


def test_bullish_sma_scoring() -> None:
    result = score_technical_indicators(
        sma_20=20,
        sma_50=10,
        rsi_14=60,
        macd=2,
        macd_signal=1,
        volatility_20=0.15,
    )

    assert result.technical_score == 100
    assert result.technical_signal == TechnicalSignal.BULLISH
    assert any("SMA20 is above SMA50" in reason for reason in result.reasons)


def test_bearish_sma_scoring() -> None:
    result = score_technical_indicators(
        sma_20=10,
        sma_50=20,
        rsi_14=60,
        macd=2,
        macd_signal=1,
        volatility_20=0.15,
    )

    assert result.technical_score == 70
    assert result.technical_signal == TechnicalSignal.NEUTRAL
    assert any("SMA20 is below SMA50" in reason for reason in result.reasons)


def test_rsi_scoring_ranges() -> None:
    strong = score_technical_indicators(20, 10, 60, 2, 1, 0.15)
    moderate = score_technical_indicators(20, 10, 40, 2, 1, 0.15)
    overbought = score_technical_indicators(20, 10, 75, 2, 1, 0.15)
    oversold = score_technical_indicators(20, 10, 25, 2, 1, 0.15)

    assert strong.technical_score > moderate.technical_score
    assert moderate.technical_score > overbought.technical_score
    assert overbought.technical_score > oversold.technical_score


def test_macd_scoring() -> None:
    bullish = score_technical_indicators(20, 10, 60, 2.0, 1.0, 0.15)
    neutral = score_technical_indicators(20, 10, 60, 1.0, 1.0, 0.15)
    bearish = score_technical_indicators(20, 10, 60, 0.5, 1.0, 0.15)

    assert bullish.technical_score > neutral.technical_score
    assert neutral.technical_score > bearish.technical_score


def test_volatility_scoring() -> None:
    low = score_technical_indicators(20, 10, 60, 2, 1, 0.15)
    moderate = score_technical_indicators(20, 10, 60, 2, 1, 0.25)
    high = score_technical_indicators(20, 10, 60, 2, 1, 0.45)

    assert low.technical_score > moderate.technical_score
    assert moderate.technical_score > high.technical_score


def test_final_score_remains_within_0_to_100() -> None:
    result = score_technical_indicators(
        sma_20=None,
        sma_50=None,
        rsi_14=None,
        macd=None,
        macd_signal=None,
        volatility_20=None,
    )

    assert 0 <= result.technical_score <= 100


def test_signal_mapping_thresholds() -> None:
    assert map_score_to_signal(75) == TechnicalSignal.BULLISH
    assert map_score_to_signal(74.99) == TechnicalSignal.NEUTRAL
    assert map_score_to_signal(50) == TechnicalSignal.NEUTRAL
    assert map_score_to_signal(49.99) == TechnicalSignal.BEARISH


def test_missing_indicator_handling() -> None:
    class FakeSession:
        def __init__(self) -> None:
            self.calls = 0

        def scalar(self, statement):
            self.calls += 1
            if self.calls == 1:
                return type("FakeEtf", (), {"id": 1, "symbol": "E1VFVN30"})()
            return None

    with pytest.raises(TechnicalAnalysisNotFoundError, match="No technical indicator"):
        get_latest_technical_analysis(FakeSession(), "E1VFVN30")


def latest_analysis(
    symbol: str,
    score: float,
    analysis_date: date = date(2026, 8, 21),
) -> LatestTechnicalAnalysis:
    return LatestTechnicalAnalysis(
        symbol=symbol,
        date=analysis_date,
        technical_score=score,
        technical_signal=map_score_to_signal(score),
        indicators={
            "sma_20": 20.0,
            "sma_50": 18.0,
            "rsi_14": 60.0,
            "macd": 1.2,
            "macd_signal": 0.8,
            "volatility_20": 0.18,
        },
        reasons=[],
    )


def test_ranking_sorted_by_score_descending(monkeypatch) -> None:
    analyses = {
        "E1VFVN30": latest_analysis("E1VFVN30", 60),
        "FUEVFVND": latest_analysis("FUEVFVND", 90),
        "FUEVN100": latest_analysis("FUEVN100", 75),
    }

    monkeypatch.setattr(
        "app.services.analysis_service.get_latest_technical_analysis",
        lambda db_session, symbol: analyses[symbol],
    )

    ranking = get_technical_ranking(None, symbols=list(analyses))

    assert [item.symbol for item in ranking.rankings] == [
        "FUEVFVND",
        "FUEVN100",
        "E1VFVN30",
    ]


def test_equal_ranking_scores_sort_by_symbol(monkeypatch) -> None:
    analyses = {
        "FUEVFVND": latest_analysis("FUEVFVND", 70),
        "E1VFVN30": latest_analysis("E1VFVN30", 70),
        "FUEDCMID": latest_analysis("FUEDCMID", 70),
    }

    monkeypatch.setattr(
        "app.services.analysis_service.get_latest_technical_analysis",
        lambda db_session, symbol: analyses[symbol],
    )

    ranking = get_technical_ranking(None, symbols=list(analyses))

    assert [item.symbol for item in ranking.rankings] == [
        "E1VFVN30",
        "FUEDCMID",
        "FUEVFVND",
    ]


def test_ranking_ranks_begin_at_one(monkeypatch) -> None:
    analyses = {
        "E1VFVN30": latest_analysis("E1VFVN30", 80),
        "FUEVFVND": latest_analysis("FUEVFVND", 70),
    }

    monkeypatch.setattr(
        "app.services.analysis_service.get_latest_technical_analysis",
        lambda db_session, symbol: analyses[symbol],
    )

    ranking = get_technical_ranking(None, symbols=list(analyses))

    assert [item.rank for item in ranking.rankings] == [1, 2]


def test_ranking_skips_missing_etf_data(monkeypatch) -> None:
    analyses = {
        "E1VFVN30": latest_analysis("E1VFVN30", 80),
        "FUEVFVND": TechnicalAnalysisNotFoundError("missing"),
        "FUEVN100": latest_analysis("FUEVN100", 70),
    }

    def fake_latest(db_session, symbol: str):
        result = analyses[symbol]
        if isinstance(result, TechnicalAnalysisNotFoundError):
            raise result
        return result

    monkeypatch.setattr(
        "app.services.analysis_service.get_latest_technical_analysis",
        fake_latest,
    )

    ranking = get_technical_ranking(None, symbols=list(analyses))

    assert [item.symbol for item in ranking.rankings] == ["E1VFVN30", "FUEVN100"]
    assert ranking.as_of_date == date(2026, 8, 21)


def test_ranking_all_missing_data_raises_error(monkeypatch) -> None:
    def fake_latest(db_session, symbol: str):
        raise TechnicalAnalysisNotFoundError("missing")

    monkeypatch.setattr(
        "app.services.analysis_service.get_latest_technical_analysis",
        fake_latest,
    )

    with pytest.raises(TechnicalAnalysisNotFoundError, match="No technical analysis"):
        get_technical_ranking(None, symbols=["E1VFVN30", "FUEVFVND"])


def test_ranking_as_of_date_uses_max_latest_analysis_date(monkeypatch) -> None:
    analyses = {
        "E1VFVN30": latest_analysis("E1VFVN30", 80, date(2026, 8, 20)),
        "FUEVFVND": latest_analysis("FUEVFVND", 70, date(2026, 8, 21)),
    }

    monkeypatch.setattr(
        "app.services.analysis_service.get_latest_technical_analysis",
        lambda db_session, symbol: analyses[symbol],
    )

    ranking = get_technical_ranking(None, symbols=list(analyses))

    assert ranking.as_of_date == date(2026, 8, 21)
