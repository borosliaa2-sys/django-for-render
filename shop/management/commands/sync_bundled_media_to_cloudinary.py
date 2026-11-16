"""Mirror bundled catalogue media to Cloudinary as a recovery backup.

The site always serves images through its own ``/media/`` URL.  Cloudinary is
not a browser-facing delivery provider: this command merely guarantees a copy
exists there so a reset local disk can restore the file server-side on demand.
"""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from shop.cloudinary_backup import sync_local_file_to_cloudinary
from shop.models import Article, Order, Product


class Command(BaseCommand):
    help = "Synchronize catalogue, article, and card-receipt media to Cloudinary recovery storage."

    def add_arguments(self, parser):
        parser.add_argument(
            "--receipts-only",
            action="store_true",
            help="Only back up card-payment receipts (including safe legacy MEDIA_ROOT fallback).",
        )

    @staticmethod
    def _legacy_receipt_source(stored_name: str) -> Path | None:
        """Locate a receipt uploaded before private receipt storage existed.

        Database records keep the same logical ``payment_receipts/...`` name
        after the privacy release, but their old physical file is still under
        MEDIA_ROOT. The field now points at PRIVATE_RECEIPTS_ROOT, so a normal
        ``field.storage.path`` lookup cannot find such a legacy file.
        """
        if not stored_name.startswith("payment_receipts/"):
            return None
        legacy_root = Path(settings.MEDIA_ROOT).resolve()
        candidate = (legacy_root / stored_name).resolve()
        if legacy_root not in candidate.parents or not candidate.is_file():
            return None
        return candidate

    def _local_source(self, field, stored_name: str, *, is_receipt: bool) -> tuple[Path | None, str]:
        """Return a safe local source and whether it is current or legacy."""
        try:
            storage_root = Path(field.storage.location).resolve()
            source = Path(field.storage.path(stored_name)).resolve()
        except (AttributeError, NotImplementedError, OSError, ValueError):
            source = None
            storage_root = None

        if source and storage_root and storage_root in source.parents and source.is_file():
            return source, "current"
        if is_receipt:
            legacy = self._legacy_receipt_source(stored_name)
            if legacy:
                return legacy, "legacy"
        return None, "missing"

    def _sync_field(self, model, field_name: str, label: str) -> tuple[int, int, int, int]:
        uploaded = existing = missing = legacy_sources = 0
        is_receipt = model is Order and field_name == "card_receipt"
        for obj in model.objects.exclude(**{f"{field_name}__isnull": True}).exclude(
            **{field_name: ""}
        ).iterator(chunk_size=100):
            field = getattr(obj, field_name)
            stored_name = str(getattr(field, "name", "") or "").lstrip("/")
            source, origin = self._local_source(field, stored_name, is_receipt=is_receipt)
            if source is None:
                missing += 1
                self.stderr.write(f"Missing local {label}: {stored_name}")
                continue
            if origin == "legacy":
                legacy_sources += 1
                self.stdout.write(f"Using legacy MEDIA_ROOT copy for {label}: {stored_name}")

            try:
                result = sync_local_file_to_cloudinary(stored_name, source)
            except Exception as exc:
                raise CommandError(
                    f"Could not back up {stored_name} to Cloudinary. Verify the API key, "
                    "API secret, cloud name and Cloudinary account limits."
                ) from exc

            if result == "uploaded":
                uploaded += 1
            elif result == "existing":
                existing += 1

        return uploaded, existing, missing, legacy_sources

    def handle(self, *args, **options):
        if not getattr(settings, "CLOUDINARY_ENABLED", False):
            self.stdout.write(
                self.style.WARNING(
                    "Cloudinary is not configured; local media has no remote recovery copy. "
                    "Set a complete CLOUDINARY_URL or all three CLOUDINARY_* credentials."
                )
            )
            return

        receipts_only = bool(options.get("receipts_only"))
        receipt_counts = self._sync_field(Order, "card_receipt", "card payment receipt")
        if receipts_only:
            self.stdout.write(
                self.style.SUCCESS(
                    "Cloudinary receipt recovery backup complete: "
                    f"uploaded/existing/missing/legacy-source={receipt_counts[0]}/{receipt_counts[1]}/{receipt_counts[2]}/{receipt_counts[3]}."
                )
            )
            return

        product_counts = self._sync_field(Product, "image_file", "product image")
        article_counts = self._sync_field(Article, "image_file", "article image")
        self.stdout.write(
            self.style.SUCCESS(
                "Cloudinary recovery backup complete: "
                f"products uploaded/existing/missing={product_counts[0]}/{product_counts[1]}/{product_counts[2]}, "
                f"articles uploaded/existing/missing={article_counts[0]}/{article_counts[1]}/{article_counts[2]}, "
                f"receipts uploaded/existing/missing/legacy-source={receipt_counts[0]}/{receipt_counts[1]}/{receipt_counts[2]}/{receipt_counts[3]}."
            )
        )
