"""Схемы операций, общих для техники и расходников: единая выдача."""

from typing import Annotated

from pydantic import BaseModel, Field

from app.modules.assets.schemas import AssetRead, Comment, UnavailableAsset
from app.modules.assets.stock_schemas import Quantity, StockItemRead

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
