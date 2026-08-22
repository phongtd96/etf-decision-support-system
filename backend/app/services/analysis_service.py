from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.etf import Etf
from app.models.price_history import PriceHistory
from app.models.technical_indicator import TechnicalIndicator

INDICATOR_COLUMNS = [
    "sma_20",
    "sma_50",
    "rsi_14",
    "macd",
    "macd_signal",
    "volatility_20",
]
SUPPORTED_ETF_SYMBOLS = [
    "E1VFVN30",
    "FUEVFVND",
    "FUEVN100",
    "FUEDCMID",
    "FUESSVFL",
]
TREND_WEIGHT = 30.0
RSI_WEIGHT = 25.0
MACD_WEIGHT = 25.0
VOLATILITY_WEIGHT = 20.0

BULLISH_THRESHOLD = 75.0
NEUTRAL_THRESHOLD = 50.0

MACD_EQUAL_TOLERANCE = 1e-6
LOW_VOLATILITY_THRESHOLD = 0.20
MODERATE_VOLATILITY_THRESHOLD = 0.35


class TechnicalIndicatorError(ValueError):
    pass


class TechnicalAnalysisNotFoundError(LookupError):
    pass


class TechnicalSignal(StrEnum):
    BULLISH = "BULLISH"
    NEUTRAL = "NEUTRAL"
    BEARISH = "BEARISH"


@dataclass(frozen=True)
class TechnicalIndicatorSaveStats:
    processed_rows: int


@dataclass(frozen=True)
class TechnicalScoreResult:
    technical_score: float
    technical_signal: TechnicalSignal
    reasons: list[str]


@dataclass(frozen=True)
class LatestTechnicalAnalysis:
    symbol: str
    date: date
    technical_score: float
    technical_signal: TechnicalSignal
    indicators: dict[str, float | None]
    reasons: list[str]


@dataclass(frozen=True)
class TechnicalRankingItem:
    rank: int
    symbol: str
    date: date
    technical_score: float
    technical_signal: TechnicalSignal


@dataclass(frozen=True)
class TechnicalRanking:
    as_of_date: date
    rankings: list[TechnicalRankingItem]


def load_price_history(db_session: Session, symbol: str) -> pd.DataFrame:
    statement = (
        select(
            PriceHistory.date,
            PriceHistory.close,
        )
        .join(Etf, Etf.id == PriceHistory.etf_id)
        .where(Etf.symbol == symbol)
        .order_by(PriceHistory.date.asc())
    )
    rows = db_session.execute(statement).all()
    return pd.DataFrame(rows, columns=["date", "close"])


def get_technical_ranking(
    db_session: Session,
    symbols: list[str] | None = None,
) -> TechnicalRanking:
    symbols_to_rank = symbols or SUPPORTED_ETF_SYMBOLS
    analyses: list[LatestTechnicalAnalysis] = []

    for symbol in symbols_to_rank:
        try:
            analyses.append(get_latest_technical_analysis(db_session, symbol))
        except TechnicalAnalysisNotFoundError:
            continue

    if not analyses:
        raise TechnicalAnalysisNotFoundError("No technical analysis data available.")

    sorted_analyses = sorted(
        analyses,
        key=lambda analysis: (-analysis.technical_score, analysis.symbol),
    )
    rankings = [
        TechnicalRankingItem(
            rank=index,
            symbol=analysis.symbol,
            date=analysis.date,
            technical_score=analysis.technical_score,
            technical_signal=analysis.technical_signal,
        )
        for index, analysis in enumerate(sorted_analyses, start=1)
    ]

    return TechnicalRanking(
        as_of_date=max(analysis.date for analysis in analyses),
        rankings=rankings,
    )


def get_latest_technical_analysis(
    db_session: Session,
    symbol: str,
) -> LatestTechnicalAnalysis:
    etf = db_session.scalar(select(Etf).where(Etf.symbol == symbol))
    if etf is None:
        raise TechnicalAnalysisNotFoundError(f"ETF not found: {symbol}")

    latest_indicator = db_session.scalar(
        select(TechnicalIndicator)
        .where(TechnicalIndicator.etf_id == etf.id)
        .order_by(TechnicalIndicator.date.desc())
        .limit(1)
    )
    if latest_indicator is None:
        raise TechnicalAnalysisNotFoundError(
            f"No technical indicator data found for ETF: {symbol}"
        )

    indicators = {
        column: _to_float_or_none(getattr(latest_indicator, column))
        for column in INDICATOR_COLUMNS
    }
    score = score_technical_indicators(**indicators)

    return LatestTechnicalAnalysis(
        symbol=etf.symbol,
        date=latest_indicator.date,
        technical_score=score.technical_score,
        technical_signal=score.technical_signal,
        indicators=indicators,
        reasons=score.reasons,
    )


