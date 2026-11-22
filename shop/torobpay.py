"""Official TorobPay CPG gateway client.

Implements the published CPG v1.3.31 flow: OAuth password grant, per-amount
eligibility, payment-token creation, verify, settle, and cancel.  All amounts
sent to TorobPay are rials; storefront prices are stored in tomans.
"""
from __future__ import annotations

import base64
import json
import logging
import urllib.error
import urllib.request
from typing import Any

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

_TOKEN_PATH = "/api/online/v1/oauth/token"
_ELIGIBLE_PATH = "/api/online/offer/v1/eligible"
_PAYMENT_TOKEN_PATH = "/api/online/payment/v1/token"
_VERIFY_PATH = "/api/online/payment/v1/verify"
_SETTLE_PATH = "/api/online/payment/v1/settle"
_CANCEL_PATH = "/api/online/payment/v1/cancel"
_TIMEOUT_SECONDS = 12
_TOKEN_CACHE_SECONDS = 50 * 60  # Provider documents a one-hour JWT lifetime.


def _base_url() -> str:
    return str(getattr(settings, "TOROB_PAY_BASE_URL", "https://cpg.torobpay.com")).rstrip("/")


def _credentials() -> tuple[str, str, str, str]:
    return (
        str(getattr(settings, "TOROB_PAY_MERCHANT_CODE", "") or "").strip(),
        str(getattr(settings, "TOROB_PAY_MERCHANT_KEY", "") or "").strip(),
        str(getattr(settings, "TOROB_PAY_USERNAME", "") or "").strip(),
        str(getattr(settings, "TOROB_PAY_PASSWORD", "") or "").strip(),
    )


def is_configured() -> bool:
    return bool(getattr(settings, "TOROB_PAY_CREDENTIALS_CONFIGURED", False) and all(_credentials()))


def _error_message(payload: Any, fallback: str) -> str:
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            return str(error.get("user_message") or error.get("message") or fallback)
    return fallback


