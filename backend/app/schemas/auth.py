from pydantic import BaseModel, ConfigDict
from datetime import datetime

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
