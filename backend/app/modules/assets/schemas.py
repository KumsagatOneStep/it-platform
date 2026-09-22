from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any, ClassVar, Literal

from pydantic import AfterValidator, BaseModel, Field

from app.core.schemas import PartialUpdate
from app.modules.assets.models import AssetEventType, AssetStatus
from app.modules.assets.transitions import Operation


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip() or None


Comment = Annotated[str | None, Field(max_length=1000), AfterValidator(_blank_to_none)]
SerialNumber = Annotated[str | None, Field(max_length=128), AfterValidator(_blank_to_none)]
InventoryNumber = Annotated[str, Field(min_length=1, max_length=64)]
Model = Annotated[str, Field(min_length=1, max_length=200)]
Cost = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]
AssetIds = Annotated[list[int], Field(min_length=1, max_length=50)]


class AssetCreate(BaseModel):
    asset_type_id: int
    inventory_number: InventoryNumber
    serial_number: SerialNumber = None
    model: Model
    location_id: int
    accepted_at: date
    purchased_at: date | None = None
    warranty_until: date | None = None
    initial_cost: Cost | None = None
    needs_review: bool = False


class AssetUpdate(PartialUpdate):
    non_nullable: ClassVar[frozenset[str]] = frozenset(
        {"asset_type_id", "inventory_number", "model", "accepted_at", "needs_review"}
    )

    version: int
    asset_type_id: int | None = None
    inventory_number: InventoryNumber | None = None
    serial_number: SerialNumber = None
    model: Model | None = None
    accepted_at: date | None = None
    purchased_at: date | None = None
    warranty_until: date | None = None
    initial_cost: Cost | None = None
    needs_review: bool | None = None


class AssetRead(BaseModel):
    id: int
    asset_type_id: int
    asset_type_name: str
    inventory_number: str
    serial_number: str | None
    model: str
    status: AssetStatus
    location_id: int
    location_name: str
    owner_id: int | None
    owner_name: str | None
    accepted_at: date
    purchased_at: date | None
    warranty_until: date | None
    initial_cost: Decimal | None
    needs_review: bool
    version: int
    created_at: datetime
    updated_at: datetime
    allowed_operations: list[Operation]


class AssetEventRead(BaseModel):
    id: int
    event_type: AssetEventType
    operation: Operation | None
    from_owner_id: int | None
    from_owner_name: str | None
    to_owner_id: int | None
    to_owner_name: str | None
    from_status: AssetStatus | None
    to_status: AssetStatus | None
    from_location_id: int | None
    from_location_name: str | None
    to_location_id: int | None
    to_location_name: str | None
    reason_id: int | None
    reason_name: str | None
    changes: dict[str, Any] | None
    comment: str | None
    performed_by: int
    performed_by_name: str
    created_at: datetime


class IssueOperation(BaseModel):
    operation: Literal[Operation.ISSUE]
    owner_id: int
    reason_id: int | None = None
    comment: Comment = None


class ReturnOperation(BaseModel):
    """Возврат на склад: из работы или из ремонта."""

    operation: Literal[Operation.RETURN, Operation.REPAIR_TO_STOCK]
    location_id: int | None = None
    comment: Comment = None


class StatusOperation(BaseModel):
    """Операции без дополнительных полей."""

    operation: Literal[
        Operation.RESERVE, Operation.UNRESERVE, Operation.TO_REPAIR, Operation.REPAIR_TO_OWNER
    ]
    comment: Comment = None


class WriteOffOperation(BaseModel):
    operation: Literal[Operation.WRITE_OFF]
    reason_id: int | None = None
    """Обязательна; проверяется сервисом, чтобы вернуть код reason_required."""
    comment: Comment = None


class MoveOperation(BaseModel):
    operation: Literal[Operation.MOVE]
    location_id: int
    comment: Comment = None


AssetOperationRequest = Annotated[
    IssueOperation | ReturnOperation | StatusOperation | WriteOffOperation | MoveOperation,
    Field(discriminator="operation"),
]


class AssetReturnRequest(BaseModel):
    asset_ids: AssetIds
    location_id: int | None = None
    comment: Comment = None


class UnavailableAsset(BaseModel):
    """Элемент details ошибок assets_unavailable и checkout_unavailable."""

    asset_id: int
    inventory_number: str | None
    status: AssetStatus | None
