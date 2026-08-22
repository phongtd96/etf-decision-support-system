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


class SensitivityComparisonRow(BaseModel):
    symbol: str
    balanced_score: float
    balanced_rank: int
    growth_score: float
    growth_rank: int
    growth_rank_change: int
    risk_averse_score: float
    risk_averse_rank: int
    risk_averse_rank_change: int


class SensitivityStabilitySummary(BaseModel):
    top_etf_stable: bool
    max_absolute_rank_change: int
    growth_changed_count: int
    risk_averse_changed_count: int


class DSSSensitivityResponse(BaseModel):
    as_of_date: date
    profiles: dict[str, dict[str, float]]
    comparisons: list[SensitivityComparisonRow]
    stability_summary: SensitivityStabilitySummary
