from datetime import UTC, datetime
from decimal import Decimal

import pytest
from adapters.paper.broker import PaperBroker
from adapters.paper.execution_adapter import PaperExecutionAdapter
from storage.in_memory import InMemoryStorage
from trading_core.domain.enums import AssetClass, OrderState, OrderType, Side, TimeInForce, TradingMode, Venue
from trading_core.domain.errors import BrokerUnavailableError
from trading_core.domain.models import Instrument, OrderIntent, RiskConfig, RiskContext
from trading_core.execution.engine import ExecutionEngine
from trading_core.risk.engine import RiskEngine
from trading_core.risk.kill_switch import KillSwitch


def make_instrument() -> Instrument:
    return Instrument(
        id="moex-si",
        venue=Venue.PAPER,
        asset_class=AssetClass.FUTURES,
        native_symbol="SiH6",
        canonical_symbol="MOEX:SIH6",
        name="Si futures",
        lot_size=Decimal("1"),
        tick_size=Decimal("1"),
        tick_value=Decimal("1"),
        currency="RUB",
    )


def make_context(**overrides: object) -> RiskContext:
    now = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
    values: dict[str, object] = {
        "instrument": make_instrument(),
        "now": now,
        "market_data_ts": now,
        "bid": Decimal("99.95"),
        "ask": Decimal("100.05"),
        "portfolio_value": Decimal("100000"),
    }
    values.update(overrides)
    return RiskContext(**values)


def make_intent(**overrides: object) -> OrderIntent:
    values: dict[str, object] = {
        "strategy_id": "test",
        "signal_id": "sig",
        "venue": Venue.PAPER,
        "instrument_id": "moex-si",
        "side": Side.BUY,
        "order_type": OrderType.MARKET,
        "qty": Decimal("1"),
        "time_in_force": TimeInForce.DAY,
        "reason": "execution test",
        "risk_amount": Decimal("10"),
        "idempotency_key": "exec-key",
    }
    values.update(overrides)
    return OrderIntent(**values)


@pytest.mark.asyncio
async def test_rejected_order_does_not_call_broker_and_audits() -> None:
    storage = InMemoryStorage()
    broker = PaperBroker()
    broker.set_market("moex-si", bid=Decimal("99.9"), ask=Decimal("100.1"), last=Decimal("100"))
    engine = ExecutionEngine(
        risk_engine=RiskEngine(
            RiskConfig(trading_mode=TradingMode.PAPER, instrument_allowlist=["other"]),
            KillSwitch(),
        ),
        execution_port=PaperExecutionAdapter(broker),
        storage=storage,
    )

    result = await engine.execute_order_intent(make_intent(), make_context())

    assert result.submitted is False
    assert result.order.state == OrderState.RISK_REJECTED
    assert len(broker.executions) == 0
    assert [log.action for log in storage.audit_logs] == [
        "before_risk_check",
        "order_state_transition",
        "risk_rejected",
    ]
    assert storage.audit_logs[1].payload == {
        "from_state": "NEW",
        "to_state": "RISK_REJECTED",
        "reason": "risk_rejected",
    }
    assert len(storage.risk_decisions) == 1
    assert len(storage.orders) == 1


@pytest.mark.asyncio
async def test_approved_paper_order_calls_broker_and_stores_outputs() -> None:
    storage = InMemoryStorage()
    broker = PaperBroker()
    broker.set_market("moex-si", bid=Decimal("99.9"), ask=Decimal("100.1"), last=Decimal("100"))
    engine = ExecutionEngine(
        risk_engine=RiskEngine(
            RiskConfig(trading_mode=TradingMode.PAPER, instrument_allowlist=["moex-si"]),
            KillSwitch(),
        ),
        execution_port=PaperExecutionAdapter(broker),
        storage=storage,
    )

    result = await engine.execute_order_intent(make_intent(), make_context())

    assert result.submitted is True
    assert result.order.state == OrderState.FILLED
    assert len(result.executions) == 1
    assert [log.action for log in storage.audit_logs] == [
        "before_risk_check",
        "order_state_transition",
        "before_broker_submission",
        "order_state_transition",
        "order_state_transition",
        "after_broker_submission",
    ]
    assert len(storage.order_intents) == 1
    assert len(storage.risk_decisions) == 1
    assert [order.state for order in storage.orders] == [
        OrderState.APPROVED,
        OrderState.SUBMITTED,
        OrderState.FILLED,
    ]
    assert {order.id for order in storage.orders} == {result.order.id}
    assert len(storage.executions) == 1
    assert storage.executions[0].order_id == result.order.id


class FailingExecutionAdapter:
    async def place_order(self, order_intent: OrderIntent):
        raise BrokerUnavailableError("broker down")

    async def cancel_order(self, order_id: str):
        raise BrokerUnavailableError("broker down")

    async def get_order_state(self, order_id: str):
        return OrderState.FAILED

    async def stream_orders(self):
        if False:
            yield None

    async def stream_executions(self):
        if False:
            yield None


@pytest.mark.asyncio
async def test_broker_exception_records_kill_switch_error_and_failed_order() -> None:
    storage = InMemoryStorage()
    kill_switch = KillSwitch(broker_error_threshold=1)
    engine = ExecutionEngine(
        risk_engine=RiskEngine(
            RiskConfig(trading_mode=TradingMode.PAPER, instrument_allowlist=["moex-si"]),
            kill_switch,
        ),
        execution_port=FailingExecutionAdapter(),
        storage=storage,
    )

    result = await engine.execute_order_intent(make_intent(), make_context())

    assert result.submitted is False
    assert result.order.state == OrderState.FAILED
    assert kill_switch.active is True
    assert storage.audit_logs[-1].action == "broker_submission_failed"
