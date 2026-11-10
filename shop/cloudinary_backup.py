"""Private Cloudinary backup helpers for locally served media.

Cloudinary is deliberately a recovery copy, not a browser-facing delivery URL:
visitors always request ``/media/...`` from Attarbashi.  The helpers here are
used after a local save and by the deployment sync command.
"""
from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.files import File


def cloudinary_backup_enabled() -> bool:
    return bool(getattr(settings, "CLOUDINARY_ENABLED", False))


def _remote_storage():
    """Create the Cloudinary storage only when complete credentials exist."""
    if not cloudinary_backup_enabled():
        return None
    from cloudinary_storage.storage import MediaCloudinaryStorage

    return MediaCloudinaryStorage()


def sync_local_file_to_cloudinary(name: str, source: Path) -> str:
    """Ensure one local media file exists in Cloudinary.

    Returns ``"uploaded"`` or ``"existing"``.  It intentionally never
    returns Cloudinary's public id to callers: the database continues to hold
    the stable local path used by the site's own ``/media/`` endpoint.
    """
    storage = _remote_storage()
    if storage is None:
        return "disabled"
    if storage.exists(name):
        return "existing"
    with source.open("rb") as local_file:
        storage.save(name, File(local_file, name=source.name))
    return "uploaded"
