"""ادمین فروشگاه — Product (+MEDIA ImageField), Variant (compare_price), Review, Wishlist"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import Article, CartItem, Category, Order, OrderItem, Product, ProductVariant, Review, Wishlist


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "variant", "product_name", "variant_weight", "price", "quantity", "total_price")
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "full_name", "phone_number", "status", "stock_reserved_display", "grand_total_display", "postal_tracking_code", "created_at")
    list_filter = ("status", "stock_reserved", "created_at", "province")
    search_fields = ("order_number", "full_name", "phone_number", "postal_tracking_code", "payment_reference")
    list_editable = ("status", "postal_tracking_code")
    readonly_fields = ("order_number", "stock_reserved", "created_at", "updated_at", "payment_reference")
    inlines = [OrderItemInline]
    actions = ["cancel_and_restock_orders", "mark_as_paid", "mark_as_processing", "mark_as_shipped"]

    def grand_total_display(self, obj):
        return f"{obj.grand_total:,} تومان"
    grand_total_display.short_description = "مبلغ نهایی"

    def stock_reserved_display(self, obj):
        if obj.stock_reserved:
            return mark_safe('<span style="color:#10b981; font-weight:bold;">✓ کسر از انبار</span>')
        return mark_safe('<span style="color:#6b7280;">آزاد / برگشت‌خورده</span>')
    stock_reserved_display.short_description = "موجودی انبار"

    @admin.action(description="❌ لغو سفارش‌های انتخاب‌شده و بازگردانی موجودی به انبار")
    def cancel_and_restock_orders(self, request, queryset):
        count = 0
        for order in queryset:
            order.status = "cancelled"
            order.release_stock()
            order.save(update_fields=["status"])
            count += 1
        self.message_user(request, f"{count} سفارش لغو شد و موجودی اقلام آن‌ها به انبار بازگردانده شد.")

    @admin.action(description="✅ تغییر وضعیت به پرداخت‌شده (آماده‌سازی)")
    def mark_as_paid(self, request, queryset):
        for order in queryset:
            order.status = "paid"
            if not order.stock_reserved:
                try:
                    order.reserve_stock()
                except ValueError:
                    pass
            order.save(update_fields=["status"])
        self.message_user(request, "وضعیت سفارش‌های انتخاب‌شده به پرداخت‌شده تغییر یافت.")

    @admin.action(description="📦 تغییر وضعیت به در حال بسته‌بندی در انبار")
    def mark_as_processing(self, request, queryset):
        for order in queryset:
            order.status = "processing"
            if not order.stock_reserved:
                try:
                    order.reserve_stock()
                except ValueError:
                    pass
            order.save(update_fields=["status"])
        self.message_user(request, "وضعیت سفارش‌های انتخاب‌شده به در حال بسته‌بندی تغییر یافت.")

    @admin.action(description="🚚 تغییر وضعیت به ارسال‌شده به پست")
    def mark_as_shipped(self, request, queryset):
        queryset.update(status="shipped")
        self.message_user(request, "وضعیت سفارش‌های انتخاب‌شده به ارسال‌شده تغییر یافت.")


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ("amount", "unit", "pack_count", "price", "compare_price", "stock", "is_active")
    ordering = ("price",)
    show_change_link = True
    verbose_name = "واریانت"
    verbose_name_plural = "واریانت‌ها (واحد: گرم/کیلو/عدد + تخفیف)"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "sort_order", "product_count_display", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}
    list_editable = ("is_active", "sort_order")
    ordering = ("sort_order", "name")

    def product_count_display(self, obj):
        return obj.products.count()
    product_count_display.short_description = "تعداد محصولات"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("thumb", "name", "category", "is_active", "is_popular", "is_featured", "min_price_display", "updated_at")
    list_filter = ("category", "is_active", "is_popular", "is_featured", "temperament")
    search_fields = ("name", "slug", "description", "short_description")
    prepopulated_fields = {"slug": ("name",)}
    list_editable = ("is_active", "is_popular", "is_featured")
    readonly_fields = ("created_at", "updated_at")
    inlines = [ProductVariantInline]
    ordering = ("-is_featured", "-is_popular", "sort_order", "name")
    list_select_related = ("category",)
    fields = ("category", "name", "slug", "description", "short_description", "image", "image_file", "temperament", "is_active", "is_popular", "is_featured", "sort_order")

    def thumb(self, obj):
        url = obj.image_url
        return format_html('<img src="{}" style="width:42px;height:42px;object-fit:cover;border-radius:8px; background:#f8f8f8;">', url)
    thumb.short_description = "عکس"

    def min_price_display(self, obj):
        p = obj.min_price
        return f"{p:,} تومان" if p else "—"
    min_price_display.short_description = "حداقل قیمت"


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("product", "display_weight", "unit", "price", "compare_price", "discount_percent_display", "stock", "is_active", "updated_at")
    list_filter = ("product__category", "unit", "is_active")
    list_editable = ("price", "compare_price", "stock", "is_active")
    search_fields = ("product__name",)
    ordering = ("product__name", "price")
    list_select_related = ("product__category",)

    def discount_percent_display(self, obj):
        v = obj.discount_percent
        return f"%{v}" if v else "—"
    discount_percent_display.short_description = "تخفیف"


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "display_name", "rating", "is_approved", "created_at")
    list_filter = ("rating", "is_approved", "product__category")
    search_fields = ("product__name", "guest_name", "comment", "user__username")
    list_editable = ("is_approved",)
    ordering = ("-created_at",)
    list_select_related = ("product__category",)


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ("user", "product", "created_at")
    search_fields = ("user__username", "product__name")
    list_filter = ("user",)
    ordering = ("-created_at",)
    list_select_related = ("product__category",)


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("user", "variant", "quantity", "updated_at")
    search_fields = ("user__username", "variant__product__name")
    list_filter = ("user",)
    ordering = ("-updated_at",)
    list_select_related = ("user", "variant", "variant__product")


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("thumb", "title", "category_name", "author_name", "reading_time", "views_count", "is_published", "created_at")
    list_filter = ("category_name", "is_published", "created_at")
    search_fields = ("title", "summary", "content", "author_name")
    prepopulated_fields = {"slug": ("title",)}
    list_editable = ("is_published",)
    readonly_fields = ("thumb_preview", "views_count", "created_at", "updated_at")
    ordering = ("-created_at",)

    def thumb(self, obj):
        if obj.image_url:
            return format_html('<img src="{}" style="width:45px;height:45px;border-radius:8px;object-fit:cover;border:1px solid #ddd;" />', obj.image_url)
        return "—"
    thumb.short_description = "تصویر"

    def thumb_preview(self, obj):
        if obj.image_url:
            return format_html('<img src="{}" style="max-width:220px;max-height:160px;border-radius:10px;border:1px solid #ddd;" />', obj.image_url)
        return "تصویری ثبت نشده است."
    thumb_preview.short_description = "پیش‌نمایش تصویر شاخص"

