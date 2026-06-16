from fastapi import APIRouter
from trading_core.strategy.registry import available_strategies

router = APIRouter(prefix="/api/strategies", tags=["strategies"])


@router.get("")
def list_strategies() -> list[str]:
    return sorted(available_strategies())
