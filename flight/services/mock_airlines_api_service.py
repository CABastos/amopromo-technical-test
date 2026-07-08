import logging
import time
from datetime import date

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class MockAirlinesApiError(Exception):
    """Raised when the Mock Airlines search API cannot be reached or returns an
    unexpected response.

    Callers depend on this domain exception rather than on ``requests``
    internals, keeping the HTTP library an implementation detail of this layer.
    The use case maps it to a 502 (bad gateway) at the delivery boundary.
    """


class MockAirlinesApiService:
    """HTTP client for the Mock Airlines single-date flight search API.

    The provider cannot combine two dates in one call, so a round-trip search
    invokes :meth:`search_flights` twice (outbound, then the swapped route for
    the return). Configuration (URL, API key, Basic Auth credentials, timeout)
    is injected via the constructor and defaults to Django settings, mirroring
    :class:`airport.services.DomesticApiService` so tests can supply fakes.
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        username: str | None = None,
        password: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self._base_url = (base_url or settings.FLIGHT_API_BASE_URL).rstrip("/")
        self._api_key = api_key or settings.FLIGHT_API_KEY
        self._username = username or settings.FLIGHT_API_USER
        self._password = password or settings.FLIGHT_API_PASSWORD
        self._timeout = timeout if timeout is not None else settings.FLIGHT_API_TIMEOUT

    def search_flights(self, origin: str, destination: str, flight_date: date) -> dict:
        """Return the raw search payload for one origin/destination/date.

        The payload is a dict with a ``summary`` block and an ``options`` list
        (possibly empty). The list is validated here so downstream layers can
        trust its type.

        Raises:
            MockAirlinesApiError: on any network error, non-2xx status, invalid
                JSON, a payload that is not a JSON object, or a missing/non-list
                ``options`` field.
        """
        url = f"{self._base_url}/{self._api_key}/{origin}/{destination}/{flight_date.isoformat()}"
        logger.info("Searching flights %s->%s on %s", origin, destination, flight_date.isoformat())
        started = time.monotonic()

        try:
            response = requests.get(
                url,
                auth=(self._username, self._password),
                timeout=self._timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            status = exc.response.status_code if exc.response is not None else "n/a"
            logger.error("Flight search request failed (status=%s): %s", status, exc)
            raise MockAirlinesApiError(f"Failed to search flights: {exc}") from exc
        except ValueError as exc:  # includes JSON decode errors
            logger.error("Flight search returned invalid JSON: %s", exc)
            raise MockAirlinesApiError(f"Invalid JSON from flight search API: {exc}") from exc

        if not isinstance(payload, dict):
            logger.error(
                "Flight search returned unexpected payload type: %s",
                type(payload).__name__,
            )
            raise MockAirlinesApiError("Flight search payload is not a JSON object")
        if not isinstance(payload.get("options"), list):
            logger.error("Flight search payload missing a list of options")
            raise MockAirlinesApiError("Flight search payload has no options list")

        duration = time.monotonic() - started
        logger.info("Found %d flight options in %.2fs", len(payload["options"]), duration)
        return payload
