from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "20260617_0002"
down_revision: str | None = "20260617_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DECIMAL = sa.Numeric(38, 18)


def upgrade() -> None:
    op.create_index(
        "ix_instruments_venue_asset_class_native_symbol",
        "instruments",
        ["venue", "asset_class", "native_symbol"],
    )
    op.create_table(
        "contract_specs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("instrument_id", sa.String(128), nullable=False),
        sa.Column("lot_size", DECIMAL, nullable=False),
        sa.Column("tick_size", DECIMAL, nullable=False),
        sa.Column("tick_value", DECIMAL, nullable=False),
        sa.Column("currency", sa.String(16), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("first_trade_date", sa.Date(), nullable=True),
        sa.Column("last_trade_date", sa.Date(), nullable=True),
        sa.Column("underlying_symbol", sa.String(128), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("instrument_id", name="uq_contract_specs_instrument_id"),
    )
    op.create_index("ix_contract_specs_instrument_id", "contract_specs", ["instrument_id"])


def downgrade() -> None:
    op.drop_index("ix_contract_specs_instrument_id", table_name="contract_specs")
    op.drop_table("contract_specs")
    op.drop_index("ix_instruments_venue_asset_class_native_symbol", table_name="instruments")
