from decimal import Decimal

from trading_core.config import AppConfig
from trading_core.domain.enums import OrderType, Side, TimeInForce, Venue
from trading_core.domain.models import OrderIntent
from trading_core.risk.kill_switch import KillSwitch


def make_intent(side: Side, qty: Decimal) -> OrderIntent:
    return OrderIntent(
        strategy_id="test",
        signal_id="sig",
        venue=Venue.PAPER,
        instrument_id="moex-si",
        side=side,
        order_type=OrderType.LIMIT,
        qty=qty,
        limit_price=Decimal("100"),
        time_in_force=TimeInForce.DAY,
        reason="test",
        idempotency_key="ks-key",
    )


def test_kill_switch_blocks_new_orders() -> None:
    kill_switch = KillSwitch(AppConfig().risk)
    kill_switch.activate("manual")

    assert (
        kill_switch.allows_order(make_intent(Side.BUY, Decimal("1")), current_position_qty=Decimal("0"))
        is False
    )


def test_kill_switch_allows_reduce_only_order_when_configured() -> None:
    kill_switch = KillSwitch(AppConfig().risk)
    kill_switch.activate("manual")

    assert (
        kill_switch.allows_order(make_intent(Side.SELL, Decimal("1")), current_position_qty=Decimal("2"))
        is True
    )


def test_kill_switch_rejects_reduce_order_that_flips_long_position() -> None:
    kill_switch = KillSwitch(AppConfig().risk)
    kill_switch.activate("manual")

    assert (
        kill_switch.allows_order(make_intent(Side.SELL, Decimal("3")), current_position_qty=Decimal("2"))
        is False
    )


def test_kill_switch_allows_short_reduce_only_order_when_configured() -> None:
    kill_switch = KillSwitch(AppConfig().risk)
    kill_switch.activate("manual")

    assert (
        kill_switch.allows_order(make_intent(Side.BUY, Decimal("1")), current_position_qty=Decimal("-2"))
        is True
    )


def test_kill_switch_rejects_reduce_order_that_flips_short_position() -> None:
    kill_switch = KillSwitch(AppConfig().risk)
    kill_switch.activate("manual")

    assert (
        kill_switch.allows_order(make_intent(Side.BUY, Decimal("3")), current_position_qty=Decimal("-2"))
        is False
    )


def test_kill_switch_auto_activates_after_error_threshold() -> None:
    kill_switch = KillSwitch(AppConfig().risk, broker_error_threshold=2)

    kill_switch.record_broker_error("first")
    kill_switch.record_broker_error("second")

    assert kill_switch.active is True
    assert "broker errors" in str(kill_switch.reason)
