import hmac

from django.conf import settings
from rest_framework import authentication, exceptions

_SCHEME = "Bearer"


class StaticTokenUser:
    """Minimal authenticated principal for a valid static token.

    The flight API has no user model — a correct token is all it needs — so a
    request carrying the token is represented by this single anonymous-but-
    authenticated user. Only ``is_authenticated`` matters to ``IsAuthenticated``.
    """

    is_authenticated = True

    def __str__(self) -> str:
        return "flight-api-token-user"


class StaticTokenAuthentication(authentication.BaseAuthentication):
    """Authenticate requests by a shared secret in the ``Authorization`` header.

    The header must read ``Authorization: Bearer <token>`` and ``<token>`` must
    equal ``settings.FLIGHT_SEARCH_ACCESS_TOKEN`` (compared in constant time).

    Following DRF's contract: a *missing* credential (no header, or a different
    scheme) returns ``None`` so the request continues unauthenticated and
    ``IsAuthenticated`` produces a 401, while a *malformed or wrong* Bearer
    credential raises ``AuthenticationFailed``. An empty configured token fails
    closed: no request can ever authenticate.
    """

    keyword = _SCHEME

    def authenticate(self, request):
        # Work in bytes throughout so an arbitrary header value can never raise
        # (e.g. hmac.compare_digest rejects non-ASCII ``str``).
        header = authentication.get_authorization_header(request)
        if not header:
            return None

        parts = header.split()
        if not parts:
            # A present-but-whitespace-only header carries no credential.
            return None
        if parts[0].lower() != self.keyword.encode().lower():
            return None
        if len(parts) != 2:
            raise exceptions.AuthenticationFailed("Invalid Authorization header format.")

        configured = settings.FLIGHT_SEARCH_ACCESS_TOKEN
        if not configured or not hmac.compare_digest(parts[1], configured.encode()):
            raise exceptions.AuthenticationFailed("Invalid or missing API token.")

        return (StaticTokenUser(), parts[1].decode("latin-1"))

    def authenticate_header(self, request) -> str:
        # Drives the WWW-Authenticate challenge on 401 responses.
        return self.keyword
