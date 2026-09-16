from typing import NoReturn

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.db import constraint_name
from app.core.errors import ConflictError, ValidationFailedError
from app.modules.users_auth.models import User, UserRole
from app.modules.users_auth.passwords import hash_password_async, validate_password_strength


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