def score_technical_indicators(
    sma_20: float | Decimal | None,
    sma_50: float | Decimal | None,
    rsi_14: float | Decimal | None,
    macd: float | Decimal | None,
    macd_signal: float | Decimal | None,
    volatility_20: float | Decimal | None,
) -> TechnicalScoreResult:
    reasons: list[str] = []
    score = 0.0

    sma_20_value = _to_float_or_none(sma_20)
    sma_50_value = _to_float_or_none(sma_50)
    if sma_20_value is None or sma_50_value is None:
        trend_score = TREND_WEIGHT / 2
        reasons.append("Trend is neutral because SMA20 or SMA50 is unavailable.")
    elif sma_20_value > sma_50_value:
        trend_score = TREND_WEIGHT
        reasons.append("Trend is bullish because SMA20 is above SMA50.")
    elif sma_20_value == sma_50_value:
        trend_score = TREND_WEIGHT / 2
        reasons.append("Trend is neutral because SMA20 equals SMA50.")
    else:
        trend_score = 0.0
        reasons.append("Trend is bearish because SMA20 is below SMA50.")
    score += trend_score

    rsi_value = _to_float_or_none(rsi_14)
    if rsi_value is None:
        rsi_score = RSI_WEIGHT / 2
        reasons.append("RSI momentum is neutral because RSI14 is unavailable.")
    elif 50 <= rsi_value <= 70:
        rsi_score = RSI_WEIGHT
        reasons.append("RSI momentum is positive because RSI14 is between 50 and 70.")
    elif 30 <= rsi_value < 50:
        rsi_score = 15.0
        reasons.append("RSI momentum is moderate because RSI14 is between 30 and 50.")
    elif rsi_value > 70:
        rsi_score = 10.0
        reasons.append("RSI score is reduced because RSI14 indicates overbought risk.")
    else:
        rsi_score = 8.0
        reasons.append("RSI score is low because RSI14 indicates oversold weakness.")
    score += rsi_score

    macd_value = _to_float_or_none(macd)
    macd_signal_value = _to_float_or_none(macd_signal)
    if macd_value is None or macd_signal_value is None:
        macd_score = MACD_WEIGHT / 2
        reasons.append("MACD momentum is neutral because MACD data is unavailable.")
    elif macd_value > macd_signal_value:
        macd_score = MACD_WEIGHT
        reasons.append("MACD confirms momentum because MACD is above its signal line.")
    elif abs(macd_value - macd_signal_value) <= MACD_EQUAL_TOLERANCE:
        macd_score = MACD_WEIGHT / 2
        reasons.append("MACD is neutral because MACD is approximately equal to its signal line.")
    else:
        macd_score = 0.0
        reasons.append("MACD does not confirm momentum because MACD is below its signal line.")
    score += macd_score

    volatility_value = _to_float_or_none(volatility_20)
    if volatility_value is None:
        volatility_score = VOLATILITY_WEIGHT / 2
        reasons.append("Risk is neutral because 20-day volatility is unavailable.")
    elif volatility_value <= LOW_VOLATILITY_THRESHOLD:
        volatility_score = VOLATILITY_WEIGHT
        reasons.append("Risk score is strong because 20-day volatility is low.")
    elif volatility_value <= MODERATE_VOLATILITY_THRESHOLD:
        volatility_score = VOLATILITY_WEIGHT / 2
        reasons.append("Risk score is moderate because 20-day volatility is moderate.")
    else:
        volatility_score = 0.0
        reasons.append("Risk score is low because 20-day volatility is elevated.")
    score += volatility_score

    technical_score = max(0.0, min(100.0, round(score, 2)))
    return TechnicalScoreResult(
        technical_score=technical_score,
        technical_signal=map_score_to_signal(technical_score),
        reasons=reasons,
    )


def map_score_to_signal(score: float) -> TechnicalSignal:
    if score >= BULLISH_THRESHOLD:
        return TechnicalSignal.BULLISH
    if score >= NEUTRAL_THRESHOLD:
        return TechnicalSignal.NEUTRAL
    return TechnicalSignal.BEARISH


