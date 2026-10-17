"""
ویوهای سبد خرید — افزودن/به‌روزرسانی/حذف (POST امن + بررسی موجودی انبار در دیتابیس + پشتیبانی AJAX)
"""
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .cart import Cart
from .models import ProductVariant


def _is_ajax(request) -> bool:
    return (
        request.headers.get("x-requested-with") == "XMLHttpRequest"
        or "application/json" in request.headers.get("accept", "")
        or request.POST.get("ajax") == "1"
    )


@require_POST
def cart_add(request, variant_id: int):
    variant = get_object_or_404(
        ProductVariant.objects.select_related("product"),
        id=variant_id,
        is_active=True,
        product__is_active=True,
    )
    is_ajax = _is_ajax(request)
    qty_raw = str(request.POST.get("qty") or request.POST.get("quantity") or "1")[:3]
    try:
        qty = max(1, min(int(qty_raw), 99))
    except ValueError:
        qty = 1

    # ۱. بررسی موجودی دیتابیس
    if variant.stock <= 0:
        msg = f"متأسفانه «{variant.product.name}» ({variant.display_weight}) در انبار موجود نیست."
        if is_ajax:
            return JsonResponse({"success": False, "message": msg, "stock": 0}, status=400)
        messages.error(request, msg)
        next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "/cart/"
        return redirect(next_url)

    cart = Cart(request)
    current_qty_in_cart = cart.get_qty(variant)

    if current_qty_in_cart + qty > variant.stock:
        max_possible = variant.stock - current_qty_in_cart
        if max_possible <= 0:
            msg = f"حداکثر موجودی در انبار ({variant.stock} عدد) قبلاً به سبد شما اضافه شده است."
            if is_ajax:
                return JsonResponse({"success": False, "message": msg, "stock": variant.stock}, status=400)
            messages.warning(request, msg)
            next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "/cart/"
            return redirect(next_url)
        qty = max_possible

    cart.add(variant, qty=qty)
    msg = f"«{variant.product.name}» ({variant.display_weight}) به سبد خرید اضافه شد."

    if is_ajax:
        return JsonResponse({
            "success": True,
            "message": msg,
            "cart_count": len(cart),
            "cart_total": cart.total_price,
            "item_qty": cart.get_qty(variant),
            "stock": variant.stock,
            "variant_id": variant.id,
            "product_name": variant.product.name,
        })

    messages.success(request, msg)
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "/cart/"
    return redirect(next_url)


@require_POST
def cart_update(request, variant_id: int):
    variant = get_object_or_404(ProductVariant.objects.select_related("product"), id=variant_id)
    is_ajax = _is_ajax(request)
    qty_raw = str(request.POST.get("qty") or request.POST.get("quantity") or "1")[:3]
    try:
        qty = max(0, min(int(qty_raw), 99))
    except ValueError:
        qty = 1

    cart = Cart(request)
    if qty == 0:
        cart.remove(variant)
        msg = f"«{variant.product.name}» از سبد حذف شد."
        if is_ajax:
            return JsonResponse({
                "success": True,
                "action": "removed",
                "message": msg,
                "cart_count": len(cart),
                "cart_total": cart.total_price,
            })
        messages.info(request, msg)
    else:
        if variant.stock > 0 and qty > variant.stock:
            qty = int(variant.stock)
        cart.set_qty(variant, qty)
        msg = "سبد خرید به‌روزرسانی شد."
        if is_ajax:
            return JsonResponse({
                "success": True,
                "action": "updated",
                "message": msg,
                "cart_count": len(cart),
                "cart_total": cart.total_price,
                "item_qty": qty,
                "subtotal": variant.price * qty,
                "stock": variant.stock,
            })
        messages.success(request, msg)

    return redirect("shop:cart_detail")


@require_POST
def cart_remove(request, variant_id: int):
    is_ajax = _is_ajax(request)
    cart = Cart(request)
    cart.remove(int(variant_id))
    msg = "محصول از سبد حذف شد."
    if is_ajax:
        return JsonResponse({
            "success": True,
            "message": msg,
            "cart_count": len(cart),
            "cart_total": cart.total_price,
        })
    messages.info(request, msg)
    return redirect("shop:cart_detail")


@require_POST
def cart_clear(request):
    is_ajax = _is_ajax(request)
    cart = Cart(request)
    cart.clear()
    msg = "سبد خرید خالی شد."
    if is_ajax:
        return JsonResponse({
            "success": True,
            "message": msg,
            "cart_count": 0,
            "cart_total": 0,
        })
    messages.info(request, msg)
    return redirect("shop:cart_detail")


def cart_detail(request):
    cart = Cart(request)
    items = list(cart)
    return render(request, "cart.html", {"items": items, "cart": cart})