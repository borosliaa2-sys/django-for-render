from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .form import CustomUserChangeForm, CustomUserCrationForm
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCrationForm
    form = CustomUserChangeForm
    model = CustomUser
    list_display = [
        'username',
        'first_name',
        'last_name',
        'phone_number',
        'email',
        'is_staff',
    ]

    fieldsets = UserAdmin.fieldsets + ((None, {"fields" : ('phone_number', 'age')}),)
    add_fieldsets = UserAdmin.add_fieldsets + ((None, {"fields" : ('phone_number', 'age')}),)

admin.site.register(CustomUser, CustomUserAdmin)