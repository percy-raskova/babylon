"""Gating + validation tests for the deep-pane endpoints (spec-099, no DB).

Only the paths that short-circuit before any reader is opened: the feature
flag, authentication, and param validation (bad source / bad uuid). Data paths
are integration tests.
"""

from __future__ import annotations

from typing import Any

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

pytestmark = [pytest.mark.unit, pytest.mark.django_db]

_SID = "edf07b2e-ac2f-4ed7-990e-cadd159ed7b2"

_DEEP = [
    ("observatory:verify", {"session_id": _SID}),
    ("observatory:boundary", {"session_id": _SID}),
    ("observatory:conservation", {"session_id": _SID}),
    ("observatory:diff", {}),
]


def _authed(username: str) -> Client:
    User.objects.create_user(username=username, password="pw12345678")  # noqa: S106
    client = Client()
    client.login(username=username, password="pw12345678")  # noqa: S106
    return client


class TestDeepRouting:
    def test_reverse(self) -> None:
        assert reverse("observatory:verify", kwargs={"session_id": _SID}).endswith("/verify/")
        assert reverse("observatory:diff") == "/api/observatory/diff/"


class TestDeepGating:
    @pytest.mark.parametrize(("name", "kwargs"), _DEEP)
    def test_disabled_404(self, settings: Any, name: str, kwargs: dict[str, str]) -> None:
        settings.OBSERVATORY_ENABLED = False
        assert _authed("d_off").get(reverse(name, kwargs=kwargs)).status_code == 404

    @pytest.mark.parametrize(("name", "kwargs"), _DEEP)
    def test_unauth_forbidden(self, settings: Any, name: str, kwargs: dict[str, str]) -> None:
        settings.OBSERVATORY_ENABLED = True
        assert Client().get(reverse(name, kwargs=kwargs)).status_code in (401, 403)


class TestDeepValidation:
    def test_bad_source_400(self, settings: Any) -> None:
        settings.OBSERVATORY_ENABLED = True
        url = reverse("observatory:verify", kwargs={"session_id": _SID})
        assert _authed("d_src").get(url, {"source": "cloud"}).status_code == 400

    def test_bad_uuid_400(self, settings: Any) -> None:
        settings.OBSERVATORY_ENABLED = True
        url = reverse("observatory:boundary", kwargs={"session_id": "not-a-uuid"})
        assert _authed("d_uuid").get(url).status_code == 400

    def test_diff_missing_ids_400(self, settings: Any) -> None:
        settings.OBSERVATORY_ENABLED = True
        assert _authed("d_diff").get(reverse("observatory:diff")).status_code == 400

    def test_conservation_bad_severity_400(self, settings: Any) -> None:
        settings.OBSERVATORY_ENABLED = True
        url = reverse("observatory:conservation", kwargs={"session_id": _SID})
        assert _authed("d_sev").get(url, {"severity": "loud"}).status_code == 400
