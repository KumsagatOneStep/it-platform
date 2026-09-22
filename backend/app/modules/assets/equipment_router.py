"""API, общее для техники и расходников: единая выдача — только Admin."""

from fastapi import APIRouter

from app.core.db import SessionDep
from app.modules.assets import checkout as checkout_service
from app.modules.assets.equipment_schemas import CheckoutRequest, CheckoutResult
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
