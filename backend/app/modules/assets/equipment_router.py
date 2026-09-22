"""API, общее для техники и расходников: единая выдача и журнал движений — только Admin."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from app.core.db import SessionDep
from app.core.errors import ValidationFailedError
from app.core.schemas import Page, PaginationDep
from app.modules.assets import checkout as checkout_service
from app.modules.assets import journal
from app.modules.assets.equipment_schemas import (
    CheckoutRequest,
    CheckoutResult,
    JournalEntryRead,
)
from app.modules.assets.journal_presenter import journal_to_read
from app.modules.assets.presenter import assets_to_read
from app.modules.assets.stock_presenter import stock_items_to_read
from app.modules.users_auth.service import AdminDep

router = APIRouter(prefix="/equipment", tags=["equipment"])


@router.post("/checkout", response_model=CheckoutResult)
async def checkout(body: CheckoutRequest, session: SessionDep, admin: AdminDep) -> CheckoutResult:
    assets, items = await checkout_service.checkout(session, admin, body)
    return CheckoutResult(
        assets=await assets_to_read(session, assets, admin),
        stock_items=await stock_items_to_read(session, items),
    )


@router.get("/movements", response_model=Page[JournalEntryRead])
async def list_movements(
    session: SessionDep,
    admin: AdminDep,
    pagination: PaginationDep,
    date_from: date | None = None,
    date_to: date | None = None,
    kind: journal.JournalKind | None = None,
    group: Annotated[list[journal.JournalGroup] | None, Query()] = None,
    person_id: int | None = None,
    performed_by: int | None = None,
    location_id: int | None = None,
) -> Page[JournalEntryRead]:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise ValidationFailedError("Начало периода позже его конца", code="date_range_invalid")
    filters = journal.JournalFilters(
        date_from=date_from,
        date_to=date_to,
        kind=kind,
        groups=group,
        person_id=person_id,
        performed_by=performed_by,
        location_id=location_id,
    )
    rows, total = await journal.list_journal(
        session, filters, limit=pagination.limit, offset=pagination.offset
    )
    return Page(
        items=await journal_to_read(session, rows),
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )
