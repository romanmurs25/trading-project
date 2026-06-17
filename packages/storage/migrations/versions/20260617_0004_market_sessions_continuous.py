"""market sessions and continuous futures metadata

Revision ID: 20260617_0004
Revises: 20260617_0003
Create Date: 2026-06-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260617_0004"
down_revision: str | None = "20260617_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "market_sessions",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("venue", sa.String(length=32), nullable=False),
        sa.Column("market", sa.String(length=64), nullable=False),
        sa.Column("session_type", sa.String(length=32), nullable=False),
        sa.Column("session_date", sa.Date(), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_trading", sa.Boolean(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
    )
    op.create_index("ix_market_sessions_venue", "market_sessions", ["venue"])
    op.create_index("ix_market_sessions_market", "market_sessions", ["market"])
    op.create_index("ix_market_sessions_session_type", "market_sessions", ["session_type"])
    op.create_index("ix_market_sessions_session_date", "market_sessions", ["session_date"])
    op.create_index("ix_market_sessions_start", "market_sessions", ["start"])
    op.create_index("ix_market_sessions_end", "market_sessions", ["end"])

    op.create_table(
        "continuous_series",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("venue", sa.String(length=32), nullable=False),
        sa.Column("underlying_symbol", sa.String(length=128), nullable=False),
        sa.Column("canonical_symbol", sa.String(length=128), nullable=False),
        sa.Column("interval", sa.String(length=16), nullable=False),
        sa.Column("roll_rule", sa.JSON(), nullable=False),
        sa.Column("adjustment_method", sa.String(length=32), nullable=False),
        sa.Column("start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("canonical_symbol", name="uq_continuous_series_canonical_symbol"),
    )
    op.create_index("ix_continuous_series_venue", "continuous_series", ["venue"])
    op.create_index("ix_continuous_series_underlying_symbol", "continuous_series", ["underlying_symbol"])
    op.create_index("ix_continuous_series_canonical_symbol", "continuous_series", ["canonical_symbol"])

    op.create_table(
        "continuous_series_components",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("continuous_series_id", sa.String(length=128), nullable=False),
        sa.Column("instrument_id", sa.String(length=128), nullable=False),
        sa.Column("canonical_symbol", sa.String(length=128), nullable=False),
        sa.Column("start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("roll_date", sa.Date(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
    )
    op.create_index(
        "ix_continuous_series_components_continuous_series_id",
        "continuous_series_components",
        ["continuous_series_id"],
    )
    op.create_index(
        "ix_continuous_series_components_instrument_id",
        "continuous_series_components",
        ["instrument_id"],
    )
    op.create_index(
        "ix_continuous_series_components_canonical_symbol",
        "continuous_series_components",
        ["canonical_symbol"],
    )

    op.create_table(
        "roll_events",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("venue", sa.String(length=32), nullable=False),
        sa.Column("underlying_symbol", sa.String(length=128), nullable=False),
        sa.Column("from_instrument_id", sa.String(length=128), nullable=False),
        sa.Column("to_instrument_id", sa.String(length=128), nullable=False),
        sa.Column("roll_date", sa.Date(), nullable=False),
        sa.Column("reason", sa.String(length=512), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
    )
    op.create_index("ix_roll_events_venue", "roll_events", ["venue"])
    op.create_index("ix_roll_events_underlying_symbol", "roll_events", ["underlying_symbol"])
    op.create_index("ix_roll_events_roll_date", "roll_events", ["roll_date"])


def downgrade() -> None:
    op.drop_index("ix_roll_events_roll_date", table_name="roll_events")
    op.drop_index("ix_roll_events_underlying_symbol", table_name="roll_events")
    op.drop_index("ix_roll_events_venue", table_name="roll_events")
    op.drop_table("roll_events")
    op.drop_index(
        "ix_continuous_series_components_canonical_symbol",
        table_name="continuous_series_components",
    )
    op.drop_index("ix_continuous_series_components_instrument_id", table_name="continuous_series_components")
    op.drop_index(
        "ix_continuous_series_components_continuous_series_id",
        table_name="continuous_series_components",
    )
    op.drop_table("continuous_series_components")
    op.drop_index("ix_continuous_series_canonical_symbol", table_name="continuous_series")
    op.drop_index("ix_continuous_series_underlying_symbol", table_name="continuous_series")
    op.drop_index("ix_continuous_series_venue", table_name="continuous_series")
    op.drop_table("continuous_series")
    op.drop_index("ix_market_sessions_end", table_name="market_sessions")
    op.drop_index("ix_market_sessions_start", table_name="market_sessions")
    op.drop_index("ix_market_sessions_session_date", table_name="market_sessions")
    op.drop_index("ix_market_sessions_session_type", table_name="market_sessions")
    op.drop_index("ix_market_sessions_market", table_name="market_sessions")
    op.drop_index("ix_market_sessions_venue", table_name="market_sessions")
    op.drop_table("market_sessions")
