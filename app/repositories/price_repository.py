from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CurrencyPrice


class PriceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, ticker: str, price: float, timestamp: int) -> None:
        record = CurrencyPrice(ticker=ticker, price=price, timestamp=timestamp)
        self._session.add(record)
    async def commit(self) -> None:
        await self._session.commit()

    async def get_all_by_ticker(self, ticker: str) -> list[CurrencyPrice]:
        result = await self._session.execute(
            select(CurrencyPrice)
            .where(CurrencyPrice.ticker == ticker)
            .order_by(desc(CurrencyPrice.timestamp))
        )
        return list(result.scalars().all())

    async def get_latest_by_ticker(self, ticker: str) -> CurrencyPrice | None:
        result = await self._session.execute(
            select(CurrencyPrice)
            .where(CurrencyPrice.ticker == ticker)
            .order_by(desc(CurrencyPrice.timestamp))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_ticker_and_date_range(
        self,
        ticker: str,
        from_timestamp: int,
        to_timestamp: int,
    ) -> list[CurrencyPrice]:
        result = await self._session.execute(
            select(CurrencyPrice)
            .where(
                CurrencyPrice.ticker == ticker,
                CurrencyPrice.timestamp >= from_timestamp,
                CurrencyPrice.timestamp <= to_timestamp,
            )
            .order_by(desc(CurrencyPrice.timestamp))
        )
        return list(result.scalars().all())