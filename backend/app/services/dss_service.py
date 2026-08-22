from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.etf import Etf
from app.models.price_history import PriceHistory
from app.models.technical_indicator import TechnicalIndicator
from app.services.analysis_service import SUPPORTED_ETF_SYMBOLS


class CriterionType(StrEnum):
    BENEFIT = "BENEFIT"
    COST = "COST"


@dataclass(frozen=True)
class SmartCriterion:
    name: str
    weight: float
    criterion_type: CriterionType


@dataclass(frozen=True)
class SmartAlternative:
    symbol: str
    date: date
    raw_values: dict[str, float]


@dataclass(frozen=True)
class SmartRankingItem:
    rank: int
    symbol: str
    date: date
    raw_values: dict[str, float]
    utilities: dict[str, float]
    weighted_contributions: dict[str, float]
    smart_score: float
    reasons: list[str]


@dataclass(frozen=True)
class SmartRanking:
    as_of_date: date
    rankings: list[SmartRankingItem]


@dataclass(frozen=True)
class SensitivityComparisonItem:
    symbol: str
    balanced_score: float
    balanced_rank: int
    growth_score: float
    growth_rank: int
    risk_averse_score: float
    risk_averse_rank: int
    growth_rank_change: int
    risk_averse_rank_change: int


@dataclass(frozen=True)
class SensitivityStabilitySummary:
    top_etf_stable: bool
    max_absolute_rank_change: int
    growth_changed_count: int
    risk_averse_changed_count: int


@dataclass(frozen=True)
class SmartSensitivityAnalysis:
    as_of_date: date
    scenario_rankings: dict[str, SmartRanking]
    comparisons: list[SensitivityComparisonItem]
    stability_summary: SensitivityStabilitySummary


class DSSDataError(ValueError):
    pass


TECHNICAL_MOMENTUM_WEIGHTS = {
    "trend": 0.35,
    "rsi": 0.30,
    "macd": 0.35,
}

SMART_CRITERIA = [
    SmartCriterion("technical_momentum", 0.30, CriterionType.BENEFIT),
    SmartCriterion("return_20d", 0.25, CriterionType.BENEFIT),
    SmartCriterion("volatility_20d", 0.20, CriterionType.COST),
    SmartCriterion("max_drawdown_60d", 0.15, CriterionType.COST),
    SmartCriterion("avg_volume_20d", 0.10, CriterionType.BENEFIT),
]

SMART_WEIGHT_PROFILES = {
    "BALANCED": {
        "technical_momentum": 0.30,
        "return_20d": 0.25,
        "volatility_20d": 0.20,
        "max_drawdown_60d": 0.15,
        "avg_volume_20d": 0.10,
    },
    "GROWTH": {
        "technical_momentum": 0.35,
        "return_20d": 0.35,
        "volatility_20d": 0.10,
        "max_drawdown_60d": 0.10,
        "avg_volume_20d": 0.10,
    },
    "RISK_AVERSE": {
        "technical_momentum": 0.20,
        "return_20d": 0.15,
        "volatility_20d": 0.30,
        "max_drawdown_60d": 0.25,
        "avg_volume_20d": 0.10,
    },
}


def validate_smart_weights() -> None:
    total_weight = sum(criterion.weight for criterion in SMART_CRITERIA)
    if not np.isclose(total_weight, 1.0):
        raise DSSDataError(f"SMART weights must sum to 1.0, got {total_weight}.")


def calculate_technical_momentum_score(
    sma_20: float | Decimal | None,
    sma_50: float | Decimal | None,
    rsi_14: float | Decimal | None,
    macd: float | Decimal | None,
    macd_signal: float | Decimal | None,
) -> float:
    trend_score = _score_sma_trend(_to_float_or_none(sma_20), _to_float_or_none(sma_50))
    rsi_score = _score_rsi(_to_float_or_none(rsi_14))
    macd_score = _score_macd(_to_float_or_none(macd), _to_float_or_none(macd_signal))

    score = (
        trend_score * TECHNICAL_MOMENTUM_WEIGHTS["trend"]
        + rsi_score * TECHNICAL_MOMENTUM_WEIGHTS["rsi"]
        + macd_score * TECHNICAL_MOMENTUM_WEIGHTS["macd"]
    )
    return round(max(0.0, min(100.0, score)), 2)


