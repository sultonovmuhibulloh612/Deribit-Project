from app.models import CurrencyPrice
from app.repositories.price_repository import PriceRepository
from app.schemas import CurrencyPriceRecord, LatestPriceResponse


class PriceService:
    def __init__(self, repository: PriceRepository) -> None:
        self._repository = repository

    async def store_price(self, ticker: str, price: float, timestamp: int) -> CurrencyPrice:
        return await self._repository.save(
            ticker=ticker.lower(),
            price=price,
            timestamp=timestamp,
        )

    async def get_all_prices(self, ticker: str) -> list[CurrencyPriceRecord]:
        records = await self._repository.get_all_by_ticker(ticker.lower())
        return [CurrencyPriceRecord.model_validate(r) for r in records]

    async def get_latest_price(self, ticker: str) -> LatestPriceResponse | None:
        record = await self._repository.get_latest_by_ticker(ticker.lower())
        if record is None:
            return None
        return LatestPriceResponse.model_validate(record)

    async def get_prices_in_range(
        self,
        ticker: str,
        from_timestamp: int,
        to_timestamp: int,
    ) -> list[CurrencyPriceRecord]:
        records = await self._repository.get_by_ticker_and_date_range(
            ticker=ticker.lower(),
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )
        return [CurrencyPriceRecord.model_validate(r) for r in records]