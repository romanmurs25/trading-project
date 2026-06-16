from decimal import Decimal

from adapters.paper.broker import PaperBroker
from trading_core.domain.enums import OrderState, OrderType, Side, TimeInForce, Venue
from trading_core.domain.models import OrderIntent


def make_intent(
    *,
    side: Side = Side.BUY,
    order_type: OrderType = OrderType.MARKET,
    qty: Decimal = Decimal("1"),
    limit_price: Decimal | None = None,
    idempotency_key: str | None = None,
) -> OrderIntent:
    return OrderIntent(
        strategy_id="test",
        signal_id="sig",
        venue=Venue.PAPER,
        instrument_id="moex-si",
        side=side,
        order_type=order_type,
        qty=qty,
        limit_price=limit_price,
        time_in_force=TimeInForce.DAY,
        reason="paper test",
        idempotency_key=idempotency_key or f"paper-{side.value}-{order_type.value}-{qty}",
    )


def test_paper_broker_executes_market_order() -> None:
    broker = PaperBroker(initial_cash=Decimal("10000"))
    broker.set_market("moex-si", bid=Decimal("99.90"), ask=Decimal("100.10"), last=Decimal("100"))

    order, executions = broker.place_order(make_intent())

    assert order.state == OrderState.FILLED
    assert executions[0].price == Decimal("100.10")
    assert broker.positions["moex-si"].qty == Decimal("1")


def test_paper_broker_simulates_slippage_and_commission() -> None:
    broker = PaperBroker(
        initial_cash=Decimal("10000"),
        commission_rate=Decimal("0.001"),
        slippage=Decimal("0.05"),
    )
    broker.set_market("moex-si", bid=Decimal("99.90"), ask=Decimal("100.10"), last=Decimal("100"))

    _, executions = broker.place_order(make_intent(qty=Decimal("2")))

    assert executions[0].price == Decimal("100.15")
    assert executions[0].commission == Decimal("0.200300")
    assert broker.cash == Decimal("9799.499700")


def test_paper_broker_executes_crossed_limit_order() -> None:
    broker = PaperBroker(initial_cash=Decimal("10000"))
    broker.set_market("moex-si", bid=Decimal("99.90"), ask=Decimal("100.10"), last=Decimal("100"))

    order, executions = broker.place_order(
        make_intent(order_type=OrderType.LIMIT, limit_price=Decimal("101"))
    )

    assert order.state == OrderState.FILLED
    assert executions


def test_paper_broker_duplicate_idempotency_key_does_not_create_duplicate_execution() -> None:
    broker = PaperBroker(initial_cash=Decimal("10000"))
    broker.set_market("moex-si", bid=Decimal("99.90"), ask=Decimal("100.10"), last=Decimal("100"))
    intent = make_intent()

    first_order, first_executions = broker.place_order(intent)
    second_order, second_executions = broker.place_order(intent)

    assert second_order.id == first_order.id
    assert second_executions == first_executions
    assert len(broker.executions) == 1


def test_non_crossing_limit_order_remains_submitted_then_fills_after_market_update() -> None:
    broker = PaperBroker(initial_cash=Decimal("10000"))
    broker.set_market("moex-si", bid=Decimal("99.90"), ask=Decimal("100.10"), last=Decimal("100"))

    order, executions = broker.place_order(
        make_intent(order_type=OrderType.LIMIT, limit_price=Decimal("99"))
    )
    broker.set_market("moex-si", bid=Decimal("98.80"), ask=Decimal("99"), last=Decimal("99"))
    pending_executions = broker.process_pending_orders()

    assert order.state == OrderState.SUBMITTED
    assert executions == []
    assert len(pending_executions) == 1
    assert broker.orders[order.id].state == OrderState.FILLED


def test_closing_long_records_realized_pnl_after_commission() -> None:
    broker = PaperBroker(initial_cash=Decimal("10000"), commission_rate=Decimal("0.001"))
    broker.set_market("moex-si", bid=Decimal("100"), ask=Decimal("100"), last=Decimal("100"))
    broker.place_order(make_intent(qty=Decimal("1"), idempotency_key="entry"))
    broker.set_market("moex-si", bid=Decimal("110"), ask=Decimal("110"), last=Decimal("110"))

    broker.place_order(
        make_intent(side=Side.SELL, qty=Decimal("1"), idempotency_key="exit")
    )

    assert broker.positions["moex-si"].qty == Decimal("0")
    assert broker.closed_trade_pnls[-1] == Decimal("9.79")


def test_reversal_long_to_short_updates_qty_and_realized_pnl() -> None:
    broker = PaperBroker(initial_cash=Decimal("10000"))
    broker.set_market("moex-si", bid=Decimal("100"), ask=Decimal("100"), last=Decimal("100"))
    broker.place_order(make_intent(qty=Decimal("1"), idempotency_key="entry"))
    broker.set_market("moex-si", bid=Decimal("110"), ask=Decimal("110"), last=Decimal("110"))

    broker.place_order(
        make_intent(side=Side.SELL, qty=Decimal("2"), idempotency_key="reverse")
    )

    assert broker.positions["moex-si"].qty == Decimal("-1")
    assert broker.positions["moex-si"].avg_price == Decimal("110")
    assert broker.closed_trade_pnls[-1] == Decimal("10")


def test_final_equity_marks_long_and_short_positions() -> None:
    long_broker = PaperBroker(initial_cash=Decimal("10000"))
    long_broker.set_market("moex-si", bid=Decimal("100"), ask=Decimal("100"), last=Decimal("100"))
    long_broker.place_order(make_intent(qty=Decimal("1"), idempotency_key="long"))
    long_broker.set_market("moex-si", bid=Decimal("105"), ask=Decimal("105"), last=Decimal("105"))

    short_broker = PaperBroker(initial_cash=Decimal("10000"))
    short_broker.set_market("moex-si", bid=Decimal("100"), ask=Decimal("100"), last=Decimal("100"))
    short_broker.place_order(make_intent(side=Side.SELL, qty=Decimal("1"), idempotency_key="short"))
    short_broker.set_market("moex-si", bid=Decimal("95"), ask=Decimal("95"), last=Decimal("95"))

    assert long_broker.final_equity() == Decimal("10005")
    assert short_broker.final_equity() == Decimal("10005")
