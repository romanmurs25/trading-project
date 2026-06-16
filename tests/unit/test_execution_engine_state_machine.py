from collections.abc import AsyncIterator
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from storage.in_memory import InMemoryStorage
from trading_core.domain.enums import AssetClass, OrderState, OrderType, Side, TimeInForce, TradingMode, Venue
from trading_core.domain.errors import BrokerUnavailableError, DataValidationError
from trading_core.domain.models import (
    BrokerOrderResult,
    Execution,
    Instrument,
    Order,
    OrderIntent,
    RiskConfig,
    RiskContext,
)
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
        "strategy_id": "state-machine-test",
        "signal_id": "sig",
        "venue": Venue.PAPER,
        "instrument_id": "moex-si",
        "side": Side.BUY,
        "order_type": OrderType.MARKET,
        "qty": Decimal("1"),
        "time_in_force": TimeInForce.DAY,
        "reason": "state machine test",
        "risk_amount": Decimal("10"),
        "idempotency_key": "state-machine-key",
    }
    values.update(overrides)
    return OrderIntent(**values)


class RecordingExecutionAdapter:
    def __init__(self, returned_state: OrderState = OrderState.FILLED, fail: bool = False) -> None:
        self.returned_state = returned_state
        self.fail = fail
        self.calls = 0

    async def place_order(self, order_intent: OrderIntent) -> BrokerOrderResult:
        self.calls += 1
        if self.fail:
            raise BrokerUnavailableError("broker down")
        order = Order(
            order_intent_id=order_intent.id,
            venue=Venue.PAPER,
            broker_order_id="paper-1",
            idempotency_key=str(order_intent.idempotency_key),
            state=self.returned_state,
            side=order_intent.side,
            order_type=order_intent.order_type,
            qty=order_intent.qty,
            filled_qty=order_intent.qty if self.returned_state == OrderState.FILLED else Decimal("0"),
            avg_fill_price=Decimal("100.05") if self.returned_state == OrderState.FILLED else None,
        )
        executions = []
        if self.returned_state == OrderState.FILLED:
            executions.append(
                Execution(
                    order_id=order.id,
                    venue=Venue.PAPER,
                    broker_execution_id="paper-exec-1",
                    instrument_id=order_intent.instrument_id,
                    side=order_intent.side,
                    qty=order_intent.qty,
                    price=Decimal("100.05"),
                )
            )
        return BrokerOrderResult(order=order, executions=executions)

    async def cancel_order(self, order_id: str) -> Order:
        raise NotImplementedError

    async def get_order_state(self, order_id: str) -> OrderState:
        return self.returned_state

    async def stream_orders(self) -> AsyncIterator[Order]:
        if False:
            yield Order(
                order_intent_id="unused",
                venue=Venue.PAPER,
                idempotency_key="unused",
                side=Side.BUY,
                order_type=OrderType.MARKET,
                qty=Decimal("1"),
            )

    async def stream_executions(self) -> AsyncIterator[Execution]:
        if False:
            yield Execution(
                order_id="unused",
                venue=Venue.PAPER,
                instrument_id="unused",
                side=Side.BUY,
                qty=Decimal("1"),
                price=Decimal("1"),
            )


def make_engine(
    adapter: RecordingExecutionAdapter,
    storage: InMemoryStorage,
    *,
    allowlist: list[str] | None = None,
) -> ExecutionEngine:
    return ExecutionEngine(
        risk_engine=RiskEngine(
            RiskConfig(trading_mode=TradingMode.PAPER, instrument_allowlist=allowlist or ["moex-si"]),
            KillSwitch(),
        ),
        execution_port=adapter,
        storage=storage,
    )


def state_transition_payloads(storage: InMemoryStorage) -> list[dict[str, object]]:
    return [log.payload for log in storage.audit_logs if log.action == "order_state_transition"]


@pytest.mark.asyncio
async def test_approved_paper_order_passes_through_valid_state_transitions() -> None:
    storage = InMemoryStorage()
    adapter = RecordingExecutionAdapter(returned_state=OrderState.FILLED)
    engine = make_engine(adapter, storage)

    result = await engine.execute_order_intent(make_intent(), make_context())

    assert result.order.state == OrderState.FILLED
    assert adapter.calls == 1
    assert state_transition_payloads(storage) == [
        {"from_state": "NEW", "to_state": "APPROVED", "reason": "risk_approved"},
        {"from_state": "APPROVED", "to_state": "SUBMITTED", "reason": "broker_submitted"},
        {"from_state": "SUBMITTED", "to_state": "FILLED", "reason": "broker_filled"},
    ]


@pytest.mark.asyncio
async def test_rejected_order_passes_new_to_risk_rejected_and_skips_broker() -> None:
    storage = InMemoryStorage()
    adapter = RecordingExecutionAdapter()
    engine = make_engine(adapter, storage, allowlist=["other"])

    result = await engine.execute_order_intent(make_intent(), make_context())

    assert result.order.state == OrderState.RISK_REJECTED
    assert adapter.calls == 0
    assert state_transition_payloads(storage) == [
        {"from_state": "NEW", "to_state": "RISK_REJECTED", "reason": "risk_rejected"}
    ]


@pytest.mark.asyncio
async def test_broker_failure_transitions_approved_order_to_failed() -> None:
    storage = InMemoryStorage()
    adapter = RecordingExecutionAdapter(fail=True)
    kill_switch = KillSwitch(broker_error_threshold=1)
    engine = ExecutionEngine(
        risk_engine=RiskEngine(
            RiskConfig(trading_mode=TradingMode.PAPER, instrument_allowlist=["moex-si"]),
            kill_switch,
        ),
        execution_port=adapter,
        storage=storage,
    )

    result = await engine.execute_order_intent(make_intent(), make_context())

    assert result.order.state == OrderState.FAILED
    assert kill_switch.active is True
    assert state_transition_payloads(storage) == [
        {"from_state": "NEW", "to_state": "APPROVED", "reason": "risk_approved"},
        {"from_state": "APPROVED", "to_state": "FAILED", "reason": "broker_submission_failed"},
    ]


@pytest.mark.asyncio
async def test_invalid_adapter_state_transition_raises_data_validation_error() -> None:
    storage = InMemoryStorage()
    adapter = RecordingExecutionAdapter(returned_state=OrderState.RISK_REJECTED)
    engine = make_engine(adapter, storage)

    with pytest.raises(DataValidationError):
        await engine.execute_order_intent(make_intent(), make_context())
