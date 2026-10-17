"""
فرم‌های کاربری — ثبت‌نام سریع و تفکیک‌شده (نام، نام خانوادگی، شماره تماس، رمز عبور آسان)
"""
from django import forms
from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth.password_validation import validate_password
from .models import CustomUser


def clean_digits(val: str) -> str:
    if not val:
        return ""
    val = str(val).strip()
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    arabic_digits = "٠١٢٣٤٥٦٧٨٩"
    for p, a, d in zip(persian_digits, arabic_digits, "0123456789"):
        val = val.replace(p, d).replace(a, d)
    return val.replace(" ", "").replace("-", "")


class CustomUserCreationForm(forms.ModelForm):
    """
    فرم ثبت‌نام سریع و روان:
    - تفکیک دقیق نام و نام خانوادگی جهت تکمیل خودکار اطلاعات سفارش
    - شماره تلفن همراه جهت ورود و ارسال پیامک رهگیری
    - رمز عبور آسان و بدون سخت‌گیری
    """
    first_name = forms.CharField(
        label="نام",
        max_length=60,
        required=True,
        widget=forms.TextInput(attrs={
            "placeholder": "مثال: علی",
            "class": "auth-input",
            "autocomplete": "given-name",
            "autofocus": True,
        }),
    )
    last_name = forms.CharField(
        label="نام خانوادگی",
        max_length=60,
        required=True,
        widget=forms.TextInput(attrs={
            "placeholder": "مثال: محمدی",
            "class": "auth-input",
            "autocomplete": "family-name",
        }),
    )
    phone_number = forms.CharField(
        label="شماره تلفن همراه (نام کاربری برای ورود)",
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            "placeholder": "مثال: 09123456789",
            "class": "auth-input",
            "type": "tel",
            "autocomplete": "tel",
        }),
    )
    password1 = forms.CharField(
        label="رمز عبور",
        widget=forms.PasswordInput(attrs={
            "placeholder": "حداقل ۸ کاراکتر",
            "class": "auth-input",
            "autocomplete": "new-password",
        }),
        help_text="",
    )
    password2 = forms.CharField(
        label="تکرار رمز عبور",
        widget=forms.PasswordInput(attrs={
            "placeholder": "تکرار رمز عبور",
            "class": "auth-input",
            "autocomplete": "new-password",
        }),
        help_text="",
    )

    class Meta:
        model = CustomUser
        fields = ("first_name", "last_name", "phone_number")

    def clean_phone_number(self):
        phone = clean_digits(self.cleaned_data.get("phone_number", ""))
        if phone.startswith("+98"):
            phone = "0" + phone[3:]
        elif phone.startswith("98") and len(phone) == 12:
            phone = "0" + phone[2:]
        elif len(phone) == 10 and phone.startswith("9"):
            phone = "0" + phone

        if not phone.isdigit() or len(phone) < 10:
            raise forms.ValidationError("لطفاً یک شماره تلفن همراه معتبر وارد کنید (مثال: 09123456789).")

        # بررسی عدم تکراری بودن شماره تلفن یا نام کاربری
        if CustomUser.objects.filter(username=phone).exists() or CustomUser.objects.filter(phone_number=phone).exists():
            raise forms.ValidationError("کاربری با این شماره همراه قبلاً ثبت‌نام کرده است. لطفاً وارد شوید.")

        return phone

    def clean_password1(self):
        p1 = self.cleaned_data.get("password1", "")
        if len(p1) < 8:
            raise forms.ValidationError("رمز عبور باید حداقل ۸ کاراکتر باشد.")
        return p1

    def clean_password2(self):
        p1 = self.cleaned_data.get("password1")
        p2 = self.cleaned_data.get("password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("تکرار رمز عبور با رمز عبور وارد شده مطابقت ندارد.")
        return p2

    def save(self, commit=True):
        user = super().save(commit=False)
        phone = self.cleaned_data.get("phone_number")
        user.username = phone
        user.phone_number = phone
        user.first_name = self.cleaned_data.get("first_name", "").strip()
        user.last_name = self.cleaned_data.get("last_name", "").strip()
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class CustomUserChangeForm(UserChangeForm):
    """فرم ویرایش کاربر در ادمین"""
    class Meta:
        model = CustomUser
        fields = UserChangeForm.Meta.fields


# حفظ نام‌های قدیمی برای سازگاری با کدهای قبلی
CustomUserCrationForm = CustomUserCreationForm
CustomUserCrationForm.__name__ = "CustomUserCrationForm"
CustomUserChangeForm.__name__ = "CustomUserChangeForm"
