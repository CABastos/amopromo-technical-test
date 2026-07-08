import logging
import time

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class DomesticApiError(Exception):
    """Raised when the external airports API cannot be reached or returns an
    unexpected response.

    Callers depend on this domain exception rather than on ``requests``
    internals, keeping the HTTP library an implementation detail of this layer.
    """


class DomesticApiService:
    """HTTP client for the external (domestic) airports API.

    Fetches the full airport catalogue as a JSON object keyed by IATA code.
    Configuration (URL, API key, Basic Auth credentials, timeout) is injected
    via the constructor and defaults to Django settings, so tests can supply
    fakes and Problem 2's search-API client can reuse this shape.
    """

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
        """Return the raw airports payload as a dict keyed by IATA code.

        Raises:
            DomesticApiError: on any network error, non-2xx status, invalid
                JSON, or a payload that is not a JSON object.
        """
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
        except ValueError as exc:  # includes JSON decode errors
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
