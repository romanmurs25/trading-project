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


@dataclass(frozen=True)
class PaperClosedTrade:
    instrument_id: str
    side_closed: Side
    qty: Decimal
    entry_price: Decimal
    exit_price: Decimal
    entry_commission: Decimal
    exit_commission: Decimal
    gross_pnl: Decimal
    net_pnl: Decimal


@dataclass
class PaperOpenPosition:
    qty: Decimal
    avg_price: Decimal
    entry_commission: Decimal


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
    closed_trades: list[PaperClosedTrade] = field(default_factory=list)
    _idempotency_index: dict[str, tuple[str, list[str]]] = field(default_factory=dict)
    _pending_intents: dict[str, OrderIntent] = field(default_factory=dict)
    _open_positions: dict[str, PaperOpenPosition] = field(default_factory=dict)
    _realized_pnl_by_instrument: dict[str, Decimal] = field(default_factory=dict)

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
        return [trade.net_pnl for trade in self.closed_trades]

    def get_closed_trades(self) -> list[PaperClosedTrade]:
        return list(self.closed_trades)

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

        open_position = self._open_positions.get(execution.instrument_id)
        if open_position is None or open_position.qty == 0:
            self._open_positions[execution.instrument_id] = PaperOpenPosition(
                qty=signed_qty,
                avg_price=execution.price,
                entry_commission=execution.commission,
            )
            self._sync_position(execution.instrument_id, execution.venue)
            return

        if (open_position.qty > 0 and signed_qty > 0) or (open_position.qty < 0 and signed_qty < 0):
            self._increase_position(execution, open_position, signed_qty)
        else:
            self._close_or_reverse_position(execution, open_position, signed_qty)
        self._sync_position(execution.instrument_id, execution.venue)

    def _increase_position(
        self,
        execution: Execution,
        open_position: PaperOpenPosition,
        signed_qty: Decimal,
    ) -> None:
        new_qty = open_position.qty + signed_qty
        existing_notional = abs(open_position.qty) * open_position.avg_price
        execution_notional = execution.qty * execution.price
        self._open_positions[execution.instrument_id] = PaperOpenPosition(
            qty=new_qty,
            avg_price=(existing_notional + execution_notional) / abs(new_qty),
            entry_commission=open_position.entry_commission + execution.commission,
        )

    def _close_or_reverse_position(
        self,
        execution: Execution,
        open_position: PaperOpenPosition,
        signed_qty: Decimal,
    ) -> None:
        close_qty = min(abs(open_position.qty), execution.qty)
        entry_commission = open_position.entry_commission * (close_qty / abs(open_position.qty))
        exit_commission = execution.commission * (close_qty / execution.qty)
        side_closed = Side.BUY if open_position.qty > 0 else Side.SELL
        if side_closed == Side.BUY:
            gross_pnl = (execution.price - open_position.avg_price) * close_qty
        else:
            gross_pnl = (open_position.avg_price - execution.price) * close_qty
        net_pnl = gross_pnl - entry_commission - exit_commission
        self._record_closed_trade(
            PaperClosedTrade(
                instrument_id=execution.instrument_id,
                side_closed=side_closed,
                qty=close_qty,
                entry_price=open_position.avg_price,
                exit_price=execution.price,
                entry_commission=entry_commission,
                exit_commission=exit_commission,
                gross_pnl=gross_pnl,
                net_pnl=net_pnl,
            )
        )

        remaining_open_qty = abs(open_position.qty) - close_qty
        remaining_execution_qty = execution.qty - close_qty
        if remaining_open_qty > 0:
            direction = Decimal("1") if open_position.qty > 0 else Decimal("-1")
            self._open_positions[execution.instrument_id] = PaperOpenPosition(
                qty=direction * remaining_open_qty,
                avg_price=open_position.avg_price,
                entry_commission=open_position.entry_commission - entry_commission,
            )
            return
        if remaining_execution_qty > 0:
            direction = Decimal("1") if signed_qty > 0 else Decimal("-1")
            self._open_positions[execution.instrument_id] = PaperOpenPosition(
                qty=direction * remaining_execution_qty,
                avg_price=execution.price,
                entry_commission=execution.commission - exit_commission,
            )
            return
        self._open_positions[execution.instrument_id] = PaperOpenPosition(
            qty=Decimal("0"),
            avg_price=execution.price,
            entry_commission=Decimal("0"),
        )

    def _record_closed_trade(self, trade: PaperClosedTrade) -> None:
        self.closed_trades.append(trade)
        self.closed_trade_pnls.append(trade.net_pnl)
        self._realized_pnl_by_instrument[trade.instrument_id] = (
            self._realized_pnl_by_instrument.get(trade.instrument_id, Decimal("0")) + trade.net_pnl
        )

    def _sync_position(self, instrument_id: str, venue: Venue) -> None:
        open_position = self._open_positions[instrument_id]
        realized_pnl = self._realized_pnl_by_instrument.get(instrument_id, Decimal("0"))
        self.positions[instrument_id] = Position(
            instrument_id=instrument_id,
            venue=venue,
            qty=open_position.qty,
            avg_price=open_position.avg_price,
            realized_pnl=realized_pnl,
        )
        self._mark_position(instrument_id)

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
