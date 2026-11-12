from pathlib import Path
from urllib.parse import urlencode, unquote, urlsplit

from django import template
from django.conf import settings
from django.templatetags.static import static
from django.urls import reverse

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


@register.simple_tag
def responsive_media(image_value, width):
    """Return a cacheable, same-origin WebP derivative for a local image.

    Product media and bundled static editorial assets both pass through the
    trusted responsive endpoint.  Remote URLs are deliberately not proxied:
    normalised catalogue records are local, and an unexpected remote value is
    left untouched rather than turning this site into an open image proxy.
    """
    source_url = str(getattr(image_value, "url", image_value) or "").strip()
    if not source_url:
        return ""
    try:
        target_width = max(64, min(int(width), 2000))
    except (TypeError, ValueError):
        return source_url

    parsed = urlsplit(source_url)
    if parsed.scheme or parsed.netloc:
        return source_url

    source_path = unquote(parsed.path or "")
    static_url = str(getattr(settings, "STATIC_URL", "/static/") or "/static/")
    media_url = str(getattr(settings, "MEDIA_URL", "/media/") or "/media/")
    if not source_path.startswith((static_url, media_url)):
        return source_url

    # Preserve the normal public path but discard an old cache-busting query;
    # the derivative URL itself is versioned by its source mtime and size.
    normalized_source = source_path
    return f"{reverse('responsive_media', args=[target_width])}?{urlencode({'src': normalized_source})}"


@register.filter(name="cloudinary_thumbnail")
def cloudinary_thumbnail(url, width=480):
    """Backward-compatible filter now backed by same-origin derivatives.

    Older templates and any custom content can still call this filter.  It no
    longer emits a browser-facing Cloudinary URL for a local source.
    """
    return responsive_media(url, width)
