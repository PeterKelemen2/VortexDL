from typing import Any
from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime

class UserBase(BaseModel):
    username: str

class UserLogin(UserBase):
    password: str
    device_name: str | None = None
    user_agent: str | None = None

class UserRegister(UserLogin):
    email: EmailStr
    password_confirm: str

class UserRead(UserBase):
    id: int
    email: str | None
    role: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserListResponse(BaseModel):
    items: list[UserRead]
    page: int
    page_size: int
    total: int
    total_pages: int


class UserUpdate(BaseModel):
    username: str | None = None
    current_password: str | None = None
    new_password: str | None = None
    new_password_confirm: str | None = None


class UserAdminUpdate(BaseModel):
    username: str | None = None
    role: str | None = None
    new_password: str | None = None
    new_password_confirm: str | None = None
    confirm_email: EmailStr


class UserAdminDelete(BaseModel):
    confirm_email: EmailStr
