from pydantic import BaseModel, EmailStr
from datetime import datetime

class UserBase(BaseModel):
    username: str

class UserLogin(UserBase):
    password: str

class UserRegister(UserLogin):
    email: EmailStr
    password_confirm: str

class UserRead(UserBase):
    id: int
    role: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
