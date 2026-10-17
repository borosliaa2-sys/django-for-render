"""WSGI entry point for local development and Railway."""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.conf import settings
from django.core.wsgi import get_wsgi_application
from whitenoise import WhiteNoise

application = get_wsgi_application()

# Product imagery is curated catalogue data committed with this repository, not
# user-generated files. Serving this fixed media directory through WhiteNoise
# makes /media/products/catalog/... available on Railway without a second CDN.
# For future user uploads, use a Railway Volume or object storage instead.
application = WhiteNoise(application, root=str(settings.MEDIA_ROOT), prefix="/media/")
