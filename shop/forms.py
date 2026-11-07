from django import forms

from .models import ContactMessage, Review


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["guest_name", "rating", "comment"]
        widgets = {
            "comment": forms.Textarea(attrs={"rows": 3, "placeholder": "نظر خود را بنویسید…"}),
            "guest_name": forms.TextInput(attrs={"placeholder": "نام شما (اختیاری اگر لاگین هستید)"}),
        }
        labels = {"guest_name": "نام", "rating": "امتیاز", "comment": "متن نظر"}

    def clean_comment(self):
        v = self.cleaned_data["comment"].strip()
        if len(v) < 5:
            raise forms.ValidationError("نظر خیلی کوتاه است.")
        return v


class ContactMessageForm(forms.ModelForm):
    """Server-validated contact form; every valid request is stored for admin follow-up."""

    class Meta:
        model = ContactMessage
        fields = ["full_name", "phone", "email", "category", "message"]
        widgets = {
            "full_name": forms.TextInput(
                attrs={"placeholder": "نام و نام خانوادگی شما", "autocomplete": "name"}
            ),
            "phone": forms.TelInput(
                attrs={"placeholder": "مثال: ۰۹۹۶۰۵۵۵۷۸۹", "autocomplete": "tel", "inputmode": "tel"}
            ),
            "email": forms.EmailInput(
                attrs={"placeholder": "در صورت تمایل", "autocomplete": "email", "dir": "ltr"}
            ),
            "category": forms.Select(),
            "message": forms.Textarea(
                attrs={"rows": 5, "placeholder": "متن پیام، درخواست یا سوال خود را بنویسید…"}
            ),
        }
        labels = {
            "full_name": "نام و نام خانوادگی",
            "phone": "شماره تماس",
            "email": "ایمیل (اختیاری)",
            "category": "دسته‌بندی پیام",
            "message": "متن پیام یا سوال",
        }

    def clean_full_name(self):
        value = self.cleaned_data["full_name"].strip()
        if len(value) < 2:
            raise forms.ValidationError("لطفاً نام کامل‌تری وارد کنید.")
        return value

    def clean_phone(self):
        value = self.cleaned_data["phone"].strip()
        english_digits = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
        normalized = value.translate(english_digits).replace(" ", "").replace("-", "")
        digits = normalized.lstrip("+")
        if not digits.isdigit() or not 8 <= len(digits) <= 15:
            raise forms.ValidationError("لطفاً یک شماره تماس معتبر وارد کنید.")
        return normalized

    def clean_message(self):
        value = self.cleaned_data["message"].strip()
        if len(value) < 10:
            raise forms.ValidationError("برای رسیدگی بهتر، پیام را حداقل در ۱۰ نویسه بنویسید.")
        return value
