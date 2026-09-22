"""Оргтехника: активы и история активов

Revision ID: 0005
Revises: 0004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_STATUSES = "'in_stock', 'reserved', 'in_use', 'in_repair', 'written_off'"
_EVENT_TYPES = "'created', 'issued', 'returned', 'status_changed', 'moved', 'edited', 'written_off'"


def upgrade() -> None:
    op.create_table(
        "assets",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("asset_type_id", sa.Integer(), nullable=False),
        sa.Column("inventory_number", sa.String(64), nullable=False),
        sa.Column("serial_number", sa.String(128), nullable=True),
        sa.Column("model", sa.String(200), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=True),
        sa.Column("accepted_at", sa.Date(), nullable=False),
        sa.Column("purchased_at", sa.Date(), nullable=True),
        sa.Column("warranty_until", sa.Date(), nullable=True),
        sa.Column("initial_cost", sa.Numeric(12, 2), nullable=True),
        sa.Column("needs_review", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("inventory_number", name="uq_assets_inventory_number"),
        sa.CheckConstraint(f"status IN ({_STATUSES})", name="ck_assets_status"),
        sa.CheckConstraint(
            "status <> 'in_use' OR owner_id IS NOT NULL", name="ck_assets_in_use_has_owner"
        ),
        sa.CheckConstraint(
            "status NOT IN ('in_stock', 'reserved', 'written_off') OR owner_id IS NULL",
            name="ck_assets_stock_has_no_owner",
        ),
        sa.CheckConstraint(
            "initial_cost IS NULL OR initial_cost >= 0", name="ck_assets_initial_cost"
        ),
        sa.ForeignKeyConstraint(
            ["asset_type_id"], ["common.asset_types.id"], name="fk_assets_asset_type_id_asset_types"
        ),
        sa.ForeignKeyConstraint(
            ["location_id"], ["common.locations.id"], name="fk_assets_location_id_locations"
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["common.users.id"], name="fk_assets_owner_id_users"),
        schema="equipment",
    )
    for column in ("asset_type_id", "status", "location_id", "owner_id"):
        op.create_index(f"ix_assets_{column}", "assets", [column], schema="equipment")
    op.create_index(
        "uq_assets_serial_number",
        "assets",
        ["serial_number"],
        unique=True,
        schema="equipment",
        postgresql_where=sa.text("serial_number IS NOT NULL"),
    )

    op.create_table(
        "asset_events",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("asset_id", sa.BigInteger(), nullable=False),
        sa.Column("event_type", sa.String(16), nullable=False),
        sa.Column("operation", sa.String(32), nullable=True),
        sa.Column("from_owner_id", sa.Integer(), nullable=True),
        sa.Column("to_owner_id", sa.Integer(), nullable=True),
        sa.Column("from_status", sa.String(16), nullable=True),
        sa.Column("to_status", sa.String(16), nullable=True),
        sa.Column("from_location_id", sa.Integer(), nullable=True),
        sa.Column("to_location_id", sa.Integer(), nullable=True),
        sa.Column("reason_id", sa.Integer(), nullable=True),
        sa.Column("changes", postgresql.JSONB(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("performed_by", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(f"event_type IN ({_EVENT_TYPES})", name="ck_asset_events_event_type"),
        sa.ForeignKeyConstraint(
            ["asset_id"], ["equipment.assets.id"], name="fk_asset_events_asset_id_assets"
        ),
        sa.ForeignKeyConstraint(
            ["from_owner_id"], ["common.users.id"], name="fk_asset_events_from_owner_id_users"
        ),
        sa.ForeignKeyConstraint(
            ["to_owner_id"], ["common.users.id"], name="fk_asset_events_to_owner_id_users"
        ),
        sa.ForeignKeyConstraint(
            ["from_location_id"],
            ["common.locations.id"],
            name="fk_asset_events_from_location_id_locations",
        ),
        sa.ForeignKeyConstraint(
            ["to_location_id"],
            ["common.locations.id"],
            name="fk_asset_events_to_location_id_locations",
        ),
        sa.ForeignKeyConstraint(
            ["reason_id"],
            ["common.issue_reasons.id"],
            name="fk_asset_events_reason_id_issue_reasons",
        ),
        sa.ForeignKeyConstraint(
            ["performed_by"], ["common.users.id"], name="fk_asset_events_performed_by_users"
        ),
        schema="equipment",
    )
    op.create_index(
        "ix_asset_events_asset_id_id", "asset_events", ["asset_id", "id"], schema="equipment"
    )


def downgrade() -> None:
    op.drop_table("asset_events", schema="equipment")
    op.drop_table("assets", schema="equipment")
