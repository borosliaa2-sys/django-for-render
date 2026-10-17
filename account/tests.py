from django.test import TestCase, Client
from django.urls import reverse
from .models import CustomUser


class AccountAuthTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_quick_signup_with_persian_digits_and_8char_password(self):
        signup_data = {
            "first_name": "سارا",
            "last_name": "احمدی",
            "phone_number": "۰۹۱۲۹۸۷۶۵۴۳",
            "password1": "password123",
            "password2": "password123",
        }
        res = self.client.post(reverse("signup"), signup_data, follow=True)
        self.assertEqual(res.status_code, 200)

        user = CustomUser.objects.filter(phone_number="09129876543").first()
        self.assertIsNotNone(user)
        self.assertEqual(user.first_name, "سارا")
        self.assertEqual(user.last_name, "احمدی")
        self.assertEqual(user.get_full_name(), "سارا احمدی")
        self.assertTrue(user.check_password("password123"))

    def test_signup_rejects_password_shorter_than_8_chars(self):
        signup_data = {
            "first_name": "امید",
            "last_name": "نوری",
            "phone_number": "09121113355",
            "password1": "12345",
            "password2": "12345",
        }
        res = self.client.post(reverse("signup"), signup_data)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "حداقل ۸ کاراکتر")

    def test_login_with_phone_number(self):
        user = CustomUser.objects.create_user(
            username="09351112233",
            phone_number="09351112233",
            first_name="رضا",
            last_name="کرمی",
            password="securepassword123"
        )
        login_res = self.client.post(
            reverse("login"),
            {"username": "09351112233", "password": "securepassword123"},
            follow=True
        )
        self.assertEqual(login_res.status_code, 200)
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.id)
