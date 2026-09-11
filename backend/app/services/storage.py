"""File storage abstraction: local, Cloudinary, or S3."""

import uuid
from pathlib import Path

import aiofiles
from fastapi import UploadFile

from app.core.config import settings


async def save_upload(file: UploadFile, subfolder: str = "general") -> str:
    """Save uploaded file and return URL/path."""
    ext = Path(file.filename or "file").suffix
    filename = f"{uuid.uuid4()}{ext}"

    if settings.STORAGE_BACKEND == "cloudinary" and settings.CLOUDINARY_CLOUD_NAME:
        return await _save_cloudinary(file, subfolder, filename)
    elif settings.STORAGE_BACKEND == "s3" and settings.AWS_S3_BUCKET:
        return await _save_s3(file, subfolder, filename)
    else:
        return await _save_local(file, subfolder, filename)


async def _save_local(file: UploadFile, subfolder: str, filename: str) -> str:
    upload_path = Path(settings.UPLOAD_DIR) / subfolder
    upload_path.mkdir(parents=True, exist_ok=True)
    file_path = upload_path / filename
    content = await file.read()
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)
    return f"/uploads/{subfolder}/{filename}"


async def _save_cloudinary(file: UploadFile, subfolder: str, filename: str) -> str:
    import cloudinary
    import cloudinary.uploader

    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
    )
    content = await file.read()
    result = cloudinary.uploader.upload(content, folder=f"medicare/{subfolder}", public_id=filename)
    return result["secure_url"]


async def _save_s3(file: UploadFile, subfolder: str, filename: str) -> str:
    import boto3

    s3 = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )
    key = f"{subfolder}/{filename}"
    content = await file.read()
    s3.put_object(Bucket=settings.AWS_S3_BUCKET, Key=key, Body=content)
    return f"https://{settings.AWS_S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"
