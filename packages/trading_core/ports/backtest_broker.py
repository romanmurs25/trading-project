from collections.abc import Sequence
from decimal import Decimal
from typing import Protocol

from trading_core.domain.enums import Side
from trading_core.domain.models import Execution, Order, OrderIntent, Position


class ClosedTradeLike(Protocol):
    instrument_id: str
    side_closed: Side
    qty: Decimal
    entry_price: Decimal
    exit_price: Decimal
    gross_pnl: Decimal
    net_pnl: Decimal


class BacktestBrokerPort(Protocol):
    initial_cash: Decimal

    def set_market(self, instrument_id: str, bid: Decimal, ask: Decimal, last: Decimal) -> None: ...

    def place_order(self, order_intent: OrderIntent) -> tuple[Order, list[Execution]]: ...

    def process_pending_orders(self) -> list[Execution]: ...

    def final_equity(self) -> Decimal: ...

    def get_position(self, instrument_id: str) -> Position | None: ...

    def get_closed_trade_pnls(self) -> list[Decimal]: ...

    def get_executions(self) -> list[Execution]: ...


class ClosedTradeProvider(Protocol):
    def get_closed_trades(self) -> Sequence[ClosedTradeLike]: ...
