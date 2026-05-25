import os
import uuid
from pathlib import Path
from fastapi import HTTPException, UploadFile
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.models.user import User
from app.models.user_image import UserImage
from app.schemas.user import UserImageCrop

ALLOWED_IMAGE_TYPES = {
    'image/jpeg': 'jpg',
    'image/png': 'png',
    'image/webp': 'webp',
}


def _ensure_upload_dir() -> Path:
    root = Path(settings.PROFILE_IMAGE_UPLOAD_DIR)
    root.mkdir(parents=True, exist_ok=True)
    subdir = root / settings.PROFILE_IMAGE_UPLOAD_SUBDIR
    subdir.mkdir(parents=True, exist_ok=True)
    return root


def _get_user_image_subpath(user_id: int, filename: str) -> str:
    return f"{settings.PROFILE_IMAGE_UPLOAD_SUBDIR}/{user_id}/{filename}"


async def list_user_profile_images(current_user: User, db: AsyncSession) -> list[UserImage]:
    stmt = select(UserImage).where(UserImage.user_id == current_user.id).order_by(UserImage.created_at)
    result = await db.execute(stmt)
    return result.scalars().all()


async def create_user_profile_image(current_user: User, upload_file: UploadFile, db: AsyncSession) -> UserImage:
    if upload_file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported image type. Use JPG, PNG, or WEBP.")

    file_bytes = await upload_file.read()
    max_size = settings.PROFILE_IMAGE_MAX_SIZE_MB * 1024 * 1024
    if len(file_bytes) > max_size:
        raise HTTPException(status_code=400, detail=f"Image must be {settings.PROFILE_IMAGE_MAX_SIZE_MB} MB or smaller.")

    extension = ALLOWED_IMAGE_TYPES[upload_file.content_type]
    filename = f"{uuid.uuid4().hex}.{extension}"
    root_dir = _ensure_upload_dir()
    user_dir = root_dir / settings.PROFILE_IMAGE_UPLOAD_SUBDIR / str(current_user.id)
    user_dir.mkdir(parents=True, exist_ok=True)
    destination = user_dir / filename

    try:
        destination.write_bytes(file_bytes)
    except OSError as exc:
        raise HTTPException(status_code=500, detail="Unable to save profile image.") from exc

    relative_path = _get_user_image_subpath(current_user.id, filename)

    image_record = UserImage(
        user_id=current_user.id,
        file_path=relative_path,
        original_filename=Path(upload_file.filename).name,
        mime_type=upload_file.content_type,
        is_active=False,
    )
    db.add(image_record)
    await db.commit()
    await db.refresh(image_record)
    return image_record


async def update_user_profile_image_crop(current_user: User, image_id: int, crop_data: UserImageCrop, db: AsyncSession) -> UserImage:
    stmt = select(UserImage).where(UserImage.id == image_id, UserImage.user_id == current_user.id)
    result = await db.execute(stmt)
    image_record = result.scalar_one_or_none()
    if image_record is None:
        raise HTTPException(status_code=404, detail="Profile image not found.")

    if crop_data.crop_x < 0 or crop_data.crop_y < 0 or crop_data.crop_size <= 0:
        raise HTTPException(status_code=400, detail="Invalid crop values.")

    if crop_data.original_width <= 0 or crop_data.original_height <= 0:
        raise HTTPException(status_code=400, detail="Original image dimensions are required.")

    if crop_data.crop_x + crop_data.crop_size > crop_data.original_width:
        raise HTTPException(status_code=400, detail="Crop area extends beyond image width.")

    if crop_data.crop_y + crop_data.crop_size > crop_data.original_height:
        raise HTTPException(status_code=400, detail="Crop area extends beyond image height.")

    await db.execute(
        update(UserImage)
        .where(UserImage.user_id == current_user.id, UserImage.is_active == True)
        .values(is_active=False)
    )

    image_record.crop_x = crop_data.crop_x
    image_record.crop_y = crop_data.crop_y
    image_record.crop_size = crop_data.crop_size
    image_record.original_width = crop_data.original_width
    image_record.original_height = crop_data.original_height
    image_record.is_active = True

    await db.commit()
    await db.refresh(image_record)
    return image_record
