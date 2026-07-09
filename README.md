# AmoPromo Technical Test

Backend service for the AmoPromo technical test.

## Problem 1 — Airport Import Service

A service that caches Brazilian airport data locally (IATA code, city, state,
coordinates) by importing it from an external API. Running it daily means
downstream flight-search features (Problem 2) can validate that an airport
exists and compute Haversine distances from a local table instead of repeatedly
querying the remote API.

The importer is a Django management command:

```bash
python manage.py import_airports
```

Each run inserts new airports, updates existing ones, and **soft-deletes**
airports that disappear from the payload (sets `is_active=False` rather than
removing rows), so history and any future foreign keys stay intact.

## Problem 2 — Flight Search API

A token-protected REST endpoint that searches **round-trip** flights. Given an
origin, destination, departure date, and return date, it queries the Mock
Airlines provider **twice** (the provider searches a single date, so the return
leg is a separate call with the airports swapped), enriches every flight with a
price and meta block, builds all outbound × return combinations, and returns
them sorted ascending by total price.

### Endpoint

```
GET /api/flights/search/?origin=GRU&destination=GIG&departure_date=2030-01-01&return_date=2030-01-05
```

Every request must carry the static bearer token (see
`FLIGHT_SEARCH_ACCESS_TOKEN`):

```bash
curl -H "Authorization: Bearer $FLIGHT_SEARCH_ACCESS_TOKEN" \
  "http://localhost:8000/api/flights/search/?origin=GRU&destination=GIG&departure_date=2030-01-01&return_date=2030-01-05"
```

### Query parameters

| Parameter | Type | Rules |
|---|---|---|
| `origin` | IATA (3 letters) | required; normalized to upper-case; must be a known **active** airport; must differ from `destination` |
| `destination` | IATA (3 letters) | required; same rules as `origin` |
| `departure_date` | `YYYY-MM-DD` | required; not in the past |
| `return_date` | `YYYY-MM-DD` | required; on or after `departure_date` |

### Response

`200 OK` returns the resolved endpoints, the route distance, and every
combination (each a `price` aggregate plus its two enriched legs), ascending by
`price.total`:

```json
{
  "summary": {
    "from": {"iata": "GRU", "city": "Sao Paulo", "state": "SP", "lat": -23.435, "lon": -46.473},
    "to": {"iata": "GIG", "city": "Rio de Janeiro", "state": "RJ", "lat": -22.81, "lon": -43.251},
    "departure_date": "2030-01-01",
    "return_date": "2030-01-05",
    "currency": "BRL",
    "range_km": 338.0
  },
  "count": 1,
  "options": [
    {
      "price": {"fare": 700.0, "fees": 80.0, "total": 780.0},
      "outbound": {
        "departure_time": "2030-01-01T08:00:00",
        "arrival_time": "2030-01-01T10:00:00",
        "aircraft": {"model": "A320", "manufacturer": "Airbus"},
        "price": {"fare": 300.0, "fees": 40.0, "total": 340.0},
        "meta": {"range": 338.0, "cruise_speed_kmh": 169.0, "cost_per_km": 0.89}
      },
      "inbound": {
        "departure_time": "2030-01-01T08:00:00",
        "arrival_time": "2030-01-01T10:00:00",
        "aircraft": {"model": "A320", "manufacturer": "Airbus"},
        "price": {"fare": 400.0, "fees": 40.0, "total": 440.0},
        "meta": {"range": 338.0, "cruise_speed_kmh": 169.0, "cost_per_km": 1.18}
      }
    }
  ]
}
```

Per-flight `price`/`meta` blocks keep the provider's contract field names
(`fees`, `range`); the top-level `price` on each option is the round-trip
aggregate. An empty leg (no flights on a date) is a valid result: `200` with
`options: []`.

### Enrichment

The provider populates only each flight's `fare`; everything else is computed
here (all values rounded to two decimals). `distance_km` is the origin↔
destination great-circle (Haversine) distance, computed once per route:

