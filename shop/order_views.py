"""
ویوهای سفارشات، پیگیری مرسوله پستی، درگاه پرداخت زرین‌پال و فاکتور، سوالات متداول و پروفایل کاربری
"""
import random
import time
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import TemplateView

from .cart import Cart
from .models import Order, OrderItem, ProductVariant
from .zarinpal import request_payment, verify_payment


class FaqView(TemplateView):
    """
    صفحه سوالات متداول (FAQ)
    """
    template_name = "faq.html"


class OrderTrackingView(View):
    """
    صفحه پیگیری سفارش و کد رهگیری پستی
    """
    template_name = "tracking.html"

    def get(self, request):
        query = request.GET.get("query", "").strip()
        orders = []
        searched = bool(query)

        if query:
            clean_query = query.replace("#", "").replace("AT-", "").replace("at-", "").strip()
            orders = Order.objects.filter(
                models_q_filter(query, clean_query)
            ).prefetch_related("items__product").distinct()

        return render(request, self.template_name, {
            "query": query,
            "orders": orders,
            "searched": searched,
        })


def models_q_filter(query: str, clean_query: str):
    from django.db.models import Q
    return (
        Q(order_number__icontains=query)
        | Q(order_number__icontains=clean_query)
        | Q(phone_number__icontains=query)
        | Q(postal_tracking_code__icontains=query)
    )


class CheckoutView(View):
    """
    ثبت نهایی سفارش، رزرو و قفل موجودی انبار، و اتصال به درگاه پرداخت زرین‌پال
    """
    def post(self, request):
        cart = Cart(request)
        if len(cart) == 0:
            messages.warning(request, "سبد خرید شما خالی است.")
            return redirect("shop:cart_detail")

        if not request.user.is_authenticated:
            messages.info(request, "جهت تکمیل پرداخت و نهایی کردن خرید، لطفاً ثبت‌نام سریع را انجام دهید یا وارد حساب خود شوید.")
            return redirect(f"{reverse('signup')}?next={reverse('shop:cart_detail')}?open_checkout=1")

        full_name = request.POST.get("full_name", "").strip()
        phone_number = request.POST.get("phone_number", "").strip()
        province = request.POST.get("province", "تهران").strip()
        city = request.POST.get("city", "تهران").strip()
        address = request.POST.get("address", "").strip()
        postal_code = request.POST.get("postal_code", "").strip()
        notes = request.POST.get("notes", "").strip()

        if request.user.is_authenticated:
            if not full_name:
                full_name = request.user.get_full_name() or request.user.username
            if not phone_number and hasattr(request.user, "phone_number"):
                phone_number = request.user.phone_number or ""

        if not full_name:
            full_name = "مشتری گرامی عطارباشی"
        if not phone_number:
            phone_number = "09120000000"
        if not address:
            address = "آدرس ثبت‌شده در حساب کاربری"

        order_number = f"AT-{random.randint(100000, 999999)}"
        payment_reference = f"TRX-{int(time.time())}-{random.randint(100, 999)}"
        postal_tracking_code = f"1948200{random.randint(10000000000000000, 99999999999999999)}"[:24]

        try:
            with transaction.atomic():
                order = Order.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    order_number=order_number,
                    postal_tracking_code=postal_tracking_code,
                    full_name=full_name,
                    phone_number=phone_number,
                    province=province,
                    city=city,
                    address=address,
                    postal_code=postal_code,
                    total_price=cart.total_price,
                    shipping_cost=35000,
                    status='pending',
                    stock_reserved=False,
                    payment_reference=payment_reference,
                    notes=notes,
                )

                for item in cart:
                    variant = item["variant"]
                    price_val = item.get("price") or getattr(variant, "price", 0)
                    qty_val = item.get("qty", 1)
                    OrderItem.objects.create(
                        order=order,
                        product=variant.product,
                        variant=variant,
                        product_name=variant.product.name,
                        variant_weight=variant.display_weight,
                        price=price_val,
                        quantity=qty_val,
                    )

                # رزرو اتمیک و کسر فوری از انبار برای جلوگیری از سفارش همزمان و موجودی منفی
                order.reserve_stock()

        except ValueError as e:
            messages.error(request, str(e))
            return redirect("shop:cart_detail")
        except Exception as e:
            messages.error(request, f"خطایی در ثبت سفارش رخ داد: {str(e)}")
            return redirect("shop:cart_detail")

        # ارسال درخواست پرداخت به زرین‌پال
        total_amount = order.total_price + order.shipping_cost
        callback_url = request.build_absolute_uri(f"/payment/verify/?order={order.order_number}")
        description = f"پرداخت سفارش شماره {order.order_number} فروشگاه عطارباشی"

        pay_res = request_payment(
            amount_toman=total_amount,
            description=description,
            callback_url=callback_url,
            mobile=phone_number,
            email=request.user.email if (request.user.is_authenticated and request.user.email) else ""
        )

        if pay_res.get("success"):
            if pay_res.get("mode") == "live" and pay_res.get("url"):
                # انتقال مستقیم کاربر به درگاه بانکی زرین‌پال
                return redirect(pay_res["url"])
            else:
                # حالت تستی / شبیه‌ساز پرداخت
                return redirect(f"/payment/verify/?order={order.order_number}&status=success&Authority={pay_res.get('authority')}")
        else:
            messages.error(request, pay_res.get("message", "خطا در اتصال به درگاه پرداخت."))
            return redirect("shop:cart_detail")


