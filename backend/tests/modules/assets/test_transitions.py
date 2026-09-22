"""Таблица переходов против п. 4.2.2 ТЗ: все пары «статус × операция»."""

import pytest

from app.modules.assets.models import AssetStatus as S
from app.modules.assets.transitions import TRANSITIONS, Operation, OwnerRule, allowed_operations

# Ожидания выписаны из ТЗ независимо от реализации.
EXPECTED_FROM: dict[Operation, set[S]] = {
    Operation.ISSUE: {S.IN_STOCK, S.RESERVED},
    Operation.RETURN: {S.IN_USE},
    Operation.RESERVE: {S.IN_STOCK},
    Operation.UNRESERVE: {S.RESERVED},
    Operation.TO_REPAIR: {S.IN_STOCK, S.IN_USE, S.RESERVED},
    Operation.REPAIR_TO_OWNER: {S.IN_REPAIR},
    Operation.REPAIR_TO_STOCK: {S.IN_REPAIR},
    Operation.WRITE_OFF: {S.IN_STOCK, S.IN_REPAIR},
    Operation.MOVE: {S.IN_STOCK, S.RESERVED, S.IN_USE, S.IN_REPAIR},
}
EXPECTED_TO: dict[Operation, S | None] = {
    Operation.ISSUE: S.IN_USE,
    Operation.RETURN: S.IN_STOCK,
    Operation.RESERVE: S.RESERVED,
    Operation.UNRESERVE: S.IN_STOCK,
    Operation.TO_REPAIR: S.IN_REPAIR,
    Operation.REPAIR_TO_OWNER: S.IN_USE,
    Operation.REPAIR_TO_STOCK: S.IN_STOCK,
    Operation.WRITE_OFF: S.WRITTEN_OFF,
    Operation.MOVE: None,
}
EXPECTED_OWNER: dict[Operation, OwnerRule] = {
    Operation.ISSUE: OwnerRule.SET,
    Operation.RETURN: OwnerRule.CLEAR,
    Operation.RESERVE: OwnerRule.KEEP,
    Operation.UNRESERVE: OwnerRule.KEEP,
    Operation.TO_REPAIR: OwnerRule.KEEP,
    Operation.REPAIR_TO_OWNER: OwnerRule.KEEP,
    Operation.REPAIR_TO_STOCK: OwnerRule.CLEAR,
    Operation.WRITE_OFF: OwnerRule.CLEAR,
    Operation.MOVE: OwnerRule.KEEP,
}


@pytest.mark.parametrize("status", list(S))
@pytest.mark.parametrize("operation", list(Operation))
def test_operation_allowed_only_from_statuses_in_spec(operation: Operation, status: S) -> None:
    owner_id = 7 if status in {S.IN_USE, S.IN_REPAIR} else None

    allowed = operation in allowed_operations(status, owner_id)

    assert allowed == (status in EXPECTED_FROM[operation])


@pytest.mark.parametrize("operation", list(Operation))
def test_target_status_and_owner_rule(operation: Operation) -> None:
    assert TRANSITIONS[operation].to_status == EXPECTED_TO[operation]
    assert TRANSITIONS[operation].owner == EXPECTED_OWNER[operation]


def test_repair_to_owner_requires_owner() -> None:
    assert Operation.REPAIR_TO_OWNER in allowed_operations(S.IN_REPAIR, owner_id=7)
    assert Operation.REPAIR_TO_OWNER not in allowed_operations(S.IN_REPAIR, owner_id=None)


def test_written_off_is_final() -> None:
    assert allowed_operations(S.WRITTEN_OFF, owner_id=None) == []
