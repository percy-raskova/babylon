"""Accounts URL configuration.

Routes for session-based authentication: login, logout, whoami.
"""

from __future__ import annotations

from django.urls import URLPattern, path

from . import views

app_name = "accounts"

urlpatterns: list[URLPattern] = [
    path("login/", views.login_page, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("whoami/", views.whoami, name="whoami"),
]
