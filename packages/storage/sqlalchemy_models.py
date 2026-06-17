from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import JSON, Date, DateTime, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class InstrumentRow(Base):
    __tablename__ = "instruments"
    __table_args__ = (
        Index("ix_instruments_venue_asset_class_native_symbol", "venue", "asset_class", "native_symbol"),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    venue: Mapped[str] = mapped_column(String(32), index=True)
    asset_class: Mapped[str] = mapped_column(String(32))
    native_symbol: Mapped[str] = mapped_column(String(128))
    canonical_symbol: Mapped[str] = mapped_column(String(128), unique=True)
    name: Mapped[str] = mapped_column(String(256))
    lot_size: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    tick_size: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    tick_value: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    currency: Mapped[str] = mapped_column(String(16))
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)


class ContractSpecRow(Base):
    __tablename__ = "contract_specs"
    __table_args__ = (
        UniqueConstraint("instrument_id", name="uq_contract_specs_instrument_id"),
        Index("ix_contract_specs_instrument_id", "instrument_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    instrument_id: Mapped[str] = mapped_column(String(128))
    lot_size: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    tick_size: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    tick_value: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    currency: Mapped[str] = mapped_column(String(16))
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    first_trade_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_trade_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    underlying_symbol: Mapped[str | None] = mapped_column(String(128), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)


class CandleRow(Base):
    __tablename__ = "candles"
    __table_args__ = (
        UniqueConstraint("venue", "instrument_id", "interval", "ts_start", name="uq_candles_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    venue: Mapped[str] = mapped_column(String(32))
    instrument_id: Mapped[str] = mapped_column(String(128))
    interval: Mapped[str] = mapped_column(String(16))
    ts_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ts_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    open: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    high: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    low: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    close: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    volume: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    value: Mapped[Decimal | None] = mapped_column(Numeric(38, 18), nullable=True)
    trades_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(64))


class SignalRow(Base):
    __tablename__ = "signals"
    __table_args__ = (Index("ix_signals_strategy_instrument_ts", "strategy_id", "instrument_id", "ts"),)

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(128))
    instrument_id: Mapped[str] = mapped_column(String(128))
    venue: Mapped[str] = mapped_column(String(32))
    direction: Mapped[str] = mapped_column(String(32))
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    price: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    payload: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)


class OrderIntentRow(Base):
    __tablename__ = "order_intents"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(128))
    signal_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    venue: Mapped[str] = mapped_column(String(32))
    instrument_id: Mapped[str] = mapped_column(String(128))
    side: Mapped[str] = mapped_column(String(16))
    order_type: Mapped[str] = mapped_column(String(32))
    qty: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    limit_price: Mapped[Decimal | None] = mapped_column(Numeric(38, 18), nullable=True)
    stop_price: Mapped[Decimal | None] = mapped_column(Numeric(38, 18), nullable=True)
    take_profit: Mapped[Decimal | None] = mapped_column(Numeric(38, 18), nullable=True)
    stop_loss: Mapped[Decimal | None] = mapped_column(Numeric(38, 18), nullable=True)
    time_in_force: Mapped[str] = mapped_column(String(32))
    reason: Mapped[str] = mapped_column(String(512))
    risk_amount: Mapped[Decimal | None] = mapped_column(Numeric(38, 18), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(256), unique=True, nullable=True)
    payload: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RiskDecisionRow(Base):
    __tablename__ = "risk_decisions"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    order_intent_id: Mapped[str] = mapped_column(String(128), index=True)
    approved: Mapped[bool]
    reason: Mapped[str] = mapped_column(String(512))
    checks: Mapped[dict[str, object]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class OrderRow(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    order_intent_id: Mapped[str] = mapped_column(String(128), index=True)
    venue: Mapped[str] = mapped_column(String(32))
    broker_order_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(256), unique=True)
    state: Mapped[str] = mapped_column(String(64))
    side: Mapped[str] = mapped_column(String(16))
    order_type: Mapped[str] = mapped_column(String(32))
    qty: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    filled_qty: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    avg_fill_price: Mapped[Decimal | None] = mapped_column(Numeric(38, 18), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ExecutionRow(Base):
    __tablename__ = "executions"
    __table_args__ = (UniqueConstraint("venue", "broker_execution_id", name="uq_executions_broker_exec"),)

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    order_id: Mapped[str] = mapped_column(String(128), index=True)
    venue: Mapped[str] = mapped_column(String(32))
    broker_execution_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    instrument_id: Mapped[str] = mapped_column(String(128))
    side: Mapped[str] = mapped_column(String(16))
    qty: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    price: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    commission: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PositionRow(Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    instrument_id: Mapped[str] = mapped_column(String(128))
    venue: Mapped[str] = mapped_column(String(32))
    qty: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    avg_price: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    unrealized_pnl: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class BacktestRunRow(Base):
    __tablename__ = "backtest_runs"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(128), index=True)
    metrics: Mapped[dict[str, object]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ResearchRunRow(Base):
    __tablename__ = "research_runs"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(128), index=True)
    canonical_symbol: Mapped[str] = mapped_column(String(128), index=True)
    instrument_id: Mapped[str] = mapped_column(String(128), index=True)
    interval: Mapped[str] = mapped_column(String(16))
    start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    parameter_grid: Mapped[dict[str, object]] = mapped_column(JSON)
    data_quality_gate: Mapped[dict[str, object]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(32), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)


class ResearchBacktestResultRow(Base):
    __tablename__ = "research_backtest_results"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    research_run_id: Mapped[str] = mapped_column(String(128), index=True)
    backtest_run_id: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    strategy_id: Mapped[str] = mapped_column(String(128), index=True)
    canonical_symbol: Mapped[str] = mapped_column(String(128), index=True)
    instrument_id: Mapped[str] = mapped_column(String(128), index=True)
    interval: Mapped[str] = mapped_column(String(16))
    start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    params: Mapped[dict[str, object]] = mapped_column(JSON)
    metrics: Mapped[dict[str, object]] = mapped_column(JSON)
    quality_report: Mapped[dict[str, object]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(32), index=True)
    error_message: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class BacktestEquityPointRow(Base):
    __tablename__ = "backtest_equity_points"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    backtest_run_id: Mapped[str] = mapped_column(String(128), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    equity: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    drawdown: Mapped[Decimal] = mapped_column(Numeric(38, 18))


class BacktestTradeRecordRow(Base):
    __tablename__ = "backtest_trade_records"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    backtest_run_id: Mapped[str] = mapped_column(String(128), index=True)
    instrument_id: Mapped[str] = mapped_column(String(128), index=True)
    side: Mapped[str] = mapped_column(String(16))
    entry_ts: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    exit_ts: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    entry_price: Mapped[Decimal | None] = mapped_column(Numeric(38, 18), nullable=True)
    exit_price: Mapped[Decimal | None] = mapped_column(Numeric(38, 18), nullable=True)
    qty: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    gross_pnl: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    net_pnl: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    r_multiple: Mapped[Decimal | None] = mapped_column(Numeric(38, 18), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)


class AuditLogRow(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_logs_entity_ts", "entity_type", "entity_id", "ts"),)

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[str] = mapped_column(String(128))
    action: Mapped[str] = mapped_column(String(128))
    payload: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SystemEventRow(Base):
    __tablename__ = "system_events"
    __table_args__ = (Index("ix_system_events_type_ts", "event_type", "ts"),)

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(128))
    payload: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
