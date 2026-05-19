from pydantic import BaseModel

class RoleRead(BaseModel):
    id: int
    name: str
    description: str | None = None

    class Config:
        from_attributes = True
