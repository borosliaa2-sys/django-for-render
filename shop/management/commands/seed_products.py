"""
seed_products — وزن کل در pro.txt = «موجودی کل انبار» (کل وزنی که داریم).
واحد هر واریانت از سه گزینه: گرم / کیلوگرم / عدد (قابل تغییر در ادمین).
"""
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify
from shop.models import Category, Product, ProductVariant

CATEGORY_DEFS = [
    ("آرد و مواد اولیه", "categories/category-1.webp", 10),
    ("مربا", "categories/category-2.webp", 20),
    ("دمنوش", "categories/category-3.webp", 30),
    ("لواشک", "categories/category-4.webp", 40),
    ("ترشی و شور", "categories/category-5.webp", 50),
    ("روغن ها", "categories/category-6.webp", 60),
    ("سبزیجات خشک", "categories/category-7.webp", 70),
    ("سویق و پودرهای خاص", "categories/category-8.webp", 80),
    ("نوشیدنی و عرقیات", "categories/category-9.webp", 90),
    ("میوه خشک و آجیلی", "categories/category-10.webp", 100),
    ("خشکبار و مغزیجات", "categories/category-11.webp", 110),
    ("محصولات بهداشتی", "categories/category-12.webp", 120),
    ("گیاهان دارویی", "categories/category-13.webp", 130),
    ("ادویه و چاشنی", "categories/category-14.webp", 140),
    ("شیرینی و تنقلات", "categories/category-15.webp", 150),
    ("سایر", "categories/category-16.webp", 999),
]
CATEGORY_KEYWORDS = {
    "ترشی و شور": ["ترشی", "خیارشور", "سیر ترشی", "شوری"],
    "خشکبار و مغزیجات": ["تخمه", "نخودچی", "بادام", "خلال", "پسته", "کشمش", "گندمک", "پفیلا"],
    "میوه خشک و آجیلی": ["گیلاس خشک", "میوه خشک", "آلوچه", "پر هلو", "پر گلابی", "پر کیوی", "توت خشکه", "قارا"],
    "شیرینی و تنقلات": ["نبات", "پولکی", "حلواارده", "قاوت", "تمرهندی"],
    "نوشیدنی و عرقیات": ["نسکافه", "کاپوچینو", "قهوه"],
    "سبزیجات خشک": ["تره خشک"],
    "سویق و پودرهای خاص": ["پودر سنجد", "سویق"],
    "آرد و مواد اولیه": ["آرد"],
    "ادویه و چاشنی": ["نمک دریایی", "ادویه"],
    "سایر": ["سس مایونز", "ارده", "شیره", "سه شیره", "زیتون"],
}
FA_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")

def fa_to_en(s: str) -> str:
    return s.translate(FA_DIGITS)

def parse_weight_amount_unit(raw: str):
    """
    از '1885' '1kg' '500g' '200-300' '—' -> (amount: Decimal, unit: gram/kilogram/piece)
    بازه میانگین می‌گیرد. عدد بدون واحد = گرم.
    """
    raw = fa_to_en(raw.strip().lower())
    if not raw or raw in ("-", "—", "–", "ـ", "none"):
        return (Decimal("0"), "gram")
    is_kg = "kg" in raw
    # بازه
    if "-" in raw and not raw.startswith("-"):
        parts = re.findall(r"[\d.]+", raw)
        if len(parts) >= 2:
            try:
                a, b = float(parts[0]), float(parts[1])
                avg = (a + b) / 2
                if is_kg:
                    return (Decimal(str(avg)), "kilogram")
                return (Decimal(str(int(avg))), "gram")
            except ValueError:
                pass
    nums = re.findall(r"[\d.]+", raw)
    if not nums:
        return (Decimal("0"), "gram")
    try:
        val = float(nums[0])
    except ValueError:
        return (Decimal("0"), "gram")
    if is_kg:
        return (Decimal(str(val)), "kilogram")
    # g صریح یا عدد خام -> گرم
    return (Decimal(str(int(val))), "gram")

def parse_price_to_toman(raw: str) -> int:
    raw = fa_to_en(str(raw).strip())
    if not raw or raw in ("-", "—", "ـ", "none", ""):
        return 0
    m = re.search(r"\d+", raw)
    if not m:
        return 0
    return int(m.group(0))

