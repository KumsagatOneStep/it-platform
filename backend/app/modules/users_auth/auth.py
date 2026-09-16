import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.config import get_settings
from app.core.errors import UnauthorizedError, ValidationFailedError
from app.modules.users_auth.models import RefreshToken, User
from app.modules.users_auth.passwords import (
    dummy_verify_async,
    hash_password_async,
    validate_password_strength,
    verify_password_async,
)
from app.modules.users_auth.tokens import (
    create_access_token,
    hash_refresh_token,
    new_refresh_token,
)
from app.modules.users_auth.users import get_user_by_email

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    must_change_password: bool


def _now() -> datetime:
    return datetime.now(UTC)


def _invalid_refresh() -> UnauthorizedError:
    return UnauthorizedError("Сессия истекла, войдите снова", code="invalid_refresh_token")


async def authenticate(session: AsyncSession, email: str, password: str) -> User | None:
    user = await get_user_by_email(session, email)
    if user is None:
        await dummy_verify_async(password)
        return None
    if not await verify_password_async(user.password_hash, password) or not user.is_active:
        return None
    return user


async def issue_tokens(session: AsyncSession, user: User) -> TokenPair:
    raw, token_hash = new_refresh_token()
    session.add(
        RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=_now() + timedelta(days=get_settings().refresh_token_ttl_days),
        )
    )
    await session.commit()
    return TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=raw,
        must_change_password=user.must_change_password,
    )


async def login(session: AsyncSession, *, email: str, password: str) -> TokenPair:
    user = await authenticate(session, email, password)
    if user is None:
        raise UnauthorizedError("Неверный email или пароль", code="invalid_credentials")
    return await issue_tokens(session, user)


async def revoke_all_refresh_tokens(session: AsyncSession, user_id: int, *, reason: str) -> None:
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=_now(), revoked_reason=reason)
    )


async def rotate_refresh_token(session: AsyncSession, raw: str | None) -> TokenPair:
    if not raw:
        raise _invalid_refresh()
    token = await session.scalar(
        select(RefreshToken)
        .where(RefreshToken.token_hash == hash_refresh_token(raw))
        .with_for_update()
    )
    if token is None:
        raise _invalid_refresh()
    now = _now()
    if token.revoked_at is not None:
        if token.revoked_reason == "rotated":
            # Повторное использование уже провёрнутого (ротированного) токена —
            # вероятная кража: отзываем все сессии пользователя.
            await revoke_all_refresh_tokens(session, token.user_id, reason="reuse_detected")
            await session.commit()
            logger.warning("auth.refresh_token_reuse", extra={"user_id": token.user_id})
        # Токен отозван по другой причине (logout, смена пароля) — это не признак кражи,
        # остальные сессии пользователя не трогаем.
        raise _invalid_refresh()
    if token.expires_at <= now:
        raise _invalid_refresh()
    user = await session.get(User, token.user_id)
    if user is None or not user.is_active:
        raise _invalid_refresh()
    token.revoked_at = now
    token.revoked_reason = "rotated"
    return await issue_tokens(session, user)


async def logout(session: AsyncSession, raw: str | None) -> None:
    if not raw:
        return
    await session.execute(
        update(RefreshToken)
        .where(
            RefreshToken.token_hash == hash_refresh_token(raw),
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=_now(), revoked_reason="logout")
    )
    await session.commit()


async def change_password(
    session: AsyncSession, *, user_id: int, current_password: str, new_password: str
) -> TokenPair:
    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("Требуется вход", code="not_authenticated")
    if not await verify_password_async(user.password_hash, current_password):
        raise ValidationFailedError(
            "Текущий пароль указан неверно", code="invalid_current_password"
        )
    validate_password_strength(new_password)
    if await verify_password_async(user.password_hash, new_password):
        raise ValidationFailedError(
            "Новый пароль должен отличаться от текущего", code="password_reused"
        )
    user.password_hash = await hash_password_async(new_password)
    user.must_change_password = False
    await revoke_all_refresh_tokens(session, user.id, reason="password_change")
    record_audit(
        session,
        entity_type="user",
        entity_id=user.id,
        user_id=user.id,
        action="change_password",
        diff={},
    )
    return await issue_tokens(session, user)
