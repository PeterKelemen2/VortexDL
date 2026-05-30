from typing import Annotated
from pydantic import BaseModel, EmailStr, ConfigDict, Field
from datetime import datetime

# Strict types used at registration and password-change time only
Username = Annotated[str, Field(min_length=3, max_length=64, pattern=r'^[a-zA-Z0-9_-]+$')]
Password = Annotated[str, Field(min_length=12, max_length=128)]


class UserBase(BaseModel):
    # Login accepts whatever the user typed — no format enforcement here.
    username: str = Field(min_length=1, max_length=255)


class UserLogin(UserBase):
    # No min-length on password at login; the hash check handles wrong passwords.
    password: str = Field(min_length=1, max_length=128)
    # Optional TOTP code or backup code when the account has 2FA enabled.
    totp_code: str | None = Field(None, max_length=32)
    device_name: str | None = Field(None, max_length=255)
    user_agent: str | None = Field(None, max_length=512)


class UserRegister(BaseModel):
    # Registration enforces strict username/password rules independently of UserLogin.
    username: Username
    password: Password
    password_confirm: str = Field(min_length=1, max_length=128)
    email: EmailStr
    device_name: str | None = Field(None, max_length=255)
    user_agent: str | None = Field(None, max_length=512)


class UserImageRead(BaseModel):
    id: int
    url: str
    file_path: str
    avatar_url: str | None = None
    thumbnail_url: str | None = None
    preview_url: str | None = None
    original_filename: str
    mime_type: str
    original_width: int | None
    original_height: int | None
    crop_x: float | None
    crop_y: float | None
    crop_size: float | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserRead(UserBase):
    id: int
    email: str | None
    role: str
    created_at: datetime
    updated_at: datetime
    profile_image: UserImageRead | None = None

    model_config = ConfigDict(from_attributes=True)


class UserListResponse(BaseModel):
    items: list[UserRead]
    page: int
    page_size: int
    total: int
    total_pages: int


class UserUpdate(BaseModel):
    username: Username | None = None
    current_password: str | None = Field(None, max_length=128)
    new_password: Password | None = None
    new_password_confirm: str | None = Field(None, max_length=128)


class UserImageCrop(BaseModel):
    crop_x: float = Field(ge=0)
    crop_y: float = Field(ge=0)
    crop_size: float = Field(gt=0)
    original_width: int = Field(gt=0)
    original_height: int = Field(gt=0)


class UserAdminUpdate(BaseModel):
    username: Username | None = None
    role: str | None = Field(None, max_length=64)
    new_password: Password | None = None
    new_password_confirm: str | None = Field(None, max_length=128)
    confirm_email: EmailStr


class UserAdminDelete(BaseModel):
    confirm_email: EmailStr
