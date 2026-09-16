from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditLog, diff_values, record_audit


class _Color(StrEnum):
    RED = "red"
    BLUE = "blue"


def test_diff_values_returns_only_changed_fields() -> None:
    before = {"name": "Старое", "color": _Color.RED, "count": 1}
    after = {"name": "Новое", "color": _Color.BLUE, "count": 1}

    assert diff_values(before, after) == {"name": ["Старое", "Новое"], "color": ["red", "blue"]}


def test_diff_values_serializes_datetimes() -> None:
    moment = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)

    assert diff_values({}, {"at": moment}) == {"at": [None, "2026-09-16T12:00:00+00:00"]}


async def test_record_audit_persists_entry(db_session: AsyncSession) -> None:
    record_audit(
        db_session,
        entity_type="test_entity",
        entity_id=42,
        user_id=None,
        action="create",
        diff={"name": [None, "Тест"]},
    )
    await db_session.flush()

    row = (
        await db_session.scalars(select(AuditLog).where(AuditLog.entity_type == "test_entity"))
    ).one()
    assert row.entity_id == "42"
    assert row.action == "create"
    assert row.diff == {"name": [None, "Тест"]}
    assert row.created_at is not None
