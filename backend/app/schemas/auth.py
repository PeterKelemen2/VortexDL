from pydantic import BaseModel, ConfigDict, EmailStr, Field
from datetime import datetime
from typing import Annotated

# Strict password type reused from the registration flow.
Password = Annotated[str, Field(min_length=12, max_length=128)]

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"

class TokenRefreshRequest(BaseModel):
    refresh_token: str | None = None

class RefreshTokenSession(BaseModel):
    id: int
    resolved_name: str | None
    device_name: str | None
    user_agent: str | None
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime
    current: bool = False

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    msg: str


class EmailVerificationRequest(BaseModel):
    email: EmailStr


class EmailVerificationConfirm(BaseModel):
    token: str = Field(min_length=1, max_length=512)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=1, max_length=512)
    new_password: Password
    new_password_confirm: str = Field(min_length=1, max_length=128)


# --- Two-factor authentication ---------------------------------------------
class TwoFactorSetupResponse(BaseModel):
    secret: str
    otpauth_uri: str
    qr_code: str  # data:image/png;base64,... URI
    backup_codes: list[str]


class TwoFactorVerifyRequest(BaseModel):
    code: str = Field(min_length=1, max_length=32)


class TwoFactorDisableRequest(BaseModel):
    password: str = Field(min_length=1, max_length=128)


class TwoFactorStatusResponse(BaseModel):
    enabled: bool


class BackupCodesResponse(BaseModel):
    backup_codes: list[str]
