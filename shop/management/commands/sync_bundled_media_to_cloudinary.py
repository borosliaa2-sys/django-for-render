"""Upload the repository-bundled catalogue files to Cloudinary once.

The original catalogue uses FileField names such as ``products/catalog/foo.webp``.
Those files are present in the deployment bundle, but Cloudinary cannot serve a
file merely because its database name exists: the binary must be uploaded once.
This command is deliberately safe on later deploys and only uploads a file when
its Cloudinary URL is absent.
"""

from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError

from shop.models import Article, Product


class Command(BaseCommand):
    help = "Synchronize bundled catalogue/article media to Cloudinary when it is configured."

    def _sync_field(self, model, field_name: str, label: str) -> tuple[int, int, int]:
        uploaded = existing = missing = 0
        media_root = Path(settings.MEDIA_ROOT).resolve()

        for obj in model.objects.exclude(**{f"{field_name}__isnull": True}).exclude(
            **{field_name: ""}
        ).iterator(chunk_size=100):
            field = getattr(obj, field_name)
            stored_name = str(getattr(field, "name", "") or "").lstrip("/")
            if not stored_name:
                continue

            try:
                if default_storage.exists(stored_name):
                    existing += 1
                    continue
            except Exception as exc:
                raise CommandError(
                    "Cloudinary response could not be verified. Check CLOUDINARY_URL "
                    "(or CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY and "
                    "CLOUDINARY_API_SECRET) in Render Environment."
                ) from exc

            source = (media_root / stored_name).resolve()
            if media_root not in source.parents or not source.is_file():
                missing += 1
                self.stderr.write(f"Missing bundled {label}: {stored_name}")
                continue

            try:
                with source.open("rb") as local_file:
                    remote_name = default_storage.save(stored_name, File(local_file, name=source.name))
            except Exception as exc:
                raise CommandError(
                    f"Could not upload {stored_name} to Cloudinary. Verify the API key, "
                    "API secret, cloud name and Cloudinary account limits."
                ) from exc

            # Cloudinary can normalize the public id (including the configured
            # prefix). Persist the returned id so future URLs target that exact
            # resource instead of the old local-only name.
            if remote_name and remote_name != stored_name:
                model.objects.filter(pk=obj.pk).update(**{field_name: remote_name})
            uploaded += 1

        return uploaded, existing, missing

    def handle(self, *args, **options):
        if not getattr(settings, "CLOUDINARY_ENABLED", False):
            self.stdout.write(
                self.style.WARNING(
                    "Cloudinary is not configured; bundled media remains local. "
                    "Set a complete CLOUDINARY_URL or all three CLOUDINARY_* credentials."
                )
            )
            return

        product_counts = self._sync_field(Product, "image_file", "product image")
        article_counts = self._sync_field(Article, "image_file", "article image")
        self.stdout.write(
            self.style.SUCCESS(
                "Cloudinary media sync complete: "
                f"products uploaded/existing/missing={product_counts[0]}/{product_counts[1]}/{product_counts[2]}, "
                f"articles uploaded/existing/missing={article_counts[0]}/{article_counts[1]}/{article_counts[2]}."
            )
        )
