from django import template

register = template.Library()

@register.filter(name="format_price")
def format_price(value):
    """فرمت ۳ رقم ۳ رقم قیمت با کاما — مثلا ۲۵۰,۰۰۰"""
    try:
        if value is None or value == "":
            return ""
        val = int(value)
        return f"{val:,}"
    except (ValueError, TypeError):
        return value

@register.filter(name="intcomma_fa")
def intcomma_fa(value):
    """جداکننده ۳ رقمی ارقام"""
    try:
        if value is None or value == "":
            return ""
        val = int(value)
        return f"{val:,}"
    except (ValueError, TypeError):
        return value
