"""
مدل‌های فروشگاه عطارباشی — دسته، محصول، واریانت (واحد: گرم/کیلو/عدد) + نظر + سبد خرید
قیمت‌ها به تومان (عدد صحیح) ذخیره می‌شوند.
"""
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
import os

from django.contrib.auth.signals import user_logged_in
from django.db import models, transaction
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.urls import reverse
from django.utils.text import slugify

from .image_optimization import optimize_new_upload


class CategoryManager(models.Manager):
    def with_product_counts(self):
        return self.annotate(product_count=models.Count("products"))


class Category(models.Model):
    name = models.CharField("نام دسته", max_length=100, unique=True)
    slug = models.SlugField("اسلاگ", max_length=120, unique=True, allow_unicode=True)
    description = models.TextField("توضیحات", blank=True)
    icon_image = models.CharField("فایل آیکون", max_length=150, blank=True)
    is_active = models.BooleanField("فعال", default=True)
    sort_order = models.PositiveIntegerField("ترتیب نمایش", default=0)
    created_at = models.DateTimeField("ایجاد شده", auto_now_add=True)
    updated_at = models.DateTimeField("به‌روزرسانی", auto_now=True)

    objects = CategoryManager()

    class Meta:
        verbose_name = "دسته‌بندی"
        verbose_name_plural = "دسته‌بندی‌ها"
        ordering = ["sort_order", "name"]
        indexes = [
            models.Index(fields=["slug"], name="cat_slug_idx"),
            models.Index(fields=["is_active", "sort_order"], name="cat_active_sort_idx"),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name, allow_unicode=True)
            self.slug = self._unique_slug(base)
        super().save(*args, **kwargs)

    def _unique_slug(self, base: str) -> str:
        slug = base
        n = 1
        while Category.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base}-{n}"
            n += 1
        return slug

    def get_absolute_url(self):
        return reverse("shop:category", kwargs={"slug": self.slug})


class ProductManager(models.Manager):
    def active(self):
        return self.filter(is_active=True).select_related("category")

    def popular(self, limit=6):
        return self.active().filter(is_popular=True)[:limit]

    def featured(self, limit=None):
        qs = self.active().filter(is_featured=True)
        return qs[:limit] if limit else qs


class Product(models.Model):
    category = models.ForeignKey(
        Category,
        verbose_name="دسته‌بندی",
        on_delete=models.PROTECT,
        related_name="products",
    )
    name = models.CharField("نام محصول", max_length=150)
    slug = models.SlugField("اسلاگ", max_length=170, unique=True, allow_unicode=True)
    description = models.TextField("توضیحات کامل", blank=True)
    short_description = models.TextField("توضیح کوتاه", max_length=300, blank=True)
    image = models.CharField("عکس اصلی (مسیر قدیمی)", max_length=200, blank=True)
    # MEDIA upload; new admin uploads are optimized to WebP before storage.
    image_file = models.FileField("عکس (MEDIA)", upload_to="products/%Y/%m/", blank=True, null=True)
    TEMPERAMENT_CHOICES = [
        ("hot", "گرم"),
        ("cold", "سرد"),
        ("moderate", "معتدل"),
    ]
    temperament = models.CharField("طبع", max_length=10, choices=TEMPERAMENT_CHOICES, blank=True)
    is_active = models.BooleanField("فعال", default=True)
    is_popular = models.BooleanField("پرفروش/محبوب", default=False)
    is_featured = models.BooleanField("محصول پیشنهادی / ویژه", default=False)
    sort_order = models.PositiveIntegerField("ترتیب نمایش", default=0)
    created_at = models.DateTimeField("ایجاد شده", auto_now_add=True)
    updated_at = models.DateTimeField("به‌روزرسانی", auto_now=True)

    objects = ProductManager()

    class Meta:
        verbose_name = "محصول"
        verbose_name_plural = "محصولات"
        ordering = ["-is_featured", "-is_popular", "sort_order", "name"]
        indexes = [
            models.Index(fields=["slug"], name="prod_slug_idx"),
            models.Index(fields=["category", "is_active"], name="prod_cat_active_idx"),
            models.Index(fields=["is_popular", "is_active"], name="prod_pop_active_idx"),
            models.Index(fields=["is_featured", "is_active"], name="prod_feat_active_idx"),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Files uploaded from Django admin are converted to oriented WebP,
        # constrained to 1600px, and named from the Persian product title.
        # Bundled/fixture media stays as-is.
        optimize_new_upload(self.image_file, descriptive_name=self.name)
        if not self.slug:
            base = slugify(self.name, allow_unicode=True)
            self.slug = self._unique_slug(base)
        super().save(*args, **kwargs)

    def _unique_slug(self, base: str) -> str:
        slug = base
        n = 1
        while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base}-{n}"
            n += 1
        return slug

    def get_absolute_url(self):
        return reverse("shop:product_detail", kwargs={"slug": self.slug})

    @property
    def primary_variant(self):
        v = self.variants.filter(stock__gt=0).first()
        return v if v is not None else self.variants.first()

    @property
    def min_price(self):
        v = self.variants.filter(stock__gt=0).order_by("price").first()
        if v is None:
            v = self.variants.order_by("price").first()
        return v.price if v else None

    # rating & wishlist helpers
    @property
    def avg_rating(self) -> float | None:
        from django.db.models import Avg
        agg = self.reviews.filter(is_approved=True).aggregate(a=Avg("rating"))
        return round(float(agg["a"]), 1) if agg["a"] is not None else None

    @property
    def review_count(self) -> int:
        return self.reviews.filter(is_approved=True).count()

    # discount: اولین واریانتی که تخفیف دارد (برای نمایش در کارت)
    @property
    def best_discount_percent(self) -> int | None:
        for v in self.variants.all():
            if v.discount_percent:
                return int(v.discount_percent)
        return None

    # نگهداری فیلد legacy برای واریانت‌های قدیمی که unit نداشته‌اند
    @property
    def image_url(self):
        # 1) MEDIA ImageField دارد؟
        if hasattr(self, "image_file") and getattr(self, "image_file"):
            try:
                if getattr(self.image_file, "name", ""):
                    return self.image_file.url  # type: ignore
            except ValueError:
                pass
        if self.image:
            from django.templatetags.static import static
            return static(self.image)
        from django.templatetags.static import static
        return static("images/logo.jpg")


class ProductVariant(models.Model):
    """
    واریانت بسته‌بندی — واحد قابل‌تغییر: گرم / کیلوگرم / عدد
    - unit=gram → amount مثل 250 (گرم)، تبدیل مقدارها دقیق
    - unit=kilogram → amount مثل 2.5 (یا 1 اگر '1kg' در seed)
    - unit=piece → amount مثل 2 (تعداد) - برای 'بسته دو عددی' و مشابه
    قیمت همچنان تومان عدد صحیح.
    """
    UNIT_CHOICES = [
        ("gram", "گرم"),
        ("kilogram", "کیلوگرم"),
        ("piece", "عدد/بسته"),
    ]

    product = models.ForeignKey(
        Product,
        verbose_name="محصول",
        on_delete=models.CASCADE,
        related_name="variants",
    )
    # مقدار عددی بسته‌بندی (با واحد)
    amount = models.DecimalField("مقدار", max_digits=8, decimal_places=2, default=0)
    unit = models.CharField("واحد", max_length=10, choices=UNIT_CHOICES, default="gram")
    # تعداد بسته‌ها (جدا از مقدار واحدی) — برای 'بسته 2 عددی' یا کارتن چندتایی
    pack_count = models.PositiveIntegerField("تعداد بسته‌ها", default=1)
    # وزن کل (گرم) — اختیاری، برای انبار
    total_weight = models.PositiveIntegerField("وزن کل (گرم)", blank=True, null=True)
    price = models.PositiveIntegerField("قیمت (تومان)")
    # قیمت قبلی (برای محاسبه تخفیف). اگر خالی باشد تخفیفی نشان داده نمی‌شود
    compare_price = models.PositiveIntegerField("قیمت قبلی (برای تخفیف)", blank=True, null=True)
    stock = models.PositiveIntegerField("موجودی", default=0)
    is_active = models.BooleanField("فعال", default=True)
    created_at = models.DateTimeField("ایجاد شده", auto_now_add=True)
    updated_at = models.DateTimeField("به‌روزرسانی", auto_now=True)

    # --- سازگاری با قبل (seed قدیمی از pack_weight می‌خواند) ---
    @property
    def pack_weight(self) -> int:
        """سازگاری: مقدار قدیمی گرم به‌صورت int"""
        if self.unit == "kilogram":
            return int(float(self.amount) * 1000)
        if self.unit == "gram":
            return int(float(self.amount))
        return int(float(self.amount))

    class Meta:
        verbose_name = "واریانت بسته‌بندی"
        verbose_name_plural = "واریانت‌های بسته‌بندی"
        ordering = ["price"]
        indexes = [
            models.Index(fields=["product", "is_active", "stock"], name="var_prod_active_idx"),
            models.Index(fields=["price"], name="var_price_idx"),
        ]

    def __str__(self):
        return f"{self.product.name} — {self.display_weight}"

    @property
    def discount_percent(self) -> int | None:
        if not self.compare_price or self.compare_price <= self.price:
            return None
        try:
            return round(100 * (1 - self.price / self.compare_price))
        except Exception:
            return None

    @property
    def display_weight(self) -> str:
        """نمایش دوستانه: '250 گرم × 2' / '1 کیلوگرم × 4' / '2 عدد × 4'"""
        from django.contrib.humanize.templatetags.humanize import intcomma
        amt = float(self.amount)
        if amt == int(amt):
            amt_str = f"{int(amt)}"
        else:
            amt_str = f"{amt:.2f}".rstrip("0").rstrip(".")
        unit_label = dict(self.UNIT_CHOICES).get(self.unit, "")
        if self.pack_count > 1:
            return f"{amt_str} {unit_label} × {self.pack_count}"
        return f"{amt_str} {unit_label}"

    @property
    def total_grams(self) -> int:
        if self.total_weight:
            return int(self.total_weight)
        if self.unit == "kilogram":
            return int(float(self.amount) * 1000) * self.pack_count
        if self.unit == "gram":
            return int(float(self.amount)) * self.pack_count
        return 0


