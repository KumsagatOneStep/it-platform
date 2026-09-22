"""API расходников — только Admin (раздел скрыт от Employee и Manager)."""

from typing import Annotated

from fastapi import APIRouter, Body, Query

from app.core.db import SessionDep
from app.core.schemas import Page, PaginationDep
from app.modules.assets import stock_operations, stock_registry
from app.modules.assets.stock_presenter import (
    movements_to_read,
    stock_item_to_read,
    stock_items_to_read,
)
from app.modules.assets.stock_schemas import (
    StockItemCreate,
    StockItemRead,
    StockItemUpdate,
    StockMovementRead,
    StockOperationRequest,
)
from app.modules.users_auth.service import AdminDep

router = APIRouter(prefix="/stock-items", tags=["stock"])


@router.get("", response_model=Page[StockItemRead])
async def list_stock_items(
    session: SessionDep,
    admin: AdminDep,
    pagination: PaginationDep,
    category_id: int | None = None,
    location_id: int | None = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    low_stock: bool = False,
    in_stock: bool = False,
    include_inactive: bool = False,
) -> Page[StockItemRead]:
    filters = stock_registry.StockItemFilters(
        category_id=category_id,
        location_id=location_id,
        q=q,
        low_stock=low_stock,
        in_stock=in_stock,
        include_inactive=include_inactive,
    )
    items, total = await stock_registry.list_stock_items(
        session, filters, limit=pagination.limit, offset=pagination.offset
    )
    return Page(
        items=await stock_items_to_read(session, items),
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )


@router.post("", response_model=StockItemRead, status_code=201)
async def create_stock_item(
    body: StockItemCreate, session: SessionDep, admin: AdminDep
) -> StockItemRead:
    item = await stock_registry.create_stock_item(
        session, actor_id=admin.id, data=body.model_dump()
    )
    return await stock_item_to_read(session, item)


@router.get("/{item_id}", response_model=StockItemRead)
async def get_stock_item(item_id: int, session: SessionDep, admin: AdminDep) -> StockItemRead:
    item = await stock_registry.get_stock_item(session, item_id)
    return await stock_item_to_read(session, item)


@router.patch("/{item_id}", response_model=StockItemRead)
async def update_stock_item(
    item_id: int, body: StockItemUpdate, session: SessionDep, admin: AdminDep
) -> StockItemRead:
    item = await stock_registry.update_stock_item(
        session,
        actor_id=admin.id,
        item_id=item_id,
        version=body.version,
        updates=body.model_dump(exclude_unset=True, exclude={"version"}),
    )
    return await stock_item_to_read(session, item)


@router.post("/{item_id}/operations", response_model=StockItemRead)
async def apply_stock_operation(
    item_id: int,
    body: Annotated[StockOperationRequest, Body()],
    session: SessionDep,
    admin: AdminDep,
) -> StockItemRead:
    item = await stock_operations.apply_stock_operation(session, admin, item_id, body)
    return await stock_item_to_read(session, item)


@router.get("/{item_id}/movements", response_model=Page[StockMovementRead])
async def list_stock_movements(
    item_id: int, session: SessionDep, admin: AdminDep, pagination: PaginationDep
) -> Page[StockMovementRead]:
    movements, total = await stock_registry.list_movements(
        session, item_id, limit=pagination.limit, offset=pagination.offset
    )
    return Page(
        items=await movements_to_read(session, movements),
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )
