"""Best-effort owner notifications sent through the Telegram Bot API.

This module only sends outbound messages.  It does not receive commands and
therefore needs neither a webhook nor a continuously running bot process.
Missing or invalid credentials never block a customer checkout or contact form.
"""
from __future__ import annotations

import json
import logging
import threading
import urllib.error
import urllib.request
from collections.abc import Iterable

from django.conf import settings

logger = logging.getLogger(__name__)


def _configured_chat_ids() -> tuple[str, ...]:
    raw_ids: Iterable[str] = getattr(settings, "TELEGRAM_CHAT_IDS", ())
    valid_ids = []
    for chat_id in raw_ids:
        value = str(chat_id).strip()
        # Telegram private IDs are numeric; supergroup IDs normally begin
        # with -100, so a leading minus is intentionally accepted.
        if value and value.lstrip("-").isdigit():
            valid_ids.append(value)
        elif value:
            logger.warning("Ignoring non-numeric TELEGRAM_CHAT_IDS entry")
    return tuple(valid_ids)


def notifications_enabled() -> bool:
    return bool(
        getattr(settings, "TELEGRAM_NOTIFICATIONS_ENABLED", False)
        and getattr(settings, "TELEGRAM_BOT_TOKEN", "")
        and _configured_chat_ids()
    )


def _send(chat_id: str, text: str) -> None:
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    endpoint = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps(
        {
            "chat_id": chat_id,
            "text": text[:4096],
            "disable_web_page_preview": True,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            if response.status != 200:
                logger.warning("Telegram notification returned HTTP %s", response.status)
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        # Notifications are operationally useful, but must never interrupt a
        # paid order or prevent a customer support message from being stored.
        logger.warning("Telegram notification was not delivered: %s", exc)


def notify(text: str) -> None:
    """Deliver a short message to every configured owner/admin chat.

    The network call runs in a daemon thread after the database transaction has
    committed.  A temporary Telegram outage therefore cannot slow checkout or
    cause a customer-facing error.
    """
    if not notifications_enabled() or not text.strip():
        return
    for chat_id in _configured_chat_ids():
        threading.Thread(target=_send, args=(chat_id, text), daemon=True).start()


def notify_support_message(contact_message) -> None:
    notify(
        "📩 پیام پشتیبانی جدید\n"
        f"نام: {contact_message.full_name}\n"
        f"موبایل: {contact_message.phone}\n"
        f"دسته: {contact_message.get_category_display()}\n"
        f"متن: {contact_message.message[:900]}"
    )


def _stock_lines(order) -> str:
    rows = []
    for item in order.items.select_related("variant", "product").all():
        remaining = item.variant.stock if item.variant_id and item.variant else "—"
        rows.append(f"• {item.product_name} × {item.quantity} | باقی‌مانده: {remaining}")
    return "\n".join(rows) or "—"


def notify_new_order(order) -> None:
    notify(
        "🛒 سفارش جدید ثبت شد\n"
        f"شماره: {order.order_number}\n"
        f"مشتری: {order.full_name} | {order.phone_number}\n"
        f"مبلغ کالا: {order.total_price:,} تومان\n"
        f"ارسال: {order.get_shipping_method_display()}\n"
        f"پرداخت: {order.get_payment_method_display()}"
    )


def notify_payment_success(order) -> None:
    notify(
        "✅ پرداخت سفارش تأیید شد\n"
        f"شماره: {order.order_number}\n"
        f"روش پرداخت: {order.get_payment_method_display()}\n"
        f"مبلغ پرداختی: {order.grand_total:,} تومان\n"
        "موجودی باقی‌مانده پس از رزرو:\n"
        f"{_stock_lines(order)}"
    )


def notify_payment_cancelled(order) -> None:
    notify(
        "⚠️ پرداخت/سفارش لغو شد\n"
        f"شماره: {order.order_number}\n"
        f"مشتری: {order.full_name} | {order.phone_number}"
    )


def notify_card_receipt_uploaded(order) -> None:
    notify(
        "🧾 رسید کارت‌به‌کارت ارسال شد؛ نیازمند بررسی\n"
        f"شماره: {order.order_number}\n"
        f"مشتری: {order.full_name} | {order.phone_number}\n"
        f"مبلغ: {order.grand_total:,} تومان"
    )