class Review(models.Model):
    """
    نظر خریداران — برای هر محصول، با کاربر یا نام مهمان، امتیاز ۱-۵
    """
    product = models.ForeignKey(Product, verbose_name="محصول", on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="کاربر",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviews",
    )
    guest_name = models.CharField("نام مهمان", max_length=80, blank=True)
    rating = models.PositiveSmallIntegerField("امتیاز", validators=[MinValueValidator(1), MaxValueValidator(5)], default=5)
    comment = models.TextField("متن نظر", max_length=600)
    is_approved = models.BooleanField("تأیید شده", default=True)
    created_at = models.DateTimeField("ایجاد شده", auto_now_add=True)

    class Meta:
        verbose_name = "نظر"
        verbose_name_plural = "نظرات"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["product", "is_approved", "-created_at"], name="review_prod_approved_idx"),
        ]

    def __str__(self):
        return f"{self.product.name} — {self.display_name} ({self.rating}/5)"

    @property
    def display_name(self) -> str:
        if self.user:
            return getattr(self.user, "username", str(self.user))
        return self.guest_name or "مهمان"

    @property
    def stars_html(self) -> str:
        return "★" * self.rating + "☆" * (5 - self.rating)


class ContactMessage(models.Model):
    """پیام‌های ثبت‌شده از فرم تماس؛ قابل پیگیری در پنل مدیریت."""

    CATEGORY_CHOICES = [
        ("order", "پیگیری سفارش و ارسال"),
        ("product", "پرسش درباره محصول"),
        ("support", "پشتیبانی سایت"),
        ("suggestion", "پیشنهاد یا انتقاد"),
        ("cooperation", "همکاری"),
        ("other", "سایر"),
    ]
    STATUS_CHOICES = [
        ("new", "جدید"),
        ("in_progress", "در حال پیگیری"),
        ("answered", "پاسخ داده شد"),
        ("closed", "بسته شد"),
    ]

    full_name = models.CharField("نام و نام خانوادگی", max_length=120)
    phone = models.CharField("شماره تماس", max_length=24)
    email = models.EmailField("ایمیل", blank=True)
    category = models.CharField(
        "دسته‌بندی پیام", max_length=20, choices=CATEGORY_CHOICES, default="support"
    )
    message = models.TextField("متن پیام", max_length=3000)
    status = models.CharField(
        "وضعیت رسیدگی", max_length=20, choices=STATUS_CHOICES, default="new"
    )
    created_at = models.DateTimeField("زمان ثبت", auto_now_add=True)
    updated_at = models.DateTimeField("آخرین به‌روزرسانی", auto_now=True)

    class Meta:
        verbose_name = "پیام تماس"
        verbose_name_plural = "پیام‌های تماس و پشتیبانی"
        ordering = ["status", "-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"], name="contact_status_created_idx"),
            models.Index(fields=["category", "-created_at"], name="contact_category_created_idx"),
        ]

    def __str__(self):
        return f"{self.get_category_display()} — {self.full_name}"


