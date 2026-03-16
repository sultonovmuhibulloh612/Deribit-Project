from sqlalchemy import BigInteger, String, Numeric, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CurrencyPrice(Base):
    __tablename__ = "currency_prices"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    price: Mapped[float] = mapped_column(Numeric(precision=18, scale=8), nullable=False)
    timestamp: Mapped[int] = mapped_column(BigInteger, nullable=False)

    __table_args__ = (
        Index("ix_currency_prices_ticker_timestamp", "ticker", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<CurrencyPrice ticker={self.ticker} price={self.price} ts={self.timestamp}>"