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

    def save_system_event(self, event: SystemEvent) -> None: ...

    def save_audit_log(self, audit_log: AuditLog) -> None: ...
