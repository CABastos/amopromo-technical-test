import os

# Disable DB log storage before Django reads settings, so tests stay DB-free.
os.environ["LOG_STORAGE_ENABLED"] = "False"