class Wishlist(models.Model):
    """لیست علاقه‌مندی — هر کاربر حداکثر یک سوژه‌ی محصول"""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="کاربر", on_delete=models.CASCADE, related_name="wishlists")
    product = models.ForeignKey(Product, verbose_name="محصول", on_delete=models.CASCADE, related_name="wishlisted_by")
    created_at = models.DateTimeField("ایجاد", auto_now_add=True)

    class Meta:
        verbose_name = "علاقه‌مندی"
        verbose_name_plural = "علاقه‌مندی‌ها"
        unique_together = ("user", "product")
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"], name="wish_user_created_idx")]

    def __str__(self):
        return f"{self.user} ♥ {self.product.name}"


class CartItem(models.Model):
    """
    اقلام سبد خرید کاربر — ذخیره دائمی در دیتابیس تا با خروج (Logout) و ورود مجدد پاک نشوند.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="کاربر",
        on_delete=models.CASCADE,
        related_name="cart_items",
    )
    variant = models.ForeignKey(
        ProductVariant,
        verbose_name="واریانت محصول",
        on_delete=models.CASCADE,
        related_name="user_cart_items",
    )
    quantity = models.PositiveIntegerField("تعداد", default=1)
    created_at = models.DateTimeField("تاریخ ایجاد", auto_now_add=True)
    updated_at = models.DateTimeField("به‌روزرسانی", auto_now=True)

    class Meta:
        verbose_name = "آیتم سبد خرید"
        verbose_name_plural = "اقلام سبد خرید کاربران"
        unique_together = ("user", "variant")
        indexes = [
            models.Index(fields=["user", "-updated_at"], name="cart_user_updated_idx"),
        ]

    def __str__(self):
        return f"{self.user} -> {self.variant} ({self.quantity})"


class Article(models.Model):
    """
    مقالات و وبلاگ آموزشی عطارباشی
    """
    title = models.CharField("عنوان مقاله", max_length=200)
    slug = models.SlugField("اسلاگ", max_length=220, unique=True, allow_unicode=True)
    category_name = models.CharField("دسته‌بندی موضوعی", max_length=100, default="طب سنتی و سلامتی")
    summary = models.TextField("خلاصه یا مقدمه", max_length=400)
    content = models.TextField("متن کامل مقاله")
    image = models.CharField("تصویر شاخص (مسیر استاتیک)", max_length=200, blank=True)
    image_file = models.FileField("تصویر شاخص (MEDIA)", upload_to="articles/%Y/%m/", blank=True, null=True)
    related_products = models.ManyToManyField(
        Product,
        verbose_name="محصولات مرتبط",
        related_name="related_articles",
        blank=True,
    )
    author_name = models.CharField("نویسنده", max_length=100, default="تحریریه عطارباشی")
    reading_time = models.PositiveIntegerField("مدت مطالعه (دقیقه)", default=5)
    views_count = models.PositiveIntegerField("تعداد بازدید", default=0)
    sort_order = models.PositiveIntegerField("ترتیب نمایش", default=0)
    is_published = models.BooleanField("منتشر شده", default=True)
    created_at = models.DateTimeField("تاریخ انتشار", auto_now_add=True)
    updated_at = models.DateTimeField("به‌روزرسانی", auto_now=True)

    class Meta:
        verbose_name = "مقاله"
        verbose_name_plural = "مقالات و وبلاگ"
        ordering = ["sort_order", "-created_at"]
        indexes = [
            models.Index(fields=["slug"], name="art_slug_idx"),
            models.Index(fields=["is_published", "sort_order", "-created_at"], name="art_pub_sort_idx"),
        ]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("shop:article_detail", kwargs={"slug": self.slug})

    @property
    def image_url(self) -> str:
        if self.image_file:
            try:
                if getattr(self.image_file, "name", ""):
                    return self.image_file.url
            except ValueError:
                pass
        if self.image:
            img = str(self.image).strip()
            if img.startswith("http://") or img.startswith("https://"):
                return img
            if img.startswith("/static/") or img.startswith("/media/"):
                return img
            if img.startswith("static/"):
                return f"/{img}"
            if img.startswith("media/"):
                return f"/{img}"
            if img.startswith("images/"):
                return f"/static/{img}"
            if img.startswith("products/"):
                return f"/media/{img}"
            return f"/static/images/{img}"
        return "/static/images/articles/herbal-tea-calm.webp"

    def save(self, *args, **kwargs):
        # Images uploaded through the admin are automatically converted to an
        # oriented WebP at a web-friendly maximum size and named from the
        # article title, preserving Persian words for new media paths.
        optimize_new_upload(self.image_file, descriptive_name=self.title)
        if not self.slug:
            base = slugify(self.title, allow_unicode=True)
            self.slug = self._unique_slug(base)
        super().save(*args, **kwargs)

    def _unique_slug(self, base: str) -> str:
        slug = base
        n = 1
        while Article.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base}-{n}"
            n += 1
        return slug


class Order(models.Model):
    """
    سفارشات مشتریان عطارباشی
    """
    STATUS_CHOICES = [
        ('pending', 'در انتظار پرداخت'),
        ('paid', 'پرداخت شده و در حال آماده‌سازی'),
        ('processing', 'در حال بسته‌بندی در انبار'),
        ('shipped', 'ارسال شده به اداره پست'),
        ('delivered', 'تحویل داده شده به مشتری'),
        ('cancelled', 'لغو شده'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders', verbose_name="کاربر")
    order_number = models.CharField("شماره سفارش", max_length=25, unique=True)
    postal_tracking_code = models.CharField("کد رهگیری پستی (۲۴ رقمی)", max_length=50, blank=True)
    full_name = models.CharField("نام و نام خانوادگی تحویل‌گیرنده", max_length=150)
    phone_number = models.CharField("شماره تماس", max_length=20)
    province = models.CharField("استان", max_length=80, blank=True)
    city = models.CharField("شهر", max_length=80, blank=True)
    address = models.TextField("آدرس دقیق پستی")
    postal_code = models.CharField("کد پستی", max_length=20, blank=True)
    total_price = models.PositiveIntegerField("مبلغ کل محصولات (تومان)", default=0)
    shipping_cost = models.PositiveIntegerField("هزینه ارسال (تومان)", default=35000)
    status = models.CharField("وضعیت سفارش", max_length=20, choices=STATUS_CHOICES, default='paid')
    stock_reserved = models.BooleanField("موجودی رزرو/کسر شده در انبار", default=False)
    payment_reference = models.CharField("کد رهگیری بانکی / درگاه", max_length=100, blank=True)
    notes = models.TextField("توضیحات مشتری", blank=True)
    created_at = models.DateTimeField("تاریخ ثبت سفارش", auto_now_add=True)
    updated_at = models.DateTimeField("به‌روزرسانی", auto_now=True)

    class Meta:
        verbose_name = "سفارش"
        verbose_name_plural = "سفارشات"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["order_number"], name="order_num_idx"),
            models.Index(fields=["phone_number"], name="order_phone_idx"),
            models.Index(fields=["user", "-created_at"], name="order_user_idx"),
        ]

    def __str__(self):
        return f"سفارش #{self.order_number} ({self.full_name})"

    @property
    def grand_total(self):
        return self.total_price + self.shipping_cost

    @property
    def status_label(self):
        return dict(self.STATUS_CHOICES).get(self.status, self.status)

    @property
    def status_step(self):
        # شماره مرحله برای استپر وضعیت در پیگیری سفارش (1 تا 4)
        mapping = {
            'pending': 1,
            'paid': 2,
            'processing': 2,
            'shipped': 3,
            'delivered': 4,
            'cancelled': 0,
        }
        return mapping.get(self.status, 2)

    def reserve_stock(self):
        """
        رزرو و کسر موجودی انبار برای اقلام سفارش به صورت امن، اتمیک و با قفل سطرها (select_for_update)
        از بروز خطای موجودی منفی یا خرید همزمان چند کاربر جلوگیری می‌کند.
        """
        if self.stock_reserved:
            return True
        with transaction.atomic():
            for item in self.items.select_related("variant").all():
                if item.variant_id:
                    v = ProductVariant.objects.select_for_update().filter(pk=item.variant_id).first()
                    if v:
                        if v.stock < item.quantity:
                            raise ValueError(f"موجودی «{item.product_name}» ({item.variant_weight}) کافی نیست (موجودی فعلی: {v.stock} عدد).")
                        v.stock -= item.quantity
                        v.save(update_fields=["stock"])
            self.stock_reserved = True
            Order.objects.filter(pk=self.pk).update(stock_reserved=True)
        return True

    def release_stock(self):
        """
        آزادسازی و بازگردانی موجودی به انبار در صورت لغو سفارش یا حذف
        """
        if not self.stock_reserved:
            return True
        with transaction.atomic():
            for item in self.items.select_related("variant").all():
                if item.variant_id:
                    v = ProductVariant.objects.select_for_update().filter(pk=item.variant_id).first()
                    if v:
                        v.stock += item.quantity
                        v.save(update_fields=["stock"])
            self.stock_reserved = False
            Order.objects.filter(pk=self.pk).update(stock_reserved=False)
        return True

    def save(self, *args, **kwargs):
        # بررسی تغییر وضعیت سفارش در زمان ویرایش (مثلاً تغییر وضعیت در پنل ادمین)
        if self.pk:
            old_order = Order.objects.filter(pk=self.pk).first()
            if old_order:
                # اگر وضعیت قبلاً لغو نبوده و اکنون لغو شده است -> بازگشت موجودی به انبار
                if old_order.status != "cancelled" and self.status == "cancelled":
                    self.release_stock()
                # اگر قبلاً لغو بوده و اکنون به وضعیت فعال بازگردانده شده -> رزرو مجدد موجودی
                elif old_order.status == "cancelled" and self.status != "cancelled":
                    try:
                        self.reserve_stock()
                    except ValueError:
                        pass
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.stock_reserved:
            self.release_stock()
        return super().delete(*args, **kwargs)


class OrderItem(models.Model):
    """
    اقلام سفارش
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name="سفارش")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, related_name='order_items', verbose_name="محصول")
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="واریانت")
    product_name = models.CharField("نام محصول", max_length=255)
    variant_weight = models.CharField("وزن / واریانت", max_length=60, blank=True)
    price = models.PositiveIntegerField("قیمت واحد (تومان)")
    quantity = models.PositiveIntegerField("تعداد", default=1)

    class Meta:
        verbose_name = "آیتم سفارش"
        verbose_name_plural = "اقلام سفارشات"

    def __str__(self):
        return f"{self.product_name} × {self.quantity}"

    @property
    def total_price(self):
        return self.price * self.quantity


