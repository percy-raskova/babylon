"""Test configuration for Django web tests.

Uses SQLite in-memory for fast unit tests.
Integration tests in tests/integration/web/ use PostgreSQL.
"""

from __future__ import annotations

import django
from django.conf import settings

# Configure Django settings before any test imports
if not settings.configured:
    settings.configure(
        **{
            "DEBUG": False,
            "SECRET_KEY": "test-secret-key-not-for-production",
            "DATABASES": {
                "default": {
                    "ENGINE": "django.db.backends.sqlite3",
                    "NAME": ":memory:",
                },
            },
            "INSTALLED_APPS": [
                "django.contrib.admin",
                "django.contrib.auth",
                "django.contrib.contenttypes",
                "django.contrib.sessions",
                "django.contrib.messages",
                "django.contrib.staticfiles",
                "rest_framework",
                "corsheaders",
                "game.apps.GameConfig",
                "accounts.apps.AccountsConfig",
            ],
            "ROOT_URLCONF": "babylon_web.urls",
            "MIDDLEWARE": [
                "django.middleware.security.SecurityMiddleware",
                "corsheaders.middleware.CorsMiddleware",
                "django.contrib.sessions.middleware.SessionMiddleware",
                "django.middleware.common.CommonMiddleware",
                "django.middleware.csrf.CsrfViewMiddleware",
                "django.contrib.auth.middleware.AuthenticationMiddleware",
                "django.contrib.messages.middleware.MessageMiddleware",
                "django.middleware.clickjacking.XFrameOptionsMiddleware",
            ],
            "TEMPLATES": [
                {
                    "BACKEND": "django.template.backends.django.DjangoTemplates",
                    "DIRS": [],
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
            ],
            "REST_FRAMEWORK": {
                "DEFAULT_AUTHENTICATION_CLASSES": [
                    "rest_framework.authentication.SessionAuthentication",
                ],
                "DEFAULT_PERMISSION_CLASSES": [
                    "rest_framework.permissions.IsAuthenticated",
                ],
                "DEFAULT_RENDERER_CLASSES": [
                    "rest_framework.renderers.JSONRenderer",
                ],
            },
            "DEFAULT_AUTO_FIELD": "django.db.models.BigAutoField",
            "PASSWORD_HASHERS": [
                "django.contrib.auth.hashers.MD5PasswordHasher",
            ],
        }
    )
    django.setup()
