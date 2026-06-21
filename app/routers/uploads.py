import io

import cloudinary
import cloudinary.uploader
from fastapi import APIRouter, Depends, HTTPException, UploadFile

from app.core.config import settings
from app.core.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/uploads", tags=["uploads"])

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/avif"}
MAX_SIZE = 8 * 1024 * 1024  # 8 MB


def _cloudinary_configured() -> bool:
    return bool(settings.cloudinary_cloud_name and settings.cloudinary_api_key and settings.cloudinary_api_secret)


@router.post("")
async def upload_image(file: UploadFile, current_user: User = Depends(get_current_user)):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Format d'image non supporté")

    data = await file.read()
    if len(data) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="Image trop volumineuse (max 8 Mo)")

    if not _cloudinary_configured():
        raise HTTPException(
            status_code=503,
            detail="Stockage cloud non configuré. Ajoutez les variables CLOUDINARY_* dans les paramètres du serveur.",
        )

    cloudinary.config(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
        secure=True,
    )

    result = cloudinary.uploader.upload(
        io.BytesIO(data),
        folder="yfic",
        resource_type="image",
        overwrite=False,
    )

    return {"url": result["secure_url"]}
