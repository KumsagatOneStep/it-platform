from dataclasses import dataclass

from app.core.events import DomainEvent


@dataclass(frozen=True)
class DepartmentHeadChanged(DomainEvent):
    department_id: int
    old_head_id: int | None
    new_head_id: int | None
