from pathlib import Path

from django import template
from django.conf import settings
from django.templatetags.static import static

register = template.Library()

_FA_DIGITS = str.maketrans("0123456789,", "۰۱۲۳۴۵۶۷۸۹٬")
_DEFAULT_CATEGORY_ICON = "images/categories/category-16.webp"


def _format_fa_price(value):
    """Format an integer price with Persian digits and the Arabic thousands mark."""
    try:
        if value is None or value == "":
            return ""
        return f"{int(value):,}".translate(_FA_DIGITS)
    except (ValueError, TypeError):
        return value


def _static_source_exists(relative_path: str) -> bool:
    """Check the committed source before asking manifest storage for a URL."""
    for root in getattr(settings, "STATICFILES_DIRS", []):
        if (Path(root) / relative_path).is_file():
            return True
    return False


@register.simple_tag(name="category_icon_url")
def category_icon_url(icon_path):
    """Return a manifest-safe category icon URL with a bundled fallback.

    This keeps pages live even if an older database still references an icon
    file that was replaced by a newer deployment.
    """
    clean = str(icon_path or "").strip().lstrip("/")
    if clean.startswith("images/"):
        clean = clean[len("images/"):]
    candidate = f"images/{clean}" if clean else _DEFAULT_CATEGORY_ICON
    if not _static_source_exists(candidate):
        candidate = _DEFAULT_CATEGORY_ICON
    return static(candidate)


@register.filter(name="format_price")
def format_price(value):
    """مثال: 250000 → ۲۵۰٬۰۰۰"""
    return _format_fa_price(value)


@register.filter(name="intcomma_fa")
def intcomma_fa(value):
    """نمایش عدد با رقم و جداکنندهٔ فارسی."""
    return _format_fa_price(value)


@register.filter(name="cart_quantity")
def cart_quantity(cart_quantities, variant_id):
    """Look up a persisted cart quantity by a dynamic variant id in templates."""
    try:
        return int((cart_quantities or {}).get(str(variant_id), 0))
    except (AttributeError, TypeError, ValueError):
        return 0
