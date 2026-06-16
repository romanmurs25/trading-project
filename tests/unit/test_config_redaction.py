from trading_core.config import AppConfig, redact_mapping, redact_secret


def test_redact_secret_masks_sensitive_value() -> None:
    assert redact_secret("secret-token") == "***REDACTED***"
    assert redact_secret("") == ""


def test_safe_config_redacts_credentials() -> None:
    config = AppConfig(bybit_api_key="key", bybit_api_secret="secret", tinvest_token="token")

    safe = config.safe_dict()

    assert safe["bybit_api_key"] == "***REDACTED***"
    assert safe["bybit_api_secret"] == "***REDACTED***"
    assert safe["tinvest_token"] == "***REDACTED***"
    assert safe["allow_live_trading"] is False


def test_redact_mapping_masks_authorization_headers() -> None:
    redacted = redact_mapping({"Authorization": "Bearer abc", "normal": "value"})

    assert redacted["Authorization"] == "***REDACTED***"
    assert redacted["normal"] == "value"


def test_safe_config_redacts_database_password_only() -> None:
    config = AppConfig(database_url="postgresql+asyncpg://user:pass@localhost:5432/trading")

    assert config.safe_dict()["database_url"] == (
        "postgresql+asyncpg://user:***REDACTED***@localhost:5432/trading"
    )


def test_safe_config_redacts_redis_password_only() -> None:
    config = AppConfig(redis_url="redis://:redis-pass@localhost:6379/0")

    assert config.safe_dict()["redis_url"] == "redis://:***REDACTED***@localhost:6379/0"
