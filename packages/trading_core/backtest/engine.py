from dataclasses import dataclass
from decimal import Decimal
from typing import cast

from trading_core.backtest.metrics import expectancy, max_drawdown, profit_factor, win_rate
from trading_core.domain.enums import OrderType, Side, SignalDirection, TimeInForce
from trading_core.domain.models import Candle, Instrument, OrderIntent, RiskContext, Signal
from trading_core.ports.backtest_broker import BacktestBrokerPort, ClosedTradeProvider
from trading_core.research.models import BacktestEquityPoint, BacktestTradeRecord
from trading_core.risk.engine import RiskEngine
from trading_core.strategy.base import Strategy


@dataclass(frozen=True)
class BacktestResult:
    total_pnl: Decimal
    final_equity: Decimal
    max_drawdown: Decimal
    win_rate: Decimal
    avg_win: Decimal
    avg_loss: Decimal
    profit_factor: Decimal
    expectancy: Decimal
    avg_r: Decimal
    trades_count: int
    closed_trades_count: int
    rejected_signals_count: int
    executions_count: int
    exposure_bars: int
    metrics: dict[str, Decimal]
    equity_curve: list[BacktestEquityPoint]
    trade_records: list[BacktestTradeRecord]


@dataclass
class ActiveExitPlan:
    direction: SignalDirection
    stop_loss: Decimal | None
    take_profit: Decimal | None


