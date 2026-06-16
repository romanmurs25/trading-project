from abc import ABC, abstractmethod
from collections.abc import Sequence

from trading_core.domain.models import Candle, Signal


class Strategy(ABC):
    strategy_id: str

    @abstractmethod
    def on_candle(self, candle: Candle, history: Sequence[Candle]) -> Signal | None:
        """Вернуть Signal или None. Стратегии не создают ордера и не вызывают внешние сервисы."""
