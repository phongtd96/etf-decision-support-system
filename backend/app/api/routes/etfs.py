from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.schemas.etf import ETFPriceHistoryResponse
from app.services.etf_service import ETFNotFoundError, get_etf_price_history

router = APIRouter()


@router.get("/{symbol}/prices", response_model=ETFPriceHistoryResponse)
def get_prices(
    symbol: str,
    days: int | None = Query(default=None, gt=0, le=1500),
    db_session: Session = Depends(get_db),
) -> ETFPriceHistoryResponse:
    try:
        price_history = get_etf_price_history(db_session, symbol, days)
    except ETFNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return ETFPriceHistoryResponse(
        symbol=price_history.symbol,
        prices=[
            {
                "date": price.date,
                "open": price.open,
                "high": price.high,
                "low": price.low,
                "close": price.close,
                "volume": price.volume,
            }
            for price in price_history.prices
        ],
    )
