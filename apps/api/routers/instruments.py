from typing import cast

from adapters.moex_iss.instruments import MoexIssInstrumentsService
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from storage.in_memory import InMemoryStorage
from trading_core.domain.enums import AssetClass, Venue
from trading_core.domain.models import ContractSpec, DomainModel, Instrument
from trading_core.ports.storage import StoragePort

router = APIRouter(prefix="/api/instruments", tags=["instruments"])


@router.get("")
def list_instruments(
    request: Request,
    venue: Venue | None = Query(None),
    asset_class: AssetClass | None = Query(None),
    is_active: bool | None = Query(None),
) -> list[dict[str, object]]:
    storage = _storage(request)
    return [
        _model_json(instrument)
        for instrument in storage.list_instruments(venue=venue, asset_class=asset_class, is_active=is_active)
    ]


@router.get("/by-symbol/{canonical_symbol}")
def get_instrument_by_symbol(canonical_symbol: str, request: Request) -> dict[str, object]:
    storage = _storage(request)
    instrument = storage.get_instrument_by_canonical_symbol(canonical_symbol)
    if instrument is None:
        raise HTTPException(status_code=404, detail="instrument not found")
    return _instrument_detail(storage, instrument)


@router.get("/{instrument_id}")
def get_instrument(instrument_id: str, request: Request) -> dict[str, object]:
    storage = _storage(request)
    instrument = storage.get_instrument(instrument_id)
    if instrument is None:
        raise HTTPException(status_code=404, detail="instrument not found")
    return _instrument_detail(storage, instrument)


class MoexInstrumentSyncRequest(BaseModel):
    asset_class: str = "futures"
    storage: str = "in-memory"
    dry_run: bool = True
    allow_network: bool = False


class MoexInstrumentSyncResponse(BaseModel):
    status: str
    instruments_count: int
    contract_specs_count: int
    dry_run: bool
    allow_network: bool
    warnings: list[str]


@router.post("/sync/moex")
async def sync_moex_instruments(
    request_body: MoexInstrumentSyncRequest,
    request: Request,
) -> MoexInstrumentSyncResponse:
    if request_body.asset_class != "futures":
        raise HTTPException(status_code=400, detail="only futures instruments are supported for MOEX sync")

    warnings: list[str] = []
    if not request_body.allow_network:
        warnings.append("external network is disabled by default; pass allow_network=true explicitly")
        return MoexInstrumentSyncResponse(
            status="skipped",
            instruments_count=0,
            contract_specs_count=0,
            dry_run=request_body.dry_run,
            allow_network=request_body.allow_network,
            warnings=warnings,
        )

    service = _moex_instruments_service(request)
    if request_body.dry_run:
        instruments = await service.get_futures_instruments()
        contract_specs = await service.get_futures_contract_specs()
        return MoexInstrumentSyncResponse(
            status="dry_run",
            instruments_count=len(instruments),
            contract_specs_count=len(contract_specs),
            dry_run=request_body.dry_run,
            allow_network=request_body.allow_network,
            warnings=warnings,
        )

    sync_result = await service.sync_futures_instruments(_storage(request))
    return MoexInstrumentSyncResponse(
        status="saved",
        instruments_count=sync_result.instruments_count,
        contract_specs_count=sync_result.contract_specs_count,
        dry_run=request_body.dry_run,
        allow_network=request_body.allow_network,
        warnings=warnings,
    )


def _storage(request: Request) -> StoragePort:
    if not hasattr(request.app.state, "storage"):
        request.app.state.storage = InMemoryStorage()
    return cast(StoragePort, request.app.state.storage)


def _moex_instruments_service(request: Request) -> MoexIssInstrumentsService:
    if not hasattr(request.app.state, "moex_instruments_service"):
        request.app.state.moex_instruments_service = MoexIssInstrumentsService()
    return cast(MoexIssInstrumentsService, request.app.state.moex_instruments_service)


def _instrument_detail(storage: StoragePort, instrument: Instrument) -> dict[str, object]:
    contract_spec = storage.get_contract_spec(instrument.id)
    return {
        "instrument": _model_json(instrument),
        "contract_spec": _contract_spec_json(contract_spec),
    }


def _model_json(model: DomainModel) -> dict[str, object]:
    payload = model.model_dump(mode="json")
    return payload if isinstance(payload, dict) else {}


def _contract_spec_json(contract_spec: ContractSpec | None) -> dict[str, object] | None:
    return _model_json(contract_spec) if contract_spec is not None else None
