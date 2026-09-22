from typing import Annotated

from fastapi import APIRouter, Body, Query

from app.core.db import SessionDep
from app.core.schemas import Page, PaginationDep
from app.modules.assets import operations, registry
from app.modules.assets.access import get_visible_asset
from app.modules.assets.models import AssetStatus
from app.modules.assets.presenter import asset_to_read, assets_to_read, events_to_read
from app.modules.assets.schemas import (
    AssetCreate,
    AssetEventRead,
    AssetOperationRequest,
    AssetRead,
    AssetReturnRequest,
    AssetUpdate,
)
from app.modules.users_auth.service import AdminDep, CurrentUserDep

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("", response_model=Page[AssetRead])
async def list_assets(
    session: SessionDep,
    user: CurrentUserDep,
    pagination: PaginationDep,
    status: Annotated[list[AssetStatus] | None, Query()] = None,
    asset_type_id: int | None = None,
    owner_id: int | None = None,
    location_id: int | None = None,
    needs_review: bool | None = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
) -> Page[AssetRead]:
    filters = registry.AssetFilters(
        statuses=status,
        asset_type_id=asset_type_id,
        owner_id=owner_id,
        location_id=location_id,
        needs_review=needs_review,
        q=q,
    )
    items, total = await registry.list_assets(
        session, user, filters, limit=pagination.limit, offset=pagination.offset
    )
    return Page(
        items=await assets_to_read(session, items, user),
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )


@router.post("", response_model=AssetRead, status_code=201)
async def create_asset(body: AssetCreate, session: SessionDep, admin: AdminDep) -> AssetRead:
    asset = await registry.create_asset(session, actor_id=admin.id, data=body.model_dump())
    return await asset_to_read(session, asset, admin)


@router.get("/{asset_id}", response_model=AssetRead)
async def get_asset(asset_id: int, session: SessionDep, user: CurrentUserDep) -> AssetRead:
    asset = await get_visible_asset(session, user, asset_id)
    return await asset_to_read(session, asset, user)


@router.patch("/{asset_id}", response_model=AssetRead)
async def update_asset(
    asset_id: int, body: AssetUpdate, session: SessionDep, admin: AdminDep
) -> AssetRead:
    updates = body.model_dump(exclude_unset=True, exclude={"version"})
    asset = await registry.update_asset(
        session, admin, asset_id=asset_id, version=body.version, updates=updates
    )
    return await asset_to_read(session, asset, admin)


@router.get("/{asset_id}/events", response_model=Page[AssetEventRead])
async def list_asset_events(
    asset_id: int, session: SessionDep, user: CurrentUserDep, pagination: PaginationDep
) -> Page[AssetEventRead]:
    events, total = await registry.list_events(
        session, user, asset_id, limit=pagination.limit, offset=pagination.offset
    )
    return Page(
        items=await events_to_read(session, events),
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )


@router.post("/return", response_model=list[AssetRead])
async def return_assets(
    body: AssetReturnRequest, session: SessionDep, admin: AdminDep
) -> list[AssetRead]:
    assets = await operations.return_assets(
        session, admin, asset_ids=body.asset_ids, location_id=body.location_id, comment=body.comment
    )
    return await assets_to_read(session, assets, admin)


@router.post("/{asset_id}/operations", response_model=AssetRead)
async def apply_operation(
    asset_id: int,
    body: Annotated[AssetOperationRequest, Body()],
    session: SessionDep,
    admin: AdminDep,
) -> AssetRead:
    asset = await operations.apply_operation(session, admin, asset_id, body)
    return await asset_to_read(session, asset, admin)
