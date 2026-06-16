from uuid import uuid4

from trading_core.domain.models import OrderIntent


def ensure_idempotency_key(order_intent: OrderIntent) -> OrderIntent:
    if order_intent.idempotency_key:
        return order_intent
    return order_intent.model_copy(update={"idempotency_key": f"intent-{order_intent.id}-{uuid4()}"})
