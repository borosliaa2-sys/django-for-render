"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path

from shop.media_views import serve_site_media


def healthz(request):
    """Lightweight endpoint used by Render health checks."""
    return HttpResponse("ok", content_type="text/plain")


urlpatterns = [
    path("healthz/", healthz, name="healthz"),
    # Always same-origin: this view serves a local image and recovers it from
    # Cloudinary server-side only when the local file is absent.
    path("media/<path:media_path>", serve_site_media, name="site_media"),
    path("admin/", admin.site.urls),
    path("", include("shop.urls", namespace="shop")),
    path("account/", include("django.contrib.auth.urls")),
    path("account/", include("account.urls")),
]

handler404 = "shop.views.custom_404"
handler500 = "shop.views.custom_500"

