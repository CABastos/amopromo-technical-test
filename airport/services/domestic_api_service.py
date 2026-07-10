import logging
import time

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class DomesticApiError(Exception):
    """Raised when the external airports API fails or returns an unexpected response."""


class DomesticApiService:
    """HTTP client for the external (domestic) airports API."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        username: str | None = None,
        password: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self._base_url = (base_url or settings.AIRPORT_API_BASE_URL).rstrip("/")
        self._api_key = api_key or settings.AIRPORT_API_KEY
        self._username = username or settings.AIRPORT_API_USER
        self._password = password or settings.AIRPORT_API_PASSWORD
        self._timeout = timeout if timeout is not None else settings.AIRPORT_API_TIMEOUT

    def fetch_airports(self) -> dict:
        """Return the raw airports payload as a dict keyed by IATA code."""
        url = f"{self._base_url}/{self._api_key}"
        logger.info("Fetching airports from domestic API")
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
            logger.error("Domestic API request failed (status=%s): %s", status, exc)
            raise DomesticApiError(f"Failed to fetch airports: {exc}") from exc
        except ValueError as exc:
            logger.error("Domestic API returned invalid JSON: %s", exc)
            raise DomesticApiError(f"Invalid JSON from airports API: {exc}") from exc

        if not isinstance(payload, dict):
            logger.error(
                "Domestic API returned unexpected payload type: %s",
                type(payload).__name__,
            )
            raise DomesticApiError("Airports payload is not a JSON object")

        duration = time.monotonic() - started
        logger.info("Fetched %d airports in %.2fs", len(payload), duration)
        return payload
