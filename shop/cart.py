"""
سبد خرید هیبریدی (سشن برای مهمان، دیتابیس پایدار CartItem برای کاربر لاگین)
با خروج از حساب و ورود مجدد، اقلام سبد خرید کاربر به طور کامل حفظ می‌شوند.
"""
from decimal import Decimal
from django.http import HttpRequest
from .models import CartItem, ProductVariant

CART_SESSION_KEY = "shop_cart"  # {str(variant_id): qty_int}


class Cart:
    def __init__(self, request: HttpRequest):
        self.request = request
        self.session = getattr(request, "session", {})
        self.user = request.user if getattr(request, "user", None) and request.user.is_authenticated else None

        if self.user:
            # ۱. همگام‌سازی و انتقال هرگونه قلم سشن به دیتابیس کاربر
            session_cart = self.session.get(CART_SESSION_KEY) if hasattr(self.session, "get") else None
            if isinstance(session_cart, dict) and session_cart:
                for vid_str, qty in session_cart.items():
                    try:
                        vid = int(vid_str)
                        qty = max(1, min(int(qty), 99))
                        item, created = CartItem.objects.get_or_create(
                            user=self.user,
                            variant_id=vid,
                            defaults={"quantity": qty},
                        )
                        if not created:
                            item.quantity = min(99, item.quantity + qty)
                            item.save()
                    except Exception:
                        pass
                self.session[CART_SESSION_KEY] = {}
                if hasattr(self.session, "modified"):
                    self.session.modified = True

            # ۲. بارگذاری سبد خرید از دیتابیس کاربر
            db_items = CartItem.objects.filter(user=self.user)
            self._cart = {str(item.variant_id): item.quantity for item in db_items}
        else:
            cart = self.session.get(CART_SESSION_KEY) if hasattr(self.session, "get") else None
            if not isinstance(cart, dict):
                cart = {}
                if hasattr(self.session, "__setitem__"):
                    self.session[CART_SESSION_KEY] = cart
            self._cart = cart

    def get_qty(self, variant: ProductVariant | int) -> int:
        vid = str(variant.id) if hasattr(variant, "id") else str(variant)
        return int(self._cart.get(vid, 0))

    def add(self, variant: ProductVariant, qty: int = 1) -> None:
        qty = max(1, min(int(qty), 99))
        key = str(variant.id)
        new_qty = min(99, self._cart.get(key, 0) + qty)
        self._cart[key] = new_qty
        if self.user:
            CartItem.objects.update_or_create(
                user=self.user,
                variant=variant,
                defaults={"quantity": new_qty},
            )
        else:
            self.save_session()

    def set_qty(self, variant: ProductVariant, qty: int) -> None:
        qty = int(qty)
        if qty <= 0:
            self.remove(variant)
            return
        new_qty = min(99, max(1, qty))
        self._cart[str(variant.id)] = new_qty
        if self.user:
            CartItem.objects.update_or_create(
                user=self.user,
                variant=variant,
                defaults={"quantity": new_qty},
            )
        else:
            self.save_session()

    def remove(self, variant: ProductVariant | int) -> None:
        vid = str(variant.id) if hasattr(variant, "id") else str(variant)
        self._cart.pop(vid, None)
        if self.user:
            try:
                CartItem.objects.filter(user=self.user, variant_id=int(vid)).delete()
            except Exception:
                pass
        else:
            self.save_session()

    def clear(self) -> None:
        self._cart = {}
        if self.user:
            CartItem.objects.filter(user=self.user).delete()
        if hasattr(self.session, "__setitem__"):
            self.session[CART_SESSION_KEY] = {}
            if hasattr(self.session, "modified"):
                self.session.modified = True

    def save_session(self) -> None:
        if hasattr(self.session, "__setitem__"):
            self.session[CART_SESSION_KEY] = self._cart
            if hasattr(self.session, "modified"):
                self.session.modified = True

    def save(self) -> None:
        if self.user:
            for vid_str, qty in self._cart.items():
                try:
                    CartItem.objects.update_or_create(
                        user=self.user,
                        variant_id=int(vid_str),
                        defaults={"quantity": int(qty)},
                    )
                except Exception:
                    pass
        else:
            self.save_session()

    def __iter__(self):
        """Yield شکل {variant, product, qty, price, subtotal}"""
        vids = [int(k) for k in self._cart.keys()]
        variants = ProductVariant.objects.filter(id__in=vids).select_related("product", "product__category")
        vmap = {v.id: v for v in variants}
        for k, qty in list(self._cart.items()):
            v = vmap.get(int(k))
            if v is None or qty <= 0:
                continue
            yield {
                "variant": v,
                "product": v.product,
                "qty": int(qty),
                "price": int(v.price),
                "subtotal": int(v.price) * int(qty),
            }

    def __len__(self) -> int:
        return sum(int(q) for q in self._cart.values())

    @property
    def quantities(self) -> dict[str, int]:
        """A copy for templates/API helpers: variant id → current cart quantity."""
        return {str(variant_id): int(quantity) for variant_id, quantity in self._cart.items()}

    @property
    def total_price(self) -> int:
        total = 0
        vids = [int(k) for k in self._cart.keys()]
        vmap = {v.id: v for v in ProductVariant.objects.filter(id__in=vids).only("id", "price")}
        for k, qty in self._cart.items():
            v = vmap.get(int(k))
            if v:
                total += int(v.price) * int(qty)
        return total

    @property
    def distinct_count(self) -> int:
        return len(self._cart)