def guess_category(product_name: str) -> str:
    name_low = product_name.lower()
    for cat, kws in CATEGORY_KEYWORDS.items():
        for kw in kws:
            if kw.lower() in name_low:
                return cat
    return "سایر"

def ensure_categories():
    mapping = {}
    for name, icon, order in CATEGORY_DEFS:
        slug = slugify(name, allow_unicode=True)
        obj, _ = Category.objects.update_or_create(
            slug=slug,
            defaults={"name": name, "icon_image": icon, "sort_order": order, "is_active": True},
        )
        mapping[name] = obj
    return mapping

def parse_pro_txt(text: str):
    lines = [ln.strip() for ln in text.splitlines()]
    products = []
    current = None
    pending = {}
    def flush():
        nonlocal pending, current
        if current is not None and pending:
            current["variants"].append(dict(pending))
            pending = {}
    for line in lines:
        if not line:
            flush()
            continue
        if line.startswith("اسم "):
            flush()
            name = line.replace("اسم ", "", 1).strip()
            if not name:
                current = None
                continue
            current = {"name": name, "variants": []}
            products.append(current)
            pending = {}
        elif current is None:
            continue
        elif line.startswith("وزن بسته بندی"):
            if pending.get("price_raw") is not None:
                flush()
            pending["pack_weight_raw"] = line.replace("وزن بسته بندی", "", 1).strip()
        elif line.startswith("تعداد بسته ها"):
            pending["pack_count_raw"] = line.replace("تعداد بسته ها", "", 1).strip()
        elif line.startswith("وزن کل"):
            pending["total_weight_raw"] = line.replace("وزن کل", "", 1).strip()
        elif line.startswith("قیمت"):
            val = line.replace("قیمت", "", 1).strip()
            if "price_raw" in pending and pending["price_raw"] not in ("", "-", "—", "ـ"):
                if not pending.get("price_raw"):
                    pending["price_raw"] = val
                flush()
                pending["price_raw"] = val
            else:
                pending["price_raw"] = val
    flush()
    return products

def parse_inventory_grams(raw: str) -> int | None:
    """وزن کل (موجودی انبار) -> گرم یا None. برای '—' برمی‌گرداند None"""
    raw = fa_to_en(raw.strip().lower()) if raw else ""
    if not raw or raw in ("-", "—", "–", "ـ", "none"):
        return None
    # kg/g تشخیص
    is_kg = "kg" in raw
    nums = re.findall(r"[\d.]+", raw)
    if not nums:
        return None
    try:
        val = float(nums[0])
    except ValueError:
        return None
    if is_kg:
        return int(val * 1000)
    return int(val)

