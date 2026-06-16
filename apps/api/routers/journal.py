from fastapi import APIRouter

router = APIRouter(prefix="/api/journal", tags=["journal"])


@router.get("")
def list_journal() -> dict[str, object]:
    return {
        "items": [],
        "status": "placeholder",
        "note": "Journal persistence will be implemented after storage repositories.",
    }
