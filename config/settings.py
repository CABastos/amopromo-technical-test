"""Django settings for the config project."""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
    LOG_LEVEL=(str, "INFO"),
    LOG_STORAGE_ENABLED=(bool, True),
)
environ.Env.read_env(BASE_DIR / ".env")


SECRET_KEY = env(
    "SECRET_KEY",
    default="django-insecure-_r#rvh4(#3g74zjjf8vb8)uie%57&*aht042#8$@8us-kmrzlx",
)

DEBUG = env("DEBUG")

ALLOWED_HOSTS = env("ALLOWED_HOSTS")


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party apps
    "rest_framework",
    # Local apps
    "airport",
    "flight",
    "applog",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://amopromo:amopromo@localhost:5432/amopromo",
    ),
}


# Password validation

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files

STATIC_URL = "static/"

# Default primary key field type

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Logging

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} [{levelname}] {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": env("LOG_LEVEL"),
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

LOG_STORAGE_ENABLED = env("LOG_STORAGE_ENABLED")
if LOG_STORAGE_ENABLED:
    LOGGING["handlers"]["db_log"] = {"class": "applog.handlers.DatabaseLogHandler"}
    LOGGING["loggers"]["airport"] = {"handlers": ["db_log"], "propagate": True}
    LOGGING["loggers"]["flight"] = {"handlers": ["db_log"], "propagate": True}


# External airports API (Problem 1 import source)

AIRPORT_API_BASE_URL = env(
    "AIRPORT_API_BASE_URL",
    default="https://stub.amopromo.com/air/airports",
)
AIRPORT_API_KEY = env("AIRPORT_API_KEY", default="")
AIRPORT_API_USER = env("AIRPORT_API_USER", default="")
AIRPORT_API_PASSWORD = env("AIRPORT_API_PASSWORD", default="")
AIRPORT_API_TIMEOUT = env.float("AIRPORT_API_TIMEOUT", default=10.0)


# Mock Airlines flight search API (Problem 2 provider)

FLIGHT_API_BASE_URL = env(
    "FLIGHT_API_BASE_URL",
    default="https://stub.amopromo.com/air/search",
)
FLIGHT_API_KEY = env("FLIGHT_API_KEY", default="")
FLIGHT_API_USER = env("FLIGHT_API_USER", default="")
FLIGHT_API_PASSWORD = env("FLIGHT_API_PASSWORD", default="")
FLIGHT_API_TIMEOUT = env.float("FLIGHT_API_TIMEOUT", default=10.0)


# Flight search endpoint access token (inbound auth)

FLIGHT_SEARCH_ACCESS_TOKEN = env("FLIGHT_SEARCH_ACCESS_TOKEN", default="")
