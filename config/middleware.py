"""Small deployment middleware used by the Django storefront."""

from django.conf import settings
from django.http import HttpResponsePermanentRedirect, HttpResponseRedirect


class CanonicalHostMiddleware:
    """Send public traffic from aliases to the selected primary hostname.

    Render's ``onrender.com`` URL and the ``www`` alias remain valid service
    hosts, but serving the same shop at multiple URLs creates duplicate public
    pages.  The redirect is opt-in through ``DJANGO_CANONICAL_HOST`` and is
    disabled for local debug sessions.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        canonical_host = getattr(settings, "CANONICAL_HOST", "")
        exempt_paths = getattr(settings, "CANONICAL_REDIRECT_EXEMPT_PATHS", set())

        if (
            getattr(settings, "CANONICAL_REDIRECT_ENABLED", False)
            and canonical_host
            and request.path not in exempt_paths
        ):
            request_host = request.get_host().split(":", 1)[0].lower().rstrip(".")
            if request_host != canonical_host:
                target = f"https://{canonical_host}{request.get_full_path()}"
                # Preserve SEO-friendly permanent redirects for normal pages.
                # A temporary redirect for an unexpected POST avoids silently
                # changing it into a GET at a different host.
                if request.method in {"GET", "HEAD", "OPTIONS"}:
                    return HttpResponsePermanentRedirect(target)
                return HttpResponseRedirect(target)

        return self.get_response(request)
