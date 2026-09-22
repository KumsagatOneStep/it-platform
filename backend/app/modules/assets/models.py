from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class AssetStatus(StrEnum):
    IN_STOCK = "in_stock"
    RESERVED = "reserved"
    IN_USE = "in_use"
    IN_REPAIR = "in_repair"
    WRITTEN_OFF = "written_off"


class AssetEventType(StrEnum):
    CREATED = "created"
    ISSUED = "issued"
    RETURNED = "returned"
    STATUS_CHANGED = "status_changed"
    MOVED = "moved"
    EDITED = "edited"
    WRITTEN_OFF = "written_off"


def _enum_column(enum: type[StrEnum]) -> SAEnum:
    # create_constraint=False: CHECK ck_assets_status / ck_asset_events_event_type создаются
    # миграцией 0005 вручную, как ck_users_role в users_auth (миграция 0002).
    return SAEnum(
        enum,
        native_enum=False,
        create_constraint=False,
        length=16,
        values_callable=lambda members: [member.value for member in members],
    )


class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (
        CheckConstraint("status <> 'in_use' OR owner_id IS NOT NULL", name="in_use_has_owner"),
        CheckConstraint(
            "status NOT IN ('in_stock', 'reserved', 'written_off') OR owner_id IS NULL",
            name="stock_has_no_owner",
        ),
        CheckConstraint("initial_cost IS NULL OR initial_cost >= 0", name="initial_cost"),
        Index(
            "uq_assets_serial_number",
            "serial_number",
            unique=True,
            postgresql_where="serial_number IS NOT NULL",
        ),
        {"schema": "equipment"},
    )
    __mapper_args__ = {"eager_defaults": True}  # noqa: RUF012

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    asset_type_id: Mapped[int] = mapped_column(ForeignKey("common.asset_types.id"), index=True)
    inventory_number: Mapped[str] = mapped_column(String(64), unique=True)
    serial_number: Mapped[str | None] = mapped_column(String(128))
    model: Mapped[str] = mapped_column(String(200))
    status: Mapped[AssetStatus] = mapped_column(_enum_column(AssetStatus), index=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("common.locations.id"), index=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("common.users.id"), index=True)
    accepted_at: Mapped[date] = mapped_column(Date)
    purchased_at: Mapped[date | None] = mapped_column(Date)
    warranty_until: Mapped[date | None] = mapped_column(Date)
    initial_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AssetEvent(Base):
    __tablename__ = "asset_events"
    __table_args__ = (
        Index("ix_asset_events_asset_id_id", "asset_id", "id"),
        {"schema": "equipment"},
    )
    __mapper_args__ = {"eager_defaults": True}  # noqa: RUF012

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("equipment.assets.id"))
    event_type: Mapped[AssetEventType] = mapped_column(_enum_column(AssetEventType))
    operation: Mapped[str | None] = mapped_column(String(32))
    from_owner_id: Mapped[int | None] = mapped_column(ForeignKey("common.users.id"))
    to_owner_id: Mapped[int | None] = mapped_column(ForeignKey("common.users.id"))
    from_status: Mapped[AssetStatus | None] = mapped_column(_enum_column(AssetStatus))
    to_status: Mapped[AssetStatus | None] = mapped_column(_enum_column(AssetStatus))
    from_location_id: Mapped[int | None] = mapped_column(ForeignKey("common.locations.id"))
    to_location_id: Mapped[int | None] = mapped_column(ForeignKey("common.locations.id"))
    reason_id: Mapped[int | None] = mapped_column(ForeignKey("common.issue_reasons.id"))
    changes: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    comment: Mapped[str | None] = mapped_column(Text)
    performed_by: Mapped[int] = mapped_column(ForeignKey("common.users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
