from enum import StrEnum

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Department(Base):
    __tablename__ = "departments"
    __table_args__ = {"schema": "common"}  # noqa: RUF012

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    head_id: Mapped[int | None] = mapped_column(ForeignKey("common.users.id"))


class Location(Base):
    __tablename__ = "locations"
    __table_args__ = {"schema": "common"}  # noqa: RUF012

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class AssetType(Base):
    __tablename__ = "asset_types"
    __table_args__ = {"schema": "common"}  # noqa: RUF012

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class StockCategory(Base):
    __tablename__ = "stock_categories"
    __table_args__ = {"schema": "common"}  # noqa: RUF012

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class IssueReasonApplicability(StrEnum):
    ASSETS = "assets"
    STOCK = "stock"
    BOTH = "both"


class IssueReason(Base):
    __tablename__ = "issue_reasons"
    __table_args__ = {"schema": "common"}  # noqa: RUF012

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    applicability: Mapped[IssueReasonApplicability] = mapped_column(
        SAEnum(
            IssueReasonApplicability,
            native_enum=False,
            length=16,
            values_callable=lambda enum: [member.value for member in enum],
        )
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class TicketType(Base):
    __tablename__ = "ticket_types"
    __table_args__ = {"schema": "common"}  # noqa: RUF012

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=True)
    default_assignee_id: Mapped[int | None] = mapped_column(ForeignKey("common.users.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