def calculate_return_20d(price_df: pd.DataFrame) -> float:
    _require_observations(price_df, 21, "Return20")
    prices = _prepare_price_frame(price_df)
    return float(prices["close"].iloc[-1] / prices["close"].iloc[-21] - 1)


def calculate_volatility_20d(price_df: pd.DataFrame) -> float:
    _require_observations(price_df, 21, "Volatility20")
    prices = _prepare_price_frame(price_df)
    daily_returns = prices["close"].pct_change()
    return float(daily_returns.tail(20).std() * np.sqrt(252))


def calculate_max_drawdown_60d(price_df: pd.DataFrame) -> float:
    _require_observations(price_df, 60, "MDD60")
    prices = _prepare_price_frame(price_df).tail(60).copy()
    running_peak = prices["close"].cummax()
    drawdown = prices["close"] / running_peak - 1
    return float(abs(drawdown.min()))


def calculate_average_volume_20d(price_df: pd.DataFrame) -> float:
    _require_observations(price_df, 20, "AverageVolume20")
    prices = _prepare_price_frame(price_df)
    return float(prices["volume"].tail(20).mean())


def normalize_criterion_values(
    values: list[float],
    criterion_type: CriterionType,
) -> list[float]:
    if not values:
        return []

    min_value = min(values)
    max_value = max(values)
    if np.isclose(max_value, min_value):
        return [0.5 for _ in values]

    utilities = []
    for value in values:
        if criterion_type == CriterionType.BENEFIT:
            utility = (value - min_value) / (max_value - min_value)
        else:
            utility = (max_value - value) / (max_value - min_value)
        utilities.append(float(max(0.0, min(1.0, utility))))
    return utilities


def calculate_smart_ranking(alternatives: list[SmartAlternative]) -> SmartRanking:
    validate_smart_weights()
    if not alternatives:
        raise DSSDataError("No ETF alternatives available for SMART ranking.")

    utilities_by_symbol = {alternative.symbol: {} for alternative in alternatives}
    for criterion in SMART_CRITERIA:
        values = [alternative.raw_values[criterion.name] for alternative in alternatives]
        utilities = normalize_criterion_values(values, criterion.criterion_type)
        for alternative, utility in zip(alternatives, utilities, strict=True):
            utilities_by_symbol[alternative.symbol][criterion.name] = utility

    ranking_items = []
    for alternative in alternatives:
        utilities = utilities_by_symbol[alternative.symbol]
        contributions = {
            criterion.name: utilities[criterion.name] * criterion.weight * 100
            for criterion in SMART_CRITERIA
        }
        smart_score = round(sum(contributions.values()), 2)
        ranking_items.append(
            SmartRankingItem(
                rank=0,
                symbol=alternative.symbol,
                date=alternative.date,
                raw_values=alternative.raw_values,
                utilities=utilities,
                weighted_contributions=contributions,
                smart_score=max(0.0, min(100.0, smart_score)),
                reasons=build_dss_reasons(alternative.raw_values, utilities),
            )
        )

    sorted_items = sorted(ranking_items, key=lambda item: (-item.smart_score, item.symbol))
    ranked_items = [
        SmartRankingItem(
            rank=index,
            symbol=item.symbol,
            date=item.date,
            raw_values=item.raw_values,
            utilities=item.utilities,
            weighted_contributions=item.weighted_contributions,
            smart_score=item.smart_score,
            reasons=item.reasons,
        )
        for index, item in enumerate(sorted_items, start=1)
    ]

    return SmartRanking(
        as_of_date=max(alternative.date for alternative in alternatives),
        rankings=ranked_items,
    )


