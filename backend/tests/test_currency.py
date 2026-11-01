import pytest
import httpx
from app.config import Settings
from app.tools.currency import get_rate, resolve_currency_for_origin, APPROX_USD_RATES


def test_same_currency():
    assert asyncio_run(get_rate("USD", "USD")) == 1.0
    assert asyncio_run(get_rate("EUR", "EUR")) == 1.0


def test_resolve_currency_for_origin():
    assert resolve_currency_for_origin(origin="Madrid") == "EUR"
    assert resolve_currency_for_origin(origin="London") == "GBP"
    assert resolve_currency_for_origin(iata="BLR") == "INR"
    assert resolve_currency_for_origin(country_code="JP") == "JPY"
    assert resolve_currency_for_origin(origin="UnknownCityXYZ") is None


@pytest.mark.asyncio
async def test_get_rate_with_exchangerate_api(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "exchangerate_api_key", "mock_key_123")

    class MockResponse:
        status_code = 200
        def json(self):
            return {
                "result": "success",
                "base_code": "USD",
                "target_code": "EUR",
                "conversion_rate": 0.92,
            }

    class MockClient:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def get(self, url, **kwargs):
            assert "mock_key_123/pair/USD/EUR" in url
            return MockResponse()

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: MockClient())

    rate = await get_rate("USD", "EUR")
    assert rate == 0.92


@pytest.mark.asyncio
async def test_get_rate_fallback_when_exchangerate_fails(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "exchangerate_api_key", "bad_key")

    calls = []

    class MockClient:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def get(self, url, **kwargs):
            calls.append(url)
            if "exchangerate-api" in url:
                # ExchangeRate API fails
                return type("R", (), {"status_code": 403, "json": lambda self: {"result": "error"}})()
            # Frankfurter succeeds
            return type("R", (), {
                "status_code": 200,
                "json": lambda self: {"rates": {"EUR": 0.88}},
            })()

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: MockClient())

    rate = await get_rate("USD", "EUR")
    assert rate == 0.88
    assert any("exchangerate-api" in c for c in calls)
    assert any("frankfurter" in c for c in calls)


@pytest.mark.asyncio
async def test_get_rate_offline_approx_fallback(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "exchangerate_api_key", None)

    class FailingClient:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def get(self, url, **kwargs):
            raise httpx.ConnectError("Network down")

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: FailingClient())

    rate = await get_rate("USD", "INR")
    expected = APPROX_USD_RATES["INR"] / APPROX_USD_RATES["USD"]
    assert rate == pytest.approx(expected, rel=1e-3)


def asyncio_run(coro):
    import asyncio
    return asyncio.run(coro)
