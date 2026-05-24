from pydantic import BaseModel, EmailStr
from datetime import datetime

class UserBase(BaseModel):
    username: str

class UserLogin(UserBase):
    password: str
    device_name: str | None = None

class UserRegister(UserLogin):
    email: EmailStr
    password_confirm: str

class UserRead(UserBase):
    id: int
    email: str | None
    role: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
