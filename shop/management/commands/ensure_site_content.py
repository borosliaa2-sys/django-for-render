"""Keep deployment-owned icons and starter editorial content available."""

import hashlib
import json

from django.core.management.base import BaseCommand

from shop.editorial_content import MANAGED_ARTICLES
from shop.models import Article, Category, Product


CATEGORY_ICONS = {
    "آرد و مواد اولیه": "categories/category-1.webp",
    "مربا": "categories/category-2.webp",
    "دمنوش": "categories/category-3.webp",
    "لواشک": "categories/category-4.webp",
    "ترشی و شور": "categories/category-5.webp",
    "روغن ها": "categories/category-6.webp",
    "سبزیجات خشک": "categories/category-7.webp",
    "سویق و پودرهای خاص": "categories/category-8.webp",
    "نوشیدنی و عرقیات": "categories/category-9.webp",
    "میوه خشک و آجیلی": "categories/category-10.webp",
    "خشکبار و مغزیجات": "categories/category-11.webp",
    "محصولات بهداشتی": "categories/category-12.webp",
    "گیاهان دارویی": "categories/category-13.webp",
    "ادویه و چاشنی": "categories/category-14.webp",
    "شیرینی و تنقلات": "categories/category-15.webp",
    "سایر": "categories/category-16.webp",
}

# These are fingerprints of the eight supplied articles before the editorial
# revision. An existing article is refined only when its stored source still
# exactly matches this known version. Admin-written edits are never replaced.
PREVIOUS_ARTICLE_FINGERPRINTS = {
    "خواص-دمنوش-آرامش-اعصاب": "b6c8bc885ad6b38e9a8706fed7118318a1c44ecf33d54ecdd34597b765050e40",
    "شناخت-طبع-و-مزاج-طب-سنتی": "57f176d9326b67a5c050edeebdf7f0a1c86e5e5f5b3d02003ebc67719d92fe00",
    "خواص-سیر-ترشی-هفت-ساله": "feb3337581adc41ff640202a9dec7c655200d81131f91cca481d0993ee03eac0",
    "فواید-میوه-خشک-و-خشکبار": "4daf8ac9d1a1644c9714d1ab0bf03dd74d123f676abd3cfd3f317ed2f19d4b22",
    "نگهداری-گیاهان-دارویی-و-ادویه": "372137eac2e24b768e09efff09de779c81365dc0c0e119612304e9191b1f9833",
    "دمنوش-به-لیمو-برای-عصرهای-آرام": "921410a4eb8c2ffa540a79396688b5bbfac5065694d5b3df41c470673204bd3e",
    "راهنمای-مصرف-عرقیات-گیاهی": "a5efca15c055deeb16ff38693c056d83a7c500d12b05760ae1733aef6eeece39",
    "هفت-ادویه-برای-آشپزی-سالم": "ca69a16ae91227e7213aa013b5728afda93eb05afdc3e0700f013d171e340ebb",
}

FINGERPRINT_FIELDS = ("title", "category_name", "summary", "content", "image", "reading_time")
REFINABLE_FIELDS = (
    "title",
    "category_name",
    "summary",
    "content",
    "image",
    "image_file",
    "author_name",
    "reading_time",
)


def article_fingerprint(article):
    payload = {field: getattr(article, field) for field in FINGERPRINT_FIELDS}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def article_defaults(item):
    return {key: value for key, value in item.items() if key != "product_slugs"}


def article_matches_managed_values(article, item):
    for field in REFINABLE_FIELDS:
        value = getattr(article, field)
        if field == "image_file":
            value = getattr(value, "name", value) or ""
        if value != item[field]:
            return False
    return True


class Command(BaseCommand):
    help = "Repair category assets and safely seed curated articles and verified related products."

    def handle(self, *args, **options):
        repaired_icons = 0
        for category_name, icon_path in CATEGORY_ICONS.items():
            repaired_icons += Category.objects.filter(name=category_name).exclude(
                icon_image=icon_path
            ).update(icon_image=icon_path)

        created_articles = 0
        refined_articles = 0
        linked_articles = 0
        preserved_articles = 0
        missing_product_slugs = set()

        for item in MANAGED_ARTICLES:
            defaults = article_defaults(item)
            article, created = Article.objects.get_or_create(
                slug=item["slug"], defaults=defaults
            )
            created_articles += int(created)

            # Apply this editorial revision once, but only to an unchanged
            # previous starter article. Content changed in the admin is kept.
            expected_fingerprint = PREVIOUS_ARTICLE_FINGERPRINTS.get(article.slug)
            if not created and expected_fingerprint:
                if article_fingerprint(article) == expected_fingerprint:
                    for field in REFINABLE_FIELDS:
                        setattr(article, field, item[field])
                    article.save(update_fields=[*REFINABLE_FIELDS, "updated_at"])
                    refined_articles += 1
                elif not article_matches_managed_values(article, item):
                    preserved_articles += 1

            # Curated relations are seeded only when no editor has selected
            # products manually. This prevents unrelated fallback products.
            if not article.related_products.exists():
                wanted_slugs = item["product_slugs"]
                products_by_slug = {
                    product.slug: product
                    for product in Product.objects.filter(
                        slug__in=wanted_slugs, is_active=True
                    )
                }
                missing_product_slugs.update(set(wanted_slugs) - set(products_by_slug))
                selected_products = [
                    products_by_slug[slug]
                    for slug in wanted_slugs
                    if slug in products_by_slug
                ]
                if selected_products:
                    article.related_products.set(selected_products)
                    linked_articles += 1

        message = (
            "Site content ready: "
            f"{repaired_icons} category icon(s) repaired, "
            f"{created_articles} article(s) created, "
            f"{refined_articles} starter article(s) refined, "
            f"{linked_articles} curated product group(s) linked."
        )
        self.stdout.write(self.style.SUCCESS(message))
        if preserved_articles:
            self.stdout.write(
                self.style.WARNING(
                    f"Kept {preserved_articles} article(s) that no longer match the old starter text."
                )
            )
        if missing_product_slugs:
            self.stdout.write(
                self.style.WARNING(
                    "Unlinked missing product slug(s): "
                    + ", ".join(sorted(missing_product_slugs))
                )
            )
