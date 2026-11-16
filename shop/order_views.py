"""Secure checkout, payment verification, and customer order views."""
from __future__ import annotations

import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic import TemplateView
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .cart import Cart
from .models import CustomerAddress, Order, OrderItem, ProductVariant
from .telegram_notifications import (
    notify_card_receipt_uploaded,
    notify_new_order,
    notify_payment_cancelled,
    notify_payment_success,
)
from .zarinpal import request_payment, verify_payment


VALID_SHIPPING_METHODS = {choice[0] for choice in Order.SHIPPING_METHOD_CHOICES}
VALID_PAYMENT_METHODS = {choice[0] for choice in Order.PAYMENT_METHOD_CHOICES}


def _order_number() -> str:
    return f"ATB-{timezone.now():%y%m%d}-{uuid.uuid4().hex[:7].upper()}"


def _checkout_error(request, message: str):
    messages.error(request, message)
    return redirect(f"{reverse('shop:cart_detail')}?open_checkout=1")


def _address_data(request):
    selected_id = (request.POST.get("saved_address_id") or "").strip()
    if selected_id:
        address = CustomerAddress.objects.filter(pk=selected_id, user=request.user).first()
        if not address:
            return None, "نشانی انتخاب‌شده معتبر نیست."
        return {
            "full_name": address.full_name,
            "phone_number": address.phone_number,
            "province": address.province,
            "city": address.city,
            "address": address.address,
            "postal_code": address.postal_code,
        }, ""

    fields = ("full_name", "phone_number", "province", "city", "address", "postal_code")
    data = {field: (request.POST.get(field) or "").strip() for field in fields}
    required = ("full_name", "phone_number", "province", "city", "address")
    if any(not data[field] for field in required):
        return None, "لطفاً اطلاعات کامل تحویل‌گیرنده و نشانی را وارد کنید."
    return data, ""


def _maybe_save_address(request, data):
    """Save an address once, without creating a duplicate on every checkout."""
    if request.POST.get("save_address") != "1":
        return
    label = (request.POST.get("address_label") or "").strip()[:80]
    make_default = request.POST.get("make_default") == "1"
    identity = {
        "full_name": data["full_name"],
        "phone_number": data["phone_number"],
        "province": data["province"],
        "city": data["city"],
        "address": data["address"],
        "postal_code": data["postal_code"],
    }
    # Use the most recently used matching address if old duplicate data exists;
    # new checkout attempts update it instead of inserting another row.
    saved = CustomerAddress.objects.filter(user=request.user, **identity).order_by("-is_default", "-updated_at").first()
    is_first_address = not CustomerAddress.objects.filter(user=request.user).exists()
    if saved:
        update_fields = []
        if label and saved.label != label:
            saved.label = label
            update_fields.append("label")
        if make_default and not saved.is_default:
            CustomerAddress.objects.filter(user=request.user, is_default=True).exclude(pk=saved.pk).update(is_default=False)
            saved.is_default = True
            update_fields.append("is_default")
        if update_fields:
            update_fields.append("updated_at")
            saved.save(update_fields=update_fields)
        return saved

    if make_default:
        CustomerAddress.objects.filter(user=request.user, is_default=True).update(is_default=False)
    return CustomerAddress.objects.create(
        user=request.user,
        label=label,
        is_default=make_default or is_first_address,
        **identity,
    )


