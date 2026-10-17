"""
ویوهای فروشگاه — خانه، جستجو (امن، صفحه‌بندی، اعتبارسنجی)، جزئیات و دسته
"""
from django.contrib import messages
from django.db.models import Avg, Case, Count, IntegerField, Max, Q, QuerySet, Value, When
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.generic import DetailView, ListView, TemplateView

from .forms import ReviewForm
from .models import Article, Category, Product

MAX_Q_LENGTH = 100
ALLOWED_SORTS = {"popular", "cheap", "expensive", "newest"}


class HomeView(TemplateView):
    """صفحه خانه — دسته‌ها + محصولات محبوب"""
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["categories"] = (
            Category.objects.filter(is_active=True)
            .annotate(product_count=Count("products", filter=Q(products__is_active=True)))
            .order_by("sort_order", "name")
        )
        popular = Product.objects.filter(is_active=True, is_popular=True).select_related("category").prefetch_related("variants", "reviews")
        if not popular.exists():
            popular = Product.objects.filter(is_active=True).select_related("category").prefetch_related("variants", "reviews")[:6]
        else:
            popular = popular[:6]
        ctx["popular_products"] = popular
        return ctx


HomeVIew = HomeView


class SearchView(ListView):
    template_name = "search.html"
    context_object_name = "products"
    paginate_by = 20

    def get_queryset(self):
        params = self.request.GET
        qs: QuerySet = Product.objects.filter(is_active=True).select_related("category").prefetch_related("variants", "reviews")
        q = params.get("q", "").strip()[:MAX_Q_LENGTH]
        category_slug = params.get("category", "").strip()[:80]
        temperament = params.get("temperament", "").strip()[:20]
        sort = params.get("sort", "popular").strip()
        min_price_raw = params.get("min_price", "").strip()[:10]
        max_price_raw = params.get("max_price", "").strip()[:10]

        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(description__icontains=q)
                | Q(short_description__icontains=q)
                | Q(category__name__icontains=q)
            )
        if category_slug and Category.objects.filter(slug=category_slug).exists():
            qs = qs.filter(category__slug=category_slug)
        if temperament in ("hot", "cold", "moderate"):
            qs = qs.filter(temperament=temperament)
        if min_price_raw.isdigit():
            qs = qs.filter(variants__price__gte=int(min_price_raw)).distinct()
        if max_price_raw.isdigit():
            qs = qs.filter(variants__price__lte=int(max_price_raw)).distinct()

        # همیشه محصولات موجود در اول و محصولات ناموجود در آخر لیست
        qs = qs.annotate(
            in_stock=Max(
                Case(
                    When(variants__is_active=True, variants__stock__gt=0, then=Value(1)),
                    default=Value(0),
                    output_field=IntegerField(),
                )
            )
        )

        if sort == "cheap":
            qs = qs.order_by("-in_stock", "variants__price")
        elif sort == "expensive":
            qs = qs.order_by("-in_stock", "-variants__price")
        elif sort == "newest":
            qs = qs.order_by("-in_stock", "-created_at")
        else:
            qs = qs.order_by("-in_stock", "-is_popular", "sort_order", "name")
        return qs.distinct()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        params = self.request.GET
        q = params.get("q", "").strip()[:MAX_Q_LENGTH]
        sort = params.get("sort", "popular").strip()
        if sort not in ALLOWED_SORTS:
            sort = "popular"
        category_slug = params.get("category", "").strip()[:80]
        min_price = params.get("min_price", "").strip()[:10]
        max_price = params.get("max_price", "").strip()[:10]
        temperament = params.get("temperament", "").strip()[:20]
        if temperament not in ("hot", "cold", "moderate"):
            temperament = ""
        # view: پیش‌فرض نمایش گرید (grid) برای دسکتاپ
        view_param = params.get("view", "").strip()
        if view_param in ("grid", "list"):
            view_mode = view_param
        elif self.request.COOKIES.get("shop_view") in ("grid", "list"):
            view_mode = self.request.COOKIES.get("shop_view")
        else:
            view_mode = "grid"
        querystring_parts = []
        for k in ("q", "category", "temperament", "min_price", "max_price", "sort"):
            v = params.get(k, "").strip()
            if v:
                querystring_parts.append(f"{k}={v}")
        ctx["query"] = q
        ctx["sort"] = sort
        ctx["category_slug"] = category_slug
        ctx["min_price"] = min_price if min_price.isdigit() else ""
        ctx["max_price"] = max_price if max_price.isdigit() else ""
        ctx["temperament"] = temperament
        ctx["querystring"] = "&".join(querystring_parts)
        ctx["view"] = view_mode
        ctx["categories"] = (
            Category.objects.filter(is_active=True)
            .annotate(product_count=Count("products", filter=Q(products__is_active=True)))
            .order_by("sort_order", "name")
        )
        ctx["has_filters"] = bool(q or category_slug or temperament or min_price or max_price)
        ctx["total_count"] = ctx["paginator"].count if ("paginator" in ctx and ctx["paginator"]) else (len(ctx["products"]) if "products" in ctx and ctx["products"] else 0)
        return ctx


