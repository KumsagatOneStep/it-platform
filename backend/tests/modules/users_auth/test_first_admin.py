import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditLog
from app.core.errors import ConflictError, ValidationFailedError
from app.modules.users_auth.models import UserRole
from app.modules.users_auth.passwords import verify_password
from app.modules.users_auth.service import create_first_admin


async def test_creates_active_admin_with_normalized_email(db_session: AsyncSession) -> None:
    user = await create_first_admin(
        db_session, email="  Admin@Company.RU ", full_name="Администратор", password="Strong-Pass-1"
    )

    assert user.email == "admin@company.ru"
    assert user.role is UserRole.ADMIN
    assert user.is_active
    assert not user.must_change_password
    assert verify_password(user.password_hash, "Strong-Pass-1")
    audit = (
        await db_session.scalars(select(AuditLog).where(AuditLog.entity_id == str(user.id)))
    ).one()
    assert audit.entity_type == "user"
    assert audit.action == "create"


async def test_duplicate_email_rejected(db_session: AsyncSession) -> None:
    await create_first_admin(
        db_session, email="admin@company.ru", full_name="Первый", password="Strong-Pass-1"
    )

    with pytest.raises(ConflictError) as exc_info:
        await create_first_admin(
            db_session, email="ADMIN@company.ru", full_name="Второй", password="Strong-Pass-1"
        )

    assert exc_info.value.code == "email_taken"


async def test_weak_password_rejected(db_session: AsyncSession) -> None:
    with pytest.raises(ValidationFailedError):
        await create_first_admin(
            db_session, email="admin@company.ru", full_name="Администратор", password="short"
        )
