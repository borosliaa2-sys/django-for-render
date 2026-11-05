# عطارباشی — نسخهٔ آمادهٔ Render + Neon

این نسخه برای استقرار Django روی **Render Web Service** و اتصال به دیتابیس **Neon PostgreSQL** آماده شده است. اتصال Neon با متغیر استاندارد `DATABASE_URL` انجام می‌شود.

## وضعیت کاتالوگ داخل پروژه

- **۳۷۷ محصول**، **۱۶ دسته‌بندی** و **۴۳ واریانت قبلی**
- **۴ مقاله** از دیتابیس اولیه
- ۳۵۴ تصویر ارسالی به WebP مربع ۱۲۰۰×۱۲۰۰ تبدیل شده‌اند.
- برای همهٔ محصولات توضیح کوتاه و کامل ثبت شده است.
- ۳۳۹ کالای جدیدی که در منیفست قیمت و موجودی نداشتند، باید پیش از فروش در پنل ادمین قیمت/موجودی واقعی بگیرند.
- گزارش ورود کاتالوگ و شباهت کالاها در `reports/catalog-import-report-fa.md` است.

## تغییرات رابط کاربری در این نسخه

- در موبایل، تصویر و تقویم Hero مخفی هستند؛ دکمه‌ها گردی ۲۵ پیکسل دارند و اندازهٔ متن Hero مطابق طراحی جدید تنظیم شده است.
- سه کاروسل پس از «محصولات پیشنهادی» افزوده شده‌اند: **ادویه و چاشنی**، **گیاهان دارویی** و **سبزیجات خشک**.
- هر کاروسل حداکثر ۱۰ محصول نخستِ فعال همان دسته را نمایش می‌دهد و به آرشیو کامل دسته لینک دارد.

## فایل‌های مخصوص Render

| فایل | کاربرد |
|---|---|
| `render.yaml` | تعریف اختیاری Render Blueprint برای Web Service |
| `build.sh` | نصب وابستگی‌ها، `collectstatic`، Migration و Seed اولیه |
| `requirements.txt` | Django، Gunicorn، WhiteNoise، PostgreSQL driver و وابستگی‌ها |
| `shop/fixtures/catalog.json` | کاتالوگ اولیه برای Neon خالی |
| `shop/management/commands/ensure_catalog.py` | Fixture را فقط زمانی وارد می‌کند که هیچ محصولی در دیتابیس نیست |

در اولین Deploy روی دیتابیس خالی، `build.sh` این ترتیب را اجرا می‌کند:

```text
pip install → collectstatic → migrate → ensure_catalog
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

### برای دامنهٔ اختصاصی در آینده

وقتی دامنهٔ شخصی اضافه کردید، هر دو مقدار را اضافه کنید:

```text
DJANGO_ALLOWED_HOSTS=shop.example.com,www.shop.example.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://shop.example.com,https://www.shop.example.com
```

در صورت استفاده از زرین‌پال، آن‌ها را نیز فقط در Environment قرار دهید:

```text
ZARINPAL_MERCHANT_ID=<merchant-id واقعی>
ZARINPAL_SANDBOX=False
```

---

## ساخت مدیر سایت

پس از Deploy، از Shell سرویس Render یا از Render CLI اجرا کنید:

```bash
python manage.py createsuperuser
```

پنل مدیریت در مسیر `/admin/` است.

## تصاویر و فایل‌های آینده

تصاویر فعلی کاتالوگ همراه repository هستند و از مسیر `/media/products/catalog/` سرو می‌شوند؛ برای آن‌ها نیاز به Volume ندارید.

اما آپلود جدید از پنل ادمین روی دیسک موقت Render ذخیره می‌شود و ممکن است با Deploy بعدی از بین برود. برای فایل‌های جدید در آینده، Render Disk یا فضای S3/Cloudinary اضافه کنید.

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
