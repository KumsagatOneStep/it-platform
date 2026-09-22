"""Расходники: позиции на складах и движения остатков

Revision ID: 0006
Revises: 0005
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_MOVEMENT_TYPES = "'receipt', 'issue', 'write_off', 'adjustment', 'transfer_out', 'transfer_in'"


def upgrade() -> None:
    op.create_table(
        "stock_items",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("stock_category_id", sa.Integer(), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("min_quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("quantity >= 0", name="ck_stock_items_quantity"),
        sa.CheckConstraint("min_quantity >= 0", name="ck_stock_items_min_quantity"),
        sa.CheckConstraint("is_active OR quantity = 0", name="ck_stock_items_inactive_is_empty"),
        sa.ForeignKeyConstraint(
            ["stock_category_id"],
            ["common.stock_categories.id"],
            name="fk_stock_items_stock_category_id_stock_categories",
        ),
        sa.ForeignKeyConstraint(
            ["location_id"], ["common.locations.id"], name="fk_stock_items_location_id_locations"
        ),
        schema="equipment",
    )
    for column in ("stock_category_id", "location_id"):
        op.create_index(f"ix_stock_items_{column}", "stock_items", [column], schema="equipment")
    op.create_index(
        "uq_stock_items_name_location",
        "stock_items",
        [sa.text("lower(name)"), "location_id"],
        unique=True,
        schema="equipment",
    )

    op.create_table(
        "stock_movements",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("stock_item_id", sa.BigInteger(), nullable=False),
        sa.Column("movement_type", sa.String(16), nullable=False),
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column("quantity_after", sa.Integer(), nullable=False),
        sa.Column("document_date", sa.Date(), nullable=True),
        sa.Column("transfer_id", sa.Uuid(), nullable=True),
        sa.Column("reason_id", sa.Integer(), nullable=True),
        sa.Column("recipient_id", sa.Integer(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("performed_by", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            f"movement_type IN ({_MOVEMENT_TYPES})", name="ck_stock_movements_movement_type"
        ),
        sa.CheckConstraint("delta <> 0", name="ck_stock_movements_delta_not_zero"),
        sa.CheckConstraint("quantity_after >= 0", name="ck_stock_movements_quantity_after"),
        sa.CheckConstraint(
            "movement_type NOT IN ('receipt', 'transfer_in') OR delta > 0",
            name="ck_stock_movements_incoming_sign",
        ),
        sa.CheckConstraint(
            "movement_type NOT IN ('issue', 'write_off', 'transfer_out') OR delta < 0",
            name="ck_stock_movements_outgoing_sign",
        ),
        sa.CheckConstraint(
            "(movement_type = 'receipt') = (document_date IS NOT NULL)",
            name="ck_stock_movements_document_date",
        ),
        sa.CheckConstraint(
            "(movement_type IN ('transfer_out', 'transfer_in')) = (transfer_id IS NOT NULL)",
            name="ck_stock_movements_transfer_id",
        ),
        sa.CheckConstraint(
            "(movement_type = 'issue') = (recipient_id IS NOT NULL)",
            name="ck_stock_movements_recipient",
        ),
        sa.CheckConstraint(
            "movement_type <> 'adjustment' OR comment IS NOT NULL",
            name="ck_stock_movements_adjustment_comment",
        ),
        sa.ForeignKeyConstraint(
            ["stock_item_id"],
            ["equipment.stock_items.id"],
            name="fk_stock_movements_stock_item_id_stock_items",
        ),
        sa.ForeignKeyConstraint(
            ["reason_id"],
            ["common.issue_reasons.id"],
            name="fk_stock_movements_reason_id_issue_reasons",
        ),
        sa.ForeignKeyConstraint(
            ["recipient_id"], ["common.users.id"], name="fk_stock_movements_recipient_id_users"
        ),
        sa.ForeignKeyConstraint(
            ["performed_by"], ["common.users.id"], name="fk_stock_movements_performed_by_users"
        ),
        schema="equipment",
    )
    op.create_index(
        "ix_stock_movements_stock_item_id_id",
        "stock_movements",
        ["stock_item_id", "id"],
        schema="equipment",
    )
    op.create_index(
        "ix_stock_movements_transfer_id", "stock_movements", ["transfer_id"], schema="equipment"
    )
    op.create_index(
        "ix_stock_movements_created_at", "stock_movements", ["created_at"], schema="equipment"
    )


def downgrade() -> None:
    op.drop_table("stock_movements", schema="equipment")
    op.drop_table("stock_items", schema="equipment")
