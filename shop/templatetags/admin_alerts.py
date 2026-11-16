"""Small, permission-aware alert components for the Django admin."""
from __future__ import annotations

from django import template
from django.urls import reverse
from django.utils.html import format_html, format_html_join

from shop.models import ContactMessage, Order

register = template.Library()


def _alert_context(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated or not user.is_staff:
        return {
            "can_view_orders": False,
            "can_view_messages": False,
            "receipt_review_count": 0,
            "unread_support_count": 0,
            "orders_url": "",
            "messages_url": "",
        }

    can_view_orders = user.has_perm("shop.view_order")
    can_view_messages = user.has_perm("shop.view_contactmessage")
    return {
        "can_view_orders": can_view_orders,
        "can_view_messages": can_view_messages,
        "receipt_review_count": (
            Order.objects.filter(status="awaiting_receipt", card_receipt__isnull=False).count()
            if can_view_orders
            else 0
        ),
        "unread_support_count": ContactMessage.objects.filter(status="new").count() if can_view_messages else 0,
        "orders_url": reverse("admin:shop_order_changelist") if can_view_orders else "",
        "messages_url": reverse("admin:shop_contactmessage_changelist") if can_view_messages else "",
    }


@register.inclusion_tag("admin/includes/review_alert_panel.html", takes_context=True)
def admin_review_panel(context):
    """Dashboard alert panel for card receipts and unread support messages."""
    return _alert_context(context.get("request"))


@register.simple_tag(takes_context=True)
def admin_review_badges(context):
    """Compact notification links displayed in the admin header on every page."""
    alerts = _alert_context(context.get("request"))
    links = []
    if alerts["receipt_review_count"]:
        links.append(
            (
                alerts["orders_url"] + "?status__exact=awaiting_receipt",
                f"🧾 {alerts['receipt_review_count']} رسید نیازمند بررسی",
                "admin-alert-badge admin-alert-badge--receipt",
            )
        )
    if alerts["unread_support_count"]:
        links.append(
            (
                alerts["messages_url"] + "?status__exact=new",
                f"📩 {alerts['unread_support_count']} پیام خوانده‌نشده",
                "admin-alert-badge admin-alert-badge--message",
            )
        )
    if not links:
        return ""
    return format_html_join(
        " ",
        '<a class="{}" href="{}">{}</a>',
        ((css_class, url, text) for url, text, css_class in links),
    )
