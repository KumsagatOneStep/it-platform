"""Пользователи и refresh-токены

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.CheckConstraint("role IN ('employee', 'manager', 'admin')", name="ck_users_role"),
        schema="common",
    )
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["common.users.id"],
            name="fk_refresh_tokens_user_id_users",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("token_hash", name="uq_refresh_tokens_token_hash"),
        schema="common",
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"], schema="common")
    op.create_foreign_key(
        "fk_audit_log_user_id_users",
        "audit_log",
        "users",
        ["user_id"],
        ["id"],
        source_schema="common",
        referent_schema="common",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_audit_log_user_id_users", "audit_log", schema="common", type_="foreignkey"
    )
    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens", schema="common")
    op.drop_table("refresh_tokens", schema="common")
    op.drop_table("users", schema="common")
