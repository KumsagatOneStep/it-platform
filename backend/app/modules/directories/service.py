"""Публичный интерфейс модуля directories.

Другие модули импортируют только этот файл и events.py.
"""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.directories.models import Department


@dataclass(frozen=True)
class DepartmentInfo:
    id: int
    name: str
    head_id: int | None


async def get_department(session: AsyncSession, department_id: int) -> DepartmentInfo | None:
    department = await session.get(Department, department_id)
    if department is None:
        return None
    return DepartmentInfo(id=department.id, name=department.name, head_id=department.head_id)


__all__ = ["DepartmentInfo", "get_department"]
