from datetime import date

from pydantic import BaseModel


class PriceHistoryPointResponse(BaseModel):
    date: date
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    volume: int | None


class ETFPriceHistoryResponse(BaseModel):
    symbol: str
    prices: list[PriceHistoryPointResponse]
