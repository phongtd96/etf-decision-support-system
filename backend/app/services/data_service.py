from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import pandas as pd
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from vnstock import Quote

from app.models.etf import Etf
from app.models.price_history import PriceHistory

DATA_SOURCE = "VCI"
INTERVAL = "1D"
REQUIRED_PROVIDER_COLUMNS = ["time", "open", "high", "low", "close", "volume"]
PRICE_COLUMNS = ["open", "high", "low", "close", "volume"]


class PriceDataValidationError(ValueError):
    pass


@dataclass(frozen=True)
class PriceHistorySaveStats:
    processed_rows: int


def fetch_etf_history(
    symbol: str,
    start_date: str,
    end_date: str | None = None,
) -> pd.DataFrame:
    quote = Quote(source="vci", symbol=symbol)
    return quote.history(start=start_date, end=end_date, interval=INTERVAL)


def normalize_price_data(df: pd.DataFrame) -> pd.DataFrame:
    missing_columns = [
        column for column in REQUIRED_PROVIDER_COLUMNS if column not in df.columns
    ]
    if missing_columns:
        raise PriceDataValidationError(f"Missing required columns: {missing_columns}")

    normalized = df[REQUIRED_PROVIDER_COLUMNS].copy()
    normalized["date"] = pd.to_datetime(normalized["time"], errors="coerce").dt.date
    normalized = normalized.drop(columns=["time"])

    for column in PRICE_COLUMNS:
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")

    normalized["adjusted_close"] = None
    normalized["data_source"] = DATA_SOURCE

    normalized = normalized[
        [
            "date",
            "open",
            "high",
            "low",
            "close",
            "adjusted_close",
            "volume",
            "data_source",
        ]
    ]
    normalized = normalized.drop_duplicates()
    return normalized.sort_values("date").reset_index(drop=True)


def filter_price_date_range(
    df: pd.DataFrame,
    start_date: str | date,
    end_date: str | date | None = None,
) -> pd.DataFrame:
    filtered = df.copy()
    dates = pd.to_datetime(filtered["date"], errors="coerce")
    start = pd.Timestamp(start_date)

    date_mask = dates >= start
    if end_date is not None:
        end = pd.Timestamp(end_date)
        date_mask = date_mask & (dates <= end)

    filtered = filtered.loc[date_mask].copy()
    return filtered.sort_values("date").reset_index(drop=True)


def validate_price_data(df: pd.DataFrame) -> None:
    required_columns = [
        "date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "adjusted_close",
        "data_source",
    ]
    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        raise PriceDataValidationError(f"Missing required columns: {missing_columns}")

    if df.empty:
        raise PriceDataValidationError("Price data is empty.")

    missing_values = df[["open", "high", "low", "close", "volume"]].isna()
    if missing_values.any().any():
        bad_rows = df.loc[missing_values.any(axis=1)]
        raise PriceDataValidationError(
            f"Missing OHLCV values found:\n{_format_rows(bad_rows)}"
        )

    duplicate_date_mask = df["date"].duplicated(keep=False)
    if duplicate_date_mask.any():
        bad_rows = df.loc[duplicate_date_mask]
        raise PriceDataValidationError(
            f"Duplicate dates found:\n{_format_rows(bad_rows)}"
        )

    invalid_ohlc_mask = (
        (df["high"] < df["low"])
        | (df["open"] > df["high"])
        | (df["open"] < df["low"])
        | (df["close"] > df["high"])
        | (df["close"] < df["low"])
    )
    if invalid_ohlc_mask.any():
        bad_rows = df.loc[invalid_ohlc_mask]
        raise PriceDataValidationError(
            f"Invalid OHLC relationships found:\n{_format_rows(bad_rows)}"
        )

    negative_volume_mask = df["volume"] < 0
    if negative_volume_mask.any():
        bad_rows = df.loc[negative_volume_mask]
        raise PriceDataValidationError(
            f"Negative volume values found:\n{_format_rows(bad_rows)}"
        )

    dates = pd.to_datetime(df["date"], errors="coerce")
    if dates.isna().any():
        bad_rows = df.loc[dates.isna()]
        raise PriceDataValidationError(f"Invalid dates found:\n{_format_rows(bad_rows)}")

    if not dates.is_monotonic_increasing:
        raise PriceDataValidationError("Dates must be monotonic ascending.")


def save_price_history(
    db_session: Session,
    etf: Etf,
    df: pd.DataFrame,
    data_source: str = DATA_SOURCE,
) -> PriceHistorySaveStats:
    validate_price_data(df)

    rows = []
    for record in df.to_dict(orient="records"):
        rows.append(
            {
                "etf_id": etf.id,
                "date": _to_date(record["date"]),
                "open": record["open"],
                "high": record["high"],
                "low": record["low"],
                "close": record["close"],
                "adjusted_close": None,
                "volume": int(record["volume"]),
                "data_source": data_source,
            }
        )

    statement = insert(PriceHistory).values(rows)
    update_columns = {
        "open": statement.excluded.open,
        "high": statement.excluded.high,
        "low": statement.excluded.low,
        "close": statement.excluded.close,
        "adjusted_close": statement.excluded.adjusted_close,
        "volume": statement.excluded.volume,
        "data_source": statement.excluded.data_source,
    }
    statement = statement.on_conflict_do_update(
        index_elements=["etf_id", "date"],
        set_=update_columns,
    )

    db_session.execute(statement)
    return PriceHistorySaveStats(processed_rows=len(rows))


def _format_rows(df: pd.DataFrame) -> str:
    return df.to_string(index=False)


def _to_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    return pd.Timestamp(value).date()
