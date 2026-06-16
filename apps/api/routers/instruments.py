from fastapi import APIRouter

router = APIRouter(prefix="/api/instruments", tags=["instruments"])


@router.get("")
def list_instruments() -> list[dict[str, str]]:
    return []
