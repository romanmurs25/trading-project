from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, cast

from trading_core.config import AppConfig
from trading_core.domain.enums import AssetClass
from trading_core.domain.errors import DataValidationError
from trading_core.domain.models import Candle, Instrument, OrderBookSnapshot, TickTrade

from adapters.moex_iss.client import MoexIssClient, MoexPayload
from adapters.moex_iss.mapper import map_candles_payload

INTERVAL_MAPPING = {
    "1m": "1",
    "10m": "10",
    "1h": "60",
    "1d": "24",
}


class MoexClientProtocol(Protocol):
    async def get(self, path: str, params: dict[str, str] | None = None) -> MoexPayload: ...


def moex_interval(interval: str) -> str:
    try:
        return INTERVAL_MAPPING[interval]
    except KeyError as exc:
        raise DataValidationError(f"Unsupported MOEX ISS candle interval: {interval}") from exc


@dataclass
class MoexIssMarketDataAdapter:
    client: MoexClientProtocol | None = None
    config: AppConfig = field(default_factory=AppConfig)
    page_size: int = 100

    async def get_historical_candles(
        self,
        instrument: Instrument,
        interval: str,
        start: datetime,
        end: datetime,
    ) -> list[Candle]:
        self._validate_datetime_window(start, end)
        client = self.client or MoexIssClient(base_url=self.config.moex_iss_base_url)
        path = self._candles_path(instrument)
        offset = 0
        candles: list[Candle] = []
        while True:
            payload = await client.get(
                path,
                params={
                    "interval": moex_interval(interval),
                    "from": start.date().isoformat(),
                    "till": end.date().isoformat(),
                    "start": str(offset),
                },
            )
            page = map_candles_payload(payload, instrument, interval, self.config.exchange_timezone)
            candles.extend(self._filter_window(page, start, end))
            if len(page) < self.page_size:
                break
            offset += len(page)
        return candles

    def stream_candles(
        self,
        instruments: Sequence[Instrument],
        interval: str,
    ) -> AsyncIterator[Candle]:
        raise NotImplementedError("MOEX ISS realtime candle stream is not implemented in read-only MVP")

    async def get_order_book(self, instrument: Instrument) -> OrderBookSnapshot:
        raise NotImplementedError("MOEX ISS order book is not implemented in read-only MVP")

    async def get_last_trade(self, instrument: Instrument) -> TickTrade:
        raise NotImplementedError("MOEX ISS last trade is not implemented in read-only MVP")

    async def get_trading_status(self, instrument: Instrument) -> str:
        return "read_only_unknown"

    def _validate_datetime_window(self, start: datetime, end: datetime) -> None:
        if start.tzinfo is None or end.tzinfo is None:
            raise DataValidationError("MOEX ISS historical candles require timezone-aware start/end")
        if start >= end:
            raise DataValidationError("MOEX ISS historical candles require start < end")

    def _filter_window(self, candles: list[Candle], start: datetime, end: datetime) -> list[Candle]:
        return [candle for candle in candles if start <= candle.ts_start < end]

    def _candles_path(self, instrument: Instrument) -> str:
        metadata = instrument.metadata
        engine = cast(str | None, metadata.get("moex_engine"))
        market = cast(str | None, metadata.get("moex_market"))
        board = cast(str | None, metadata.get("moex_board"))
        if engine is None or market is None:
            if instrument.asset_class == AssetClass.FUTURES:
                engine = engine or "futures"
                market = market or "forts"
            else:
                engine = engine or "stock"
                market = market or "shares"
        symbol = instrument.native_symbol
        board_segment = f"/boards/{board}" if board else ""
        return f"engines/{engine}/markets/{market}{board_segment}/securities/{symbol}/candles.json"
