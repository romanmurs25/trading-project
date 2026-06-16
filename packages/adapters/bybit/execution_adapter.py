from trading_core.domain.errors import LiveTradingDisabledError
from trading_core.domain.models import OrderIntent


class BybitExecutionAdapter:
    supports_live_execution = False
    read_only = True

    async def place_order(self, order_intent: OrderIntent) -> None:
        raise LiveTradingDisabledError(
            "Bybit order placement is disabled in MVP "
            f"for order intent {order_intent.id}; TradFi is not implemented"
        )

    async def stream_private_orders(self) -> None:
        raise NotImplementedError(
            "TODO: implement private order stream skeleton for sandbox/live guarded mode"
        )
