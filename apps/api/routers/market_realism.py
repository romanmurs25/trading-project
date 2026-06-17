from datetime import UTC, date, datetime, time
from typing import cast

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from storage.in_memory import InMemoryStorage
from trading_core.analytics.session_quality import analyze_candle_series_session_aware
from trading_core.domain.enums import AssetClass, Venue
from trading_core.domain.errors import DataValidationError
from trading_core.domain.models import DomainModel
from trading_core.market.calendar import MarketCalendarService
from trading_core.market.continuous import build_continuous_futures_series
from trading_core.market.moex_templates import default_moex_futures_session_templates
from trading_core.market.roll import ContractChain, RollRule, build_contract_chain, select_front_contract
from trading_core.market.sessions import SessionType
from trading_core.ports.storage import StoragePort

router = APIRouter(tags=["market-realism"])


class GenerateSessionsRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_date: date = Field(alias="from")
    to_date: date = Field(alias="to")
    venue: Venue = Venue.MOEX
    market: str = "forts"
    write: bool = False


class BuildContinuousRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    underlying: str
    interval: str = "1m"
    from_date: date = Field(alias="from")
    to_date: date = Field(alias="to")
    roll_days_before_expiry: int = 5
    write: bool = False


@router.get("/api/market/sessions")
def list_market_sessions(
    request: Request,
    venue: Venue | None = Query(None),
    market: str | None = Query(None),
) -> list[dict[str, object]]:
    sessions = _storage(request).load_market_sessions(venue=venue, market=market)
    return [_model_json(session) for session in sessions]


@router.post("/api/market/sessions/generate")
def generate_market_sessions(request_body: GenerateSessionsRequest, request: Request) -> dict[str, object]:
    calendar = _default_moex_calendar()
    sessions = [
        session
        for session in calendar.generate_sessions(
            _date_start(request_body.from_date),
            _date_start(request_body.to_date),
        )
        if session.venue == request_body.venue and session.market == request_body.market
    ]
    if request_body.write:
        _storage(request).save_market_sessions(sessions)
    return {
        "sessions_count": len(sessions),
        "trading_sessions_count": sum(1 for session in sessions if session.is_trading),
        "clearing_sessions_count": sum(
            1 for session in sessions if session.session_type == SessionType.CLEARING
        ),
        "written": request_body.write,
        "sessions": [_model_json(session) for session in sessions],
    }


@router.get("/api/data/quality/session-aware")
def data_quality_session_aware(
    request: Request,
    canonical_symbol: str = Query(...),
    interval: str = Query("1m"),
    from_date: date = Query(..., alias="from"),
    to_date: date = Query(..., alias="to"),
) -> dict[str, object]:
    storage = _storage(request)
    instrument = storage.get_instrument_by_canonical_symbol(canonical_symbol)
    if instrument is None:
        raise HTTPException(status_code=404, detail="instrument not found")
    start = _date_start(from_date)
    end = _date_start(to_date)
    report = analyze_candle_series_session_aware(
        storage.load_candles(instrument.id, interval, start, end),
        interval,
        _default_moex_calendar(),
        start,
        end,
    )
    return {
        "canonical_symbol": canonical_symbol,
        "instrument_id": instrument.id,
        "quality_mode": "session_aware",
        "report": _model_json(report),
    }


@router.get("/api/futures/chain")
def futures_chain(request: Request, underlying: str = Query(...)) -> dict[str, object]:
    try:
        chain = _contract_chain(_storage(request), underlying)
    except DataValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "underlying_symbol": underlying,
        "contracts": [_model_json(instrument) for instrument in chain.instruments],
    }


@router.get("/api/futures/select-front")
def futures_select_front(
    request: Request,
    underlying: str = Query(...),
    as_of: date = Query(...),
    roll_days_before_expiry: int = Query(5),
) -> dict[str, object]:
    try:
        decision = select_front_contract(
            _contract_chain(_storage(request), underlying),
            _date_start(as_of),
            RollRule(roll_days_before_expiry=roll_days_before_expiry),
        )
    except DataValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _model_json(decision)


@router.post("/api/data/continuous/build")
def data_build_continuous(request_body: BuildContinuousRequest, request: Request) -> dict[str, object]:
    storage = _storage(request)
    start = _date_start(request_body.from_date)
    end = _date_start(request_body.to_date)
    try:
        chain = _contract_chain(storage, request_body.underlying)
        candles_by_instrument = {
            instrument.id: storage.load_candles(instrument.id, request_body.interval, start, end)
            for instrument in chain.instruments
        }
        series, components, candles, events = build_continuous_futures_series(
            underlying_symbol=request_body.underlying,
            instruments=chain.instruments,
            contract_specs=chain.contract_specs,
            candles_by_instrument=candles_by_instrument,
            start=start,
            end=end,
            interval=request_body.interval,
            roll_rule=RollRule(roll_days_before_expiry=request_body.roll_days_before_expiry),
        )
    except DataValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if request_body.write:
        storage.save_continuous_series(series)
        storage.save_continuous_series_components(components)
        storage.save_roll_events(events)
        storage.save_candles(candles)
    return {
        "continuous_series_id": series.id,
        "canonical_symbol": series.canonical_symbol,
        "components_count": len(components),
        "candles_count": len(candles),
        "roll_events_count": len(events),
        "written": request_body.write,
        "warnings": series.metadata.get("warnings", []),
    }


@router.get("/api/continuous-series")
def list_continuous_series(
    request: Request,
    underlying_symbol: str | None = Query(None),
    interval: str | None = Query(None),
) -> list[dict[str, object]]:
    series = _storage(request).list_continuous_series(
        underlying_symbol=underlying_symbol,
        interval=interval,
    )
    return [_model_json(item) for item in series]


@router.get("/api/continuous-series/{series_id}/components")
def list_continuous_series_components(series_id: str, request: Request) -> dict[str, object]:
    storage = _storage(request)
    if storage.get_continuous_series(series_id) is None:
        raise HTTPException(status_code=404, detail="continuous series not found")
    return {
        "continuous_series_id": series_id,
        "components": [
            _model_json(component)
            for component in storage.load_continuous_series_components(series_id)
        ],
    }


@router.get("/api/roll-events")
def list_roll_events(
    request: Request,
    underlying_symbol: str | None = Query(None),
    from_date: date | None = Query(None, alias="from"),
    to_date: date | None = Query(None, alias="to"),
) -> list[dict[str, object]]:
    events = _storage(request).load_roll_events(
        underlying_symbol=underlying_symbol,
        start_date=from_date,
        end_date=to_date,
    )
    return [_model_json(event) for event in events]


def _storage(request: Request) -> StoragePort:
    if not hasattr(request.app.state, "storage"):
        request.app.state.storage = InMemoryStorage()
    return cast(StoragePort, request.app.state.storage)


def _default_moex_calendar() -> MarketCalendarService:
    return MarketCalendarService(default_moex_futures_session_templates())


def _contract_chain(storage: StoragePort, underlying: str) -> ContractChain:
    instruments = storage.list_instruments(venue=Venue.MOEX, asset_class=AssetClass.FUTURES)
    specs = [
        spec
        for instrument in instruments
        if (spec := storage.get_contract_spec(instrument.id)) is not None
    ]
    return build_contract_chain(instruments, specs, underlying)


def _date_start(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=UTC)


def _model_json(model: DomainModel) -> dict[str, object]:
    payload = model.model_dump(mode="json")
    return payload if isinstance(payload, dict) else {}
