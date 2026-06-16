from collections.abc import AsyncIterator
from typing import Protocol

from trading_core.domain.enums import OrderState
from trading_core.domain.models import BrokerOrderResult, Execution, Order, OrderIntent


class ExecutionPort(Protocol):
    async def place_order(self, order_intent: OrderIntent) -> BrokerOrderResult: ...

    async def cancel_order(self, order_id: str) -> Order: ...

    async def get_order_state(self, order_id: str) -> OrderState: ...

    async def stream_orders(self) -> AsyncIterator[Order]: ...

    async def stream_executions(self) -> AsyncIterator[Execution]: ...
