from pydantic import BaseModel, EmailStr
from datetime import datetime

class UserBase(BaseModel):
    username: str
    email: EmailStr | None = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserRegister(UserBase):
    password: str
    password_confirm: str

class UserRead(UserBase):
    id: int
    role: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
