import os

# Force log storage off before pytest-django imports settings. This root
# conftest runs before django.setup(), and environ's read_env() never overwrites
# a variable already present in os.environ, so this wins over any local .env.
# It keeps the existing DB-free tests from attempting log-table writes; the
# applog tests exercise the handler with an injected fake instead.
os.environ["LOG_STORAGE_ENABLED"] = "False"
