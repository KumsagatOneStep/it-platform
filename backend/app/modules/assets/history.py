"""Запись истории актива: AssetEvent и общий AuditLog."""

from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import diff_values, record_audit
from app.modules.assets.models import Asset, AssetEvent, AssetEventType, AssetStatus

ENTITY_TYPE = "asset"


@dataclass(frozen=True)
class Placement:
    """Статус, владелец и локация актива — то, что меняют операции."""

    status: AssetStatus
    owner_id: int | None
    location_id: int

    @classmethod
    def of(cls, asset: Asset) -> "Placement":
        return cls(status=asset.status, owner_id=asset.owner_id, location_id=asset.location_id)


def jsonable(values: dict[str, Any]) -> dict[str, Any]:
    """Decimal → str: diff_values и JSONB не умеют Decimal."""
    return {
        key: str(value) if isinstance(value, Decimal) else value for key, value in values.items()
    }


def changed_fields(before: dict[str, Any], after: dict[str, Any]) -> dict[str, list[Any]]:
    """Изменившиеся поля в виде {поле: [было, стало]}; сравнение по исходным значениям
    (Decimal("1000") == Decimal("1000.00")), в ответ — JSON-совместимые."""
    keys = [key for key, value in after.items() if before.get(key) != value]
    return diff_values(
        jsonable({key: before.get(key) for key in keys}),
        jsonable({key: after[key] for key in keys}),
    )


def record_event(
    session: AsyncSession,
    asset: Asset,
    *,
    event_type: AssetEventType,
    actor_id: int,
    before: Placement | None,
    operation: str | None = None,
    reason_id: int | None = None,
    changes: dict[str, list[Any]] | None = None,
    comment: str | None = None,
) -> None:
    """Пишет событие и аудит. В событии заполняются только изменившиеся пары «было/стало».

    before=None — создание: «было» пусто, «стало» — текущие статус, владелец и локация.
    """
    after = Placement.of(asset)
    event = AssetEvent(
        asset_id=asset.id,
        event_type=event_type,
        operation=operation,
        reason_id=reason_id,
        changes=changes,
        comment=comment,
        performed_by=actor_id,
    )
    if before is None or before.status != after.status:
        event.from_status = before.status if before else None
        event.to_status = after.status
    if (before.owner_id if before else None) != after.owner_id:
        event.from_owner_id = before.owner_id if before else None
        event.to_owner_id = after.owner_id
    if before is None or before.location_id != after.location_id:
        event.from_location_id = before.location_id if before else None
        event.to_location_id = after.location_id
    session.add(event)

    if changes is not None:
        audit_diff = changes
    else:
        audit_diff = diff_values(asdict(before) if before else {}, asdict(after))
    record_audit(
        session,
        entity_type=ENTITY_TYPE,
        entity_id=asset.id,
        user_id=actor_id,
        action=operation or event_type.value,
        diff=audit_diff,
    )
