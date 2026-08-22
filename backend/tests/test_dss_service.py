from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from app.services.dss_service import (
    CriterionType,
    DSSDataError,
    SMART_CRITERIA,
    SMART_WEIGHT_PROFILES,
    SmartAlternative,
    SmartRanking,
    SmartRankingItem,
    calculate_average_volume_20d,
    calculate_max_drawdown_60d,
    calculate_return_20d,
    calculate_sensitivity_analysis_from_database,
    calculate_sensitivity_analysis_from_ranking,
    calculate_smart_ranking,
    calculate_smart_ranking_from_database,
    calculate_smart_ranking_from_utilities,
    calculate_technical_momentum_score,
    calculate_volatility_20d,
    normalize_criterion_values,
    validate_weight_profile,
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


def test_predefined_weight_profiles_sum_to_one() -> None:
    for weights in SMART_WEIGHT_PROFILES.values():
        assert sum(weights.values()) == pytest.approx(1.0)


def test_default_smart_weights_remain_unchanged() -> None:
    assert {criterion.name: criterion.weight for criterion in SMART_CRITERIA} == {
        "technical_momentum": 0.30,
        "return_20d": 0.25,
        "volatility_20d": 0.20,
        "max_drawdown_60d": 0.15,
        "avg_volume_20d": 0.10,
    }


def test_same_utilities_are_reused_across_scenarios() -> None:
    base_ranking = normalized_ranking()

    sensitivity = calculate_sensitivity_analysis_from_ranking(base_ranking)

    for scenario_ranking in sensitivity.scenario_rankings.values():
        for item in scenario_ranking.rankings:
            base_item = next(
                base_item
                for base_item in base_ranking.rankings
                if base_item.symbol == item.symbol
            )
            assert item.utilities == base_item.utilities


def test_scenario_score_calculation() -> None:
    base_ranking = normalized_ranking()

    ranking = calculate_smart_ranking_from_utilities(
        base_ranking,
        SMART_WEIGHT_PROFILES["GROWTH"],
    )

    aaa = next(item for item in ranking.rankings if item.symbol == "AAA")
    assert aaa.smart_score == pytest.approx(50.0)
    assert sum(aaa.weighted_contributions.values()) == pytest.approx(50.0)


def test_scenario_ranking_descending() -> None:
    ranking = calculate_smart_ranking_from_utilities(
        normalized_ranking(),
        SMART_WEIGHT_PROFILES["GROWTH"],
    )

    assert [item.symbol for item in ranking.rankings] == ["BBB", "AAA"]


def test_scenario_deterministic_tie_break() -> None:
    base_ranking = SmartRanking(
        as_of_date=date(2026, 8, 21),
        rankings=[
            utility_item("BBB", 1, 50.0, equal_utilities()),
            utility_item("AAA", 2, 50.0, equal_utilities()),
        ],
    )

    ranking = calculate_smart_ranking_from_utilities(
        base_ranking,
        SMART_WEIGHT_PROFILES["BALANCED"],
    )

    assert [item.symbol for item in ranking.rankings] == ["AAA", "BBB"]


def test_rank_change_calculation() -> None:
    sensitivity = calculate_sensitivity_analysis_from_ranking(normalized_ranking())
    comparison_by_symbol = {item.symbol: item for item in sensitivity.comparisons}

    assert comparison_by_symbol["AAA"].growth_rank_change == -1
    assert comparison_by_symbol["BBB"].growth_rank_change == 1
    assert comparison_by_symbol["AAA"].risk_averse_rank_change == 0


def test_invalid_weights_rejected() -> None:
    invalid_weights = dict(SMART_WEIGHT_PROFILES["BALANCED"])
    invalid_weights["return_20d"] = -0.10

    with pytest.raises(DSSDataError, match="non-negative"):
        validate_weight_profile(invalid_weights)


def test_sensitivity_analysis_no_database_writes(monkeypatch) -> None:
    class ReadOnlyFakeSession:
        def add(self, value):
            raise AssertionError("Sensitivity analysis must not add database rows.")

        def commit(self):
            raise AssertionError("Sensitivity analysis must not commit.")

    def fake_load_smart_alternatives(db_session, symbols=None, as_of_date=None):
        return [
            SmartAlternative("AAA", date(2026, 8, 21), raw_values("AAA", 10)),
            SmartAlternative("BBB", date(2026, 8, 21), raw_values("BBB", 20)),
        ]

    monkeypatch.setattr(
        "app.services.dss_service.load_smart_alternatives",
        fake_load_smart_alternatives,
    )

    sensitivity = calculate_sensitivity_analysis_from_database(ReadOnlyFakeSession())

    assert set(sensitivity.scenario_rankings) == {"BALANCED", "GROWTH", "RISK_AVERSE"}


def raw_values(symbol: str, base: float) -> dict[str, float]:
    return {
        "technical_momentum": base,
        "return_20d": base / 100,
        "volatility_20d": 1 / base,
        "max_drawdown_60d": 1 / base,
        "avg_volume_20d": base * 1000,
    }


def normalized_ranking() -> SmartRanking:
    return SmartRanking(
        as_of_date=date(2026, 8, 21),
        rankings=[
            utility_item(
                symbol="AAA",
                rank=1,
                smart_score=60.0,
                utilities={
                    "technical_momentum": 0.5,
                    "return_20d": 0.5,
                    "volatility_20d": 0.5,
                    "max_drawdown_60d": 0.5,
                    "avg_volume_20d": 0.5,
                },
            ),
            utility_item(
                symbol="BBB",
                rank=2,
                smart_score=50.0,
                utilities={
                    "technical_momentum": 0.5,
                    "return_20d": 0.7,
                    "volatility_20d": 0.0,
                    "max_drawdown_60d": 0.6,
                    "avg_volume_20d": 0.5,
                },
            ),
        ],
    )


def utility_item(
    symbol: str,
    rank: int,
    smart_score: float,
    utilities: dict[str, float],
) -> SmartRankingItem:
    return SmartRankingItem(
        rank=rank,
        symbol=symbol,
        date=date(2026, 8, 21),
        raw_values={criterion.name: utilities[criterion.name] for criterion in SMART_CRITERIA},
        utilities=utilities,
        weighted_contributions={
            criterion.name: utilities[criterion.name] * criterion.weight * 100
            for criterion in SMART_CRITERIA
        },
        smart_score=smart_score,
        reasons=["Deterministic test reason."],
    )


def equal_utilities() -> dict[str, float]:
    return {criterion.name: 0.5 for criterion in SMART_CRITERIA}
