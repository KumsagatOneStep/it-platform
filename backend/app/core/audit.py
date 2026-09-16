from collections.abc import Mapping
from datetime import date, datetime
from enum import Enum
from typing import Any

from sqlalchemy import BigInteger, DateTime, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_log_entity", "entity_type", "entity_id"),
        {"schema": "common"},
    )
    __mapper_args__ = {"eager_defaults": True}  # noqa: RUF012

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[str] = mapped_column(String(64))
    user_id: Mapped[int | None] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(32))
    diff: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


def _json_safe(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime | date):
        return value.isoformat()
    return value


def diff_values(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, list[Any]]:
    return {
        key: [_json_safe(before.get(key)), _json_safe(value)]
        for key, value in after.items()
        if before.get(key) != value
    }


def record_audit(
    session: AsyncSession,
    *,
    entity_type: str,
    entity_id: int | str,
    user_id: int | None,
    action: str,
    diff: dict[str, Any],
) -> None:
    session.add(
        AuditLog(
            entity_type=entity_type,
            entity_id=str(entity_id),
            user_id=user_id,
            action=action,
            diff=diff,
        )
    )
