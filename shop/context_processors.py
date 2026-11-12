"""Small context values shared by all storefront templates."""
from __future__ import annotations

import json

from django.conf import settings
from django.utils.safestring import mark_safe

from .cart import Cart
from .models import Category
from .wishlist_views import _effective_wishlist_ids


def cart(request):
    c = Cart(request)
    try:
        wids = _effective_wishlist_ids(request)
        wcount = len(wids)
    except Exception:
        wids, wcount = set(), 0
    # The per-variant map lets product cards render the quantity control again
    # after a refresh instead of falling back to «افزودن به سبد».
    cart_quantities = c.quantities
    return {
        "cart": c,
        "cart_total": c.total_price,
        "cart_count": len(c),
        "cart_quantities": cart_quantities,
        "wishlist_ids": wids,
        "wishlist_count": wcount,
    }


def navigation_categories(request):
    """Active catalogue categories for the desktop hover and mobile submenu."""
    return {
        "nav_categories": Category.objects.filter(is_active=True)
        .only("name", "slug", "sort_order")
        .order_by("sort_order", "name")
    }


def seo(request):
    """Canonical, crawl policy, and safe sitewide JSON-LD for public pages."""
    canonical_host = str(getattr(settings, "CANONICAL_HOST", "") or "").strip()
    if canonical_host:
        origin = f"https://{canonical_host}"
    else:
        origin = request.build_absolute_uri("/").rstrip("/")
    canonical_url = f"{origin}{request.path}"

    noindex_prefixes = (
        "/account/",
        "/admin/",
        "/api/",
        "/cart/",
        "/checkout/",
        "/payment/",
        "/profile/",
        "/tracking/",
        "/wishlist/",
    )
    is_noindex = request.path.startswith(noindex_prefixes) or request.path == "/search/" or bool(request.GET)
    robots_directive = "noindex,follow" if is_noindex else "index,follow"

    organization = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Store",
                "@id": f"{origin}/#organization",
                "name": "عطارباشی",
                "url": f"{origin}/",
                "logo": f"{origin}/static/images/logo.jpg",
                "image": f"{origin}/static/images/logo.jpg",
                "telephone": "+989960555789",
                "email": "info@attarbashiesf.ir",
                "address": {
                    "@type": "PostalAddress",
                    "addressLocality": "نجف‌آباد",
                    "addressRegion": "اصفهان",
                    "addressCountry": "IR",
                    "streetAddress": "امیرآباد، خیابان طالقانی، کوچه خزائلی، پلاک ۱۶",
                },
            },
            {
                "@type": "WebSite",
                "@id": f"{origin}/#website",
                "url": f"{origin}/",
                "name": "عطارباشی",
                "inLanguage": "fa-IR",
                "publisher": {"@id": f"{origin}/#organization"},
            },
        ],
    }
    # json.dumps returns only our fixed values here.  Marking it safe prevents
    # Django from escaping quote characters inside application/ld+json.
    return {
        "canonical_url": canonical_url,
        "robots_directive": robots_directive,
        "organization_schema_json": mark_safe(json.dumps(organization, ensure_ascii=False, separators=(",", ":"))),
    }
