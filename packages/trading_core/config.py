import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from urllib.parse import SplitResult, urlsplit, urlunsplit

from trading_core.domain.enums import TradingMode
from trading_core.domain.models import RiskConfig

SECRET_MARKERS = ("token", "secret", "api_key", "authorization", "password")
REDACTED = "***REDACTED***"


def _bool_from_env(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _decimal_from_env(name: str, default: str) -> Decimal:
    return Decimal(os.getenv(name, default))


def _int_from_env(name: str, default: str) -> int:
    return int(os.getenv(name, default))


def redact_secret(value: str | None) -> str:
    if value in (None, ""):
        return ""
    return REDACTED


def _is_secret_key(key: str) -> bool:
    lowered = key.lower().replace("-", "_")
    return any(marker in lowered for marker in SECRET_MARKERS)


def redact_mapping(values: Mapping[str, Any]) -> dict[str, Any]:
    return {key: redact_secret(str(value)) if _is_secret_key(key) else value for key, value in values.items()}


def redact_dsn_password(dsn: str) -> str:
    if not dsn:
        return ""
    parts = urlsplit(dsn)
    if parts.password is None or parts.hostname is None:
        return dsn
    username = parts.username or ""
    host = parts.hostname
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    port = f":{parts.port}" if parts.port is not None else ""
    netloc = f"{username}:{REDACTED}@{host}{port}"
    return urlunsplit(SplitResult(parts.scheme, netloc, parts.path, parts.query, parts.fragment))


@dataclass(frozen=True)
class AppConfig:
    app_env: str = field(default_factory=lambda: os.getenv("APP_ENV", "local"))
    trading_mode: TradingMode = field(
        default_factory=lambda: TradingMode(os.getenv("TRADING_MODE", TradingMode.RESEARCH.value))
    )
    allow_live_trading: bool = field(
        default_factory=lambda: _bool_from_env(os.getenv("ALLOW_LIVE_TRADING"), False)
    )
    database_url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/trading"
        )
    )
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    default_timezone: str = field(default_factory=lambda: os.getenv("DEFAULT_TIMEZONE", "UTC"))
    exchange_timezone: str = field(default_factory=lambda: os.getenv("EXCHANGE_TIMEZONE", "Europe/Moscow"))
    moex_iss_base_url: str = field(default_factory=lambda: os.getenv("MOEX_ISS_BASE_URL", "https://iss.moex.com/iss"))
    tinvest_token: str = field(default_factory=lambda: os.getenv("TINVEST_TOKEN", ""))
    tinvest_account_id: str = field(default_factory=lambda: os.getenv("TINVEST_ACCOUNT_ID", ""))
    tinvest_sandbox: bool = field(default_factory=lambda: _bool_from_env(os.getenv("TINVEST_SANDBOX"), True))
    bybit_api_key: str = field(default_factory=lambda: os.getenv("BYBIT_API_KEY", ""))
    bybit_api_secret: str = field(default_factory=lambda: os.getenv("BYBIT_API_SECRET", ""))
    bybit_testnet: bool = field(default_factory=lambda: _bool_from_env(os.getenv("BYBIT_TESTNET"), True))
    bybit_recv_window: int = field(default_factory=lambda: _int_from_env("BYBIT_RECV_WINDOW", "5000"))
    risk: RiskConfig = field(default_factory=lambda: RiskConfig(
        trading_mode=TradingMode(os.getenv("TRADING_MODE", TradingMode.RESEARCH.value)),
        allow_live_trading=_bool_from_env(os.getenv("ALLOW_LIVE_TRADING"), False),
        max_risk_per_trade_pct=_decimal_from_env("RISK_MAX_RISK_PER_TRADE_PCT", "0.25"),
        max_daily_loss_pct=_decimal_from_env("RISK_MAX_DAILY_LOSS_PCT", "1.0"),
        max_weekly_loss_pct=_decimal_from_env("RISK_MAX_WEEKLY_LOSS_PCT", "3.0"),
        max_open_positions=_int_from_env("RISK_MAX_OPEN_POSITIONS", "3"),
        max_position_size=_decimal_from_env("RISK_MAX_POSITION_SIZE", "10"),
        max_notional_exposure=_decimal_from_env("RISK_MAX_NOTIONAL_EXPOSURE", "100000"),
        max_order_qty=_decimal_from_env("RISK_MAX_ORDER_QTY", "10"),
        max_spread_bps=_decimal_from_env("RISK_MAX_SPREAD_BPS", "10"),
        stale_data_seconds=_int_from_env("RISK_STALE_DATA_SECONDS", "10"),
        allow_market_orders_live=_bool_from_env(os.getenv("RISK_ALLOW_MARKET_ORDERS_LIVE"), False),
        allow_averaging_down=_bool_from_env(os.getenv("RISK_ALLOW_AVERAGING_DOWN"), False),
        allow_reduce_only_when_killed=_bool_from_env(os.getenv("RISK_ALLOW_REDUCE_ONLY_WHEN_KILLED"), True),
    ))

    def safe_dict(self) -> dict[str, Any]:
        raw: dict[str, Any] = {
            "app_env": self.app_env,
            "trading_mode": self.trading_mode.value,
            "allow_live_trading": self.allow_live_trading,
            "database_url": self.database_url,
            "redis_url": self.redis_url,
            "default_timezone": self.default_timezone,
            "exchange_timezone": self.exchange_timezone,
            "moex_iss_base_url": self.moex_iss_base_url,
            "tinvest_token": self.tinvest_token,
            "tinvest_account_id": self.tinvest_account_id,
            "tinvest_sandbox": self.tinvest_sandbox,
            "bybit_api_key": self.bybit_api_key,
            "bybit_api_secret": self.bybit_api_secret,
            "bybit_testnet": self.bybit_testnet,
            "bybit_recv_window": self.bybit_recv_window,
            "risk": self.risk.model_dump(mode="json"),
        }
        safe = redact_mapping(raw)
        safe["database_url"] = redact_dsn_password(self.database_url)
        safe["redis_url"] = redact_dsn_password(self.redis_url)
        return safe
