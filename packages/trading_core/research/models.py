from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import Field

from trading_core.domain.enums import Side
from trading_core.domain.models import DomainModel, new_id, utc_now


class ResearchStatus(StrEnum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"


class ResearchRun(DomainModel):
    id: str = Field(default_factory=new_id)
    strategy_id: str
    canonical_symbol: str
    instrument_id: str
    interval: str
    start: datetime
    end: datetime
    parameter_grid: dict[str, Any]
    data_quality_gate: dict[str, Any]
    status: ResearchStatus = ResearchStatus.CREATED
    created_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None
    notes: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResearchBacktestResult(DomainModel):
    id: str = Field(default_factory=new_id)
    research_run_id: str
    backtest_run_id: str | None = None
    strategy_id: str
    canonical_symbol: str
    instrument_id: str
    interval: str
    start: datetime
    end: datetime
    params: dict[str, Any]
    metrics: dict[str, Any]
    quality_report: dict[str, Any]
    status: ResearchStatus
    error_message: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class BacktestEquityPoint(DomainModel):
    id: str = Field(default_factory=new_id)
    backtest_run_id: str
    ts: datetime
    equity: Decimal
    drawdown: Decimal = Decimal("0")


class BacktestTradeRecord(DomainModel):
    id: str = Field(default_factory=new_id)
    backtest_run_id: str
    instrument_id: str
    side: Side
    entry_ts: datetime | None = None
    exit_ts: datetime | None = None
    entry_price: Decimal | None = None
    exit_price: Decimal | None = None
    qty: Decimal
    gross_pnl: Decimal
    net_pnl: Decimal
    r_multiple: Decimal | None = None
    reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResearchComparison(DomainModel):
    research_run_id: str
    rows: list[dict[str, Any]]
    best_by_profit_factor: dict[str, Any] | None = None
    best_by_expectancy: dict[str, Any] | None = None
    best_by_max_drawdown: dict[str, Any] | None = None
    warnings: list[str] = Field(default_factory=list)


class ResearchRunSummary(DomainModel):
    research_run_id: str
    strategy_id: str
    canonical_symbol: str
    interval: str
    start: datetime
    end: datetime
    parameter_combinations: int
    completed_backtests: int
    failed_backtests: int
    best_result_by_profit_factor: dict[str, Any] | None = None
    best_result_by_expectancy: dict[str, Any] | None = None
    warnings: list[str] = Field(default_factory=list)


class StrategyMetadata(DomainModel):
    strategy_id: str
    class_name: str
    default_params: dict[str, Any]
    supported_params: list[str]
    description: str


class WalkForwardSplit(DomainModel):
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
