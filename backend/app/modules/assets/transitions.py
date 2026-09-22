"""Таблица переходов статусов актива (п. 4.2.2 ТЗ) — единственный источник правил."""

from dataclasses import dataclass
from enum import StrEnum

from app.modules.assets.models import AssetEventType, AssetStatus


class Operation(StrEnum):
    ISSUE = "issue"
    RETURN = "return"
    RESERVE = "reserve"
    UNRESERVE = "unreserve"
    TO_REPAIR = "to_repair"
    REPAIR_TO_OWNER = "repair_to_owner"
    REPAIR_TO_STOCK = "repair_to_stock"
    WRITE_OFF = "write_off"
    MOVE = "move"


class OwnerRule(StrEnum):
    SET = "set"
    """Владелец берётся из запроса (обязателен)."""
    KEEP = "keep"
    CLEAR = "clear"


@dataclass(frozen=True)
class Transition:
    from_statuses: frozenset[AssetStatus]
    to_status: AssetStatus | None
    """None — статус не меняется (перемещение)."""
    owner: OwnerRule
    event_type: AssetEventType
    requires_owner: bool = False
    """Операция допустима, только если у актива есть владелец."""


_S = AssetStatus
_NOT_WRITTEN_OFF = frozenset(set(AssetStatus) - {AssetStatus.WRITTEN_OFF})

TRANSITIONS: dict[Operation, Transition] = {
    Operation.ISSUE: Transition(
        frozenset({_S.IN_STOCK, _S.RESERVED}), _S.IN_USE, OwnerRule.SET, AssetEventType.ISSUED
    ),
    Operation.RETURN: Transition(
        frozenset({_S.IN_USE}), _S.IN_STOCK, OwnerRule.CLEAR, AssetEventType.RETURNED
    ),
    Operation.RESERVE: Transition(
        frozenset({_S.IN_STOCK}), _S.RESERVED, OwnerRule.KEEP, AssetEventType.STATUS_CHANGED
    ),
    Operation.UNRESERVE: Transition(
        frozenset({_S.RESERVED}), _S.IN_STOCK, OwnerRule.KEEP, AssetEventType.STATUS_CHANGED
    ),
    Operation.TO_REPAIR: Transition(
        frozenset({_S.IN_STOCK, _S.IN_USE, _S.RESERVED}),
        _S.IN_REPAIR,
        OwnerRule.KEEP,
        AssetEventType.STATUS_CHANGED,
    ),
    Operation.REPAIR_TO_OWNER: Transition(
        frozenset({_S.IN_REPAIR}),
        _S.IN_USE,
        OwnerRule.KEEP,
        AssetEventType.STATUS_CHANGED,
        requires_owner=True,
    ),
    Operation.REPAIR_TO_STOCK: Transition(
        frozenset({_S.IN_REPAIR}), _S.IN_STOCK, OwnerRule.CLEAR, AssetEventType.RETURNED
    ),
    Operation.WRITE_OFF: Transition(
        frozenset({_S.IN_STOCK, _S.IN_REPAIR}),
        _S.WRITTEN_OFF,
        OwnerRule.CLEAR,
        AssetEventType.WRITTEN_OFF,
    ),
    Operation.MOVE: Transition(_NOT_WRITTEN_OFF, None, OwnerRule.KEEP, AssetEventType.MOVED),
}


def is_allowed(operation: Operation, status: AssetStatus, owner_id: int | None) -> bool:
    transition = TRANSITIONS[operation]
    if status not in transition.from_statuses:
        return False
    return not (transition.requires_owner and owner_id is None)


def allowed_operations(status: AssetStatus, owner_id: int | None) -> list[Operation]:
    """Операции, допустимые для актива в текущем состоянии, в порядке объявления."""
    return [operation for operation in Operation if is_allowed(operation, status, owner_id)]
