from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "20260617_0003"
down_revision: str | None = "20260617_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DECIMAL = sa.Numeric(38, 18)


def upgrade() -> None:
    op.create_table(
        "research_runs",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("strategy_id", sa.String(128), nullable=False),
        sa.Column("canonical_symbol", sa.String(128), nullable=False),
        sa.Column("instrument_id", sa.String(128), nullable=False),
        sa.Column("interval", sa.String(16), nullable=False),
        sa.Column("start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("parameter_grid", sa.JSON(), nullable=False),
        sa.Column("data_quality_gate", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.String(2048), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
    )
    op.create_index("ix_research_runs_strategy_id", "research_runs", ["strategy_id"])
    op.create_index("ix_research_runs_canonical_symbol", "research_runs", ["canonical_symbol"])
    op.create_index("ix_research_runs_instrument_id", "research_runs", ["instrument_id"])
    op.create_index("ix_research_runs_status", "research_runs", ["status"])

    op.create_table(
        "research_backtest_results",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("research_run_id", sa.String(128), nullable=False),
        sa.Column("backtest_run_id", sa.String(128), nullable=True),
        sa.Column("strategy_id", sa.String(128), nullable=False),
        sa.Column("canonical_symbol", sa.String(128), nullable=False),
        sa.Column("instrument_id", sa.String(128), nullable=False),
        sa.Column("interval", sa.String(16), nullable=False),
        sa.Column("start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("quality_report", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("error_message", sa.String(2048), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_research_backtest_results_research_run_id",
        "research_backtest_results",
        ["research_run_id"],
    )
    op.create_index(
        "ix_research_backtest_results_backtest_run_id",
        "research_backtest_results",
        ["backtest_run_id"],
    )
    op.create_index("ix_research_backtest_results_strategy_id", "research_backtest_results", ["strategy_id"])
    op.create_index(
        "ix_research_backtest_results_canonical_symbol",
        "research_backtest_results",
        ["canonical_symbol"],
    )
    op.create_index(
        "ix_research_backtest_results_instrument_id",
        "research_backtest_results",
        ["instrument_id"],
    )
    op.create_index("ix_research_backtest_results_status", "research_backtest_results", ["status"])

    op.create_table(
        "backtest_equity_points",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("backtest_run_id", sa.String(128), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("equity", DECIMAL, nullable=False),
        sa.Column("drawdown", DECIMAL, nullable=False),
    )
    op.create_index(
        "ix_backtest_equity_points_backtest_run_id",
        "backtest_equity_points",
        ["backtest_run_id"],
    )

    op.create_table(
        "backtest_trade_records",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("backtest_run_id", sa.String(128), nullable=False),
        sa.Column("instrument_id", sa.String(128), nullable=False),
        sa.Column("side", sa.String(16), nullable=False),
        sa.Column("entry_ts", sa.DateTime(timezone=True), nullable=True),
        sa.Column("exit_ts", sa.DateTime(timezone=True), nullable=True),
        sa.Column("entry_price", DECIMAL, nullable=True),
        sa.Column("exit_price", DECIMAL, nullable=True),
        sa.Column("qty", DECIMAL, nullable=False),
        sa.Column("gross_pnl", DECIMAL, nullable=False),
        sa.Column("net_pnl", DECIMAL, nullable=False),
        sa.Column("r_multiple", DECIMAL, nullable=True),
        sa.Column("reason", sa.String(2048), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
    )
    op.create_index(
        "ix_backtest_trade_records_backtest_run_id",
        "backtest_trade_records",
        ["backtest_run_id"],
    )
    op.create_index("ix_backtest_trade_records_instrument_id", "backtest_trade_records", ["instrument_id"])


def downgrade() -> None:
    op.drop_index("ix_backtest_trade_records_instrument_id", table_name="backtest_trade_records")
    op.drop_index("ix_backtest_trade_records_backtest_run_id", table_name="backtest_trade_records")
    op.drop_table("backtest_trade_records")
    op.drop_index("ix_backtest_equity_points_backtest_run_id", table_name="backtest_equity_points")
    op.drop_table("backtest_equity_points")
    op.drop_index("ix_research_backtest_results_status", table_name="research_backtest_results")
    op.drop_index("ix_research_backtest_results_instrument_id", table_name="research_backtest_results")
    op.drop_index("ix_research_backtest_results_canonical_symbol", table_name="research_backtest_results")
    op.drop_index("ix_research_backtest_results_strategy_id", table_name="research_backtest_results")
    op.drop_index("ix_research_backtest_results_backtest_run_id", table_name="research_backtest_results")
    op.drop_index("ix_research_backtest_results_research_run_id", table_name="research_backtest_results")
    op.drop_table("research_backtest_results")
    op.drop_index("ix_research_runs_status", table_name="research_runs")
    op.drop_index("ix_research_runs_instrument_id", table_name="research_runs")
    op.drop_index("ix_research_runs_canonical_symbol", table_name="research_runs")
    op.drop_index("ix_research_runs_strategy_id", table_name="research_runs")
    op.drop_table("research_runs")
