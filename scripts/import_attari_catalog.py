#!/usr/bin/env python3
"""Import the Attarbashi manifest, create optimized catalog imagery, and update product copy.

Usage (from django-alfa):
    python scripts/import_attari_catalog.py

The import is intentionally idempotent: new manifest items are located by their
English manifest slug on repeat runs.  High-confidence duplicates are mapped to
the existing records explicitly, so no duplicate customer-facing products are
created for those records.
"""
from __future__ import annotations

import csv
import os
import re
import shutil
import sys
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageOps

PROJECT_ROOT = Path(__file__).resolve().parents[1]
# The delivered project keeps the original manifest for auditability.  To repeat
# this import, extract the source image ZIP into data/تصاویر-محصولات first.
MANIFEST_PATH = PROJECT_ROOT / "data" / "manifest.csv"
SOURCE_IMAGE_DIR = PROJECT_ROOT / "data" / "تصاویر-محصولات"
MEDIA_ROOT = PROJECT_ROOT / "media"
DEST_IMAGE_DIR = MEDIA_ROOT / "products" / "catalog"
REPORT_PATH = PROJECT_ROOT / "reports" / "catalog-import-report-fa.md"
BACKUP_DIR = PROJECT_ROOT / "backups"

# These are semantic matches manually reviewed against the 38 products that
# already existed in the project.  They are imported as upgrades, not new rows.
MATCHED_EXISTING: dict[str, str] = {
    "25": "قهوه-هسته-خرما",       # exact
    "44": "پر-هلو",                # exact
    "46": "توت-خشکه",              # spelling variant: توت خشک
    "53": "پر-گلابی",              # spelling variant: گلابی خشک
    "62": "گیلاس-خشک",             # exact
    "77": "تره-خشک",               # exact
    "156": "پودر-سنجد",            # exact
    "214": "آلوچه",                # exact
    "215": "تخمه-گل-آفتاب",        # exact
    "225": "گندمک",                # exact
    "228": "نخودچی-نمکی",          # synonymous: نخودچی شور
    "235": "پولکی",                # exact
    "261": "تمرهندی",              # spacing variant: تمر هندی
    "298": "قاوت-40-مغز",          # spelling/number variant: قاووت چهل مغز
    "345": "ارده",                 # exact
}

# Possible but not certain duplicate families.  They are intentionally left as
# separate products, and are listed in the report for a merchandising decision.
POSSIBLE_OVERLAPS = [
    ("ترشی", "ترشی مخلوط", "170", "نوع/ترکیب و بسته‌بندی در محصول موجود مشخص نیست."),
    ("ترشی کوچک", "ترشی مخلوط", "170", "اندازهٔ بسته و نوع ترشی متفاوت یا نامشخص است."),
    ("سیر ترشی", "ترشی سیر خانگی", "167", "احتمال هم‌پوشانی بالاست، اما «خانگی» ممکن است محصول متفاوتی باشد."),
    ("سیر ترشی کوچک", "ترشی سیر خانگی", "167", "نوع و وزن بسته در ردیف موجود مشخص نیست."),
    ("زیتون", "ترشی زیتون / زیتون پرورده", "168 / 169", "زیتون ساده، ترشی و پرورده از نظر محصول یکسان نیستند."),
    ("نبات", "شاخه نبات / خرده نبات", "333 / 330", "فرم و بسته‌بندی متفاوت است."),
    ("حلواارده", "ارده", "345", "محصول مرتبط است، اما حلواارده و ارده یک کالا نیستند."),
    ("پر کیوی", "کیوی خشک ارگانیک", "43", "برچسب ارگانیک و نوع برش نیاز به تأیید دارد."),
    ("خلال بادام زمینی", "بادام زمینی", "217", "شکل محصول (خلال در برابر دانه) متفاوت است."),
    ("میوه خشک چند میوه", "آجیل چند میوه", "41", "ترکیب دقیق نامشخص است."),
    ("قارا بسته دو عددی", "قارا", "339", "بسته‌بندی و حتی دسته‌بندی ثبت‌شده متفاوت است."),
    ("کشمش", "کشمش خانگی / آفتابی / بندی", "56 / 58 / 59", "نوع کشمش در محصول موجود تعیین نشده است."),
    ("نخودچی", "نخودچی آجیلی / شور", "219 / 228", "طعم‌دار بودن و نوع برشته‌سازی متفاوت است."),
    ("پفیلا خونگی", "پفیلا ساده", "237", "احتمال شباهت وجود دارد؛ مزه و فرمول محصول نامشخص است."),
]


