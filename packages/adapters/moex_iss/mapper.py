from trading_core.domain.models import Candle


def map_candle(_: dict[str, object]) -> Candle:
    raise NotImplementedError("TODO: map MOEX ISS candle payload to Candle")
