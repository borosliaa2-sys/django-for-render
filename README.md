# عطارباشی — نسخهٔ آمادهٔ Render + Neon

این نسخه برای استقرار Django روی **Render Web Service** و اتصال به دیتابیس **Neon PostgreSQL** آماده شده است. اتصال Neon با متغیر استاندارد `DATABASE_URL` انجام می‌شود.

## وضعیت کاتالوگ داخل پروژه

- **۳۷۷ محصول**، **۱۶ دسته‌بندی** و **۴۳ واریانت قبلی**
- **۱۸ مقالهٔ آموزشی و کاربردی** با ۱۰ بنر WebP تازه و محصولات مرتبطِ انتخاب‌شده برای هر مقاله
- ۳۵۴ تصویر ارسالی به WebP مربع ۱۲۰۰×۱۲۰۰ تبدیل شده‌اند.
- برای همهٔ محصولات توضیح کوتاه و کامل ثبت شده است.
- ۳۳۹ کالای جدیدی که در منیفست قیمت و موجودی نداشتند، باید پیش از فروش در پنل ادمین قیمت/موجودی واقعی بگیرند.
- گزارش ورود کاتالوگ و شباهت کالاها در `reports/catalog-import-report-fa.md` است.

## تغییرات رابط کاربری در این نسخه

- در موبایل، تصویر و تقویم Hero مخفی هستند؛ دکمه‌ها گردی ۲۵ پیکسل دارند و اندازهٔ متن Hero مطابق طراحی جدید تنظیم شده است.
- چهار کاروسل پس از «محصولات پیشنهادی» افزوده شده‌اند: **ادویه و چاشنی**، **نوشیدنی و عرقیات**، **گیاهان دارویی** و **سبزیجات خشک**.
- هر کاروسل حداکثر ۱۰ محصول نخستِ فعال همان دسته را نمایش می‌دهد و به آرشیو کامل دسته لینک دارد.
- پس از کاروسل‌های محصول، چهار مقالهٔ منتخب با بنرهای WebP اختصاصی در یک کاروسل خودکار و قابل‌کنترل نمایش داده می‌شوند.
- انتخاب وزن/بسته‌بندی و جدول مشخصات محصول روی موبایل بدون اسکرول افقی نمایش داده می‌شوند؛ منوی کشویی بسته نیز دیگر سایه/کادر سفید مزاحم در لبهٔ راست صفحه ایجاد نمی‌کند. دکمه خرید موبایل جمع‌وجور است و favicon مرورگر از لوگوی فروشگاه ساخته شده است.
- فرم «تماس با ما» پیام را واقعاً در دیتابیس ذخیره می‌کند و در ادمین، بخش «پیام‌های تماس و پشتیبانی» با فیلتر دسته‌بندی و وضعیت رسیدگی قابل بررسی است.
- هر بازدید صفحهٔ مقاله با یک `F-expression` اتمیک در دیتابیس ثبت می‌شود؛ بنابراین شمارش بازدید در پاسخ همان صفحه به‌روز است و بازدیدهای همزمان باعث از دست رفتن شمارش نمی‌شوند.
- تمام آیکون‌های دسته‌بندی به WebP تبدیل شده‌اند؛ گزارش نهایی در `reports/image-optimization-report-fa.md` است.

## فایل‌های مخصوص Render

| فایل | کاربرد |
|---|---|
| `render.yaml` | تعریف اختیاری Render Blueprint برای Web Service |
| `build.sh` | نصب وابستگی‌ها، `collectstatic`، Migration و Seed اولیه |
| `requirements.txt` | Django، Gunicorn، WhiteNoise، PostgreSQL driver و وابستگی‌ها |
| `shop/fixtures/catalog.json` | کاتالوگ اولیه برای Neon خالی |
| `shop/management/commands/ensure_catalog.py` | Fixture را فقط زمانی وارد می‌کند که هیچ محصولی در دیتابیس نیست |
| `shop/management/commands/ensure_site_content.py` | مسیر آیکون‌های دسته‌بندی را در Neon قدیمی اصلاح، مقاله‌های ناقص را ایجاد و فقط متن مقاله‌های آغازینِ ویرایش‌نشده را یک‌بار بهبود می‌دهد |

در اولین Deploy روی دیتابیس خالی، `build.sh` این ترتیب را اجرا می‌کند:

```text
pip install → collectstatic → migrate → ensure_catalog → ensure_site_content
```

در Deployهای بعدی، اگر در Neon محصولی وجود داشته باشد، کاتالوگ دوباره‌نویسی نمی‌شود.

