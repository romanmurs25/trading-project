from decimal import Decimal


def profit_factor(pnls: list[Decimal]) -> Decimal:
    gross_profit = sum((pnl for pnl in pnls if pnl > 0), Decimal("0"))
    gross_loss = abs(sum((pnl for pnl in pnls if pnl < 0), Decimal("0")))
    if gross_loss == 0:
        return gross_profit if gross_profit > 0 else Decimal("0")
    return gross_profit / gross_loss


def expectancy(pnls: list[Decimal]) -> Decimal:
    if not pnls:
        return Decimal("0")
    return sum(pnls, Decimal("0")) / Decimal(len(pnls))


def win_rate(pnls: list[Decimal]) -> Decimal:
    if not pnls:
        return Decimal("0")
    wins = sum(1 for pnl in pnls if pnl > 0)
    return Decimal(wins) / Decimal(len(pnls))


def max_drawdown(equity_curve: list[Decimal]) -> Decimal:
    peak: Decimal | None = None
    worst = Decimal("0")
    for equity in equity_curve:
        peak = equity if peak is None else max(peak, equity)
        if peak and peak > 0:
            drawdown = (peak - equity) / peak
            worst = max(worst, drawdown)
    return worst
