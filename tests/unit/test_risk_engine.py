from datetime import UTC, datetime, timedelta
from decimal import Decimal

from trading_core.config import AppConfig
from trading_core.domain.enums import OrderType, Side, TimeInForce, TradingMode, Venue
from trading_core.domain.models import Instrument, OrderIntent, RiskConfig, RiskContext
from trading_core.risk.engine import RiskEngine
from trading_core.risk.kill_switch import KillSwitch


def make_instrument() -> Instrument:
    return Instrument(
        id="moex-si",
        venue=Venue.PAPER,
        asset_class="FUTURES",
        native_symbol="SiH6",
        canonical_symbol="MOEX:SIH6",
        name="Si futures",
        lot_size=Decimal("1"),
        tick_size=Decimal("1"),
        tick_value=Decimal("1"),
        currency="RUB",
    )


def make_intent(
    *,
    venue: Venue = Venue.PAPER,
    side: Side = Side.BUY,
    order_type: OrderType = OrderType.LIMIT,
    qty: Decimal = Decimal("1"),
    limit_price: Decimal = Decimal("100"),
    risk_amount: Decimal = Decimal("10"),
    idempotency_key: str = "risk-test-key",
) -> OrderIntent:
    return OrderIntent(
        strategy_id="test",
        signal_id="sig-1",
        venue=venue,
        instrument_id="moex-si",
        side=side,
        order_type=order_type,
        qty=qty,
        limit_price=limit_price,
        time_in_force=TimeInForce.DAY,
        reason="unit test",
        risk_amount=risk_amount,
        idempotency_key=idempotency_key,
    )


def make_context(**overrides: object) -> RiskContext:
    now = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
    values: dict[str, object] = {
        "instrument": make_instrument(),
        "now": now,
        "market_data_ts": now - timedelta(seconds=1),
        "bid": Decimal("99.95"),
        "ask": Decimal("100.05"),
        "portfolio_value": Decimal("100000"),
        "daily_pnl": Decimal("0"),
        "weekly_pnl": Decimal("0"),
        "open_positions_count": 0,
        "current_position_qty": Decimal("0"),
        "session_allows_trading": True,
        "account_available": True,
        "broker_supports_live": False,
        "adapter_read_only": False,
        "is_position_reducing": False,
    }
    values.update(overrides)
    return RiskContext(**values)


def make_engine(**config_overrides: object) -> RiskEngine:
    config = AppConfig()
    risk_values: dict[str, object] = {
        "trading_mode": TradingMode.PAPER,
        "allow_live_trading": False,
        "instrument_allowlist": ["moex-si"],
    }
    risk_values.update(config_overrides)
    risk_config = RiskConfig(**risk_values)
    return RiskEngine(config=risk_config, kill_switch=KillSwitch(config.risk))


def test_risk_engine_approves_valid_paper_order() -> None:
    decision = make_engine().evaluate(make_intent(), make_context())

    assert decision.approved is True
    assert decision.reason == "approved"


def test_risk_engine_rejects_live_order_by_default() -> None:
    engine = make_engine(trading_mode=TradingMode.LIVE_GUARDED, allow_live_trading=False)

    decision = engine.evaluate(make_intent(venue=Venue.MOEX), make_context())

    assert decision.approved is False
    assert decision.checks["live_trading_enabled"] is False


def test_risk_engine_rejects_stale_market_data() -> None:
    now = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
    decision = make_engine().evaluate(
        make_intent(),
        make_context(now=now, market_data_ts=now - timedelta(seconds=60)),
    )

    assert decision.approved is False
    assert decision.checks["market_data_fresh"] is False


def test_risk_engine_rejects_instrument_not_in_allowlist() -> None:
    decision = make_engine(instrument_allowlist=["other"]).evaluate(make_intent(), make_context())

    assert decision.approved is False
    assert decision.checks["instrument_allowlisted"] is False


def test_risk_engine_rejects_order_above_max_risk() -> None:
    decision = make_engine(max_risk_per_trade_pct=Decimal("0.01")).evaluate(
        make_intent(risk_amount=Decimal("100")),
        make_context(portfolio_value=Decimal("100000")),
    )

    assert decision.approved is False
    assert decision.checks["max_risk_per_trade"] is False


