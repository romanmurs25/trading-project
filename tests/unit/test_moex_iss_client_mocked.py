from decimal import Decimal

import httpx
import pytest
from adapters.moex_iss.client import MoexIssClient
from trading_core.domain.errors import AdapterError


@pytest.mark.asyncio
async def test_moex_iss_client_returns_payload_without_external_http() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/iss/test.json"
        return httpx.Response(
            200,
            text='{"candles":{"columns":["open"],"data":[[100.1]]}}',
            request=request,
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://moex.test/iss",
    ) as http_client:
        client = MoexIssClient(base_url="https://moex.test/iss", http_client=http_client)

        payload = await client.get("/test.json")

    assert payload["candles"] == {"columns": ["open"], "data": [[Decimal("100.1")]]}


@pytest.mark.asyncio
async def test_moex_iss_client_retries_429_then_succeeds() -> None:
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, text="too many requests", request=request)
        return httpx.Response(200, text='{"ok": true}', request=request)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://moex.test/iss",
    ) as http_client:
        client = MoexIssClient(
            base_url="https://moex.test/iss",
            http_client=http_client,
            max_retries=2,
            backoff_seconds=0,
            rate_limit_seconds=0,
        )

        payload = await client.get("/retry.json")

    assert payload == {"ok": True}
    assert calls == 2


@pytest.mark.asyncio
async def test_moex_iss_client_raises_after_5xx_retries_exhausted() -> None:
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(503, text="unavailable", request=request)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://moex.test/iss",
    ) as http_client:
        client = MoexIssClient(
            base_url="https://moex.test/iss",
            http_client=http_client,
            max_retries=2,
            backoff_seconds=0,
            rate_limit_seconds=0,
        )

        with pytest.raises(AdapterError):
            await client.get("/fails.json")

    assert calls == 3
