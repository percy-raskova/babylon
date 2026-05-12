"""Spec 061 US2 — health endpoints package.

Two endpoints:

- ``GET /health/`` (public, function view in ``babylon_web.urls``):
  returns 200 with ``{"status": "ok"}``. Used by load balancers /
  monitoring for liveness probes.
- ``GET /health/detail/`` (auth-gated, :class:`HealthDetailView` below):
  returns the diagnostic payload (engine identity, boot attempts,
  database reachability, embedding model, version + git SHA) when the
  caller is an authenticated staff user; returns 404 with the standard
  DRF body otherwise (FR-009 — security through obscurity for the
  endpoint's existence).

See ``contracts/health.yaml`` for the canonical response shape.
"""

from __future__ import annotations

from babylon_web.health.exceptions import health_obscuring_exception_handler
from babylon_web.health.permissions import IsStaff
from babylon_web.health.views import HealthDetailView

__all__ = [
    "HealthDetailView",
    "IsStaff",
    "health_obscuring_exception_handler",
]
