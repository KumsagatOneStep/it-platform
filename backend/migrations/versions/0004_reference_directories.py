"""Справочники: локации, типы техники, категории расходников, причины выдачи, типы заявок

Revision ID: 0004
Revises: 0003
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _is_active() -> sa.Column[bool]:
    return sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true())


def upgrade() -> None:
    op.create_table(
        "locations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        _is_active(),
        sa.UniqueConstraint("name", name="uq_locations_name"),
        schema="common",
    )
    for table in ("asset_types", "stock_categories"):
        op.create_table(
            table,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(255), nullable=False),
            _is_active(),
            sa.UniqueConstraint("name", name=f"uq_{table}_name"),
            schema="common",
        )
    op.create_table(
        "issue_reasons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("applicability", sa.String(16), nullable=False),
        _is_active(),
        sa.UniqueConstraint("name", name="uq_issue_reasons_name"),
        sa.CheckConstraint(
            "applicability IN ('assets', 'stock', 'both')", name="ck_issue_reasons_applicability"
        ),
        schema="common",
    )
    op.create_table(
        "ticket_types",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("default_assignee_id", sa.Integer(), nullable=True),
        _is_active(),
        sa.UniqueConstraint("code", name="uq_ticket_types_code"),
        sa.UniqueConstraint("name", name="uq_ticket_types_name"),
        sa.ForeignKeyConstraint(
            ["default_assignee_id"],
            ["common.users.id"],
            name="fk_ticket_types_default_assignee_id_users",
        ),
        schema="common",
    )


def downgrade() -> None:
    for table in ("ticket_types", "issue_reasons", "stock_categories", "asset_types", "locations"):
        op.drop_table(table, schema="common")
