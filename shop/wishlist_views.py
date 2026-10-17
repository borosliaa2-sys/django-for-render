"""Wishlist — session برای مهمان، DB برای کاربر لاگین + پشتیبانی AJAX بدون رفرش."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from .models import Product, Wishlist

WISH_SESSION_KEY = "wishlist_ids"


def _session_ids(request): return set(request.session.get(WISH_SESSION_KEY, []))
def _save_session(request, ids):
    request.session[WISH_SESSION_KEY] = list(ids)
    request.session.modified = True

def _effective_wishlist_ids(request):
    if request.user.is_authenticated:
        s_ids = _session_ids(request)
        if s_ids:
            for pid in s_ids:
                try:
                    prod = Product.objects.filter(id=pid, is_active=True).first()
                    if prod:
                        Wishlist.objects.get_or_create(user=request.user, product=prod)
                except Exception:
                    pass
            _save_session(request, set())
        return set(Wishlist.objects.filter(user=request.user).values_list("product_id", flat=True))
    return _session_ids(request)

@require_http_methods(["GET", "POST"])
def wishlist_toggle(request, product_id: int):
    product = get_object_or_404(Product, id=product_id, is_active=True)
    is_ajax = (
        request.headers.get("x-requested-with") == "XMLHttpRequest"
        or "application/json" in request.headers.get("accept", "")
        or request.POST.get("ajax") == "1"
        or request.GET.get("ajax") == "1"
    )

    if request.user.is_authenticated:
        obj, created = Wishlist.objects.get_or_create(user=request.user, product=product)
        if not created:
            obj.delete()
            is_wishlisted = False
            msg = f"«{product.name}» از لیست علاقه‌مندی‌ها حذف شد."
        else:
            is_wishlisted = True
            msg = f"«{product.name}» به لیست علاقه‌مندی‌ها اضافه شد."
        wishlist_count = Wishlist.objects.filter(user=request.user).count()
    else:
        ids = _session_ids(request)
        if product_id in ids:
            ids.discard(product_id)
            is_wishlisted = False
            msg = f"«{product.name}» از لیست علاقه‌مندی‌ها حذف شد."
        else:
            ids.add(product_id)
            is_wishlisted = True
            msg = f"«{product.name}» به لیست علاقه‌مندی‌ها اضافه شد."
        _save_session(request, ids)
        wishlist_count = len(ids)

    if is_ajax:
        return JsonResponse({
            "success": True,
            "is_wishlisted": is_wishlisted,
            "wishlist_count": wishlist_count,
            "message": msg,
            "product_id": product_id,
            "product_name": product.name,
        })

    if is_wishlisted:
        messages.success(request, msg)
    else:
        messages.info(request, msg)
    back = request.META.get("HTTP_REFERER") or "/"
    return redirect(back)

def wishlist_list(request):
    ids = _effective_wishlist_ids(request)
    products = Product.objects.filter(id__in=ids, is_active=True).select_related("category").prefetch_related("variants") if ids else Product.objects.none()
    return render(request, "wishlist.html", {"products": products, "wishlist_ids": ids})