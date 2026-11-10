"""Return bundled media records from legacy Cloudinary ids to local paths.

Older deployments stored Cloudinary's prefixed public id in ``image_file``.
The storefront is now local-first, so a record is normalized only when the
matching file is actually bundled in ``MEDIA_ROOT``.  Remote-only admin uploads
remain untouched and are recovered through the same-origin media endpoint.
"""
from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from shop.models import Article, Product


class Command(BaseCommand):
    help = "Normalize legacy Cloudinary media references when a bundled local file exists."

    def _local_name(self, stored_name: str, media_root: Path) -> str | None:
        clean = str(stored_name or "").replace("\\", "/").lstrip("/")
        prefix = str(getattr(settings, "CLOUDINARY_STORAGE", {}).get("PREFIX", "")).strip("/")
        candidates = [clean]
        if prefix and clean.startswith(f"{prefix}/"):
            candidates.append(clean[len(prefix) + 1 :])

        for candidate in candidates:
            source = (media_root / candidate).resolve()
            if media_root in source.parents and source.is_file():
                return candidate
            # Cloudinary public ids may omit the original extension although
            # the bundled source keeps it. Resolve only common image suffixes
            # inside MEDIA_ROOT; never search outside the media directory.
            if not Path(candidate).suffix:
                for suffix in (".webp", ".jpg", ".jpeg", ".png"):
                    with_suffix = f"{candidate}{suffix}"
                    source = (media_root / with_suffix).resolve()
                    if media_root in source.parents and source.is_file():
                        return with_suffix
        return None

    def _normalize_model(self, model, field_name: str, media_root: Path) -> tuple[int, int]:
        normalized = remote_only = 0
        queryset = model.objects.exclude(**{f"{field_name}__isnull": True}).exclude(
            **{field_name: ""}
        )
        for obj in queryset.iterator(chunk_size=100):
            stored_name = str(getattr(obj, field_name).name or "")
            local_name = self._local_name(stored_name, media_root)
            if local_name and local_name != stored_name:
                model.objects.filter(pk=obj.pk).update(**{field_name: local_name})
                normalized += 1
            elif not local_name:
                remote_only += 1
        return normalized, remote_only

    def handle(self, *args, **options):
        media_root = Path(settings.MEDIA_ROOT).resolve()
        product_counts = self._normalize_model(Product, "image_file", media_root)
        article_counts = self._normalize_model(Article, "image_file", media_root)
        self.stdout.write(
            self.style.SUCCESS(
                "Local media references normalized: "
                f"products normalized/remote-only={product_counts[0]}/{product_counts[1]}, "
                f"articles normalized/remote-only={article_counts[0]}/{article_counts[1]}."
            )
        )
