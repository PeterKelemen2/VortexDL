import uuid
from pathlib import Path
from fastapi import HTTPException, UploadFile
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from PIL import Image, ImageOps
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


def _get_variant_subpath(relative_path: str, variant: str) -> str:
    original = Path(relative_path)
    suffix = f"{settings.PROFILE_IMAGE_VARIANT_SEPARATOR}{variant}"
    return str(original.with_name(f"{original.stem}{suffix}{original.suffix}"))


def _get_user_image_upload_dir(current_user: User) -> Path:
    root = Path(settings.PROFILE_IMAGE_UPLOAD_DIR) / settings.PROFILE_IMAGE_UPLOAD_SUBDIR / str(current_user.id)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _variant_output_path(original_path: Path, variant: str) -> Path:
    return original_path.with_name(f"{original_path.stem}{settings.PROFILE_IMAGE_VARIANT_SEPARATOR}{variant}{original_path.suffix}")


def _generate_image_variant(original_path: Path, variant: str, crop_data: UserImageCrop | None = None) -> Path:
    variant_path = _variant_output_path(original_path, variant)
    variant_size = settings.PROFILE_IMAGE_VARIANT_SIZES.get(variant)
    if variant_size is None:
        raise ValueError(f"Unknown profile image variant: {variant}")

    if variant_path.exists() and crop_data is None:
        return variant_path

    if variant_path.exists() and crop_data is not None:
        variant_path.unlink(missing_ok=True)

    try:
        with Image.open(original_path) as raw_image:
            image = ImageOps.exif_transpose(raw_image)
            original_format = raw_image.format or original_path.suffix.lstrip('.').upper()

            if crop_data is not None:
                crop_box = (
                    int(crop_data.crop_x),
                    int(crop_data.crop_y),
                    int(crop_data.crop_x + crop_data.crop_size),
                    int(crop_data.crop_y + crop_data.crop_size),
                )
                image = image.crop(crop_box)
                image = image.resize((variant_size, variant_size), Image.LANCZOS)
            else:
                image = ImageOps.fit(image, (variant_size, variant_size), Image.LANCZOS, centering=(0.5, 0.5))

            save_kwargs = {}
            if original_format in {'JPEG', 'JPG'}:
                save_kwargs['quality'] = settings.PROFILE_IMAGE_VARIANT_QUALITY
                save_kwargs['optimize'] = True
            variant_path.parent.mkdir(parents=True, exist_ok=True)
            image.save(variant_path, format=original_format, **save_kwargs)
    except OSError as exc:
        raise HTTPException(status_code=500, detail="Failed to generate image variants.") from exc

    return variant_path


def _generate_profile_image_variants(original_path: Path, crop_data: UserImageCrop | None = None) -> None:
    for variant in settings.PROFILE_IMAGE_VARIANT_SIZES.keys():
        _generate_image_variant(original_path, variant, crop_data)


def _ensure_image_variants(image_record: UserImage) -> None:
    original_path = Path(settings.PROFILE_IMAGE_UPLOAD_DIR) / image_record.file_path
    if not original_path.exists():
        return

    crop_data = None
    if (
        image_record.crop_x is not None and
        image_record.crop_y is not None and
        image_record.crop_size is not None and
        image_record.original_width is not None and
        image_record.original_height is not None
    ):
        crop_data = UserImageCrop(
            crop_x=image_record.crop_x,
            crop_y=image_record.crop_y,
            crop_size=image_record.crop_size,
            original_width=image_record.original_width,
            original_height=image_record.original_height,
        )

    _generate_profile_image_variants(original_path, crop_data)


async def list_user_profile_images(current_user: User, db: AsyncSession) -> list[UserImage]:
    stmt = select(UserImage).where(UserImage.user_id == current_user.id).order_by(UserImage.created_at.desc())
    result = await db.execute(stmt)
    images = result.scalars().all()
    for image in images:
        try:
            _ensure_image_variants(image)
        except HTTPException:
            continue
    return images


async def activate_user_profile_image(current_user: User, image_id: int, db: AsyncSession) -> UserImage:
    stmt = select(UserImage).where(UserImage.id == image_id, UserImage.user_id == current_user.id)
    result = await db.execute(stmt)
    image_record = result.scalar_one_or_none()
    if image_record is None:
        raise HTTPException(status_code=404, detail="Profile image not found.")

    if (
        image_record.crop_x is None or
        image_record.crop_y is None or
        image_record.crop_size is None or
        image_record.original_width is None or
        image_record.original_height is None
    ):
        raise HTTPException(status_code=400, detail="Cannot activate an image without saved crop metadata.")

    await db.execute(
        update(UserImage)
        .where(UserImage.user_id == current_user.id, UserImage.is_active == True)
        .values(is_active=False)
    )

    image_record.is_active = True
    await db.commit()
    await db.refresh(image_record)
    return image_record


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
    user_dir = _get_user_image_upload_dir(current_user)
    destination = user_dir / filename

    try:
        destination.write_bytes(file_bytes)
    except OSError as exc:
        raise HTTPException(status_code=500, detail="Unable to save profile image.") from exc

    try:
        _generate_profile_image_variants(destination)
    except HTTPException:
        destination.unlink(missing_ok=True)
        raise

    relative_path = _get_user_image_subpath(current_user.id, filename)

    avatar_relative_path = _get_variant_subpath(relative_path, 'avatar')
    thumbnail_relative_path = _get_variant_subpath(relative_path, 'thumbnail')
    preview_relative_path = _get_variant_subpath(relative_path, 'preview')

    image_record = UserImage(
        user_id=current_user.id,
        file_path=relative_path,
        avatar_path=avatar_relative_path,
        thumbnail_path=thumbnail_relative_path,
        preview_path=preview_relative_path,
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

    original_path = Path(settings.PROFILE_IMAGE_UPLOAD_DIR) / image_record.file_path
    if not original_path.exists():
        raise HTTPException(status_code=500, detail="Original image file not found.")

    _generate_profile_image_variants(original_path, crop_data)

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
