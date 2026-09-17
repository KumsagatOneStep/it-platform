from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from app.core.schemas import PartialUpdate


class DepartmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    head_id: int | None


class DepartmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    head_id: int | None = None


class DepartmentUpdate(PartialUpdate):
    non_nullable: ClassVar[frozenset[str]] = frozenset({"name"})

    name: str | None = Field(default=None, min_length=1, max_length=255)
    head_id: int | None = None
