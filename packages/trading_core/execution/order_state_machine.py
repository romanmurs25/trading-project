from typing import ClassVar

from trading_core.domain.enums import OrderState
from trading_core.domain.errors import DataValidationError


class OrderStateMachine:
    allowed: ClassVar[dict[OrderState, set[OrderState]]] = {
        OrderState.NEW: {OrderState.APPROVED, OrderState.RISK_REJECTED, OrderState.FAILED},
        OrderState.RISK_REJECTED: set(),
        OrderState.APPROVED: {OrderState.SUBMITTED, OrderState.FAILED},
        OrderState.SUBMITTED: {
            OrderState.PARTIALLY_FILLED,
            OrderState.FILLED,
            OrderState.CANCEL_REQUESTED,
            OrderState.REJECTED,
            OrderState.FAILED,
            OrderState.UNKNOWN_RECONCILIATION_REQUIRED,
        },
        OrderState.PARTIALLY_FILLED: {
            OrderState.FILLED,
            OrderState.CANCEL_REQUESTED,
            OrderState.CANCELLED,
            OrderState.UNKNOWN_RECONCILIATION_REQUIRED,
        },
        OrderState.FILLED: set(),
        OrderState.CANCEL_REQUESTED: {
            OrderState.CANCELLED,
            OrderState.FAILED,
            OrderState.UNKNOWN_RECONCILIATION_REQUIRED,
        },
        OrderState.CANCELLED: set(),
        OrderState.REJECTED: set(),
        OrderState.FAILED: {OrderState.UNKNOWN_RECONCILIATION_REQUIRED},
        OrderState.UNKNOWN_RECONCILIATION_REQUIRED: {
            OrderState.SUBMITTED,
            OrderState.FAILED,
            OrderState.CANCELLED,
        },
    }

    def transition(self, current: OrderState, target: OrderState) -> OrderState:
        if target not in self.allowed[current]:
            raise DataValidationError(f"Invalid order state transition: {current.value} -> {target.value}")
        return target
