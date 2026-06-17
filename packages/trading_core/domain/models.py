from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, ClassVar
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from trading_core.domain.enums import (
    AssetClass,
    OrderState,
    OrderType,
    Side,
    SignalDirection,
    TimeInForce,
    TradingMode,
    Venue,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


def new_id() -> str:
    return str(uuid4())


class DomainModel(BaseModel):
    model_config = ConfigDict(use_enum_values=False, arbitrary_types_allowed=True)
    decimal_field_names: ClassVar[set[str]] = {
        "price",
        "qty",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "value",
        "lot_size",
        "tick_size",
        "tick_value",
        "risk_amount",
        "stop_loss",
        "take_profit",
        "limit_price",
        "stop_price",
        "commission",
        "cash",
        "equity",
        "initial_cash",
        "final_equity",
        "total_pnl",
        "max_drawdown",
        "win_rate",
        "avg_win",
        "avg_loss",
        "profit_factor",
        "expectancy",
        "avg_r",
        "entry_price",
        "exit_price",
        "gross_pnl",
        "net_pnl",
        "r_multiple",
        "pnl",
        "drawdown",
        "confidence",
        "avg_price",
        "unrealized_pnl",
        "realized_pnl",
        "filled_qty",
        "avg_fill_price",
        "adjusted_qty",
        "max_loss_after_trade",
        "portfolio_value",
        "daily_pnl",
        "weekly_pnl",
        "bid",
        "ask",
        "current_position_qty",
        "max_risk_per_trade_pct",
        "max_daily_loss_pct",
        "max_weekly_loss_pct",
        "max_position_size",
        "max_notional_exposure",
        "max_order_qty",
        "max_spread_bps",
    }

    @field_validator("*", mode="before")
    @classmethod
    def validate_common_domain_values(cls, value: Any, info: ValidationInfo) -> Any:
        if isinstance(value, datetime) and value.tzinfo is None:
            raise ValueError("datetime must be timezone-aware")
        if isinstance(value, float) and info.field_name in cls.decimal_field_names:
            raise ValueError(f"float is forbidden for Decimal field '{info.field_name}'")
        return value


class Instrument(DomainModel):
    id: str
    venue: Venue
    asset_class: AssetClass
    native_symbol: str
    canonical_symbol: str
    name: str
    lot_size: Decimal
    tick_size: Decimal
    tick_value: Decimal
    currency: str
    expiry_date: date | None = None
    is_active: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class ContractSpec(DomainModel):
    instrument_id: str
    lot_size: Decimal
    tick_size: Decimal
    tick_value: Decimal
    currency: str
    expiry_date: date | None = None
    first_trade_date: date | None = None
    last_trade_date: date | None = None
    underlying_symbol: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TradingSession(DomainModel):
    instrument_id: str
    timezone: str
    opens_at: datetime
    closes_at: datetime
    allows_trading: bool = True


class Candle(DomainModel):
    instrument_id: str
    venue: Venue
    interval: str
    ts_start: datetime
    ts_end: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    value: Decimal | None = None
    trades_count: int | None = None
    source: str


class TickTrade(DomainModel):
    instrument_id: str
    venue: Venue
    price: Decimal
    qty: Decimal
    ts: datetime


class OrderBookLevel(DomainModel):
    price: Decimal
    qty: Decimal


class OrderBookSnapshot(DomainModel):
    instrument_id: str
    venue: Venue
    bids: list[OrderBookLevel]
    asks: list[OrderBookLevel]
    ts: datetime


class Signal(DomainModel):
    id: str = Field(default_factory=new_id)
    strategy_id: str
    instrument_id: str
    venue: Venue
    direction: SignalDirection
    ts: datetime
    price: Decimal
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    confidence: Decimal | None = None
    reason: str
    debug: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class OrderIntent(DomainModel):
    id: str = Field(default_factory=new_id)
    strategy_id: str
    signal_id: str | None = None
    venue: Venue
    instrument_id: str
    side: Side
    order_type: OrderType
    qty: Decimal
    limit_price: Decimal | None = None
    stop_price: Decimal | None = None
    take_profit: Decimal | None = None
    stop_loss: Decimal | None = None
    time_in_force: TimeInForce = TimeInForce.DAY
    reason: str
    risk_amount: Decimal | None = None
    idempotency_key: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class RiskDecision(DomainModel):
    id: str = Field(default_factory=new_id)
    order_intent_id: str
    approved: bool
    reason: str
    checks: dict[str, bool]
    adjusted_qty: Decimal | None = None
    max_loss_after_trade: Decimal | None = None
    created_at: datetime = Field(default_factory=utc_now)


class Order(DomainModel):
    id: str = Field(default_factory=new_id)
    order_intent_id: str
    venue: Venue
    broker_order_id: str | None = None
    idempotency_key: str
    state: OrderState = OrderState.NEW
    side: Side
    order_type: OrderType
    qty: Decimal
    filled_qty: Decimal = Decimal("0")
    avg_fill_price: Decimal | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class Execution(DomainModel):
    id: str = Field(default_factory=new_id)
    order_id: str
    venue: Venue
    broker_execution_id: str | None = None
    instrument_id: str
    side: Side
    qty: Decimal
    price: Decimal
    commission: Decimal = Decimal("0")
    ts: datetime = Field(default_factory=utc_now)


class BrokerOrderResult(DomainModel):
    order: Order
    executions: list[Execution] = Field(default_factory=list)


class Position(DomainModel):
    instrument_id: str
    venue: Venue
    qty: Decimal
    avg_price: Decimal
    unrealized_pnl: Decimal = Decimal("0")
    realized_pnl: Decimal = Decimal("0")
    updated_at: datetime = Field(default_factory=utc_now)


class PortfolioSnapshot(DomainModel):
    cash: Decimal
    equity: Decimal
    positions: list[Position]
    ts: datetime = Field(default_factory=utc_now)


class TradeJournalEntry(DomainModel):
    id: str = Field(default_factory=new_id)
    trade_id: str | None = None
    strategy_id: str | None = None
    session_date: date | None = None
    notes: str = ""
    created_at: datetime = Field(default_factory=utc_now)


class BacktestRun(DomainModel):
    id: str = Field(default_factory=new_id)
    strategy_id: str
    strategy_config: dict[str, Any]
    risk_config: dict[str, Any]
    instruments: list[str]
    start: datetime
    end: datetime
    initial_cash: Decimal
    final_equity: Decimal
    total_pnl: Decimal
    max_drawdown: Decimal
    win_rate: Decimal
    profit_factor: Decimal
    expectancy: Decimal
    avg_r: Decimal = Decimal("0")
    trades_count: int
    created_at: datetime = Field(default_factory=utc_now)


class BacktestTrade(DomainModel):
    id: str = Field(default_factory=new_id)
    run_id: str
    instrument_id: str
    side: Side
    qty: Decimal
    entry_price: Decimal
    exit_price: Decimal | None = None
    pnl: Decimal = Decimal("0")


class StrategyConfig(DomainModel):
    strategy_id: str
    enabled: bool = True
    params: dict[str, Any] = Field(default_factory=dict)


class RiskConfig(DomainModel):
    trading_mode: TradingMode = TradingMode.RESEARCH
    allow_live_trading: bool = False
    instrument_allowlist: list[str] = Field(default_factory=list)
    max_risk_per_trade_pct: Decimal = Decimal("0.25")
    max_daily_loss_pct: Decimal = Decimal("1.0")
    max_weekly_loss_pct: Decimal = Decimal("3.0")
    max_open_positions: int = 3
    max_position_size: Decimal = Decimal("10")
    max_notional_exposure: Decimal = Decimal("100000")
    max_order_qty: Decimal = Decimal("10")
    max_spread_bps: Decimal = Decimal("10")
    stale_data_seconds: int = 10
    allow_market_orders_live: bool = False
    allow_averaging_down: bool = False
    allow_reduce_only_when_killed: bool = True


class SystemEvent(DomainModel):
    id: str = Field(default_factory=new_id)
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    ts: datetime = Field(default_factory=utc_now)


class AuditLog(DomainModel):
    id: str = Field(default_factory=new_id)
    entity_type: str
    entity_id: str
    action: str
    payload: dict[str, Any] = Field(default_factory=dict)
    ts: datetime = Field(default_factory=utc_now)


class RiskContext(DomainModel):
    instrument: Instrument
    now: datetime = Field(default_factory=utc_now)
    market_data_ts: datetime
    bid: Decimal
    ask: Decimal
    portfolio_value: Decimal
    daily_pnl: Decimal = Decimal("0")
    weekly_pnl: Decimal = Decimal("0")
    open_positions_count: int = 0
    current_position_qty: Decimal = Decimal("0")
    session_allows_trading: bool = True
    account_available: bool = True
    broker_supports_live: bool = False
    adapter_read_only: bool = False
    is_position_reducing: bool = False
