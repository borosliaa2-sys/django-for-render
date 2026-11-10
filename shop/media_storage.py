"""Local-first media storage with a best-effort Cloudinary recovery copy."""
from __future__ import annotations

import logging
from pathlib import Path

from django.conf import settings
from django.core.files.storage import FileSystemStorage

from .cloudinary_backup import cloudinary_backup_enabled, sync_local_file_to_cloudinary

logger = logging.getLogger(__name__)


class LocalMediaWithCloudinaryBackupStorage(FileSystemStorage):
    """Keep uploads on this site's filesystem and mirror them to Cloudinary.

    A customer's browser is never given a Cloudinary URL.  If the ephemeral
    local disk is reset, the media endpoint downloads the private recovery copy
    once, saves it locally again, and serves it from the Attarbashi domain.
    """

    def _save(self, name, content):
        saved_name = super()._save(name, content)
        if not cloudinary_backup_enabled():
            return saved_name

        try:
            source = Path(self.path(saved_name))
            sync_local_file_to_cloudinary(saved_name, source)
        except Exception:
            # The local upload succeeded and remains usable.  A temporary
            # Cloudinary outage must not turn an administrator upload into a
            # failed form submission; the deployment sync will retry it.
            logger.exception("Cloudinary backup failed for local media: %s", saved_name)
        return saved_name
