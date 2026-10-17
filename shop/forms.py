from django import forms
from .models import Review


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