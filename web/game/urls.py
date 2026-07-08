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
    path("games/<str:game_id>/recover/", api.game_recover, name="game-recover"),
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
    path("games/<str:game_id>/wire/", api.game_wire, name="game-wire"),
    # API: Spec 095 — Endgame Chronicle + Journal + Dialectic screen
    path(
        "games/<str:game_id>/contradiction/",
        api.game_contradiction,
        name="game-contradiction",
    ),
    path("games/<str:game_id>/endgame/", api.game_endgame, name="game-endgame"),
    path(
        "games/<str:game_id>/objectives/",
        api.game_objectives,
        name="game-objectives",
    ),
    # API: Spec 103 — Trade surfaces
    path(
        "games/<str:game_id>/trade-flows/",
        api.game_trade_flows,
        name="game-trade-flows",
    ),
    path(
        "games/<str:game_id>/exposure/",
        api.game_county_exposure,
        name="game-county-exposure",
    ),
    path(
        "games/<str:game_id>/trade-panel/",
        api.game_trade_panel,
        name="game-trade-panel",
    ),
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
        "games/<str:game_id>/actions/educate/targets/",
        api.EducateVerbView.as_view(),
        name="verb-educate-targets",
    ),
    path(
        "games/<str:game_id>/actions/educate/",
        api.EducateVerbView.as_view(),
        name="verb-educate-submit",
    ),
    path(
        "games/<str:game_id>/actions/aid/targets/",
        api.AidVerbView.as_view(),
        name="verb-aid-targets",
    ),
    path("games/<str:game_id>/actions/aid/", api.AidVerbView.as_view(), name="verb-aid-submit"),
    path(
        "games/<str:game_id>/actions/attack/targets/",
        api.AttackVerbView.as_view(),
        name="verb-attack-targets",
    ),
    path(
        "games/<str:game_id>/actions/attack/",
        api.AttackVerbView.as_view(),
        name="verb-attack-submit",
    ),
    path(
        "games/<str:game_id>/actions/mobilize/targets/",
        api.MobilizeVerbView.as_view(),
        name="verb-mobilize-targets",
    ),
    path(
        "games/<str:game_id>/actions/mobilize/",
        api.MobilizeVerbView.as_view(),
        name="verb-mobilize-submit",
    ),
    path(
        "games/<str:game_id>/actions/campaign/targets/",
        api.CampaignActionView.as_view(),
        name="verb-campaign-targets",
    ),
    path(
        "games/<str:game_id>/actions/campaign/",
        api.CampaignActionView.as_view(),
        name="verb-campaign-submit",
    ),
    path(
        "games/<str:game_id>/actions/move/targets/",
        api.MoveVerbView.as_view(),
        name="verb-move-targets",
    ),
    path("games/<str:game_id>/actions/move/", api.MoveVerbView.as_view(), name="verb-move-submit"),
    path(
        "games/<str:game_id>/actions/investigate/targets/",
        api.InvestigateVerbView.as_view(),
        name="verb-investigate-targets",
    ),
    path(
        "games/<str:game_id>/actions/investigate/",
        api.InvestigateVerbView.as_view(),
        name="verb-investigate-submit",
    ),
    path(
        "games/<str:game_id>/actions/reproduce/targets/",
        api.ReproduceVerbView.as_view(),
        name="verb-reproduce-targets",
    ),
    path(
        "games/<str:game_id>/actions/reproduce/",
        api.ReproduceVerbView.as_view(),
        name="verb-reproduce-submit",
    ),
    path(
        "games/<str:game_id>/actions/negotiate/targets/",
        api.NegotiateVerbView.as_view(),
        name="verb-negotiate-targets",
    ),
    path(
        "games/<str:game_id>/actions/negotiate/",
        api.NegotiateVerbView.as_view(),
        name="verb-negotiate-submit",
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
