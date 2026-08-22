from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.etf import Etf
from app.models.price_history import PriceHistory
from app.services.analysis_service import (
    SUPPORTED_ETF_SYMBOLS,
    calculate_technical_indicators,
    load_price_history,
    save_technical_indicators,
)
from app.services.data_service import (
    DATA_SOURCE,
    fetch_etf_history,
    filter_price_date_range,
    normalize_price_data,
    save_price_history,
    validate_price_data,
)

DEFAULT_START_DATE = "2022-01-01"


class MarketDataUpdateError(RuntimeError):
    pass


@dataclass(frozen=True)
class SymbolUpdateSummary:
    symbol: str
    fetched_rows: int
    valid_rows: int
    changed_rows: int
    latest_date: date | None
    indicators_recalculated: bool
    indicator_rows: int
    status: str
    message: str


@dataclass(frozen=True)
class MarketDataUpdateSummary:
    status: str
    latest_date: date | None
    processed_price_rows: int
    symbols_updated: list[str]
    indicators_recalculated: bool
    message: str
    details: list[SymbolUpdateSummary]


def update_market_data(
    db_session: Session,
    start_date: str = DEFAULT_START_DATE,
    symbols: list[str] | None = None,
) -> MarketDataUpdateSummary:
    symbols_to_update = symbols or SUPPORTED_ETF_SYMBOLS
    summaries: list[SymbolUpdateSummary] = []
    latest_stored_date = get_latest_stored_price_date(db_session)

    for symbol in symbols_to_update:
        summaries.append(update_symbol_market_data(db_session, symbol, start_date))

    updated_summaries = [summary for summary in summaries if summary.changed_rows > 0]
    latest_dates = [summary.latest_date for summary in summaries if summary.latest_date]
    latest_date = max(latest_dates) if latest_dates else latest_stored_date
    processed_price_rows = sum(summary.changed_rows for summary in summaries)

    if processed_price_rows == 0:
        return MarketDataUpdateSummary(
            status="already_up_to_date",
            latest_date=latest_date,
            processed_price_rows=0,
            symbols_updated=[],
            indicators_recalculated=False,
            message="Data is already up to date.",
            details=summaries,
        )

    return MarketDataUpdateSummary(
        status="updated",
        latest_date=latest_date,
        processed_price_rows=processed_price_rows,
        symbols_updated=[summary.symbol for summary in updated_summaries],
        indicators_recalculated=any(
            summary.indicators_recalculated for summary in updated_summaries
        ),
        message="Market data update completed successfully.",
        details=summaries,
    )


def update_symbol_market_data(
    db_session: Session,
    symbol: str,
    start_date: str = DEFAULT_START_DATE,
) -> SymbolUpdateSummary:
    etf = db_session.scalar(select(Etf).where(Etf.symbol == symbol))
    if etf is None:
        raise MarketDataUpdateError(f"ETF not found: {symbol}")

    fetch_start = get_symbol_fetch_start_date(db_session, etf, start_date)
    provider_df = fetch_etf_history(symbol=symbol, start_date=fetch_start.isoformat())
    normalized_df = normalize_price_data(provider_df)
    filtered_df = filter_price_date_range(normalized_df, start_date=fetch_start)
    if filtered_df.empty:
        return SymbolUpdateSummary(
            symbol=symbol,
            fetched_rows=len(provider_df),
            valid_rows=0,
            changed_rows=0,
            latest_date=None,
            indicators_recalculated=False,
            indicator_rows=0,
            status="already_up_to_date",
            message="No newer price records returned by data source.",
        )

    validate_price_data(filtered_df)

    changed_df = filter_changed_price_rows(db_session, etf, filtered_df)
    latest_date = max(filtered_df["date"]) if not filtered_df.empty else None
    if changed_df.empty:
        return SymbolUpdateSummary(
            symbol=symbol,
            fetched_rows=len(provider_df),
            valid_rows=len(filtered_df),
            changed_rows=0,
            latest_date=latest_date,
            indicators_recalculated=False,
            indicator_rows=0,
            status="already_up_to_date",
            message="No new or changed price records.",
        )

    save_stats = save_price_history(
        db_session=db_session,
        etf=etf,
        df=changed_df,
        data_source=DATA_SOURCE,
    )

    price_df = load_price_history(db_session, symbol)
    indicators_df = calculate_technical_indicators(price_df)
    indicator_stats = save_technical_indicators(db_session, etf, indicators_df)

    return SymbolUpdateSummary(
        symbol=symbol,
        fetched_rows=len(provider_df),
        valid_rows=len(filtered_df),
        changed_rows=save_stats.processed_rows,
        latest_date=latest_date,
        indicators_recalculated=True,
        indicator_rows=indicator_stats.processed_rows,
        status="updated",
        message="Price data changed; technical indicators recalculated.",
    )


