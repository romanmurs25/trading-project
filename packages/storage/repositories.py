from dataclasses import dataclass, field

from trading_core.domain.models import AuditLog, SystemEvent


@dataclass
class InMemoryAuditStore:
    audit_logs: list[AuditLog] = field(default_factory=list)
    system_events: list[SystemEvent] = field(default_factory=list)

    def save_audit_log(self, audit_log: AuditLog) -> None:
        self.audit_logs.append(audit_log)

    def save_system_event(self, event: SystemEvent) -> None:
        self.system_events.append(event)
