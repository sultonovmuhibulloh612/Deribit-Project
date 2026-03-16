import aiohttp

from app.config import settings


class DeribitClientError(Exception):
    """Raised when Deribit API returns an error or an unexpected response."""


class DeribitClient:
    """
    Async client for the Deribit JSON-RPC 2.0 REST API.

    Uses aiohttp for non-blocking HTTP requests. The client is designed
    to be used as an async context manager so the underlying session is
    properly opened and closed:

        async with DeribitClient() as client:
            price = await client.get_index_price("btc_usd")
    """

    _REQUEST_ID_SEED = 1

    def __init__(self, base_url: str = settings.deribit_base_url) -> None:
        self._base_url = base_url
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> "DeribitClient":
        self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, *_) -> None:
        if self._session:
            await self._session.close()
            self._session = None

    async def get_index_price(self, index_name: str) -> float:
        """
        Fetch the current index price for the given currency pair.

        :param index_name: Index identifier, e.g. ``"btc_usd"`` or ``"eth_usd"``.
        :returns: Current index price as a float.
        :raises DeribitClientError: On API-level errors or unexpected response shape.
        """
        payload = self._build_request(
            method=settings.deribit_index_price_method,
            params={"index_name": index_name},
        )
        response_data = await self._post(payload)
        return self._extract_index_price(response_data)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_request(self, method: str, params: dict) -> dict:
        request_id = DeribitClient._REQUEST_ID_SEED
        DeribitClient._REQUEST_ID_SEED += 1
        return {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": request_id,
        }

    async def _post(self, payload: dict) -> dict:
        if self._session is None:
            raise RuntimeError("DeribitClient must be used as an async context manager.")

        url = f"{self._base_url}/{payload['method']}"
        async with self._session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as response:
            response.raise_for_status()
            return await response.json()

    @staticmethod
    def _extract_index_price(data: dict) -> float:
        if "error" in data:
            raise DeribitClientError(
                f"Deribit API error {data['error']['code']}: {data['error']['message']}"
            )
        try:
            return float(data["result"]["index_price"])
        except (KeyError, TypeError, ValueError) as exc:
            raise DeribitClientError(f"Unexpected response structure: {data}") from exc