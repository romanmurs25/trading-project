from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Engine, create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from trading_core.domain.enums import Venue
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

from storage.sqlalchemy_models import (
    AuditLogRow,
    BacktestRunRow,
    CandleRow,
    ExecutionRow,
    OrderIntentRow,
    OrderRow,
    PositionRow,
    RiskDecisionRow,
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
                    CandleRow.ts_start <= end,
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
