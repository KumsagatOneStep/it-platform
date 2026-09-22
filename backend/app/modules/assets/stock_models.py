"""Расходники: позиции на складах и движения остатков (п. 2 спецификации 2b)."""

import uuid
from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class StockMovementType(StrEnum):
    RECEIPT = "receipt"
    ISSUE = "issue"
    WRITE_OFF = "write_off"
    ADJUSTMENT = "adjustment"
    TRANSFER_OUT = "transfer_out"
    TRANSFER_IN = "transfer_in"


class StockItem(Base):
    __tablename__ = "stock_items"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="quantity"),
        CheckConstraint("min_quantity >= 0", name="min_quantity"),
        CheckConstraint("is_active OR quantity = 0", name="inactive_is_empty"),
        {"schema": "equipment"},
    )
    __mapper_args__ = {"eager_defaults": True}  # noqa: RUF012

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    stock_category_id: Mapped[int] = mapped_column(
        ForeignKey("common.stock_categories.id"), index=True
    )
    unit: Mapped[str] = mapped_column(String(20))
    location_id: Mapped[int] = mapped_column(ForeignKey("common.locations.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    min_quantity: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# Уникальность наименования на складе без учёта регистра; по этой паре перемещение
# находит позицию на складе-получателе.
Index(
    "uq_stock_items_name_location",
    func.lower(StockItem.name),
    StockItem.location_id,
    unique=True,
)


class StockMovement(Base):
    __tablename__ = "stock_movements"
    __table_args__ = (
        CheckConstraint("delta <> 0", name="delta_not_zero"),
        CheckConstraint("quantity_after >= 0", name="quantity_after"),
        CheckConstraint(
            "movement_type NOT IN ('receipt', 'transfer_in') OR delta > 0", name="incoming_sign"
        ),
        CheckConstraint(
            "movement_type NOT IN ('issue', 'write_off', 'transfer_out') OR delta < 0",
            name="outgoing_sign",
        ),
        CheckConstraint(
            "(movement_type = 'receipt') = (document_date IS NOT NULL)", name="document_date"
        ),
        CheckConstraint(
            "(movement_type IN ('transfer_out', 'transfer_in')) = (transfer_id IS NOT NULL)",
            name="transfer_id",
        ),
        CheckConstraint("(movement_type = 'issue') = (recipient_id IS NOT NULL)", name="recipient"),
        CheckConstraint(
            "movement_type <> 'adjustment' OR comment IS NOT NULL", name="adjustment_comment"
        ),
        Index("ix_stock_movements_stock_item_id_id", "stock_item_id", "id"),
        {"schema": "equipment"},
    )
    __mapper_args__ = {"eager_defaults": True}  # noqa: RUF012

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    stock_item_id: Mapped[int] = mapped_column(ForeignKey("equipment.stock_items.id"))
    movement_type: Mapped[StockMovementType] = mapped_column(
        # CHECK ck_stock_movements_movement_type создаётся миграцией 0006 вручную, как в 0005.
        SAEnum(
            StockMovementType,
            native_enum=False,
            create_constraint=False,
            length=16,
            values_callable=lambda members: [member.value for member in members],
        )
    )
    delta: Mapped[int] = mapped_column(Integer)
    quantity_after: Mapped[int] = mapped_column(Integer)
    document_date: Mapped[date | None] = mapped_column(Date)
    transfer_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True)
    reason_id: Mapped[int | None] = mapped_column(ForeignKey("common.issue_reasons.id"))
    recipient_id: Mapped[int | None] = mapped_column(ForeignKey("common.users.id"))
    comment: Mapped[str | None] = mapped_column(Text)
    performed_by: Mapped[int] = mapped_column(ForeignKey("common.users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