class PaymentVerifyView(View):
    """
    بررسی و تایید نتیجه تراکنش بانکی زرین‌پال (فقط هنگام بازگشت از درگاه پرداخت)
    """
    def get(self, request):
        order_number = request.GET.get("order", "").strip()
        authority = request.GET.get("Authority", "").strip()
        status_param = request.GET.get("Status", "").strip() or request.GET.get("status", "").strip()

        order = None
        if order_number:
            order = Order.objects.filter(order_number=order_number).first()

        if not order and request.user.is_authenticated:
            order = Order.objects.filter(user=request.user).first()

        if not order:
            messages.error(request, "سفارش مورد نظر یافت نشد.")
            return redirect("shop:cart_detail")

        # اگر سفارش قبلاً تعیین تکلیف شده و pending نیست، وضعیت آن تغییر نمی‌کند
        if order.status != "pending":
            return redirect("shop:order_invoice", order_number=order.order_number)

        # اگر پرداخت درگاه با Authority انجام شده است
        if authority and not authority.startswith("TEST_"):
            total_amount = order.total_price + order.shipping_cost
            if status_param.upper() in ("OK", "SUCCESS", "PAID"):
                verify_res = verify_payment(amount_toman=total_amount, authority=authority)
                if verify_res.get("success"):
                    order.status = "paid"
                    ref_id = verify_res.get("ref_id", order.payment_reference)
                    order.payment_reference = f"ZP-{ref_id}"
                    order.save(update_fields=["status", "payment_reference"])
                    cart = Cart(request)
                    cart.clear()
                    messages.success(request, f"پرداخت با موفقیت انجام شد. کد پیگیری: {ref_id}")
                else:
                    order.status = "cancelled"
                    order.release_stock()
                    order.save(update_fields=["status"])
                    messages.error(request, verify_res.get("message", "تراکنش ناموفق بود یا لغو گردید."))
            else:
                order.status = "cancelled"
                order.release_stock()
                order.save(update_fields=["status"])
                messages.error(request, "تراکنش توسط کاربر لغو گردید.")
        elif status_param.lower() in ("success", "paid", "ok"):
            # حالت پرداخت تستی / شبیه‌ساز پرداخت
            order.status = "paid"
            order.save(update_fields=["status"])
            cart = Cart(request)
            cart.clear()
            messages.success(request, "پرداخت با موفقیت انجام و سفارش ثبت گردید.")
        else:
            order.status = "cancelled"
            order.release_stock()
            order.save(update_fields=["status"])
            messages.error(request, "پرداخت انجام نشد و سفارش لغو گردید.")

        return redirect("shop:order_invoice", order_number=order.order_number)


class OrderInvoiceView(View):
    """
    نمایش فاکتور و رسید سفارش — کاملاً فقط خواندنی (READ-ONLY)
    به هیچ عنوان وضعیت سفارش را تغییر نمی‌دهد!
    """
    template_name = "payment_result.html"

    def get(self, request, order_number: str = None):
        if not order_number:
            order_number = request.GET.get("order", "").strip()

        order = None
        if order_number:
            order = Order.objects.filter(order_number=order_number).prefetch_related("items").first()

        if not order and request.user.is_authenticated:
            order = Order.objects.filter(user=request.user).prefetch_related("items").first()

        if not order:
            messages.warning(request, "فاکتور سفارش مورد نظر یافت نشد.")
            if request.user.is_authenticated:
                return redirect("shop:user_orders")
            return redirect("shop:home")

        is_success = (order.status != "cancelled")

        return render(request, self.template_name, {
            "order": order,
            "is_success": is_success,
        })


PaymentResultView = OrderInvoiceView


class UserOrdersView(View):
    """
    مشاهده تاریخچه و وضعیت سفارش‌های کاربر در پروفایل
    """
    template_name = "profile/orders.html"

    def get(self, request):
        if not request.user.is_authenticated:
            messages.info(request, "برای مشاهده تاریخچه سفارش‌های خود ابتدا وارد حساب کاربری شوید.")
            return redirect(f"/account/login/?next=/profile/orders/")

        orders = Order.objects.filter(user=request.user).prefetch_related("items").order_by("-created_at")

        return render(request, self.template_name, {
            "orders": orders,
            "user": request.user,
        })