@require_POST
def create_order(request):
    if not request.user.is_authenticated:
        return redirect(f"{reverse('signup')}?next={reverse('shop:cart_detail')}?open_checkout=1")
    cart = Cart(request)
    cart_items = list(cart)
    if not cart_items:
        return _checkout_error(request, "سبد خرید شما خالی است.")

    shipping_method = (request.POST.get("shipping_method") or "tipax").strip()
    payment_method = (request.POST.get("payment_method") or "zarinpal").strip()
    if shipping_method not in VALID_SHIPPING_METHODS:
        return _checkout_error(request, "لطفاً یکی از روش‌های فعال ارسال را انتخاب کنید.")
    if payment_method not in VALID_PAYMENT_METHODS:
        return _checkout_error(request, "لطفاً روش پرداخت را انتخاب کنید.")
    if payment_method == "zarinpal" and not getattr(settings, "ZARINPAL_ENABLED", False):
        return _checkout_error(request, "پرداخت آنلاین زرین‌پال هنوز از سمت فروشگاه فعال نشده است؛ کارت‌به‌کارت را انتخاب کنید.")
    if payment_method == "card_to_card" and not getattr(settings, "CARD_TO_CARD_ENABLED", False):
        return _checkout_error(request, "پرداخت کارت‌به‌کارت هنوز توسط فروشگاه تکمیل نشده است. لطفاً با پشتیبانی تماس بگیرید.")

    delivery, error = _address_data(request)
    if error:
        return _checkout_error(request, error)

    # All three enabled carriers collect carriage from the customer on delivery.
    # No delivery amount is sent to the online gateway.
    total_price = sum(int(item["price"]) * int(item["qty"]) for item in cart_items)
    try:
        with transaction.atomic():
            # Recheck every line inside the transaction before persisting price.
            lines = []
            for item in cart_items:
                variant = ProductVariant.objects.select_for_update().select_related("product").get(pk=item["variant"].pk)
                quantity = int(item["qty"])
                if not variant.is_active or not variant.product.is_active or variant.stock < quantity:
                    raise ValueError(f"موجودی «{variant.product.name}» تغییر کرده است؛ سبد خرید را دوباره بررسی کنید.")
                lines.append((variant, quantity))

            deadline = None
            if payment_method == "card_to_card":
                deadline = timezone.now() + timedelta(minutes=settings.CARD_TO_CARD_PAYMENT_WINDOW_MINUTES)
            order = Order.objects.create(
                user=request.user,
                order_number=_order_number(),
                shipping_method=shipping_method,
                payment_method=payment_method,
                card_payment_deadline=deadline,
                total_price=total_price,
                shipping_cost=0,
                status="pending",
                **delivery,
            )
            for variant, quantity in lines:
                OrderItem.objects.create(
                    order=order,
                    product=variant.product,
                    variant=variant,
                    product_name=variant.product.name,
                    variant_weight=variant.display_weight,
                    price=variant.price,
                    quantity=quantity,
                )
            _maybe_save_address(request, delivery)
    except ValueError as exc:
        return _checkout_error(request, str(exc))

    notify_new_order(order)
    if payment_method == "card_to_card":
        # This is only a payment request, not a confirmed sale. Keep the cart
        # intact until the store verifies the receipt and marks the order paid.
        return redirect("shop:card_payment_instructions", order_number=order.order_number)

    callback_url = request.build_absolute_uri(reverse("shop:payment_verify"))
    result = request_payment(
        order.grand_total,
        f"سفارش {order.order_number} از عطارباشی",
        callback_url,
        mobile=order.phone_number,
        email=getattr(request.user, "email", ""),
    )
    if not result.get("success"):
        order.status = "cancelled"
        order.save(update_fields=["status", "updated_at"])
        return _checkout_error(request, result.get("message") or "اتصال به درگاه پرداخت ممکن نشد.")

    order.payment_authority = result.get("authority", "")
    order.save(update_fields=["payment_authority", "updated_at"])
    if result.get("mode") == "test":
        return redirect(f"{reverse('shop:payment_verify')}?Authority={order.payment_authority}&Status=OK")
    return redirect(result["url"])


@require_GET
def payment_verify(request):
    authority = (request.GET.get("Authority") or "").strip()
    status = (request.GET.get("Status") or "").strip().upper()
    order = Order.objects.filter(payment_authority=authority).prefetch_related("items__variant", "items__product").first()
    if not order:
        raise Http404("سفارش پرداخت پیدا نشد.")

    if status != "OK":
        if order.status != "cancelled":
            order.status = "cancelled"
            order.save(update_fields=["status", "updated_at"])
            notify_payment_cancelled(order)
        return render(request, "payment_result.html", {"order": order, "is_success": False})

    result = verify_payment(order.grand_total, authority)
    if not result.get("success"):
        return render(request, "payment_result.html", {"order": order, "is_success": False})

    newly_paid = order.status not in {"paid", "processing", "shipped", "delivered"}
    try:
        with transaction.atomic():
            order = Order.objects.select_for_update().prefetch_related("items__variant", "items__product").get(pk=order.pk)
            if not order.stock_reserved:
                order.reserve_stock()
            order.status = "paid"
            order.payment_reference = result.get("ref_id", "")
            order.save(update_fields=["status", "payment_reference", "updated_at"])
    except ValueError as exc:
        order.status = "cancelled"
        order.save(update_fields=["status", "updated_at"])
        messages.error(request, str(exc))
        return render(request, "payment_result.html", {"order": order, "is_success": False})

    if newly_paid:
        notify_payment_success(order)
    Cart(request).clear()
    return render(request, "payment_result.html", {"order": order, "is_success": True})


