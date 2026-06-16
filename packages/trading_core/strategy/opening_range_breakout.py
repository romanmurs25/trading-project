from collections.abc import Sequence
from decimal import Decimal

from trading_core.domain.enums import SignalDirection
from trading_core.domain.models import Candle, Signal
from trading_core.strategy.base import Strategy


class OpeningRangeBreakoutStrategy(Strategy):
    strategy_id = "opening_range_breakout"

    def __init__(
        self,
        opening_range_minutes: int = 5,
        min_volume_multiplier: Decimal = Decimal("1"),
        direction: str = "both",
        stop_mode: str = "opposite_range",
        take_profit_r_multiple: Decimal = Decimal("2"),
        max_trades_per_session: int = 1,
    ) -> None:
        self.opening_range_minutes = opening_range_minutes
        self.min_volume_multiplier = min_volume_multiplier
        self.direction = direction
        self.stop_mode = stop_mode
        self.take_profit_r_multiple = take_profit_r_multiple
        self.max_trades_per_session = max_trades_per_session
        self._signals_emitted = 0

    def on_candle(self, candle: Candle, history: Sequence[Candle]) -> Signal | None:
        if len(history) <= self.opening_range_minutes:
            return None
        if self._signals_emitted >= self.max_trades_per_session:
            return None

        opening_range = list(history[: self.opening_range_minutes])
        range_high = max(item.high for item in opening_range)
        range_low = min(item.low for item in opening_range)

        if candle.close > range_high and self.direction in {"both", "long_only"}:
            self._signals_emitted += 1
            risk = candle.close - range_low
            return Signal(
                strategy_id=self.strategy_id,
                instrument_id=candle.instrument_id,
                venue=candle.venue,
                direction=SignalDirection.LONG,
                ts=candle.ts_end,
                price=candle.close,
                stop_loss=range_low,
                take_profit=candle.close + (risk * self.take_profit_r_multiple),
                confidence=Decimal("1"),
                reason="opening range breakout above high",
                debug={"range_high": str(range_high), "range_low": str(range_low)},
            )

        if candle.close < range_low and self.direction in {"both", "short_only"}:
            self._signals_emitted += 1
            risk = range_high - candle.close
            return Signal(
                strategy_id=self.strategy_id,
                instrument_id=candle.instrument_id,
                venue=candle.venue,
                direction=SignalDirection.SHORT,
                ts=candle.ts_end,
                price=candle.close,
                stop_loss=range_high,
                take_profit=candle.close - (risk * self.take_profit_r_multiple),
                confidence=Decimal("1"),
                reason="opening range breakout below low",
                debug={"range_high": str(range_high), "range_low": str(range_low)},
            )
        return None