SearchVIew = SearchView


@method_decorator(never_cache, name="dispatch")
class ProductDetailView(DetailView):
    model = Product
    template_name = "crop.html"
    context_object_name = "product"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return Product.objects.filter(is_active=True).select_related("category").prefetch_related("variants", "reviews__user")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        product = self.object
        ctx["variants"] = product.variants.filter(is_active=True).order_by("price")
        ctx["primary_variant"] = product.variants.filter(is_active=True).order_by("price").first()
        ctx["related"] = (
            Product.objects.filter(is_active=True, category=product.category)
            .exclude(pk=product.pk)
            .select_related("category")
            .prefetch_related("variants")[:4]
        )
        approved = product.reviews.filter(is_approved=True)
        agg = approved.aggregate(a=Avg("rating"), n=Count("id"))
        ctx["avg_rating"] = round(float(agg["a"]), 1) if agg["a"] is not None else None
        ctx["review_count"] = int(agg["n"] or 0)
        ctx["reviews"] = approved.select_related("user")
        ctx["review_form"] = ReviewForm()

        # مقالات مرتبط با محصول
        words = [w for w in product.name.split() if len(w) > 2]
        art_q = Q(is_published=True)
        sub_q = Q(category_name__icontains=product.category.name) | Q(title__icontains=product.name) | Q(content__icontains=product.name)
        for w in words:
            sub_q |= Q(title__icontains=w) | Q(content__icontains=w)
        rel_arts = Article.objects.filter(art_q & sub_q).distinct()[:3]
        if not rel_arts.exists():
            rel_arts = Article.objects.filter(is_published=True).order_by("-created_at")[:3]
        ctx["related_articles"] = rel_arts

        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = ReviewForm(request.POST)
        if not form.is_valid():
            ctx = self.get_context_data()
            ctx["review_form"] = form
            messages.error(request, "لطفاً خطاهای فرم را اصلاح کنید.")
            return self.render_to_response(ctx)
        review = form.save(commit=False)
        review.product = self.object
        review.user = request.user if request.user.is_authenticated else None
        # اگر کاربر لاگین باشد، guest_name اجباری نیست
        if request.user.is_authenticated and not review.guest_name:
            review.guest_name = getattr(request.user, "username", "")
        review.is_approved = True  # در production به False تغییر بده تا مدیر تایید کند
        review.save()
        messages.success(request, "نظر شما ثبت شد. متشکریم!")
        return redirect(self.object.get_absolute_url())


