from pydantic import BaseModel, ConfigDict


class CurrencyPriceRecord(BaseModel):
    id: int
    ticker: str
    price: float
    timestamp: int

    model_config = ConfigDict(from_attributes=True)


class LatestPriceResponse(BaseModel):
    ticker: str
    price: float
    timestamp: int

    model_config = ConfigDict(from_attributes=True)