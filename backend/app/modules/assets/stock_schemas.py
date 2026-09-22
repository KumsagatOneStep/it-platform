import uuid
from datetime import date, datetime
from typing import Annotated, ClassVar, Literal

from pydantic import BaseModel, Field

from app.core.schemas import PartialUpdate
from app.modules.assets.schemas import Comment
from app.modules.assets.stock_models import StockMovementType

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


Quantity = Annotated[int, Field(ge=1, le=1_000_000)]


class StockReceiptOperation(BaseModel):
    operation: Literal["receipt"]
    quantity: Quantity
    document_date: date | None = None
    """Дата по накладной; не задана — сегодня в часовом поясе компании."""
    comment: Comment = None


class StockWriteOffOperation(BaseModel):
    operation: Literal["write_off"]
    quantity: Quantity
    reason_id: int | None = None
    """Обязательна; проверяется сервисом, чтобы вернуть код reason_required."""
    comment: Comment = None


class StockAdjustmentOperation(BaseModel):
    operation: Literal["adjustment"]
    actual_quantity: Annotated[int, Field(ge=0, le=1_000_000)]
    """Фактический остаток по итогам пересчёта; изменение вычисляет сервер."""
    comment: Comment = None
    """Обязателен; проверяется сервисом, чтобы вернуть код comment_required."""


class StockTransferOperation(BaseModel):
    operation: Literal["transfer"]
    quantity: Quantity
    to_location_id: int
    comment: Comment = None


StockOperationRequest = Annotated[
    StockReceiptOperation
    | StockWriteOffOperation
    | StockAdjustmentOperation
    | StockTransferOperation,
    Field(discriminator="operation"),
]


class StockMovementRead(BaseModel):
    id: int
    stock_item_id: int
    movement_type: StockMovementType
    delta: int
    quantity_after: int
    document_date: date | None
    transfer_id: uuid.UUID | None
    counterpart_location_id: int | None
    """Для перемещения: склад-получатель у transfer_out, склад-источник у transfer_in."""
    counterpart_location_name: str | None
    reason_id: int | None
    reason_name: str | None
    recipient_id: int | None
    recipient_name: str | None
    comment: str | None
    performed_by: int
    performed_by_name: str
    created_at: datetime
