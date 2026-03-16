from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.prices import router as prices_router
from app.database import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="Deribit Price Tracker",
    description="API for querying historical BTC/ETH index prices fetched from Deribit.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(prices_router, prefix="/api/v1")