from datetime import UTC, date, datetime, time
from decimal import Decimal, InvalidOperation
from typing import Any, cast

from adapters.paper.broker import PaperBroker
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from storage.in_memory import InMemoryStorage
from trading_core.domain.errors import DataValidationError
from trading_core.ports.storage import StoragePort
from trading_core.research.data_quality_gate import DataQualityGateConfig
from trading_core.research.models import ResearchRun
from trading_core.research.reporting import build_research_report
from trading_core.research.runner import ResearchRunner

router = APIRouter(prefix="/api/research", tags=["research"])


class ResearchRunRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    strategy_id: str
    canonical_symbol: str
    interval: str = "1m"
    from_date: date = Field(alias="from")
    to_date: date = Field(alias="to")
    parameter_grid: dict[str, list[Any]] = Field(default_factory=dict)
    initial_cash: str = "100000"
    fail_on_data_quality: bool = True
    max_combinations: int = 500


@router.post("/run")
def run_research(request_body: ResearchRunRequest, request: Request) -> dict[str, object]:
    runner = ResearchRunner(
        storage=_storage(request),
        broker_factory=lambda cash: PaperBroker(initial_cash=cash),
    )
    try:
        summary = runner.run(
            strategy_id=request_body.strategy_id,
            canonical_symbol=request_body.canonical_symbol,
            interval=request_body.interval,
            start=_date_start(request_body.from_date),
            end=_date_start(request_body.to_date),
            parameter_grid=request_body.parameter_grid,
            initial_cash=_decimal(request_body.initial_cash),
            data_quality_gate_config=_gate_config(request_body.fail_on_data_quality),
            max_combinations=request_body.max_combinations,
        )
    except DataValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _model_json(summary)


@router.get("/runs")
def list_research_runs(
    request: Request,
    strategy_id: str | None = Query(None),
    canonical_symbol: str | None = Query(None),
) -> list[dict[str, object]]:
    return [
        _model_json(run)
        for run in _storage(request).list_research_runs(
            strategy_id=strategy_id,
            canonical_symbol=canonical_symbol,
        )
    ]


@router.get("/runs/{run_id}")
def get_research_run(run_id: str, request: Request) -> dict[str, object]:
    run = _storage(request).get_research_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="research run not found")
    return _model_json(run)


@router.get("/runs/{run_id}/results")
def list_research_results(run_id: str, request: Request) -> list[dict[str, object]]:
    _require_run(run_id, request)
    return [_model_json(result) for result in _storage(request).list_research_backtest_results(run_id)]


@router.get("/runs/{run_id}/report")
def get_research_report(run_id: str, request: Request) -> dict[str, object]:
    run = _require_run(run_id, request)
    report = build_research_report(run, _storage(request).list_research_backtest_results(run_id))
    if not isinstance(report, dict):
        raise HTTPException(status_code=500, detail="unexpected report format")
    return report


@router.get("/runs/{run_id}/compare")
def compare_research_results(
    run_id: str,
    request: Request,
    sort_by: str = Query("profit_factor"),
) -> dict[str, object]:
    _require_run(run_id, request)
    rows = [_result_row(result) for result in _storage(request).list_research_backtest_results(run_id)]
    reverse = sort_by != "max_drawdown"
    rows.sort(key=lambda row: _metric_decimal(row, sort_by), reverse=reverse)
    return {
        "research_run_id": run_id,
        "sort_by": sort_by,
        "rows": rows,
        "best_row": rows[0] if rows else None,
        "warnings": [] if rows else ["no research results found"],
    }


@router.get("/runs/{run_id}/equity")
def get_research_equity(run_id: str, request: Request) -> dict[str, object]:
    _require_run(run_id, request)
    storage = _storage(request)
    points = [
        point
        for result in storage.list_research_backtest_results(run_id)
        if result.backtest_run_id is not None
        for point in storage.load_backtest_equity_points(result.backtest_run_id)
    ]
    points.sort(key=lambda point: (point.backtest_run_id, point.ts))
    return {
        "research_run_id": run_id,
        "points": [_model_json(point) for point in points],
    }


@router.get("/runs/{run_id}/trades")
def get_research_trades(run_id: str, request: Request) -> dict[str, object]:
    _require_run(run_id, request)
    storage = _storage(request)
    trades = [
        trade
        for result in storage.list_research_backtest_results(run_id)
        if result.backtest_run_id is not None
        for trade in storage.load_backtest_trade_records(result.backtest_run_id)
    ]
    trades.sort(key=lambda trade: (trade.backtest_run_id, trade.entry_ts or datetime.min.replace(tzinfo=UTC)))
    return {
        "research_run_id": run_id,
        "trades": [_model_json(trade) for trade in trades],
    }


def _storage(request: Request) -> StoragePort:
    if not hasattr(request.app.state, "storage"):
        request.app.state.storage = InMemoryStorage()
    return cast(StoragePort, request.app.state.storage)


def _require_run(run_id: str, request: Request) -> ResearchRun:
    run = _storage(request).get_research_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="research run not found")
    return run


def _date_start(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=UTC)


def _decimal(value: str) -> Decimal:
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise HTTPException(status_code=400, detail="initial_cash must be Decimal-compatible") from exc


def _gate_config(fail_on_data_quality: bool) -> DataQualityGateConfig:
    if fail_on_data_quality:
        return DataQualityGateConfig()
    return DataQualityGateConfig(
        fail_on_no_candles=False,
        max_duplicates_count=1_000_000,
        max_missing_intervals_count=1_000_000,
        max_zero_volume_count=None,
        allow_non_monotonic=True,
    )


def _model_json(model: Any) -> dict[str, object]:
    payload = model.model_dump(mode="json")
    return payload if isinstance(payload, dict) else {}


def _result_row(result: Any) -> dict[str, object]:
    payload = _model_json(result)
    return {
        "id": payload["id"],
        "backtest_run_id": payload["backtest_run_id"],
        "status": payload["status"],
        "params": payload["params"],
        "metrics": payload["metrics"],
        "error_message": payload["error_message"],
    }


def _metric_decimal(row: dict[str, object], metric_name: str) -> Decimal:
    metrics = row.get("metrics", {})
    if not isinstance(metrics, dict):
        return Decimal("0")
    try:
        return Decimal(str(metrics.get(metric_name, "0")))
    except (InvalidOperation, ValueError):
        return Decimal("0")
