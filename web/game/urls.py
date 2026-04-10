"""Game API URL configuration.

Routes all game-related API endpoints under ``/api/``.
Per-verb action endpoints (Spec 040) are nested under
``/api/games/<game_id>/actions/<verb>/``.
Per-layer map endpoints serve filtered GeoJSON at
``/api/games/<game_id>/map/<layer>/``.
"""

from __future__ import annotations

from django.urls import URLPattern, path

from . import api

app_name = "game"

urlpatterns: list[URLPattern] = [
    # ------------------------------------------------------------------ #
    # API: Scenario catalog
    # ------------------------------------------------------------------ #
    path("scenarios/", api.scenario_list, name="scenario-list"),
    # API: Game lifecycle
    path("games/", api.game_list, name="game-list"),
    path("games/<str:game_id>/", api.game_detail, name="game-detail"),
    path("games/<str:game_id>/pause/", api.game_pause, name="game-pause"),
    path("games/<str:game_id>/resume/", api.game_resume, name="game-resume"),
    # API: State
    path("games/<str:game_id>/state/", api.game_state, name="game-state"),
    path("games/<str:game_id>/map/", api.game_map, name="game-map"),
    # API: Per-layer map endpoints
    path(
        "games/<str:game_id>/map/<str:layer>/",
        api.game_map_layer,
        name="game-map-layer",
    ),
    # API: Actions — utility endpoints (available, preview, pending list)
    path(
        "games/<str:game_id>/actions/available/",
        api.actions_available,
        name="actions-available",
    ),
    path(
        "games/<str:game_id>/actions/preview/",
        api.actions_preview,
        name="actions-preview",
    ),
    # Per-verb action submission (Spec 040 §6.1)
    path(
        "games/<str:game_id>/actions/educate/",
        api.EducateActionView.as_view(),
        name="action-educate",
    ),
    path(
        "games/<str:game_id>/actions/aid/",
        api.AidActionView.as_view(),
        name="action-aid",
    ),
    path(
        "games/<str:game_id>/actions/attack/",
        api.AttackActionView.as_view(),
        name="action-attack",
    ),
    path(
        "games/<str:game_id>/actions/mobilize/",
        api.MobilizeActionView.as_view(),
        name="action-mobilize",
    ),
    path(
        "games/<str:game_id>/actions/campaign/",
        api.CampaignActionView.as_view(),
        name="action-campaign",
    ),
    path(
        "games/<str:game_id>/actions/move/",
        api.MoveActionView.as_view(),
        name="action-move",
    ),
    path(
        "games/<str:game_id>/actions/investigate/",
        api.InvestigateActionView.as_view(),
        name="action-investigate",
    ),
    path(
        "games/<str:game_id>/actions/reproduce/",
        api.ReproduceActionView.as_view(),
        name="action-reproduce",
    ),
    path(
        "games/<str:game_id>/actions/negotiate/",
        api.NegotiateActionView.as_view(),
        name="action-negotiate",
    ),
    # Legacy generic action endpoint (backward compat)
    path("games/<str:game_id>/actions/", api.actions_list, name="actions-list"),
    path("games/<str:game_id>/resolve/", api.resolve_tick, name="resolve-tick"),
    # Results
    path(
        "games/<str:game_id>/results/<int:tick>/",
        api.tick_results,
        name="tick-results",
    ),
]
