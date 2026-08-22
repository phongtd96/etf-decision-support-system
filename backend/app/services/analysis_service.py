from __future__ import annotations

from dataclasses import dataclass
from datetime import date
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


class TechnicalIndicatorError(ValueError):
    pass


@dataclass(frozen=True)
class TechnicalIndicatorSaveStats:
    processed_rows: int


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


def _to_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    return pd.Timestamp(value).date()


def _format_rows(df: pd.DataFrame) -> str:
    return df.to_string(index=False)
