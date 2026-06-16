def get_database_url() -> str:
    from trading_core.config import AppConfig

    return AppConfig().database_url
