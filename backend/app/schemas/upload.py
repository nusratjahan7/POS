from __future__ import annotations

from pydantic import BaseModel


class UploadedImage(BaseModel):
    """Result of an image upload. `url` is site-relative so it works behind any host."""

    url: str
    content_type: str
    size: int
