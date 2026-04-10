"""Root URL configuration for Babylon web application."""

from __future__ import annotations

from django.contrib import admin
from django.http import HttpRequest, HttpResponseBase, JsonResponse
from django.shortcuts import redirect
from django.urls import include, path


def health_check(request: HttpRequest) -> JsonResponse:
    """Health check endpoint. Returns 200 with status ok."""
    return JsonResponse({"status": "ok"})


def root_redirect(request: HttpRequest) -> HttpResponseBase:
    """Redirect root to the game list page."""
    return redirect("game-list-page")


urlpatterns = [
    path("", root_redirect, name="root"),
    path("health/", health_check, name="health"),
    path("admin/", admin.site.urls),
    path("api/", include("game.urls")),
    path("accounts/", include("accounts.urls")),
    # Server-rendered pages (login required)
    path("games/", include("game.page_urls")),
]
