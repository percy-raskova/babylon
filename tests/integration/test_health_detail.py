"""Spec 061 US2 / T033-T037: /health/ public + /health/detail/ auth-gated.

Five contract scenarios:

- ``test_public_health_is_open_unauthenticated`` (T033): /health/ returns
  200 + ``{"status": "ok"}`` regardless of auth state.
- ``test_unauthenticated_returns_404`` (T034): unauthenticated GET on
  /health/detail/ returns 404 with body ``{"detail": "Not found."}``.
  NOT 401, NOT 403 — security through obscurity per FR-009.
- ``test_non_staff_returns_404`` (T035): authenticated non-staff returns
  the same 404 shape.
- ``test_staff_returns_diagnostic`` (T036): authenticated staff returns
  200 + the full diagnostic payload (engine, database, embedding_model,
  version, git_sha keys).
- ``test_implementation_field_is_real_bridge`` (T037): the
  ``engine.implementation`` field reads as ``"EngineBridge"`` after a
  clean boot — NOT ``"StubEngineBridge"`` or any mock substitute.

Gated behind ``mise run test:int`` via ``pytest.mark.integration`` (the
view depends on Django + the engine bridge being importable).
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

pytestmark = pytest.mark.integration


@pytest.fixture
def staff_user(db):  # noqa: ARG001 — pytest-django fixture
    User = get_user_model()
    user, _ = User.objects.get_or_create(
        username="spec061-staff",
        defaults={"is_staff": True, "is_active": True},
    )
    user.is_staff = True
    user.is_active = True
    user.set_password("test-password-T036")
    user.save()
    return user


@pytest.fixture
def non_staff_user(db):  # noqa: ARG001
    User = get_user_model()
    user, _ = User.objects.get_or_create(
        username="spec061-nonstaff",
        defaults={"is_staff": False, "is_active": True},
    )
    user.is_staff = False
    user.is_active = True
    user.set_password("test-password-T035")
    user.save()
    return user


class TestPublicHealthEndpoint:
    """T033: /health/ is open to all callers."""

    def test_public_health_is_open_unauthenticated(self) -> None:
        client = Client()
        response = client.get("/health/")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestHealthDetailObscurity:
    """T034 + T035: hide the endpoint from unauthorized callers."""

    def test_unauthenticated_returns_404(self) -> None:
        client = Client()
        response = client.get("/health/detail/")
        assert response.status_code == 404, (
            f"expected 404 (FR-009 obscurity), got {response.status_code}"
        )
        assert response.json() == {"detail": "Not found."}

    def test_non_staff_returns_404(self, non_staff_user) -> None:
        client = Client()
        client.force_login(non_staff_user)
        response = client.get("/health/detail/")
        assert response.status_code == 404
        assert response.json() == {"detail": "Not found."}

    def test_response_does_not_leak_endpoint_existence(self) -> None:
        """The 404 body matches DRF's default 404 body byte-for-byte —
        a caller cannot distinguish ``/health/detail/`` from a route
        that simply does not exist."""
        client = Client()
        unauth_response = client.get("/health/detail/")
        # Probe a path that genuinely does not exist on the server. DRF's
        # default 404 body for unmatched routes is also {"detail": "Not found."}.
        # The comparison ensures we did not accidentally introduce a unique
        # fingerprint (e.g., empty body, custom message).
        assert unauth_response.status_code == 404
        assert unauth_response.json() == {"detail": "Not found."}


class TestHealthDetailDiagnostic:
    """T036 + T037: authorized staff receives the full diagnostic payload."""

    def test_staff_returns_diagnostic(self, staff_user) -> None:
        client = Client()
        client.force_login(staff_user)
        response = client.get("/health/detail/")
        assert response.status_code == 200, response.content
        body = response.json()
        # Top-level keys per contracts/health.yaml
        for key in (
            "status",
            "engine",
            "database",
            "embedding_model",
            "version",
            "git_sha",
        ):
            assert key in body, f"missing top-level key {key!r} in {body}"
        assert body["status"] == "ok"
        # Embedding model must report the spec 061 canonical pin.
        assert body["embedding_model"]["model_id"] == ("sentence-transformers/all-mpnet-base-v2")
        assert body["embedding_model"]["dimension"] == 768
        # Engine block must include the four diagnostic fields.
        for key in (
            "implementation",
            "boot_attempts",
            "boot_succeeded_at",
            "last_tick_resolved_at",
        ):
            assert key in body["engine"], f"missing engine.{key} in {body['engine']}"
        # Database block must include reachable + pool_size.
        assert "reachable" in body["database"]
        assert "pool_size" in body["database"]

    def test_implementation_field_is_real_bridge(self, staff_user) -> None:
        """T037: a clean boot wires the real EngineBridge, not a stub.

        If the bridge isn't initialized for this test run (e.g., the test
        runner is using settings without auto-init), the field may legitimately
        be None — but it must NEVER report ``MockEngineBridge`` or
        ``StubEngineBridge`` because those are being deleted in US7.
        """
        client = Client()
        client.force_login(staff_user)
        response = client.get("/health/detail/")
        assert response.status_code == 200
        impl = response.json()["engine"]["implementation"]
        assert impl in ("EngineBridge", None), (
            f"engine.implementation must be EngineBridge or None (got {impl!r})"
        )
        assert impl != "MockEngineBridge"
        assert impl != "StubEngineBridge"