class Command(BaseCommand):
    help = "پرکردن دسته‌ها و محصولات از pro.txt — وزن کل = موجودی انبار"
    def add_arguments(self, parser):
        parser.add_argument("--price-factor", type=int, default=1000)
        parser.add_argument("--clear", action="store_true")
    def handle(self, *args, **options):
        price_factor = options["price_factor"]
        clear = options["clear"]
        base = Path(__file__).resolve().parents[3]
        pro_path = base / "static" / "پرو" / "pro.txt"
        img_dir = base / "static" / "پرو" / "img"
        if not pro_path.exists():
            self.stderr.write(self.style.ERROR(f"pro.txt یافت نشد: {pro_path}"))
            return
        text = pro_path.read_text(encoding="utf-8")
        parsed = parse_pro_txt(text)
        self.stdout.write(f"پارس شد: {len(parsed)} محصول")
        with transaction.atomic():
            cat_map = ensure_categories()
            if clear:
                Product.objects.all().delete()
                self.stdout.write(self.style.WARNING("محصولات پاک شدند"))
            created_products = 0
            created_variants = 0
            for idx, block in enumerate(parsed):
                name = block["name"]
                cat_name = guess_category(name)
                category = cat_map.get(cat_name) or cat_map["سایر"]
                slug = slugify(name, allow_unicode=True) or f"product-{idx}"
                base_slug = slug
                n = 1
                while Product.objects.filter(slug=slug).exists():
                    slug = f"{base_slug}-{n}"
                    n += 1
                # عکس MEDIA: فایل استاتیک را به media/products کپی و FileField پر می‌کنیم
                from django.core.files.base import ContentFile as _CF
                import shutil
                media_products_dir = base / "media" / "products"
                media_products_dir.mkdir(parents=True, exist_ok=True)
                media_rel = None
                src = img_dir / f"{name}.jpg"
                if not src.exists():
                    src2 = img_dir / f"{name.strip()}.jpg"
                    if src2.exists():
                        src = src2
                if src.exists():
                    dst = media_products_dir / f"{slug}.jpg"
                    if not dst.exists():
                        try: shutil.copy2(src, dst)
                        except Exception: media_rel = None
                    media_rel = f"products/{slug}.jpg"
                    image_field = f"پرو/img/{name}.jpg"
                else:
                    image_field = "images/logo.jpg"
                existing = Product.objects.filter(slug=slug).first() or Product.objects.filter(name=name, category=category).first()
                if existing and not clear:
                    product = existing
                    product.name = name
                    product.category = category
                    product.image = image_field
                    if media_rel: product.image_file.name = media_rel
                    product.is_active = True
                    product.is_popular = idx < 8
                    product.sort_order = idx
                    product.save()
                else:
                    product = Product.objects.create(
                        name=name, slug=slug, category=category, image=image_field,
                        image_file=(media_rel or None),
                        short_description=f"{name} — محصول عطارباشی",
                        is_active=True, is_popular=idx < 8, sort_order=idx,
                    )
                    if media_rel and (media_products_dir / f"{slug}.jpg").exists():
                        try: product.image_file.name = media_rel; product.save(update_fields=["image_file"])
                        except Exception: pass
                    created_products += 1
                if not clear:
                    product.variants.all().delete()
                # تشخیص واحد عددی: اگر نام شامل 'بسته دو عددی' بود -> piece
                force_piece = "بسته دو عددی" in name or "عدد" in name
                for v in block["variants"]:
                    pw_raw = v.get("pack_weight_raw", "") or ""
                    # عددی مثل "100" برای خلال بادام -> گرم
                    amount, unit = parse_weight_amount_unit(pw_raw)
                    if force_piece and amount == 0:
                        # قارا: '200-300' وزن هر بسته -> گرم
                        pass
                    if force_piece and "قارا" in name:
                        # قارا 200-300 گرم هر عدد، ولی واحد نمایش piece بهتر است؟ نه، گرم
                        pass
                    # اگر مقدار صفر بود و وزن کل دارد (مثل کشمش وزن کل 4.2kg) -> یک واریانت 1 کیلو
                    if amount == 0:
                        tw_for_amount = v.get("total_weight_raw", "") or ""
                        if tw_for_amount and tw_for_amount not in ("-", "—", "ـ"):
                            # محصول فله‌ای: یک واریانت 1 کیلو یا 1 عدد
                            amount, unit = Decimal("1"), "kilogram"
                        else:
                            amount, unit = Decimal("1"), "piece"
                    pc_raw = fa_to_en(v.get("pack_count_raw", "") or "").strip()
                    try:
                        pc = int(re.search(r"\d+", pc_raw).group(0)) if re.search(r"\d+", pc_raw) else 1
                    except Exception:
                        pc = 1
                    tw_raw = v.get("total_weight_raw", "") or ""
                    total_g = parse_inventory_grams(tw_raw)
                    # اگر وزن کل نامشخص و pack_count داریم، total_g را از amount*pc حساب نکن — None بگذار
                    price_num = parse_price_to_toman(v.get("price_raw", "") or "")
                    if price_num and price_num < 5000:
                        price_toman = price_num * price_factor
                    else:
                        price_toman = price_num
                    stock = pc if pc > 0 else (10 if price_toman > 0 else 0)
                    # اگر قیمت 0 بود، ناموجود
                    is_active = price_toman > 0
                    # تخفیف نمونه: 10% از محصولات به‌صورت تصادفی (برای دمو)
                    compare_price = int(price_toman * 1.18) if (idx + created_variants) % 7 == 0 and price_toman > 20000 else None
                    ProductVariant.objects.create(
                        product=product,
                        amount=amount,
                        unit=unit,
                        pack_count=pc,
                        total_weight=total_g,
                        price=price_toman if price_toman else 0,
                        compare_price=compare_price,
                        stock=stock if is_active else 0,
                        is_active=is_active,
                    )
                    created_variants += 1
            self.stdout.write(self.style.SUCCESS(f"انجام شد: {created_products} محصول جدید، {created_variants} واریانت"))
