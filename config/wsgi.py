"""WSGI entry point for local development and Render."""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.conf import settings
from django.core.wsgi import get_wsgi_application
from whitenoise import WhiteNoise

application = get_wsgi_application()

# Serve every present MEDIA file from the Attarbashi domain. If an ephemeral
# Render reset has removed a file, WhiteNoise falls through to Django's
# /media/ view, which recovers its Cloudinary backup server-side and caches it
# locally again. A browser is never redirected to Cloudinary.
application = WhiteNoise(application, root=str(settings.MEDIA_ROOT), prefix="media/")
