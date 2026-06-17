from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError
from trading_core.domain.enums import AssetClass, OrderType, Side, TimeInForce, Venue
from trading_core.domain.models import Candle, Instrument, OrderIntent
from trading_core.research.models import BacktestEquityPoint, BacktestTradeRecord


def make_candle(**overrides: object) -> Candle:
    start = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
    values: dict[str, object] = {
        "instrument_id": "moex-si",
        "venue": Venue.PAPER,
        "interval": "1m",
        "ts_start": start,
        "ts_end": start + timedelta(minutes=1),
        "open": Decimal("100.1"),
        "high": Decimal("101.1"),
        "low": Decimal("99.1"),
        "close": Decimal("100.5"),
        "volume": Decimal("1000"),
        "source": "test",
    }
    values.update(overrides)
    return Candle(**values)


def make_instrument(**overrides: object) -> Instrument:
    values: dict[str, object] = {
        "id": "moex-si",
        "venue": Venue.PAPER,
        "asset_class": AssetClass.FUTURES,
        "native_symbol": "SiH6",
        "canonical_symbol": "MOEX:SIH6",
        "name": "Si futures",
        "lot_size": Decimal("1"),
        "tick_size": Decimal("0.01"),
        "tick_value": Decimal("1"),
        "currency": "RUB",
    }
    values.update(overrides)
    return Instrument(**values)


def make_intent(**overrides: object) -> OrderIntent:
    values: dict[str, object] = {
        "strategy_id": "test",
        "signal_id": "sig",
        "venue": Venue.PAPER,
        "instrument_id": "moex-si",
        "side": Side.BUY,
        "order_type": OrderType.LIMIT,
        "qty": Decimal("1"),
        "limit_price": Decimal("100"),
        "time_in_force": TimeInForce.DAY,
        "reason": "test",
        "idempotency_key": "decimal-test",
    }
    values.update(overrides)
    return OrderIntent(**values)


def test_candle_rejects_float_money_fields() -> None:
    with pytest.raises(ValidationError, match="float is forbidden"):
        make_candle(open=100.1)


def test_order_intent_rejects_float_qty() -> None:
    with pytest.raises(ValidationError, match="float is forbidden"):
        make_intent(qty=0.1)


def test_instrument_rejects_float_tick_size() -> None:
    with pytest.raises(ValidationError, match="float is forbidden"):
        make_instrument(tick_size=0.01)


def test_decimal_and_string_money_fields_are_allowed() -> None:
    candle = make_candle(open=Decimal("100.1"), close="100.2")
    instrument = make_instrument(tick_size="0.01")
    intent = make_intent(qty="1.5")

    assert candle.open == Decimal("100.1")
    assert candle.close == Decimal("100.2")
    assert instrument.tick_size == Decimal("0.01")
    assert intent.qty == Decimal("1.5")


def test_backtest_equity_point_rejects_float_drawdown() -> None:
    with pytest.raises(ValidationError, match="float is forbidden"):
        BacktestEquityPoint(
            backtest_run_id="bt-1",
            ts=datetime(2026, 1, 1, tzinfo=UTC),
            equity=Decimal("100000"),
            drawdown=0.1,
        )


def test_backtest_trade_record_rejects_float_pnl_and_r_fields() -> None:
    base_values: dict[str, object] = {
        "backtest_run_id": "bt-1",
        "instrument_id": "moex-si",
        "side": Side.BUY,
        "entry_price": Decimal("100"),
        "exit_price": Decimal("110"),
        "qty": Decimal("1"),
        "gross_pnl": Decimal("10"),
        "net_pnl": Decimal("9"),
        "r_multiple": Decimal("1"),
    }

    for field_name in ("gross_pnl", "net_pnl", "r_multiple"):
        values = {**base_values, field_name: 1.0}
        with pytest.raises(ValidationError, match="float is forbidden"):
            BacktestTradeRecord(**values)


def test_backtest_research_decimal_inputs_are_allowed() -> None:
    point = BacktestEquityPoint(
        backtest_run_id="bt-1",
        ts=datetime(2026, 1, 1, tzinfo=UTC),
        equity=Decimal("100000"),
        drawdown=Decimal("0.1"),
    )
    trade = BacktestTradeRecord(
        backtest_run_id="bt-1",
        instrument_id="moex-si",
        side=Side.BUY,
        entry_price=Decimal("100"),
        exit_price=Decimal("110"),
        qty=Decimal("1"),
        gross_pnl=Decimal("10"),
        net_pnl=Decimal("9"),
        r_multiple=Decimal("1"),
    )

    assert point.drawdown == Decimal("0.1")
    assert trade.gross_pnl == Decimal("10")
    assert trade.net_pnl == Decimal("9")
    assert trade.r_multiple == Decimal("1")