@receiver(pre_delete, sender=Order)
def order_pre_delete(sender, instance, **kwargs):
    """
    در صورت حذف سفارش، اگر موجودی آن قبلاً کسر شده باشد به انبار برمی‌گردد.
    """
    if getattr(instance, "stock_reserved", False):
        instance.release_stock()


@receiver(user_logged_in)
def merge_guest_data_on_login(sender, request, user, **kwargs):
    """
    هنگام ثبت‌نام یا ورود به حساب:
    ۱. لیست علاقه‌مندی‌های مهمان بدون از بین رفتن، به حساب کاربری منتقل و ادغام می‌شود.
    ۲. اقلام سبد خرید مهمان با سبد خرید ذخیره‌شده کاربر در دیتابیس ادغام می‌شوند.
    """
    if not request or not user:
        return

    # ۱. انتقال و ادغام علاقه‌مندی‌های سشن مهمان
    session_wishlist = request.session.get("wishlist_ids", [])
    if session_wishlist:
        try:
            valid_prods = Product.objects.filter(id__in=session_wishlist, is_active=True)
            for prod in valid_prods:
                Wishlist.objects.get_or_create(user=user, product=prod)
        except Exception:
            pass

    # ۲. انتقال و ادغام سبد خرید سشن مهمان به دیتابیس کاربر
    session_cart = request.session.get("shop_cart")
    if isinstance(session_cart, dict) and session_cart:
        try:
            for vid_str, qty in session_cart.items():
                vid = int(vid_str)
                qty = max(1, min(int(qty), 99))
                item, created = CartItem.objects.get_or_create(
                    user=user,
                    variant_id=vid,
                    defaults={"quantity": qty},
                )
                if not created:
                    item.quantity = min(99, item.quantity + qty)
                    item.save()
            request.session["shop_cart"] = {}
            request.session.modified = True
        except Exception:
            pass

