# 🗺️ نقشه جامع معماری و ساختار وب‌سایت عطارباشی (Attarbashi Architecture & Blueprint)

این سند شامل نقشه کامل **فرانت‌اند (Frontend)**، **بک‌اند (Backend)**، **معماری سیستم (Architecture)**، **پایگاه داده (Database ERD)** و **جریان داده‌ها (Data Flows)** فروشگاه آنلاین محصولات طبیعی و سنتی «عطارباشی» است.

---

## فهرست مطالب
1. [🏗️ معماری کلان سیستم (High-Level Architecture)](#1-معماری-کلان-سیستم)
2. [🎨 نقشه فرانت‌اند و رابط کاربری (Frontend Architecture)](#2-نقشه-فرانتاند-و-رابط-کاربری)
3. [⚙️ نقشه بک‌اند و سرویس‌ها (Backend Architecture)](#3-نقشه-بکاند-و-سرویسها)
4. [🗄️ مدل داده و روابط دیتابیس (Database ERD & Models)](#4-مدل-داده-و-روابط-دیتابیس)
5. [🌐 جدول کامل مسیرها و اندپوینت‌ها (URL Routing & Endpoints)](#5-جدول-کامل-مسیرها-و-اندپوینتها)
6. [🔄 نمودار جریان داده‌ها و فرآیندهای کلیدی (User & Data Flows)](#6-نمودار-جریان-دادهها-و-فرآیندهای-کلیدی)
7. [🛡️ ماتریس امنیت و عملکرد (Security & Performance)](#7-ماتریس-امنیت-و-عملکرد)

---

## ۱. 🏗️ معماری کلان سیستم

وب‌سایت بر پایه الگوی استاندارد **Django MTV (Model - Template - View)** با رویکرد **هیبریدی (Server-Rendered + Client-Side AJAX)** پیاده‌سازی شده است.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT (Browser / Mobile)                      │
│  - Responsive HTML5 / CSS3 (Grid & Flexbox)                                 │
│  - Vanilla JavaScript Engine (AJAX Fetch, DOM Manipulator, Event Listeners)  │
└───────────────────────────────────────▲─────────────────────────────────────┘
                                        │ (HTTP / HTTPS / JSON API)
┌───────────────────────────────────────▼─────────────────────────────────────┐
│                        DJANGO 6.1 APPLICATION SERVER                        │
│                                                                             │
│  ┌───────────────────────┐  ┌───────────────────────┐  ┌─────────────────┐  │
│  │     Middleware        │  │     Security Layer    │  │ Session Engine  │  │
│  │ (Security, CSRF, Auth)│  │ (XSS, Clickjack, HSTS)│  │ (Cart & State)  │  │
│  └───────────┬───────────┘  └───────────┬───────────┘  └────────┬────────┘  │
│              │                          │                       │           │
│  ┌───────────▼──────────────────────────▼───────────────────────▼────────┐  │
│  │                         URL ROUTER (config/urls.py)                   │  │
│  └───────┬──────────────────────────────┬────────────────────────┬───────┘  │
│          │                              │                        │          │
│  ┌───────▼───────────┐          ┌───────▼───────────┐    ┌───────▼───────┐  │
│  │    Shop App       │          │   Account App     │    │   API App     │  │
│  │ - Views & Handlers│          │ - Auth / Login    │    │ - JSON Data   │  │
│  │ - Cart Logic      │          │ - Fast Signup     │    │ - Autocomplete│  │
│  │ - Order Engine    │          │ - Custom User     │    │ - Cart Stats  │  │
│  └───────┬───────────┘          └───────┬───────────┘    └───────┬───────┘  │
│          │                              │                        │          │
│  ┌───────▼──────────────────────────────▼────────────────────────▼───────┐  │
│  │                     ORM & BUSINESS LOGIC (Models)                     │  │
│  └──────────────────────────────────────┬────────────────────────────────┘  │
└─────────────────────────────────────────┼───────────────────────────────────┘
                                          │
                        ┌─────────────────▼─────────────────┐
                        │      DATABASE & STORAGE LAYER     │
                        │  - SQLite (Dev) / Postgres (Prod) │
                        │  - Media Files (Images / Uploads) │
                        │  - Static Assets (CSS / JS / SVG) │
                        └───────────────────────────────────┘
```

---

## ۲. 🎨 نقشه فرانت‌اند و رابط کاربری

### ۲.۱. درخت قالب‌ها و ساختار کامپوننت‌ها (Templates Hierarchy)
```
templates/
├── base.html                      # قالب والد (Header, Navigation, Flash Messages, Footer)
├── home.html                      # صفحه اصلی (Hero, Categories, Popular Carousel, Trust Badges)
├── search.html                    # جستجو و فروشگاه (Double Pagination Top/Bottom, Filters Drawer, List/Grid View)
├── suggested.html                 # ویترین اختصاصی محصولات پیشنهادی و سرچ در کل محصولات با اتوکامپلیت
├── crop.html                      # صفحه جزئیات محصول (Gallery, Variants, Reviews, Related Articles)
├── cart.html                      # سبد خرید ریسپانسیو (Card Layout, AJAX Steppers, Checkout Modal)
├── wishlist.html                  # لیست علاقه‌مندی‌ها (AJAX Item Removal, Add to Cart)
├── faq.html                       # سوالات متداول (Live Search, Category Tabs, Accordion)
├── tracking.html                  # پیگیری مرسوله پستی (4-Step Visual Stepper, 24-digit Code, Postal Link)
├── payment_result.html            # فاکتور نهایی و رسید دیجیتال (Printable A4 Invoice, Success/Fail)
├── about.html                     # درباره عطارباشی (Brand Story, Quality Assurance)
├── contact.html                   # تماس با ما (Interactive Form, Location, Working Hours)
├── terms.html                     # قوانین، مقررات، حریم خصوصی و ضمانت بازگشت
├── 404.html                       # صفحه اختصاصی خطای ۴۰۴
├── 500.html                       # صفحه اختصاصی خطای سرور ۵۰۰
├── 403.html                       # صفحه اختصاصی دسترسی غیرمجاز ۴۰۳
├── blog/
│   ├── article_list.html          # لیست مقالات آموزشی (Search, Category Pills, Responsive Grid, Pagination Top/Bottom)
│   └── article_detail.html        # جزئیات مقاله (Breadcrumb, Content, Share Bar, Related Products)
├── profile/
│   └── orders.html                # پنل کاربری (Sidebar, Order History, Status Badges, Invoices)
└── registration/
    ├── login.html                 # فرم ورود سریع و زیبا
    └── signup.html                # فرم مینیمال ثبت‌نام در چند ثانیه
```

### ۲.۲. ماژول‌های CSS و استایل‌بندی (CSS Architecture)
* **`css/header.css`**: استایل هدر ثابت، دراپ‌داون آیکون کاربری بدون پرش، منوی همبرگری سایدبار موبایل، بج‌های شمارنده سبد و علاقه‌مندی.
* **`css/_category.css`**: استایل مدرن دسته‌بندی‌ها (کارت‌های سبک، تصاویر کاملاً دایره‌ای `border-radius: 50%` با افکت نوری نرم و تایپوگرافی واضح).
* **`css/_ppr.css`**: کاروسل محصولات پرفروش (اسکرول‌بار مخفی، اسکرول نرم `scroll-snap`، دکمه‌های شناور دوطرفه با اوپاسیتی کنترل‌شده و کارت «مشاهده بیشتر» در انتها).
* **صفحه‌بندی دوطرفه (`.pagination-top` & `.pagination-bottom`)**: دکمه‌های قبلی/بعدی و شماره صفحات با افکت شناور و بج صفحه فعال در بالا و پایین لیست کالاها.
* **`css/_main.css` & `css/css.css`**: استایل پایه‌ای متغیرها، پالت رنگی، ریست CSS و فونت‌های استاندارد فارسی (وزن‌های ۴۰۰ تا ۹۰۰).

### ۲.۳. موتور تعاملی جاوااسکریپت (`static/js/main.js`)
* **`toggleWishlistAjax(e, btn)`**: افزودن/حذف از لیست علاقه‌مندی بدون رفرش، تغییر آیکون قلب، آپدیت بج هدر، و نمایش توست اعلان (Toast).
* **`slideCarousel(id, dir)`**: پیمایش افقی کاروسل محصولات به چپ و راست با محاسبات دقیق جهت راست‌به‌چپ (RTL).
* **`toggleFilterDrawer()`**: باز و بسته کردن نرم کشوی فیلترها در صفحات جستجو و پیشنهادی‌ها فقط با کلیک کاربر.
* **`onSearchInput(val)`**: اتوکامپلیت زنده و سرچ پیش‌بین محصولات با واکشی از `/api/autocomplete/` همراه با تصویر کوچک، نام و دسته محصول.
* **مدیریت منوی کاربر**: پشتیبانی از کلیک، تاچ و هاور با قابلیت بسته شدن خودکار با کلیک در فضای بیرون (Click Outside).

---

## ۳. ⚙️ نقشه بک‌اند و سرویس‌ها

### ۳.۱. ماژول‌های پروژه (Django Apps)
1. **`shop` (فروشگاه، سفارش و محتوا)**:
   * مدیریت کاتالوگ محصولات، دسته‌ها و واریانت‌های وزنی/تعدادی.
   * موتور سبد خرید بر پایه سشن (`cart.py`).
   * سیستم ثبت سفارش، محاسبه مبالغ، کسر موجودی و فاکتور (`order_views.py`).
   * سامانه پیگیری پستی مرسولات با کدهای ۲۴ رقمی.
   * سیستم مقالات و وبلاگ آموزشی سلامت و طب سنتی.
   * جستجوی فراگیر در تمام محصولات در صفحات کاتالوگ و پیشنهادی‌ها.
2. **`account` (احراز هویت و کاربران)**:
   * مدل کاربر سفارشی `CustomUser` با فیلد شماره تماس و پشتیبانی از احراز هویت.
   * فرم‌های ثبت‌نام مینیمال و لاگین بهینه‌شده.
3. **`config` (هسته پیکربندی)**:
   * تنظیمات امنیتی، کش، مدیا، پایگاه داده و کنترل‌کننده‌های خطای سفارشی (`handler404`, `handler500`, `handler403`).

---

## ۴. 🗄️ مدل داده و روابط دیتابیس

```
  ┌─────────────────┐             1:N             ┌─────────────────┐
  │    Category     ├────────────────────────────►│     Product     │
  └─────────────────┘                             └────────┬────────┘
                                                           │
                      ┌────────────────────────────────────┼────────────────────────────────────┐
                      │ 1:N                                │ 1:N                                │ 1:N
                      ▼                                    ▼                                    ▼
             ┌─────────────────┐                  ┌─────────────────┐                  ┌─────────────────┐
             │ ProductVariant  │                  │     Review      │                  │    Wishlist     │
             └────────┬────────┘                  └────────┬────────┘                  └────────┬────────┘
                      │                                    │                                    │
                      │                                    │ N:1                                │ N:1
                      │                                    ▼                                    ▼
                      │                           ┌─────────────────┐                  ┌─────────────────┐
                      │                           │   CustomUser    │◄─────────────────┤      Order      │
                      │                           └─────────────────┘                  └────────┬────────┘
                      │ 1:N                                                                     │
                      ▼                                                                         │ 1:N
             ┌─────────────────┐                                                                ▼
             │    OrderItem    │◄───────────────────────────────────────────────────────────────┘
             └─────────────────┘
```

### ۴.۱. خلاصه مدل‌ها و فیلدها:
* **`Category`**: `name`, `slug`, `icon_image`, `description`, `is_active`, `sort_order`
* **`Product`**: `category (FK)`, `name`, `slug`, `temperament (طبع)`, `image`, `image_file`, `is_popular`, `is_featured`, `is_active`
* **`ProductVariant`**: `product (FK)`, `amount`, `unit`, `pack_count`, `price`, `compare_price`, `stock`, `is_active`
* **`Order`**: `user (FK)`, `order_number (AT-XXXXXX)`, `postal_tracking_code (24 رقمی)`, `full_name`, `phone_number`, `province`, `city`, `address`, `total_price`, `shipping_cost`, `status`, `payment_reference`
* **`OrderItem`**: `order (FK)`, `product (FK)`, `variant (FK)`, `product_name`, `variant_weight`, `price`, `quantity`
* **`Article`**: `title`, `slug`, `category_name`, `summary`, `content`, `image`, `image_file`, `author_name`, `reading_time`, `views_count`, `is_published`
* **`Review`**: `product (FK)`, `user (FK)`, `rating (1..5)`, `comment`, `is_approved`
* **`Wishlist`**: `user (FK)`, `product (FK)`, `created_at`

---

## ۵. 🌐 جدول کامل مسیرها و اندپوینت‌ها

| ردیف | مسیر (URL Path) | نام ویو (Route Name) | متد | شرح و عملکرد |
| :---: | :--- | :--- | :---: | :--- |
| **۱** | `/` | `shop:home` | GET | صفحه اصلی، دسته‌ها و کاروسل محصولات پرفروش |
| **۲** | `/search/` | `shop:search` | GET | صفحه جستجو و فروشگاه با فیلترهای تاگل و صفحه‌بندی دوطرفه بالا و پایین |
| **۳** | `/suggested/` | `shop:suggested` | GET | ویترین اختصاصی محصولات پیشنهادی و سرچ در کل محصولات همراه با اتوکامپلیت و صفحه‌بندی دوطرفه |
| **۴** | `/category/<slug>/` | `shop:category` | GET | محصولات یک دسته‌بندی خاص |
| **۵** | `/product/<slug>/` | `shop:product_detail` | GET/POST | جزئیات محصول، انتخاب واریانت، مقالات مرتبط و ثبت نظر |
| **۶** | `/blog/` | `shop:article_list` | GET | آرشیو مقالات و دانشنامه طب سنتی |
| **۷** | `/blog/<slug>/` | `shop:article_detail` | GET | متن کامل مقاله همراه با باکس خرید محصولات مرتبط |
| **۸** | `/cart/` | `shop:cart_detail` | GET | صفحه سبد خرید و مودال تسویه حساب نهایی |
| **۹** | `/cart/add/<variant_id>/` | `shop:cart_add` | POST | افزودن به سبد با اعتبارسنجی موجودی انبار (پشتیبانی از AJAX) |
| **۱۰** | `/cart/update/<variant_id>/` | `shop:cart_update` | POST | به‌روزرسانی تعداد قلم در سبد خرید (AJAX) |
| **۱۱** | `/cart/remove/<variant_id>/` | `shop:cart_remove` | POST | حذف یک آیتم از سبد خرید (AJAX) |
| **۱۲** | `/cart/clear/` | `shop:cart_clear` | POST | خالی کردن کامل سبد خرید |
| **۱۳** | `/checkout/` | `shop:checkout` | POST | ثبت قطعی سفارش، کسر از موجودی و هدایت به درگاه |
| **۱۴** | `/payment/verify/` | `shop:payment_verify` | GET | فاکتور دیجیتال رسمی و رسید تراکنش موفق/ناموفق |
| **۱۵** | `/tracking/` | `shop:order_tracking` | GET | رهگیری آنلاین وضعیت سفارش با استپر و کد رهگیری پست |
| **۱۶** | `/profile/orders/` | `shop:user_orders` | GET | تاریخچه سفارش‌های کاربر در پنل کاربری |
| **۱۷** | `/wishlist/` | `shop:wishlist_list` | GET | صفحه لیست علاقه‌مندی‌های کاربر |
| **۱۸** | `/wishlist/toggle/<id>/` | `shop:wishlist_toggle` | POST | تاگل علاقه‌مندی بدون رفرش صفحه (AJAX) |
| **۱۹** | `/faq/` | `shop:faq` | GET | سوالات متداول با سرچ زنده و تب‌های موضوعی |
| **۲۰** | `/about/` | `shop:about` | GET | صفحه درباره ما و تضمین اصالت کالا |
| **۲۱** | `/contact/` | `shop:contact` | GET | تماس با پشتیبانی و ساعات کاری |
| **۲۲** | `/terms/` | `shop:terms` | GET | قوانین، مقررات، حریم خصوصی و ضمانت ۷ روزه |
| **۲۳** | `/account/login/` | `login` | GET/POST | فرم ورود به حساب کاربری |
| **۲۴** | `/account/signup/` | `signup` | GET/POST | فرم ثبت‌نام سریع کاربران |
| **۲۵** | `/api/autocomplete/` | `shop:api_autocomplete` | GET | اندپوینت JSON برای سرچ پیش‌بین و زنده |

---

## ۶. 🔄 نمودار جریان داده‌ها و فرآیندهای کلیدی

### ۶.۱. چرخه خرید و تسویه حساب (Checkout & Order Lifecycle)
```
[کاربر در صفحه محصول یا سبد]
       │
       ▼ (کلیک "افزودن به سبد")
[بررسی موجودی انبار در دیتابیس ProductVariant.stock]
       ├─► [ناموجود]: ارسال پیام خطا / عدم اجازه ثبت
       └─► [موجود]: ثبت در سبد سشن (Cart) + آپدیت بج هدر بدون رفرش
               │
               ▼ (کلیک "تکمیل و پرداخت نهایی" در سبد)
       [باز شدن مودال اطلاعات گیرنده و آدرس Checkout Modal]
               │
               ▼ (تایید نهایی اطلاعات)
       [تراکنش دیتابیس Atomic Transaction]
         ├── ۱. ایجاد رکورد Order با شماره سفارش منحصربه‌فرد (AT-XXXXXX)
         ├── ۲. ایجاد رکوردهای OrderItem برای تک‌تک اقلام
         ├── ۳. کسر تعداد خریداری شده از فیلد stock واریانت‌ها
         ├── ۴. شبیه‌سازی / اتصال به درگاه پرداخت و تخصیص کد تراکنش
         └── ۵. پاک‌سازی کامل سبد خرید سشن
               │
               ▼
       [هدایت به صفحه فاکتور دیجیتال رسمی /payment/verify/]
         ├── امکان چاپ برگه فاکتور A4 (window.print)
         ├── استعلام لحظه‌ای در سامانه رهگیری مرسولات (/tracking/)
         └── ثبت در تاریخچه سفارش‌های پنل کاربری (/profile/orders/)
```

### ۶.۲. چرخه پیگیری مرسوله پستی (Tracking Lifecycle)
```
[کاربر شماره سفارش AT-XXXXXX یا شماره موبایل را وارد می‌کند]
       │
       ▼
[جستجو در ایندکس‌های دیتابیس Order]
       │
       ▼
[نمایش استپر ۴ مرحله‌ای وضعیت مرسوله]
  ├── مرحله ۱: ثبت و تایید سفارش
  ├── مرحله ۲: بسته‌بندی و آماده‌سازی در انبار
  ├── مرحله ۳: تحویل به شرکت ملی پست (نمایش کد ۲۴ رقمی + لینک tracking.post.ir)
  └── مرحله ۴: تحویل نهایی به خریدار
```

---

## ۷. 🛡️ ماتریس امنیت و عملکرد

| لایه | تکنولوژی / پیکربندی | هدف امنیتی و عملکردی |
| :--- | :--- | :--- |
| **XSS Defense** | `SESSION_COOKIE_HTTPONLY = True` | جلوگیری از دسترسی اسکریپت‌های مخرب به کوکی سشن |
| **Clickjacking** | `X_FRAME_OPTIONS = "DENY"` | جلوگیری از باز شدن سایت در iframe ناشناس |
| **MIME Sniffing** | `SECURE_CONTENT_TYPE_NOSNIFF = True` | ممانعت از تفسیر اشتباه فایل‌های چندرسانه‌ای |
| **CSRF Defense** | `{% csrf_token %}` + Middleware | محافظت از تمامی متدهای POST در فرم‌ها و AJAX |
| **SQL Injection** | Django ORM Parameterized Queries | حذف خطر تزریق کدهای مخرب SQL در جستجوها |
| **N+1 Optimization** | `select_related` & `prefetch_related` | کاهش کوئری‌های دیتابیس به ۲ الی ۳ کوئری فوق‌سریع |
| **Double Pagination** | Top & Bottom Page Navigation | دسترسی سریع به جابجایی بین صفحات بدون نیاز به اسکرول طولانی |
| **Asset Delivery** | Clean Modular CSS + Minified Icons | لود پرسرعت صفحات زیر ۲۰۰ میلی‌ثادیه |

---
*تهیه شده در چارچوب مستندسازی و معماری پروژه فروشگاه عطارباشی.*
