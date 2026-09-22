from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.assets.models import Asset, AssetStatus
from app.modules.users_auth.models import User
from tests.factories import make_user
from tests.modules.assets.conftest import Refs, make_asset


def _error_code(response: Any) -> str:
    code: str = response.json()["error"]["code"]
    return code


async def test_deactivation_blocked_by_owned_assets(
    client: AsyncClient, admin_headers: dict[str, str], refs: Refs, db_session: AsyncSession
) -> None:
    owner = await make_user(db_session)
    in_use = await make_asset(
        db_session, refs, inventory_number="INV-1", status=AssetStatus.IN_USE, owner_id=owner.id
    )
    await make_asset(
        db_session, refs, inventory_number="INV-2", status=AssetStatus.IN_REPAIR, owner_id=owner.id
    )

    blocked = await client.post(f"/api/admin/users/{owner.id}/deactivate", headers=admin_headers)

    assert blocked.status_code == 409
    assert _error_code(blocked) == "deactivation_blocked"
    details = blocked.json()["error"]["details"]
    assert [item["kind"] for item in details] == ["asset_owner", "asset_owner"]
    assert details[0] == {
        "kind": "asset_owner",
        "entity_id": in_use.id,
        "title": "Техника INV-1 — Lenovo ThinkPad T14",
    }


async def test_user_without_assets_can_be_deactivated(
    client: AsyncClient, admin_headers: dict[str, str], refs: Refs, db_session: AsyncSession
) -> None:
    user: User = await make_user(db_session)
    asset: Asset = await make_asset(db_session, refs, inventory_number="INV-1")
    assert asset.owner_id is None

    response = await client.post(f"/api/admin/users/{user.id}/deactivate", headers=admin_headers)

    assert response.status_code == 200