def calculate_technical_indicators(price_df: pd.DataFrame) -> pd.DataFrame:
    normalized = normalize_price_history(price_df)
    close = normalized["close"]

    daily_return = close.pct_change()
    ema_12 = close.ewm(span=12, adjust=False).mean()
    ema_26 = close.ewm(span=26, adjust=False).mean()
    macd = ema_12 - ema_26

    indicators = pd.DataFrame(
        {
            "date": normalized["date"],
            "sma_20": close.rolling(window=20).mean(),
            "sma_50": close.rolling(window=50).mean(),
            "rsi_14": calculate_rsi(close, period=14),
            "macd": macd,
            "macd_signal": macd.ewm(span=9, adjust=False).mean(),
            "volatility_20": daily_return.rolling(window=20).std() * np.sqrt(252),
        }
    )
    return indicators


def normalize_price_history(price_df: pd.DataFrame) -> pd.DataFrame:
    required_columns = ["date", "close"]
    missing_columns = [column for column in required_columns if column not in price_df]
    if missing_columns:
        raise TechnicalIndicatorError(f"Missing required columns: {missing_columns}")

    normalized = price_df[required_columns].copy()
    normalized["date"] = pd.to_datetime(normalized["date"], errors="coerce").dt.date
    normalized["close"] = pd.to_numeric(normalized["close"], errors="coerce")
    normalized = normalized.sort_values("date").reset_index(drop=True)

    if normalized.empty:
        raise TechnicalIndicatorError("Price history is empty.")

    if normalized["date"].isna().any():
        bad_rows = normalized.loc[normalized["date"].isna()]
        raise TechnicalIndicatorError(f"Invalid dates found:\n{_format_rows(bad_rows)}")

    duplicate_date_mask = normalized["date"].duplicated(keep=False)
    if duplicate_date_mask.any():
        bad_rows = normalized.loc[duplicate_date_mask]
        raise TechnicalIndicatorError(
            f"Duplicate dates found:\n{_format_rows(bad_rows)}"
        )

    if normalized["close"].isna().any():
        bad_rows = normalized.loc[normalized["close"].isna()]
        raise TechnicalIndicatorError(
            f"Missing close prices found:\n{_format_rows(bad_rows)}"
        )

    return normalized


def calculate_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    price_change = close.diff()
    gain = price_change.clip(lower=0)
    loss = -price_change.clip(upper=0)

    average_gain = gain.rolling(window=period).mean()
    average_loss = loss.rolling(window=period).mean()
    relative_strength = average_gain / average_loss
    rsi = 100 - (100 / (1 + relative_strength))

    rsi = rsi.mask((average_loss == 0) & (average_gain > 0), 100)
    rsi = rsi.mask((average_loss == 0) & (average_gain == 0), 50)
    return rsi


def save_technical_indicators(
    db_session: Session,
    etf: Etf,
    indicators_df: pd.DataFrame,
) -> TechnicalIndicatorSaveStats:
    required_columns = ["date", *INDICATOR_COLUMNS]
    missing_columns = [
        column for column in required_columns if column not in indicators_df.columns
    ]
    if missing_columns:
        raise TechnicalIndicatorError(f"Missing required columns: {missing_columns}")

    if indicators_df.empty:
        raise TechnicalIndicatorError("Technical indicator data is empty.")

    rows = []
    for record in indicators_df.to_dict(orient="records"):
        row = {"etf_id": etf.id, "date": _to_date(record["date"])}
        for column in INDICATOR_COLUMNS:
            row[column] = _none_if_nan(record[column])
        rows.append(row)

    statement = insert(TechnicalIndicator).values(rows)
    update_columns = {
        column: getattr(statement.excluded, column) for column in INDICATOR_COLUMNS
    }
    statement = statement.on_conflict_do_update(
        index_elements=["etf_id", "date"],
        set_=update_columns,
    )

    db_session.execute(statement)
    return TechnicalIndicatorSaveStats(processed_rows=len(rows))


def _none_if_nan(value: Any) -> Any:
    if pd.isna(value):
        return None
    return value


def _to_float_or_none(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def _to_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    return pd.Timestamp(value).date()


def _format_rows(df: pd.DataFrame) -> str:
    return df.to_string(index=False)
