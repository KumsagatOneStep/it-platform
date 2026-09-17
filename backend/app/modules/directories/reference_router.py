from typing import Any

from fastapi import APIRouter

from app.core.db import SessionDep
from app.modules.directories import reference
from app.modules.directories.reference import ReferenceSpec
from app.modules.users_auth.service import AdminDep, CurrentUserDep, UserRole


def build_reference_routers(spec: ReferenceSpec) -> list[APIRouter]:
    read_schema = spec.read_schema
    create_schema = spec.create_schema
    update_schema = spec.update_schema
    operation = spec.slug.replace("-", "_")

    public = APIRouter(prefix=f"/directories/{spec.slug}", tags=["directories"])
    admin = APIRouter(prefix=f"/admin/directories/{spec.slug}", tags=["admin: directories"])

    @public.get(
        "",
        response_model=list[read_schema],  # type: ignore[valid-type]
        operation_id=f"list_{operation}",
    )
    async def list_items(
        session: SessionDep, user: CurrentUserDep, include_inactive: bool = False
    ) -> Any:
        return await reference.list_items(
            session, spec, include_inactive=include_inactive and user.role == UserRole.ADMIN
        )

    @admin.post("", response_model=read_schema, status_code=201, operation_id=f"create_{operation}")
    async def create_item(
        body: create_schema,  # type: ignore[valid-type]
        session: SessionDep,
        admin_user: AdminDep,
    ) -> Any:
        return await reference.create_item(
            session,
            spec,
            actor_id=admin_user.id,
            data=body.model_dump(),  # type: ignore[attr-defined]
        )

    @admin.patch("/{item_id}", response_model=read_schema, operation_id=f"update_{operation}")
    async def update_item(
        item_id: int,
        body: update_schema,  # type: ignore[valid-type]
        session: SessionDep,
        admin_user: AdminDep,
    ) -> Any:
        return await reference.update_item(
            session,
            spec,
            actor_id=admin_user.id,
            item_id=item_id,
            updates=body.model_dump(exclude_unset=True),  # type: ignore[attr-defined]
        )

    return [public, admin]
