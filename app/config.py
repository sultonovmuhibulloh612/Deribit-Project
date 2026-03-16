from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/deribit"

    # Deribit
    deribit_base_url: str = "https://test.deribit.com/api/v2"
    deribit_index_price_method: str = "public/get_index_price"

    # Celery
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/0"
    price_fetch_interval_seconds: int = 60

    # Tickers to track
    tracked_tickers: list[str] = ["btc_usd", "eth_usd"]
    model_config = ConfigDict(env_file=".env")


settings = Settings()