def test_risk_engine_rejects_order_above_max_qty_and_exposure() -> None:
    decision = make_engine(max_order_qty=Decimal("2"), max_notional_exposure=Decimal("150")).evaluate(
        make_intent(qty=Decimal("3"), limit_price=Decimal("100")),
        make_context(),
    )

    assert decision.approved is False
    assert decision.checks["max_order_qty"] is False
    assert decision.checks["max_notional_exposure"] is False


def test_risk_engine_rejects_market_order_in_live_mode_when_not_allowed() -> None:
    engine = make_engine(
        trading_mode=TradingMode.LIVE_GUARDED,
        allow_live_trading=True,
        allow_market_orders_live=False,
    )
    decision = engine.evaluate(
        make_intent(venue=Venue.MOEX, order_type=OrderType.MARKET),
        make_context(broker_supports_live=True),
    )

    assert decision.approved is False
    assert decision.checks["market_orders_live_allowed"] is False


def test_risk_engine_rejects_when_kill_switch_is_active() -> None:
    config = AppConfig()
    kill_switch = KillSwitch(config.risk)
    kill_switch.activate("manual test")
    engine = RiskEngine(
        config=RiskConfig(
            trading_mode=TradingMode.PAPER,
            instrument_allowlist=["moex-si"],
            allow_reduce_only_when_killed=True,
        ),
        kill_switch=kill_switch,
    )

    decision = engine.evaluate(make_intent(), make_context(is_position_reducing=False))

    assert decision.approved is False
    assert decision.checks["kill_switch"] is False


def test_risk_engine_rejects_duplicate_idempotency_key_and_updates_external_set() -> None:
    seen: set[str] = set()
    engine = RiskEngine(
        config=RiskConfig(trading_mode=TradingMode.PAPER, instrument_allowlist=["moex-si"]),
        kill_switch=KillSwitch(),
        seen_idempotency_keys=seen,
    )

    first = engine.evaluate(make_intent(idempotency_key="same-key"), make_context())
    second = engine.evaluate(make_intent(idempotency_key="same-key"), make_context())

    assert first.approved is True
    assert "same-key" in seen
    assert second.approved is False
    assert second.checks["idempotency_key_is_new"] is False


def test_live_guarded_rejects_empty_allowlist_even_when_live_flags_enabled() -> None:
    engine = RiskEngine(
        config=RiskConfig(
            trading_mode=TradingMode.LIVE_GUARDED,
            allow_live_trading=True,
            instrument_allowlist=[],
        ),
        kill_switch=KillSwitch(),
    )

    decision = engine.evaluate(
        make_intent(venue=Venue.MOEX, order_type=OrderType.LIMIT),
        make_context(broker_supports_live=True),
    )

    assert decision.approved is False
    assert decision.checks["live_allowlist_non_empty"] is False


def test_max_open_positions_rejects_new_position_at_limit() -> None:
    decision = make_engine(max_open_positions=1).evaluate(
        make_intent(side=Side.BUY),
        make_context(open_positions_count=1, current_position_qty=Decimal("0")),
    )

    assert decision.approved is False
    assert decision.checks["max_open_positions"] is False


def test_max_open_positions_allows_long_reduce_only_at_limit() -> None:
    decision = make_engine(max_open_positions=1).evaluate(
        make_intent(side=Side.SELL, qty=Decimal("1")),
        make_context(open_positions_count=1, current_position_qty=Decimal("2")),
    )

    assert decision.checks["max_open_positions"] is True


def test_max_open_positions_allows_short_reduce_only_at_limit() -> None:
    decision = make_engine(max_open_positions=1).evaluate(
        make_intent(side=Side.BUY, qty=Decimal("1")),
        make_context(open_positions_count=1, current_position_qty=Decimal("-2")),
    )

    assert decision.checks["max_open_positions"] is True


def test_paper_market_order_is_allowed() -> None:
    decision = make_engine().evaluate(make_intent(order_type=OrderType.MARKET), make_context())

    assert decision.approved is True
    assert decision.checks["market_orders_live_allowed"] is True


def test_live_guarded_limit_order_can_pass_when_all_gates_are_enabled() -> None:
    engine = make_engine(
        trading_mode=TradingMode.LIVE_GUARDED,
        allow_live_trading=True,
        instrument_allowlist=["moex-si"],
    )

    decision = engine.evaluate(
        make_intent(venue=Venue.MOEX, order_type=OrderType.LIMIT),
        make_context(broker_supports_live=True),
    )

    assert decision.approved is True
