"""
JSON API برای تیم فرانت — فقط خواندنی‌ها، امن (throttleniosk، whitelist).
Base: /api/
"""
import json
from typing import Any
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q
from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_GET
from .models import Category, Product, ProductVariant

MAX_Q = 100
DEFAULT_PAGE_SIZE = 12
MAX_PAGE_SIZE = 50


def _page_size(request: HttpRequest) -> int:
    try:
        n = int(request.GET.get("page_size", str(DEFAULT_PAGE_SIZE)))
    except ValueError:
        n = DEFAULT_PAGE_SIZE
    return max(1, min(n, MAX_PAGE_SIZE))

def _prod_to_dict(p: Product) -> dict[str, Any]:
    pv = p.primary_variant
    return {
        "id": p.id,
        "name": p.name,
        "slug": p.slug,
        "url": p.get_absolute_url(),
        "category": {"id": p.category_id, "name": p.category.name, "slug": p.category.slug},
        "image_url": p.image_url,
        "is_popular": p.is_popular,
        "avg_rating": p.avg_rating,
        "review_count": p.review_count,
        "best_discount_percent": p.best_discount_percent,
        "primary_variant": {
            "id": pv.id, "price": pv.price, "compare_price": pv.compare_price,
            "discount_percent": pv.discount_percent, "display_weight": pv.display_weight,
            "in_stock": pv.stock > 0,
        } if pv else None,
    }

@require_GET
def api_categories(request: HttpRequest):
    cats = Category.objects.filter(is_active=True).annotate(
        product_count=Count("products", filter=Q(products__is_active=True))
    ).order_by("sort_order", "name")
    return JsonResponse({"categories": [
        {"id": c.id, "name": c.name, "slug": c.slug, "icon_image": c.icon_image, "product_count": c.product_count}
        for c in cats
    ]})

@require_GET
def api_products(request: HttpRequest):
    qs = Product.objects.filter(is_active=True).select_related("category").prefetch_related("variants", "reviews")
    params = request.GET
    q = (params.get("q") or "").strip()[:MAX_Q]
    cat = (params.get("category") or "").strip()[:80]
    sort = (params.get("sort") or "popular").strip()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q) | Q(short_description__icontains=q) | Q(category__name__icontains=q))
    if cat and Category.objects.filter(slug=cat).exists():
        qs = qs.filter(category__slug=cat)
    tab = (params.get("temperament") or "").strip()[:20]
    if tab in ("hot", "cold", "moderate"):
        qs = qs.filter(temperament=tab)
    minp = params.get("min_price", "").strip()[:10]
    maxp = params.get("max_price", "").strip()[:10]
    if minp.isdigit():
        qs = qs.filter(variants__price__gte=int(minp)).distinct()
    if maxp.isdigit():
        qs = qs.filter(variants__price__lte=int(maxp)).distinct()
    if sort == "cheap":
        qs = qs.order_by("variants__price")
    elif sort == "expensive":
        qs = qs.order_by("-variants__price")
    elif sort == "newest":
        qs = qs.order_by("-created_at")
    else:
        qs = qs.order_by("-is_popular", "sort_order", "name")
    pg = Paginator(qs.distinct(), _page_size(request))
    page = pg.get_page(params.get("page") or 1)
    return JsonResponse({
        "products": [_prod_to_dict(p) for p in page.object_list],
        "meta": {"page": page.number, "num_pages": pg.num_pages, "count": pg.count, "page_size": pg.per_page},
    })

@require_GET
def api_product_detail(request: HttpRequest, slug: str):
    from django.shortcuts import get_object_or_404
    p = get_object_or_404(Product.objects.filter(is_active=True).select_related("category").prefetch_related("variants", "reviews"), slug=slug)
    variants = [{"id": v.id, "price": v.price, "compare_price": v.compare_price, "discount_percent": v.discount_percent,
                 "display_weight": v.display_weight, "amount": str(v.amount), "unit": v.unit, "pack_count": v.pack_count,
                 "stock": v.stock, "is_active": v.is_active} for v in p.variants.filter(is_active=True).order_by("price")]
    reviews = [{"id": r.id, "name": r.display_name, "rating": r.rating, "stars": r.stars_html, "comment": r.comment, "created_at": r.created_at.isoformat()} for r in p.reviews.filter(is_approved=True)[:20]]
    related = Product.objects.filter(is_active=True, category=p.category).exclude(pk=p.pk).select_related("category").prefetch_related("variants")[:6]
    return JsonResponse({"product": {**_prod_to_dict(p), "variants": variants, "reviews": reviews, "related": [_prod_to_dict(x) for x in related]}})

@require_GET
def api_cart(request: HttpRequest):
    from .cart import Cart
    c = Cart(request)
    items = [{"variant_id": r["variant"].id, "product_id": r["product"].id, "product_name": r["product"].name,
              "display_weight": r["variant"].display_weight, "price": r["variant"].price, "qty": r["qty"], "subtotal": r["subtotal"]} for r in c]
    return JsonResponse({"items": items, "total_price": c.total_price, "count": len(c), "distinct": c.distinct_count})

@require_GET
def api_wishlist(request: HttpRequest):
    from .wishlist_views import _effective_wishlist_ids
    ids = _effective_wishlist_ids(request)
    prods = Product.objects.filter(id__in=ids, is_active=True).select_related("category").prefetch_related("variants") if ids else []
    return JsonResponse({"products": [_prod_to_dict(p) for p in prods], "ids": list(ids), "count": len(ids)})

@require_GET
def api_autocomplete(request: HttpRequest):
    q = (request.GET.get("q") or "").strip()[:MAX_Q]
    if not q:
        return JsonResponse({"results": []})
    qs = Product.objects.filter(is_active=True, name__icontains=q).select_related("category").order_by("name")[:10]
    return JsonResponse({"results": [{"id": p.id, "name": p.name, "slug": p.slug, "url": p.get_absolute_url(), "image_url": p.image_url, "category": p.category.name} for p in qs]})