from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from app.core.schemas import PartialUpdate
from app.modules.directories.models import IssueReasonApplicability


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


class LocationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    is_active: bool


class LocationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)


class LocationUpdate(PartialUpdate):
    non_nullable: ClassVar[frozenset[str]] = frozenset({"name", "is_active"})

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    is_active: bool | None = None


class NamedItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    is_active: bool


class AssetTypeRead(NamedItemRead):
    pass


class StockCategoryRead(NamedItemRead):
    pass


class AssetTypeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class StockCategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class AssetTypeUpdate(PartialUpdate):
    non_nullable: ClassVar[frozenset[str]] = frozenset({"name", "is_active"})

    name: str | None = Field(default=None, min_length=1, max_length=255)
    is_active: bool | None = None


class StockCategoryUpdate(AssetTypeUpdate):
    pass


class IssueReasonRead(NamedItemRead):
    applicability: IssueReasonApplicability


class IssueReasonCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    applicability: IssueReasonApplicability


class IssueReasonUpdate(PartialUpdate):
    non_nullable: ClassVar[frozenset[str]] = frozenset({"name", "applicability", "is_active"})

    name: str | None = Field(default=None, min_length=1, max_length=255)
    applicability: IssueReasonApplicability | None = None
    is_active: bool | None = None


class TicketTypeRead(NamedItemRead):
    code: str
    requires_approval: bool
    default_assignee_id: int | None


class TicketTypeCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=255)
    requires_approval: bool = True
    default_assignee_id: int | None = None


class TicketTypeUpdate(PartialUpdate):
    non_nullable: ClassVar[frozenset[str]] = frozenset({"name", "requires_approval", "is_active"})

    name: str | None = Field(default=None, min_length=1, max_length=255)
    requires_approval: bool | None = None
    default_assignee_id: int | None = None
    is_active: bool | None = None
