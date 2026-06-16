from decimal import Decimal

from trading_core.domain.enums import Side
from trading_core.domain.models import OrderIntent


def signed_order_qty(order_intent: OrderIntent) -> Decimal:
    if order_intent.side == Side.BUY:
        return order_intent.qty
    return -order_intent.qty


def is_position_reducing(order_intent: OrderIntent, current_position_qty: Decimal) -> bool:
    if current_position_qty > 0:
        return order_intent.side == Side.SELL and order_intent.qty <= current_position_qty
    if current_position_qty < 0:
        return order_intent.side == Side.BUY and order_intent.qty <= abs(current_position_qty)
    return False


def is_new_position(order_intent: OrderIntent, current_position_qty: Decimal) -> bool:
    return current_position_qty == 0 and order_intent.qty > 0
