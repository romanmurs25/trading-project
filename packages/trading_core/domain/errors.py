class TradingError(Exception):
    """Базовая ошибка торгового домена."""


class LiveTradingDisabledError(TradingError):
    """Live-исполнение запрещено текущей конфигурацией."""


class RiskRejectedError(TradingError):
    """RiskEngine отклонил заявку."""


class StaleMarketDataError(TradingError):
    """Рыночные данные устарели."""


class BrokerUnavailableError(TradingError):
    """Брокер или адаптер недоступен."""


class ReconciliationRequiredError(TradingError):
    """Требуется сверка состояния ордера."""


class DataValidationError(TradingError):
    """Данные нарушают доменные инварианты."""


class AdapterError(TradingError):
    """Ошибка внешнего адаптера."""
