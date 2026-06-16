from datetime import UTC, date, datetime, time
from decimal import Decimal

from adapters.moex_iss.market_data_adapter import MoexIssMarketDataAdapter
from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field
from storage.in_memory import InMemoryStorage
from trading_core.domain.enums import AssetClass, Venue
from trading_core.domain.models import Instrument

router = APIRouter(prefix="/api/market-data", tags=["market-data"])


@router.get("/candles")
def list_candles() -> list[dict[str, str]]:
    return []


class MoexBackfillRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    symbol: str
    instrument_id: str
    interval: str = "1m"
    from_date: date = Field(alias="from")
    to_date: date = Field(alias="to")
    storage: str = "in-memory"
    dry_run: bool = True
    allow_network: bool = False


class MoexBackfillResponse(BaseModel):
    status: str
    candles_loaded: int
    candles_saved: int
    dry_run: bool
    warnings: list[str]


@router.post("/backfill/moex")
async def backfill_moex(request_body: MoexBackfillRequest, request: Request) -> MoexBackfillResponse:
    warnings: list[str] = []
    if not request_body.allow_network:
        warnings.append("external network is disabled by default; pass allow_network=true explicitly")
        return MoexBackfillResponse(
            status="skipped",
            candles_loaded=0,
            candles_saved=0,
            dry_run=request_body.dry_run,
            warnings=warnings,
        )

    adapter = getattr(request.app.state, "moex_market_data_adapter", MoexIssMarketDataAdapter())
    instrument = _moex_instrument(request_body.symbol, request_body.instrument_id)
    start = datetime.combine(request_body.from_date, time.min, tzinfo=UTC)
    end = datetime.combine(request_body.to_date, time.min, tzinfo=UTC)
    candles = await adapter.get_historical_candles(instrument, request_body.interval, start, end)
    candles_saved = 0
    if not request_body.dry_run:
        storage = getattr(request.app.state, "storage", InMemoryStorage())
        storage.save_candles(candles)
        candles_saved = len(candles)
    return MoexBackfillResponse(
        status="dry_run" if request_body.dry_run else "saved",
        candles_loaded=len(candles),
        candles_saved=candles_saved,
        dry_run=request_body.dry_run,
        warnings=warnings,
    )


def _moex_instrument(symbol: str, instrument_id: str) -> Instrument:
    return Instrument(
        id=instrument_id,
        venue=Venue.MOEX,
        asset_class=AssetClass.FUTURES,
        native_symbol=symbol,
        canonical_symbol=f"MOEX:{symbol}",
        name=symbol,
        lot_size=Decimal("1"),
        tick_size=Decimal("1"),
        tick_value=Decimal("1"),
        currency="RUB",
    )