| Field | Formula |
|---|---|
| `price.fees` (per leg) | `max(fare * 0.10, 40.00)` — 10% of the fare, floored at R$40 |
| `price.total` (per leg) | `fare + fees` |
| `meta.range` | `distance_km` |
| `meta.cruise_speed_kmh` | `distance_km / duration_hours` |
| `meta.cost_per_km` | `fare / distance_km` |

The round-trip `price` is the **sum** of the two legs' `fare`/`fees`/`total`.
It deliberately does **not** re-apply the R$40 fee floor to the combined fare:
each leg already priced its own fee (including the floor), and re-pricing the
pair would silently discount a leg whose fee sat on that floor. This is a
documented ambiguity in the challenge; summing the legs keeps each leg's fee
honest.

### Errors

| Status | When | Body |
|---|---|---|
| `400 Bad Request` | Invalid input (bad IATA, same origin/destination, past departure, return before departure, malformed date) or an unknown/inactive airport | `{"<field>": [...]}` or `{"detail": "..."}` |
| `401 Unauthorized` | Missing or wrong token | `{"detail": "..."}` with a `WWW-Authenticate: Bearer` challenge |
| `502 Bad Gateway` | The flight provider is unreachable or returns an unexpected response | `{"detail": "Flight provider is unavailable."}` |

### Architecture

The `flight` app mirrors the `airport` app's layered shape, but its entry point
is an HTTP view instead of a management command and it persists nothing
(read-only):

```
SearchFlightsView (DRF APIView / delivery)
    │  StaticTokenAuthentication + IsAuthenticated
    │  FlightSearchQuerySerializer → FlightSearchQuery DTO
    ▼
SearchRoundTripUseCase (orchestration)
    ├── AirportRepository.get_active_by_iatas   → airport existence + coordinates
    ├── haversine_km(...)                        → route distance (once)
    └── MockAirlinesApiService.search_flights    → provider HTTP (called twice)
        FlightOptionDTO.from_raw    → per-leg price + meta enrichment
        RoundTripOptionDTO.combine  → outbound × return aggregation
```

- **`api/`** — delivery: `StaticTokenAuthentication` (constant-time bearer-token
  check, fails closed), `FlightSearchQuerySerializer` (shape → delegates the
  domain rules to the DTO), and `SearchFlightsView` (auth, error mapping, JSON
  presenters).
- **`dto/`** — `FlightSearchQuery` (request rules), `FlightOptionDTO` (a
  validated, enriched leg), `RoundTripOptionDTO` (price aggregation).
- **`helpers/haversine_helper.py`** — pure great-circle distance.
- **`services/mock_airlines_api_service.py`** — provider HTTP client; wraps
  failures in `MockAirlinesApiError`.
- **`usecases/search_round_trip_usecase.py`** — orchestration; raises
  `UnknownAirportError` before any provider call when an airport is unknown, and
  skips (logs) individual flights that fail enrichment.

## Stack

- Python 3.13
- Django 5.2 LTS
- Django REST Framework (Problem 2 HTTP layer)
- PostgreSQL 16 (via Docker)
- `psycopg`, `requests`, `django-environ`
- `pytest` / `pytest-django`, `ruff`

## Architecture

The `airport` app is organized in layers, each in its own folder with one file
per component. Dependencies point inward and are passed by constructor
injection (no DI framework), which keeps the use case unit-testable with fakes:

```
import_airports (Job / management command)
        │  instantiates and runs
        ▼
UpsertAirportsUseCase (orchestration)
    ├── DomesticApiService   → HTTP only (fetch payload)
    └── AirportRepository    → persistence only (ORM)
        exchanges AirportDTO (frozen dataclass) between layers
```

- **`services/domestic_api_service.py`** — HTTP client for the external API
  (Basic Auth, timeout, `raise_for_status`); wraps failures in `DomesticApiError`.
- **`dto/airport_dto.py`** — `AirportDTO`, an immutable value object.
  `AirportDTO.from_raw()` owns validation/normalization of a raw record.
