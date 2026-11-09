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
