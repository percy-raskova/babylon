"""Game API URL configuration.

Routes all game-related API endpoints under ``/api/``.
"""

from __future__ import annotations

from django.urls import URLPattern, path

from . import api

app_name = "game"

urlpatterns: list[URLPattern] = [
    # Scenario catalog
    path("scenarios/", api.scenario_list, name="scenario-list"),
    # Game lifecycle
    path("games/", api.game_list, name="game-list"),
    path("games/<str:game_id>/", api.game_detail, name="game-detail"),
    path("games/<str:game_id>/pause/", api.game_pause, name="game-pause"),
    path("games/<str:game_id>/resume/", api.game_resume, name="game-resume"),
    # State
    path("games/<str:game_id>/state/", api.game_state, name="game-state"),
    # Actions
    path(
        "games/<str:game_id>/actions/available/",
        api.actions_available,
        name="actions-available",
    ),
    path("games/<str:game_id>/actions/", api.actions_list, name="actions-list"),
    path("games/<str:game_id>/resolve/", api.resolve_tick, name="resolve-tick"),
    # Results
    path(
        "games/<str:game_id>/results/<int:tick>/",
        api.tick_results,
        name="tick-results",
    ),
]