class SuggestedProductsView(ListView):
    """صفحه محصولات پیشنهادی — با قابلیت جستجو در تمام محصولات و فیلترهای پیشرفته"""
    template_name = "suggested.html"
    context_object_name = "products"
    paginate_by = 20

    def get_queryset(self):
        params = self.request.GET
        q = params.get("q", "").strip()[:MAX_Q_LENGTH]
        category_slug = params.get("category", "").strip()[:80]
        temperament = params.get("temperament", "").strip()[:20]
        sort = params.get("sort", "popular").strip()
        min_price_raw = params.get("min_price", "").strip()[:10]
        max_price_raw = params.get("max_price", "").strip()[:10]

        if q:
            # در صورت جستجو، در میان تمام محصولات فعال جستجو شود
            qs = Product.objects.filter(is_active=True).select_related("category").prefetch_related("variants", "reviews")
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(description__icontains=q)
                | Q(short_description__icontains=q)
                | Q(category__name__icontains=q)
            )
        else:
            # در حالت عادی، فقط محصولات دست‌چین و پیشنهادی (is_featured) نمایش داده شوند
            qs = Product.objects.filter(is_active=True, is_featured=True).select_related("category").prefetch_related("variants", "reviews")
            if not qs.exists():
                qs = Product.objects.filter(is_active=True, is_popular=True).select_related("category").prefetch_related("variants", "reviews")
                if not qs.exists():
                    qs = Product.objects.filter(is_active=True).select_related("category").prefetch_related("variants", "reviews")

        if category_slug and Category.objects.filter(slug=category_slug).exists():
            qs = qs.filter(category__slug=category_slug)
        if temperament in ("hot", "cold", "moderate"):
            qs = qs.filter(temperament=temperament)
        if min_price_raw.isdigit():
            qs = qs.filter(variants__price__gte=int(min_price_raw)).distinct()
        if max_price_raw.isdigit():
            qs = qs.filter(variants__price__lte=int(max_price_raw)).distinct()

        # همیشه محصولات موجود اول و ناموجودها آخر
        qs = qs.annotate(
            in_stock=Max(
                Case(
                    When(variants__is_active=True, variants__stock__gt=0, then=Value(1)),
                    default=Value(0),
                    output_field=IntegerField(),
                )
            )
        )

        if sort == "cheap":
            qs = qs.order_by("-in_stock", "variants__price")
        elif sort == "expensive":
            qs = qs.order_by("-in_stock", "-variants__price")
        elif sort == "newest":
            qs = qs.order_by("-in_stock", "-created_at")
        else:
            qs = qs.order_by("-in_stock", "-is_featured", "-is_popular", "sort_order", "name")
        return qs.distinct()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        params = self.request.GET
        q = params.get("q", "").strip()[:MAX_Q_LENGTH]
        sort = params.get("sort", "popular").strip()
        if sort not in ALLOWED_SORTS:
            sort = "popular"
        category_slug = params.get("category", "").strip()[:80]
        min_price = params.get("min_price", "").strip()[:10]
        max_price = params.get("max_price", "").strip()[:10]
        temperament = params.get("temperament", "").strip()[:20]
        if temperament not in ("hot", "cold", "moderate"):
            temperament = ""
        view_param = params.get("view", "").strip()
        if view_param in ("grid", "list"):
            view_mode = view_param
        elif self.request.COOKIES.get("shop_view") in ("grid", "list"):
            view_mode = self.request.COOKIES.get("shop_view")
        else:
            view_mode = "grid"
        querystring_parts = []
        for k in ("q", "category", "temperament", "min_price", "max_price", "sort"):
            v = params.get(k, "").strip()
            if v:
                querystring_parts.append(f"{k}={v}")
        
        if q:
            ctx["page_title"] = f"جستجو: {q}"
            ctx["page_subtitle"] = f"نتایج جستجو در میان تمام محصولات برای «{q}»"
        else:
            ctx["page_title"] = "محصولات پیشنهادی"
            ctx["page_subtitle"] = "محصولات برگزیده و پیشنهادی مدیریت فروشگاه عطارباشی"
            
        ctx["is_suggested_page"] = True
        ctx["query"] = q
        ctx["sort"] = sort
        ctx["category_slug"] = category_slug
        ctx["min_price"] = min_price if min_price.isdigit() else ""
        ctx["max_price"] = max_price if max_price.isdigit() else ""
        ctx["temperament"] = temperament
        ctx["querystring"] = "&".join(querystring_parts)
        ctx["view"] = view_mode
        ctx["categories"] = (
            Category.objects.filter(is_active=True)
            .annotate(product_count=Count("products", filter=Q(products__is_active=True)))
            .order_by("sort_order", "name")
        )
        ctx["has_filters"] = bool(category_slug or temperament or min_price or max_price)
        ctx["total_count"] = ctx["paginator"].count if ("paginator" in ctx and ctx["paginator"]) else (len(ctx["products"]) if "products" in ctx and ctx["products"] else 0)
        return ctx


class AboutView(TemplateView):
    template_name = "about.html"


class ContactView(TemplateView):
    template_name = "contact.html"


class TermsView(TemplateView):
    template_name = "terms.html"


