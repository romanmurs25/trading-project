from collections.abc import Sequence
from decimal import Decimal

from trading_core.domain.enums import SignalDirection
from trading_core.domain.models import Candle, Signal
from trading_core.strategy.base import Strategy


class VWAPReclaimStrategy(Strategy):
    strategy_id = "vwap_reclaim"

    def __init__(
        self,
        vwap_mode: str = "session",
        vwap_window: int = 20,
        min_volume_multiplier: Decimal = Decimal("1"),
        reclaim_confirmation_bars: int = 1,
        stop_ticks: Decimal = Decimal("2"),
        take_profit_r_multiple: Decimal = Decimal("2"),
    ) -> None:
        self.vwap_mode = vwap_mode
        self.vwap_window = vwap_window
        self.min_volume_multiplier = min_volume_multiplier
        self.reclaim_confirmation_bars = reclaim_confirmation_bars
        self.stop_ticks = stop_ticks
        self.take_profit_r_multiple = take_profit_r_multiple

    def on_candle(self, candle: Candle, history: Sequence[Candle]) -> Signal | None:
        if len(history) < max(2, self.reclaim_confirmation_bars + 1):
            return None
        previous = history[-2]
        previous_vwap = self._vwap(history[:-1])
        current_vwap = self._vwap(history)
        if previous.close < previous_vwap and candle.close > current_vwap:
            risk = self.stop_ticks
            return Signal(
                strategy_id=self.strategy_id,
                instrument_id=candle.instrument_id,
                venue=candle.venue,
                direction=SignalDirection.LONG,
                ts=candle.ts_end,
                price=candle.close,
                stop_loss=candle.close - risk,
                take_profit=candle.close + (risk * self.take_profit_r_multiple),
                confidence=Decimal("0.5"),
                reason="price reclaimed VWAP",
                debug={"vwap": str(current_vwap), "mode": self.vwap_mode},
            )
        if previous.close > previous_vwap and candle.close < current_vwap:
            risk = self.stop_ticks
            return Signal(
                strategy_id=self.strategy_id,
                instrument_id=candle.instrument_id,
                venue=candle.venue,
                direction=SignalDirection.SHORT,
                ts=candle.ts_end,
                price=candle.close,
                stop_loss=candle.close + risk,
                take_profit=candle.close - (risk * self.take_profit_r_multiple),
                confidence=Decimal("0.5"),
                reason="price rejected VWAP",
                debug={"vwap": str(current_vwap), "mode": self.vwap_mode},
            )
        return None

    def _vwap(self, history: Sequence[Candle]) -> Decimal:
        data = list(history[-self.vwap_window :]) if self.vwap_mode == "rolling" else list(history)
        total_volume = sum((item.volume for item in data), Decimal("0"))
        if total_volume == 0:
            return data[-1].close
        return sum((item.close * item.volume for item in data), Decimal("0")) / total_volume
