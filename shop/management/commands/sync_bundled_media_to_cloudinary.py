"""Mirror bundled catalogue media to Cloudinary as a recovery backup.

The site always serves images through its own ``/media/`` URL.  Cloudinary is
not a browser-facing delivery provider: this command merely guarantees a copy
exists there so a reset local disk can restore the file server-side on demand.
"""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from shop.cloudinary_backup import sync_local_file_to_cloudinary
from shop.models import Article, Product


class Command(BaseCommand):
    help = "Synchronize bundled catalogue/article media to Cloudinary recovery storage."

    def _sync_field(self, model, field_name: str, label: str) -> tuple[int, int, int]:
        uploaded = existing = missing = 0
        media_root = Path(settings.MEDIA_ROOT).resolve()

        for obj in model.objects.exclude(**{f"{field_name}__isnull": True}).exclude(
            **{field_name: ""}
        ).iterator(chunk_size=100):
            field = getattr(obj, field_name)
            stored_name = str(getattr(field, "name", "") or "").lstrip("/")
            source = (media_root / stored_name).resolve()
            if media_root not in source.parents or not source.is_file():
                missing += 1
                self.stderr.write(f"Missing bundled {label}: {stored_name}")
                continue

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

        return uploaded, existing, missing

    def handle(self, *args, **options):
        if not getattr(settings, "CLOUDINARY_ENABLED", False):
            self.stdout.write(
                self.style.WARNING(
                    "Cloudinary is not configured; local media has no remote recovery copy. "
                    "Set a complete CLOUDINARY_URL or all three CLOUDINARY_* credentials."
                )
            )
            return

        product_counts = self._sync_field(Product, "image_file", "product image")
        article_counts = self._sync_field(Article, "image_file", "article image")
        self.stdout.write(
            self.style.SUCCESS(
                "Cloudinary recovery backup complete: "
                f"products uploaded/existing/missing={product_counts[0]}/{product_counts[1]}/{product_counts[2]}, "
                f"articles uploaded/existing/missing={article_counts[0]}/{article_counts[1]}/{article_counts[2]}."
            )
        )