def _json_request(
    method: str,
    path: str,
    *,
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    query: str = "",
) -> dict[str, Any]:
    """Make one provider request without ever logging authentication values."""
    url = f"{_base_url()}{path}{query}"
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8") if payload is not None else None
    request_headers = {"Accept": "application/json"}
    if payload is not None:
        request_headers["Content-Type"] = "application/json"
    request_headers.update(headers or {})
    request = urllib.request.Request(url, data=body, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        try:
            raw = exc.read().decode("utf-8")
            response_payload = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            response_payload = {}
        logger.warning("TorobPay HTTP error %s at %s", exc.code, path)
        return {"success": False, "message": _error_message(response_payload, "پاسخ نامعتبر از ترب‌پی دریافت شد."), "status_code": exc.code}
    except urllib.error.URLError:
        logger.warning("TorobPay network error at %s", path)
        return {"success": False, "message": "ارتباط با ترب‌پی برقرار نشد. لطفاً دوباره تلاش کنید."}
    except (TimeoutError, OSError):
        logger.warning("TorobPay transport error at %s", path)
        return {"success": False, "message": "ارتباط با ترب‌پی برقرار نشد. لطفاً دوباره تلاش کنید."}

    try:
        response_payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        logger.warning("TorobPay returned invalid JSON at %s", path)
        return {"success": False, "message": "پاسخ نامعتبر از ترب‌پی دریافت شد."}
    if not isinstance(response_payload, dict):
        return {"success": False, "message": "پاسخ نامعتبر از ترب‌پی دریافت شد."}
    if response_payload.get("successful") is False:
        return {"success": False, "message": _error_message(response_payload, "درخواست ترب‌پی ناموفق بود."), "payload": response_payload}
    return {"success": True, "payload": response_payload}


def _access_token() -> dict[str, Any]:
    """Return a cached official OAuth token, refreshing it only when needed."""
    if not is_configured():
        return {"success": False, "message": "اطلاعات پذیرندگی ترب‌پی در فروشگاه کامل نشده است."}
    merchant_code, merchant_key, username, password = _credentials()
    cache_key = f"torobpay:oauth:{merchant_code}"
    token = cache.get(cache_key)
    if token:
        return {"success": True, "token": token}
    basic_value = base64.b64encode(f"{merchant_code}:{merchant_key}".encode("utf-8")).decode("ascii")
    result = _json_request(
        "POST",
        _TOKEN_PATH,
        payload={"username": username, "password": password},
        headers={"Authorization": f"Basic {basic_value}"},
    )
    if not result.get("success"):
        return result
    response = result["payload"].get("response", result["payload"])
    token = response.get("access_token") if isinstance(response, dict) else ""
    if not token:
        return {"success": False, "message": "توکن دسترسی معتبر از ترب‌پی دریافت نشد."}
    cache.set(cache_key, token, _TOKEN_CACHE_SECONDS)
    return {"success": True, "token": str(token)}


def _authorized_json(method: str, path: str, *, payload: dict[str, Any] | None = None, query: str = "") -> dict[str, Any]:
    auth = _access_token()
    if not auth.get("success"):
        return auth
    return _json_request(method, path, payload=payload, query=query, headers={"Authorization": f"Bearer {auth['token']}"})


def eligible(amount_rial: int) -> dict[str, Any]:
    """Check TorobPay eligibility before making its checkout option selectable."""
    if not is_configured() or amount_rial <= 0:
        return {"success": False, "eligible": False, "message": "ترب‌پی برای این سبد در دسترس نیست."}
    # Eligibility depends only on amount in the official API. A short cache
    # avoids an extra OAuth/API round-trip on every browser refresh.
    cache_key = f"torobpay:eligible:{int(amount_rial)}"
    cached = cache.get(cache_key)
    if isinstance(cached, dict):
        return cached
    result = _authorized_json("GET", _ELIGIBLE_PATH, query=f"?amount={int(amount_rial)}")
    if not result.get("success"):
        return {"success": False, "eligible": False, "message": result.get("message", "ترب‌پی در دسترس نیست.")}
    response = result["payload"].get("response", result["payload"])
    if not isinstance(response, dict):
        return {"success": False, "eligible": False, "message": "پاسخ صلاحیت ترب‌پی معتبر نیست."}
    outcome = {
        "success": True,
        "eligible": bool(response.get("eligible")),
        "title": str(response.get("title_message") or "پرداخت اقساطی با ترب‌پی"),
        "description": str(response.get("description") or ""),
    }
    cache.set(cache_key, outcome, 60)
    return outcome


def create_payment(order, return_url: str) -> dict[str, Any]:
    """Create a hosted TorobPay purchase and return its payment page URL."""
    amount_rial = int(order.grand_total) * 10
    lines = []
    for item in order.items.select_related("product__category", "variant").all():
        product = item.product
        lines.append(
            {
                "id": str(item.variant_id or item.product_id or item.pk),
                "name": str(item.product_name)[:255],
                "count": int(item.quantity),
                "amount": int(item.price) * 10,
                "category": str(getattr(getattr(product, "category", None), "name", "other") or "other")[:100],
                "commissionType": 0,
            }
        )
    if not lines:
        return {"success": False, "message": "سبد سفارش برای ارسال به ترب‌پی خالی است."}
    payload = {
        "amount": amount_rial,
        "paymentMethodTypeDto": "ONLINE_CREDIT",
        "returnURL": return_url,
        "transactionId": order.order_number,
        "cartList": [
            {
                "cartId": order.order_number,
                "totalAmount": amount_rial,
                "taxAmount": 0,
                "shippingAmount": 0,
                "isTaxIncluded": False,
                "isShipmentIncluded": False,
                "cartItems": lines,
            }
        ],
        "address": str(order.address)[:1000],
        "postalCode": str(order.postal_code)[:20],
        "customer_full_name": str(order.full_name)[:150],
        "city": str(order.city)[:80],
        "province": str(order.province)[:80],
        "registration_phone_number": str(order.phone_number)[:20],
        "mobile": str(order.phone_number)[:20],
    }
    result = _authorized_json("POST", _PAYMENT_TOKEN_PATH, payload=payload)
    if not result.get("success"):
        return result
    response = result["payload"].get("response", result["payload"])
    if not isinstance(response, dict):
        return {"success": False, "message": "پاسخ ایجاد پرداخت ترب‌پی معتبر نیست."}
    payment_token = response.get("paymentToken")
    payment_page_url = response.get("paymentPageUrl")
    if not payment_token or not payment_page_url:
        return {"success": False, "message": "توکن یا آدرس پرداخت ترب‌پی دریافت نشد."}
    transaction_id = str(response.get("transactionId") or order.order_number)
    return {
        "success": True,
        "payment_token": str(payment_token),
        "payment_page_url": str(payment_page_url),
        "transaction_id": transaction_id,
    }


def verify(payment_token: str) -> dict[str, Any]:
    result = _authorized_json("POST", _VERIFY_PATH, payload={"paymentToken": payment_token})
    if not result.get("success"):
        return result
    response = result["payload"].get("response", result["payload"])
    transaction_id = response.get("transactionId") if isinstance(response, dict) else ""
    return {"success": bool(transaction_id), "transaction_id": str(transaction_id or ""), "message": "تأیید ترب‌پی ناموفق بود."}


def settle(payment_token: str) -> dict[str, Any]:
    result = _authorized_json("POST", _SETTLE_PATH, payload={"paymentToken": payment_token})
    if not result.get("success"):
        return result
    response = result["payload"].get("response", result["payload"])
    transaction_id = response.get("transactionId") if isinstance(response, dict) else ""
    return {"success": bool(transaction_id), "transaction_id": str(transaction_id or ""), "message": "نهایی‌سازی ترب‌پی ناموفق بود."}


def cancel(payment_token: str) -> dict[str, Any]:
    """Ask the provider to cancel/refund when the merchant cannot fulfil a verified order."""
    result = _authorized_json("POST", _CANCEL_PATH, payload={"paymentToken": payment_token})
    if not result.get("success"):
        return result
    response = result["payload"].get("response", result["payload"])
    transaction_id = response.get("transactionId") if isinstance(response, dict) else ""
    return {"success": bool(transaction_id), "transaction_id": str(transaction_id or "")}
