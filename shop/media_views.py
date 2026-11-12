"""Same-origin original and responsive media delivery.

Visitors always request an Attarbashi URL.  Local catalogue media can be
recovered from Cloudinary server-side after an ephemeral-disk cache miss, while
responsive derivatives are generated locally and cached with immutable URLs.
"""
from __future__ import annotations

import hashlib
import mimetypes
import os
import posixpath
import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urlsplit
from urllib.request import Request, urlopen

from django.conf import settings
from django.http import FileResponse, Http404
from django.views.decorators.http import require_GET
from PIL import Image, ImageOps, UnidentifiedImageError

from .models import Article, Product

_MAX_RECOVERY_BYTES = 20 * 1024 * 1024
_IMAGE_CACHE_SECONDS = 60 * 60 * 24 * 365
_MAX_RESPONSIVE_WIDTH = 2000
_RESPONSIVE_QUALITY = 78


def _safe_path_in(root: Path, raw_name: str) -> tuple[str, Path]:
    """Normalize a relative name and keep the resolved target inside *root*."""
    clean = str(raw_name or "").replace("\\", "/").lstrip("/")
    clean = posixpath.normpath(clean)
    if not clean or clean in {".", ".."} or clean.startswith("../"):
        raise Http404("Invalid media path")

    resolved_root = Path(root).resolve()
    target = (resolved_root / clean).resolve()
    if target != resolved_root and resolved_root not in target.parents:
        raise Http404("Invalid media path")
    return clean, target


def _safe_local_path(raw_name: str) -> tuple[str, Path]:
    """Return a normalized media name and a path guaranteed inside MEDIA_ROOT."""
    return _safe_path_in(Path(settings.MEDIA_ROOT), raw_name)


def _url_path(value: str) -> str:
    """Return a URL path only; query strings must never select a local file."""
    return unquote(urlsplit(str(value or "")).path or "")


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
            with Image.open(path) as image:
                content_type = Image.MIME.get(image.format)
        except (UnidentifiedImageError, OSError, ValueError):
            content_type = None
    response = FileResponse(path.open("rb"), content_type=content_type or "application/octet-stream")
    response["Cache-Control"] = f"public, max-age={_IMAGE_CACHE_SECONDS}, immutable"
    return response


def _static_source_path(raw_name: str) -> tuple[str, Path]:
    """Resolve a static source from a trusted project/staticfiles directory."""
    static_url_path = _url_path(str(getattr(settings, "STATIC_URL", "/static/") or "/static/"))
    source_path = _url_path(raw_name)
    if not source_path.startswith(static_url_path):
        raise Http404("Unsupported image source")
    relative_name = source_path[len(static_url_path):]

    static_roots = [Path(root) for root in getattr(settings, "STATICFILES_DIRS", [])]
    static_root = getattr(settings, "STATIC_ROOT", None)
    if static_root:
        static_roots.append(Path(static_root))
    for root in static_roots:
        try:
            clean_name, candidate = _safe_path_in(root, relative_name)
        except Http404:
            continue
        if candidate.is_file():
            return clean_name, candidate
    raise Http404("Static image not found")


def _responsive_source(raw_source: str) -> tuple[str, str, Path]:
    """Resolve an approved local media/static source for derivative creation."""
    source_path = _url_path(raw_source)
    media_url_path = _url_path(str(getattr(settings, "MEDIA_URL", "/media/") or "/media/"))
    if source_path.startswith(media_url_path):
        name, target = _safe_local_path(source_path[len(media_url_path):])
        if not target.is_file():
            if not _is_known_media(name) or not _recover_from_cloudinary(name, target):
                raise Http404("Media recovery copy not found")
        return "media", name, target

    name, target = _static_source_path(source_path)
    return "static", name, target


def _derivative_path(source_kind: str, source_name: str, source: Path, width: int) -> Path:
    """Return an immutable cache filename that changes when the source changes."""
    stat = source.stat()
    fingerprint = hashlib.sha256(
        f"{source_kind}:{source_name}:{stat.st_mtime_ns}:{stat.st_size}:w{width}:q{_RESPONSIVE_QUALITY}".encode()
    ).hexdigest()
    return Path(settings.MEDIA_ROOT) / ".responsive" / fingerprint[:2] / f"{fingerprint}.webp"


def _create_webp_derivative(source: Path, target: Path, width: int) -> None:
    """Resize *source* without enlarging it, then atomically save efficient WebP."""
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary_name = None
    try:
        with Image.open(source) as opened:
            image = ImageOps.exif_transpose(opened)
            if image.width > width:
                height = max(1, round(image.height * width / image.width))
                image = image.resize((width, height), Image.Resampling.LANCZOS)
            if image.mode not in {"RGB", "RGBA"}:
                image = image.convert("RGBA" if "transparency" in image.info else "RGB")
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=target.parent, delete=False, prefix=".responsive-", suffix=".webp"
            ) as temp_file:
                temporary_name = temp_file.name
                image.save(temp_file, format="WEBP", quality=_RESPONSIVE_QUALITY, method=6)
        # Concurrent first visitors can safely race here: both files encode the
        # same deterministic derivative and os.replace is atomic.
        os.replace(temporary_name, target)
    except (UnidentifiedImageError, OSError, ValueError):
        if temporary_name:
            Path(temporary_name).unlink(missing_ok=True)
        raise Http404("Image cannot be optimized")


@require_GET
def serve_responsive_media(request, width: int):
    """Serve a trusted local image resized for the rendered slot.

    The URL contains the requested width while the generated filename includes
    source metadata, so a changed admin upload receives a new derivative and
    old browser-cache entries can remain immutable.
    """
    if width < 64 or width > _MAX_RESPONSIVE_WIDTH:
        raise Http404("Unsupported image width")
    raw_source = request.GET.get("src", "")
    if not raw_source:
        raise Http404("Missing image source")

    source_kind, source_name, source = _responsive_source(raw_source)
    derivative = _derivative_path(source_kind, source_name, source, width)
    if not derivative.is_file():
        _create_webp_derivative(source, derivative, width)

    response = FileResponse(derivative.open("rb"), content_type="image/webp")
    response["Cache-Control"] = f"public, max-age={_IMAGE_CACHE_SECONDS}, immutable"
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
