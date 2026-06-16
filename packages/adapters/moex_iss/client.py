import asyncio
import json
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

import httpx
from trading_core.config import AppConfig
from trading_core.domain.errors import AdapterError, DataValidationError

MoexPayload = dict[str, Any]


@dataclass
class MoexIssClient:
    """Read-only MOEX ISS HTTP client.

    The client has no execution methods and intentionally accepts no broker credentials.
    """

    base_url: str | None = None
    http_client: httpx.AsyncClient | None = None
    timeout_seconds: float = 10.0
    max_retries: int = 2
    backoff_seconds: float = 0.25
    rate_limit_seconds: float = 0.05
    _config: AppConfig = field(default_factory=AppConfig, repr=False)

    async def get(self, path: str, params: dict[str, str] | None = None) -> MoexPayload:
        normalized_path = path.lstrip("/")
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            if self.rate_limit_seconds > 0:
                await asyncio.sleep(self.rate_limit_seconds)
            try:
                response = await self._request(normalized_path, params)
                if response.status_code in {429} or response.status_code >= 500:
                    if attempt < self.max_retries:
                        await self._backoff(attempt)
                        continue
                    raise AdapterError(f"MOEX ISS temporary error after retries: HTTP {response.status_code}")
                if response.status_code >= 400:
                    raise AdapterError(f"MOEX ISS request failed: HTTP {response.status_code}")
                return self._decode_payload(response)
            except httpx.RequestError as exc:
                last_error = exc
                if attempt < self.max_retries:
                    await self._backoff(attempt)
                    continue
                raise AdapterError(f"MOEX ISS network error after retries: {exc.__class__.__name__}") from exc
        raise AdapterError(f"MOEX ISS request failed: {last_error}") from last_error

    async def _request(self, path: str, params: dict[str, str] | None) -> httpx.Response:
        if self.http_client is not None:
            return await self.http_client.get(path, params=params)
        async with httpx.AsyncClient(base_url=self._base_url(), timeout=self.timeout_seconds) as client:
            return await client.get(path, params=params)

    async def _backoff(self, attempt: int) -> None:
        if self.backoff_seconds <= 0:
            return
        await asyncio.sleep(self.backoff_seconds * float(2**attempt))

    def _base_url(self) -> str:
        return self.base_url or self._config.moex_iss_base_url

    def _decode_payload(self, response: httpx.Response) -> MoexPayload:
        try:
            payload = json.loads(response.text, parse_float=Decimal)
        except json.JSONDecodeError as exc:
            raise DataValidationError("MOEX ISS returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise DataValidationError("MOEX ISS payload must be a JSON object")
        return payload