def validate_weight_profile(weights: dict[str, float]) -> None:
    required_criteria = {criterion.name for criterion in SMART_CRITERIA}
    provided_criteria = set(weights)
    missing_criteria = required_criteria - provided_criteria
    if missing_criteria:
        raise DSSDataError(f"Missing SMART weights for criteria: {sorted(missing_criteria)}")

    negative_criteria = [
        name for name in required_criteria if weights[name] < 0
    ]
    if negative_criteria:
        raise DSSDataError(
            f"SMART weights must be non-negative: {sorted(negative_criteria)}"
        )

    total_weight = sum(weights[name] for name in required_criteria)
    if not np.isclose(total_weight, 1.0):
        raise DSSDataError(f"SMART weights must sum to 1.0, got {total_weight}.")


def calculate_smart_ranking_from_utilities(
    base_ranking: SmartRanking,
    weights: dict[str, float],
) -> SmartRanking:
    validate_weight_profile(weights)
    if not base_ranking.rankings:
        raise DSSDataError("No ETF utilities available for SMART sensitivity analysis.")

    required_criteria = {criterion.name for criterion in SMART_CRITERIA}
    ranking_items = []
    for item in base_ranking.rankings:
        missing_utilities = required_criteria - set(item.utilities)
        if missing_utilities:
            raise DSSDataError(
                f"Missing SMART utilities for {item.symbol}: {sorted(missing_utilities)}"
            )

        contributions = {
            criterion.name: item.utilities[criterion.name] * weights[criterion.name] * 100
            for criterion in SMART_CRITERIA
        }
        smart_score = round(sum(contributions.values()), 2)
        ranking_items.append(
            SmartRankingItem(
                rank=0,
                symbol=item.symbol,
                date=item.date,
                raw_values=item.raw_values,
                utilities=item.utilities,
                weighted_contributions=contributions,
                smart_score=max(0.0, min(100.0, smart_score)),
                reasons=item.reasons,
            )
        )

    sorted_items = sorted(ranking_items, key=lambda item: (-item.smart_score, item.symbol))
    ranked_items = [
        SmartRankingItem(
            rank=index,
            symbol=item.symbol,
            date=item.date,
            raw_values=item.raw_values,
            utilities=item.utilities,
            weighted_contributions=item.weighted_contributions,
            smart_score=item.smart_score,
            reasons=item.reasons,
        )
        for index, item in enumerate(sorted_items, start=1)
    ]
    return SmartRanking(as_of_date=base_ranking.as_of_date, rankings=ranked_items)


def calculate_sensitivity_analysis_from_ranking(
    base_ranking: SmartRanking,
) -> SmartSensitivityAnalysis:
    scenario_rankings = {
        name: calculate_smart_ranking_from_utilities(base_ranking, weights)
        for name, weights in SMART_WEIGHT_PROFILES.items()
    }
    comparisons = build_sensitivity_comparisons(scenario_rankings)
    stability_summary = build_stability_summary(scenario_rankings, comparisons)
    return SmartSensitivityAnalysis(
        as_of_date=base_ranking.as_of_date,
        scenario_rankings=scenario_rankings,
        comparisons=comparisons,
        stability_summary=stability_summary,
    )


