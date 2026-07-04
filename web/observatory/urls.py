"""Observatory URL configuration — read-only endpoints under ``/api/observatory/``."""

from __future__ import annotations

from django.urls import URLPattern, path

from . import deep_views, views

app_name = "observatory"

urlpatterns: list[URLPattern] = [
    path("status/", views.observatory_status, name="status"),
    path("sessions/", views.observatory_sessions, name="sessions"),
    path("sessions/<str:session_id>/ticks/", views.observatory_ticks, name="ticks"),
    path("sessions/<str:session_id>/series/", views.observatory_series, name="series"),
    path(
        "sessions/<str:session_id>/series.csv/",
        views.observatory_series_csv,
        name="series-csv",
    ),
    path("sessions/<str:session_id>/commits/", views.observatory_commits, name="commits"),
    path("sessions/<str:session_id>/hex/", views.observatory_hex, name="hex"),
    # spec-099 deep panes
    path("sessions/<str:session_id>/verify/", deep_views.observatory_verify, name="verify"),
    path("sessions/<str:session_id>/boundary/", deep_views.observatory_boundary, name="boundary"),
    path(
        "sessions/<str:session_id>/conservation/",
        deep_views.observatory_conservation,
        name="conservation",
    ),
    path("diff/", deep_views.observatory_diff, name="diff"),
]
