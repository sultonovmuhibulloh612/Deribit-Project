import asyncio
import logging
import time
from app.client.deribit_client import DeribitClient, DeribitClientError
from app.config import settings
from worker.celery_app import celery_app
from app.repositories.price_repository import PriceRepository
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
logger = logging.getLogger(__name__)



async def _fetch_and_store_async() -> dict[str, float]:
    prices: dict[str, float] = {}
    
    async with DeribitClient() as client:
        for ticker in settings.tracked_tickers:
            try:
                price = await client.get_index_price(ticker)
                prices[ticker] = price
            except DeribitClientError as exc:
                logger.error("Failed to fetch price for %s: %s", ticker, exc)

    if prices:
        timestamp = int(time.time())
        engine = create_async_engine(settings.database_url)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        
        async with session_factory() as session:
            repo = PriceRepository(session)
            for ticker, price in prices.items():
                await repo.save(ticker=ticker, price=price, timestamp=timestamp)
            await repo.commit()
        
        await engine.dispose()

    return prices


@celery_app.task(name="worker.tasks.fetch_and_store_prices", bind=True, max_retries=3)
def fetch_and_store_prices(self) -> dict[str, float]:
    try:
        return asyncio.run(_fetch_and_store_async())
    except Exception as exc:
        logger.exception("Unexpected error during price fetch: %s", exc)
        raise self.retry(exc=exc, countdown=10)
    