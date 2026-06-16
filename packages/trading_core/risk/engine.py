from datetime import timedelta
from decimal import Decimal

from trading_core.domain.enums import OrderType, TradingMode, Venue
from trading_core.domain.models import OrderIntent, RiskConfig, RiskContext, RiskDecision
from trading_core.risk.kill_switch import KillSwitch
from trading_core.risk.rules import is_new_position, is_position_reducing, signed_order_qty


class RiskEngine:
    def __init__(
        self,
        config: RiskConfig,
        kill_switch: KillSwitch | None = None,
        seen_idempotency_keys: set[str] | None = None,
    ) -> None:
        self.config = config
        self.kill_switch = kill_switch or KillSwitch(config)
        self.seen_idempotency_keys = seen_idempotency_keys if seen_idempotency_keys is not None else set()

    def evaluate(self, order_intent: OrderIntent, context: RiskContext) -> RiskDecision:
        checks: dict[str, bool] = {}

        checks["idempotency_key_present"] = bool(order_intent.idempotency_key)
        checks["idempotency_key_is_new"] = self._idempotency_key_is_new(order_intent)

        checks["kill_switch"] = self.kill_switch.allows_order(
            order_intent,
            current_position_qty=context.current_position_qty,
        )
        checks["live_allowlist_non_empty"] = (
            self.config.trading_mode != TradingMode.LIVE_GUARDED or bool(self.config.instrument_allowlist)
        )
        checks["instrument_allowlisted"] = self._instrument_allowed(context)
        checks["session_allows_trading"] = context.session_allows_trading
        checks["account_available"] = context.account_available
        checks["market_data_fresh"] = context.now - context.market_data_ts <= timedelta(
            seconds=self.config.stale_data_seconds
        )
        checks["spread_within_limit"] = (
            self._spread_bps(context.bid, context.ask) <= self.config.max_spread_bps
        )
        checks["max_order_qty"] = order_intent.qty <= self.config.max_order_qty
        checks["max_notional_exposure"] = (
            self._notional(order_intent, context) <= self.config.max_notional_exposure
        )
        checks["max_position_size"] = abs(context.current_position_qty + self._signed_qty(order_intent)) <= (
            self.config.max_position_size
        )
        checks["max_open_positions"] = self._max_open_positions_allows(order_intent, context)
        checks["max_risk_per_trade"] = (
            self._risk_amount(order_intent, context) <= self._max_risk_amount(context)
        )
        checks["daily_loss_limit"] = abs(min(context.daily_pnl, Decimal("0"))) <= self._loss_limit(
            context.portfolio_value,
            self.config.max_daily_loss_pct,
        )
        checks["weekly_loss_limit"] = abs(min(context.weekly_pnl, Decimal("0"))) <= self._loss_limit(
            context.portfolio_value,
            self.config.max_weekly_loss_pct,
        )

        if self.config.trading_mode == TradingMode.LIVE_GUARDED or order_intent.venue != Venue.PAPER:
            checks["live_trading_enabled"] = (
                self.config.trading_mode == TradingMode.LIVE_GUARDED
                and self.config.allow_live_trading
                and context.broker_supports_live
                and not context.adapter_read_only
            )
            checks["market_orders_live_allowed"] = (
                order_intent.order_type != OrderType.MARKET or self.config.allow_market_orders_live
            )
        else:
            checks["live_trading_enabled"] = True
            checks["market_orders_live_allowed"] = True

        failed = [name for name, passed in checks.items() if not passed]
        if failed:
            return RiskDecision(
                order_intent_id=order_intent.id,
                approved=False,
                reason=f"failed checks: {', '.join(failed)}",
                checks=checks,
                max_loss_after_trade=self._risk_amount(order_intent, context),
            )

        if order_intent.idempotency_key:
            self.seen_idempotency_keys.add(order_intent.idempotency_key)
        return RiskDecision(
            order_intent_id=order_intent.id,
            approved=True,
            reason="approved",
            checks=checks,
            adjusted_qty=order_intent.qty,
            max_loss_after_trade=self._risk_amount(order_intent, context),
        )

    def _instrument_allowed(self, context: RiskContext) -> bool:
        if not self.config.instrument_allowlist:
            return self.config.trading_mode != TradingMode.LIVE_GUARDED
        allowed = set(self.config.instrument_allowlist)
        return context.instrument.id in allowed or context.instrument.canonical_symbol in allowed

    def _idempotency_key_is_new(self, order_intent: OrderIntent) -> bool:
        if not order_intent.idempotency_key:
            return False
        return order_intent.idempotency_key not in self.seen_idempotency_keys

    def _spread_bps(self, bid: Decimal, ask: Decimal) -> Decimal:
        if bid <= 0 or ask <= 0:
            return Decimal("999999")
        mid = (bid + ask) / Decimal("2")
        return ((ask - bid) / mid) * Decimal("10000")

    def _price_for_notional(self, order_intent: OrderIntent, context: RiskContext) -> Decimal:
        if order_intent.limit_price is not None:
            return order_intent.limit_price
        if order_intent.side.value == "BUY":
            return context.ask
        return context.bid

    def _notional(self, order_intent: OrderIntent, context: RiskContext) -> Decimal:
        return order_intent.qty * self._price_for_notional(order_intent, context)

    def _risk_amount(self, order_intent: OrderIntent, context: RiskContext) -> Decimal:
        if order_intent.risk_amount is not None:
            return order_intent.risk_amount
        if order_intent.stop_loss is not None:
            price_risk = abs(self._price_for_notional(order_intent, context) - order_intent.stop_loss)
            return price_risk * order_intent.qty
        return Decimal("0")

    def _max_risk_amount(self, context: RiskContext) -> Decimal:
        return context.portfolio_value * (self.config.max_risk_per_trade_pct / Decimal("100"))

    def _loss_limit(self, portfolio_value: Decimal, pct: Decimal) -> Decimal:
        return portfolio_value * (pct / Decimal("100"))

    def _signed_qty(self, order_intent: OrderIntent) -> Decimal:
        return signed_order_qty(order_intent)

    def _max_open_positions_allows(self, order_intent: OrderIntent, context: RiskContext) -> bool:
        if is_position_reducing(order_intent, context.current_position_qty):
            return True
        if is_new_position(order_intent, context.current_position_qty):
            return context.open_positions_count < self.config.max_open_positions
        return context.open_positions_count <= self.config.max_open_positions
