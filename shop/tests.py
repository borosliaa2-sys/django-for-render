from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from PIL import Image
from account.models import CustomUser
from shop.models import Article, CartItem, Category, ContactMessage, CustomerAddress, Product, ProductVariant, Order, OrderItem
from shop.cart import Cart

class ShopFullFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = CustomUser.objects.create_superuser(
            username="admin_test",
            email="admin@test.com",
            password="adminpassword123"
        )
        self.cat = Category.objects.create(name="عرقیات", slug="araghiyat")
        self.product = Product.objects.create(
            name="عرق نعناع دو آتیشه",
            slug="aragh-nana",
            category=self.cat,
            description="عرق نعناع طبیعی سنتی کاشان",
            is_active=True,
            is_featured=True
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            amount=1,
            unit="piece",
            price=65000,
            compare_price=80000,
            stock=10
        )

    def test_admin_order_changelist_view(self):
        # تست عدم بروز خطا در صفحه لیست سفارشات ادمین
        self.client.force_login(self.admin_user)
        order = Order.objects.create(
            order_number="AT-TEST01",
            postal_tracking_code="123456789012345678901234",
            full_name="کاربر تست",
            phone_number="09120000000",
            total_price=65000,
            status="pending",
            stock_reserved=True
        )
        res = self.client.get("/admin/shop/order/")
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "AT-TEST01")
        self.assertContains(res, "کسر از انبار")

    def test_stock_reservation_and_cancel_restock(self):
        # 1. مشتری اول لاگین کرده، ۳ عدد به سبد اضافه کرده و ثبت سفارش می‌کند
        self.client.force_login(self.admin_user)
        self.client.post(
            reverse("shop:cart_add", kwargs={"variant_id": self.variant.id}),
            {"quantity": 3},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        checkout_data = {
            "full_name": "علی رضایی",
            "phone_number": "09121112233",
            "province": "تهران",
            "city": "تهران",
            "address": "خیابان آزادی پلاک ۱",
        }
        res = self.client.post(reverse("shop:checkout"), checkout_data, follow=True)
        self.assertEqual(res.status_code, 200)

        # بررسی کسر آنی موجودی در دیتابیس (10 - 3 = 7)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 7)

        order = Order.objects.filter(phone_number="09121112233").first()
        self.assertIsNotNone(order)
        self.assertTrue(order.stock_reserved)

        # 2. لغو سفارش در پنل مدیریت (status -> cancelled)
        order.status = "cancelled"
        order.save()

        # بررسی بازگشت مجدد موجودی به انبار (7 + 3 = 10)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 10)
        
        order.refresh_from_db()
        self.assertFalse(order.stock_reserved)

        # 3. فعال‌سازی مجدد سفارش (status -> paid)
        order.status = "paid"
        order.save()
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 7)
        order.refresh_from_db()
        self.assertTrue(order.stock_reserved)

        # 4. حذف سفارش -> بازگشت موجودی
        order.delete()
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 10)

    def test_prevent_overselling_concurrent_orders(self):
        self.client.force_login(self.admin_user)
        self.variant.stock = 5
        self.variant.save()

        session = self.client.session
        session["shop_cart"] = {str(self.variant.id): 8}
        session.save()

        checkout_data = {
            "full_name": "خریدار اضافه",
            "phone_number": "09129990000",
            "address": "تهران",
        }
        res = self.client.post(reverse("shop:checkout"), checkout_data, follow=True)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 5)
        self.assertEqual(Order.objects.filter(phone_number="09129990000").count(), 0)

    def test_guest_checkout_redirect_and_data_preservation_on_signup(self):
        # کاربر مهمان کالا به سبد خرید و علاقه‌مندی‌ها اضافه می‌کند
        guest_client = Client()
        # ۱. افزودن به علاقه‌مندی‌ها
        guest_client.post(reverse("shop:wishlist_toggle", kwargs={"product_id": self.product.id}))
        # ۲. افزودن به سبد خرید
        guest_client.post(reverse("shop:cart_add", kwargs={"variant_id": self.variant.id}), {"quantity": 2})

        # ۳. کاربر مهمان تلاش می‌کند تسویه کند -> ریدایرکت به ثبت‌نام سریع
        res_checkout = guest_client.post(reverse("shop:checkout"), {"full_name": "مهمان"}, follow=False)
        self.assertEqual(res_checkout.status_code, 302)
        self.assertIn("/account/signup/", res_checkout.url)

        # ۴. ثبت‌نام در صفحه ثبت‌نام سریع با نام، نام خانوادگی، شماره همراه و رمز عبور ۸ کاراکتری
        signup_data = {
            "first_name": "علی",
            "last_name": "محمدی",
            "phone_number": "09123456789",
            "password1": "12345678",
            "password2": "12345678",
            "next": "/cart/?open_checkout=1"
        }
        res_signup = guest_client.post(reverse("signup"), signup_data, follow=True)
        self.assertEqual(res_signup.status_code, 200)

        # ۵. بررسی لاگین خودکار و مشخصات کاربر
        new_user = CustomUser.objects.get(phone_number="09123456789")
        self.assertEqual(new_user.first_name, "علی")
        self.assertEqual(new_user.last_name, "محمدی")
        self.assertEqual(new_user.get_full_name(), "علی محمدی")
        self.assertEqual(int(guest_client.session["_auth_user_id"]), new_user.id)

        # ۶. بررسی حفظ کامل سبد خرید در سشن و دیتابیس
        cart = Cart(res_signup.wsgi_request)
        self.assertEqual(len(cart), 2)
        self.assertEqual(cart.total_price, 65000 * 2)

        # ۷. بررسی انتقال و ذخیره خودکار علاقه‌مندی‌ها در دیتابیس برای کاربر جدید
        from shop.models import Wishlist
        self.assertTrue(Wishlist.objects.filter(user=new_user, product=self.product).exists())

        # ۸. بررسی باز شدن مودال و پر شدن خودکار نام و شماره تلفن در فرم تسویه حساب
        self.assertContains(res_signup, 'value="علی محمدی"')
        self.assertContains(res_signup, 'value="09123456789"')

    def test_cart_persists_across_logout_and_login(self):
        user_client = Client()
        user = CustomUser.objects.create_user(
            username="09120001122",
            phone_number="09120001122",
            first_name="حسین",
            last_name="رضایی",
            password="mysecretpass88"
        )
        user_client.force_login(user)

        # ۱. افزودن کالا به سبد خرید توسط کاربر لاگین‌شده
        user_client.post(reverse("shop:cart_add", kwargs={"variant_id": self.variant.id}), {"quantity": 3})
        res_cart1 = user_client.get(reverse("shop:cart_detail"))
        self.assertContains(res_cart1, "عرق نعناع دو آتیشه")
        self.assertContains(res_cart1, "3")

        # ۲. خروج از حساب (Logout)
        user_client.post(reverse("logout"))

        # سبد خرید در حالت مهمان خالی نمایش داده می‌شود
        res_logged_out = user_client.get(reverse("shop:cart_detail"))
        self.assertContains(res_logged_out, "سبد خرید شما خالی است")

        # ۳. ورود مجدد به حساب (Login)
        user_client.post(reverse("login"), {"username": "09120001122", "password": "mysecretpass88"})

        # ۴. بررسی بازگشت و بازیابی کامل سبد خرید کاربر از دیتابیس
        res_cart2 = user_client.get(reverse("shop:cart_detail"))
        self.assertContains(res_cart2, "عرق نعناع دو آتیشه")
        self.assertContains(res_cart2, "195,000")  # 3 * 65,000 = 195,000
        self.assertContains(res_cart2, "1 قلم کالا")

    def test_viewing_cancelled_order_invoice_does_not_change_status(self):
        # ساخت یک سفارش لغو شده
        order = Order.objects.create(
            user=self.admin_user,
            order_number="AT-CANCELLED01",
            postal_tracking_code="123456789012345678901234",
            full_name="کاربر تست لغو",
            phone_number="09121110000",
            total_price=65000,
            status="cancelled",
            stock_reserved=False
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            variant=self.variant,
            product_name=self.product.name,
            price=65000,
            quantity=1
        )

        self.client.force_login(self.admin_user)

        # کاربر فاکتور سفارش لغو شده را از تاریخچه سفارشات باز می‌کند
        res_invoice = self.client.get(reverse("shop:order_invoice", kwargs={"order_number": order.order_number}))
        self.assertEqual(res_invoice.status_code, 200)
        self.assertContains(res_invoice, "لغو شده")

        # بررسی قطعی عدم تغییر وضعیت سفارش در دیتابیس
        order.refresh_from_db()
        self.assertEqual(order.status, "cancelled")
        self.assertNotEqual(order.status, "paid")
        self.assertNotEqual(order.status, "processing")

    def test_tracking_never_adds_legacy_carrier_fee_to_afterpay_order(self):
        order = Order.objects.create(
            user=self.admin_user,
            order_number="AT-CARRIER-FEE",
            full_name="خریدار کرایه",
            phone_number="09120003333",
            address="اصفهان",
            shipping_method="tipax",
            shipping_cost=35000,
            total_price=65000,
            status="pending",
        )
        self.assertEqual(order.grand_total, 65000)
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("shop:order_tracking"), {"query": order.order_number})
        self.assertContains(response, "کرایه ارسال:")
        self.assertContains(response, "شرکت حمل پرداخت می")
        self.assertContains(response, "مبلغ سفارش (بدون کرایه)")
        self.assertNotContains(response, "35,000 تومان")

    def test_home_page_rendering(self):
        res = self.client.get(reverse("shop:home"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "عرق نعناع دو آتیشه")

    def test_suggested_products_view(self):
        res = self.client.get(reverse("shop:suggested"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "عرق نعناع دو آتیشه")

    def test_search_view(self):
        res = self.client.get(reverse("shop:search"), {"q": "نعناع"})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "عرق نعناع دو آتیشه")

    def test_product_detail_view(self):
        res = self.client.get(reverse("shop:product_detail", kwargs={"slug": self.product.slug}))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "عرق نعناع دو آتیشه")
        self.assertContains(res, '"@type":"Product"')
        self.assertContains(res, '"@type":"BreadcrumbList"')
        self.assertContains(res, self.cat.get_absolute_url())
        # The review labels now point at their fields and product links expose
        # server-rendered metadata for social crawlers without JavaScript.
        self.assertContains(res, 'for="id_rating"')
        self.assertContains(res, 'property="og:type" content="product"')
        self.assertContains(res, 'property="og:image" content="https://attarbashiesf.ir/static/images/logo.')

    def test_article_detail_has_social_preview_and_crawlable_share_controls(self):
        article = Article.objects.create(
            title="مقاله تست اشتراک‌گذاری",
            slug="article-share-test",
            category_name="آموزش",
            summary="توضیح کوتاه برای پیش‌نمایش اشتراک‌گذاری مقاله.",
            content="<h2>متن آزمایشی</h2><p>جزئیات مقاله آزمایشی.</p>",
            image="images/articles/herbal-tea-calm.webp",
        )
        res = self.client.get(article.get_absolute_url())
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'property="og:type" content="article"')
        self.assertContains(res, 'property="og:title" content="مقاله تست اشتراک‌گذاری | وبلاگ عطارباشی"')
        self.assertContains(res, 'property="og:image" content="https://attarbashiesf.ir/static/images/articles/herbal-tea-calm.webp"')
        self.assertContains(res, 'https://t.me/share/url?url=')
        self.assertContains(res, 'data-copy-url="https://attarbashiesf.ir/blog/article-share-test/"')
        self.assertNotContains(res, "javascript:void(0)")

    def test_wishlist_view(self):
        self.client.post(reverse("shop:wishlist_toggle", kwargs={"product_id": self.product.id}))
        res = self.client.get(reverse("shop:wishlist_list"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "عرق نعناع دو آتیشه")

    def test_article_archive_honours_admin_display_order(self):
        later = Article.objects.create(
            title="مقاله با ترتیب دیرتر", slug="article-later", category_name="آموزش",
            summary="خلاصه", content="متن", sort_order=8,
        )
        first = Article.objects.create(
            title="مقاله با ترتیب اول", slug="article-first", category_name="آموزش",
            summary="خلاصه", content="متن", sort_order=1,
        )
        res = self.client.get(reverse("shop:article_list"))
        self.assertEqual(res.status_code, 200)
        self.assertLess(res.content.find(first.title.encode()), res.content.find(later.title.encode()))
        self.client.force_login(self.admin_user)
        admin_res = self.client.get("/admin/shop/article/")
        self.assertContains(admin_res, "ترتیب نمایش")

    def test_cart_update_never_exceeds_live_stock(self):
        self.variant.stock = 2
        self.variant.save(update_fields=["stock"])
        add = self.client.post(
            reverse("shop:cart_add", kwargs={"variant_id": self.variant.id}),
            {"qty": 1, "ajax": 1}, HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(add.status_code, 200)
        update = self.client.post(
            reverse("shop:cart_update", kwargs={"variant_id": self.variant.id}),
            {"qty": 9, "ajax": 1}, HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(update.status_code, 200)
        self.assertEqual(update.json()["item_qty"], 2)
        self.assertEqual(update.json()["stock"], 2)
        # A refresh must render the same stepper, not return to an add button.
        refreshed = self.client.get(reverse("shop:home"))
        self.assertEqual(refreshed.context["cart_quantities"][str(self.variant.id)], 2)
        # The popular-products carousel uses the same server-backed quantity
        # control as the category carousels, including after a page refresh.
        self.assertContains(refreshed, 'data-cart-action-form')
        self.assertContains(refreshed, 'data-update-url')
        self.assertContains(refreshed, 'cart-stepper')

    def test_media_is_served_from_the_site_domain_and_recovers_only_on_a_local_miss(self):
        # MEDIA URLs must stay /media/... even when Cloudinary credentials are
        # configured; the browser must never receive a res.cloudinary.com URL.
        image_name = "products/test-local-media.webp"
        Product.objects.filter(pk=self.product.pk).update(image_file=image_name)
        self.product.refresh_from_db()
        self.assertEqual(self.product.image_url, f"/media/{image_name}")

        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            local_file = Path(media_root) / image_name
            local_file.parent.mkdir(parents=True)
            local_file.write_bytes(b"local-product-image")
            local_response = self.client.get(f"/media/{image_name}")
            self.assertEqual(local_response.status_code, 200)
            self.assertEqual(b"".join(local_response.streaming_content), b"local-product-image")
            self.assertIn("max-age=31536000", local_response["Cache-Control"])

            local_file.unlink()

            def recover(_name, target):
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b"recovered-product-image")
                return True

            with patch("shop.media_views._recover_from_cloudinary", side_effect=recover) as recovery:
                recovered_response = self.client.get(f"/media/{image_name}")
            self.assertEqual(recovered_response.status_code, 200)
            self.assertEqual(b"".join(recovered_response.streaming_content), b"recovered-product-image")
            recovery.assert_called_once()

    def test_responsive_media_returns_a_small_same_origin_webp(self):
        image_name = "products/test-responsive-source.webp"
        Product.objects.filter(pk=self.product.pk).update(image_file=image_name)
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            source = Path(media_root) / image_name
            source.parent.mkdir(parents=True)
            Image.new("RGB", (1200, 1200), "#c68a4b").save(source, "WEBP", quality=90)

            response = self.client.get(
                reverse("responsive_media", kwargs={"width": 160}),
                {"src": f"/media/{image_name}"},
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Content-Type"], "image/webp")
            self.assertIn("max-age=31536000", response["Cache-Control"])
            payload = b"".join(response.streaming_content)
            with Image.open(BytesIO(payload)) as derivative:
                self.assertEqual(derivative.size, (160, 160))

            unknown = self.client.get(
                reverse("responsive_media", kwargs={"width": 160}),
                {"src": "/media/not-a-known-file.webp"},
            )
            self.assertEqual(unknown.status_code, 404)

    def test_new_uploads_keep_descriptive_persian_filenames(self):
        def jpeg_upload(upload_name):
            payload = BytesIO()
            Image.new("RGB", (40, 25), "#8a4f21").save(payload, "JPEG")
            return SimpleUploadedFile(upload_name, payload.getvalue(), content_type="image/jpeg")

        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            product = Product.objects.create(
                category=self.cat,
                name="روغن سیاه دانه ممتاز",
                image_file=jpeg_upload("camera-original.JPG"),
            )
            article = Article.objects.create(
                title="خواص دمنوش به لیمو",
                category_name="آموزش",
                summary="راهنمای کوتاه",
                content="متن مقاله",
                image_file=jpeg_upload("IMG-1001.jpg"),
            )

            self.assertTrue(product.image_file.name.endswith("/روغن-سیاه-دانه-ممتاز.webp"))
            self.assertTrue(article.image_file.name.endswith("/خواص-دمنوش-به-لیمو.webp"))
            self.assertTrue((Path(media_root) / product.image_file.name).is_file())
            self.assertTrue((Path(media_root) / article.image_file.name).is_file())
            with Image.open(Path(media_root) / product.image_file.name) as optimized:
                self.assertEqual(optimized.format, "WEBP")

    def test_crawl_endpoints_and_canonical_markup_are_present(self):
        home = self.client.get(reverse("shop:home"))
        self.assertEqual(home.status_code, 200)
        self.assertContains(home, 'rel="canonical" href="https://attarbashiesf.ir/"')
        self.assertContains(home, 'type="application/ld+json"')
        self.assertContains(home, 'name="robots" content="index,follow"')
        # The source markup must use the same-origin responsive endpoint rather
        # than a Cloudinary transformation URL.
        self.assertContains(home, "/media/optimized/160/?src=")
        self.assertNotContains(home, "res.cloudinary.com")
        self.assertNotContains(home, 'class="menu-icon" aria-label=')
        self.assertContains(home, 'for="menu-btn" class="menu-icon"')
        self.assertContains(home, '<main class="all-content" id="site-main">')
        self.assertContains(home, "Vazirmatn-variable")
        self.assertNotContains(home, "Vazirmatn-Regular")

        robots = self.client.get("/robots.txt")
        self.assertEqual(robots.status_code, 200)
        self.assertContains(robots, "Sitemap: https://attarbashiesf.ir/sitemap.xml")
        self.assertContains(robots, "Disallow: /cart/")

        sitemap = self.client.get("/sitemap.xml")
        self.assertEqual(sitemap.status_code, 200)
        self.assertContains(sitemap, "<urlset")
        self.assertContains(sitemap, self.product.get_absolute_url())

    def test_custom_404_view(self):
        res = self.client.get("/a-page-that-definitely-does-not-exist/")
        self.assertEqual(res.status_code, 404)
        self.assertContains(res, "صفحه مورد نظر شما پیدا نشد", status_code=404)

    def test_checkout_displays_enabled_carriers_disabled_options_and_saved_address(self):
        CustomerAddress.objects.create(
            user=self.admin_user,
            label="خانه",
            full_name="کاربر تست",
            phone_number="09120000000",
            province="اصفهان",
            city="اصفهان",
            address="خیابان نمونه",
            is_default=True,
        )
        self.client.force_login(self.admin_user)
        self.client.post(reverse("shop:cart_add", kwargs={"variant_id": self.variant.id}), {"quantity": 1})
        response = self.client.get(reverse("shop:cart_detail"))
        self.assertContains(response, "تیپاکس")
        self.assertContains(response, "باربری")
        self.assertContains(response, "دکاپست")
        self.assertContains(response, "اسنپ‌پی — ۴ قسط")
        self.assertContains(response, "پست")
        self.assertContains(response, "خانه")
        self.assertContains(response, 'data-province="اصفهان"')
        self.assertContains(response, 'name="save_address" value="1" checked')

    @override_settings(CARD_TO_CARD_ENABLED=True, CARD_TO_CARD_NUMBER="1111222233334444")
    def test_card_to_card_order_has_two_hour_deadline_and_no_online_shipping_charge(self):
        self.client.force_login(self.admin_user)
        self.client.post(reverse("shop:cart_add", kwargs={"variant_id": self.variant.id}), {"quantity": 2})
        with patch("shop.order_views.notify_new_order") as notify_new_order:
            response = self.client.post(
                reverse("shop:checkout"),
                {
                    "full_name": "خریدار کارت",
                    "phone_number": "09121112233",
                    "province": "تهران",
                    "city": "تهران",
                    "address": "خیابان آزادی",
                    "save_address": "1",
                    "shipping_method": "freight",
                    "payment_method": "card_to_card",
                },
            )
        self.assertEqual(response.status_code, 302)
        order = Order.objects.get(phone_number="09121112233")
        self.assertEqual(order.shipping_method, "freight")
        self.assertEqual(order.payment_method, "card_to_card")
        self.assertEqual(order.shipping_cost, 0)
        self.assertEqual(order.grand_total, 130000)
        self.assertEqual(order.status, "pending")
        self.assertFalse(order.stock_reserved)
        self.assertIsNotNone(order.card_payment_deadline)
        self.assertEqual(CartItem.objects.filter(user=self.admin_user).count(), 1)
        self.assertEqual(CustomerAddress.objects.filter(user=self.admin_user).count(), 1)
        pending_invoice = self.client.get(reverse("shop:order_invoice", kwargs={"order_number": order.order_number}))
        self.assertContains(pending_invoice, "درخواست پرداخت ثبت شد")
        self.assertNotContains(pending_invoice, "کد پیگیری درگاه بانکی")

        # Only an actual paid transition removes the persisted cart.
        order.reserve_stock()
        order.status = "paid"
        order.save(update_fields=["status"])
        self.assertEqual(CartItem.objects.filter(user=self.admin_user).count(), 0)
        notify_new_order.assert_called_once_with(order)

    @override_settings(CARD_TO_CARD_ENABLED=True, CARD_TO_CARD_NUMBER="1111222233334444")
    def test_checked_save_address_does_not_create_duplicates(self):
        self.client.force_login(self.admin_user)
        self.client.post(reverse("shop:cart_add", kwargs={"variant_id": self.variant.id}), {"quantity": 1})
        data = {
            "full_name": "خریدار تکراری",
            "phone_number": "09124445566",
            "province": "تهران",
            "city": "تهران",
            "address": "کوچه آزمایش",
            "postal_code": "1234567890",
            "save_address": "1",
            "shipping_method": "tipax",
            "payment_method": "card_to_card",
        }
        with patch("shop.order_views.notify_new_order"):
            self.client.post(reverse("shop:checkout"), data)
            self.client.post(reverse("shop:checkout"), data)
        self.assertEqual(CustomerAddress.objects.filter(user=self.admin_user).count(), 1)

    def test_admin_dashboard_surfaces_receipts_and_unread_support_alerts(self):
        Order.objects.create(
            user=self.admin_user,
            order_number="AT-RECEIPT-REVIEW",
            full_name="خریدار رسید",
            phone_number="09120009999",
            address="نشانی تست",
            payment_method="card_to_card",
            status="awaiting_receipt",
            card_receipt="payment_receipts/test-receipt.png",
            total_price=65000,
        )
        ContactMessage.objects.create(
            full_name="پیام‌دهنده",
            phone="09120008888",
            category="support",
            message="این پیام هنوز در انتظار بررسی است.",
            status="new",
        )
        self.client.force_login(self.admin_user)
        response = self.client.get("/admin/")
        self.assertContains(response, "موارد نیازمند رسیدگی")
        self.assertContains(response, "1 رسید کارت‌به‌کارت")
        self.assertContains(response, "1 پیام پشتیبانی")
        self.assertContains(response, "رسید نیازمند بررسی")
        self.assertContains(response, "پیام خوانده‌نشده")

    def test_admin_order_change_displays_a_private_receipt_preview(self):
        """A receipt must not turn the staff order screen into a server error."""
        with TemporaryDirectory() as root:
            private_root = Path(root) / "private-receipts"
            with override_settings(PRIVATE_RECEIPTS_ROOT=private_root):
                order = Order.objects.create(
                    user=self.admin_user,
                    order_number="AT-ADMIN-RECEIPT",
                    full_name="خریدار رسید",
                    phone_number="09120007777",
                    address="نشانی تست",
                    payment_method="card_to_card",
                    status="awaiting_receipt",
                    total_price=65000,
                )
                image_bytes = BytesIO()
                Image.new("RGB", (24, 24), "#a84d2a").save(image_bytes, "PNG")
                order.card_receipt = SimpleUploadedFile("receipt.png", image_bytes.getvalue(), content_type="image/png")
                order.save(update_fields=["card_receipt", "updated_at"])
                self.client.force_login(self.admin_user)
                response = self.client.get(f"/admin/shop/order/{order.pk}/change/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "باز کردن تصویر با اندازه کامل")
        receipt_url = reverse("shop:view_card_receipt", kwargs={"order_number": order.order_number})
        self.assertContains(response, receipt_url)

        changelist = self.client.get("/admin/shop/order/?status__exact=awaiting_receipt")
        self.assertEqual(changelist.status_code, 200)
        self.assertContains(changelist, "نیازمند بررسی — مشاهده رسید")
        self.assertContains(changelist, receipt_url)

    def test_legacy_receipt_source_can_be_found_for_a_cloudinary_recovery_backup(self):
        from shop.management.commands.sync_bundled_media_to_cloudinary import Command

        name = "payment_receipts/2026/11/legacy-receipt.png"
        with TemporaryDirectory() as root:
            media_root = Path(root) / "media"
            private_root = Path(root) / "private-receipts"
            legacy_file = media_root / name
            legacy_file.parent.mkdir(parents=True)
            legacy_file.write_bytes(b"legacy-receipt")
            with override_settings(MEDIA_ROOT=media_root, PRIVATE_RECEIPTS_ROOT=private_root):
                order = Order(order_number="AT-LEGACY-RECEIPT", card_receipt=name)
                source, origin = Command()._local_source(
                    order.card_receipt, name, is_receipt=True
                )

        self.assertEqual(origin, "legacy")
        self.assertEqual(source, legacy_file.resolve())

    def test_private_receipt_cloudinary_backup_is_verified_or_the_local_copy_is_rolled_back(self):
        from shop.receipt_storage import PrivateReceiptStorage

        with TemporaryDirectory() as root:
            private_root = Path(root) / "private-receipts"
            with override_settings(PRIVATE_RECEIPTS_ROOT=private_root):
                storage = PrivateReceiptStorage()
                with patch("shop.receipt_storage.cloudinary_backup_enabled", return_value=True), patch(
                    "shop.receipt_storage.sync_local_file_to_cloudinary", return_value="uploaded"
                ) as sync:
                    saved = storage.save(
                        "payment_receipts/2026/11/verified.png",
                        SimpleUploadedFile("verified.png", b"verified-receipt", content_type="image/png"),
                    )
                self.assertTrue((private_root / saved).is_file())
                sync.assert_called_once_with(saved, private_root / saved)

                with patch("shop.receipt_storage.cloudinary_backup_enabled", return_value=True), patch(
                    "shop.receipt_storage.sync_local_file_to_cloudinary", side_effect=OSError("Cloudinary down")
                ):
                    with self.assertRaises(OSError):
                        storage.save(
                            "payment_receipts/2026/11/rejected.png",
                            SimpleUploadedFile("rejected.png", b"rejected-receipt", content_type="image/png"),
                        )
                self.assertFalse((private_root / "payment_receipts/2026/11/rejected.png").exists())

    def test_card_receipt_is_private_and_is_available_only_to_owner_or_staff(self):
        with TemporaryDirectory() as root:
            media_root = Path(root) / "media"
            private_root = Path(root) / "private-receipts"
            with override_settings(MEDIA_ROOT=media_root, PRIVATE_RECEIPTS_ROOT=private_root):
                order = Order.objects.create(
                    user=self.admin_user,
                    order_number="AT-PRIVATE-RECEIPT",
                    full_name="خریدار رسید خصوصی",
                    phone_number="09120007777",
                    address="نشانی تست",
                    payment_method="card_to_card",
                    status="pending",
                    total_price=65000,
                )
                image_bytes = BytesIO()
                Image.new("RGB", (24, 24), "#a84d2a").save(image_bytes, "PNG")
                upload = SimpleUploadedFile("receipt.png", image_bytes.getvalue(), content_type="image/png")
                self.client.force_login(self.admin_user)
                with patch("shop.order_views.notify_card_receipt_uploaded"):
                    upload_response = self.client.post(
                        reverse("shop:upload_card_receipt", kwargs={"order_number": order.order_number}),
                        {"receipt": upload},
                    )
                self.assertEqual(upload_response.status_code, 302)
                order.refresh_from_db()
                private_path = Path(order.card_receipt.storage.path(order.card_receipt.name))
                self.assertTrue(private_path.is_file())
                self.assertFalse((media_root / order.card_receipt.name).exists())

                owner_response = self.client.get(reverse("shop:view_card_receipt", kwargs={"order_number": order.order_number}))
                self.assertEqual(owner_response.status_code, 200)
                self.assertEqual(owner_response["Cache-Control"], "private, no-store")

                direct_response = self.client.get(f"/media/{order.card_receipt.name}")
                self.assertEqual(direct_response.status_code, 404)

                outsider = CustomUser.objects.create_user(username="outsider", phone_number="09120006666", password="testpassword123")
                self.client.force_login(outsider)
                outsider_response = self.client.get(reverse("shop:view_card_receipt", kwargs={"order_number": order.order_number}))
                self.assertEqual(outsider_response.status_code, 404)

    def test_valid_support_message_triggers_outbound_alert_after_saving(self):
        with patch("shop.views.notify_support_message") as notify_support:
            response = self.client.post(
                reverse("shop:contact"),
                {
                    "full_name": "مریم تست",
                    "phone": "09121234567",
                    "email": "",
                    "category": "support",
                    "message": "برای پیگیری سفارش کمک می‌خواهم.",
                },
            )
        self.assertEqual(response.status_code, 302)
        notify_support.assert_called_once()

    def test_cloudinary_backup_uses_a_stable_non_random_public_id(self):
        """A later sync must HEAD the exact resource uploaded on the first run."""
        import cloudinary.uploader
        from shop.cloudinary_backup import sync_local_file_to_cloudinary

        class FakeStorage:
            TAG = "media"

            def exists(self, name):
                return False

            def _prepend_prefix(self, name):
                return f"attarbashi/{name}"

            def _get_resource_type(self, name):
                return "image"

        with TemporaryDirectory() as root:
            source = Path(root) / "ai-tahini.webp"
            source.write_bytes(b"webp-image")
            with patch("shop.cloudinary_backup._remote_storage", return_value=FakeStorage()), patch(
                "cloudinary.uploader.upload"
            ) as upload:
                result = sync_local_file_to_cloudinary("products/catalog/ai-tahini.webp", source)

        self.assertEqual(result, "uploaded")
        upload.assert_called_once()
        kwargs = upload.call_args.kwargs
        self.assertEqual(kwargs["public_id"], "attarbashi/products/catalog/ai-tahini")
        self.assertEqual(kwargs["resource_type"], "image")
        self.assertFalse(kwargs["use_filename"])
        self.assertFalse(kwargs["unique_filename"])
        self.assertFalse(kwargs["overwrite"])
