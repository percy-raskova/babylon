"""Tests for Django settings configuration."""

from __future__ import annotations

import pytest
from django.conf import settings


@pytest.mark.unit
class TestBaseSettings:
    """Verify base settings are correctly configured."""

    def test_installed_apps_contains_game(self) -> None:
        assert "game.apps.GameConfig" in settings.INSTALLED_APPS

    def test_installed_apps_contains_accounts(self) -> None:
        assert "accounts.apps.AccountsConfig" in settings.INSTALLED_APPS

    def test_installed_apps_contains_rest_framework(self) -> None:
        assert "rest_framework" in settings.INSTALLED_APPS

    def test_installed_apps_contains_corsheaders(self) -> None:
        assert "corsheaders" in settings.INSTALLED_APPS

    def test_root_urlconf(self) -> None:
        assert settings.ROOT_URLCONF == "babylon_web.urls"

    def test_drf_default_authentication(self) -> None:
        auth_classes = settings.REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"]
        assert "rest_framework.authentication.SessionAuthentication" in auth_classes

    def test_drf_default_permission(self) -> None:
        perm_classes = settings.REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"]
        assert "rest_framework.permissions.IsAuthenticated" in perm_classes

    def test_drf_json_renderer_only(self) -> None:
        renderers = settings.REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"]
        assert renderers == ["rest_framework.renderers.JSONRenderer"]

    def test_cors_middleware_present(self) -> None:
        assert "corsheaders.middleware.CorsMiddleware" in settings.MIDDLEWARE
