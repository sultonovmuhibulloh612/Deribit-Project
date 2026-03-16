import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.schemas import CurrencyPriceRecord, LatestPriceResponse
from app.services.price_service import PriceService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_price_record(**kwargs) -> CurrencyPriceRecord:
    defaults = {"id": 1, "ticker": "btc_usd", "price": 50000.0, "timestamp": int(time.time())}
    return CurrencyPriceRecord(**{**defaults, **kwargs})


# ---------------------------------------------------------------------------
# PriceService unit tests (repository is mocked)
# ---------------------------------------------------------------------------

class TestPriceService:
    @pytest.fixture
    def mock_repo(self):
        return MagicMock()

    @pytest.fixture
    def service(self, mock_repo):
        return PriceService(repository=mock_repo)

    @pytest.mark.asyncio
    async def test_store_price_normalises_ticker_to_lowercase(self, service, mock_repo):
        mock_repo.save = AsyncMock(return_value=MagicMock())
        await service.store_price("BTC_USD", 50000.0, 1700000000)
        mock_repo.save.assert_called_once_with(
            ticker="btc_usd", price=50000.0, timestamp=1700000000
        )

    @pytest.mark.asyncio
    async def test_get_all_prices_returns_empty_list_when_no_data(self, service, mock_repo):
        mock_repo.get_all_by_ticker = AsyncMock(return_value=[])
        result = await service.get_all_prices("btc_usd")
        assert result == []

    @pytest.mark.asyncio
    async def test_get_latest_price_returns_none_when_no_data(self, service, mock_repo):
        mock_repo.get_latest_by_ticker = AsyncMock(return_value=None)
        result = await service.get_latest_price("btc_usd")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_prices_in_range_passes_correct_args(self, service, mock_repo):
        mock_repo.get_by_ticker_and_date_range = AsyncMock(return_value=[])
        await service.get_prices_in_range("eth_usd", 1000, 2000)
        mock_repo.get_by_ticker_and_date_range.assert_called_once_with(
            ticker="eth_usd", from_timestamp=1000, to_timestamp=2000
        )


# ---------------------------------------------------------------------------
# API route integration tests (service is mocked via DI override)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


def override_service(return_all=None, return_latest=None, return_range=None):
    """Build a mock PriceService and wire it through FastAPI dependency override."""
    mock_service = MagicMock(spec=PriceService)
    mock_service.get_all_prices = AsyncMock(return_value=return_all or [])
    mock_service.get_latest_price = AsyncMock(return_value=return_latest)
    mock_service.get_prices_in_range = AsyncMock(return_value=return_range or [])
    return mock_service


class TestPricesRouter:
    @pytest.mark.asyncio
    async def test_get_all_prices_returns_200(self, client):
        from app.api.routes.prices import get_price_service
        records = [make_price_record()]
        app.dependency_overrides[get_price_service] = lambda: override_service(return_all=records)

        response = await client.get("/api/v1/prices/all?ticker=btc_usd")
        assert response.status_code == 200
        assert len(response.json()) == 1
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_all_prices_requires_ticker(self, client):
        response = await client.get("/api/v1/prices/all")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_latest_price_returns_404_when_no_data(self, client):
        from app.api.routes.prices import get_price_service
        app.dependency_overrides[get_price_service] = lambda: override_service(return_latest=None)

        response = await client.get("/api/v1/prices/latest?ticker=btc_usd")
        assert response.status_code == 404
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_latest_price_returns_200_with_data(self, client):
        from app.api.routes.prices import get_price_service
        latest = LatestPriceResponse(ticker="btc_usd", price=50000.0, timestamp=1700000000)
        app.dependency_overrides[get_price_service] = lambda: override_service(return_latest=latest)

        response = await client.get("/api/v1/prices/latest?ticker=btc_usd")
        assert response.status_code == 200
        assert response.json()["price"] == 50000.0
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_prices_in_range_rejects_invalid_range(self, client):
        from app.api.routes.prices import get_price_service
        app.dependency_overrides[get_price_service] = lambda: override_service()

        response = await client.get(
            "/api/v1/prices/range?ticker=btc_usd&from_timestamp=2000&to_timestamp=1000"
        )
        assert response.status_code == 400
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_prices_in_range_returns_200(self, client):
        from app.api.routes.prices import get_price_service
        records = [make_price_record(timestamp=1500)]
        app.dependency_overrides[get_price_service] = lambda: override_service(return_range=records)

        response = await client.get(
            "/api/v1/prices/range?ticker=btc_usd&from_timestamp=1000&to_timestamp=2000"
        )
        assert response.status_code == 200
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# DeribitClient unit tests
# ---------------------------------------------------------------------------

class TestDeribitClient:
    @pytest.mark.asyncio
    async def test_get_index_price_parses_response_correctly(self):
        from app.client.deribit_client import DeribitClient

        fake_response = {"result": {"index_price": 42000.5}, "id": 1}

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_cm = AsyncMock()
            mock_cm.__aenter__.return_value.json = AsyncMock(return_value=fake_response)
            mock_cm.__aenter__.return_value.raise_for_status = MagicMock()
            mock_post.return_value = mock_cm

            async with DeribitClient() as deribit:
                price = await deribit.get_index_price("btc_usd")

        assert price == 42000.5

    @pytest.mark.asyncio
    async def test_get_index_price_raises_on_api_error(self):
        from app.client.deribit_client import DeribitClient, DeribitClientError

        error_response = {"error": {"code": 11050, "message": "bad_request"}, "id": 1}

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_cm = AsyncMock()
            mock_cm.__aenter__.return_value.json = AsyncMock(return_value=error_response)
            mock_cm.__aenter__.return_value.raise_for_status = MagicMock()
            mock_post.return_value = mock_cm

            async with DeribitClient() as deribit:
                with pytest.raises(DeribitClientError):
                    await deribit.get_index_price("btc_usd")