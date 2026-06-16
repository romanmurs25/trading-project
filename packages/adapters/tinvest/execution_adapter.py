from trading_core.domain.errors import LiveTradingDisabledError
from trading_core.domain.models import OrderIntent


class TInvestExecutionAdapter:
    supports_live_execution = False
    read_only = True

    async def place_order(self, order_intent: OrderIntent) -> None:
        raise LiveTradingDisabledError(
            f"T-Invest live execution is disabled in MVP for order intent {order_intent.id}"
        )