def build_sensitivity_comparisons(
    scenario_rankings: dict[str, SmartRanking],
) -> list[SensitivityComparisonItem]:
    required_scenarios = {"BALANCED", "GROWTH", "RISK_AVERSE"}
    missing_scenarios = required_scenarios - set(scenario_rankings)
    if missing_scenarios:
        raise DSSDataError(f"Missing SMART scenarios: {sorted(missing_scenarios)}")

    ranking_by_scenario = {
        name: {item.symbol: item for item in ranking.rankings}
        for name, ranking in scenario_rankings.items()
    }
    balanced_items = ranking_by_scenario["BALANCED"]
    comparisons = []
    for symbol in sorted(balanced_items):
        balanced_item = balanced_items[symbol]
        growth_item = ranking_by_scenario["GROWTH"][symbol]
        risk_averse_item = ranking_by_scenario["RISK_AVERSE"][symbol]
        comparisons.append(
            SensitivityComparisonItem(
                symbol=symbol,
                balanced_score=balanced_item.smart_score,
                balanced_rank=balanced_item.rank,
                growth_score=growth_item.smart_score,
                growth_rank=growth_item.rank,
                risk_averse_score=risk_averse_item.smart_score,
                risk_averse_rank=risk_averse_item.rank,
                growth_rank_change=balanced_item.rank - growth_item.rank,
                risk_averse_rank_change=balanced_item.rank - risk_averse_item.rank,
            )
        )
    return comparisons


def build_stability_summary(
    scenario_rankings: dict[str, SmartRanking],
    comparisons: list[SensitivityComparisonItem],
) -> SensitivityStabilitySummary:
    top_symbols = {
        ranking.rankings[0].symbol
        for ranking in scenario_rankings.values()
        if ranking.rankings
    }
    max_absolute_rank_change = max(
        (
            max(
                abs(item.growth_rank_change),
                abs(item.risk_averse_rank_change),
            )
            for item in comparisons
        ),
        default=0,
    )
    return SensitivityStabilitySummary(
        top_etf_stable=len(top_symbols) == 1,
        max_absolute_rank_change=max_absolute_rank_change,
        growth_changed_count=sum(
            1 for item in comparisons if item.growth_rank_change != 0
        ),
        risk_averse_changed_count=sum(
            1 for item in comparisons if item.risk_averse_rank_change != 0
        ),
    )


def build_dss_reasons(raw_values: dict[str, float], utilities: dict[str, float]) -> list[str]:
    reasons = []
    if utilities["technical_momentum"] >= 0.75:
        reasons.append("Strong technical momentum relative to other ETFs.")
    elif utilities["technical_momentum"] <= 0.25:
        reasons.append("Weak technical momentum relative to other ETFs.")

    if utilities["return_20d"] >= 0.75:
        reasons.append("Strong recent 20-day return.")
    elif utilities["return_20d"] <= 0.25:
        reasons.append("Weak recent 20-day return.")

    if utilities["volatility_20d"] >= 0.75:
        reasons.append("Relatively low 20-day volatility.")
    elif utilities["volatility_20d"] <= 0.25:
        reasons.append("Relatively high 20-day volatility.")

    if utilities["max_drawdown_60d"] >= 0.75:
        reasons.append("Relatively low 60-day drawdown risk.")
    elif utilities["max_drawdown_60d"] <= 0.25:
        reasons.append("Relatively high 60-day drawdown risk.")

    if utilities["avg_volume_20d"] >= 0.75:
        reasons.append("Relatively high recent trading volume.")
    elif utilities["avg_volume_20d"] <= 0.25:
        reasons.append("Relatively low recent trading volume.")

    if not reasons:
        reasons.append("Balanced SMART profile across the selected criteria.")
    return reasons


