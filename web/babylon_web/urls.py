"""Root URL configuration for Babylon web application."""

from __future__ import annotations

from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def health_check(request: object) -> JsonResponse:
    """Health check endpoint. Returns 200 with status ok."""
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("health/", health_check, name="health"),
    path("admin/", admin.site.urls),
    path("api/", include("game.urls")),
    path("accounts/", include("accounts.urls")),
]
