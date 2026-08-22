import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.schemas.data_update import MarketDataUpdateResponse
from app.services.market_data_update_service import (
    MarketDataUpdateError,
    update_market_data,
)

router = APIRouter()
logger = logging.getLogger(__name__)
PUBLIC_UPDATE_FAILURE_MESSAGE = "Market data update failed. Please try again later."


@router.post("/update", response_model=MarketDataUpdateResponse)
def update_market_data_endpoint(
    db_session: Session = Depends(get_db),
) -> MarketDataUpdateResponse:
    try:
        summary = update_market_data(db_session)
        db_session.commit()
    except MarketDataUpdateError as exc:
        db_session.rollback()
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        db_session.rollback()
        logger.exception("Unexpected market data update failure")
        raise HTTPException(
            status_code=502,
            detail=PUBLIC_UPDATE_FAILURE_MESSAGE,
        ) from exc

    return MarketDataUpdateResponse(
        status=summary.status,
        latest_date=summary.latest_date,
        processed_price_rows=summary.processed_price_rows,
        symbols_updated=summary.symbols_updated,
        indicators_recalculated=summary.indicators_recalculated,
        message=summary.message,
        details=[
            {
                "symbol": detail.symbol,
                "fetched_rows": detail.fetched_rows,
                "valid_rows": detail.valid_rows,
                "changed_rows": detail.changed_rows,
                "latest_date": detail.latest_date,
                "indicators_recalculated": detail.indicators_recalculated,
                "indicator_rows": detail.indicator_rows,
                "status": detail.status,
                "message": detail.message,
            }
            for detail in summary.details
        ],
    )
