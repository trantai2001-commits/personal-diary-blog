import os
from pathlib import Path

from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader

load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True,
)

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}


def is_allowed_image(filename: str) -> bool:
    if not filename:
        return False

    extension = Path(filename).suffix.lower().lstrip(".")
    return extension in ALLOWED_IMAGE_EXTENSIONS


def upload_cover_image(file_storage):
    result = cloudinary.uploader.upload(
        file_storage,
        folder="personal-diary-blog/covers",
        resource_type="image",
        use_filename=True,
        unique_filename=True,
        overwrite=False,
    )

    return {
        "url": result["secure_url"],
        "public_id": result["public_id"],
    }


def delete_cloudinary_image(public_id: str | None):
    if not public_id:
        return

    cloudinary.uploader.destroy(public_id, invalidate=True)