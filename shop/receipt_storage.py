"""Private storage for card-to-card receipts.

Receipts are intentionally separate from MEDIA_ROOT so static/media middleware
can never expose them merely by knowing a file name. The same best-effort
Cloudinary recovery mirror used for other uploads is retained.
"""
from __future__ import annotations

from pathlib import Path

from django.conf import settings

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


private_receipt_storage = PrivateReceiptStorage()