def load_smart_alternatives(
    db_session: Session,
    symbols: list[str] | None = None,
    as_of_date: date | None = None,
) -> list[SmartAlternative]:
    symbols_to_rank = symbols or SUPPORTED_ETF_SYMBOLS
    alternatives = []

    for symbol in symbols_to_rank:
        etf = db_session.scalar(select(Etf).where(Etf.symbol == symbol))
        if etf is None:
            continue

        price_df = load_price_data_for_etf(db_session, etf.id, as_of_date)
        if price_df.empty:
            continue

        latest_date = price_df["date"].max()
        indicator = db_session.scalar(
            select(TechnicalIndicator)
            .where(
                TechnicalIndicator.etf_id == etf.id,
                TechnicalIndicator.date <= latest_date,
            )
            .order_by(TechnicalIndicator.date.desc())
            .limit(1)
        )
        if indicator is None:
            continue

        try:
            alternatives.append(
                SmartAlternative(
                    symbol=etf.symbol,
                    date=latest_date,
                    raw_values={
                        "technical_momentum": calculate_technical_momentum_score(
                            indicator.sma_20,
                            indicator.sma_50,
                            indicator.rsi_14,
                            indicator.macd,
                            indicator.macd_signal,
                        ),
                        "return_20d": calculate_return_20d(price_df),
                        "volatility_20d": calculate_volatility_20d(price_df),
                        "max_drawdown_60d": calculate_max_drawdown_60d(price_df),
                        "avg_volume_20d": calculate_average_volume_20d(price_df),
                    },
                )
            )
        except DSSDataError:
            continue

    return alternatives


def calculate_smart_ranking_from_database(
    db_session: Session,
    symbols: list[str] | None = None,
    as_of_date: date | None = None,
) -> SmartRanking:
    alternatives = load_smart_alternatives(db_session, symbols, as_of_date)
    return calculate_smart_ranking(alternatives)


def calculate_sensitivity_analysis_from_database(
    db_session: Session,
    symbols: list[str] | None = None,
    as_of_date: date | None = None,
) -> SmartSensitivityAnalysis:
    base_ranking = calculate_smart_ranking_from_database(db_session, symbols, as_of_date)
    return calculate_sensitivity_analysis_from_ranking(base_ranking)


def load_price_data_for_etf(
    db_session: Session,
    etf_id: int,
    as_of_date: date | None = None,
) -> pd.DataFrame:
    conditions = [PriceHistory.etf_id == etf_id]
    if as_of_date is not None:
        conditions.append(PriceHistory.date <= as_of_date)

    statement = (
        select(PriceHistory.date, PriceHistory.close, PriceHistory.volume)
        .where(*conditions)
        .order_by(PriceHistory.date.asc())
    )
    rows = db_session.execute(statement).all()
    return pd.DataFrame(rows, columns=["date", "close", "volume"])


def _prepare_price_frame(price_df: pd.DataFrame) -> pd.DataFrame:
    required_columns = ["date", "close", "volume"]
    missing_columns = [column for column in required_columns if column not in price_df]
    if missing_columns:
        raise DSSDataError(f"Missing required price columns: {missing_columns}")

    prices = price_df[required_columns].copy()
    prices["date"] = pd.to_datetime(prices["date"], errors="coerce")
    prices["close"] = pd.to_numeric(prices["close"], errors="coerce")
    prices["volume"] = pd.to_numeric(prices["volume"], errors="coerce")
    prices = prices.sort_values("date").reset_index(drop=True)

    if prices[required_columns].isna().any().any():
        raise DSSDataError("Price data contains missing or invalid values.")
    return prices


def _require_observations(price_df: pd.DataFrame, required_count: int, label: str) -> None:
    if len(price_df) < required_count:
        raise DSSDataError(
            f"{label} requires at least {required_count} trading observations."
        )


def _score_sma_trend(sma_20: float | None, sma_50: float | None) -> float:
    if sma_20 is None or sma_50 is None:
        return 50.0
    if sma_20 > sma_50:
        return 100.0
    if sma_20 == sma_50:
        return 50.0
    return 0.0


def _score_rsi(rsi_14: float | None) -> float:
    if rsi_14 is None:
        return 50.0
    if 50 <= rsi_14 <= 70:
        return 100.0
    if 30 <= rsi_14 < 50:
        return 60.0
    if rsi_14 > 70:
        return 40.0
    return 30.0


def _score_macd(macd: float | None, macd_signal: float | None) -> float:
    if macd is None or macd_signal is None:
        return 50.0
    if macd > macd_signal:
        return 100.0
    if np.isclose(macd, macd_signal):
        return 50.0
    return 0.0


def _to_float_or_none(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)
