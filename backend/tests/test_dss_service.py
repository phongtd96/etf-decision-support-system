from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from app.services.dss_service import (
    CriterionType,
    DSSDataError,
    SMART_CRITERIA,
    SmartAlternative,
    calculate_average_volume_20d,
    calculate_max_drawdown_60d,
    calculate_return_20d,
    calculate_smart_ranking,
    calculate_smart_ranking_from_database,
    calculate_technical_momentum_score,
    calculate_volatility_20d,
    normalize_criterion_values,
)


def price_frame(row_count: int = 80) -> pd.DataFrame:
    start = date(2022, 1, 1)
    return pd.DataFrame(
        {
            "date": [start + timedelta(days=index) for index in range(row_count)],
            "close": [100 + index for index in range(row_count)],
            "volume": [1000 + index * 10 for index in range(row_count)],
        }
    )


def test_benefit_normalization() -> None:
    utilities = normalize_criterion_values([10, 20, 30], CriterionType.BENEFIT)

    assert utilities == [0.0, 0.5, 1.0]


def test_cost_normalization() -> None:
    utilities = normalize_criterion_values([10, 20, 30], CriterionType.COST)

    assert utilities == [1.0, 0.5, 0.0]


def test_max_equals_min_normalization_returns_half() -> None:
    utilities = normalize_criterion_values([5, 5, 5], CriterionType.BENEFIT)

    assert utilities == [0.5, 0.5, 0.5]


def test_utilities_stay_within_zero_and_one() -> None:
    utilities = normalize_criterion_values([-100, 0, 100], CriterionType.BENEFIT)

    assert all(0 <= utility <= 1 for utility in utilities)


def test_smart_weights_sum_to_one() -> None:
    assert sum(criterion.weight for criterion in SMART_CRITERIA) == pytest.approx(1.0)


def test_smart_score_stays_within_zero_and_100() -> None:
    ranking = calculate_smart_ranking(
        [
            SmartAlternative("AAA", date(2022, 1, 1), raw_values("AAA", 10)),
            SmartAlternative("BBB", date(2022, 1, 1), raw_values("BBB", 20)),
        ]
    )

    assert all(0 <= item.smart_score <= 100 for item in ranking.rankings)


def test_technical_momentum_excludes_volatility() -> None:
    score = calculate_technical_momentum_score(
        sma_20=20,
        sma_50=10,
        rsi_14=60,
        macd=2,
        macd_signal=1,
    )

    assert score == 100


def test_return20_calculation() -> None:
    result = calculate_return_20d(price_frame(25))

    assert result == pytest.approx((124 / 104) - 1)


def test_volatility20_calculation() -> None:
    prices = price_frame(25)
    expected = prices["close"].pct_change().tail(20).std() * np.sqrt(252)

    assert calculate_volatility_20d(prices) == pytest.approx(expected)


def test_mdd60_calculation() -> None:
    prices = price_frame(60)
    prices["close"] = [100, 110, 120, *([90] * 57)]

    assert calculate_max_drawdown_60d(prices) == pytest.approx(0.25)


def test_average_volume20_calculation() -> None:
    prices = price_frame(25)

    assert calculate_average_volume_20d(prices) == pytest.approx(
        prices["volume"].tail(20).mean()
    )


def test_ranking_descending() -> None:
    ranking = calculate_smart_ranking(
        [
            SmartAlternative("AAA", date(2022, 1, 1), raw_values("AAA", 10)),
            SmartAlternative("BBB", date(2022, 1, 1), raw_values("BBB", 20)),
        ]
    )

    assert [item.symbol for item in ranking.rankings] == ["BBB", "AAA"]


def test_deterministic_symbol_tie_break() -> None:
    ranking = calculate_smart_ranking(
        [
            SmartAlternative("BBB", date(2022, 1, 1), raw_values("BBB", 10)),
            SmartAlternative("AAA", date(2022, 1, 1), raw_values("AAA", 10)),
        ]
    )

    assert [item.symbol for item in ranking.rankings] == ["AAA", "BBB"]


def test_missing_or_insufficient_historical_data_handling() -> None:
    with pytest.raises(DSSDataError, match="Return20 requires"):
        calculate_return_20d(price_frame(20))


def test_no_database_writes() -> None:
    class ReadOnlyFakeSession:
        def scalar(self, statement):
            return None

        def execute(self, statement):
            raise AssertionError("DSS service should not use execute for writes here.")

        def add(self, value):
            raise AssertionError("DSS service must not add database rows.")

        def commit(self):
            raise AssertionError("DSS service must not commit.")

    with pytest.raises(DSSDataError, match="No ETF alternatives"):
        calculate_smart_ranking_from_database(ReadOnlyFakeSession(), symbols=["AAA"])


def raw_values(symbol: str, base: float) -> dict[str, float]:
    return {
        "technical_momentum": base,
        "return_20d": base / 100,
        "volatility_20d": 1 / base,
        "max_drawdown_60d": 1 / base,
        "avg_volume_20d": base * 1000,
    }
