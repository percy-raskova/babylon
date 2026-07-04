"""Root URL configuration for Babylon web application."""

from __future__ import annotations

from django.contrib import admin
from django.http import HttpRequest, HttpResponseBase, JsonResponse
from django.shortcuts import redirect
from django.urls import include, path

from babylon_web.health.views import HealthDetailView


def health_check(request: HttpRequest) -> JsonResponse:
    """Health check endpoint. Returns 200 with status ok."""
    return JsonResponse({"status": "ok"})


def root_redirect(request: HttpRequest) -> HttpResponseBase:
    """Redirect root to the game list page."""
    return redirect("game-list-page")


urlpatterns = [
    path("", root_redirect, name="root"),
    path("health/", health_check, name="health"),
    # spec 061 US2 FR-009: auth-gated diagnostic endpoint. Returns 404
    # to unauthenticated/non-staff callers (security through obscurity).
    path("health/detail/", HealthDetailView.as_view(), name="health-detail"),
    path("admin/", admin.site.urls),
    path("api/", include("game.urls")),
    # spec-096: read-only Observatory endpoints (flag-gated in views).
    path("api/observatory/", include("observatory.urls")),
    path("accounts/", include("accounts.urls")),
    # Server-rendered pages (login required)
    path("games/", include("game.page_urls")),
]
