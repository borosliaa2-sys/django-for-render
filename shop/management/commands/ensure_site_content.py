"""Keep deployment-owned icons and starter editorial content available."""

from django.core.management.base import BaseCommand

from shop.models import Article, Category


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

EXISTING_ARTICLE_IMAGES = {
    "خواص-دمنوش-آرامش-اعصاب": "images/articles/herbal-tea-calm.webp",
    "شناخت-طبع-و-مزاج-طب-سنتی": "images/articles/persian-temperament.webp",
    "خواص-سیر-ترشی-هفت-ساله": "images/articles/aged-garlic-pickle.webp",
    "فواید-میوه-خشک-و-خشکبار": "images/articles/dried-fruit-nuts.webp",
}

NEW_ARTICLES = [
    {
        "slug": "نگهداری-گیاهان-دارویی-و-ادویه",
        "title": "راهنمای نگهداری گیاهان دارویی و ادویه‌ها در خانه",
        "category_name": "آموزش نگهداری",
        "summary": "با چند نکته ساده می‌توان عطر، رنگ و کیفیت گیاهان دارویی و ادویه‌های پرمصرف را برای مدت بیشتری حفظ کرد.",
        "image": "images/articles/storing-herbs-spices.webp",
        "author_name": "تحریریه عطارباشی",
        "reading_time": 4,
        "views_count": 0,
        "is_published": True,
        "content": """
<h2>دور از نور، گرما و رطوبت</h2>
<p>بیشترین دشمن عطر و کیفیت ادویه‌ها، نور مستقیم، گرمای اجاق و رطوبت است. ظرف‌ها را در کابینتی خنک و خشک، دور از پنجره و اجاق نگه دارید تا رنگ و رایحه گیاهان دیرتر تغییر کند.</p>
<h2>ظرف مناسب انتخاب کنید</h2>
<p>شیشه‌های دردار یا قوطی‌های فلزی تمیز و کاملاً خشک انتخاب خوبی هستند. پیش از پر کردن ظرف، مطمئن شوید هیچ رطوبتی در آن باقی نمانده است؛ رطوبت می‌تواند گیاه خشک را کدر و کم‌بو کند.</p>
<h2>خرید به اندازه مصرف</h2>
<p>گیاهان و ادویه‌های معطر را بهتر است در حجم مناسب مصرف چند ماه تهیه کنید. پودرها نسبت به دانه و برگ کامل سریع‌تر عطر خود را از دست می‌دهند؛ بنابراین تا جای ممکن ادویه را نزدیک زمان مصرف آسیاب کنید.</p>
""",
    },
    {
        "slug": "دمنوش-به-لیمو-برای-عصرهای-آرام",
        "title": "دمنوش به‌لیمو؛ انتخابی خوش‌عطر برای عصرهای آرام",
        "category_name": "دمنوش و گیاهان دارویی",
        "summary": "به‌لیمو با رایحه مرکباتی و طعم ملایم خود، یکی از محبوب‌ترین انتخاب‌ها برای یک استراحت کوتاه و دلپذیر است.",
        "image": "images/articles/lemon-verbena-tea.webp",
        "author_name": "تحریریه عطارباشی",
        "reading_time": 4,
        "views_count": 0,
        "is_published": True,
        "content": """
<h2>رایحه‌ای تازه و دلنشین</h2>
<p>برگ به‌لیمو هنگام دم کشیدن رایحه‌ای لطیف و مرکباتی آزاد می‌کند. این دمنوش انتخابی خوش‌طعم برای زمانی است که می‌خواهید از نوشیدنی‌های شیرین فاصله بگیرید و چند دقیقه آرام‌تر باشید.</p>
<h2>روش دم کردن ساده</h2>
<p>برای یک فنجان، یک تا دو قاشق چای‌خوری برگ خشک به‌لیمو را با آب نزدیک به جوش ترکیب کنید و درپوش بگذارید. پس از حدود هفت تا ده دقیقه، نوشیدنی را صاف کنید. افزودن چند قطره لیموی تازه یا اندکی عسل، طعم آن را کامل‌تر می‌کند.</p>
<h2>یک نکته برای مصرف متعادل</h2>
<p>هر دمنوش گیاهی را متعادل مصرف کنید. در صورت بارداری، بیماری زمینه‌ای یا مصرف داروی ثابت، برای مصرف منظم گیاهان دارویی بهتر است با پزشک یا متخصص مشورت شود.</p>
""",
    },
    {
        "slug": "راهنمای-مصرف-عرقیات-گیاهی",
        "title": "عرقیات گیاهی را چگونه و چه زمانی مصرف کنیم؟",
        "category_name": "نوشیدنی و عرقیات",
        "summary": "کیفیت، روش نگهداری و مقدار مصرف، سه نکته کلیدی برای استفاده آگاهانه‌تر از عرقیات گیاهی هستند.",
        "image": "images/articles/herbal-distillates.webp",
        "author_name": "تحریریه عطارباشی",
        "reading_time": 5,
        "views_count": 0,
        "is_published": True,
        "content": """
<h2>انتخاب محصول شفاف و خوش‌بو</h2>
<p>عرقیات گیاهی باکیفیت معمولاً رایحه طبیعی گیاه را دارند و در بطری تمیز و دربسته نگهداری می‌شوند. برچسب محصول، تاریخ تولید و شرایط نگهداری را پیش از خرید بررسی کنید.</p>
<h2>نگهداری صحیح در خانه</h2>
<p>بطری را بعد از باز شدن در جای خنک و دور از نور مستقیم قرار دهید و همیشه در آن را محکم ببندید. استفاده از لیوان تمیز و پرهیز از برگرداندن باقی‌مانده نوشیدنی به بطری، به حفظ کیفیت کمک می‌کند.</p>
<h2>مصرف مسئولانه</h2>
<p>میزان مصرف هر عرق گیاهی یکسان نیست و به نوع گیاه، شرایط فرد و توصیه تولیدکننده بستگی دارد. برای کودکان، دوران بارداری، بیماری‌های زمینه‌ای یا مصرف دارو، پیش از مصرف منظم حتماً از پزشک یا داروساز مشورت بگیرید.</p>
""",
    },
    {
        "slug": "هفت-ادویه-برای-آشپزی-سالم",
        "title": "هفت ادویه کاربردی برای آشپزی سالم و خوش‌عطر",
        "category_name": "ادویه و چاشنی",
        "summary": "با شناخت چند ادویه ساده می‌توانید بدون افزودن چاشنی‌های آماده، طعم غذاهای روزمره را کامل‌تر و متنوع‌تر کنید.",
        "image": "images/articles/everyday-spices.webp",
        "author_name": "تحریریه عطارباشی",
        "reading_time": 5,
        "views_count": 0,
        "is_published": True,
        "content": """
<h2>ادویه را مرحله‌به‌مرحله اضافه کنید</h2>
<p>زردچوبه، دارچین، زیره، فلفل سیاه، هل، گلپر و لیموعمانی از ادویه‌های کاربردی آشپزخانه ایرانی هستند. مقدار کم و متعادل، بهترین راه برای شناخت ترکیب‌های دلخواه شماست.</p>
<h2>زمان مناسب افزودن ادویه</h2>
<p>ادویه‌های معطر مانند هل و دارچین را معمولاً در مراحل پایانی اضافه کنید تا رایحه‌شان حفظ شود. زردچوبه و زیره می‌توانند در ابتدای پخت و همراه پیاز یا روغن ملایم، عطر خود را بهتر آزاد کنند.</p>
<h2>ترکیب‌های ساده و خوش‌طعم</h2>
<p>زیره با حبوبات و برنج، دارچین با خوراک‌های شیرین یا گوشت، و لیموعمانی با خورش‌ها هماهنگی خوبی دارند. ادویه را در ظرف دربسته نگه دارید و از قرار دادن آن کنار حرارت مستقیم اجتناب کنید.</p>
""",
    },
]


class Command(BaseCommand):
    help = "Repair deployment-owned category icons and seed only missing editorial articles."

    def handle(self, *args, **options):
        repaired_icons = 0
        for category_name, icon_path in CATEGORY_ICONS.items():
            repaired_icons += Category.objects.filter(name=category_name).exclude(
                icon_image=icon_path
            ).update(icon_image=icon_path)

        repaired_article_images = 0
        for slug, image_path in EXISTING_ARTICLE_IMAGES.items():
            repaired_article_images += Article.objects.filter(slug=slug).exclude(
                image=image_path
            ).update(image=image_path, image_file="")

        created_articles = 0
        for values in NEW_ARTICLES:
            slug = values["slug"]
            _, created = Article.objects.get_or_create(slug=slug, defaults=values)
            created_articles += int(created)

        self.stdout.write(
            self.style.SUCCESS(
                "Site content ready: "
                f"{repaired_icons} category icon(s) repaired, "
                f"{repaired_article_images} article banner(s) repaired, "
                f"{created_articles} article(s) created."
            )
        )
