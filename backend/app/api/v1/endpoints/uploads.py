"""Product image uploads.

Stored on the local filesystem under ``MEDIA_ROOT`` and served read-only from
``MEDIA_URL_PREFIX``. Production deployments should front this with object
storage; the response contract (a site-relative URL) does not change if they do.

Hardening applied here:
* the client filename is never used — the stored name is a fresh UUID;
* the extension comes from the validated content type, not the request;
* only image media types are accepted, and the byte count is capped.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile, status

from app.api.deps import require_any_permission
from app.core.config import settings
from app.core.exceptions import UnprocessableError
from app.core.permissions import PermissionCode
from app.schemas.upload import UploadedImage

router = APIRouter(prefix="/uploads", tags=["uploads"])

ALLOWED_IMAGE_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


@router.post(
    "/images",
    response_model=UploadedImage,
    status_code=status.HTTP_201_CREATED,
    summary="Upload an image",
    dependencies=[
        Depends(require_any_permission(PermissionCode.CATALOG_WRITE, PermissionCode.BUSINESS_WRITE))
    ],
)
async def upload_image(
    file: Annotated[UploadFile, File(description="PNG, JPEG, WebP or GIF")],
) -> UploadedImage:
    content_type = (file.content_type or "").lower()
    extension = ALLOWED_IMAGE_TYPES.get(content_type)
    if extension is None:
        raise UnprocessableError(
            "Only PNG, JPEG, WebP and GIF images are accepted.",
            code="unsupported_image_type",
            details=[{"field": "file", "message": f"Received '{content_type or 'unknown'}'."}],
        )

    # Read one byte past the cap so an oversized upload is detected without
    # buffering the whole thing in memory.
    payload = await file.read(settings.MAX_IMAGE_BYTES + 1)
    if len(payload) > settings.MAX_IMAGE_BYTES:
        raise UnprocessableError(
            f"Images must be {settings.MAX_IMAGE_BYTES // (1024 * 1024)} MB or smaller.",
            code="image_too_large",
            details=[{"field": "file", "message": "File exceeds the size limit."}],
        )
    if not payload:
        raise UnprocessableError(
            "The uploaded file is empty.",
            code="empty_upload",
            details=[{"field": "file", "message": "No bytes received."}],
        )

    settings.media_path.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}{extension}"
    (settings.media_path / name).write_bytes(payload)

    return UploadedImage(
        url=f"{settings.MEDIA_URL_PREFIX}/{name}",
        content_type=content_type,
        size=len(payload),
    )
