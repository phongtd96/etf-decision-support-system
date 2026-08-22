from datetime import date

from pydantic import BaseModel


class SymbolUpdateSummaryResponse(BaseModel):
    symbol: str
    fetched_rows: int
    valid_rows: int
    changed_rows: int
    latest_date: date | None
    indicators_recalculated: bool
    indicator_rows: int
    status: str
    message: str


class MarketDataUpdateResponse(BaseModel):
    status: str
    latest_date: date | None
    processed_price_rows: int
    symbols_updated: list[str]
    indicators_recalculated: bool
    message: str
    details: list[SymbolUpdateSummaryResponse]
