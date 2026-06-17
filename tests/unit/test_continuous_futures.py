from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from trading_core.domain.enums import AssetClass, Venue
from trading_core.domain.errors import DataValidationError
from trading_core.domain.models import Candle, ContractSpec, Instrument
from trading_core.market.continuous import build_continuous_futures_series
from trading_core.market.roll import RollRule


def instrument(symbol: str, expiry: date) -> Instrument:
    return Instrument(
        id=f"moex:{symbol}",
        venue=Venue.MOEX,
        asset_class=AssetClass.FUTURES,
        native_symbol=symbol,
        canonical_symbol=f"MOEX:{symbol}",
        name=symbol,
        lot_size=Decimal("1"),
        tick_size=Decimal("1"),
        tick_value=Decimal("1"),
        currency="RUB",
        expiry_date=expiry,
    )


def spec(symbol: str, expiry: date) -> ContractSpec:
    return ContractSpec(
        instrument_id=f"moex:{symbol}",
        lot_size=Decimal("1"),
        tick_size=Decimal("1"),
        tick_value=Decimal("1"),
        currency="RUB",
        expiry_date=expiry,
        last_trade_date=expiry,
        underlying_symbol="Si",
    )


def candle(symbol: str, ts_start: datetime, close: str, interval: str = "1m") -> Candle:
    return Candle(
        instrument_id=f"moex:{symbol}",
        venue=Venue.MOEX,
        interval=interval,
        ts_start=ts_start,
        ts_end=ts_start + timedelta(minutes=1),
        open=Decimal(close),
        high=Decimal(close),
        low=Decimal(close),
        close=Decimal(close),
        volume=Decimal("100"),
        source="test",
    )


def test_continuous_series_combines_contracts_around_roll_date() -> None:
    h = instrument("SiH6", date(2026, 3, 19))
    m = instrument("SiM6", date(2026, 6, 18))
    series, components, candles, events = build_continuous_futures_series(
        underlying_symbol="Si",
        instruments=[h, m],
        contract_specs=[spec("SiH6", date(2026, 3, 19)), spec("SiM6", date(2026, 6, 18))],
        candles_by_instrument={
            h.id: [candle("SiH6", datetime(2026, 3, 13, 7, 0, tzinfo=UTC), "100")],
            m.id: [candle("SiM6", datetime(2026, 3, 16, 7, 0, tzinfo=UTC), "200")],
        },
        start=datetime(2026, 3, 13, tzinfo=UTC),
        end=datetime(2026, 3, 17, tzinfo=UTC),
        interval="1m",
        roll_rule=RollRule(roll_days_before_expiry=5),
    )

    assert series.canonical_symbol == "MOEX:Si:CONT:1m"
    assert [item.instrument_id for item in candles] == ["continuous:Si", "continuous:Si"]
    assert [item.close for item in candles] == [Decimal("100"), Decimal("200")]
    assert len(components) == 2
    assert components[0].instrument_id == "moex:SiH6"
    assert components[0].canonical_symbol == "MOEX:SiH6"
    assert len(events) == 1


def test_continuous_series_canonical_symbol_includes_interval() -> None:
    h = instrument("SiH6", date(2026, 3, 19))
    contract_specs = [spec("SiH6", date(2026, 3, 19))]

    one_minute, _components_1m, _candles_1m, _events_1m = build_continuous_futures_series(
        underlying_symbol="Si",
        instruments=[h],
        contract_specs=contract_specs,
        candles_by_instrument={h.id: [candle("SiH6", datetime(2026, 3, 13, 7, 0, tzinfo=UTC), "100")]},
        start=datetime(2026, 3, 13, tzinfo=UTC),
        end=datetime(2026, 3, 14, tzinfo=UTC),
        interval="1m",
        roll_rule=RollRule(),
    )
    ten_minute, _components_10m, _candles_10m, _events_10m = build_continuous_futures_series(
        underlying_symbol="Si",
        instruments=[h],
        contract_specs=contract_specs,
        candles_by_instrument={
            h.id: [candle("SiH6", datetime(2026, 3, 13, 7, 0, tzinfo=UTC), "100", interval="10m")]
        },
        start=datetime(2026, 3, 13, tzinfo=UTC),
        end=datetime(2026, 3, 14, tzinfo=UTC),
        interval="10m",
        roll_rule=RollRule(),
    )

    assert one_minute.canonical_symbol == "MOEX:Si:CONT:1m"
    assert ten_minute.canonical_symbol == "MOEX:Si:CONT:10m"
    assert one_minute.canonical_symbol != ten_minute.canonical_symbol


def test_unsupported_adjustment_method_rejected() -> None:
    with pytest.raises(DataValidationError):
        build_continuous_futures_series(
            underlying_symbol="Si",
            instruments=[instrument("SiH6", date(2026, 3, 19))],
            contract_specs=[spec("SiH6", date(2026, 3, 19))],
            candles_by_instrument={},
            start=datetime(2026, 3, 1, tzinfo=UTC),
            end=datetime(2026, 3, 2, tzinfo=UTC),
            interval="1m",
            roll_rule=RollRule(),
            adjustment_method="back_adjusted",
        )


def test_missing_selected_contract_candles_adds_warning_and_skips() -> None:
    series, components, candles, events = build_continuous_futures_series(
        underlying_symbol="Si",
        instruments=[instrument("SiH6", date(2026, 3, 19))],
        contract_specs=[spec("SiH6", date(2026, 3, 19))],
        candles_by_instrument={},
        start=datetime(2026, 3, 1, tzinfo=UTC),
        end=datetime(2026, 3, 2, tzinfo=UTC),
        interval="1m",
        roll_rule=RollRule(),
    )

    assert candles == []
    assert components == []
    assert events == []
    assert "missing candles" in series.metadata["warnings"][0]
