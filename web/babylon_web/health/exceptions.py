"""Custom DRF exception handler that hides ``/health/detail/`` from non-staff.

Spec 061 FR-009 (clarified): the auth-gated diagnostic endpoint must
return a plain 404 with body ``{"detail": "Not found."}`` for both
unauthenticated and non-staff requests. This is identical to the body
DRF returns for any other 404, so the endpoint's existence is not
disclosed by the response shape or status code.

Why a custom exception handler instead of a permission class raising
``Http404`` from ``has_permission()``? DRF issue #7529 documents that
``BrowsableAPIRenderer`` re-checks permissions with a narrower exception
catch that bypasses the API renderer when ``Http404`` is raised —
producing a Django default HTML 404 page instead of the JSON body the
client expects. The exception-handler approach avoids that footgun by
running AFTER permission resolution and only for the
:class:`HealthDetailView` class.
"""

from __future__ import annotations

from typing import Any

from rest_framework import status
from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_default_exception_handler

_OBSCURED_BODY = {"detail": "Not found."}


def health_obscuring_exception_handler(
    exc: Exception,
    context: dict[str, Any],
) -> Response | None:
    """Map auth failures on :class:`HealthDetailView` to a standard DRF 404.

    Delegates to DRF's default handler for everything else, preserving
    standard 401/403/400/500 behavior on every other endpoint.

    Args:
        exc: The raised exception.
        context: DRF-provided context, including ``context["view"]``
            (the view instance) and ``context["request"]``.

    Returns:
        A ``Response`` with status 404 + ``{"detail": "Not found."}``
        when ``exc`` is a ``NotAuthenticated``/``PermissionDenied``
        raised by a ``HealthDetailView`` instance; otherwise the
        result of the DRF default handler.
    """
    # Local import to avoid a circular dependency between
    # health.views (imports nothing from this module) and
    # health.exceptions (this module references HealthDetailView).
    from babylon_web.health.views import HealthDetailView

    if isinstance(exc, NotAuthenticated | PermissionDenied):
        view = context.get("view")
        if isinstance(view, HealthDetailView):
            return Response(
                _OBSCURED_BODY,
                status=status.HTTP_404_NOT_FOUND,
            )
    return drf_default_exception_handler(exc, context)
