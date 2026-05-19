from fastapi import APIRouter, Depends
from typing import List
from app.core.dependencies import require_role, get_db
from app.services.user_service import get_all_users
from app.schemas.user import UserRead
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/users", response_model=List[UserRead])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_role("admin")),
):
    return await get_all_users(db)
