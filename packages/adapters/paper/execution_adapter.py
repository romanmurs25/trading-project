from collections.abc import AsyncIterator

from trading_core.domain.enums import OrderState
from trading_core.domain.models import BrokerOrderResult, Execution, Order, OrderIntent

from adapters.paper.broker import PaperBroker


class PaperExecutionAdapter:
    supports_live_execution = False
    read_only = False

    def __init__(self, broker: PaperBroker) -> None:
        self.broker = broker

    async def place_order(self, order_intent: OrderIntent) -> BrokerOrderResult:
        order, executions = self.broker.place_order(order_intent)
        return BrokerOrderResult(order=order, executions=executions)

    async def cancel_order(self, order_id: str) -> Order:
        order = self.broker.orders[order_id]
        cancelled = order.model_copy(update={"state": OrderState.CANCELLED})
        self.broker.orders[order_id] = cancelled
        return cancelled

    async def get_order_state(self, order_id: str) -> OrderState:
        return self.broker.orders[order_id].state

    async def stream_orders(self) -> AsyncIterator[Order]:
        for order in self.broker.orders.values():
            yield order

    async def stream_executions(self) -> AsyncIterator[Execution]:
        for execution in self.broker.executions:
            yield execution
