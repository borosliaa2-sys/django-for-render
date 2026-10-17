"""
ماژول اتصال به درگاه پرداخت زرین‌پال (Zarinpal REST API v4)
پشتیبانی از ریال/تومان، سَندباکس و درگاه مستقیم
"""
import json
import logging
import urllib.request
import urllib.error
from django.conf import settings

logger = logging.getLogger(__name__)

# آدرس‌های REST API نسخه ۴ زرین‌پال
ZARINPAL_API_REQUEST = "https://payment.zarinpal.com/pg/v4/payment/request.json"
ZARINPAL_API_VERIFY = "https://payment.zarinpal.com/pg/v4/payment/verify.json"
ZARINPAL_STARTPAY = "https://payment.zarinpal.com/pg/StartPay/"

ZARINPAL_SANDBOX_REQUEST = "https://sandbox.zarinpal.com/pg/v4/payment/request.json"
ZARINPAL_SANDBOX_VERIFY = "https://sandbox.zarinpal.com/pg/v4/payment/verify.json"
ZARINPAL_SANDBOX_STARTPAY = "https://sandbox.zarinpal.com/pg/StartPay/"


def get_merchant_id():
    return getattr(settings, "ZARINPAL_MERCHANT_ID", "00000000-0000-0000-0000-000000000000")


def is_sandbox():
    return getattr(settings, "ZARINPAL_SANDBOX", False)


def request_payment(amount_toman: int, description: str, callback_url: str, mobile: str = "", email: str = ""):
    """
    درخواست شناسه پرداخت (Authority) از زرین‌پال
    مقدار amount_toman به تومان است و با واحد IRT به زرین‌پال ارسال می‌شود.
    """
    merchant_id = get_merchant_id()
    sandbox = is_sandbox()
    
    # اگر مرچنت کد تستی باشد، شبیه‌سازی پرداخت انجام می‌شود
    if not merchant_id or merchant_id.startswith("00000000") or merchant_id == "YOUR_MERCHANT_ID":
        logger.info("حالت پرداخت تستی فعال است (مرچنت کد تنظیم نشده است).")
        return {
            "success": True,
            "mode": "test",
            "authority": "TEST_AUTHORITY_12345",
            "url": None,
        }

    api_url = ZARINPAL_SANDBOX_REQUEST if sandbox else ZARINPAL_API_REQUEST
    startpay_url = ZARINPAL_SANDBOX_STARTPAY if sandbox else ZARINPAL_STARTPAY

    data = {
        "merchant_id": merchant_id,
        "amount": int(amount_toman),
        "currency": "IRT",  # تومان
        "description": description[:500],
        "callback_url": callback_url,
        "metadata": {
            "mobile": mobile or "",
            "email": email or "",
        }
    }

    try:
        req = urllib.request.Request(
            api_url,
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            data_body = res_data.get("data", {})
            code = data_body.get("code")
            authority = data_body.get("authority")

            if code == 100 and authority:
                return {
                    "success": True,
                    "mode": "live",
                    "authority": authority,
                    "url": f"{startpay_url}{authority}",
                }
            else:
                errors = res_data.get("errors", {})
                logger.error(f"Zarinpal Request Error: code={code}, errors={errors}")
                return {
                    "success": False,
                    "message": f"خطا در درگاه زرین‌پال (کد {code})",
                    "errors": errors,
                }
    except urllib.error.URLError as e:
        logger.error(f"Zarinpal Network Error: {e}")
        return {
            "success": False,
            "message": "عدم برقراری ارتباط با درگاه زرین‌پال. لطفاً اتصال اینترنت خود را بررسی کنید.",
        }
    except Exception as e:
        logger.error(f"Zarinpal Unexpected Error: {e}")
        return {
            "success": False,
            "message": f"خطای پیش‌بینی نشده: {str(e)}",
        }


def verify_payment(amount_toman: int, authority: str):
    """
    تأیید و راستی‌آزمایی تراکنش با زرین‌پال پس از بازگشت کاربر
    """
    merchant_id = get_merchant_id()
    sandbox = is_sandbox()

    if authority.startswith("TEST_") or not merchant_id or merchant_id.startswith("00000000"):
        return {
            "success": True,
            "mode": "test",
            "ref_id": "TEST_REF_123456",
            "code": 100,
        }

    api_url = ZARINPAL_SANDBOX_VERIFY if sandbox else ZARINPAL_API_VERIFY

    data = {
        "merchant_id": merchant_id,
        "amount": int(amount_toman),
        "authority": authority,
    }

    try:
        req = urllib.request.Request(
            api_url,
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            data_body = res_data.get("data", {})
            code = data_body.get("code")
            ref_id = data_body.get("ref_id")

            if code in (100, 101):  # 100: پرداخت موفق، 101: قبلا وریفای شده
                return {
                    "success": True,
                    "ref_id": str(ref_id),
                    "code": code,
                }
            else:
                errors = res_data.get("errors", {})
                return {
                    "success": False,
                    "code": code,
                    "message": f"تراکنش ناموفق بود یا توسط کاربر لغو شد (کد {code})",
                    "errors": errors,
                }
    except Exception as e:
        logger.error(f"Zarinpal Verify Error: {e}")
        return {
            "success": False,
            "message": f"خطا در تأیید پرداخت: {str(e)}",
        }
