"""Private Cloudinary backup helpers for locally served media.

Cloudinary is deliberately a recovery copy, not a browser-facing delivery URL:
visitors always request ``/media/...`` from Attarbashi. The helpers here are
used after a local save and by the deployment sync command.
"""
from __future__ import annotations

import logging
import posixpath
from pathlib import Path

from django.conf import settings
from django.core.files import File

logger = logging.getLogger(__name__)


def cloudinary_backup_enabled() -> bool:
    return bool(getattr(settings, "CLOUDINARY_ENABLED", False))


def _remote_storage():
    """Create the Cloudinary storage only when complete credentials exist."""
    if not cloudinary_backup_enabled():
        return None
    from cloudinary_storage.storage import MediaCloudinaryStorage

    return MediaCloudinaryStorage()


def _canonical_public_id(storage, name: str) -> str:
    """Return the Cloudinary public ID which corresponds to ``/media/name``.

    ``django-cloudinary-storage`` normally uploads with ``use_filename=True``
    but without an explicit public ID. Cloudinary may append a random suffix in
    that case. Its generated ID then differs from the ID queried by
    ``storage.exists(name)``, which makes a later sync upload another copy.

    Image delivery URLs include the file extension as the format. Cloudinary's
    image public ID must therefore omit that final extension while retaining
    the configured folder prefix.
    """
    remote_name = storage._prepend_prefix(name.replace("\\", "/"))
    public_id, extension = posixpath.splitext(remote_name)
    return public_id if extension else remote_name


def _cloudinary_asset_folder(name: str) -> str:
    """Return the Media Library folder for a logical local-media path.

    Cloudinary accounts created since mid-2024 normally use *dynamic folders*:
    a slash in ``public_id`` controls delivery identity but **does not** place
    the asset in that folder in the Media Library. Without ``asset_folder`` a
    new receipt therefore appears under Home even though its public ID contains
    ``payment_receipts/2026/11``.

    Keep the configurable Cloudinary namespace in the public ID (needed for
    recovery URLs), while making the visible Media Library hierarchy match the
    site's logical media path exactly: ``payment_receipts/YYYY/MM``.
    """
    clean_name = name.replace("\\", "/").lstrip("/")
    return posixpath.dirname(clean_name)


def _upload_with_deterministic_public_id(storage, name: str, local_file, source_name: str) -> None:
    """Upload one recovery copy at the same stable ID used by ``exists``.

    ``overwrite=False`` is deliberate: this helper is a missing-backup repair,
    not a content-replacement mechanism. A newly uploaded product normally has
    a new media name; existing live backup copies are never overwritten.
    """
    import cloudinary.uploader

    remote_name = storage._prepend_prefix(name.replace("\\", "/"))
    options = {
        "public_id": _canonical_public_id(storage, name),
        "resource_type": storage._get_resource_type(remote_name),
        "tags": storage.TAG,
        "use_filename": False,
        "unique_filename": False,
        "overwrite": False,
    }
    asset_folder = _cloudinary_asset_folder(name)
    if asset_folder:
        # Dynamic-folder accounts otherwise place this asset in Home. Fixed
        # folder accounts continue using the public-ID path, so delivery stays
        # compatible in both modes.
        options["asset_folder"] = asset_folder
    cloudinary.uploader.upload(File(local_file, name=source_name), **options)


def _organize_existing_receipt(storage, name: str) -> None:
    """Move a pre-v38 receipt out of Home without changing its public ID."""
    if not name.replace("\\", "/").lstrip("/").startswith("payment_receipts/"):
        return
    asset_folder = _cloudinary_asset_folder(name)
    if not asset_folder:
        return
    import cloudinary.api

    remote_name = storage._prepend_prefix(name.replace("\\", "/"))
    try:
        cloudinary.api.update(
            _canonical_public_id(storage, name),
            resource_type=storage._get_resource_type(remote_name),
            asset_folder=asset_folder,
        )
    except Exception:
        # Folder placement is a Media Library organization improvement. An
        # existing, verified recovery asset must remain usable even if the
        # account is in legacy fixed-folder mode or its Admin API is limited.
        logger.warning("Could not move Cloudinary receipt into %s: %s", asset_folder, name, exc_info=True)


def organize_existing_cloudinary_receipt(name: str) -> str:
    """Place an existing remote receipt in its YYYY/MM Media Library folder.

    This intentionally needs no local source file, so it can repair a receipt
    that already exists remotely but whose ephemeral Render copy has gone.
    Returns ``existing``, ``missing``, or ``disabled``.
    """
    storage = _remote_storage()
    if storage is None:
        return "disabled"
    if not storage.exists(name):
        return "missing"
    _organize_existing_receipt(storage, name)
    return "existing"


def sync_local_file_to_cloudinary(name: str, source: Path) -> str:
    """Ensure one local media file exists in Cloudinary without duplicates.

    Returns ``"uploaded"`` or ``"existing"``. It intentionally never returns
    Cloudinary's public ID to callers: the database continues to hold the
    stable local path used by the site's own ``/media/`` endpoint.

    New recovery copies use an explicit, deterministic Cloudinary public ID.
    This makes the storage URL checked by ``exists(name)`` exactly match the
    uploaded resource and prevents each later deploy from producing a
    collision-suffixed duplicate.
    """
    storage = _remote_storage()
    if storage is None:
        return "disabled"
    if storage.exists(name):
        _organize_existing_receipt(storage, name)
        return "existing"

    try:
        with source.open("rb") as local_file:
            _upload_with_deterministic_public_id(storage, name, local_file, source.name)
    except Exception:
        # A concurrent upload can win between the HEAD check and the upload.
        # In that narrow case the desired deterministic backup now exists and
        # the result is still successful; do not retry with a random name.
        if storage.exists(name):
            _organize_existing_receipt(storage, name)
            return "existing"
        raise
    return "uploaded"
