from datetime import UTC, datetime, timedelta
from decimal import Decimal

from adapters.paper.broker import PaperBroker
from trading_core.backtest.engine import BacktestEngine
from trading_core.domain.enums import SignalDirection, Venue
from trading_core.domain.models import Candle, Instrument, RiskConfig
from trading_core.risk.engine import RiskEngine
from trading_core.risk.kill_switch import KillSwitch
from trading_core.strategy.opening_range_breakout import OpeningRangeBreakoutStrategy


def make_instrument() -> Instrument:
    return Instrument(
        id="moex-si",
        venue=Venue.PAPER,
        asset_class="FUTURES",
        native_symbol="SiH6",
        canonical_symbol="MOEX:SIH6",
        name="Si futures",
        lot_size=Decimal("1"),
        tick_size=Decimal("1"),
        tick_value=Decimal("1"),
        currency="RUB",
    )


def test_backtest_engine_runs_on_synthetic_candles() -> None:
    start = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
    candles = [
        Candle(
            instrument_id="moex-si",
            venue=Venue.PAPER,
            interval="1m",
            ts_start=start + timedelta(minutes=i),
            ts_end=start + timedelta(minutes=i + 1),
            open=Decimal("100") + Decimal(i),
            high=Decimal("101") + Decimal(i),
            low=Decimal("99") + Decimal(i),
            close=Decimal("100") + Decimal(i),
            volume=Decimal("1000"),
            source="synthetic",
        )
        for i in range(6)
    ]
    risk_config = RiskConfig(instrument_allowlist=["moex-si"])
    engine = BacktestEngine(
        strategy=OpeningRangeBreakoutStrategy(opening_range_minutes=2),
        risk_engine=RiskEngine(risk_config, KillSwitch()),
        broker=PaperBroker(initial_cash=Decimal("100000")),
    )

    result = engine.run(candles=candles, instrument=make_instrument())

    assert result.trades_count >= 1
    assert result.final_equity > Decimal("0")
    assert result.metrics["profit_factor"] >= Decimal("0")


class OneShotSignalStrategy:
    strategy_id = "one_shot"

    def __init__(
        self,
        direction: SignalDirection = SignalDirection.LONG,
        stop_loss: Decimal = Decimal("98"),
        take_profit: Decimal = Decimal("104"),
    ) -> None:
        self.direction = direction
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.sent = False

    def on_candle(self, candle: Candle, history: list[Candle]):
        if self.sent or len(history) == 1:
            return None
        self.sent = True
        from trading_core.domain.models import Signal

        return Signal(
            strategy_id=self.strategy_id,
            instrument_id=candle.instrument_id,
            venue=candle.venue,
            direction=self.direction,
            ts=candle.ts_end,
            price=candle.close,
            stop_loss=self.stop_loss,
            take_profit=self.take_profit,
            reason="one shot",
        )


def make_candles_with_prices(prices: list[tuple[str, str, str]]) -> list[Candle]:
    start = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
    return [
        Candle(
            instrument_id="moex-si",
            venue=Venue.PAPER,
            interval="1m",
            ts_start=start + timedelta(minutes=i),
            ts_end=start + timedelta(minutes=i + 1),
            open=Decimal(open_price),
            high=Decimal(high),
            low=Decimal(low),
            close=Decimal(open_price),
            volume=Decimal("1000"),
            source="synthetic",
        )
        for i, (open_price, high, low) in enumerate(prices)
    ]


def make_backtest(strategy: object, risk_config: RiskConfig | None = None) -> BacktestEngine:
    config = risk_config or RiskConfig(trading_mode="PAPER", instrument_allowlist=["moex-si"])
    return BacktestEngine(
        strategy=strategy,
        risk_engine=RiskEngine(config, KillSwitch()),
        broker=PaperBroker(initial_cash=Decimal("100000")),
    )


def test_backtest_closes_position_by_take_profit() -> None:
    result = make_backtest(OneShotSignalStrategy(take_profit=Decimal("103"))).run(
        candles=make_candles_with_prices([
            ("100", "101", "99"),
            ("101", "102", "100"),
            ("102", "104", "101"),
        ]),
        instrument=make_instrument(),
    )

    assert result.closed_trades_count == 1
    assert result.executions_count == 2
    assert result.total_pnl > Decimal("0")


def test_backtest_closes_position_by_stop_loss() -> None:
    result = make_backtest(OneShotSignalStrategy(stop_loss=Decimal("99"), take_profit=Decimal("110"))).run(
        candles=make_candles_with_prices([("100", "101", "99"), ("101", "102", "100"), ("100", "101", "98")]),
        instrument=make_instrument(),
    )

    assert result.closed_trades_count == 1
    assert result.total_pnl < Decimal("0")


def test_backtest_force_closes_open_position_at_end() -> None:
    result = make_backtest(OneShotSignalStrategy(stop_loss=Decimal("90"), take_profit=Decimal("120"))).run(
        candles=make_candles_with_prices([
            ("100", "101", "99"),
            ("101", "102", "100"),
            ("102", "103", "101"),
        ]),
        instrument=make_instrument(),
    )

    assert result.closed_trades_count == 1
    assert result.executions_count == 2


def test_backtest_counts_rejected_risk_signals() -> None:
    result = make_backtest(
        OneShotSignalStrategy(),
        RiskConfig(trading_mode="PAPER", instrument_allowlist=["other"]),
    ).run(
        candles=make_candles_with_prices([
            ("100", "101", "99"),
            ("101", "102", "100"),
            ("102", "103", "101"),
        ]),
        instrument=make_instrument(),
    )

    assert result.rejected_signals_count == 1
    assert result.closed_trades_count == 0
