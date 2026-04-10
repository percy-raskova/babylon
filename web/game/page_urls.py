"""Server-rendered page URL configuration.

Routes for Django-template pages (not JSON API endpoints).
Separate from ``urls.py`` to keep API routing clean.
"""

from __future__ import annotations

from django.urls import URLPattern, path

from . import api

urlpatterns: list[URLPattern] = [
    path("", api.game_list_page, name="game-list-page"),
]
