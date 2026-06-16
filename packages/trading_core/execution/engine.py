from dataclasses import dataclass, field

from trading_core.domain.enums import OrderState
from trading_core.domain.errors import BrokerUnavailableError
from trading_core.domain.models import AuditLog, Execution, Order, OrderIntent, RiskContext, RiskDecision
from trading_core.execution.idempotency import ensure_idempotency_key
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
            order = self.rejected_order(safe_intent)
            self._save_order(order)
            audit_logs.append(self._audit("order", order.id, "risk_rejected"))
            return OrderExecutionResult(
                order_intent=safe_intent,
                risk_decision=decision,
                order=order,
                audit_logs=audit_logs,
                submitted=False,
            )

        approved_order = self._new_order(safe_intent, OrderState.APPROVED)
        try:
            audit_logs.append(self._audit("order_intent", safe_intent.id, "before_broker_submission"))
            broker_result = await self.execution_port.place_order(safe_intent)
        except BrokerUnavailableError:
            self.kill_switch.record_broker_error("broker submission failed")
            failed_order = approved_order.model_copy(update={"state": OrderState.FAILED})
            self._save_order(failed_order)
            audit_logs.append(self._audit("order", failed_order.id, "broker_submission_failed"))
            return OrderExecutionResult(
                order_intent=safe_intent,
                risk_decision=decision,
                order=failed_order,
                audit_logs=audit_logs,
                submitted=False,
            )

        self._save_order(broker_result.order)
        for execution in broker_result.executions:
            self._save_execution(execution)
        audit_logs.append(self._audit("order", broker_result.order.id, "after_broker_submission"))
        return OrderExecutionResult(
            order_intent=safe_intent,
            risk_decision=decision,
            order=broker_result.order,
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
        return self._new_order(safe_intent, OrderState.RISK_REJECTED)

    def _new_order(self, order_intent: OrderIntent, state: OrderState) -> Order:
        return Order(
            order_intent_id=order_intent.id,
            venue=order_intent.venue,
            idempotency_key=str(order_intent.idempotency_key),
            state=state,
            side=order_intent.side,
            order_type=order_intent.order_type,
            qty=order_intent.qty,
        )

    def _audit(self, entity_type: str, entity_id: str, action: str) -> AuditLog:
        audit_log = AuditLog(entity_type=entity_type, entity_id=entity_id, action=action)
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