- **`repositories/airport_repository.py`** — the only code that touches the ORM.
  `upsert_many()` performs a single `INSERT ... ON CONFLICT DO UPDATE`;
  `deactivate_missing()` soft-deletes airports absent from the payload.
- **`usecases/upsert_airports_usecase.py`** — fetches, validates (skipping
  invalid records), and persists inside one transaction; returns a summary.
  Aborts via `NoValidAirportsError` if **zero** records are valid, which guards
  against a broken/empty payload soft-deleting the entire table.
- **`management/commands/import_airports.py`** — thin wrapper: runs the use
  case, prints the summary, and exits non-zero on failure.

### Project structure

```
amopromo-technical-test/
├── docker-compose.yml          # postgres:16 + healthcheck
├── .env.example                # copy to .env
├── requirements.txt
├── ruff.toml
├── pytest.ini
├── manage.py
├── config/                     # Django project (settings, LOGGING)
├── airport/
│   ├── migrations/
│   ├── models/                # Airport ORM model
│   ├── dto/                   # AirportDTO + validation
│   ├── services/              # DomesticApiService (HTTP)
│   ├── repositories/          # AirportRepository (persistence)
│   ├── usecases/              # UpsertAirportsUseCase (orchestration)
│   ├── management/commands/   # import_airports (job)
│   └── tests/                 # use case + DTO unit tests
├── flight/                    # Problem 2 — read-only, no models
│   ├── api/                   # auth, serializer, view (DRF delivery)
│   ├── dto/                   # query, enriched leg, round-trip aggregation
│   ├── helpers/               # haversine distance
│   ├── services/              # MockAirlinesApiService (HTTP)
│   ├── usecases/              # SearchRoundTripUseCase (orchestration)
│   └── tests/                 # DTO, helper, and use case unit tests
└── applog/                    # cross-cutting — persists airport/flight logs
    ├── migrations/
    ├── models/                # AppLogEntry ORM model
    ├── repositories/          # AppLogRepository (persistence)
    ├── handlers/              # DatabaseLogHandler (logging.Handler)
    ├── management/commands/   # purge_logs (retention job)
    ├── admin.py               # read-only log viewer
    └── tests/                 # handler, repository, admin tests
```

## Data model

`Airport` (table `airport_airport`):

| Field | Type | Notes |
|---|---|---|
| `id` | BigAutoField | surrogate primary key |
| `iata` | CharField(3) | unique (indexed) — used for lookups |
| `city` | CharField(120) | |
| `state` | CharField(2) | Brazilian state abbreviation |
| `lat`, `lon` | FloatField | used for Haversine distance |
| `is_active` | BooleanField | soft-delete flag (default `True`) |
| `created_at` | DateTimeField | `auto_now_add` |
| `updated_at` | DateTimeField | `auto_now` |