class BacktestEngine:
    def __init__(self, strategy: Strategy, risk_engine: RiskEngine, broker: BacktestBrokerPort) -> None:
        self.strategy = strategy
        self.risk_engine = risk_engine
        self.broker = broker

    def run(self, candles: list[Candle], instrument: Instrument) -> BacktestResult:
        history: list[Candle] = []
        equity_values: list[tuple[Candle | None, Decimal]] = [(None, self.broker.initial_cash)]
        rejected_signals_count = 0
        exposure_bars = 0
        active_exit_plan: ActiveExitPlan | None = None

        for candle in candles:
            bid = candle.close - Decimal("0.05")
            ask = candle.close + Decimal("0.05")
            self.broker.set_market(instrument.id, bid=bid, ask=ask, last=candle.close)
            self.broker.process_pending_orders()

            active_exit_plan = self._maybe_exit_position(candle, instrument, active_exit_plan)
            exposure_position = self.broker.get_position(instrument.id)
            if exposure_position is not None and exposure_position.qty != 0:
                exposure_bars += 1

            history.append(candle)
            signal = self.strategy.on_candle(candle, history)
            if signal is None or self._has_open_position(instrument.id):
                equity_values.append((candle, self.broker.final_equity()))
                continue

            intent = self._intent_from_signal(signal, instrument)
            current_position = self.broker.get_position(instrument.id)
            decision = self.risk_engine.evaluate(
                intent,
                RiskContext(
                    instrument=instrument,
                    now=candle.ts_end,
                    market_data_ts=candle.ts_end,
                    bid=bid,
                    ask=ask,
                    portfolio_value=self.broker.final_equity(),
                    current_position_qty=current_position.qty if current_position else Decimal("0"),
                ),
            )
            if decision.approved:
                self.broker.place_order(intent)
                active_exit_plan = ActiveExitPlan(
                    direction=signal.direction,
                    stop_loss=signal.stop_loss,
                    take_profit=signal.take_profit,
                )
            else:
                rejected_signals_count += 1
            equity_values.append((candle, self.broker.final_equity()))

        if candles and self._has_open_position(instrument.id):
            self._force_close_position(candles[-1], instrument)
            equity_values.append((candles[-1], self.broker.final_equity()))

        final_equity = self.broker.final_equity()
        total_pnl = final_equity - self.broker.initial_cash
        trade_pnls = self.broker.get_closed_trade_pnls()
        result_profit_factor = profit_factor(trade_pnls)
        result_expectancy = expectancy(trade_pnls)
        result_win_rate = win_rate(trade_pnls)
        equity_points = self._equity_points(equity_values)
        result_max_drawdown = max_drawdown([point.equity for point in equity_points])
        wins = [pnl for pnl in trade_pnls if pnl > 0]
        losses = [pnl for pnl in trade_pnls if pnl < 0]
        avg_win = sum(wins, Decimal("0")) / Decimal(len(wins)) if wins else Decimal("0")
        avg_loss = sum(losses, Decimal("0")) / Decimal(len(losses)) if losses else Decimal("0")
        executions_count = len(self.broker.get_executions())
        closed_trades_count = len(trade_pnls)
        return BacktestResult(
            total_pnl=total_pnl,
            final_equity=final_equity,
            max_drawdown=result_max_drawdown,
            win_rate=result_win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=result_profit_factor,
            expectancy=result_expectancy,
            avg_r=result_expectancy,
            trades_count=executions_count,
            closed_trades_count=closed_trades_count,
            rejected_signals_count=rejected_signals_count,
            executions_count=executions_count,
            exposure_bars=exposure_bars,
            metrics={
                "total_pnl": total_pnl,
                "final_equity": final_equity,
                "max_drawdown": result_max_drawdown,
                "win_rate": result_win_rate,
                "avg_win": avg_win,
                "avg_loss": avg_loss,
                "profit_factor": result_profit_factor,
                "expectancy": result_expectancy,
                "avg_r": result_expectancy,
                "trades_count": Decimal(executions_count),
                "closed_trades_count": Decimal(closed_trades_count),
                "rejected_signals_count": Decimal(rejected_signals_count),
                "executions_count": Decimal(executions_count),
                "exposure_bars": Decimal(exposure_bars),
            },
            equity_curve=equity_points,
            trade_records=self._trade_records(),
        )

    def _intent_from_signal(self, signal: Signal, instrument: Instrument) -> OrderIntent:
        side = Side.BUY if signal.direction == SignalDirection.LONG else Side.SELL
        risk_amount = abs(signal.price - signal.stop_loss) if signal.stop_loss is not None else Decimal("0")
        return OrderIntent(
            strategy_id=signal.strategy_id,
            signal_id=signal.id,
            venue=instrument.venue,
            instrument_id=instrument.id,
            side=side,
            order_type=OrderType.MARKET,
            qty=Decimal("1"),
            time_in_force=TimeInForce.DAY,
            reason=signal.reason,
            risk_amount=risk_amount,
            idempotency_key=f"bt-{signal.id}",
        )

    def _maybe_exit_position(
        self,
        candle: Candle,
        instrument: Instrument,
        active_exit_plan: ActiveExitPlan | None,
    ) -> ActiveExitPlan | None:
        if active_exit_plan is None or not self._has_open_position(instrument.id):
            return active_exit_plan
        exit_price = self._exit_price(candle, active_exit_plan)
        if exit_price is None:
            return active_exit_plan
        self._close_position_at(candle, instrument, exit_price, "planned exit")
        return None

    def _exit_price(self, candle: Candle, exit_plan: ActiveExitPlan) -> Decimal | None:
        # Консервативно считаем, что если stop и take-profit достигнуты в одной свече, stop был первым.
        if exit_plan.direction == SignalDirection.LONG:
            if exit_plan.stop_loss is not None and candle.low <= exit_plan.stop_loss:
                return exit_plan.stop_loss
            if exit_plan.take_profit is not None and candle.high >= exit_plan.take_profit:
                return exit_plan.take_profit
        if exit_plan.direction == SignalDirection.SHORT:
            if exit_plan.stop_loss is not None and candle.high >= exit_plan.stop_loss:
                return exit_plan.stop_loss
            if exit_plan.take_profit is not None and candle.low <= exit_plan.take_profit:
                return exit_plan.take_profit
        return None

    def _force_close_position(self, candle: Candle, instrument: Instrument) -> None:
        self._close_position_at(candle, instrument, candle.close, "forced close at end")

    def _close_position_at(self, candle: Candle, instrument: Instrument, price: Decimal, reason: str) -> None:
        position = self.broker.get_position(instrument.id)
        if position is None or position.qty == 0:
            return
        self.broker.set_market(instrument.id, bid=price, ask=price, last=price)
        side = Side.SELL if position.qty > 0 else Side.BUY
        self.broker.place_order(
            OrderIntent(
                strategy_id=self.strategy.strategy_id,
                signal_id=None,
                venue=instrument.venue,
                instrument_id=instrument.id,
                side=side,
                order_type=OrderType.MARKET,
                qty=abs(position.qty),
                time_in_force=TimeInForce.DAY,
                reason=reason,
                risk_amount=Decimal("0"),
                idempotency_key=f"bt-exit-{instrument.id}-{candle.ts_end.isoformat()}-{reason}",
            )
        )

    def _has_open_position(self, instrument_id: str) -> bool:
        position = self.broker.get_position(instrument_id)
        return position is not None and position.qty != 0

    def _equity_points(self, equity_values: list[tuple[Candle | None, Decimal]]) -> list[BacktestEquityPoint]:
        points: list[BacktestEquityPoint] = []
        peak: Decimal | None = None
        first_candle = next((candle for candle, _equity in equity_values if candle is not None), None)
        for candle, equity in equity_values:
            peak = equity if peak is None else max(peak, equity)
            drawdown = Decimal("0") if peak <= 0 else (peak - equity) / peak
            ts = (
                candle.ts_end
                if candle is not None
                else first_candle.ts_start
                if first_candle is not None
                else None
            )
            if ts is None:
                continue
            points.append(
                BacktestEquityPoint(
                    backtest_run_id="pending",
                    ts=ts,
                    equity=equity,
                    drawdown=drawdown,
                )
            )
        return points

    def _trade_records(self) -> list[BacktestTradeRecord]:
        if not hasattr(self.broker, "get_closed_trades"):
            return []
        closed_trade_provider = cast(ClosedTradeProvider, self.broker)
        return [
            BacktestTradeRecord(
                backtest_run_id="pending",
                instrument_id=trade.instrument_id,
                side=trade.side_closed,
                entry_price=trade.entry_price,
                exit_price=trade.exit_price,
                qty=trade.qty,
                gross_pnl=trade.gross_pnl,
                net_pnl=trade.net_pnl,
                r_multiple=None,
                reason="paper closed trade",
            )
            for trade in closed_trade_provider.get_closed_trades()
        ]
