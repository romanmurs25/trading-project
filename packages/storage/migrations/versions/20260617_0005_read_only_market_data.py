"""read-only market data ingestion metadata

Revision ID: 20260617_0005
Revises: 20260617_0004
Create Date: 2026-06-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260617_0005"
down_revision: str | None = "20260617_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "market_data_ingestion_runs",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("venue", sa.String(length=32), nullable=False),
        sa.Column("instruments", sa.JSON(), nullable=False),
        sa.Column("interval", sa.String(length=16), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stopped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_event_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("events_count", sa.Integer(), nullable=False),
        sa.Column("candles_count", sa.Integer(), nullable=False),
        sa.Column("errors_count", sa.Integer(), nullable=False),
        sa.Column("read_only", sa.Boolean(), nullable=False),
        sa.Column("allow_network", sa.Boolean(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
    )
    op.create_index(
        "ix_market_data_ingestion_runs_source_status_started",
        "market_data_ingestion_runs",
        ["source", "status", "started_at"],
    )

    op.create_table(
        "market_data_events",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("venue", sa.String(length=32), nullable=False),
        sa.Column("instrument_id", sa.String(length=128), nullable=False),
        sa.Column("canonical_symbol", sa.String(length=128), nullable=False),
        sa.Column("interval", sa.String(length=16), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
    )
    op.create_index(
        "ix_market_data_events_source_instrument_interval_received",
        "market_data_events",
        ["source", "instrument_id", "interval", "received_at"],
    )

    op.create_table(
        "live_candle_snapshots",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("venue", sa.String(length=32), nullable=False),
        sa.Column("instrument_id", sa.String(length=128), nullable=False),
        sa.Column("canonical_symbol", sa.String(length=128), nullable=False),
        sa.Column("interval", sa.String(length=16), nullable=False),
        sa.Column("ts_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ts_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(38, 18), nullable=False),
        sa.Column("high", sa.Numeric(38, 18), nullable=False),
        sa.Column("low", sa.Numeric(38, 18), nullable=False),
        sa.Column("close", sa.Numeric(38, 18), nullable=False),
        sa.Column("volume", sa.Numeric(38, 18), nullable=False),
        sa.Column("value", sa.Numeric(38, 18), nullable=True),
        sa.Column("trades_count", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_closed", sa.Boolean(), nullable=False),
        sa.Column("freshness", sa.String(length=32), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint(
            "source",
            "venue",
            "instrument_id",
            "interval",
            "ts_start",
            name="uq_live_candle_snapshots_market_key",
        ),
    )
    op.create_index(
        "ix_live_candle_snapshots_source_canonical_interval_ts",
        "live_candle_snapshots",
        ["source", "canonical_symbol", "interval", "ts_start"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_live_candle_snapshots_source_canonical_interval_ts",
        table_name="live_candle_snapshots",
    )
    op.drop_table("live_candle_snapshots")
    op.drop_index(
        "ix_market_data_events_source_instrument_interval_received",
        table_name="market_data_events",
    )
    op.drop_table("market_data_events")
    op.drop_index(
        "ix_market_data_ingestion_runs_source_status_started",
        table_name="market_data_ingestion_runs",
    )
    op.drop_table("market_data_ingestion_runs")
