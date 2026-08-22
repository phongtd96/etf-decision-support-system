from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.etf import Etf
from app.models.price_history import PriceHistory
from app.services.analysis_service import SUPPORTED_ETF_SYMBOLS


class ETFNotFoundError(LookupError):
    pass


@dataclass(frozen=True)
class PriceHistoryPoint:
    date: date
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    volume: int | None


@dataclass(frozen=True)
class ETFPriceHistory:
    symbol: str
    prices: list[PriceHistoryPoint]


def get_etf_price_history(
    db_session: Session,
    symbol: str,
    days: int | None = None,
) -> ETFPriceHistory:
    requested_symbol = symbol.upper()
    if requested_symbol not in SUPPORTED_ETF_SYMBOLS:
        raise ETFNotFoundError(f"ETF not found: {requested_symbol}")

    etf = db_session.scalar(select(Etf).where(Etf.symbol == requested_symbol))
    if etf is None:
        raise ETFNotFoundError(f"ETF not found: {requested_symbol}")

    statement = (
        select(
            PriceHistory.date,
            PriceHistory.open,
            PriceHistory.high,
            PriceHistory.low,
            PriceHistory.close,
            PriceHistory.volume,
        )
        .where(PriceHistory.etf_id == etf.id)
        .order_by(PriceHistory.date.desc())
    )
    if days is not None:
        statement = statement.limit(days)

    rows = db_session.execute(statement).all()
    prices = [
        PriceHistoryPoint(
            date=row.date,
            open=_to_float_or_none(row.open),
            high=_to_float_or_none(row.high),
            low=_to_float_or_none(row.low),
            close=_to_float_or_none(row.close),
            volume=row.volume,
        )
        for row in reversed(rows)
    ]
    return ETFPriceHistory(symbol=requested_symbol, prices=prices)


def _to_float_or_none(value: object) -> float | None:
    if value is None:
        return None
    return float(value)
