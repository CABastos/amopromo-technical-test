import logging
import time
from datetime import date

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class MockAirlinesApiError(Exception):
    """Raised when the Mock Airlines search API fails or returns an unexpected response."""


class MockAirlinesApiService:
    """HTTP client for the Mock Airlines single-date flight search API."""

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
        """Return the raw search payload for one origin/destination/date."""
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
        except ValueError as exc:
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
