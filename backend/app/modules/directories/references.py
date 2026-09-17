from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ValidationFailedError
from app.modules.directories import schemas
from app.modules.directories.models import (
    AssetType,
    IssueReason,
    Location,
    StockCategory,
    TicketType,
)
from app.modules.directories.reference import ReferenceSpec
from app.modules.users_auth.service import UserRole, get_user_info

_ASSIGNEE_ROLES = frozenset({UserRole.MANAGER, UserRole.ADMIN})


async def validate_ticket_type(session: AsyncSession, data: dict[str, Any]) -> None:
    assignee_id = data.get("default_assignee_id")
    if assignee_id is None:
        return
    info = await get_user_info(session, assignee_id)
    if info is None or not info.is_active or info.role not in _ASSIGNEE_ROLES:
        raise ValidationFailedError(
            "Исполнителем по умолчанию может быть только активный Manager или Admin",
            code="invalid_default_assignee",
        )


REFERENCE_SPECS: tuple[ReferenceSpec, ...] = (
    ReferenceSpec(
        slug="locations",
        model=Location,
        read_schema=schemas.LocationRead,
        create_schema=schemas.LocationCreate,
        update_schema=schemas.LocationUpdate,
        entity_type="location",
    ),
    ReferenceSpec(
        slug="asset-types",
        model=AssetType,
        read_schema=schemas.AssetTypeRead,
        create_schema=schemas.AssetTypeCreate,
        update_schema=schemas.AssetTypeUpdate,
        entity_type="asset_type",
    ),
    ReferenceSpec(
        slug="stock-categories",
        model=StockCategory,
        read_schema=schemas.StockCategoryRead,
        create_schema=schemas.StockCategoryCreate,
        update_schema=schemas.StockCategoryUpdate,
        entity_type="stock_category",
    ),
    ReferenceSpec(
        slug="issue-reasons",
        model=IssueReason,
        read_schema=schemas.IssueReasonRead,
        create_schema=schemas.IssueReasonCreate,
        update_schema=schemas.IssueReasonUpdate,
        entity_type="issue_reason",
    ),
    ReferenceSpec(
        slug="ticket-types",
        model=TicketType,
        read_schema=schemas.TicketTypeRead,
        create_schema=schemas.TicketTypeCreate,
        update_schema=schemas.TicketTypeUpdate,
        entity_type="ticket_type",
        validate=validate_ticket_type,
        text_fields=("code", "name"),
    ),
)
