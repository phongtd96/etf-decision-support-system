from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.schemas.analysis import TechnicalAnalysisResponse
from app.services.analysis_service import (
    TechnicalAnalysisNotFoundError,
    get_latest_technical_analysis,
)

router = APIRouter()


@router.get("/{symbol}", response_model=TechnicalAnalysisResponse)
def get_technical_analysis(
    symbol: str,
    db_session: Session = Depends(get_db),
) -> TechnicalAnalysisResponse:
    try:
        analysis = get_latest_technical_analysis(db_session, symbol.upper())
    except TechnicalAnalysisNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return TechnicalAnalysisResponse(
        symbol=analysis.symbol,
        date=analysis.date,
        technical_score=analysis.technical_score,
        technical_signal=analysis.technical_signal.value,
        indicators=analysis.indicators,
        reasons=analysis.reasons,
    )
