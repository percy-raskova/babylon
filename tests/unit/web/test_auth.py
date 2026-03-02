"""Tests for session-based authentication (Phase 5).

Tests login/logout views, whoami endpoint, and API auth gating.
"""

from __future__ import annotations

import json

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse


@pytest.mark.unit
@pytest.mark.django_db
class TestLoginView:
    """Verify login page and form submission."""

    def test_login_page_returns_200(self) -> None:
        client = Client()
        response = client.get(reverse("accounts:login"))
        assert response.status_code == 200

    def test_login_page_contains_form(self) -> None:
        client = Client()
        response = client.get(reverse("accounts:login"))
        content = response.content.decode()
        assert "<form" in content
        assert 'name="username"' in content
        assert 'name="password"' in content

    def test_login_success(self) -> None:
        User.objects.create_user(username="tester", password="testpass123")
        client = Client()
        response = client.post(
            reverse("accounts:login"),
            {"username": "tester", "password": "testpass123"},
        )
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["status"] == "ok"
        assert data["data"]["username"] == "tester"

    def test_login_failure_returns_401(self) -> None:
        client = Client()
        response = client.post(
            reverse("accounts:login"),
            {"username": "nobody", "password": "wrong"},
        )
        assert response.status_code == 401
        data = json.loads(response.content)
        assert data["status"] == "error"

    def test_login_creates_session(self) -> None:
        User.objects.create_user(username="tester", password="testpass123")
        client = Client()
        client.post(
            reverse("accounts:login"),
            {"username": "tester", "password": "testpass123"},
        )
        # After login, whoami should return authenticated
        response = client.get(reverse("accounts:whoami"))
        data = json.loads(response.content)
        assert data["data"]["is_authenticated"] is True
        assert data["data"]["username"] == "tester"


@pytest.mark.unit
@pytest.mark.django_db
class TestLogoutView:
    """Verify logout endpoint."""

    def test_logout_requires_post(self) -> None:
        client = Client()
        response = client.get(reverse("accounts:logout"))
        assert response.status_code == 405

    def test_logout_clears_session(self) -> None:
        User.objects.create_user(username="tester", password="testpass123")
        client = Client()
        client.login(username="tester", password="testpass123")

        response = client.post(reverse("accounts:logout"))
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["status"] == "ok"

        # After logout, whoami should show unauthenticated
        response = client.get(reverse("accounts:whoami"))
        data = json.loads(response.content)
        assert data["data"]["is_authenticated"] is False


@pytest.mark.unit
@pytest.mark.django_db
class TestWhoami:
    """Verify whoami endpoint."""

    def test_whoami_unauthenticated(self) -> None:
        client = Client()
        response = client.get(reverse("accounts:whoami"))
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["data"]["is_authenticated"] is False

    def test_whoami_authenticated(self) -> None:
        User.objects.create_user(username="tester", password="testpass123")
        client = Client()
        client.login(username="tester", password="testpass123")

        response = client.get(reverse("accounts:whoami"))
        data = json.loads(response.content)
        assert data["data"]["is_authenticated"] is True
        assert data["data"]["username"] == "tester"
        assert "id" in data["data"]


@pytest.mark.unit
@pytest.mark.django_db
class TestAPIAuthGating:
    """Verify API endpoints are gated behind authentication."""

    def test_game_list_requires_auth(self) -> None:
        client = Client()
        response = client.get(reverse("game:game-list"))
        assert response.status_code == 403

    def test_game_list_accessible_when_logged_in(self) -> None:
        User.objects.create_user(username="tester", password="testpass123")
        client = Client()
        client.login(username="tester", password="testpass123")

        response = client.get(reverse("game:game-list"))
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["status"] == "ok"
        assert isinstance(data["data"], list)


@pytest.mark.unit
class TestAuthURLRouting:
    """Verify auth URL patterns resolve correctly."""

    def test_login_url(self) -> None:
        url = reverse("accounts:login")
        assert url == "/accounts/login/"

    def test_logout_url(self) -> None:
        url = reverse("accounts:logout")
        assert url == "/accounts/logout/"

    def test_whoami_url(self) -> None:
        url = reverse("accounts:whoami")
        assert url == "/accounts/whoami/"