def ingest_all_price_history(
    db_session: Session,
    start_date: str = DEFAULT_START_DATE,
    symbols: list[str] | None = None,
) -> list[SymbolUpdateSummary]:
    symbols_to_update = symbols or SUPPORTED_ETF_SYMBOLS
    summaries = []
    for symbol in symbols_to_update:
        etf = db_session.scalar(select(Etf).where(Etf.symbol == symbol))
        if etf is None:
            raise MarketDataUpdateError(f"ETF not found: {symbol}")

        provider_df = fetch_etf_history(symbol=symbol, start_date=start_date)
        normalized_df = normalize_price_data(provider_df)
        filtered_df = filter_price_date_range(normalized_df, start_date=start_date)
        validate_price_data(filtered_df)
        stats = save_price_history(
            db_session=db_session,
            etf=etf,
            df=filtered_df,
            data_source=DATA_SOURCE,
        )
        summaries.append(
            SymbolUpdateSummary(
                symbol=symbol,
                fetched_rows=len(provider_df),
                valid_rows=len(filtered_df),
                changed_rows=stats.processed_rows,
                latest_date=max(filtered_df["date"]) if not filtered_df.empty else None,
                indicators_recalculated=False,
                indicator_rows=0,
                status="updated",
                message="Historical price data ingested.",
            )
        )
    return summaries


def get_symbol_fetch_start_date(
    db_session: Session,
    etf: Etf,
    default_start_date: str,
) -> date:
    latest_date = db_session.scalar(
        select(PriceHistory.date)
        .where(PriceHistory.etf_id == etf.id)
        .order_by(PriceHistory.date.desc())
        .limit(1)
    )
    if latest_date is not None:
        return latest_date
    return pd.Timestamp(default_start_date).date()


def get_latest_stored_price_date(db_session: Session) -> date | None:
    return db_session.scalar(
        select(PriceHistory.date).order_by(PriceHistory.date.desc()).limit(1)
    )


def filter_changed_price_rows(
    db_session: Session,
    etf: Etf,
    df: pd.DataFrame,
) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    candidate_dates = [pd.Timestamp(value).date() for value in df["date"]]
    existing_rows = db_session.execute(
        select(
            PriceHistory.date,
            PriceHistory.open,
            PriceHistory.high,
            PriceHistory.low,
            PriceHistory.close,
            PriceHistory.volume,
            PriceHistory.data_source,
        )
        .where(
            PriceHistory.etf_id == etf.id,
            PriceHistory.date.in_(candidate_dates),
        )
    ).all()
    existing_by_date = {row.date: row for row in existing_rows}

    changed_records = []
    for record in df.to_dict(orient="records"):
        record_date = pd.Timestamp(record["date"]).date()
        existing = existing_by_date.get(record_date)
        if existing is None or _price_record_changed(record, existing):
            changed_records.append(record)

    return pd.DataFrame(changed_records, columns=df.columns)


def _price_record_changed(record: dict[str, object], existing: object) -> bool:
    return (
        _decimal_to_float(existing.open) != float(record["open"])
        or _decimal_to_float(existing.high) != float(record["high"])
        or _decimal_to_float(existing.low) != float(record["low"])
        or _decimal_to_float(existing.close) != float(record["close"])
        or int(existing.volume) != int(record["volume"])
        or existing.data_source != DATA_SOURCE
    )


def _decimal_to_float(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value)
