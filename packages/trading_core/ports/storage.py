from datetime import datetime
from typing import Protocol

from trading_core.domain.enums import AssetClass, Venue
from trading_core.domain.models import (
    AuditLog,
    BacktestRun,
    Candle,
    ContractSpec,
    Execution,
    Instrument,
    Order,
    OrderIntent,
    Position,
    RiskDecision,
    Signal,
    SystemEvent,
    TradeJournalEntry,
)
from trading_core.research.models import (
    BacktestEquityPoint,
    BacktestTradeRecord,
    ResearchBacktestResult,
    ResearchRun,
    ResearchStatus,
)


class StoragePort(Protocol):
    def save_instrument(self, instrument: Instrument) -> None: ...

    def save_instruments(self, instruments: list[Instrument]) -> None: ...

    def get_instrument(self, instrument_id: str) -> Instrument | None: ...

    def get_instrument_by_canonical_symbol(self, canonical_symbol: str) -> Instrument | None: ...

    def list_instruments(
        self,
        venue: Venue | None = None,
        asset_class: AssetClass | None = None,
        is_active: bool | None = None,
    ) -> list[Instrument]: ...

    def save_contract_spec(self, contract_spec: ContractSpec) -> None: ...

    def get_contract_spec(self, instrument_id: str) -> ContractSpec | None: ...

    def save_candles(self, candles: list[Candle]) -> None: ...

    def load_candles(
        self,
        instrument_id: str,
        interval: str,
        start: datetime,
        end: datetime,
    ) -> list[Candle]: ...

    def save_signal(self, signal: Signal) -> None: ...

    def save_order_intent(self, order_intent: OrderIntent) -> None: ...

    def save_risk_decision(self, risk_decision: RiskDecision) -> None: ...

    def save_order(self, order: Order) -> None: ...

    def save_execution(self, execution: Execution) -> None: ...

    def save_position(self, position: Position) -> None: ...

    def save_journal_entry(self, entry: TradeJournalEntry) -> None: ...

    def save_backtest_run(self, run: BacktestRun) -> None: ...

    def save_research_run(self, run: ResearchRun) -> None: ...

    def get_research_run(self, run_id: str) -> ResearchRun | None: ...

    def list_research_runs(
        self,
        strategy_id: str | None = None,
        canonical_symbol: str | None = None,
        status: ResearchStatus | None = None,
    ) -> list[ResearchRun]: ...

    def save_research_backtest_result(self, result: ResearchBacktestResult) -> None: ...

    def list_research_backtest_results(self, research_run_id: str) -> list[ResearchBacktestResult]: ...

    def get_research_backtest_result(self, result_id: str) -> ResearchBacktestResult | None: ...

    def save_backtest_equity_points(self, points: list[BacktestEquityPoint]) -> None: ...

    def load_backtest_equity_points(self, backtest_run_id: str) -> list[BacktestEquityPoint]: ...

    def save_backtest_trade_records(self, records: list[BacktestTradeRecord]) -> None: ...

    def load_backtest_trade_records(self, backtest_run_id: str) -> list[BacktestTradeRecord]: ...

    def save_system_event(self, event: SystemEvent) -> None: ...

    def save_audit_log(self, audit_log: AuditLog) -> None: ...