---

## روش توصیه‌شده: جایگزینی فایل‌ها در GitHub

### با Git / GitHub Desktop

1. از repository فعلی یک Clone یا Backup بگیرید.
2. ZIP را Extract کنید.
3. **محتویات** پوشهٔ `attarbashi-render-neon-ready` را، نه خود پوشه را، روی ریشهٔ repository کپی کنید و فایل‌ها را Overwrite کنید.
4. پوشهٔ مخفی `.git` repository خود را حذف نکنید.
5. در ترمینال داخل repository اجرا کنید:

```bash
git status
git add -A
git commit -m "Configure Django for Render and Neon"
git push origin main
```

اگر با Linux/macOS کار می‌کنید، پس از Extract می‌توانید از این الگو استفاده کنید:

```bash
rsync -av --delete --exclude='.git' /path/to/attarbashi-render-neon-ready/ /path/to/your-repository/
```

این کار فایل‌های Railway قبلی مانند `railway.toml` و `Procfile` را نیز حذف می‌کند. Render آن فایل‌ها را استفاده نمی‌کند؛ باقی ماندنشان هم مانع Deploy نیست، اما بهتر است پاک شوند.

### با رابط وب GitHub

می‌توانید فایل‌های ZIP را Extract کنید و تمام محتویات پوشهٔ نهایی را با **Add file → Upload files** آپلود کنید. برای حجم تصاویر کاتالوگ، روش GitHub Desktop یا `git push` مطمئن‌تر است. فایل‌های زیر را آپلود نکنید:

- `.env`
- `db.sqlite3`
- `staticfiles/`

تصاویر `media/products/catalog/` باید در repository باشند؛ `.gitignore` جدید این مسیر را نادیده نمی‌گیرد.

---

## تنظیم Render برای سرویس فعلی شما

چون شما از قبل یک Render Web Service دارید، پس از Push جدید در داشبورد Render مسیر **Service → Settings** را باز کنید و این مقادیر را ثبت کنید:

```text
Runtime:       Python
Build Command: bash build.sh
Start Command: gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers ${WEB_CONCURRENCY:-2} --timeout 120 --access-logfile - --error-logfile -
Health Check:  /
```

سپس **Manual Deploy → Deploy latest commit** را بزنید یا Auto Deploy را فعال کنید.

> اگر به‌جای سرویس فعلی، یک سرویس جدید از گزینهٔ **New → Blueprint** بسازید، Render فایل `render.yaml` را می‌خواند و این تنظیمات را خودکار اعمال می‌کند.

---

## متغیرهای محیطی Render

شما گفته‌اید `DATABASE_URL` نئون را در Render تنظیم کرده‌اید؛ آن را نگه دارید. رشتهٔ Neon معمولاً باید `sslmode=require` داشته باشد.

در **Environment** سرویس Render این موارد را بررسی یا اضافه کنید:

```text
DATABASE_URL=<Neon connection string>
DJANGO_SECRET_KEY=<کلید تصادفی بلند و محرمانه>
DJANGO_DEBUG=0
DJANGO_SECURE_SSL_REDIRECT=1
```

برای ساخت کلید امن روی سیستم خود:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### دامنهٔ پیش‌فرض Render

تا زمانی که از دامنهٔ خود Render مانند `your-service.onrender.com` استفاده می‌کنید، لازم نیست `DJANGO_ALLOWED_HOSTS` یا `DJANGO_CSRF_TRUSTED_ORIGINS` را دستی تنظیم کنید. کد، متغیر خودکار `RENDER_EXTERNAL_HOSTNAME` را تشخیص می‌دهد و دامنه را به هر دو فهرست اضافه می‌کند.

### دامنهٔ اختصاصی فعلی: `attarbashiesf.ir`

در **Environment** سرویس فعلی Render این مقادیر را ثبت کنید:

```text
DJANGO_CANONICAL_HOST=attarbashiesf.ir
DJANGO_ALLOWED_HOSTS=attarbashiesf.ir,www.attarbashiesf.ir
DJANGO_CSRF_TRUSTED_ORIGINS=https://attarbashiesf.ir,https://www.attarbashiesf.ir
```

در این پروژه، دامنهٔ اصلی بدون `www` است. پس از Deploy، بازدیدهای `www.attarbashiesf.ir` و آدرس پیش‌فرض `*.onrender.com` با حفظ مسیر و Query String به `https://attarbashiesf.ir` منتقل می‌شوند. مسیر `/healthz/` از Redirect مستثناست تا بررسی سلامت Render بدون وابستگی به دامنه انجام شود.

