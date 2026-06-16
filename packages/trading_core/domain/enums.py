from enum import StrEnum


class Venue(StrEnum):
    MOEX = "MOEX"
    BYBIT = "BYBIT"
    PAPER = "PAPER"


class AssetClass(StrEnum):
    FUTURES = "FUTURES"
    STOCK = "STOCK"
    CRYPTO = "CRYPTO"
    FX = "FX"
    INDEX = "INDEX"
    COMMODITY = "COMMODITY"


class Side(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(StrEnum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class TimeInForce(StrEnum):
    DAY = "DAY"
    IOC = "IOC"
    FOK = "FOK"
    GTC = "GTC"


class TradingMode(StrEnum):
    RESEARCH = "RESEARCH"
    PAPER = "PAPER"
    SANDBOX = "SANDBOX"
    LIVE_READONLY = "LIVE_READONLY"
    LIVE_GUARDED = "LIVE_GUARDED"


class OrderState(StrEnum):
    NEW = "NEW"
    RISK_REJECTED = "RISK_REJECTED"
    APPROVED = "APPROVED"
    SUBMITTED = "SUBMITTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    UNKNOWN_RECONCILIATION_REQUIRED = "UNKNOWN_RECONCILIATION_REQUIRED"


class SignalDirection(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"
