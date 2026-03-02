"""Accounts app configuration."""

from __future__ import annotations

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Django app for player accounts and authentication."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
