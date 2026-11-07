"""Create the first Django admin from secure deployment environment variables."""

from __future__ import annotations

import os

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        "Create an admin account once when DJANGO_SUPERUSER_USERNAME and "
        "DJANGO_SUPERUSER_PASSWORD are configured. Existing passwords are never changed."
    )

    def handle(self, *args, **options):
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "").strip()
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "").strip()

        if not username or not password:
            self.stdout.write(
                "No superuser bootstrap credentials configured; skipped."
            )
            return

        user_model = get_user_model()
        username_field = user_model.USERNAME_FIELD
        lookup = {username_field: username}
        user = user_model._default_manager.filter(**lookup).first()

        if user:
            changed_fields = []
            if not user.is_staff:
                user.is_staff = True
                changed_fields.append("is_staff")
            if not user.is_superuser:
                user.is_superuser = True
                changed_fields.append("is_superuser")
            if email and hasattr(user, "email") and not user.email:
                user.email = user_model.objects.normalize_email(email)
                changed_fields.append("email")
            if changed_fields:
                user.save(update_fields=changed_fields)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Existing user '{username}' is now an administrator."
                    )
                )
            else:
                self.stdout.write(
                    f"Administrator '{username}' already exists; no changes made."
                )
            return

        create_values = {username_field: username}
        if email and any(field.name == "email" for field in user_model._meta.fields):
            create_values["email"] = user_model.objects.normalize_email(email)

        user = user_model(**create_values)
        try:
            validate_password(password, user=user)
        except ValidationError as exc:
            raise CommandError("رمز مدیر با سیاست رمز عبور سازگار نیست: " + " ".join(exc.messages))

        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save(using=user_model._default_manager.db)
        self.stdout.write(
            self.style.SUCCESS(f"Administrator '{username}' was created successfully.")
        )
