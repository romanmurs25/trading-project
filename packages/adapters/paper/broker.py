from dataclasses import dataclass, field
from decimal import Decimal

from trading_core.domain.enums import OrderState, OrderType, Side, Venue
from trading_core.domain.errors import BrokerUnavailableError
from trading_core.domain.models import Execution, Order, OrderIntent, Position, utc_now


@dataclass(frozen=True)
class PaperMarket:
    bid: Decimal
    ask: Decimal
    last: Decimal


@dataclass
class PaperBroker:
    """Sync paper simulator.

    latency_ms зарезервирован и не влияет на исполнение в MVP.
    Duplicate idempotency key возвращает исходный order/executions без повторного исполнения.
    Reversal закрывает текущую позицию и открывает остаток по средней цене нового исполнения.
    """

    initial_cash: Decimal = Decimal("100000")
    commission_rate: Decimal = Decimal("0")
    slippage: Decimal = Decimal("0")
    latency_ms: int = 0
    cash: Decimal = field(init=False)
    positions: dict[str, Position] = field(default_factory=dict)
    orders: dict[str, Order] = field(default_factory=dict)
    executions: list[Execution] = field(default_factory=list)
    markets: dict[str, PaperMarket] = field(default_factory=dict)
    closed_trade_pnls: list[Decimal] = field(default_factory=list)
    _idempotency_index: dict[str, tuple[str, list[str]]] = field(default_factory=dict)
    _pending_intents: dict[str, OrderIntent] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.cash = self.initial_cash

    def set_market(self, instrument_id: str, bid: Decimal, ask: Decimal, last: Decimal) -> None:
        if bid <= 0 or ask <= 0 or ask < bid:
            raise BrokerUnavailableError("invalid paper market quote")
        self.markets[instrument_id] = PaperMarket(bid=bid, ask=ask, last=last)
        self._mark_position(instrument_id)

    def place_order(self, order_intent: OrderIntent) -> tuple[Order, list[Execution]]:
        existing = self._existing_result(order_intent)
        if existing is not None:
            return existing
        market = self.markets.get(order_intent.instrument_id)
        if market is None:
            raise BrokerUnavailableError(f"no paper market for {order_intent.instrument_id}")

        order = Order(
            order_intent_id=order_intent.id,
            venue=Venue.PAPER,
            broker_order_id=f"paper-{len(self.orders) + 1}",
            idempotency_key=str(order_intent.idempotency_key),
            state=OrderState.SUBMITTED,
            side=order_intent.side,
            order_type=order_intent.order_type,
            qty=order_intent.qty,
        )

        fill_price = self._fill_price(order_intent, market)
        if fill_price is None:
            self.orders[order.id] = order
            self._pending_intents[order.id] = order_intent
            self._remember_idempotency(order_intent, order, [])
            return order, []

        executions = self._fill_order(order, order_intent, fill_price)
        self._remember_idempotency(order_intent, self.orders[order.id], executions)
        return self.orders[order.id], executions

    def process_pending_orders(self) -> list[Execution]:
        all_executions: list[Execution] = []
        for order in list(self.orders.values()):
            if order.state != OrderState.SUBMITTED:
                continue
            intent = self._pending_intents.get(order.id)
            if intent is None:
                continue
            market = self.markets.get(intent.instrument_id)
            if market is None:
                continue
            fill_price = self._fill_price(intent, market)
            if fill_price is None:
                continue
            executions = self._fill_order(order, intent, fill_price)
            self._pending_intents.pop(order.id, None)
            self._remember_idempotency(intent, self.orders[order.id], executions)
            all_executions.extend(executions)
        return all_executions

    def final_equity(self) -> Decimal:
        equity = self.cash
        for instrument_id, position in self.positions.items():
            market = self.markets.get(instrument_id)
            if market is None:
                continue
            mark = market.bid if position.qty >= 0 else market.ask
            equity += position.qty * mark
        return equity

    def get_position(self, instrument_id: str) -> Position | None:
        return self.positions.get(instrument_id)

    def get_closed_trade_pnls(self) -> list[Decimal]:
        return list(self.closed_trade_pnls)

    def get_executions(self) -> list[Execution]:
        return list(self.executions)

    def _fill_price(self, order_intent: OrderIntent, market: PaperMarket) -> Decimal | None:
        if order_intent.order_type == OrderType.MARKET:
            return self._market_fill_price(order_intent.side, market)
        if order_intent.order_type == OrderType.LIMIT:
            if order_intent.limit_price is None:
                return None
            if order_intent.side == Side.BUY and order_intent.limit_price >= market.ask:
                return self._market_fill_price(order_intent.side, market)
            if order_intent.side == Side.SELL and order_intent.limit_price <= market.bid:
                return self._market_fill_price(order_intent.side, market)
        return None

    def _market_fill_price(self, side: Side, market: PaperMarket) -> Decimal:
        if side == Side.BUY:
            return market.ask + self.slippage
        return market.bid - self.slippage

    def _apply_execution(self, execution: Execution) -> None:
        signed_qty = execution.qty if execution.side == Side.BUY else -execution.qty
        gross = execution.price * execution.qty
        if execution.side == Side.BUY:
            self.cash -= gross + execution.commission
        else:
            self.cash += gross - execution.commission

        existing = self.positions.get(execution.instrument_id)
        if existing is None or existing.qty == 0:
            self.positions[execution.instrument_id] = Position(
                instrument_id=execution.instrument_id,
                venue=execution.venue,
                qty=signed_qty,
                avg_price=execution.price,
                realized_pnl=Decimal("0") - execution.commission,
            )
            self._mark_position(execution.instrument_id)
            return

        new_qty = existing.qty + signed_qty
        realized_delta = self._realized_delta(existing, execution)
        entry_commission_allocated = self._entry_commission_for_closed_qty(existing, execution)
        if new_qty == 0:
            avg_price = execution.price
        elif (existing.qty > 0 and signed_qty > 0) or (existing.qty < 0 and signed_qty < 0):
            existing_notional = abs(existing.qty) * existing.avg_price
            execution_notional = execution.qty * execution.price
            avg_price = (existing_notional + execution_notional) / abs(new_qty)
        else:
            avg_price = existing.avg_price if abs(new_qty) < abs(existing.qty) else execution.price

        self.positions[execution.instrument_id] = existing.model_copy(
            update={
                "qty": new_qty,
                "avg_price": avg_price,
                "realized_pnl": (
                    existing.realized_pnl + realized_delta - execution.commission - entry_commission_allocated
                ),
                "updated_at": utc_now(),
            }
        )
        if realized_delta != 0:
            self.closed_trade_pnls.append(realized_delta - execution.commission - entry_commission_allocated)
        self._mark_position(execution.instrument_id)

    def _realized_delta(self, position: Position, execution: Execution) -> Decimal:
        if position.qty > 0 and execution.side == Side.SELL:
            closing_qty = min(position.qty, execution.qty)
            return (execution.price - position.avg_price) * closing_qty
        if position.qty < 0 and execution.side == Side.BUY:
            closing_qty = min(abs(position.qty), execution.qty)
            return (position.avg_price - execution.price) * closing_qty
        return Decimal("0")

    def _mark_position(self, instrument_id: str) -> None:
        position = self.positions.get(instrument_id)
        market = self.markets.get(instrument_id)
        if position is None or market is None:
            return
        mark = market.bid if position.qty >= 0 else market.ask
        unrealized = (mark - position.avg_price) * position.qty
        self.positions[instrument_id] = position.model_copy(
            update={"unrealized_pnl": unrealized, "updated_at": utc_now()}
        )

    def _fill_order(self, order: Order, order_intent: OrderIntent, fill_price: Decimal) -> list[Execution]:
        commission = fill_price * order_intent.qty * self.commission_rate
        execution = Execution(
            order_id=order.id,
            venue=Venue.PAPER,
            broker_execution_id=f"paper-exec-{len(self.executions) + 1}",
            instrument_id=order_intent.instrument_id,
            side=order_intent.side,
            qty=order_intent.qty,
            price=fill_price,
            commission=commission,
            ts=utc_now(),
        )
        filled_order = order.model_copy(
            update={
                "state": OrderState.FILLED,
                "filled_qty": order_intent.qty,
                "avg_fill_price": fill_price,
                "updated_at": utc_now(),
            }
        )
        self._apply_execution(execution)
        self.orders[order.id] = filled_order
        self.executions.append(execution)
        return [execution]

    def _existing_result(self, order_intent: OrderIntent) -> tuple[Order, list[Execution]] | None:
        key = order_intent.idempotency_key
        if not key or key not in self._idempotency_index:
            return None
        order_id, execution_ids = self._idempotency_index[key]
        executions = [execution for execution in self.executions if execution.id in execution_ids]
        return self.orders[order_id], executions

    def _remember_idempotency(
        self,
        order_intent: OrderIntent,
        order: Order,
        executions: list[Execution],
    ) -> None:
        if order_intent.idempotency_key:
            self._idempotency_index[order_intent.idempotency_key] = (
                order.id,
                [execution.id for execution in executions],
            )

    def _entry_commission_for_closed_qty(self, position: Position, execution: Execution) -> Decimal:
        closes_long = position.qty > 0 and execution.side == Side.SELL
        closes_short = position.qty < 0 and execution.side == Side.BUY
        if closes_long or closes_short:
            closing_qty = min(abs(position.qty), execution.qty)
            if abs(position.qty) == 0:
                return Decimal("0")
            total_entry_commission = abs(position.realized_pnl) if position.realized_pnl < 0 else Decimal("0")
            return total_entry_commission * (closing_qty / abs(position.qty))
        return Decimal("0")
