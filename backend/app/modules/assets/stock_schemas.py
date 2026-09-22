from datetime import datetime
from typing import Annotated, ClassVar

from pydantic import BaseModel, Field

from app.core.schemas import PartialUpdate

StockName = Annotated[str, Field(min_length=1, max_length=200)]
Unit = Annotated[str, Field(min_length=1, max_length=20)]
MinQuantity = Annotated[int, Field(ge=0, le=1_000_000)]


class StockItemCreate(BaseModel):
    name: StockName
    stock_category_id: int
    unit: Unit
    location_id: int
    min_quantity: MinQuantity = 0


class StockItemUpdate(PartialUpdate):
    """Склад не меняется правкой — только перемещением количества."""

    non_nullable: ClassVar[frozenset[str]] = frozenset(
        {"name", "stock_category_id", "unit", "min_quantity", "is_active"}
    )

    version: int
    name: StockName | None = None
    stock_category_id: int | None = None
    unit: Unit | None = None
    min_quantity: MinQuantity | None = None
    is_active: bool | None = None


class StockItemRead(BaseModel):
    id: int
    name: str
    stock_category_id: int
    category_name: str
    unit: str
    location_id: int
    location_name: str
    quantity: int
    min_quantity: int
    is_low: bool
    is_active: bool
    version: int
    created_at: datetime
    updated_at: datetime
