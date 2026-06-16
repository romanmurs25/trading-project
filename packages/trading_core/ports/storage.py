from datetime import datetime
from typing import Protocol

from trading_core.domain.models import (
    AuditLog,
    BacktestRun,
    Candle,
    Execution,
    Order,
    OrderIntent,
    Position,
    RiskDecision,
    Signal,
    SystemEvent,
    TradeJournalEntry,
)


class StoragePort(Protocol):
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

    def save_system_event(self, event: SystemEvent) -> None: ...

    def save_audit_log(self, audit_log: AuditLog) -> None: ...
