from pydantic import BaseModel
from datetime import datetime

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenRefreshRequest(BaseModel):
    refresh_token: str

class RefreshTokenSession(BaseModel):
    id: int
    device_os: str | None
    device_name: str | None
    user_agent: str | None
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime

    class Config:
        from_attributes = True
