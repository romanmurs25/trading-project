from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import Engine, create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from trading_core.domain.enums import AssetClass, Side, Venue
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
from trading_core.market.continuous import ContinuousSeries, ContinuousSeriesComponent
from trading_core.market.roll import RollEvent
from trading_core.market.sessions import MarketSession, SessionType
from trading_core.research.models import (
    BacktestEquityPoint,
    BacktestTradeRecord,
    ResearchBacktestResult,
    ResearchRun,
    ResearchStatus,
)

from storage.sqlalchemy_models import (
    AuditLogRow,
    BacktestEquityPointRow,
    BacktestRunRow,
    BacktestTradeRecordRow,
    CandleRow,
    ContinuousSeriesComponentRow,
    ContinuousSeriesRow,
    ContractSpecRow,
    ExecutionRow,
    InstrumentRow,
    MarketSessionRow,
    OrderIntentRow,
    OrderRow,
    PositionRow,
    ResearchBacktestResultRow,
    ResearchRunRow,
    RiskDecisionRow,
    RollEventRow,
    SignalRow,
    SystemEventRow,
)


@dataclass
class SQLAlchemyStorage:
    """Synchronous SQLAlchemy repository implementation for MVP persistence tests."""

    session_factory: sessionmaker[Session]

    @classmethod
    def from_url(cls, database_url: str) -> "SQLAlchemyStorage":
        engine = create_engine(database_url)
        return cls(sessionmaker(bind=engine))

    @classmethod
    def from_engine(cls, engine: Engine) -> "SQLAlchemyStorage":
        return cls(sessionmaker(bind=engine))

    def save_instrument(self, instrument: Instrument) -> None:
        with self.session_factory.begin() as session:
            existing = session.scalar(
                select(InstrumentRow).where(InstrumentRow.id == instrument.id)
            ) or session.scalar(
                select(InstrumentRow).where(InstrumentRow.canonical_symbol == instrument.canonical_symbol)
            )
            if existing is None:
                session.add(_instrument_row(instrument))
            else:
                _update_instrument_row(existing, instrument)

    def save_instruments(self, instruments: list[Instrument]) -> None:
        for instrument in instruments:
            self.save_instrument(instrument)

    def get_instrument(self, instrument_id: str) -> Instrument | None:
        with self.session_factory() as session:
            row = session.scalar(select(InstrumentRow).where(InstrumentRow.id == instrument_id))
            return _instrument_from_row(row) if row is not None else None

    def get_instrument_by_canonical_symbol(self, canonical_symbol: str) -> Instrument | None:
        with self.session_factory() as session:
            row = session.scalar(
                select(InstrumentRow).where(InstrumentRow.canonical_symbol == canonical_symbol)
            )
            return _instrument_from_row(row) if row is not None else None

    def list_instruments(
        self,
        venue: Venue | None = None,
        asset_class: AssetClass | None = None,
        is_active: bool | None = None,
    ) -> list[Instrument]:
        statement = select(InstrumentRow)
        if venue is not None:
            statement = statement.where(InstrumentRow.venue == venue.value)
        if asset_class is not None:
            statement = statement.where(InstrumentRow.asset_class == asset_class.value)
        if is_active is not None:
            statement = statement.where(InstrumentRow.is_active == is_active)
        statement = statement.order_by(InstrumentRow.canonical_symbol)
        with self.session_factory() as session:
            return [_instrument_from_row(row) for row in session.scalars(statement).all()]

    def save_contract_spec(self, contract_spec: ContractSpec) -> None:
        with self.session_factory.begin() as session:
            existing = session.scalar(
                select(ContractSpecRow).where(ContractSpecRow.instrument_id == contract_spec.instrument_id)
            )
            if existing is None:
                session.add(_contract_spec_row(contract_spec))
            else:
                _update_contract_spec_row(existing, contract_spec)

    def get_contract_spec(self, instrument_id: str) -> ContractSpec | None:
        with self.session_factory() as session:
            row = session.scalar(
                select(ContractSpecRow).where(ContractSpecRow.instrument_id == instrument_id)
            )
            return _contract_spec_from_row(row) if row is not None else None

    def save_candles(self, candles: list[Candle]) -> None:
        with self.session_factory.begin() as session:
            for candle in candles:
                existing = session.scalar(
                    select(CandleRow).where(
                        CandleRow.venue == candle.venue.value,
                        CandleRow.instrument_id == candle.instrument_id,
                        CandleRow.interval == candle.interval,
                        CandleRow.ts_start == candle.ts_start,
                    )
                )
                if existing is None:
                    session.add(_candle_row(candle))
                else:
                    _update_candle_row(existing, candle)

    def load_candles(
        self,
        instrument_id: str,
        interval: str,
        start: datetime,
        end: datetime,
    ) -> list[Candle]:
        with self.session_factory() as session:
            rows = session.scalars(
                select(CandleRow)
                .where(
                    CandleRow.instrument_id == instrument_id,
                    CandleRow.interval == interval,
                    CandleRow.ts_start >= start,
                    CandleRow.ts_start < end,
                )
                .order_by(CandleRow.ts_start)
            ).all()
            return [_candle_from_row(row) for row in rows]

    def save_signal(self, signal: Signal) -> None:
        with self.session_factory.begin() as session:
            session.merge(
                SignalRow(
                    id=signal.id,
                    strategy_id=signal.strategy_id,
                    instrument_id=signal.instrument_id,
                    venue=signal.venue.value,
                    direction=signal.direction.value,
                    ts=signal.ts,
                    price=signal.price,
                    payload=_json_payload(signal),
                )
            )

    def save_order_intent(self, order_intent: OrderIntent) -> None:
        with self.session_factory.begin() as session:
            session.merge(
                OrderIntentRow(
                    id=order_intent.id,
                    strategy_id=order_intent.strategy_id,
                    signal_id=order_intent.signal_id,
                    venue=order_intent.venue.value,
                    instrument_id=order_intent.instrument_id,
                    side=order_intent.side.value,
                    order_type=order_intent.order_type.value,
                    qty=order_intent.qty,
                    limit_price=order_intent.limit_price,
                    stop_price=order_intent.stop_price,
                    take_profit=order_intent.take_profit,
                    stop_loss=order_intent.stop_loss,
                    time_in_force=order_intent.time_in_force.value,
                    reason=order_intent.reason,
                    risk_amount=order_intent.risk_amount,
                    idempotency_key=order_intent.idempotency_key,
                    payload=_json_payload(order_intent),
                    created_at=order_intent.created_at,
                )
            )

    def save_risk_decision(self, risk_decision: RiskDecision) -> None:
        with self.session_factory.begin() as session:
            session.merge(
                RiskDecisionRow(
                    id=risk_decision.id,
                    order_intent_id=risk_decision.order_intent_id,
                    approved=risk_decision.approved,
                    reason=risk_decision.reason,
                    checks=risk_decision.checks,
                    created_at=risk_decision.created_at,
                )
            )

    def save_order(self, order: Order) -> None:
        with self.session_factory.begin() as session:
            session.merge(
                OrderRow(
                    id=order.id,
                    order_intent_id=order.order_intent_id,
                    venue=order.venue.value,
                    broker_order_id=order.broker_order_id,
                    idempotency_key=order.idempotency_key,
                    state=order.state.value,
                    side=order.side.value,
                    order_type=order.order_type.value,
                    qty=order.qty,
                    filled_qty=order.filled_qty,
                    avg_fill_price=order.avg_fill_price,
                    created_at=order.created_at,
                    updated_at=order.updated_at,
                )
            )

    def save_execution(self, execution: Execution) -> None:
        with self.session_factory.begin() as session:
            session.merge(
                ExecutionRow(
                    id=execution.id,
                    order_id=execution.order_id,
                    venue=execution.venue.value,
                    broker_execution_id=execution.broker_execution_id,
                    instrument_id=execution.instrument_id,
                    side=execution.side.value,
                    qty=execution.qty,
                    price=execution.price,
                    commission=execution.commission,
                    ts=execution.ts,
                )
            )

    def save_position(self, position: Position) -> None:
        with self.session_factory.begin() as session:
            existing = session.scalar(
                select(PositionRow).where(
                    PositionRow.instrument_id == position.instrument_id,
                    PositionRow.venue == position.venue.value,
                )
            )
            row = PositionRow(
                instrument_id=position.instrument_id,
                venue=position.venue.value,
                qty=position.qty,
                avg_price=position.avg_price,
                unrealized_pnl=position.unrealized_pnl,
                realized_pnl=position.realized_pnl,
                updated_at=position.updated_at,
            )
            if existing is None:
                session.add(row)
            else:
                existing.qty = row.qty
                existing.avg_price = row.avg_price
                existing.unrealized_pnl = row.unrealized_pnl
                existing.realized_pnl = row.realized_pnl
                existing.updated_at = row.updated_at

    def save_journal_entry(self, entry: TradeJournalEntry) -> None:
        self.save_system_event(
            SystemEvent(
                event_type="trade_journal_entry_saved",
                payload=entry.model_dump(mode="json"),
                ts=entry.created_at,
            )
        )

    def save_backtest_run(self, run: BacktestRun) -> None:
        with self.session_factory.begin() as session:
            session.merge(
                BacktestRunRow(
                    id=run.id,
                    strategy_id=run.strategy_id,
                    metrics=run.model_dump(mode="json"),
                    created_at=run.created_at,
                )
            )

    def save_research_run(self, run: ResearchRun) -> None:
        with self.session_factory.begin() as session:
            session.merge(_research_run_row(run))

    def get_research_run(self, run_id: str) -> ResearchRun | None:
        with self.session_factory() as session:
            row = session.scalar(select(ResearchRunRow).where(ResearchRunRow.id == run_id))
            return _research_run_from_row(row) if row is not None else None

    def list_research_runs(
        self,
        strategy_id: str | None = None,
        canonical_symbol: str | None = None,
        status: ResearchStatus | None = None,
    ) -> list[ResearchRun]:
        statement = select(ResearchRunRow)
        if strategy_id is not None:
            statement = statement.where(ResearchRunRow.strategy_id == strategy_id)
        if canonical_symbol is not None:
            statement = statement.where(ResearchRunRow.canonical_symbol == canonical_symbol)
        if status is not None:
            statement = statement.where(ResearchRunRow.status == status.value)
        statement = statement.order_by(ResearchRunRow.created_at)
        with self.session_factory() as session:
            return [_research_run_from_row(row) for row in session.scalars(statement).all()]

    def save_research_backtest_result(self, result: ResearchBacktestResult) -> None:
        with self.session_factory.begin() as session:
            session.merge(_research_backtest_result_row(result))

    def list_research_backtest_results(self, research_run_id: str) -> list[ResearchBacktestResult]:
        statement = (
            select(ResearchBacktestResultRow)
            .where(ResearchBacktestResultRow.research_run_id == research_run_id)
            .order_by(ResearchBacktestResultRow.created_at)
        )
        with self.session_factory() as session:
            return [
                _research_backtest_result_from_row(row)
                for row in session.scalars(statement).all()
            ]

    def get_research_backtest_result(self, result_id: str) -> ResearchBacktestResult | None:
        with self.session_factory() as session:
            row = session.scalar(
                select(ResearchBacktestResultRow).where(ResearchBacktestResultRow.id == result_id)
            )
            return _research_backtest_result_from_row(row) if row is not None else None

    def save_backtest_equity_points(self, points: list[BacktestEquityPoint]) -> None:
        with self.session_factory.begin() as session:
            for point in points:
                session.merge(_backtest_equity_point_row(point))

    def load_backtest_equity_points(self, backtest_run_id: str) -> list[BacktestEquityPoint]:
        statement = (
            select(BacktestEquityPointRow)
            .where(BacktestEquityPointRow.backtest_run_id == backtest_run_id)
            .order_by(BacktestEquityPointRow.ts)
        )
        with self.session_factory() as session:
            return [_backtest_equity_point_from_row(row) for row in session.scalars(statement).all()]

    def save_backtest_trade_records(self, records: list[BacktestTradeRecord]) -> None:
        with self.session_factory.begin() as session:
            for record in records:
                session.merge(_backtest_trade_record_row(record))

    def load_backtest_trade_records(self, backtest_run_id: str) -> list[BacktestTradeRecord]:
        statement = select(BacktestTradeRecordRow).where(
            BacktestTradeRecordRow.backtest_run_id == backtest_run_id
        )
        with self.session_factory() as session:
            return [_backtest_trade_record_from_row(row) for row in session.scalars(statement).all()]

    def save_market_sessions(self, sessions: list[MarketSession]) -> None:
        with self.session_factory.begin() as session:
            for market_session in sessions:
                session.merge(_market_session_row(market_session))

    def load_market_sessions(
        self,
        venue: Venue | None = None,
        market: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[MarketSession]:
        statement = select(MarketSessionRow)
        if venue is not None:
            statement = statement.where(MarketSessionRow.venue == venue.value)
        if market is not None:
            statement = statement.where(MarketSessionRow.market == market)
        if start is not None:
            statement = statement.where(MarketSessionRow.end > start)
        if end is not None:
            statement = statement.where(MarketSessionRow.start < end)
        statement = statement.order_by(MarketSessionRow.start)
        with self.session_factory() as session:
            return [_market_session_from_row(row) for row in session.scalars(statement).all()]

    def save_continuous_series(self, series: ContinuousSeries) -> None:
        with self.session_factory.begin() as session:
            existing = session.scalar(
                select(ContinuousSeriesRow).where(ContinuousSeriesRow.id == series.id)
            ) or session.scalar(
                select(ContinuousSeriesRow).where(
                    ContinuousSeriesRow.canonical_symbol == series.canonical_symbol
                )
            )
            if existing is None:
                session.add(_continuous_series_row(series))
            else:
                _update_continuous_series_row(existing, series)

    def get_continuous_series(self, series_id: str) -> ContinuousSeries | None:
        with self.session_factory() as session:
            row = session.scalar(select(ContinuousSeriesRow).where(ContinuousSeriesRow.id == series_id))
            return _continuous_series_from_row(row) if row is not None else None

    def get_continuous_series_by_canonical_symbol(self, canonical_symbol: str) -> ContinuousSeries | None:
        with self.session_factory() as session:
            row = session.scalar(
                select(ContinuousSeriesRow).where(
                    ContinuousSeriesRow.canonical_symbol == canonical_symbol
                )
            )
            return _continuous_series_from_row(row) if row is not None else None

    def save_continuous_series_components(self, components: list[ContinuousSeriesComponent]) -> None:
        with self.session_factory.begin() as session:
            for component in components:
                session.merge(_continuous_series_component_row(component))

    def load_continuous_series_components(self, series_id: str) -> list[ContinuousSeriesComponent]:
        statement = (
            select(ContinuousSeriesComponentRow)
            .where(ContinuousSeriesComponentRow.continuous_series_id == series_id)
            .order_by(ContinuousSeriesComponentRow.start)
        )
        with self.session_factory() as session:
            return [
                _continuous_series_component_from_row(row)
                for row in session.scalars(statement).all()
            ]

    def save_roll_events(self, events: list[RollEvent]) -> None:
        with self.session_factory.begin() as session:
            for event in events:
                session.merge(_roll_event_row(event))

    def load_roll_events(
        self,
        underlying_symbol: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[RollEvent]:
        statement = select(RollEventRow)
        if underlying_symbol is not None:
            statement = statement.where(RollEventRow.underlying_symbol == underlying_symbol)
        if start_date is not None:
            statement = statement.where(RollEventRow.roll_date >= start_date)
        if end_date is not None:
            statement = statement.where(RollEventRow.roll_date < end_date)
        statement = statement.order_by(RollEventRow.roll_date)
        with self.session_factory() as session:
            return [_roll_event_from_row(row) for row in session.scalars(statement).all()]

    def save_system_event(self, event: SystemEvent) -> None:
        with self.session_factory.begin() as session:
            session.merge(
                SystemEventRow(
                    id=event.id,
                    event_type=event.event_type,
                    payload=event.payload,
                    ts=event.ts,
                )
            )

    def save_audit_log(self, audit_log: AuditLog) -> None:
        with self.session_factory.begin() as session:
            session.merge(
                AuditLogRow(
                    id=audit_log.id,
                    entity_type=audit_log.entity_type,
                    entity_id=audit_log.entity_id,
                    action=audit_log.action,
                    payload=audit_log.payload,
                    ts=audit_log.ts,
                )
            )


def _instrument_row(instrument: Instrument) -> InstrumentRow:
    return InstrumentRow(
        id=instrument.id,
        venue=instrument.venue.value,
        asset_class=instrument.asset_class.value,
        native_symbol=instrument.native_symbol,
        canonical_symbol=instrument.canonical_symbol,
        name=instrument.name,
        lot_size=instrument.lot_size,
        tick_size=instrument.tick_size,
        tick_value=instrument.tick_value,
        currency=instrument.currency,
        expiry_date=instrument.expiry_date,
        is_active=instrument.is_active,
        metadata_json=instrument.metadata,
    )


def _update_instrument_row(row: InstrumentRow, instrument: Instrument) -> None:
    row.id = instrument.id
    row.venue = instrument.venue.value
    row.asset_class = instrument.asset_class.value
    row.native_symbol = instrument.native_symbol
    row.canonical_symbol = instrument.canonical_symbol
    row.name = instrument.name
    row.lot_size = instrument.lot_size
    row.tick_size = instrument.tick_size
    row.tick_value = instrument.tick_value
    row.currency = instrument.currency
    row.expiry_date = instrument.expiry_date
    row.is_active = instrument.is_active
    row.metadata_json = instrument.metadata


def _instrument_from_row(row: InstrumentRow) -> Instrument:
    return Instrument(
        id=row.id,
        venue=Venue(row.venue),
        asset_class=AssetClass(row.asset_class),
        native_symbol=row.native_symbol,
        canonical_symbol=row.canonical_symbol,
        name=row.name,
        lot_size=row.lot_size,
        tick_size=row.tick_size,
        tick_value=row.tick_value,
        currency=row.currency,
        expiry_date=row.expiry_date,
        is_active=row.is_active,
        metadata=dict(row.metadata_json or {}),
    )


def _contract_spec_row(contract_spec: ContractSpec) -> ContractSpecRow:
    return ContractSpecRow(
        instrument_id=contract_spec.instrument_id,
        lot_size=contract_spec.lot_size,
        tick_size=contract_spec.tick_size,
        tick_value=contract_spec.tick_value,
        currency=contract_spec.currency,
        expiry_date=contract_spec.expiry_date,
        first_trade_date=contract_spec.first_trade_date,
        last_trade_date=contract_spec.last_trade_date,
        underlying_symbol=contract_spec.underlying_symbol,
        metadata_json=contract_spec.metadata,
    )


def _update_contract_spec_row(row: ContractSpecRow, contract_spec: ContractSpec) -> None:
    row.instrument_id = contract_spec.instrument_id
    row.lot_size = contract_spec.lot_size
    row.tick_size = contract_spec.tick_size
    row.tick_value = contract_spec.tick_value
    row.currency = contract_spec.currency
    row.expiry_date = contract_spec.expiry_date
    row.first_trade_date = contract_spec.first_trade_date
    row.last_trade_date = contract_spec.last_trade_date
    row.underlying_symbol = contract_spec.underlying_symbol
    row.metadata_json = contract_spec.metadata


def _contract_spec_from_row(row: ContractSpecRow) -> ContractSpec:
    return ContractSpec(
        instrument_id=row.instrument_id,
        lot_size=row.lot_size,
        tick_size=row.tick_size,
        tick_value=row.tick_value,
        currency=row.currency,
        expiry_date=row.expiry_date,
        first_trade_date=row.first_trade_date,
        last_trade_date=row.last_trade_date,
        underlying_symbol=row.underlying_symbol,
        metadata=dict(row.metadata_json or {}),
    )


def _research_run_row(run: ResearchRun) -> ResearchRunRow:
    payload = run.model_dump(mode="json")
    return ResearchRunRow(
        id=run.id,
        strategy_id=run.strategy_id,
        canonical_symbol=run.canonical_symbol,
        instrument_id=run.instrument_id,
        interval=run.interval,
        start=run.start,
        end=run.end,
        parameter_grid=payload["parameter_grid"],
        data_quality_gate=payload["data_quality_gate"],
        status=run.status.value,
        created_at=run.created_at,
        completed_at=run.completed_at,
        notes=run.notes,
        metadata_json=payload["metadata"],
    )


def _research_run_from_row(row: ResearchRunRow) -> ResearchRun:
    return ResearchRun(
        id=row.id,
        strategy_id=row.strategy_id,
        canonical_symbol=row.canonical_symbol,
        instrument_id=row.instrument_id,
        interval=row.interval,
        start=_aware(row.start),
        end=_aware(row.end),
        parameter_grid=dict(row.parameter_grid or {}),
        data_quality_gate=dict(row.data_quality_gate or {}),
        status=ResearchStatus(row.status),
        created_at=_aware(row.created_at),
        completed_at=_aware(row.completed_at) if row.completed_at is not None else None,
        notes=row.notes,
        metadata=dict(row.metadata_json or {}),
    )


def _research_backtest_result_row(result: ResearchBacktestResult) -> ResearchBacktestResultRow:
    payload = result.model_dump(mode="json")
    return ResearchBacktestResultRow(
        id=result.id,
        research_run_id=result.research_run_id,
        backtest_run_id=result.backtest_run_id,
        strategy_id=result.strategy_id,
        canonical_symbol=result.canonical_symbol,
        instrument_id=result.instrument_id,
        interval=result.interval,
        start=result.start,
        end=result.end,
        params=payload["params"],
        metrics=payload["metrics"],
        quality_report=payload["quality_report"],
        status=result.status.value,
        error_message=result.error_message,
        created_at=result.created_at,
    )


def _research_backtest_result_from_row(row: ResearchBacktestResultRow) -> ResearchBacktestResult:
    return ResearchBacktestResult(
        id=row.id,
        research_run_id=row.research_run_id,
        backtest_run_id=row.backtest_run_id,
        strategy_id=row.strategy_id,
        canonical_symbol=row.canonical_symbol,
        instrument_id=row.instrument_id,
        interval=row.interval,
        start=_aware(row.start),
        end=_aware(row.end),
        params=dict(row.params or {}),
        metrics=dict(row.metrics or {}),
        quality_report=dict(row.quality_report or {}),
        status=ResearchStatus(row.status),
        error_message=row.error_message,
        created_at=_aware(row.created_at),
    )


def _backtest_equity_point_row(point: BacktestEquityPoint) -> BacktestEquityPointRow:
    return BacktestEquityPointRow(
        id=point.id,
        backtest_run_id=point.backtest_run_id,
        ts=point.ts,
        equity=point.equity,
        drawdown=point.drawdown,
    )


def _backtest_equity_point_from_row(row: BacktestEquityPointRow) -> BacktestEquityPoint:
    return BacktestEquityPoint(
        id=row.id,
        backtest_run_id=row.backtest_run_id,
        ts=_aware(row.ts),
        equity=row.equity,
        drawdown=row.drawdown,
    )


def _backtest_trade_record_row(record: BacktestTradeRecord) -> BacktestTradeRecordRow:
    payload = record.model_dump(mode="json")
    return BacktestTradeRecordRow(
        id=record.id,
        backtest_run_id=record.backtest_run_id,
        instrument_id=record.instrument_id,
        side=record.side.value,
        entry_ts=record.entry_ts,
        exit_ts=record.exit_ts,
        entry_price=record.entry_price,
        exit_price=record.exit_price,
        qty=record.qty,
        gross_pnl=record.gross_pnl,
        net_pnl=record.net_pnl,
        r_multiple=record.r_multiple,
        reason=record.reason,
        metadata_json=payload["metadata"],
    )


def _backtest_trade_record_from_row(row: BacktestTradeRecordRow) -> BacktestTradeRecord:
    return BacktestTradeRecord(
        id=row.id,
        backtest_run_id=row.backtest_run_id,
        instrument_id=row.instrument_id,
        side=Side(row.side),
        entry_ts=_aware(row.entry_ts) if row.entry_ts is not None else None,
        exit_ts=_aware(row.exit_ts) if row.exit_ts is not None else None,
        entry_price=row.entry_price,
        exit_price=row.exit_price,
        qty=row.qty,
        gross_pnl=row.gross_pnl,
        net_pnl=row.net_pnl,
        r_multiple=row.r_multiple,
        reason=row.reason,
        metadata=dict(row.metadata_json or {}),
    )


def _market_session_row(session: MarketSession) -> MarketSessionRow:
    payload = session.model_dump(mode="json")
    return MarketSessionRow(
        id=session.id,
        venue=session.venue.value,
        market=session.market,
        session_type=session.session_type.value,
        session_date=session.session_date,
        timezone=session.timezone,
        start=session.start,
        end=session.end,
        is_trading=session.is_trading,
        metadata_json=payload["metadata"],
    )


def _market_session_from_row(row: MarketSessionRow) -> MarketSession:
    return MarketSession(
        id=row.id,
        venue=Venue(row.venue),
        market=row.market,
        session_type=SessionType(row.session_type),
        session_date=row.session_date,
        timezone=row.timezone,
        start=_aware(row.start),
        end=_aware(row.end),
        is_trading=row.is_trading,
        metadata=dict(row.metadata_json or {}),
    )


def _continuous_series_row(series: ContinuousSeries) -> ContinuousSeriesRow:
    payload = series.model_dump(mode="json")
    return ContinuousSeriesRow(
        id=series.id,
        venue=series.venue,
        underlying_symbol=series.underlying_symbol,
        canonical_symbol=series.canonical_symbol,
        interval=series.interval,
        roll_rule=payload["roll_rule"],
        adjustment_method=series.adjustment_method,
        start=series.start,
        end=series.end,
        created_at=series.created_at,
        metadata_json=payload["metadata"],
    )


def _update_continuous_series_row(row: ContinuousSeriesRow, series: ContinuousSeries) -> None:
    payload = series.model_dump(mode="json")
    row.id = series.id
    row.venue = series.venue
    row.underlying_symbol = series.underlying_symbol
    row.canonical_symbol = series.canonical_symbol
    row.interval = series.interval
    row.roll_rule = payload["roll_rule"]
    row.adjustment_method = series.adjustment_method
    row.start = series.start
    row.end = series.end
    row.created_at = series.created_at
    row.metadata_json = payload["metadata"]


def _continuous_series_from_row(row: ContinuousSeriesRow) -> ContinuousSeries:
    return ContinuousSeries(
        id=row.id,
        venue=row.venue,
        underlying_symbol=row.underlying_symbol,
        canonical_symbol=row.canonical_symbol,
        interval=row.interval,
        roll_rule=dict(row.roll_rule or {}),
        adjustment_method=row.adjustment_method,
        start=_aware(row.start),
        end=_aware(row.end),
        created_at=_aware(row.created_at),
        metadata=dict(row.metadata_json or {}),
    )


def _continuous_series_component_row(component: ContinuousSeriesComponent) -> ContinuousSeriesComponentRow:
    payload = component.model_dump(mode="json")
    return ContinuousSeriesComponentRow(
        id=component.id,
        continuous_series_id=component.continuous_series_id,
        instrument_id=component.instrument_id,
        canonical_symbol=component.canonical_symbol,
        start=component.start,
        end=component.end,
        roll_date=component.roll_date,
        metadata_json=payload["metadata"],
    )


def _continuous_series_component_from_row(row: ContinuousSeriesComponentRow) -> ContinuousSeriesComponent:
    return ContinuousSeriesComponent(
        id=row.id,
        continuous_series_id=row.continuous_series_id,
        instrument_id=row.instrument_id,
        canonical_symbol=row.canonical_symbol,
        start=_aware(row.start),
        end=_aware(row.end),
        roll_date=row.roll_date,
        metadata=dict(row.metadata_json or {}),
    )


def _roll_event_row(event: RollEvent) -> RollEventRow:
    payload = event.model_dump(mode="json")
    return RollEventRow(
        id=event.id,
        venue=event.venue,
        underlying_symbol=event.underlying_symbol,
        from_instrument_id=event.from_instrument_id,
        to_instrument_id=event.to_instrument_id,
        roll_date=event.roll_date,
        reason=event.reason,
        metadata_json=payload["metadata"],
    )


def _roll_event_from_row(row: RollEventRow) -> RollEvent:
    return RollEvent(
        id=row.id,
        venue=row.venue,
        underlying_symbol=row.underlying_symbol,
        from_instrument_id=row.from_instrument_id,
        to_instrument_id=row.to_instrument_id,
        roll_date=row.roll_date,
        reason=row.reason,
        metadata=dict(row.metadata_json or {}),
    )


def _candle_row(candle: Candle) -> CandleRow:
    return CandleRow(
        venue=candle.venue.value,
        instrument_id=candle.instrument_id,
        interval=candle.interval,
        ts_start=candle.ts_start,
        ts_end=candle.ts_end,
        open=candle.open,
        high=candle.high,
        low=candle.low,
        close=candle.close,
        volume=candle.volume,
        value=candle.value,
        trades_count=candle.trades_count,
        source=candle.source,
    )


def _update_candle_row(row: CandleRow, candle: Candle) -> None:
    row.ts_end = candle.ts_end
    row.open = candle.open
    row.high = candle.high
    row.low = candle.low
    row.close = candle.close
    row.volume = candle.volume
    row.value = candle.value
    row.trades_count = candle.trades_count
    row.source = candle.source


def _candle_from_row(row: CandleRow) -> Candle:
    return Candle(
        instrument_id=row.instrument_id,
        venue=Venue(row.venue),
        interval=row.interval,
        ts_start=_aware(row.ts_start),
        ts_end=_aware(row.ts_end),
        open=row.open,
        high=row.high,
        low=row.low,
        close=row.close,
        volume=row.volume,
        value=row.value,
        trades_count=row.trades_count,
        source=row.source,
    )


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _json_payload(model: Any) -> dict[str, Any]:
    payload = model.model_dump(mode="json")
    return payload if isinstance(payload, dict) else {}
