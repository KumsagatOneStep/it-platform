from dataclasses import dataclass
from typing import Annotated, ClassVar, Generic, Self, TypeVar

from fastapi import Depends, Query
from pydantic import BaseModel, model_validator

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


@dataclass(frozen=True)
class Pagination:
    limit: int
    offset: int


def get_pagination(
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Pagination:
    return Pagination(limit=limit, offset=offset)


PaginationDep = Annotated[Pagination, Depends(get_pagination)]


class PartialUpdate(BaseModel):
    """Тело PATCH-запроса: переданы только изменяемые поля.

    Для полей из non_nullable значение null запрещено.
    """

    non_nullable: ClassVar[frozenset[str]] = frozenset()

    @model_validator(mode="after")
    def _reject_nulls(self) -> Self:
        for field in self.model_fields_set & self.non_nullable:
            if getattr(self, field) is None:
                raise ValueError(f"Поле {field} не может быть пустым")
        return self
