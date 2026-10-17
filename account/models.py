from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    phone_number = models.CharField("شماره همراه", max_length=20, blank=True)
    age = models.PositiveIntegerField("سن", null=True, blank=True)

    def get_full_name(self):
        full = f"{self.first_name} {self.last_name}".strip()
        return full or self.username