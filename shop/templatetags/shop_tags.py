from django import template

register = template.Library()

_FA_DIGITS = str.maketrans("0123456789,", "۰۱۲۳۴۵۶۷۸۹٬")


def _format_fa_price(value):
    """Format an integer price with Persian digits and the Arabic thousands mark."""
    try:
        if value is None or value == "":
            return ""
        return f"{int(value):,}".translate(_FA_DIGITS)
    except (ValueError, TypeError):
        return value


@register.filter(name="format_price")
def format_price(value):
    """مثال: 250000 → ۲۵۰٬۰۰۰"""
    return _format_fa_price(value)


@register.filter(name="intcomma_fa")
def intcomma_fa(value):
    """نمایش عدد با رقم و جداکنندهٔ فارسی."""
    return _format_fa_price(value)
