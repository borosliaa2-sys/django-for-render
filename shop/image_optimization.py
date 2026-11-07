"""WebP optimization for images newly uploaded in the admin."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from django.utils.text import slugify
from PIL import Image, ImageOps, UnidentifiedImageError


MAX_UPLOAD_IMAGE_SIZE = (1600, 1600)
WEBP_QUALITY = 82


def optimize_new_upload(field_file) -> bool:
    """Convert a newly assigned FileField image to a correctly oriented WebP.

    A committed field is already in storage (for example a bundled catalogue
    asset loaded from a fixture), so it is intentionally untouched. The helper
    only processes a fresh file assigned through Django admin or a form.
    """
    if not field_file or getattr(field_file, "_committed", True):
        return False

    try:
        source = field_file.file
        source.seek(0)
        with Image.open(source) as opened:
            image = ImageOps.exif_transpose(opened)
            image.thumbnail(MAX_UPLOAD_IMAGE_SIZE, Image.Resampling.LANCZOS)
            if image.mode not in {"RGB", "RGBA"}:
                image = image.convert("RGBA" if "transparency" in image.info else "RGB")

            output = BytesIO()
            image.save(output, format="WEBP", quality=WEBP_QUALITY, method=6)
    except (UnidentifiedImageError, OSError, ValueError):
        # Keep Django's normal FileField behavior if an unexpected file is
        # supplied; the optimizer must never make an admin edit fail silently.
        return False

    raw_name = Path(field_file.name or "image").stem
    optimized_name = f"{slugify(raw_name) or 'image'}.webp"
    field_file.save(optimized_name, ContentFile(output.getvalue()), save=False)
    return True
