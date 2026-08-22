from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.schemas.dss import (
    CriterionDetail,
    DSSRankingItem,
    DSSRankingResponse,
    DSSSensitivityResponse,
)
from app.services.dss_service import (
    DSSDataError,
    SMART_CRITERIA,
    SMART_WEIGHT_PROFILES,
    SmartRanking,
    SmartRankingItem,
    SmartSensitivityAnalysis,
    calculate_sensitivity_analysis_from_database,
    calculate_smart_ranking_from_database,
)

router = APIRouter()


@router.get("/ranking", response_model=DSSRankingResponse)
def get_dss_ranking(db_session: Session = Depends(get_db)) -> DSSRankingResponse:
    try:
        ranking = calculate_smart_ranking_from_database(db_session)
    except DSSDataError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return _build_ranking_response(ranking)


@router.get("/sensitivity", response_model=DSSSensitivityResponse)
def get_dss_sensitivity(
    db_session: Session = Depends(get_db),
) -> DSSSensitivityResponse:
    try:
        sensitivity = calculate_sensitivity_analysis_from_database(db_session)
    except DSSDataError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return _build_sensitivity_response(sensitivity)


@router.get("/{symbol}", response_model=DSSRankingItem)
def get_dss_detail(
    symbol: str,
    db_session: Session = Depends(get_db),
) -> DSSRankingItem:
    requested_symbol = symbol.upper()
    try:
        ranking = calculate_smart_ranking_from_database(db_session)
    except DSSDataError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    for item in ranking.rankings:
        if item.symbol == requested_symbol:
            return _build_ranking_item(item)

    raise HTTPException(
        status_code=404,
        detail=f"No DSS ranking data found for ETF symbol {requested_symbol}.",
    )


def _build_ranking_response(ranking: SmartRanking) -> DSSRankingResponse:
    return DSSRankingResponse(
        as_of_date=ranking.as_of_date,
        methodology="SMART",
        weights={criterion.name: criterion.weight for criterion in SMART_CRITERIA},
        rankings=[_build_ranking_item(item) for item in ranking.rankings],
    )


def _build_ranking_item(item: SmartRankingItem) -> DSSRankingItem:
    criteria_by_name = {criterion.name: criterion for criterion in SMART_CRITERIA}
    criteria = {
        name: CriterionDetail(
            raw_value=item.raw_values[name],
            utility=item.utilities[name],
            weight=criterion.weight,
            weighted_contribution=item.weighted_contributions[name],
            criterion_type=criterion.criterion_type.value,
        )
        for name, criterion in criteria_by_name.items()
    }
    return DSSRankingItem(
        rank=item.rank,
        symbol=item.symbol,
        smart_score=item.smart_score,
        criteria=criteria,
        reasons=item.reasons,
    )


def _build_sensitivity_response(
    sensitivity: SmartSensitivityAnalysis,
) -> DSSSensitivityResponse:
    return DSSSensitivityResponse(
        as_of_date=sensitivity.as_of_date,
        profiles=SMART_WEIGHT_PROFILES,
        comparisons=[
            {
                "symbol": item.symbol,
                "balanced_score": item.balanced_score,
                "balanced_rank": item.balanced_rank,
                "growth_score": item.growth_score,
                "growth_rank": item.growth_rank,
                "growth_rank_change": item.growth_rank_change,
                "risk_averse_score": item.risk_averse_score,
                "risk_averse_rank": item.risk_averse_rank,
                "risk_averse_rank_change": item.risk_averse_rank_change,
            }
            for item in sensitivity.comparisons
        ],
        stability_summary={
            "top_etf_stable": sensitivity.stability_summary.top_etf_stable,
            "max_absolute_rank_change": (
                sensitivity.stability_summary.max_absolute_rank_change
            ),
            "growth_changed_count": sensitivity.stability_summary.growth_changed_count,
            "risk_averse_changed_count": (
                sensitivity.stability_summary.risk_averse_changed_count
            ),
        },
    )