در صورت استفاده از زرین‌پال، آن‌ها را نیز فقط در Environment قرار دهید:

```text
ZARINPAL_MERCHANT_ID=<merchant-id واقعی>
ZARINPAL_SANDBOX=False
```

---

## ساخت مدیر سایت، حتی بدون Shell Render

`build.sh` در هر Deploy دستور امن و idempotent `ensure_superuser` را اجرا می‌کند. در Render → Environment این سه مقدار را فقط برای ایجاد اولین مدیر وارد کنید:

```text
DJANGO_SUPERUSER_USERNAME=<نام کاربری مدیر>
DJANGO_SUPERUSER_EMAIL=<ایمیل مدیر>
DJANGO_SUPERUSER_PASSWORD=<رمز طولانی و یکتا>
```

سپس یک Deploy جدید انجام دهید. حساب مدیر در Neon ساخته می‌شود و در Deployهای بعدی رمز آن بازنویسی نمی‌شود. پس از مشاهدهٔ پیام موفقیت در Build Log، متغیر `DJANGO_SUPERUSER_PASSWORD` را از Render حذف کنید. پنل مدیریت در `https://attarbashiesf.ir/admin/` است.

در سرویس‌های پولی که Shell دارند، اجرای `python manage.py createsuperuser` نیز قابل استفاده است.

## تصاویر و فایل‌های آینده

تصاویر فعلی کاتالوگ همراه repository هستند و از مسیر `/media/products/catalog/` سرو می‌شوند؛ برای آن‌ها نیاز به Volume ندارید.

هر تصویر **جدیدی** که از پنل ادمین برای محصول یا مقاله بارگذاری شود، پیش از ذخیره به WebP با کیفیت وب و حداکثر اندازهٔ ۱۶۰۰×۱۶۰۰ پیکسل تبدیل و جهت EXIF آن اصلاح می‌شود. گزارش فعلی بهینه‌سازی در `reports/image-optimization-report-fa.md` است.

اما آپلود جدید از پنل ادمین روی دیسک موقت Render ذخیره می‌شود و ممکن است با Deploy بعدی از بین برود.

### اتصال اختیاری Cloudinary برای آپلودهای جدید

این نسخه `cloudinary` و `cloudinary-storage` را دارد، اما **فقط زمانی فعال می‌شود که متغیرهای محیطی آن را در Render وارد کنید**. هیچ کلید یا آدرس محرمانه‌ای در Git یا ZIP ثبت نشده است. فایل‌های استاتیک و تصاویر فعلی کاتالوگ همچنان با WhiteNoise/Repository سرو می‌شوند؛ Cloudinary فقط مقصد `MEDIA` برای آپلودهای تازهٔ پنل ادمین است.

1. در Cloudinary از صفحهٔ **Dashboard → API Keys** مقدار API Environment variable را کپی کنید.
2. در Render → سرویس → **Environment** یک متغیر با این قالب بسازید:

```text
CLOUDINARY_URL=cloudinary://API_KEY:API_SECRET@CLOUD_NAME
CLOUDINARY_FOLDER=attarbashi
```

3. Deploy جدید انجام دهید. در Build Log، وابستگی‌ها نصب می‌شوند و از آن پس تصویر جدید محصول یا مقاله مستقیماً و با HTTPS در Cloudinary ذخیره خواهد شد.

به‌جای `CLOUDINARY_URL` می‌توانید سه متغیر `CLOUDINARY_CLOUD_NAME`، `CLOUDINARY_API_KEY` و `CLOUDINARY_API_SECRET` را جداگانه وارد کنید. تنظیم `CLOUDINARY_FOLDER` اختیاری است و پیش‌فرض آن `attarbashi` است. برای توسعهٔ محلی یا وقتی این متغیرها خالی‌اند، پروژه خودکار به ذخیره‌سازی محلی `MEDIA` برمی‌گردد.

> کلیدهای Cloudinary را فقط در Render Environment یا فایل `.env` خصوصی وارد کنید؛ هرگز آن‌ها را در GitHub، screenshot یا ticket عمومی قرار ندهید.

## اجرای محلی

```bash
python -m venv .venv
source .venv/bin/activate          # ویندوز: .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env
# در .env مقدار DJANGO_SECRET_KEY را تنظیم و DJANGO_DEBUG=1 بگذارید.
python manage.py migrate
python manage.py ensure_catalog
python manage.py runserver
```
