"""Tests for the health check endpoint."""

from __future__ import annotations

import json

import pytest
from django.test import RequestFactory

from babylon_web.urls import health_check


@pytest.mark.unit
class TestHealthEndpoint:
    """Verify the health check endpoint returns 200 with status ok."""

    def test_health_returns_200(self) -> None:
        factory = RequestFactory()
        request = factory.get("/health/")
        response = health_check(request)
        assert response.status_code == 200

    def test_health_returns_json_status_ok(self) -> None:
        factory = RequestFactory()
        request = factory.get("/health/")
        response = health_check(request)
        data = json.loads(response.content)
        assert data == {"status": "ok"}

    def test_health_content_type_is_json(self) -> None:
        factory = RequestFactory()
        request = factory.get("/health/")
        response = health_check(request)
        assert response["Content-Type"] == "application/json"
