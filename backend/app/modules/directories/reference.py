from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, NoReturn

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import diff_values, record_audit
from app.core.db import constraint_name
from app.core.errors import ConflictError, NotFoundError, ValidationFailedError
from app.core.text import normalize_text_field

Validator = Callable[[AsyncSession, dict[str, Any]], Awaitable[None]]

_FIELD_LABELS: dict[str, str] = {
    "name": "Название",
    "code": "Код",
}


@dataclass(frozen=True)
class ReferenceSpec:
    slug: str
    model: type[Any]
    read_schema: type[BaseModel]
    create_schema: type[BaseModel]
    update_schema: type[BaseModel]
    entity_type: str
    validate: Validator | None = None
    text_fields: tuple[str, ...] = ("name",)
    """Строковые поля, которые нормализуются (strip) и не могут быть пустыми после этого.

    Реализация общая для всех справочников (см. review round 1 задачи 10 —
    department_name_blank): один и тот же helper вместо копии на сущность.
    """


def _raise_integrity_error(exc: IntegrityError) -> NoReturn:
    name = constraint_name(exc) or ""
    if name.startswith("uq_"):
        raise ConflictError(
            "Элемент с таким значением уже существует",
            code="already_exists",
            details={"constraint": name},
        ) from exc
    if name.startswith("fk_"):
        raise ValidationFailedError(
            "Связанная запись не найдена", code="reference_not_found"
        ) from exc
    raise exc


def _normalize_text_fields(spec: ReferenceSpec, values: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(values)
    for field_name in spec.text_fields:
        raw = normalized.get(field_name)
        if isinstance(raw, str):
            label = _FIELD_LABELS.get(field_name, field_name)
            normalized[field_name] = normalize_text_field(
                raw, code=f"{field_name}_blank", message=f"{label} не может быть пустым"
            )
    return normalized


async def list_items(
    session: AsyncSession, spec: ReferenceSpec, *, include_inactive: bool
) -> list[Any]:
    stmt = select(spec.model).order_by(spec.model.name, spec.model.id)
    if not include_inactive:
        stmt = stmt.where(spec.model.is_active.is_(True))
    return list(await session.scalars(stmt))


async def create_item(
    session: AsyncSession, spec: ReferenceSpec, *, actor_id: int, data: dict[str, Any]
) -> Any:
    data = _normalize_text_fields(spec, data)
    if spec.validate is not None:
        await spec.validate(session, data)
    item = spec.model(**data)
    try:
        async with session.begin_nested():
            session.add(item)
    except IntegrityError as exc:
        _raise_integrity_error(exc)
    record_audit(
        session,
        entity_type=spec.entity_type,
        entity_id=item.id,
        user_id=actor_id,
        action="create",
        diff=diff_values({}, data),
    )
    await session.commit()
    return item


async def update_item(
    session: AsyncSession,
    spec: ReferenceSpec,
    *,
    actor_id: int,
    item_id: int,
    updates: dict[str, Any],
) -> Any:
    item = await session.get(spec.model, item_id)
    if item is None:
        raise NotFoundError("Элемент справочника не найден", code="reference_item_not_found")
    updates = _normalize_text_fields(spec, updates)
    if spec.validate is not None:
        await spec.validate(session, updates)
    before = {key: getattr(item, key) for key in updates}
    try:
        async with session.begin_nested():
            for key, value in updates.items():
                setattr(item, key, value)
    except IntegrityError as exc:
        _raise_integrity_error(exc)
    diff = diff_values(before, updates)
    if diff:
        record_audit(
            session,
            entity_type=spec.entity_type,
            entity_id=item.id,
            user_id=actor_id,
            action="update",
            diff=diff,
        )
    await session.commit()
    return item
