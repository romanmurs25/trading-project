from decimal import Decimal

from adapters.paper.broker import PaperBroker
from trading_core.domain.enums import OrderType, Side, TimeInForce, Venue
from trading_core.domain.models import OrderIntent


def make_intent(
    *,
    side: Side = Side.BUY,
    qty: Decimal = Decimal("1"),
    idempotency_key: str,
) -> OrderIntent:
    return OrderIntent(
        strategy_id="accounting-test",
        signal_id="sig",
        venue=Venue.PAPER,
        instrument_id="moex-si",
        side=side,
        order_type=OrderType.MARKET,
        qty=qty,
        time_in_force=TimeInForce.DAY,
        reason="accounting test",
        idempotency_key=idempotency_key,
    )


def test_breakeven_close_with_commission_creates_negative_closed_trade() -> None:
    broker = PaperBroker(initial_cash=Decimal("10000"), commission_rate=Decimal("0.001"))
    broker.set_market("moex-si", bid=Decimal("100"), ask=Decimal("100"), last=Decimal("100"))

    broker.place_order(make_intent(side=Side.BUY, qty=Decimal("1"), idempotency_key="entry"))
    broker.place_order(make_intent(side=Side.SELL, qty=Decimal("1"), idempotency_key="exit"))

    closed_trades = broker.get_closed_trades()
    assert len(closed_trades) == 1
    assert closed_trades[0].gross_pnl == Decimal("0")
    assert closed_trades[0].entry_commission == Decimal("0.100")
    assert closed_trades[0].exit_commission == Decimal("0.100")
    assert closed_trades[0].net_pnl == Decimal("-0.200")
    assert broker.get_closed_trade_pnls() == [Decimal("-0.200")]


def test_partial_close_allocates_entry_commission_proportionally() -> None:
    broker = PaperBroker(initial_cash=Decimal("10000"), commission_rate=Decimal("0.001"))
    broker.set_market("moex-si", bid=Decimal("100"), ask=Decimal("100"), last=Decimal("100"))

    broker.place_order(make_intent(side=Side.BUY, qty=Decimal("2"), idempotency_key="entry"))
    broker.set_market("moex-si", bid=Decimal("110"), ask=Decimal("110"), last=Decimal("110"))
    broker.place_order(make_intent(side=Side.SELL, qty=Decimal("1"), idempotency_key="partial-exit"))

    closed_trade = broker.get_closed_trades()[0]
    assert closed_trade.qty == Decimal("1")
    assert closed_trade.entry_commission == Decimal("0.100")
    assert closed_trade.exit_commission == Decimal("0.110")
    assert closed_trade.gross_pnl == Decimal("10")
    assert closed_trade.net_pnl == Decimal("9.790")
    assert broker.get_position("moex-si").qty == Decimal("1")


def test_full_close_clears_position_qty_and_records_closed_trade() -> None:
    broker = PaperBroker(initial_cash=Decimal("10000"))
    broker.set_market("moex-si", bid=Decimal("100"), ask=Decimal("100"), last=Decimal("100"))

    broker.place_order(make_intent(side=Side.BUY, qty=Decimal("1"), idempotency_key="entry"))
    broker.set_market("moex-si", bid=Decimal("101"), ask=Decimal("101"), last=Decimal("101"))
    broker.place_order(make_intent(side=Side.SELL, qty=Decimal("1"), idempotency_key="exit"))

    assert broker.get_position("moex-si").qty == Decimal("0")
    assert broker.get_closed_trades()[0].net_pnl == Decimal("1")


def test_reversal_long_to_short_records_closed_trade_and_opens_short_remainder() -> None:
    broker = PaperBroker(initial_cash=Decimal("10000"))
    broker.set_market("moex-si", bid=Decimal("100"), ask=Decimal("100"), last=Decimal("100"))

    broker.place_order(make_intent(side=Side.BUY, qty=Decimal("1"), idempotency_key="entry"))
    broker.set_market("moex-si", bid=Decimal("110"), ask=Decimal("110"), last=Decimal("110"))
    broker.place_order(make_intent(side=Side.SELL, qty=Decimal("2"), idempotency_key="reverse"))

    closed_trade = broker.get_closed_trades()[0]
    position = broker.get_position("moex-si")
    assert closed_trade.side_closed == Side.BUY
    assert closed_trade.qty == Decimal("1")
    assert closed_trade.net_pnl == Decimal("10")
    assert position.qty == Decimal("-1")
    assert position.avg_price == Decimal("110")


def test_reversal_short_to_long_records_closed_trade_and_opens_long_remainder() -> None:
    broker = PaperBroker(initial_cash=Decimal("10000"))
    broker.set_market("moex-si", bid=Decimal("100"), ask=Decimal("100"), last=Decimal("100"))

    broker.place_order(make_intent(side=Side.SELL, qty=Decimal("1"), idempotency_key="entry"))
    broker.set_market("moex-si", bid=Decimal("90"), ask=Decimal("90"), last=Decimal("90"))
    broker.place_order(make_intent(side=Side.BUY, qty=Decimal("2"), idempotency_key="reverse"))

    closed_trade = broker.get_closed_trades()[0]
    position = broker.get_position("moex-si")
    assert closed_trade.side_closed == Side.SELL
    assert closed_trade.qty == Decimal("1")
    assert closed_trade.net_pnl == Decimal("10")
    assert position.qty == Decimal("1")
    assert position.avg_price == Decimal("90")


def test_final_equity_remains_correct_for_long_and_short_with_closed_trade_accounting() -> None:
    long_broker = PaperBroker(initial_cash=Decimal("10000"), commission_rate=Decimal("0.001"))
    long_broker.set_market("moex-si", bid=Decimal("100"), ask=Decimal("100"), last=Decimal("100"))
    long_broker.place_order(make_intent(side=Side.BUY, qty=Decimal("1"), idempotency_key="long"))
    long_broker.set_market("moex-si", bid=Decimal("105"), ask=Decimal("105"), last=Decimal("105"))

    short_broker = PaperBroker(initial_cash=Decimal("10000"), commission_rate=Decimal("0.001"))
    short_broker.set_market("moex-si", bid=Decimal("100"), ask=Decimal("100"), last=Decimal("100"))
    short_broker.place_order(make_intent(side=Side.SELL, qty=Decimal("1"), idempotency_key="short"))
    short_broker.set_market("moex-si", bid=Decimal("95"), ask=Decimal("95"), last=Decimal("95"))

    assert long_broker.final_equity() == Decimal("10004.900")
    assert short_broker.final_equity() == Decimal("10004.900")
