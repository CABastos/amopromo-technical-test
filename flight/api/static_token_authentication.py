import hmac

from django.conf import settings
from rest_framework import authentication, exceptions

_SCHEME = "Bearer"


class StaticTokenUser:
    """Minimal authenticated principal for a valid static token."""

    is_authenticated = True

    def __str__(self) -> str:
        return "flight-api-token-user"


class StaticTokenAuthentication(authentication.BaseAuthentication):
    """Authenticate requests by a shared secret in the Authorization header."""

    keyword = _SCHEME

    def authenticate(self, request):
        header = authentication.get_authorization_header(request)
        if not header:
            return None

        parts = header.split()
        if not parts:
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
        return self.keyword
