from typing import Any, NoReturn

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import diff_values, record_audit
from app.core.db import constraint_name
from app.core.errors import ConflictError, NotFoundError, ValidationFailedError
from app.core.events import event_bus
from app.core.text import normalize_text_field
from app.modules.directories.events import DepartmentHeadChanged
from app.modules.directories.models import Department
from app.modules.users_auth.service import UserRole, get_user_info

_HEAD_ROLES = frozenset({UserRole.MANAGER, UserRole.ADMIN})


def _raise_integrity_error(exc: IntegrityError) -> NoReturn:
    if constraint_name(exc) == "uq_departments_name":
        raise ConflictError(
            "Отдел с таким названием уже существует", code="department_name_taken"
        ) from exc
    raise exc


def _normalize_name(name: str) -> str:
    """Убирает пробелы по краям; одинаково для create и update (см. review round 1)."""
    return normalize_text_field(
        name, code="department_name_blank", message="Название отдела не может быть пустым"
    )


async def _validate_head(session: AsyncSession, user_id: int) -> None:
    info = await get_user_info(session, user_id)
    if info is None or not info.is_active:
        raise ValidationFailedError(
            "Руководитель не найден или деактивирован", code="head_not_found"
        )
    if info.role not in _HEAD_ROLES:
        raise ValidationFailedError(
            "Руководителем отдела может быть только Manager или Admin", code="head_invalid_role"
        )


async def list_departments(session: AsyncSession) -> list[Department]:
    return list(await session.scalars(select(Department).order_by(Department.name)))


async def create_department(
    session: AsyncSession, *, actor_id: int, name: str, head_id: int | None
) -> Department:
    normalized_name = _normalize_name(name)
    if head_id is not None:
        await _validate_head(session, head_id)
    department = Department(name=normalized_name, head_id=head_id)
    try:
        async with session.begin_nested():
            session.add(department)
    except IntegrityError as exc:
        _raise_integrity_error(exc)
    record_audit(
        session,
        entity_type="department",
        entity_id=department.id,
        user_id=actor_id,
        action="create",
        diff=diff_values({}, {"name": department.name, "head_id": head_id}),
    )
    await session.commit()
    return department


async def update_department(
    session: AsyncSession, *, actor_id: int, department_id: int, updates: dict[str, Any]
) -> Department:
    department = await session.get(Department, department_id)
    if department is None:
        raise NotFoundError("Отдел не найден", code="department_not_found")
    if "name" in updates:
        updates = {**updates, "name": _normalize_name(updates["name"])}
    if updates.get("head_id") is not None:
        await _validate_head(session, updates["head_id"])
    before = {key: getattr(department, key) for key in updates}
    try:
        async with session.begin_nested():
            for key, value in updates.items():
                setattr(department, key, value)
    except IntegrityError as exc:
        _raise_integrity_error(exc)
    if "head_id" in updates and before["head_id"] != department.head_id:
        await event_bus.publish(
            session,
            DepartmentHeadChanged(
                department_id=department.id,
                old_head_id=before["head_id"],
                new_head_id=department.head_id,
            ),
        )
    diff = diff_values(before, updates)
    if diff:
        record_audit(
            session,
            entity_type="department",
            entity_id=department.id,
            user_id=actor_id,
            action="update",
            diff=diff,
        )
    await session.commit()
    return department
