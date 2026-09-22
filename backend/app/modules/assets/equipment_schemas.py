"""Схемы, общие для техники и расходников: единая выдача и журнал движений."""

from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, Field

from app.modules.assets.journal import JournalKind
from app.modules.assets.models import AssetEventType, AssetStatus
from app.modules.assets.schemas import AssetRead, Comment, UnavailableAsset
from app.modules.assets.stock_models import StockMovementType
from app.modules.assets.stock_schemas import Quantity, StockItemRead
from app.modules.assets.transitions import Operation

MAX_CHECKOUT_LINES = 50


class StockLine(BaseModel):
    stock_item_id: int
    quantity: Quantity


class CheckoutRequest(BaseModel):
    recipient_id: int
    asset_ids: Annotated[list[int], Field(max_length=MAX_CHECKOUT_LINES)] = []
    stock_lines: Annotated[list[StockLine], Field(max_length=MAX_CHECKOUT_LINES)] = []
    reason_id: int | None = None
    comment: Comment = None


class CheckoutResult(BaseModel):
    assets: list[AssetRead]
    stock_items: list[StockItemRead]


class UnavailableStockLine(BaseModel):
    """Строка расходников, которую нельзя выдать: позиция не найдена, неактивна или мало остатка."""

    stock_item_id: int
    name: str | None
    requested: int
    available: int | None


class CheckoutUnavailable(BaseModel):
    """details ошибки checkout_unavailable."""

    assets: list[UnavailableAsset]
    stock: list[UnavailableStockLine]


class JournalEntryRead(BaseModel):
    """Строка журнала: событие техники (kind = asset) или движение расходника (kind = stock)."""

    kind: JournalKind
    id: int
    created_at: datetime
    asset_event_type: AssetEventType | None
    asset_operation: Operation | None
    movement_type: StockMovementType | None
    object_id: int
    """id актива или позиции — для ссылки на карточку."""
    object_label: str
    delta: int | None
    quantity_after: int | None
    unit: str | None
    document_date: date | None
    from_owner_id: int | None
    from_owner_name: str | None
    to_owner_id: int | None
    """Новый владелец актива или получатель расходника."""
    to_owner_name: str | None
    from_status: AssetStatus | None
    to_status: AssetStatus | None
    from_location_id: int | None
    from_location_name: str | None
    to_location_id: int | None
    to_location_name: str | None
    reason_id: int | None
    reason_name: str | None
    comment: str | None
    performed_by: int
    performed_by_name: str
