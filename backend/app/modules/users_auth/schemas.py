from datetime import datetime
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.schemas import PartialUpdate
from app.modules.users_auth.models import UserRole


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=256)


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    must_change_password: bool


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=1, max_length=256)


class MeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: UserRole
    department_id: int | None
    must_change_password: bool


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: UserRole
    department_id: int | None
    is_active: bool
    must_change_password: bool
    created_at: datetime


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    role: UserRole
    department_id: int | None = None


class UserUpdate(PartialUpdate):
    non_nullable: ClassVar[frozenset[str]] = frozenset({"full_name", "role"})

    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    role: UserRole | None = None
    department_id: int | None = None


class UserCreatedResponse(BaseModel):
    user: UserRead
    temporary_password: str


class TemporaryPasswordResponse(BaseModel):
    temporary_password: str


class UserBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    department_id: int | None
