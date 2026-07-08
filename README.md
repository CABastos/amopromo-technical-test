# AmoPromo Technical Test

Backend service for the AmoPromo technical test.

## Problem 1 — Airport Import Service

A daily service that caches Brazilian airport data locally (IATA code, city, state,
coordinates) by importing it from an external API, so downstream flight-search
features can validate airports and compute distances without repeatedly hitting the
remote API.

The importer runs as a Django management command:

```bash
python manage.py import_airports
```

> Full setup, usage, and scheduling instructions are documented later (see the
> Problem 1 documentation step). This is a skeleton.

## Stack

- Python 3.13
- Django 5.2 LTS
- PostgreSQL 16 (via Docker)
- `psycopg`, `requests`, `django-environ`
- `pytest` / `pytest-django`, `ruff`