CATEGORY_USAGE = {
    "دمنوش": "دم‌کردن و سرو یک نوشیدنی خوش‌عطر در خانه",
    "مربا": "صبحانه، میان‌وعده و سرو کنار نان و کره",
    "میوه خشک و آجیلی": "میان‌وعده، پذیرایی و استفاده در ترکیب‌های خانگی",
    "خشکبار و مغزیجات": "میان‌وعده، پذیرایی و افزودن به ترکیب‌های غذایی",
    "لواشک": "میان‌وعده و پذیرایی با طعم میوه‌ای",
    "سبزیجات خشک": "آشپزی روزمره، سوپ و خوراک‌های خانگی",
    "ادویه و چاشنی": "طعم‌دهی و آماده‌سازی غذاهای خانگی",
    "گیاهان دارویی": "کاربردهای رایج خانگی یا تهیهٔ دم‌کرده، متناسب با برچسب محصول",
    "نوشیدنی و عرقیات": "سرو در نوشیدنی‌ها یا استفادهٔ رایج خانگی، متناسب با برچسب محصول",
    "روغن‌ها": "استفادهٔ موردنظر درج‌شده روی بسته‌بندی",
    "آرد و مواد اولیه": "آشپزی، شیرینی‌پزی و آماده‌سازی خوراکی‌های خانگی",
    "سویق و پودرهای خاص": "تهیهٔ خوراکی‌ها و نوشیدنی‌های خانگی، مطابق روش مصرف محصول",
    "محصولات بهداشتی": "کاربرد موردنظر درج‌شده روی بسته‌بندی",
    "شیرینی و تنقلات": "میان‌وعده و پذیرایی",
    "ترشی و شور": "سرو کنار غذا و تکمیل سفرهٔ ایرانی",
    "سایر": "استفادهٔ روزمره، متناسب با نوع و برچسب محصول",
}


def canon(value: str) -> str:
    """Conservative Persian normalization used only for category matching."""
    value = unicodedata.normalize("NFKC", value or "")
    value = value.replace("ي", "ی").replace("ك", "ک").replace("\u200c", " ").replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value).strip().lower()
    return value


def safe_stem(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_-]+", "-", value).strip("-")
    return value[:120] or "product"


def source_images_by_id() -> dict[str, Path]:
    by_id: dict[str, Path] = {}
    for path in SOURCE_IMAGE_DIR.glob("*.*"):
        match = re.match(r"^(\d+)-", path.name)
        if match:
            by_id[match.group(1)] = path
    return by_id


