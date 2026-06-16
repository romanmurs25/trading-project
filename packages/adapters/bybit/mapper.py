from trading_core.domain.models import Candle


def map_kline(_: dict[str, object]) -> Candle:
    raise NotImplementedError("TODO: map Bybit kline payload to Candle")
