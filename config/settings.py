"""Production-ready Django settings for Attarbashi.

Local development uses SQLite when DATABASE_URL is unset. Render can connect
to Neon through the same standard PostgreSQL DATABASE_URL environment variable.
"""
from __future__ import annotations

import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
# Lets local developers use a private .env file; Railway environment variables
# still take precedence and .env remains excluded from Git.
load_dotenv(BASE_DIR / ".env")


def env_flag(name: str, default: str = "0") -> bool:
    return os.environ.get(name, default).strip().lower() in {"1", "true", "yes", "on"}


def csv_env(name: str) -> list[str]:
    return [item.strip() for item in os.environ.get(name, "").split(",") if item.strip()]


# ----- Core environment -----
_DEFAULT_SECRET_KEY = "django-insecure-local-development-only-change-me-before-production"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", _DEFAULT_SECRET_KEY)
DEBUG = env_flag("DJANGO_DEBUG", "0")
if not DEBUG and SECRET_KEY == _DEFAULT_SECRET_KEY:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is false. "
        "Add it in Railway Variables before deploying."
    )

# Render sets RENDER_EXTERNAL_HOSTNAME to the service's onrender.com host.
# RAILWAY_PUBLIC_DOMAIN is retained as a harmless fallback for local migration
# from the previous deployment bundle.
render_external_hostname = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "").strip()
railway_public_domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "").strip()
deployment_domains = [domain for domain in (render_external_hostname, railway_public_domain) if domain]

configured_hosts = csv_env("DJANGO_ALLOWED_HOSTS")
if DEBUG:
    ALLOWED_HOSTS = ["*"]
else:
    ALLOWED_HOSTS = configured_hosts or ["localhost", "127.0.0.1", "testserver"]
    for domain in deployment_domains:
        if domain not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(domain)

configured_csrf_origins = csv_env("DJANGO_CSRF_TRUSTED_ORIGINS")
if configured_csrf_origins:
    CSRF_TRUSTED_ORIGINS = configured_csrf_origins
else:
    CSRF_TRUSTED_ORIGINS = [
        "https://*.e2b.app",
        "http://*.e2b.app",
        "http://127.0.0.1",
        "http://localhost",
    ]
    for domain in deployment_domains:
        origin = f"https://{domain}"
        if origin not in CSRF_TRUSTED_ORIGINS:
            CSRF_TRUSTED_ORIGINS.append(origin)


# ----- Applications -----
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "shop",
    "account",
]

AUTH_USER_MODEL = "account.CustomUser"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "shop.context_processors.cart",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# ----- Database -----
# Railway's Postgres plugin exposes DATABASE_URL.  SQLite remains a convenient
# fallback for local development and for opening the supplied project offline.
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
        conn_health_checks=True,
    )
}


# ----- Authentication / locale -----
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
]
AUTHENTICATION_BACKENDS = ["account.backends.PhoneOrUsernameAuthBackend"]

LANGUAGE_CODE = "fa-ir"
TIME_ZONE = "Asia/Tehran"
USE_I18N = True
USE_TZ = True
USE_THOUSAND_SEPARATOR = True
THOUSAND_SEPARATOR = ","
NUMBER_GROUPING = 3


# ----- Static and bundled catalogue media -----
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# Compressed manifest assets are generated at build time by `collectstatic`.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ----- Login -----
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "shop:home"
LOGOUT_REDIRECT_URL = "shop:home"


# ----- Production security -----
# Railway terminates TLS before forwarding traffic to Gunicorn.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env_flag("DJANGO_SECURE_SSL_REDIRECT", "0")
SESSION_COOKIE_SECURE = not DEBUG and SECURE_SSL_REDIRECT
CSRF_COOKIE_SECURE = not DEBUG and SECURE_SSL_REDIRECT
SECURE_HSTS_SECONDS = 31536000 if (not DEBUG and SECURE_SSL_REDIRECT) else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG and SECURE_SSL_REDIRECT
SECURE_HSTS_PRELOAD = not DEBUG and SECURE_SSL_REDIRECT
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "SAMEORIGIN" if DEBUG else "DENY"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_REFERRER_POLICY = "same-origin"


# ----- Sessions / logging -----
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7
SESSION_SAVE_EVERY_REQUEST = False
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": os.environ.get("DJANGO_LOG_LEVEL", "WARNING")},
}


# ----- Zarinpal -----
ZARINPAL_MERCHANT_ID = os.environ.get("ZARINPAL_MERCHANT_ID", "00000000-0000-0000-0000-000000000000")
ZARINPAL_SANDBOX = env_flag("ZARINPAL_SANDBOX", "0")
