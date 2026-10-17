"""
ویوهای حساب کاربری — ثبت‌نام سریع و امن با لاگین خودکار و حفظ کامل سبد خرید و علاقه‌مندی‌ها
"""
from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import CreateView

from .form import CustomUserCreationForm


class SingUpView(CreateView):
    form_class = CustomUserCreationForm
    template_name = "registration/signup.html"

    def form_valid(self, form):
        user = form.save()
        # لاگین فوری کاربر بلافاصله پس از ثبت‌نام
        login(self.request, user, backend="account.backends.PhoneOrUsernameAuthBackend")
        messages.success(self.request, f"خوش آمدید، حساب کاربری شما با موفقیت ایجاد شد.")

        next_url = self.request.POST.get("next") or self.request.GET.get("next")
        if next_url and url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts={self.request.get_host()},
            require_https=self.request.is_secure(),
        ):
            return redirect(next_url)
        return redirect("shop:home")

