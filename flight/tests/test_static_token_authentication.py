import pytest
from rest_framework import exceptions
from rest_framework.test import APIRequestFactory

from flight.api.static_token_authentication import StaticTokenAuthentication

factory = APIRequestFactory()


def _authenticate(header=None):
    kwargs = {"HTTP_AUTHORIZATION": header} if header is not None else {}
    return StaticTokenAuthentication().authenticate(factory.get("/", **kwargs))


def test_no_header_returns_none():
    assert _authenticate() is None


def test_whitespace_only_header_returns_none():
    # Regression: a present-but-whitespace header must be treated as "no
    # credential" (-> None -> 401), not crash with IndexError (-> 500).
    assert _authenticate("   ") is None


def test_non_bearer_scheme_returns_none():
    assert _authenticate("Basic abc") is None


def test_malformed_bearer_raises(settings):
    settings.FLIGHT_SEARCH_ACCESS_TOKEN = "secret"
    with pytest.raises(exceptions.AuthenticationFailed):
        _authenticate("Bearer")  # scheme present, token missing


def test_wrong_token_raises(settings):
    settings.FLIGHT_SEARCH_ACCESS_TOKEN = "secret"
    with pytest.raises(exceptions.AuthenticationFailed):
        _authenticate("Bearer wrong")


def test_valid_token_authenticates(settings):
    settings.FLIGHT_SEARCH_ACCESS_TOKEN = "secret"
    user, token = _authenticate("Bearer secret")
    assert user.is_authenticated and token == "secret"
