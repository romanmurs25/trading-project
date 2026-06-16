from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "20260617_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DECIMAL = sa.Numeric(38, 18)


def upgrade() -> None:
    op.create_table(
        "instruments",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("venue", sa.String(32), nullable=False),
        sa.Column("asset_class", sa.String(32), nullable=False),
        sa.Column("native_symbol", sa.String(128), nullable=False),
        sa.Column("canonical_symbol", sa.String(128), nullable=False, unique=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("lot_size", DECIMAL, nullable=False),
        sa.Column("tick_size", DECIMAL, nullable=False),
        sa.Column("tick_value", DECIMAL, nullable=False),
        sa.Column("currency", sa.String(16), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
    )
    op.create_index("ix_instruments_venue", "instruments", ["venue"])

    op.create_table(
        "candles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("venue", sa.String(32), nullable=False),
        sa.Column("instrument_id", sa.String(128), nullable=False),
        sa.Column("interval", sa.String(16), nullable=False),
        sa.Column("ts_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ts_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", DECIMAL, nullable=False),
        sa.Column("high", DECIMAL, nullable=False),
        sa.Column("low", DECIMAL, nullable=False),
        sa.Column("close", DECIMAL, nullable=False),
        sa.Column("volume", DECIMAL, nullable=False),
        sa.Column("value", DECIMAL, nullable=True),
        sa.Column("trades_count", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(64), nullable=False),
        sa.UniqueConstraint("venue", "instrument_id", "interval", "ts_start", name="uq_candles_key"),
    )

    op.create_table(
        "signals",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("strategy_id", sa.String(128), nullable=False),
        sa.Column("instrument_id", sa.String(128), nullable=False),
        sa.Column("venue", sa.String(32), nullable=False),
        sa.Column("direction", sa.String(32), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("price", DECIMAL, nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
    )
    op.create_index("ix_signals_strategy_instrument_ts", "signals", ["strategy_id", "instrument_id", "ts"])

    op.create_table(
        "order_intents",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("strategy_id", sa.String(128), nullable=False),
        sa.Column("signal_id", sa.String(128), nullable=True),
        sa.Column("venue", sa.String(32), nullable=False),
        sa.Column("instrument_id", sa.String(128), nullable=False),
        sa.Column("side", sa.String(16), nullable=False),
        sa.Column("order_type", sa.String(32), nullable=False),
        sa.Column("qty", DECIMAL, nullable=False),
        sa.Column("limit_price", DECIMAL, nullable=True),
        sa.Column("stop_price", DECIMAL, nullable=True),
        sa.Column("take_profit", DECIMAL, nullable=True),
        sa.Column("stop_loss", DECIMAL, nullable=True),
        sa.Column("time_in_force", sa.String(32), nullable=False),
        sa.Column("reason", sa.String(512), nullable=False),
        sa.Column("risk_amount", DECIMAL, nullable=True),
        sa.Column("idempotency_key", sa.String(256), nullable=True, unique=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "risk_decisions",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("order_intent_id", sa.String(128), nullable=False),
        sa.Column("approved", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.String(512), nullable=False),
        sa.Column("checks", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_risk_decisions_order_intent_id", "risk_decisions", ["order_intent_id"])

    op.create_table(
        "orders",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("order_intent_id", sa.String(128), nullable=False),
        sa.Column("venue", sa.String(32), nullable=False),
        sa.Column("broker_order_id", sa.String(256), nullable=True),
        sa.Column("idempotency_key", sa.String(256), nullable=False, unique=True),
        sa.Column("state", sa.String(64), nullable=False),
        sa.Column("side", sa.String(16), nullable=False),
        sa.Column("order_type", sa.String(32), nullable=False),
        sa.Column("qty", DECIMAL, nullable=False),
        sa.Column("filled_qty", DECIMAL, nullable=False),
        sa.Column("avg_fill_price", DECIMAL, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_orders_order_intent_id", "orders", ["order_intent_id"])

    op.create_table(
        "executions",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("order_id", sa.String(128), nullable=False),
        sa.Column("venue", sa.String(32), nullable=False),
        sa.Column("broker_execution_id", sa.String(256), nullable=True),
        sa.Column("instrument_id", sa.String(128), nullable=False),
        sa.Column("side", sa.String(16), nullable=False),
        sa.Column("qty", DECIMAL, nullable=False),
        sa.Column("price", DECIMAL, nullable=False),
        sa.Column("commission", DECIMAL, nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("venue", "broker_execution_id", name="uq_executions_broker_exec"),
    )
    op.create_index("ix_executions_order_id", "executions", ["order_id"])

    op.create_table(
        "positions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("instrument_id", sa.String(128), nullable=False),
        sa.Column("venue", sa.String(32), nullable=False),
        sa.Column("qty", DECIMAL, nullable=False),
        sa.Column("avg_price", DECIMAL, nullable=False),
        sa.Column("unrealized_pnl", DECIMAL, nullable=False),
        sa.Column("realized_pnl", DECIMAL, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "backtest_runs",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("strategy_id", sa.String(128), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_backtest_runs_strategy_id", "backtest_runs", ["strategy_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(128), nullable=False),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_logs_entity_ts", "audit_logs", ["entity_type", "entity_id", "ts"])

    op.create_table(
        "system_events",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_system_events_type_ts", "system_events", ["event_type", "ts"])


def downgrade() -> None:
    op.drop_index("ix_system_events_type_ts", table_name="system_events")
    op.drop_table("system_events")
    op.drop_index("ix_audit_logs_entity_ts", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index("ix_backtest_runs_strategy_id", table_name="backtest_runs")
    op.drop_table("backtest_runs")
    op.drop_table("positions")
    op.drop_index("ix_executions_order_id", table_name="executions")
    op.drop_table("executions")
    op.drop_index("ix_orders_order_intent_id", table_name="orders")
    op.drop_table("orders")
    op.drop_index("ix_risk_decisions_order_intent_id", table_name="risk_decisions")
    op.drop_table("risk_decisions")
    op.drop_table("order_intents")
    op.drop_index("ix_signals_strategy_instrument_ts", table_name="signals")
    op.drop_table("signals")
    op.drop_table("candles")
    op.drop_index("ix_instruments_venue", table_name="instruments")
    op.drop_table("instruments")
