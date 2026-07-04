"""Base Django settings for the Babylon web application.

All secrets are sourced from environment variables.
Submodules (development.py, production.py) import ``*`` from here
and override as needed.
"""

from __future__ import annotations

import os
from pathlib import Path

from observatory.db import build_sim_database_alias, default_sim_dsn

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # web/

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-dev-only-change-in-production",
)

DEBUG = False

ALLOWED_HOSTS: list[str] = []

# --------------------------------------------------------------------------- #
# Application definition
# --------------------------------------------------------------------------- #
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "corsheaders",
    # Project apps
    "game.apps.GameConfig",
    "accounts.apps.AccountsConfig",
    # spec-096 Observatory — read-only debug dashboard over the simulation DB.
    "observatory.apps.ObservatoryConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "babylon_web.middleware.RequestLoggingMiddleware",
    # spec 061 T127 FR-010: turn mid-session DB-unreachable into HTTP 503.
    "babylon_web.middleware.EngineAvailabilityMiddleware",
]

ROOT_URLCONF = "babylon_web.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "babylon_web.wsgi.application"

# --------------------------------------------------------------------------- #
# Database — PostGIS backend for H3 spatial queries
# --------------------------------------------------------------------------- #
DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": os.environ.get("POSTGRES_DB", "babylon"),
        "USER": os.environ.get("POSTGRES_USER", "babylon"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "babylon"),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    },
    # spec-096: the second, READ-ONLY alias pointing at the simulation runner's
    # Postgres (spec-062 dynamic_* schema + spec-087-089 additions). DSN from
    # BABYLON_PG_DSN (default localhost:5433/babylon_test — the tick_probe
    # pattern). The SimDatabaseRouter refuses migrations for this alias; the
    # connection is opened default_transaction_read_only=on. See
    # observatory/db.py and web/HOW-TO-LOCAL-DEV.md (two-DB alias map).
    "sim": build_sim_database_alias(default_sim_dsn()),
}

# spec-096: only SimDatabaseRouter refuses migrations for the "sim" alias;
# it abstains on all product-model routing.
DATABASE_ROUTERS = ["observatory.router.SimDatabaseRouter"]

# spec-096: master feature flag for the Observatory dashboard + endpoints.
# Enabled by default here; production.py flips it off (development.py keeps On).
OBSERVATORY_ENABLED = True

# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/api/games/"

# --------------------------------------------------------------------------- #
# i18n
# --------------------------------------------------------------------------- #
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# --------------------------------------------------------------------------- #
# Static files
# --------------------------------------------------------------------------- #
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# --------------------------------------------------------------------------- #
# Django REST Framework
# --------------------------------------------------------------------------- #
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    # spec 061 US2 FR-009: HealthDetailView raises NotAuthenticated /
    # PermissionDenied via standard DRF permission classes; this custom
    # exception handler intercepts THOSE specific exceptions for THAT
    # specific view and returns a uniform 404 with the standard DRF body.
    # Every other endpoint preserves DRF's normal 401/403 behavior.
    # See research.md R5 + DRF issue #7529 for why we don't use
    # has_permission() raising Http404.
    "EXCEPTION_HANDLER": "babylon_web.health.exceptions.health_obscuring_exception_handler",
}

# --------------------------------------------------------------------------- #
# Misc
# --------------------------------------------------------------------------- #
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --------------------------------------------------------------------------- #
# Logging — structured JSON output for all layers
# --------------------------------------------------------------------------- #
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "babylon_web.log_formatter.WebJSONFormatter",
        },
        "console": {
            "format": "[{asctime}] {levelname:<8} {name}: {message}",
            "style": "{",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "console",
            "level": "INFO",
        },
        "file_json": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_DIR / "web.jsonl"),
            "maxBytes": 10_000_000,  # 10 MB
            "backupCount": 5,
            "formatter": "json",
            "level": "DEBUG",
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_DIR / "web_errors.jsonl"),
            "maxBytes": 5_000_000,  # 5 MB
            "backupCount": 10,
            "formatter": "json",
            "level": "ERROR",
        },
    },
    "loggers": {
        # Django internals
        "django": {
            "handlers": ["console", "file_json"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console", "file_json", "error_file"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["file_json"],
            "level": os.environ.get("DJANGO_DB_LOG_LEVEL", "WARNING"),
            "propagate": False,
        },
        # Application loggers
        "babylon_web": {
            "handlers": ["console", "file_json", "error_file"],
            "level": "DEBUG",
            "propagate": False,
        },
        "babylon_web.request": {
            "handlers": ["console", "file_json"],
            "level": "INFO",
            "propagate": False,
        },
        "game": {
            "handlers": ["console", "file_json", "error_file"],
            "level": "DEBUG",
            "propagate": False,
        },
        "game.engine_bridge": {
            "handlers": ["console", "file_json", "error_file"],
            "level": "DEBUG",
            "propagate": False,
        },
        "accounts": {
            "handlers": ["console", "file_json"],
            "level": "INFO",
            "propagate": False,
        },
        # Babylon engine (when called via bridge)
        "babylon": {
            "handlers": ["file_json"],
            "level": os.environ.get("ENGINE_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console", "file_json"],
        "level": "WARNING",
    },
}
