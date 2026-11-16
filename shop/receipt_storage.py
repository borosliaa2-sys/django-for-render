"""Private storage for card-to-card receipts.

Receipts are intentionally separate from MEDIA_ROOT so static/media middleware
can never expose them merely by knowing a file name. The same best-effort
Cloudinary recovery mirror used for other uploads is retained.
"""
from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.files.storage import FileSystemStorage

from .cloudinary_backup import cloudinary_backup_enabled, sync_local_file_to_cloudinary
from .media_storage import LocalMediaWithCloudinaryBackupStorage


class PrivateReceiptStorage(LocalMediaWithCloudinaryBackupStorage):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("location", settings.PRIVATE_RECEIPTS_ROOT)
        # This URL is never embedded in customer/admin HTML; authorized views
        # use the protected order receipt endpoint instead.
        kwargs.setdefault("base_url", "/private-receipts/")
        super().__init__(*args, **kwargs)

    @property
    def location(self):
        # Resolve this at use time so Django tests and isolated deployments can
        # override PRIVATE_RECEIPTS_ROOT without rebuilding the storage object.
        return str(Path(settings.PRIVATE_RECEIPTS_ROOT).resolve())

    def _save(self, name, content):
        """Save a receipt privately and verify its Cloudinary recovery copy.

        General product/article media may use a best-effort backup because the
        local original remains publicly available. A payment receipt is a
        private financial document and must not be reported as successfully
        uploaded when a configured Cloudinary backup has failed. In that case
        remove the just-written temporary local copy and let the view show the
        customer a retry message instead.
        """
        # Deliberately bypass LocalMediaWithCloudinaryBackupStorage._save:
        # that method logs and swallows a Cloudinary failure, which is unsafe
        # for an acknowledged payment receipt.
        saved_name = FileSystemStorage._save(self, name, content)
        if not cloudinary_backup_enabled():
            return saved_name
        try:
            sync_local_file_to_cloudinary(saved_name, Path(self.path(saved_name)))
        except Exception:
            try:
                Path(self.path(saved_name)).unlink(missing_ok=True)
            except OSError:
                pass
            raise
        return saved_name


private_receipt_storage = PrivateReceiptStorage()
