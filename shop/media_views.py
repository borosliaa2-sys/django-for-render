"""Same-origin media delivery with Cloudinary recovery on a local cache miss."""
from __future__ import annotations

import mimetypes
import os
import posixpath
import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from django.conf import settings
from django.http import FileResponse, Http404
from django.views.decorators.http import require_GET

from .models import Article, Product

_MAX_RECOVERY_BYTES = 20 * 1024 * 1024


def _safe_local_path(raw_name: str) -> tuple[str, Path]:
    """Return a normalized media name and a path guaranteed inside MEDIA_ROOT."""
    clean = str(raw_name or "").replace("\\", "/").lstrip("/")
    clean = posixpath.normpath(clean)
    if not clean or clean in {".", ".."} or clean.startswith("../"):
        raise Http404("Invalid media path")

    root = Path(settings.MEDIA_ROOT).resolve()
    target = (root / clean).resolve()
    if target != root and root not in target.parents:
        raise Http404("Invalid media path")
    return clean, target


def _is_known_media(name: str) -> bool:
    """Do not turn an arbitrary public URL into a Cloudinary proxy request."""
    return (
        Product.objects.filter(image_file=name).exists()
        or Article.objects.filter(image_file=name).exists()
    )


def _cloudinary_public_ids(name: str):
    """Yield the current and legacy Cloudinary public-id forms for a file."""
    seen: set[str] = set()
    prefix = str(getattr(settings, "CLOUDINARY_STORAGE", {}).get("PREFIX", "")).strip("/")
    for candidate in (name, f"{prefix}/{name}" if prefix else ""):
        candidate = candidate.strip("/")
        if candidate and candidate not in seen:
            seen.add(candidate)
            yield candidate


def _recover_from_cloudinary(name: str, target: Path) -> bool:
    """Download a missing public image server-side and atomically cache it."""
    config = getattr(settings, "CLOUDINARY_STORAGE", {})
    cloud_name = str(config.get("CLOUD_NAME", "")).strip()
    if not getattr(settings, "CLOUDINARY_ENABLED", False) or not cloud_name:
        return False

    for public_id in _cloudinary_public_ids(name):
        url = (
            f"https://res.cloudinary.com/{quote(cloud_name, safe='')}/image/upload/"
            f"{quote(public_id, safe='/')}"
        )
        temporary_name = None
        try:
            request = Request(url, headers={"User-Agent": "Attarbashi-media-recovery/1.0"})
            with urlopen(request, timeout=15) as upstream:
                content_type = upstream.headers.get_content_type()
                if not content_type.startswith("image/"):
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(
                    mode="wb", dir=target.parent, delete=False, prefix=".media-recovery-"
                ) as temp_file:
                    temporary_name = temp_file.name
                    total = 0
                    while chunk := upstream.read(64 * 1024):
                        total += len(chunk)
                        if total > _MAX_RECOVERY_BYTES:
                            raise ValueError("Cloudinary recovery file is too large")
                        temp_file.write(chunk)
                os.replace(temporary_name, target)
                return True
        except (HTTPError, URLError, TimeoutError, ValueError, OSError):
            if temporary_name:
                Path(temporary_name).unlink(missing_ok=True)
            # Try the other safe public-id shape (prefixed or unprefixed).
            continue
    return False


def _file_response(path: Path):
    content_type, _encoding = mimetypes.guess_type(str(path))
    if not content_type:
        # Legacy Cloudinary public ids can omit the original suffix. Preserve
        # an image content type after recovery so an <img> still renders.
        try:
            from PIL import Image

            with Image.open(path) as image:
                content_type = Image.MIME.get(image.format)
        except Exception:
            content_type = None
    response = FileResponse(path.open("rb"), content_type=content_type or "application/octet-stream")
    response["Cache-Control"] = "public, max-age=86400, stale-while-revalidate=604800"
    return response


@require_GET
def serve_site_media(request, media_path: str):
    """Serve media from Attarbashi; use Cloudinary only after a local miss."""
    name, target = _safe_local_path(media_path)
    if target.is_file():
        return _file_response(target)

    if not _is_known_media(name):
        raise Http404("Media not found")
    if not _recover_from_cloudinary(name, target):
        raise Http404("Media recovery copy not found")
    return _file_response(target)
