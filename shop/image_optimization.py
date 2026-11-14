"""WebP optimization for images newly uploaded in the admin."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from django.utils.text import slugify
from PIL import Image, ImageOps, UnidentifiedImageError


MAX_UPLOAD_IMAGE_SIZE = (1600, 1600)
WEBP_QUALITY = 82
# FileField paths include e.g. ``products/2026/10/`` and the field's default
# database length is 100. Keeping the stem comfortably below that leaves room
# for the path, suffix, and a collision suffix added by Django storage.
MAX_OPTIMIZED_NAME_STEM_LENGTH = 70


def optimized_image_name(raw_name: str) -> str:
    """Return a compact, URL-safe WebP filename while retaining Persian text.

    ``allow_unicode=True`` keeps meaningful Persian product/article names in
    newly uploaded image paths.  Django's local storage and same-origin media
    URLs handle these names safely (browsers percent-encode them in requests).
    Existing stored paths are deliberately never renamed.
    """
    stem = slugify(raw_name or "", allow_unicode=True).strip("-")
    stem = stem[:MAX_OPTIMIZED_NAME_STEM_LENGTH].rstrip("-")
    return f"{stem or 'image'}.webp"


def optimize_new_upload(field_file, descriptive_name: str = "") -> bool:
    """Convert a fresh FileField image to an oriented, descriptive WebP.

    A committed field is already in storage (for example a bundled catalogue
    asset loaded from a fixture), so it is intentionally untouched. The helper
    only processes a fresh file assigned through Django admin or a form. When
    supplied, ``descriptive_name`` (the product or article title) is used for
    the filename; this makes new Persian uploads meaningful without changing
    any existing public media URL.
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

    raw_name = descriptive_name or Path(field_file.name or "image").stem
    field_file.save(optimized_image_name(raw_name), ContentFile(output.getvalue()), save=False)
    return True
