from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.schemas.dss import CriterionDetail, DSSRankingItem, DSSRankingResponse
from app.services.dss_service import (
    DSSDataError,
    SMART_CRITERIA,
    SmartRanking,
    SmartRankingItem,
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
