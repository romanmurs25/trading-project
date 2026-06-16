from typing import Protocol

from trading_core.domain.models import SystemEvent


class EventBusPort(Protocol):
    def publish(self, event: SystemEvent) -> None: ...
