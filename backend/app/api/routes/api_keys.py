from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.api_key import (
    ApiKeyCreate,
    ApiKeyCreateResponse,
    ApiKeyRead,
)
from app.services import api_key_service

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.post("", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_key(
    data: ApiKeyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiKeyCreateResponse:
    """Create a new API key. The plaintext key is returned only once."""
    api_key, plaintext = await api_key_service.create_api_key(data, current_user.id, db)
    return ApiKeyCreateResponse.model_validate(
        {**ApiKeyRead.model_validate(api_key).model_dump(), "key": plaintext}
    )


@router.get("", response_model=list[ApiKeyRead])
async def list_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ApiKeyRead]:
    keys = await api_key_service.list_api_keys(current_user.id, db)
    return [ApiKeyRead.model_validate(k) for k in keys]


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await api_key_service.revoke_api_key(key_id, current_user.id, db)
