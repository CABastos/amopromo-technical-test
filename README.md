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

## Stack

- Python 3.13
- Django 5.2 LTS
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
└── airport/
    ├── migrations/
    ├── models/                 # Airport ORM model
    ├── dto/                    # AirportDTO + validation
    ├── services/               # DomesticApiService (HTTP)
    ├── repositories/           # AirportRepository (persistence)
    ├── usecases/               # UpsertAirportsUseCase (orchestration)
    ├── management/commands/    # import_airports (job)
    └── tests/                  # use case + DTO unit tests
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

## Tests and linting

```bash
pytest                # unit tests (no database or network required)
ruff check .          # lint
ruff format .         # format
```

The use-case and DTO tests use in-memory fakes and an injected transaction
boundary, so they need neither PostgreSQL nor the external API.

## Scheduling (daily import)

Run the command once a day with cron. Use absolute paths and run from the
project root so the `.env` file is loaded. Example — every day at 03:00:

```cron
0 3 * * * cd /srv/amopromo-technical-test && /srv/amopromo-technical-test/.venv/bin/python manage.py import_airports >> /var/log/import_airports.log 2>&1
```
