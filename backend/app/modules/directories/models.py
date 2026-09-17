from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Department(Base):
    __tablename__ = "departments"
    __table_args__ = {"schema": "common"}  # noqa: RUF012

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    head_id: Mapped[int | None] = mapped_column(ForeignKey("common.users.id"))
