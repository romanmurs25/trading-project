from fastapi import APIRouter

from apps.api.deps import storage

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.get("")
def list_orders() -> list[dict[str, object]]:
    return [order.model_dump(mode="json") for order in storage.orders]
