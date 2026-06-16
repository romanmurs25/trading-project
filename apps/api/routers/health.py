from fastapi import APIRouter
from trading_core.config import AppConfig

router = APIRouter()


@router.get("/health")
def health() -> dict[str, object]:
    config = AppConfig()
    return {
        "status": "ok",
        "trading_mode": config.trading_mode.value,
        "live_trading_enabled": config.allow_live_trading,
    }
