from dataclasses import dataclass, field

from trading_core.domain.enums import OrderState
from trading_core.domain.errors import BrokerUnavailableError
from trading_core.domain.models import AuditLog, Execution, Order, OrderIntent, RiskContext, RiskDecision
from trading_core.execution.idempotency import ensure_idempotency_key
from trading_core.execution.order_state_machine import OrderStateMachine
from trading_core.ports.execution import ExecutionPort
from trading_core.ports.storage import StoragePort
from trading_core.risk.engine import RiskEngine
from trading_core.risk.kill_switch import KillSwitch


@dataclass(frozen=True)
class OrderExecutionResult:
    order_intent: OrderIntent
    risk_decision: RiskDecision
    order: Order
    executions: list[Execution] = field(default_factory=list)
    audit_logs: list[AuditLog] = field(default_factory=list)
    submitted: bool = False


class ExecutionEngine:
    def __init__(
        self,
        risk_engine: RiskEngine,
        execution_port: ExecutionPort,
        storage: StoragePort | None = None,
    ) -> None:
        self.risk_engine = risk_engine
        self.execution_port = execution_port
        self.storage = storage
        self.kill_switch: KillSwitch = risk_engine.kill_switch
        self.state_machine = OrderStateMachine()

    async def execute_order_intent(
        self,
        order_intent: OrderIntent,
        context: RiskContext,
    ) -> OrderExecutionResult:
        safe_intent = ensure_idempotency_key(order_intent)
        audit_logs: list[AuditLog] = []
        self._save_order_intent(safe_intent)

        audit_logs.append(self._audit("order_intent", safe_intent.id, "before_risk_check"))
        decision = self.risk_engine.evaluate(safe_intent, context)
        self._save_risk_decision(decision)

        if not decision.approved:
            order = self._transition_order(
                self._new_order(safe_intent),
                OrderState.RISK_REJECTED,
                "risk_rejected",
                audit_logs,
            )
            self._save_order(order)
            audit_logs.append(self._audit("order", order.id, "risk_rejected"))
            return OrderExecutionResult(
                order_intent=safe_intent,
                risk_decision=decision,
                order=order,
                audit_logs=audit_logs,
                submitted=False,
            )

        approved_order = self._transition_order(
            self._new_order(safe_intent),
            OrderState.APPROVED,
            "risk_approved",
            audit_logs,
        )
        try:
            audit_logs.append(self._audit("order_intent", safe_intent.id, "before_broker_submission"))
            broker_result = await self.execution_port.place_order(safe_intent)
        except BrokerUnavailableError:
            self.kill_switch.record_broker_error("broker submission failed")
            failed_order = self._transition_order(
                approved_order,
                OrderState.FAILED,
                "broker_submission_failed",
                audit_logs,
            )
            self._save_order(failed_order)
            audit_logs.append(self._audit("order", failed_order.id, "broker_submission_failed"))
            return OrderExecutionResult(
                order_intent=safe_intent,
                risk_decision=decision,
                order=failed_order,
                audit_logs=audit_logs,
                submitted=False,
            )

        final_order = self._validate_broker_order_state_path(approved_order, broker_result.order, audit_logs)
        self._save_order(final_order)
        for execution in broker_result.executions:
            self._save_execution(execution)
        audit_logs.append(self._audit("order", final_order.id, "after_broker_submission"))
        return OrderExecutionResult(
            order_intent=safe_intent,
            risk_decision=decision,
            order=final_order,
            executions=broker_result.executions,
            audit_logs=audit_logs,
            submitted=True,
        )

    def precheck(self, order_intent: OrderIntent, context: RiskContext) -> RiskDecision:
        safe_intent = ensure_idempotency_key(order_intent)
        if self.storage:
            self.storage.save_audit_log(
                AuditLog(entity_type="order_intent", entity_id=safe_intent.id, action="before_risk_check")
            )
        decision = self.risk_engine.evaluate(safe_intent, context)
        if self.storage:
            self.storage.save_risk_decision(decision)
        return decision

    def rejected_order(self, order_intent: OrderIntent) -> Order:
        safe_intent = ensure_idempotency_key(order_intent)
        return self._transition_order(
            self._new_order(safe_intent),
            OrderState.RISK_REJECTED,
            "risk_rejected",
            [],
        )

    def _new_order(self, order_intent: OrderIntent) -> Order:
        return Order(
            order_intent_id=order_intent.id,
            venue=order_intent.venue,
            idempotency_key=str(order_intent.idempotency_key),
            state=OrderState.NEW,
            side=order_intent.side,
            order_type=order_intent.order_type,
            qty=order_intent.qty,
        )

    def _validate_broker_order_state_path(
        self,
        approved_order: Order,
        broker_order: Order,
        audit_logs: list[AuditLog],
    ) -> Order:
        target = broker_order.state
        path: dict[OrderState, list[tuple[OrderState, str]]] = {
            OrderState.SUBMITTED: [(OrderState.SUBMITTED, "broker_submitted")],
            OrderState.PARTIALLY_FILLED: [
                (OrderState.SUBMITTED, "broker_submitted"),
                (OrderState.PARTIALLY_FILLED, "broker_partially_filled"),
            ],
            OrderState.FILLED: [
                (OrderState.SUBMITTED, "broker_submitted"),
                (OrderState.FILLED, "broker_filled"),
            ],
            OrderState.REJECTED: [
                (OrderState.SUBMITTED, "broker_submitted"),
                (OrderState.REJECTED, "broker_rejected"),
            ],
            OrderState.FAILED: [
                (OrderState.SUBMITTED, "broker_submitted"),
                (OrderState.FAILED, "broker_failed"),
            ],
            OrderState.CANCEL_REQUESTED: [
                (OrderState.SUBMITTED, "broker_submitted"),
                (OrderState.CANCEL_REQUESTED, "broker_cancel_requested"),
            ],
            OrderState.CANCELLED: [
                (OrderState.SUBMITTED, "broker_submitted"),
                (OrderState.CANCEL_REQUESTED, "broker_cancel_requested"),
                (OrderState.CANCELLED, "broker_cancelled"),
            ],
            OrderState.UNKNOWN_RECONCILIATION_REQUIRED: [
                (OrderState.SUBMITTED, "broker_submitted"),
                (OrderState.UNKNOWN_RECONCILIATION_REQUIRED, "broker_reconciliation_required"),
            ],
        }
        steps = path.get(target, [(target, "broker_returned_state")])
        current = approved_order
        for state, reason in steps:
            current = self._transition_order(current, state, reason, audit_logs)
        return broker_order

    def _transition_order(
        self,
        order: Order,
        target: OrderState,
        reason: str,
        audit_logs: list[AuditLog],
    ) -> Order:
        from_state = order.state
        next_state = self.state_machine.transition(from_state, target)
        transitioned = order.model_copy(update={"state": next_state})
        audit_logs.append(
            self._audit(
                "order",
                transitioned.id,
                "order_state_transition",
                {
                    "from_state": from_state.value,
                    "to_state": next_state.value,
                    "reason": reason,
                },
            )
        )
        return transitioned

    def _audit(
        self,
        entity_type: str,
        entity_id: str,
        action: str,
        payload: dict[str, object] | None = None,
    ) -> AuditLog:
        audit_log = AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            payload=payload or {},
        )
        if self.storage:
            self.storage.save_audit_log(audit_log)
        return audit_log

    def _save_order_intent(self, order_intent: OrderIntent) -> None:
        if self.storage:
            self.storage.save_order_intent(order_intent)

    def _save_risk_decision(self, decision: RiskDecision) -> None:
        if self.storage:
            self.storage.save_risk_decision(decision)

    def _save_order(self, order: Order) -> None:
        if self.storage:
            self.storage.save_order(order)

    def _save_execution(self, execution: Execution) -> None:
        if self.storage:
            self.storage.save_execution(execution)