`AppLogEntry` (table `applog_applogentry`) — see [Log storage](#log-storage):

| Field | Type | Notes |
|---|---|---|
| `id` | BigAutoField | surrogate primary key |
| `logger_name` | CharField(255) | e.g. `flight.services.mock_airlines_api_service` (indexed) |
| `level` | PositiveSmallIntegerField | numeric level (20, 30, 40…) (indexed) |
| `level_name` | CharField(10) | `INFO`, `WARNING`, `ERROR`, … |
| `message` | TextField | fully interpolated message |
| `func_name` | CharField(255) | originating function |
| `lineno` | PositiveIntegerField | originating line number |
| `traceback` | TextField | formatted exception, empty when none |
| `created_at` | DateTimeField | `auto_now_add` (indexed) — rows are immutable |

## Setup

### Prerequisites

- Python 3.13
- Docker (with Docker Compose)

### 1. Create a virtual environment and install dependencies

```bash
python -m venv .venv
# Windows:      .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure the environment

Copy the example file and fill in the values. The external API credentials
(Basic Auth user/password and the API key) come from the AmoPromo challenge
gist and are **not** committed.

```bash
cp .env.example .env
# then edit .env and set AIRPORT_API_KEY / AIRPORT_API_USER / AIRPORT_API_PASSWORD
```

### 3. Start PostgreSQL

```bash
docker compose up -d
```

The container exposes Postgres on the port from `.env` (`POSTGRES_PORT`, default
`5432`) and reports healthy once ready.

### 4. Apply migrations

```bash
python manage.py migrate
```

## Running the import

```bash
python manage.py import_airports
```

Example output:

```
[INFO] airport.services.domestic_api_service: Fetching airports from domestic API
[INFO] airport.services.domestic_api_service: Fetched 125 airports in 2.81s
[INFO] airport.repositories.airport_repository: Upserted airports: 125 created, 0 updated
[INFO] airport.repositories.airport_repository: Deactivated 0 airports missing from payload
[INFO] airport.usecases.upsert_airports_usecase: Import complete: 125 created, 0 updated, 0 deactivated, 0 skipped
Airport import complete: 125 created, 0 updated, 0 deactivated, 0 skipped
```

Running it again reports `0 created, N updated` — the operation is idempotent.
On failure (e.g. the API is unreachable) the command logs the error and exits
with a non-zero status without modifying the database.

## Running the flight search API

The Problem 2 endpoint needs the airport table populated (run the import above),
the provider credentials, and an access token. In `.env`, set the `FLIGHT_API_*`
variables (same Basic Auth as the airports API, distinct key/URL) and generate a
token for `FLIGHT_SEARCH_ACCESS_TOKEN`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Then start the development server and call the endpoint (see
[Problem 2 — Flight Search API](#problem-2--flight-search-api) for the full
contract):

```bash
python manage.py runserver
curl -H "Authorization: Bearer $FLIGHT_SEARCH_ACCESS_TOKEN" \
  "http://localhost:8000/api/flights/search/?origin=GRU&destination=GIG&departure_date=2030-01-01&return_date=2030-01-05"
```

`FLIGHT_SEARCH_ACCESS_TOKEN` fails closed: with no token configured, the
endpoint rejects every request with `401`.

## Log storage

Application logs from the `airport.*` and `flight.*` loggers are persisted to
the `app_log_entry` table (the `applog` app) in addition to the console. This is
handled by a custom `logging.Handler` wired into `LOGGING` in `config/settings.py`
and attached to those two loggers, so the existing `logging.getLogger(__name__)`
calls flow into the database with no change to the app code. Console output is
unchanged — each record is printed once and stored once.

Toggle it with `LOG_STORAGE_ENABLED` in `.env` (default `True`); when off, the
logging config is identical to console-only. The test suite forces it off so the
unit tests stay database-free.

View stored logs in the Django admin (read-only, filterable by level and logger,
searchable, with a date drill-down):

```bash
python manage.py createsuperuser
python manage.py runserver
# then open http://localhost:8000/admin/ and select "App log entries"
```

Retention is a separate cron-friendly command — delete entries older than N days
(default 30):

```bash
python manage.py purge_logs --days 30
```

The handler writes one row synchronously per record and never raises: a database
failure degrades to a dropped log row, never a failed request or import. At
higher volume the natural evolution is batched or asynchronous writes.

## Tests and linting

```bash
pytest                # unit tests (no database or network required)
ruff check .          # lint
ruff format .         # format
```

The unit tests (DTOs, the haversine helper, and both use cases) run on in-memory
fakes — and, for the import, an injected transaction boundary — so they need
neither PostgreSQL nor the external APIs. The one exception is
`applog/tests/test_app_log_repository.py`, which exercises real ORM writes and is
marked `@pytest.mark.django_db`; it needs the docker-compose Postgres running
(`docker compose up -d`). Everything else, including the log handler and admin
tests, stays database-free.

## Scheduling (daily import)

Run the command once a day with cron. Use absolute paths and run from the
project root so the `.env` file is loaded. Example — every day at 03:00:

```cron
0 3 * * * cd /srv/amopromo-technical-test && /srv/amopromo-technical-test/.venv/bin/python manage.py import_airports >> /var/log/import_airports.log 2>&1
```
