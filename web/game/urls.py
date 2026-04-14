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
    path("games/<str:game_id>/summary/", api.game_summary, name="game-summary"),
    path("games/<str:game_id>/timeseries/", api.game_timeseries, name="game-timeseries"),
    path("games/<str:game_id>/map/", api.game_map, name="game-map"),
    # API: Domain Dashboards
    path("games/<str:game_id>/economy/", api.game_economy, name="game-economy"),
    path("games/<str:game_id>/communities/", api.game_communities, name="game-communities"),
    path("games/<str:game_id>/organizations/", api.game_organizations, name="game-organizations"),
    path("games/<str:game_id>/edges/", api.game_edges, name="game-edges"),
    path(
        "games/<str:game_id>/state-apparatus/",
        api.game_state_apparatus,
        name="game-state-apparatus",
    ),
    path("games/<str:game_id>/journal/", api.game_journal, name="game-journal"),
    path("games/<str:game_id>/alerts/", api.game_alerts, name="game-alerts"),
    # API: Spatial Multi-Scale
    path("games/<str:game_id>/orgs/network/", api.org_network, name="org-network"),
    path(
        "games/<str:game_id>/hypergraph/communities/",
        api.hypergraph_communities,
        name="hypergraph-communities",
    ),
    path(
        "games/<str:game_id>/infrastructure/",
        api.game_infrastructure,
        name="game-infrastructure",
    ),
    # API: Inspector Drill-Downs
    path("games/<str:game_id>/node/<str:node_id>/", api.inspector_node, name="inspector-node"),
    path("games/<str:game_id>/org/<str:org_id>/", api.inspector_org, name="inspector-org"),
    path(
        "games/<str:game_id>/community/<str:hyperedge_id>/",
        api.inspector_community,
        name="inspector-community",
    ),
    path("games/<str:game_id>/edge/<str:edge_id>/", api.inspector_edge, name="inspector-edge"),
    path("games/<str:game_id>/hex/<str:h3_index>/", api.inspector_hex, name="inspector-hex"),
    # API: Actions — utility endpoints (available, preview, pending list, cancel)
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
    path(
        "games/<str:game_id>/actions/<int:action_id>/",
        api.action_delete,
        name="action-delete",
    ),
    # Per-verb action submission (Spec 040 §6.1 / Spec 043)
    path(
        "games/<str:game_id>/verbs/educate/",
        api.EducateVerbView.as_view(),
        name="verb-educate",
    ),
    path(
        "games/<str:game_id>/verbs/aid/",
        api.AidVerbView.as_view(),
        name="verb-aid",
    ),
    path(
        "games/<str:game_id>/verbs/attack/",
        api.AttackVerbView.as_view(),
        name="verb-attack",
    ),
    path(
        "games/<str:game_id>/verbs/mobilize/",
        api.MobilizeVerbView.as_view(),
        name="verb-mobilize",
    ),
    path(
        "games/<str:game_id>/actions/campaign/",
        api.CampaignActionView.as_view(),
        name="action-campaign",
    ),
    path(
        "games/<str:game_id>/verbs/move/",
        api.MoveVerbView.as_view(),
        name="verb-move",
    ),
    path(
        "games/<str:game_id>/verbs/investigate/",
        api.InvestigateVerbView.as_view(),
        name="verb-investigate",
    ),
    path(
        "games/<str:game_id>/verbs/reproduce/",
        api.ReproduceVerbView.as_view(),
        name="verb-reproduce",
    ),
    path(
        "games/<str:game_id>/verbs/negotiate/",
        api.NegotiateVerbView.as_view(),
        name="verb-negotiate",
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
    # ------------------------------------------------------------------ #
    # V2 Dialectic Engine endpoints
    # ------------------------------------------------------------------ #
    path(
        "games/<str:game_id>/v2/world/",
        api.dialectic_world_state,
        name="v2-world-state",
    ),
    path(
        "games/<str:game_id>/v2/dialectics/<str:dialectic_id>/",
        api.dialectic_detail,
        name="v2-dialectic-detail",
    ),
]
