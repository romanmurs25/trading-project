from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from adapters.moex_iss.market_data_adapter import MoexIssMarketDataAdapter, moex_interval
from trading_core.domain.enums import AssetClass, Venue
from trading_core.domain.errors import DataValidationError
from trading_core.domain.models import Instrument


class FakeMoexClient:
    def __init__(self, pages: list[dict[str, object]]) -> None:
        self.pages = pages
        self.calls: list[tuple[str, dict[str, str]]] = []

    async def get(self, path: str, params: dict[str, str] | None = None) -> dict[str, object]:
        self.calls.append((path, params or {}))
        return self.pages.pop(0)


def make_instrument() -> Instrument:
    return Instrument(
        id="moex-si",
        venue=Venue.MOEX,
        asset_class=AssetClass.FUTURES,
        native_symbol="SiH6",
        canonical_symbol="MOEX:SIH6",
        name="Si futures",
        lot_size=Decimal("1"),
        tick_size=Decimal("1"),
        tick_value=Decimal("1"),
        currency="RUB",
    )


def payload(rows: list[list[Any]]) -> dict[str, object]:
    return {
        "candles": {
            "columns": ["begin", "end", "open", "high", "low", "close", "volume", "value"],
            "data": rows,
        }
    }


@pytest.mark.asyncio
async def test_moex_market_data_adapter_loads_single_page() -> None:
    client = FakeMoexClient(
        [
            payload(
                [
                    [
                        "2026-01-01 10:00:00",
                        "2026-01-01 10:01:00",
                        "100",
                        "101",
                        "99",
                        "100.5",
                        "10",
                        "1000",
                    ]
                ]
            )
        ]
    )
    adapter = MoexIssMarketDataAdapter(client=client, page_size=100)

    candles = await adapter.get_historical_candles(
        make_instrument(),
        "1m",
        datetime(2026, 1, 1, tzinfo=UTC),
        datetime(2026, 1, 2, tzinfo=UTC),
    )

    assert len(candles) == 1
    assert candles[0].close == Decimal("100.5")
    assert client.calls[0][1]["interval"] == "1"
    assert client.calls[0][1]["start"] == "0"


@pytest.mark.asyncio
async def test_moex_market_data_adapter_paginates_until_short_page() -> None:
    client = FakeMoexClient(
        [
            payload([["2026-01-01 10:00:00", "2026-01-01 10:01:00", "100", "101", "99", "100", "1", "1"]]),
            payload([["2026-01-01 10:01:00", "2026-01-01 10:02:00", "101", "102", "100", "101", "1", "1"]]),
            payload([]),
        ]
    )
    adapter = MoexIssMarketDataAdapter(client=client, page_size=1)

    candles = await adapter.get_historical_candles(
        make_instrument(),
        "1m",
        datetime(2026, 1, 1, tzinfo=UTC),
        datetime(2026, 1, 2, tzinfo=UTC),
    )

    assert len(candles) == 2
    assert [call[1]["start"] for call in client.calls] == ["0", "1", "2"]


@pytest.mark.asyncio
async def test_moex_market_data_adapter_filters_exact_datetime_window() -> None:
    client = FakeMoexClient(
        [
            payload(
                [
                    ["2026-01-01 10:00:00", "2026-01-01 10:01:00", "100", "101", "99", "100", "1", "1"],
                    ["2026-01-01 10:01:00", "2026-01-01 10:02:00", "101", "102", "100", "101", "1", "1"],
                    ["2026-01-01 10:02:00", "2026-01-01 10:03:00", "102", "103", "101", "102", "1", "1"],
                    ["2026-01-01 10:03:00", "2026-01-01 10:04:00", "103", "104", "102", "103", "1", "1"],
                ]
            )
        ]
    )
    adapter = MoexIssMarketDataAdapter(client=client, page_size=100)

    candles = await adapter.get_historical_candles(
        make_instrument(),
        "1m",
        datetime(2026, 1, 1, 7, 1, tzinfo=UTC),
        datetime(2026, 1, 1, 7, 3, tzinfo=UTC),
    )

    assert [candle.close for candle in candles] == [Decimal("101"), Decimal("102")]


@pytest.mark.asyncio
async def test_moex_market_data_adapter_rejects_naive_datetime_window() -> None:
    adapter = MoexIssMarketDataAdapter(client=FakeMoexClient([]))

    with pytest.raises(DataValidationError):
        await adapter.get_historical_candles(
            make_instrument(),
            "1m",
            datetime(2026, 1, 1),
            datetime(2026, 1, 2, tzinfo=UTC),
        )

    with pytest.raises(DataValidationError):
        await adapter.get_historical_candles(
            make_instrument(),
            "1m",
            datetime(2026, 1, 1, tzinfo=UTC),
            datetime(2026, 1, 2),
        )


@pytest.mark.asyncio
async def test_moex_market_data_adapter_rejects_start_at_or_after_end() -> None:
    adapter = MoexIssMarketDataAdapter(client=FakeMoexClient([]))

    with pytest.raises(DataValidationError):
        await adapter.get_historical_candles(
            make_instrument(),
            "1m",
            datetime(2026, 1, 2, tzinfo=UTC),
            datetime(2026, 1, 2, tzinfo=UTC),
        )


def test_moex_interval_mapping_is_explicit() -> None:
    assert moex_interval("1m") == "1"
    assert moex_interval("10m") == "10"
    assert moex_interval("1h") == "60"
    assert moex_interval("1d") == "24"


def test_moex_market_data_adapter_does_not_expose_execution_methods() -> None:
    assert not hasattr(MoexIssMarketDataAdapter, "place_order")
    assert not hasattr(MoexIssMarketDataAdapter, "cancel_order")
