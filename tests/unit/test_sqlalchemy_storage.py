from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from storage.sqlalchemy_models import AuditLogRow, Base, CandleRow, ExecutionRow, OrderRow
from storage.sqlalchemy_repositories import SQLAlchemyStorage
from trading_core.domain.enums import OrderState, OrderType, Side, Venue
from trading_core.domain.models import AuditLog, Candle, Execution, Order, OrderIntent, RiskDecision


def make_storage() -> SQLAlchemyStorage:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return SQLAlchemyStorage(sessionmaker(bind=engine))


def make_candle(close: Decimal = Decimal("100.5")) -> Candle:
    start = datetime(2026, 1, 1, 7, 0, tzinfo=UTC)
    return Candle(
        instrument_id="moex-si",
        venue=Venue.MOEX,
        interval="1m",
        ts_start=start,
        ts_end=start + timedelta(minutes=1),
        open=Decimal("100"),
        high=Decimal("101"),
        low=Decimal("99"),
        close=close,
        volume=Decimal("10"),
        value=Decimal("1000"),
        source="moex-iss",
    )


def test_sqlalchemy_storage_saves_and_loads_candles() -> None:
    storage = make_storage()
    candle = make_candle()

    storage.save_candles([candle])
    loaded = storage.load_candles(
        "moex-si",
        "1m",
        datetime(2026, 1, 1, 6, 0, tzinfo=UTC),
        datetime(2026, 1, 1, 8, 0, tzinfo=UTC),
    )

    assert loaded == [candle]


def test_sqlalchemy_storage_load_candles_excludes_candle_exactly_at_end() -> None:
    storage = make_storage()
    start = datetime(2026, 1, 1, 7, 0, tzinfo=UTC)
    first = make_candle()
    at_end = first.model_copy(
        update={
            "ts_start": start + timedelta(minutes=1),
            "ts_end": start + timedelta(minutes=2),
            "close": Decimal("101"),
        }
    )

    storage.save_candles([first, at_end])
    loaded = storage.load_candles("moex-si", "1m", start, start + timedelta(minutes=1))

    assert loaded == [first]


def test_sqlalchemy_storage_upserts_duplicate_candle_without_duplicate_row() -> None:
    storage = make_storage()
    first = make_candle(close=Decimal("100.5"))
    updated = make_candle(close=Decimal("101.5"))

    storage.save_candles([first])
    storage.save_candles([updated])

    with storage.session_factory() as session:
        rows_count = session.scalar(select(func.count()).select_from(CandleRow))
    loaded = storage.load_candles(
        "moex-si",
        "1m",
        datetime(2026, 1, 1, 6, 0, tzinfo=UTC),
        datetime(2026, 1, 1, 8, 0, tzinfo=UTC),
    )
    assert rows_count == 1
    assert loaded[0].close == Decimal("101.500000000000000000")


def test_sqlalchemy_storage_saves_audit_logs() -> None:
    storage = make_storage()
    audit = AuditLog(
        entity_type="order",
        entity_id="order-1",
        action="order_state_transition",
        payload={"from_state": "NEW", "to_state": "APPROVED"},
    )

    storage.save_audit_log(audit)

    with storage.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(AuditLogRow)) == 1


def test_sqlalchemy_storage_saves_orders_and_executions() -> None:
    storage = make_storage()
    intent = OrderIntent(
        id="intent-1",
        strategy_id="test",
        venue=Venue.PAPER,
        instrument_id="moex-si",
        side=Side.BUY,
        order_type=OrderType.MARKET,
        qty=Decimal("1"),
        reason="storage test",
        idempotency_key="idem-1",
    )
    decision = RiskDecision(
        order_intent_id=intent.id,
        approved=True,
        reason="approved",
        checks={"ok": True},
    )
    order = Order(
        id="order-1",
        order_intent_id=intent.id,
        venue=Venue.PAPER,
        broker_order_id="paper-1",
        idempotency_key="idem-1",
        state=OrderState.FILLED,
        side=Side.BUY,
        order_type=OrderType.MARKET,
        qty=Decimal("1"),
        filled_qty=Decimal("1"),
        avg_fill_price=Decimal("100"),
    )
    execution = Execution(
        id="exec-1",
        order_id=order.id,
        venue=Venue.PAPER,
        broker_execution_id="paper-exec-1",
        instrument_id="moex-si",
        side=Side.BUY,
        qty=Decimal("1"),
        price=Decimal("100"),
    )

    storage.save_order_intent(intent)
    storage.save_risk_decision(decision)
    storage.save_order(order)
    storage.save_execution(execution)

    with storage.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(OrderRow)) == 1
        assert session.scalar(select(func.count()).select_from(ExecutionRow)) == 1