class CategoryDetailView(ListView):
    template_name = "search.html"
    context_object_name = "products"
    paginate_by = 20

    def get_queryset(self):
        self.category = Category.objects.filter(slug=self.kwargs["slug"], is_active=True).first()
        if not self.category:
            return Product.objects.none()
        qs = Product.objects.filter(is_active=True, category=self.category).select_related("category").prefetch_related("variants", "reviews")
        sort = self.request.GET.get("sort", "popular").strip()

        # همیشه محصولات موجود در اول و ناموجود در آخر
        qs = qs.annotate(
            in_stock=Max(
                Case(
                    When(variants__is_active=True, variants__stock__gt=0, then=Value(1)),
                    default=Value(0),
                    output_field=IntegerField(),
                )
            )
        )

        if sort == "cheap":
            qs = qs.order_by("-in_stock", "variants__price")
        elif sort == "expensive":
            qs = qs.order_by("-in_stock", "-variants__price")
        elif sort == "newest":
            qs = qs.order_by("-in_stock", "-created_at")
        else:
            qs = qs.order_by("-in_stock", "-is_popular", "sort_order", "name")
        return qs.distinct()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        params = self.request.GET
        view_param = params.get("view", "").strip()
        view_mode = view_param if view_param in ("grid", "list") else (self.request.COOKIES.get("shop_view") or "grid")
        ctx["category"] = getattr(self, "category", None)
        ctx["query"] = ""
        ctx["sort"] = params.get("sort", "popular").strip()
        if ctx["sort"] not in ALLOWED_SORTS:
            ctx["sort"] = "popular"
        ctx["category_slug"] = self.kwargs["slug"]
        ctx["view"] = view_mode
        ctx["categories"] = (
            Category.objects.filter(is_active=True)
            .annotate(product_count=Count("products", filter=Q(products__is_active=True)))
            .order_by("sort_order", "name")
        )
        ctx["has_filters"] = True
        ctx["total_count"] = ctx["paginator"].count if ("paginator" in ctx and ctx["paginator"]) else (len(ctx["products"]) if "products" in ctx and ctx["products"] else 0)
        return ctx


class ArticleListView(ListView):
    """لیست مقالات و وبلاگ آموزشی عطارباشی"""
    model = Article
    template_name = "blog/article_list.html"
    context_object_name = "articles"
    paginate_by = 9

    def get_queryset(self):
        qs = Article.objects.filter(is_published=True).order_by("-created_at")
        q = self.request.GET.get("q", "").strip()[:MAX_Q_LENGTH]
        category = self.request.GET.get("category", "").strip()
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(summary__icontains=q) | Q(content__icontains=q))
        if category:
            qs = qs.filter(category_name=category)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["query"] = self.request.GET.get("q", "").strip()
        ctx["selected_category"] = self.request.GET.get("category", "").strip()
        ctx["categories"] = Article.objects.filter(is_published=True).values_list("category_name", flat=True).distinct()
        ctx["recent_articles"] = Article.objects.filter(is_published=True).order_by("-created_at")[:5]
        return ctx


class ArticleDetailView(DetailView):
    """جزئیات مقاله"""
    model = Article
    template_name = "blog/article_detail.html"
    context_object_name = "article"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return Article.objects.filter(is_published=True)

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        # افزایش بازدید
        Article.objects.filter(pk=obj.pk).update(views_count=obj.views_count + 1)
        return obj

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        article = self.object
        ctx["related_articles"] = (
            Article.objects.filter(is_published=True)
            .exclude(pk=article.pk)
            .order_by("-created_at")[:4]
        )
        # محصولات مرتبط با مقاله
        words = [w for w in article.title.split() if len(w) > 2]
        prod_q = Q(is_active=True)
        sub_q = Q(name__icontains=article.title) | Q(category__name__icontains=article.category_name) | Q(description__icontains=article.title)
        for w in words:
            sub_q |= Q(name__icontains=w) | Q(description__icontains=w)
        rel_prods = Product.objects.filter(prod_q & sub_q).select_related("category").prefetch_related("variants").distinct()[:4]
        if not rel_prods.exists():
            rel_prods = Product.objects.filter(is_active=True).select_related("category").prefetch_related("variants")[:4]
        ctx["related_products"] = rel_prods
        return ctx


def custom_404(request, exception=None):
    """صفحه خطای ۴۰۴ سفارشی"""
    return render(request, "404.html", status=404)


def custom_500(request):
    """صفحه خطای ۵۰۰ سفارشی"""
    return render(request, "500.html", status=500)


