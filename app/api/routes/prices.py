from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.repositories.price_repository import PriceRepository
from app.schemas import CurrencyPriceRecord, LatestPriceResponse
from app.services.price_service import PriceService

router = APIRouter(prefix="/prices", tags=["prices"])


def get_price_service(session: AsyncSession = Depends(get_db_session)) -> PriceService:
    repository = PriceRepository(session)
    return PriceService(repository)


@router.get("/all", response_model=list[CurrencyPriceRecord])
async def get_all_prices(
    ticker: str = Query(..., description="Currency ticker, e.g. btc_usd"),
    service: PriceService = Depends(get_price_service),
) -> list[CurrencyPriceRecord]:
    """Return all stored price records for the given ticker."""
    return await service.get_all_prices(ticker)


@router.get("/latest", response_model=LatestPriceResponse)
async def get_latest_price(
    ticker: str = Query(..., description="Currency ticker, e.g. btc_usd"),
    service: PriceService = Depends(get_price_service),
) -> LatestPriceResponse:
    """Return the most recent price record for the given ticker."""
    result = await service.get_latest_price(ticker)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No data found for ticker '{ticker}'")
    return result


@router.get("/range", response_model=list[CurrencyPriceRecord])
async def get_prices_in_range(
    ticker: str = Query(..., description="Currency ticker, e.g. btc_usd"),
    from_timestamp: int = Query(..., description="Start of range as UNIX timestamp (seconds)"),
    to_timestamp: int = Query(..., description="End of range as UNIX timestamp (seconds)"),
    service: PriceService = Depends(get_price_service),
) -> list[CurrencyPriceRecord]:
    """Return price records for the given ticker within the specified UNIX timestamp range."""
    if from_timestamp > to_timestamp:
        raise HTTPException(
            status_code=400,
            detail="'from_timestamp' must be less than or equal to 'to_timestamp'",
        )
    return await service.get_prices_in_range(ticker, from_timestamp, to_timestamp)