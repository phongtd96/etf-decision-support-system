from datetime import date

from pydantic import BaseModel


class TechnicalIndicatorValues(BaseModel):
    sma_20: float | None
    sma_50: float | None
    rsi_14: float | None
    macd: float | None
    macd_signal: float | None
    volatility_20: float | None


class TechnicalAnalysisResponse(BaseModel):
    symbol: str
    date: date
    technical_score: float
    technical_signal: str
    indicators: TechnicalIndicatorValues
    reasons: list[str]


class TechnicalRankingItem(BaseModel):
    rank: int
    symbol: str
    date: date
    technical_score: float
    technical_signal: str


class TechnicalRankingResponse(BaseModel):
    as_of_date: date
    rankings: list[TechnicalRankingItem]
