"""Публичные функции service.py, которыми пользуются другие модули."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.directories.models import (
    Department,
    IssueReason,
    IssueReasonApplicability,
    Location,
    StockCategory,
)
from app.modules.directories.service import get_reference_item, get_reference_names
from app.modules.users_auth.service import get_user_names, list_department_user_ids
from tests.factories import make_user


async def test_get_user_names(db_session: AsyncSession) -> None:
    first = await make_user(db_session, full_name="Петров Пётр")
    second = await make_user(db_session, full_name="Сидорова Анна")

    names = await get_user_names(db_session, {first.id, second.id, 999999})

    assert names == {first.id: "Петров Пётр", second.id: "Сидорова Анна"}
    assert await get_user_names(db_session, set()) == {}


async def test_list_department_user_ids_includes_inactive(db_session: AsyncSession) -> None:
    department = Department(name="Бухгалтерия")
    db_session.add(department)
    await db_session.flush()
    active = await make_user(db_session, department_id=department.id)
    inactive = await make_user(db_session, department_id=department.id, is_active=False)
    await make_user(db_session)

    ids = await list_department_user_ids(db_session, department.id)

    assert sorted(ids) == sorted([active.id, inactive.id])


async def test_get_reference_item(db_session: AsyncSession) -> None:
    reason = IssueReason(name="Заправка", applicability=IssueReasonApplicability.STOCK)
    location = Location(name="Склад", is_active=False)
    db_session.add_all([reason, location])
    await db_session.flush()

    reason_info = await get_reference_item(db_session, "issue-reasons", reason.id)
    location_info = await get_reference_item(db_session, "locations", location.id)

    assert reason_info is not None
    assert reason_info.applicability == "stock"
    assert reason_info.is_active is True
    assert location_info is not None
    assert location_info.is_active is False
    assert location_info.applicability is None
    assert await get_reference_item(db_session, "asset-types", 999999) is None


async def test_get_reference_names(db_session: AsyncSession) -> None:
    location = Location(name="Склад")
    db_session.add(location)
    await db_session.flush()

    assert await get_reference_names(db_session, "locations", {location.id}) == {
        location.id: "Склад"
    }


async def test_stock_categories_reference(db_session: AsyncSession) -> None:
    category = StockCategory(name="Картриджи", is_active=False)
    db_session.add(category)
    await db_session.flush()

    info = await get_reference_item(db_session, "stock-categories", category.id)

    assert info is not None
    assert info.is_active is False
    assert await get_reference_names(db_session, "stock-categories", {category.id}) == {
        category.id: "Картриджи"
    }
