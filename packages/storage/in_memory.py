from dataclasses import dataclass, field
from datetime import datetime

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


@dataclass
class InMemoryStorage:
    candles: list[Candle] = field(default_factory=list)
    signals: list[Signal] = field(default_factory=list)
    order_intents: list[OrderIntent] = field(default_factory=list)
    risk_decisions: list[RiskDecision] = field(default_factory=list)
    orders: list[Order] = field(default_factory=list)
    executions: list[Execution] = field(default_factory=list)
    positions: list[Position] = field(default_factory=list)
    journal_entries: list[TradeJournalEntry] = field(default_factory=list)
    backtest_runs: list[BacktestRun] = field(default_factory=list)
    system_events: list[SystemEvent] = field(default_factory=list)
    audit_logs: list[AuditLog] = field(default_factory=list)

    def save_candles(self, candles: list[Candle]) -> None:
        self.candles.extend(candles)

    def load_candles(self, instrument_id: str, interval: str, start: datetime, end: datetime) -> list[Candle]:
        return [
            candle
            for candle in self.candles
            if candle.instrument_id == instrument_id
            and candle.interval == interval
            and start <= candle.ts_start <= end
        ]

    def save_signal(self, signal: Signal) -> None:
        self.signals.append(signal)

    def save_order_intent(self, order_intent: OrderIntent) -> None:
        self.order_intents.append(order_intent)

    def save_risk_decision(self, risk_decision: RiskDecision) -> None:
        self.risk_decisions.append(risk_decision)

    def save_order(self, order: Order) -> None:
        self.orders.append(order)

    def save_execution(self, execution: Execution) -> None:
        self.executions.append(execution)

    def save_position(self, position: Position) -> None:
        self.positions.append(position)

    def save_journal_entry(self, entry: TradeJournalEntry) -> None:
        self.journal_entries.append(entry)

    def save_backtest_run(self, run: BacktestRun) -> None:
        self.backtest_runs.append(run)

    def save_system_event(self, event: SystemEvent) -> None:
        self.system_events.append(event)

    def save_audit_log(self, audit_log: AuditLog) -> None:
        self.audit_logs.append(audit_log)
