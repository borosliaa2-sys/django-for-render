# عطارباشی — نسخهٔ آمادهٔ Railway

این نسخه برای استقرار Django روی **Railway + PostgreSQL** آماده شده است. کاتالوگ بهینه‌شدهٔ عطاری، تصاویر محصول و تنظیمات production در همین مخزن قرار دارند.

## محتوا و وضعیت کاتالوگ

- **۳۷۷ محصول**، **۱۶ دسته‌بندی** و **۴۳ واریانت قیمت/وزن قبلی**
- **۴ مقاله** از دیتابیس اولیه
- ۳۵۴ تصویر ارسالی به WebP مربع ۱۲۰۰×۱۲۰۰ تبدیل شده‌اند.
- همهٔ محصولات توضیح کوتاه و کامل دارند.
- ۳۳۹ کالای جدیدی که قیمت و موجودی‌شان در منیفست نبود، بدون قیمت/واریانت وارد شده‌اند؛ پس پیش از فروش باید قیمت و موجودی واقعی‌شان در پنل ادمین ثبت شود.
- جزئیات ورودی کاتالوگ و تشابه‌ها در `reports/catalog-import-report-fa.md` است.

## فایل‌های Railway

| فایل | کاربرد |
|---|---|
| `railway.toml` | دستور build، start و health check Railway |
| `Procfile` | دستور سازگار با محیط‌های Procfile |
| `.python-version` | Python 3.12.8 برای Railway/Nixpacks |
| `requirements.txt` | Django، Gunicorn، WhiteNoise، Postgres driver و وابستگی‌ها |
| `shop/fixtures/catalog.json` | کاتالوگ اولیه برای یک دیتابیس PostgreSQL خالی |
| `shop/management/commands/ensure_catalog.py` | بارگذاری خودکار fixture فقط وقتی هیچ محصولی وجود ندارد |

در اولین بالا آمدن سرویس، Railway این ترتیب را اجرا می‌کند: `migrate` → `ensure_catalog` → `gunicorn`.

## راه‌اندازی روی Railway

### ۱. آپلود در GitHub

ZIP را از حالت فشرده خارج کنید و محتوای پوشه را در repository خود قرار دهید. سپس Commit و Push کنید. فایل‌های زیر نباید Commit شوند:

- `.env`
- `db.sqlite3`
- `staticfiles/`

`.gitignore` برای این موارد آماده است؛ اما `media/products/catalog/` عمداً باید Commit شود، چون تصاویر کاتالوگ سایت هستند.

### ۲. ساخت سرویس و Postgres

1. در Railway یک **New Project → Deploy from GitHub Repo** بسازید و repository را انتخاب کنید.
2. در همان Project یک **PostgreSQL** اضافه کنید.
3. در سرویس Django، بخش **Variables**، متغیر `DATABASE_URL` را به متغیر Postgres وصل کنید:
   ```text
   DATABASE_URL=${{Postgres.DATABASE_URL}}
   ```
   اگر Railway هنگام اتصال خودکار آن را ایجاد کرده، فقط از درست بودن اتصال مطمئن شوید.
4. در Settings سرویس، یک Public Domain بسازید. پس از آن Railway مقدار `RAILWAY_PUBLIC_DOMAIN` را فراهم می‌کند.

### ۳. متغیرهای ضروری Railway

این متغیرها را در سرویس Django ثبت کنید:

```text
DJANGO_SECRET_KEY=<یک کلید تصادفی طولانی و محرمانه>
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=${{RAILWAY_PUBLIC_DOMAIN}}
DJANGO_CSRF_TRUSTED_ORIGINS=https://${{RAILWAY_PUBLIC_DOMAIN}}
DJANGO_SECURE_SSL_REDIRECT=1
```

برای ساخت یک کلید امن روی سیستم خود:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

> بدون `DJANGO_SECRET_KEY`، build یا startup در حالت production عمداً متوقف می‌شود تا سایت ناامن Deploy نشود.

برای دامنهٔ اختصاصی، پس از اتصال دامنه این دو مقدار را با دامنهٔ واقعی جایگزین یا کامل کنید:

```text
DJANGO_ALLOWED_HOSTS=shop.example.com,www.shop.example.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://shop.example.com,https://www.shop.example.com
```

در صورت استفاده از زرین‌پال، این‌ها را هم در Variables ثبت کنید و هرگز در GitHub قرار ندهید:

```text
ZARINPAL_MERCHANT_ID=<merchant-id واقعی>
ZARINPAL_SANDBOX=False
```

### ۴. Deploy

Railway به صورت خودکار موارد زیر را از `railway.toml` اجرا می‌کند:

```text
Build:  python manage.py collectstatic --noinput
Start:  migrate → ensure_catalog → gunicorn
```

Health check مسیر `/` است. در اولین Deploy به PostgreSQL خالی، fixture کاتالوگ بارگذاری می‌شود. در Deployهای بعدی، چون محصولات از قبل وجود دارند، داده‌ها دوباره‌نویسی نمی‌شوند.

### ۵. ساخت مدیر سایت

پس از Deploy، از Railway CLI یا Shell سرویس اجرا کنید:

```bash
python manage.py createsuperuser
```

پنل مدیریت در مسیر `/admin/` قرار دارد.

## مدیا و ماندگاری داده

تصاویر فعلیِ کاتالوگ جزو repository هستند و از مسیر `/media/products/catalog/` توسط WhiteNoise سرو می‌شوند؛ بنابراین برای تصاویر موجود نیازی به Volume ندارید.

اما فایل‌هایی که بعداً از پنل ادمین Upload شوند، روی فایل‌سیستم موقت Railway باقی می‌مانند و با redeploy ممکن است از بین بروند. برای آپلودهای آینده یکی از این گزینه‌ها را اضافه کنید:

- Railway Volume متصل به مسیر `media/`
- Object Storage سازگار با S3 / Cloudinary

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

اگر از SQLite محلی خالی استفاده کنید، `ensure_catalog` کاتالوگ را فقط یک‌بار بارگذاری می‌کند.
