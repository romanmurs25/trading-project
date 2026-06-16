from datetime import UTC, datetime
from decimal import Decimal

import pytest
from adapters.moex_iss.mapper import map_candles_payload
from trading_core.domain.enums import AssetClass, Venue
from trading_core.domain.errors import DataValidationError
from trading_core.domain.models import Instrument


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


def make_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "candles": {
            "columns": ["begin", "end", "open", "high", "low", "close", "volume", "value"],
            "data": [
                [
                    "2026-01-01 10:00:00",
                    "2026-01-01 10:01:00",
                    "100.1",
                    "101.2",
                    "99.9",
                    "100.8",
                    "42",
                    "4200.12",
                ]
            ],
        }
    }
    payload.update(overrides)
    return payload


def test_map_moex_iss_candle_payload_happy_path() -> None:
    candles = map_candles_payload(make_payload(), make_instrument(), "1m", "Europe/Moscow")

    assert len(candles) == 1
    candle = candles[0]
    assert candle.venue == Venue.MOEX
    assert candle.open == Decimal("100.1")
    assert candle.high == Decimal("101.2")
    assert candle.low == Decimal("99.9")
    assert candle.close == Decimal("100.8")
    assert candle.volume == Decimal("42")
    assert candle.value == Decimal("4200.12")
    assert candle.ts_start == datetime(2026, 1, 1, 7, 0, tzinfo=UTC)
    assert candle.ts_end == datetime(2026, 1, 1, 7, 1, tzinfo=UTC)


def test_map_moex_iss_candle_payload_rejects_missing_column() -> None:
    payload = make_payload(candles={"columns": ["begin", "end", "open"], "data": [["2026-01-01", "x", "1"]]})

    with pytest.raises(DataValidationError):
        map_candles_payload(payload, make_instrument(), "1m", "Europe/Moscow")


def test_map_moex_iss_candle_payload_rejects_invalid_decimal() -> None:
    payload = make_payload(
        candles={
            "columns": ["begin", "end", "open", "high", "low", "close", "volume"],
            "data": [["2026-01-01 10:00:00", "2026-01-01 10:01:00", "bad", "1", "1", "1", "1"]],
        }
    )

    with pytest.raises(DataValidationError):
        map_candles_payload(payload, make_instrument(), "1m", "Europe/Moscow")


def test_map_moex_iss_candle_payload_converts_naive_exchange_datetime_to_utc() -> None:
    candles = map_candles_payload(make_payload(), make_instrument(), "1m", "Europe/Moscow")

    assert candles[0].ts_start.tzinfo is UTC
    assert candles[0].ts_start.hour == 7
