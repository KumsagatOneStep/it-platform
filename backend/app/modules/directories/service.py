"""Публичный интерфейс модуля directories.

Другие модули импортируют только этот файл и events.py.
"""

from dataclasses import dataclass
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.directories.models import AssetType, Department, IssueReason, Location

ReferenceKind = Literal["locations", "asset-types", "issue-reasons"]

_ReferenceModel = Location | AssetType | IssueReason

_REFERENCE_MODELS: dict[ReferenceKind, type[_ReferenceModel]] = {
    "locations": Location,
    "asset-types": AssetType,
    "issue-reasons": IssueReason,
}


@dataclass(frozen=True)
class DepartmentInfo:
    id: int
    name: str
    head_id: int | None


@dataclass(frozen=True)
class ReferenceItemInfo:
    id: int
    name: str
    is_active: bool
    applicability: str | None
    """Только для причин выдачи: assets / stock / both."""


async def get_department(session: AsyncSession, department_id: int) -> DepartmentInfo | None:
    department = await session.get(Department, department_id)
    if department is None:
        return None
    return DepartmentInfo(id=department.id, name=department.name, head_id=department.head_id)


async def get_reference_item(
    session: AsyncSession, kind: ReferenceKind, item_id: int
) -> ReferenceItemInfo | None:
    item: _ReferenceModel | None = await session.get(_REFERENCE_MODELS[kind], item_id)
    if item is None:
        return None
    applicability = item.applicability.value if isinstance(item, IssueReason) else None
    return ReferenceItemInfo(
        id=item.id, name=item.name, is_active=item.is_active, applicability=applicability
    )


async def get_reference_names(
    session: AsyncSession, kind: ReferenceKind, item_ids: set[int]
) -> dict[int, str]:
    if not item_ids:
        return {}
    model = _REFERENCE_MODELS[kind]
    rows = await session.execute(select(model.id, model.name).where(model.id.in_(item_ids)))
    return {item_id: name for item_id, name in rows.tuples()}


__all__ = [
    "DepartmentInfo",
    "ReferenceItemInfo",
    "ReferenceKind",
    "get_department",
    "get_reference_item",
    "get_reference_names",
]
