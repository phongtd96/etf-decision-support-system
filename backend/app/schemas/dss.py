from datetime import date

from pydantic import BaseModel


class CriterionDetail(BaseModel):
    raw_value: float
    utility: float
    weight: float
    weighted_contribution: float
    criterion_type: str


class DSSRankingItem(BaseModel):
    rank: int
    symbol: str
    smart_score: float
    criteria: dict[str, CriterionDetail]
    reasons: list[str]


class DSSRankingResponse(BaseModel):
    as_of_date: date
    methodology: str
    weights: dict[str, float]
    rankings: list[DSSRankingItem]