def make_square_webp(source: Path, destination: Path) -> tuple[int, int]:
    """Create a consistent 1200×1200 catalog image without inventing visual content."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as opened:
        image = ImageOps.exif_transpose(opened)
        if image.mode in ("RGBA", "LA"):
            canvas = Image.new("RGBA", (1200, 1200), (255, 252, 248, 255))
            contained = ImageOps.contain(image, (1080, 1080), Image.Resampling.LANCZOS)
            x = (1200 - contained.width) // 2
            y = (1200 - contained.height) // 2
            canvas.alpha_composite(contained, (x, y))
            canvas.convert("RGB").save(destination, "WEBP", quality=86, method=6)
        else:
            image = image.convert("RGB")
            canvas = Image.new("RGB", (1200, 1200), (255, 252, 248))
            contained = ImageOps.contain(image, (1080, 1080), Image.Resampling.LANCZOS)
            x = (1200 - contained.width) // 2
            y = (1200 - contained.height) // 2
            canvas.paste(contained, (x, y))
            canvas.save(destination, "WEBP", quality=86, method=6)
    return (1200, 1200)


def copy_for_product(name: str, category: str) -> tuple[str, str]:
    usage = CATEGORY_USAGE.get(category, "استفادهٔ روزمره، متناسب با نوع و برچسب محصول")
    short = f"«{name}» از محصولات منتخب عطارباشی برای {usage} است."
    full = (
        f"«{name}» در گروه «{category}» عطارباشی قرار دارد و برای {usage} انتخاب شده است. "
        "ویژگی‌های محصول را پیش از خرید با برچسب و اطلاعات به‌روزشدهٔ فروشگاه بررسی کنید.\n\n"
        "شرایط نگهداری: محصول را در ظرف دربسته، محیط خشک و خنک و دور از نور مستقیم نگه دارید. "
        "پس از باز شدن بسته، برای حفظ تازگی در زمان مناسب مصرف شود."
    )
    return short[:300], full


def existing_source(product) -> Path | None:
    if product.image_file and getattr(product.image_file, "name", ""):
        candidate = MEDIA_ROOT / product.image_file.name
        if candidate.is_file():
            return candidate
    if product.image:
        candidate = PROJECT_ROOT / "static" / product.image
        if candidate.is_file():
            return candidate
    return None


def main() -> None:
    if not MANIFEST_PATH.is_file():
        raise SystemExit(f"Manifest not found: {MANIFEST_PATH}")
    if not SOURCE_IMAGE_DIR.is_dir():
        raise SystemExit(f"Image directory not found: {SOURCE_IMAGE_DIR}")

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    sys.path.insert(0, str(PROJECT_ROOT))
    import django

    django.setup()
    from django.db import transaction
    from shop.models import Category, Product

    with MANIFEST_PATH.open(encoding="utf-8-sig", newline="") as manifest_file:
        manifest = list(csv.DictReader(manifest_file))
    if not manifest or set(manifest[0]) != {"id", "name", "category", "slug", "base_image", "file"}:
        raise SystemExit("Unexpected manifest columns or empty manifest.")

    source_by_id = source_images_by_id()
    missing_sources = [row for row in manifest if row["id"] not in source_by_id]
    if missing_sources:
        examples = ", ".join(f"#{row['id']} {row['name']}" for row in missing_sources[:5])
        raise SystemExit(f"Missing images for {len(missing_sources)} manifest rows: {examples}")

    categories_by_name = {canon(c.name): c for c in Category.objects.all()}
    missing_categories = sorted({row["category"] for row in manifest if canon(row["category"]) not in categories_by_name})
    if missing_categories:
        raise SystemExit(f"Missing categories in site database: {', '.join(missing_categories)}")

    initial_products = list(Product.objects.select_related("category").all())
    initial_by_slug = {p.slug: p for p in initial_products}
    for manifest_id, existing_slug in MATCHED_EXISTING.items():
        if existing_slug not in initial_by_slug:
            raise SystemExit(f"Expected existing product not found for manifest #{manifest_id}: {existing_slug}")

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_path = BACKUP_DIR / "db-before-attari-import.sqlite3"
    if not backup_path.exists():
        shutil.copy2(PROJECT_ROOT / "db.sqlite3", backup_path)

    DEST_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    converted_images = 0
    image_path_by_manifest_id: dict[str, str] = {}

    # Normalize every supplied product image to a practical square WebP derivative.
    for row in manifest:
        relative = f"products/catalog/{row['id']}-{safe_stem(row['slug'])}.webp"
        output_path = MEDIA_ROOT / relative
        make_square_webp(source_by_id[row["id"]], output_path)
        image_path_by_manifest_id[row["id"]] = relative
        converted_images += 1

    created = 0
    upgraded = 0
    updated_existing_ids: set[int] = set()
    category_counts: Counter[str] = Counter()

    with transaction.atomic():
        for row in manifest:
            category = categories_by_name[canon(row["category"])]
            target = None
            if row["id"] in MATCHED_EXISTING:
                target = initial_by_slug[MATCHED_EXISTING[row["id"]]]
            else:
                target = Product.objects.filter(slug=row["slug"]).first()

            if target is None:
                target = Product(
                    name=row["name"],
                    slug=row["slug"],
                    category=category,
                    is_active=True,
                    is_popular=False,
                    is_featured=False,
                    sort_order=int(row["id"]),
                )
                created += 1
            else:
                if target.pk in {p.pk for p in initial_products}:
                    updated_existing_ids.add(target.pk)
                upgraded += 1
                target.category = category
                target.is_active = True
                target.sort_order = int(row["id"])

            # Existing names/slugs are preserved on matches; the rest get the
            # manifest's canonical name/slug.  This prevents broken old links.
            if not target.pk or row["id"] not in MATCHED_EXISTING:
                target.name = row["name"]
                target.slug = row["slug"]

            target.short_description, target.description = copy_for_product(target.name, category.name)
            target.image_file = image_path_by_manifest_id[row["id"]]
            target.save()
            category_counts[category.name] += 1

        # The remaining legacy products also receive complete product copy and a
        # normalized image; this includes all 38 original products, not only
        # those that matched manifest rows.
        for product in Product.objects.select_related("category").all():
            if product.pk in updated_existing_ids:
                continue
            # Newly created products were populated in the manifest loop.
            if product.slug in {row["slug"] for row in manifest}:
                continue
            source = existing_source(product)
            if source is None:
                raise SystemExit(f"No usable image found for existing product #{product.pk}: {product.name}")
            relative = f"products/catalog/existing-{product.pk}-{safe_stem(product.slug)}.webp"
            make_square_webp(source, MEDIA_ROOT / relative)
            product.image_file = relative
            product.short_description, product.description = copy_for_product(product.name, product.category.name)
            product.save(update_fields=["image_file", "short_description", "description", "updated_at"])
            converted_images += 1

    all_products = list(Product.objects.select_related("category").all())
    description_missing = [p for p in all_products if not p.description.strip() or not p.short_description.strip()]
    missing_images = [p for p in all_products if not p.image_file or not (MEDIA_ROOT / p.image_file.name).is_file()]
    non_square = []
    for product in all_products:
        if product.image_file and (MEDIA_ROOT / product.image_file.name).is_file():
            with Image.open(MEDIA_ROOT / product.image_file.name) as check_image:
                if check_image.size != (1200, 1200):
                    non_square.append(product)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# گزارش ورود کاتالوگ عطاری",
        "",
        f"- زمان اجرا: {datetime.now().astimezone().isoformat(timespec='seconds')}",
        f"- منبع داده: `manifest.csv` با **{len(manifest)}** ردیف و فایل ZIP تصاویر با **{len(source_by_id)}** تصویر قابل‌نگاشت.",
        f"- محصولات پیش از ورود: **{len(initial_products)}**.",
        f"- محصولات جدید ثبت‌شده: **{created}**.",
        f"- ردیف‌های منیفست که به‌عنوان به‌روزرسانی محصول موجود اعمال شدند: **{len(updated_existing_ids)}**.",
        f"- محصولات نهایی سایت: **{len(all_products)}**.",
        f"- تصویرهای بهینه‌شدهٔ ایجادشده: **{converted_images}** فایل WebP مربع ۱۲۰۰×۱۲۰۰.",
        f"- شرح کوتاه و شرح کامل ثبت‌شده: **{len(all_products) - len(description_missing)}** از **{len(all_products)}** محصول.",
        "- قیمت، موجودی و واریانت تازه ایجاد نشده‌اند؛ زیرا منیفست فقط نام، دسته و تصویر دارد. کالاهای جدید در رابط کاربری با وضعیت «تماس بگیرید / ناموجود» دیده می‌شوند تا قیمت و موجودی واقعی از پنل مدیریت ثبت شود.",
        "",
        "## تطابق‌های قطعی اعمال‌شده (بدون ایجاد محصول تکراری)",
        "",
        "| شناسهٔ منیفست | ردیف منیفست | محصول موجودِ به‌روزشده | دلیل |",
        "|---:|---|---|---|",
    ]
    manifest_by_id = {row["id"]: row for row in manifest}
    for manifest_id, slug in MATCHED_EXISTING.items():
        product = initial_by_slug[slug]
        row = manifest_by_id[manifest_id]
        lines.append(f"| {manifest_id} | {row['name']} | {product.name} | تطابق قطعی یا تفاوت نگارشی/واحد |")

    lines += [
        "",
        "## شباهت‌های احتمالیِ نیازمند تصمیم فروشگاه",
        "",
        "این موارد **ادغام نشده‌اند** تا مشخصات یا بسته‌بندی متفاوت به اشتباه حذف نشود.",
        "",
        "| محصول موجود | محصول/محصولات منیفست | شناسهٔ منیفست | دلیل عدم ادغام خودکار |",
        "|---|---|---|---|",
    ]
    for old, new, ids, note in POSSIBLE_OVERLAPS:
        lines.append(f"| {old} | {new} | {ids} | {note} |")

    lines += [
        "",
        "## پوشش دسته‌ها در منیفست",
        "",
        "| دسته | تعداد ردیف‌های منیفست |",
        "|---|---:|",
    ]
    for category, count in sorted(category_counts.items()):
        lines.append(f"| {category} | {count} |")

    lines += [
        "",
        "## کنترل کیفیت پس از ورود",
        "",
        f"- محصولات بدون توضیح: **{len(description_missing)}**",
        f"- محصولات بدون فایل تصویر: **{len(missing_images)}**",
        f"- تصویرهای خارج از ابعاد هدف ۱۲۰۰×۱۲۰۰: **{len(non_square)}**",
        f"- بکاپ دیتابیس قبل از ورود: `{backup_path.relative_to(PROJECT_ROOT)}`",
        "",
        "تمام متن‌ها با ادعاهای درمانی قطعی نوشته نشده‌اند و قبل از مصرف تخصصی، اطلاعات برچسب محصول باید ملاک قرار گیرد.",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Imported {len(manifest)} manifest rows: {created} created, {len(updated_existing_ids)} existing upgraded.")
    print(f"Final product count: {len(all_products)}")
    print(f"WebP derivatives created: {converted_images}")
    print(f"Report: {REPORT_PATH.relative_to(PROJECT_ROOT)}")
    if description_missing or missing_images or non_square:
        raise SystemExit("Post-import quality checks failed; inspect the report.")


if __name__ == "__main__":
    main()
