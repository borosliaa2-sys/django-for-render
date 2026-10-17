"""
بک‌اند احراز هویت با شماره تلفن یا نام کاربری + تبدیل خودکار اعداد فارسی و عربی
"""
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from .models import CustomUser


def normalize_phone_number(val: str) -> str:
    if not val:
        return ""
    val = str(val).strip()
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    arabic_digits = "٠١٢٣٤٥٦٧٨٩"
    for p, a, d in zip(persian_digits, arabic_digits, "0123456789"):
        val = val.replace(p, d).replace(a, d)
    return val.replace(" ", "").replace("-", "").replace("+98", "0")


class PhoneOrUsernameAuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None
        
        raw_val = str(username).strip()
        norm_val = normalize_phone_number(raw_val)

        try:
            # جستجو بر اساس نام کاربری یا شماره همراه
            user = CustomUser.objects.filter(
                Q(username__iexact=raw_val)
                | Q(username__iexact=norm_val)
                | Q(phone_number=norm_val)
                | Q(phone_number=raw_val)
            ).first()

            if user and user.check_password(password):
                return user
        except Exception:
            return None

        return None
