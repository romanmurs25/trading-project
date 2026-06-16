from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from trading_core.config import AppConfig
from trading_core.domain.models import OrderIntent, RiskConfig, utc_now
from trading_core.risk.rules import is_position_reducing


@dataclass
class KillSwitch:
    config: RiskConfig | None = None
    broker_error_threshold: int = 5
    active: bool = False
    reason: str | None = None
    activated_at: datetime | None = None
    broker_error_count: int = 0

    def __post_init__(self) -> None:
        if self.config is None:
            self.config = AppConfig().risk

    def activate(self, reason: str) -> None:
        self.active = True
        self.reason = reason
        self.activated_at = utc_now()

    def deactivate(self) -> None:
        self.active = False
        self.reason = None
        self.activated_at = None
        self.broker_error_count = 0

    def record_broker_error(self, reason: str) -> None:
        self.broker_error_count += 1
        if self.broker_error_count >= self.broker_error_threshold:
            self.activate(f"automatic activation after broker errors: {reason}")

    def record_stale_market_data_breach(self, reason: str) -> None:
        self.activate(f"automatic activation after stale market data breach: {reason}")

    def record_reconciliation_failure(self, reason: str) -> None:
        self.activate(f"automatic activation after reconciliation failure: {reason}")

    def check_daily_loss(self, daily_loss: Decimal, max_loss: Decimal) -> None:
        if daily_loss <= -abs(max_loss):
            self.activate("automatic activation after daily loss limit")

    def check_weekly_loss(self, weekly_loss: Decimal, max_loss: Decimal) -> None:
        if weekly_loss <= -abs(max_loss):
            self.activate("automatic activation after weekly loss limit")

    def allows_order(self, order_intent: OrderIntent, current_position_qty: Decimal) -> bool:
        if not self.active:
            return True
        if not self.config or not self.config.allow_reduce_only_when_killed:
            return False
        return is_position_reducing(order_intent, current_position_qty)
