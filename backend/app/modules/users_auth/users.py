from dataclasses import asdict
from typing import Any, NoReturn

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import diff_values, record_audit
from app.core.db import constraint_name
from app.core.errors import ConflictError, NotFoundError, ValidationFailedError
from app.core.events import event_bus
from app.modules.users_auth.events import UserDeactivationRequested
from app.modules.users_auth.models import User, UserRole
from app.modules.users_auth.passwords import (
    generate_temporary_password,
    hash_password_async,
    validate_password_strength,
)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def raise_user_integrity_error(exc: IntegrityError) -> NoReturn:
    name = constraint_name(exc)
    if name == "uq_users_email":
        raise ConflictError(
            "Пользователь с таким email уже существует", code="email_taken"
        ) from exc
    if name == "fk_users_department_id_departments":
        raise ValidationFailedError("Отдел не найден", code="department_not_found") from exc
    raise exc


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    result: User | None = await session.scalar(
        select(User).where(User.email == normalize_email(email))
    )
    return result


async def create_user(
    session: AsyncSession,
    *,
    email: str,
    full_name: str,
    role: UserRole,
    department_id: int | None,
    password: str,
    must_change_password: bool,
) -> User:
    user = User(
        email=normalize_email(email),
        full_name=full_name.strip(),
        password_hash=await hash_password_async(password),
        role=role,
        department_id=department_id,
        must_change_password=must_change_password,
    )
    try:
        async with session.begin_nested():
            session.add(user)
    except IntegrityError as exc:
        raise_user_integrity_error(exc)
    return user


async def create_first_admin(
    session: AsyncSession, *, email: str, full_name: str, password: str
) -> User:
    validate_password_strength(password)
    user = await create_user(
        session,
        email=email,
        full_name=full_name,
        role=UserRole.ADMIN,
        department_id=None,
        password=password,
        must_change_password=False,
    )
    record_audit(
        session,
        entity_type="user",
        entity_id=user.id,
        user_id=None,
        action="create",
        diff={"email": [None, user.email], "role": [None, user.role.value]},
    )
    await session.commit()
    return user


async def list_users(
    session: AsyncSession,
    *,
    q: str | None,
    role: UserRole | None,
    department_id: int | None,
    is_active: bool | None,
    limit: int,
    offset: int,
) -> tuple[list[User], int]:
    stmt = select(User)
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(or_(User.full_name.ilike(pattern), User.email.ilike(pattern)))
    if role is not None:
        stmt = stmt.where(User.role == role)
    if department_id is not None:
        stmt = stmt.where(User.department_id == department_id)
    if is_active is not None:
        stmt = stmt.where(User.is_active.is_(is_active))
    total = await session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = await session.scalars(
        stmt.order_by(User.full_name, User.id).limit(limit).offset(offset)
    )
    return list(items), total


async def search_active_users(session: AsyncSession, *, q: str, limit: int) -> list[User]:
    pattern = f"%{q.strip()}%"
    items = await session.scalars(
        select(User)
        .where(
            User.is_active.is_(True), or_(User.full_name.ilike(pattern), User.email.ilike(pattern))
        )
        .order_by(User.full_name, User.id)
        .limit(limit)
    )
    return list(items)


async def get_user_or_404(session: AsyncSession, user_id: int) -> User:
    user = await session.get(User, user_id)
    if user is None:
        raise NotFoundError("Пользователь не найден", code="user_not_found")
    return user


async def _ensure_not_last_admin(session: AsyncSession, user_id: int) -> None:
    other_admins = await session.scalar(
        select(func.count())
        .select_from(User)
        .where(User.role == UserRole.ADMIN, User.is_active.is_(True), User.id != user_id)
    )
    if not other_admins:
        raise ConflictError(
            "В системе должен оставаться хотя бы один активный администратор", code="last_admin"
        )


async def admin_create_user(
    session: AsyncSession,
    *,
    actor_id: int,
    email: str,
    full_name: str,
    role: UserRole,
    department_id: int | None,
) -> tuple[User, str]:
    temporary_password = generate_temporary_password()
    user = await create_user(
        session,
        email=email,
        full_name=full_name,
        role=role,
        department_id=department_id,
        password=temporary_password,
        must_change_password=True,
    )
    record_audit(
        session,
        entity_type="user",
        entity_id=user.id,
        user_id=actor_id,
        action="create",
        diff=diff_values(
            {},
            {
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "department_id": user.department_id,
            },
        ),
    )
    await session.commit()
    return user, temporary_password


async def update_user(
    session: AsyncSession, *, actor_id: int, user_id: int, updates: dict[str, Any]
) -> User:
    user = await get_user_or_404(session, user_id)
    if (
        "role" in updates
        and user.role == UserRole.ADMIN
        and updates["role"] != UserRole.ADMIN
        and user.is_active
    ):
        await _ensure_not_last_admin(session, user.id)
    before = {key: getattr(user, key) for key in updates}
    try:
        async with session.begin_nested():
            for key, value in updates.items():
                setattr(user, key, value)
    except IntegrityError as exc:
        raise_user_integrity_error(exc)
    diff = diff_values(before, updates)
    if diff:
        record_audit(
            session,
            entity_type="user",
            entity_id=user.id,
            user_id=actor_id,
            action="update",
            diff=diff,
        )
    await session.commit()
    return user


async def deactivate_user(session: AsyncSession, *, actor_id: int, user_id: int) -> User:
    user = await get_user_or_404(session, user_id)
    if user.id == actor_id:
        raise ConflictError(
            "Нельзя деактивировать собственную учётную запись", code="cannot_deactivate_self"
        )
    if not user.is_active:
        return user
    if user.role == UserRole.ADMIN:
        await _ensure_not_last_admin(session, user.id)
    event = UserDeactivationRequested(user_id=user.id)
    await event_bus.publish(session, event)
    if event.blockers:
        raise ConflictError(
            "Перед деактивацией нужно передать ответственность другим сотрудникам",
            code="deactivation_blocked",
            details=[asdict(blocker) for blocker in event.blockers],
        )
    # Импорт внутри функции: auth.py импортирует users.py.
    from app.modules.users_auth.auth import revoke_all_refresh_tokens

    user.is_active = False
    await revoke_all_refresh_tokens(session, user.id, reason="deactivated")
    record_audit(
        session,
        entity_type="user",
        entity_id=user.id,
        user_id=actor_id,
        action="deactivate",
        diff={"is_active": [True, False]},
    )
    await session.commit()
    return user


async def activate_user(session: AsyncSession, *, actor_id: int, user_id: int) -> User:
    user = await get_user_or_404(session, user_id)
    if user.is_active:
        return user
    user.is_active = True
    record_audit(
        session,
        entity_type="user",
        entity_id=user.id,
        user_id=actor_id,
        action="activate",
        diff={"is_active": [False, True]},
    )
    await session.commit()
    return user


async def issue_temporary_password(session: AsyncSession, *, actor_id: int, user_id: int) -> str:
    from app.modules.users_auth.auth import revoke_all_refresh_tokens

    user = await get_user_or_404(session, user_id)
    temporary_password = generate_temporary_password()
    user.password_hash = await hash_password_async(temporary_password)
    user.must_change_password = True
    await revoke_all_refresh_tokens(session, user.id, reason="temporary_password")
    record_audit(
        session,
        entity_type="user",
        entity_id=user.id,
        user_id=actor_id,
        action="temporary_password",
        diff={},
    )
    await session.commit()
    return temporary_password
