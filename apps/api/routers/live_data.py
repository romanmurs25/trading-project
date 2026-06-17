from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast

from adapters.demo.live_replay import replay_demo_candles_once
from adapters.moex_iss.live_polling import MoexIssPollingMarketDataAdapter
from adapters.moex_iss.market_data_adapter import MoexIssMarketDataAdapter
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from storage.in_memory import InMemoryStorage
from trading_core.domain.enums import AssetClass, Venue
from trading_core.domain.errors import DataValidationError
from trading_core.domain.models import DomainModel, Instrument
from trading_core.live_data.ingestion import ReadOnlyMarketDataIngestionService
from trading_core.live_data.models import MarketDataIngestionStatus, MarketDataSource
from trading_core.ports.storage import StoragePort

router = APIRouter(prefix="/api/live-data", tags=["live-data"])


class DemoReplayRequest(BaseModel):
    canonical_symbol: str = "MOEX:SiH6"
    interval: str = "1m"
    count: int = 20


class PollMoexOnceRequest(BaseModel):
    symbol: str | None = None
    instrument_id: str | None = None
    canonical_symbol: str | None = None
    interval: str = "1m"
    lookback_minutes: int = 5
    dry_run: bool = True
    allow_network: bool = False


@router.get("/state")
def live_data_state(request: Request) -> dict[str, object]:
    return _model_json(ReadOnlyMarketDataIngestionService(storage=_storage(request)).state())


@router.get("/events")
def live_data_events(
    request: Request,
    source: MarketDataSource | None = Query(None),
    canonical_symbol: str | None = Query(None),
    interval: str | None = Query(None),
    limit: int = Query(100),
) -> dict[str, object]:
    events = _storage(request).list_market_data_events(
        source=source,
        canonical_symbol=canonical_symbol,
        interval=interval,
        limit=limit,
    )
    return {"events": [_model_json(event) for event in events]}


@router.get("/candles")
def live_data_candles(
    request: Request,
    source: MarketDataSource | None = Query(None),
    canonical_symbol: str | None = Query(None),
    interval: str | None = Query(None),
    limit: int = Query(100),
) -> dict[str, object]:
    service = ReadOnlyMarketDataIngestionService(storage=_storage(request))
    snapshots = _storage(request).list_live_candle_snapshots(
        source=source,
        canonical_symbol=canonical_symbol,
        interval=interval,
        limit=limit,
    )
    return {"candles": [_model_json(service.with_current_freshness(snapshot)) for snapshot in snapshots]}


@router.post("/replay-demo")
def live_data_replay_demo(request_body: DemoReplayRequest, request: Request) -> dict[str, object]:
    result = replay_demo_candles_once(
        storage=_storage(request),
        canonical_symbol=request_body.canonical_symbol,
        interval=request_body.interval,
        count=request_body.count,
    )
    return {
        "status": "saved",
        "source": result.run.source.value,
        "run_id": result.run.id,
        "read_only": result.run.read_only,
        "allow_network": result.run.allow_network,
        "snapshots_count": len(result.snapshots),
        "latest_snapshot": _model_json(result.snapshots[0]) if result.snapshots else None,
    }


@router.post("/poll/moex-once")
async def live_data_poll_moex_once(
    request_body: PollMoexOnceRequest,
    request: Request,
) -> dict[str, object]:
    warnings: list[str] = []
    instrument = _resolve_moex_instrument(request_body, _storage(request))
    if not request_body.allow_network:
        warnings.append("external network is disabled by default; pass allow_network=true explicitly")
        return {
            "status": "skipped",
            "source": MarketDataSource.MOEX_ISS_POLLING.value,
            "canonical_symbol": instrument.canonical_symbol,
            "interval": request_body.interval,
            "lookback_minutes": request_body.lookback_minutes,
            "dry_run": request_body.dry_run,
            "allow_network": request_body.allow_network,
            "candles_loaded": 0,
            "candles_saved": 0,
            "warnings": warnings,
        }

    adapter = _moex_polling_adapter(request)
    try:
        candles = await adapter.poll_latest_candles_once(
            instrument=instrument,
            interval=request_body.interval,
            end=datetime.now(UTC),
            lookback_minutes=request_body.lookback_minutes,
        )
    except DataValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    candles_saved = 0
    if not request_body.dry_run:
        service = ReadOnlyMarketDataIngestionService(storage=_storage(request))
        run = service.start_run(
            source=MarketDataSource.MOEX_ISS_POLLING,
            venue=instrument.venue,
            instruments=[instrument.canonical_symbol],
            interval=request_body.interval,
            allow_network=True,
            metadata={"source": "moex-iss-polling-once"},
        )
        service.ingest_candles(
            run_id=run.id,
            source=MarketDataSource.MOEX_ISS_POLLING,
            instrument=instrument,
            candles=candles,
        )
        service.stop_run(run.id, status=MarketDataIngestionStatus.STOPPED)
        candles_saved = len(candles)
    return {
        "status": "dry_run" if request_body.dry_run else "saved",
        "source": MarketDataSource.MOEX_ISS_POLLING.value,
        "canonical_symbol": instrument.canonical_symbol,
        "interval": request_body.interval,
        "lookback_minutes": request_body.lookback_minutes,
        "dry_run": request_body.dry_run,
        "allow_network": request_body.allow_network,
        "candles_loaded": len(candles),
        "candles_saved": candles_saved,
        "warnings": warnings,
    }


def _storage(request: Request) -> StoragePort:
    if not hasattr(request.app.state, "storage"):
        request.app.state.storage = InMemoryStorage()
    return cast(StoragePort, request.app.state.storage)


def _moex_polling_adapter(request: Request) -> MoexIssPollingMarketDataAdapter:
    if not hasattr(request.app.state, "moex_polling_adapter"):
        request.app.state.moex_polling_adapter = MoexIssPollingMarketDataAdapter(MoexIssMarketDataAdapter())
    return cast(MoexIssPollingMarketDataAdapter, request.app.state.moex_polling_adapter)


def _resolve_moex_instrument(request_body: PollMoexOnceRequest, storage: StoragePort) -> Instrument:
    if request_body.canonical_symbol is not None:
        instrument = storage.get_instrument_by_canonical_symbol(request_body.canonical_symbol)
        if instrument is None:
            raise HTTPException(status_code=404, detail="instrument not found")
        return instrument
    if request_body.symbol is None or request_body.instrument_id is None:
        raise HTTPException(
            status_code=400,
            detail="pass either canonical_symbol or both symbol and instrument_id",
        )
    return Instrument(
        id=request_body.instrument_id,
        venue=Venue.MOEX,
        asset_class=AssetClass.FUTURES,
        native_symbol=request_body.symbol,
        canonical_symbol=f"MOEX:{request_body.symbol}",
        name=request_body.symbol,
        lot_size=Decimal("1"),
        tick_size=Decimal("1"),
        tick_value=Decimal("1"),
        currency="RUB",
    )


def _model_json(model: DomainModel) -> dict[str, object]:
    payload: Any = model.model_dump(mode="json")
    return payload if isinstance(payload, dict) else {}
