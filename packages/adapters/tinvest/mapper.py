from trading_core.domain.models import Order


def map_order(_: dict[str, object]) -> Order:
    raise NotImplementedError("TODO: map T-Invest order payload")