@login_required
@require_GET
def card_payment_instructions(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user, payment_method="card_to_card")
    expired = bool(order.card_payment_deadline and timezone.now() > order.card_payment_deadline)
    return render(
        request,
        "card_payment.html",
        {
            "order": order,
            "expired": expired,
            "card_number": settings.CARD_TO_CARD_NUMBER,
            "card_holder": settings.CARD_TO_CARD_ACCOUNT_HOLDER,
            "bank_name": settings.CARD_TO_CARD_BANK_NAME,
        },
    )


@login_required
@require_POST
def upload_card_receipt(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user, payment_method="card_to_card")
    receipt = request.FILES.get("receipt")
    if not receipt:
        messages.error(request, "لطفاً تصویر یا فایل رسید پرداخت را انتخاب کنید.")
        return redirect("shop:card_payment_instructions", order_number=order.order_number)
    if order.card_payment_deadline and timezone.now() > order.card_payment_deadline:
        messages.error(request, "مهلت دو ساعتهٔ ثبت رسید این سفارش پایان یافته است؛ با پشتیبانی تماس بگیرید.")
        return redirect("shop:card_payment_instructions", order_number=order.order_number)
    if receipt.size > 8 * 1024 * 1024:
        messages.error(request, "حجم رسید باید حداکثر ۸ مگابایت باشد.")
        return redirect("shop:card_payment_instructions", order_number=order.order_number)
    if getattr(receipt, "content_type", "") not in {"image/jpeg", "image/png", "image/webp"}:
        messages.error(request, "رسید باید تصویر JPG، PNG یا WebP باشد.")
        return redirect("shop:card_payment_instructions", order_number=order.order_number)

    order.card_receipt = receipt
    order.receipt_uploaded_at = timezone.now()
    order.status = "awaiting_receipt"
    order.save(update_fields=["card_receipt", "receipt_uploaded_at", "status", "updated_at"])
    notify_card_receipt_uploaded(order)
    messages.success(request, "رسید شما ثبت شد. پس از بررسی فروشگاه، وضعیت سفارش به‌روزرسانی می‌شود.")
    return redirect("shop:card_payment_instructions", order_number=order.order_number)


@login_required
@require_GET
def user_orders(request):
    orders = Order.objects.filter(user=request.user).prefetch_related("items").order_by("-created_at")
    return render(request, "profile/orders.html", {"orders": orders})


class FaqView(TemplateView):
    template_name = "faq.html"


def order_tracking(request):
    query = (request.GET.get("query") or "").strip()
    orders = Order.objects.none()
    searched = bool(query)
    if query:
        # The existing public tracking page accepts either an exact order ID or
        # the phone recorded for that order. Logged-in users are additionally
        # limited to their own order history.
        orders = Order.objects.prefetch_related("items").filter(
            Q(order_number__iexact=query) | Q(phone_number=query)
        ).order_by("-created_at")
        if request.user.is_authenticated:
            orders = orders.filter(user=request.user)
    return render(request, "tracking.html", {"orders": orders, "query": query, "searched": searched})


@login_required
def order_invoice(request, order_number):
    order = get_object_or_404(Order.objects.prefetch_related("items"), order_number=order_number, user=request.user)
    paid_statuses = {"paid", "processing", "shipped", "delivered"}
    pending_statuses = {"pending", "awaiting_receipt"}
    return render(
        request,
        "payment_result.html",
        {
            "order": order,
            "is_success": order.status in paid_statuses,
            "is_pending_payment": order.status in pending_statuses,
        },
    )


@login_required
def payment_result(request):
    order_number = (request.GET.get("order") or "").strip()
    if order_number:
        return redirect("shop:order_invoice", order_number=order_number)
    return redirect("shop:user_orders")
