"""DRF permission class enforcing staff-only access to /health/detail/."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework.permissions import BasePermission

if TYPE_CHECKING:
    from rest_framework.request import Request
    from rest_framework.views import APIView


class IsStaff(BasePermission):
    """Allow only authenticated users with ``is_staff=True``.

    Used by :class:`babylon_web.health.views.HealthDetailView`. Combined
    with :class:`rest_framework.permissions.IsAuthenticated` so that
    anonymous requests fail at ``IsAuthenticated`` (raising
    ``NotAuthenticated``) and authenticated non-staff fail here
    (raising ``PermissionDenied``). Both exceptions are caught by the
    spec 061 :func:`health_obscuring_exception_handler` and remapped
    to a uniform 404, hiding the endpoint's existence.
    """

    message = "Not found."  # ignored by the custom handler; documented for clarity.

    def has_permission(self, request: Request, view: APIView) -> bool:  # noqa: ARG002 — DRF protocol
        user = getattr(request, "user", None)
        return bool(user is not None and getattr(user, "is_staff", False))
