from dataclasses import dataclass, field
from datetime import date, datetime

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
from trading_core.live_data.models import (
    LiveCandleSnapshot,
    MarketDataEvent,
    MarketDataIngestionRun,
    MarketDataIngestionStatus,
    MarketDataSource,
)
from trading_core.market.continuous import ContinuousSeries, ContinuousSeriesComponent
from trading_core.market.roll import RollEvent
from trading_core.market.sessions import MarketSession
from trading_core.research.models import (
    BacktestEquityPoint,
    BacktestTradeRecord,
    ResearchBacktestResult,
    ResearchRun,
    ResearchStatus,
)


@dataclass
class InMemoryStorage:
    instruments: list[Instrument] = field(default_factory=list)
    contract_specs: list[ContractSpec] = field(default_factory=list)
    candles: list[Candle] = field(default_factory=list)
    signals: list[Signal] = field(default_factory=list)
    order_intents: list[OrderIntent] = field(default_factory=list)
    risk_decisions: list[RiskDecision] = field(default_factory=list)
    orders: list[Order] = field(default_factory=list)
    executions: list[Execution] = field(default_factory=list)
    positions: list[Position] = field(default_factory=list)
    journal_entries: list[TradeJournalEntry] = field(default_factory=list)
    backtest_runs: list[BacktestRun] = field(default_factory=list)
    research_runs: list[ResearchRun] = field(default_factory=list)
    research_backtest_results: list[ResearchBacktestResult] = field(default_factory=list)
    backtest_equity_points: list[BacktestEquityPoint] = field(default_factory=list)
    backtest_trade_records: list[BacktestTradeRecord] = field(default_factory=list)
    market_sessions: list[MarketSession] = field(default_factory=list)
    continuous_series: list[ContinuousSeries] = field(default_factory=list)
    continuous_series_components: list[ContinuousSeriesComponent] = field(default_factory=list)
    roll_events: list[RollEvent] = field(default_factory=list)
    market_data_ingestion_runs: list[MarketDataIngestionRun] = field(default_factory=list)
    market_data_events: list[MarketDataEvent] = field(default_factory=list)
    live_candle_snapshots: list[LiveCandleSnapshot] = field(default_factory=list)
    system_events: list[SystemEvent] = field(default_factory=list)
    audit_logs: list[AuditLog] = field(default_factory=list)

    def save_instrument(self, instrument: Instrument) -> None:
        for index, existing in enumerate(self.instruments):
            if existing.id == instrument.id or existing.canonical_symbol == instrument.canonical_symbol:
                self.instruments[index] = instrument
                return
        self.instruments.append(instrument)

    def save_instruments(self, instruments: list[Instrument]) -> None:
        for instrument in instruments:
            self.save_instrument(instrument)

    def get_instrument(self, instrument_id: str) -> Instrument | None:
        return next((instrument for instrument in self.instruments if instrument.id == instrument_id), None)

    def get_instrument_by_canonical_symbol(self, canonical_symbol: str) -> Instrument | None:
        return next(
            (
                instrument
                for instrument in self.instruments
                if instrument.canonical_symbol == canonical_symbol
            ),
            None,
        )

    def list_instruments(
        self,
        venue: Venue | None = None,
        asset_class: AssetClass | None = None,
        is_active: bool | None = None,
    ) -> list[Instrument]:
        instruments = self.instruments
        if venue is not None:
            instruments = [instrument for instrument in instruments if instrument.venue == venue]
        if asset_class is not None:
            instruments = [instrument for instrument in instruments if instrument.asset_class == asset_class]
        if is_active is not None:
            instruments = [instrument for instrument in instruments if instrument.is_active is is_active]
        return sorted(instruments, key=lambda instrument: instrument.canonical_symbol)

    def save_contract_spec(self, contract_spec: ContractSpec) -> None:
        for index, existing in enumerate(self.contract_specs):
            if existing.instrument_id == contract_spec.instrument_id:
                self.contract_specs[index] = contract_spec
                return
        self.contract_specs.append(contract_spec)

    def get_contract_spec(self, instrument_id: str) -> ContractSpec | None:
        return next((spec for spec in self.contract_specs if spec.instrument_id == instrument_id), None)

    def save_candles(self, candles: list[Candle]) -> None:
        self.candles.extend(candles)

    def load_candles(self, instrument_id: str, interval: str, start: datetime, end: datetime) -> list[Candle]:
        return [
            candle
            for candle in self.candles
            if candle.instrument_id == instrument_id
            and candle.interval == interval
            and start <= candle.ts_start < end
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

    def save_research_run(self, run: ResearchRun) -> None:
        self.research_runs = [existing for existing in self.research_runs if existing.id != run.id]
        self.research_runs.append(run)

    def get_research_run(self, run_id: str) -> ResearchRun | None:
        return next((run for run in self.research_runs if run.id == run_id), None)

    def list_research_runs(
        self,
        strategy_id: str | None = None,
        canonical_symbol: str | None = None,
        status: ResearchStatus | None = None,
    ) -> list[ResearchRun]:
        runs = self.research_runs
        if strategy_id is not None:
            runs = [run for run in runs if run.strategy_id == strategy_id]
        if canonical_symbol is not None:
            runs = [run for run in runs if run.canonical_symbol == canonical_symbol]
        if status is not None:
            runs = [run for run in runs if run.status == status]
        return sorted(runs, key=lambda run: run.created_at)

    def save_research_backtest_result(self, result: ResearchBacktestResult) -> None:
        self.research_backtest_results = [
            existing for existing in self.research_backtest_results if existing.id != result.id
        ]
        self.research_backtest_results.append(result)

    def list_research_backtest_results(self, research_run_id: str) -> list[ResearchBacktestResult]:
        return [
            result
            for result in self.research_backtest_results
            if result.research_run_id == research_run_id
        ]

    def get_research_backtest_result(self, result_id: str) -> ResearchBacktestResult | None:
        return next((result for result in self.research_backtest_results if result.id == result_id), None)

    def save_backtest_equity_points(self, points: list[BacktestEquityPoint]) -> None:
        point_ids = {point.id for point in points}
        self.backtest_equity_points = [
            point for point in self.backtest_equity_points if point.id not in point_ids
        ]
        self.backtest_equity_points.extend(points)

    def load_backtest_equity_points(self, backtest_run_id: str) -> list[BacktestEquityPoint]:
        return sorted(
            (point for point in self.backtest_equity_points if point.backtest_run_id == backtest_run_id),
            key=lambda point: point.ts,
        )

    def save_backtest_trade_records(self, records: list[BacktestTradeRecord]) -> None:
        record_ids = {record.id for record in records}
        self.backtest_trade_records = [
            record for record in self.backtest_trade_records if record.id not in record_ids
        ]
        self.backtest_trade_records.extend(records)

    def load_backtest_trade_records(self, backtest_run_id: str) -> list[BacktestTradeRecord]:
        return [
            record for record in self.backtest_trade_records if record.backtest_run_id == backtest_run_id
        ]

    def save_market_sessions(self, sessions: list[MarketSession]) -> None:
        session_ids = {session.id for session in sessions}
        self.market_sessions = [session for session in self.market_sessions if session.id not in session_ids]
        self.market_sessions.extend(sessions)

    def load_market_sessions(
        self,
        venue: Venue | None = None,
        market: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[MarketSession]:
        sessions = self.market_sessions
        if venue is not None:
            sessions = [session for session in sessions if session.venue == venue]
        if market is not None:
            sessions = [session for session in sessions if session.market == market]
        if start is not None:
            sessions = [session for session in sessions if session.end > start]
        if end is not None:
            sessions = [session for session in sessions if session.start < end]
        return sorted(sessions, key=lambda session: session.start)

    def save_continuous_series(self, series: ContinuousSeries) -> None:
        self.continuous_series = [
            existing
            for existing in self.continuous_series
            if existing.id != series.id and existing.canonical_symbol != series.canonical_symbol
        ]
        self.continuous_series.append(series)

    def get_continuous_series(self, series_id: str) -> ContinuousSeries | None:
        return next((series for series in self.continuous_series if series.id == series_id), None)

    def get_continuous_series_by_canonical_symbol(self, canonical_symbol: str) -> ContinuousSeries | None:
        return next(
            (series for series in self.continuous_series if series.canonical_symbol == canonical_symbol),
            None,
        )

    def list_continuous_series(
        self,
        underlying_symbol: str | None = None,
        interval: str | None = None,
    ) -> list[ContinuousSeries]:
        series = self.continuous_series
        if underlying_symbol is not None:
            series = [item for item in series if item.underlying_symbol == underlying_symbol]
        if interval is not None:
            series = [item for item in series if item.interval == interval]
        return sorted(series, key=lambda item: (item.underlying_symbol, item.interval, item.start))

    def save_continuous_series_components(self, components: list[ContinuousSeriesComponent]) -> None:
        component_ids = {component.id for component in components}
        self.continuous_series_components = [
            component for component in self.continuous_series_components if component.id not in component_ids
        ]
        self.continuous_series_components.extend(components)

    def load_continuous_series_components(self, series_id: str) -> list[ContinuousSeriesComponent]:
        return sorted(
            (
                component
                for component in self.continuous_series_components
                if component.continuous_series_id == series_id
            ),
            key=lambda component: component.start,
        )

    def save_roll_events(self, events: list[RollEvent]) -> None:
        event_ids = {event.id for event in events}
        self.roll_events = [event for event in self.roll_events if event.id not in event_ids]
        self.roll_events.extend(events)

    def load_roll_events(
        self,
        underlying_symbol: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[RollEvent]:
        events = self.roll_events
        if underlying_symbol is not None:
            events = [event for event in events if event.underlying_symbol == underlying_symbol]
        if start_date is not None:
            events = [event for event in events if event.roll_date >= start_date]
        if end_date is not None:
            events = [event for event in events if event.roll_date < end_date]
        return sorted(events, key=lambda event: event.roll_date)

    def save_market_data_ingestion_run(self, run: MarketDataIngestionRun) -> None:
        self.market_data_ingestion_runs = [
            existing for existing in self.market_data_ingestion_runs if existing.id != run.id
        ]
        self.market_data_ingestion_runs.append(run)

    def get_market_data_ingestion_run(self, run_id: str) -> MarketDataIngestionRun | None:
        return next((run for run in self.market_data_ingestion_runs if run.id == run_id), None)

    def list_market_data_ingestion_runs(
        self,
        source: MarketDataSource | None = None,
        status: MarketDataIngestionStatus | None = None,
        limit: int = 100,
    ) -> list[MarketDataIngestionRun]:
        runs = self.market_data_ingestion_runs
        if source is not None:
            runs = [run for run in runs if run.source == source]
        if status is not None:
            runs = [run for run in runs if run.status == status]
        return sorted(runs, key=lambda run: run.started_at, reverse=True)[:limit]

    def save_market_data_event(self, event: MarketDataEvent) -> None:
        self.market_data_events.append(event)

    def save_market_data_events(self, events: list[MarketDataEvent]) -> None:
        self.market_data_events.extend(events)

    def list_market_data_events(
        self,
        source: MarketDataSource | None = None,
        instrument_id: str | None = None,
        canonical_symbol: str | None = None,
        interval: str | None = None,
        limit: int = 500,
    ) -> list[MarketDataEvent]:
        events = self.market_data_events
        if source is not None:
            events = [event for event in events if event.source == source]
        if instrument_id is not None:
            events = [event for event in events if event.instrument_id == instrument_id]
        if canonical_symbol is not None:
            events = [event for event in events if event.canonical_symbol == canonical_symbol]
        if interval is not None:
            events = [event for event in events if event.interval == interval]
        return sorted(events, key=lambda event: event.received_at, reverse=True)[:limit]

    def save_live_candle_snapshot(self, snapshot: LiveCandleSnapshot) -> None:
        key = _live_candle_snapshot_key(snapshot)
        self.live_candle_snapshots = [
            existing
            for existing in self.live_candle_snapshots
            if _live_candle_snapshot_key(existing) != key
        ]
        self.live_candle_snapshots.append(snapshot)

    def save_live_candle_snapshots(self, snapshots: list[LiveCandleSnapshot]) -> None:
        for snapshot in snapshots:
            self.save_live_candle_snapshot(snapshot)

    def list_live_candle_snapshots(
        self,
        source: MarketDataSource | None = None,
        instrument_id: str | None = None,
        canonical_symbol: str | None = None,
        interval: str | None = None,
        limit: int = 500,
    ) -> list[LiveCandleSnapshot]:
        snapshots = self.live_candle_snapshots
        if source is not None:
            snapshots = [snapshot for snapshot in snapshots if snapshot.source == source]
        if instrument_id is not None:
            snapshots = [snapshot for snapshot in snapshots if snapshot.instrument_id == instrument_id]
        if canonical_symbol is not None:
            snapshots = [snapshot for snapshot in snapshots if snapshot.canonical_symbol == canonical_symbol]
        if interval is not None:
            snapshots = [snapshot for snapshot in snapshots if snapshot.interval == interval]
        return sorted(snapshots, key=lambda snapshot: (snapshot.ts_start, snapshot.updated_at), reverse=True)[
            :limit
        ]

    def get_latest_live_candle_snapshot(
        self,
        canonical_symbol: str,
        interval: str,
    ) -> LiveCandleSnapshot | None:
        snapshots = self.list_live_candle_snapshots(
            canonical_symbol=canonical_symbol,
            interval=interval,
            limit=1,
        )
        return snapshots[0] if snapshots else None

    def save_system_event(self, event: SystemEvent) -> None:
        self.system_events.append(event)

    def save_audit_log(self, audit_log: AuditLog) -> None:
        self.audit_logs.append(audit_log)


def _live_candle_snapshot_key(snapshot: LiveCandleSnapshot) -> tuple[str, str, str, str, datetime]:
    return (
        snapshot.source.value,
        snapshot.venue.value,
        snapshot.instrument_id,
        snapshot.interval,
        snapshot.ts_start,
    )
