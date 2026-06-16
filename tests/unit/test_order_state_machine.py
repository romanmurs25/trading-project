import pytest
from trading_core.domain.enums import OrderState
from trading_core.domain.errors import DataValidationError
from trading_core.execution.order_state_machine import OrderStateMachine


def test_order_state_machine_accepts_valid_transition() -> None:
    machine = OrderStateMachine()

    assert machine.transition(OrderState.NEW, OrderState.APPROVED) == OrderState.APPROVED
    assert machine.transition(OrderState.APPROVED, OrderState.SUBMITTED) == OrderState.SUBMITTED


def test_order_state_machine_rejects_invalid_transition() -> None:
    machine = OrderStateMachine()

    with pytest.raises(DataValidationError):
        machine.transition(OrderState.NEW, OrderState.FILLED)
