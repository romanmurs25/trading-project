from fastapi import APIRouter

router = APIRouter(prefix="/api/market-data", tags=["market-data"])


@router.get("/candles")
def list_candles() -> list[dict[str, str]]:
    return []
