"""Отделы

Revision ID: 0003
Revises: 0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "departments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("head_id", sa.Integer(), nullable=True),
        sa.UniqueConstraint("name", name="uq_departments_name"),
        sa.ForeignKeyConstraint(
            ["head_id"], ["common.users.id"], name="fk_departments_head_id_users"
        ),
        schema="common",
    )
    op.create_foreign_key(
        "fk_users_department_id_departments",
        "users",
        "departments",
        ["department_id"],
        ["id"],
        source_schema="common",
        referent_schema="common",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_users_department_id_departments", "users", schema="common", type_="foreignkey"
    )
    op.drop_table("departments", schema="common")
