"""DRF API views for game lifecycle, state, and actions.

All views return the standard response envelope:
``{"status": "ok", "data": {...}, "tick": N, "session_id": "uuid"}``

The EngineBridge is lazily instantiated via ``_get_bridge()`` and cached
per-process. In tests, patch ``game.api._bridge_instance``.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any
from uuid import UUID

from django.conf import settings as django_settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpRequest, HttpResponseBase, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from game.models import ActionResult, GameSession, PlayerAction

from .log_handler import log_game_event, sanitize_for_log
from .map_contract import MAP_METRIC_PROPERTIES
from .serializers import (
    ActionResultSerializer,
    AidAvailableSerializer,
    AidSubmitSerializer,
    AttackAvailableSerializer,
    AttackSubmitSerializer,
    BaseActionSerializer,
    CampaignActionSerializer,
    CreateGameSerializer,
    EducateAvailableSerializer,
    EducateSubmitSerializer,
    GameSessionListSerializer,
    GameSnapshotSerializer,
    InvestigateAvailableSerializer,
    InvestigateSubmitSerializer,
    MobilizeAvailableSerializer,
    MobilizeSubmitSerializer,
    MoveAvailableSerializer,
    MoveSubmitSerializer,
    NegotiateAvailableSerializer,
    NegotiateSubmitSerializer,
    ReproduceAvailableSerializer,
    ReproduceSubmitSerializer,
    SubmitActionSerializer,
)
from .tick_resolver import resolve_game_tick

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------- #
# Bridge singleton (lazily initialized)
# ---------------------------------------------------------------------- #

_bridge_instance: Any | None = None


def _get_bridge() -> Any:
    """Return the cached EngineBridge instance, creating on first use.

    Spec 061 US7 (T112): the MockEngineBridge path has been removed.
    Production must initialize the bridge via ``GameConfig.ready()``
    (see ``game.apps``). In SQLite-only dev configurations the legacy
    ``StubEngineBridge`` remains as a non-persisting fallback so the
    Django app boots without Postgres.

    Returns a mock-friendly ``Any`` so tests can replace ``_bridge_instance``.
    """
    global _bridge_instance  # noqa: PLW0603
    if _bridge_instance is None:
        from .stub_bridge import StubEngineBridge

        # Seam Sensor 3 (provenance): the StubEngineBridge serves fabricated
        # values through the real API contract. That is fine in DEBUG (dev/stub
        # settings, DEBUG=True), but serving it with DEBUG off would render fake
        # data as if real — the "rendered but fake" honesty violation this sensor
        # exists to forbid. Fail loud (III.11) instead of silently faking.
        if not django_settings.DEBUG:
            raise ImproperlyConfigured(
                "EngineBridge not initialized and DEBUG is off — refusing to serve the "
                "StubEngineBridge's fabricated data through the production API "
                "(Seam Sensor 3 provenance / Constitution III.11). Initialize a real "
                "bridge via init_bridge() / GameConfig.ready() with a persistence layer."
            )
        logger.warning(
            "EngineBridge not initialized — falling back to StubEngineBridge. "
            "Set up PostgreSQL or call init_bridge() for production use."
        )
        _bridge_instance = StubEngineBridge()
    return _bridge_instance


def init_bridge(persistence: Any) -> None:
    """Initialize the bridge singleton with a persistence layer.

    Call this from Django's AppConfig.ready() or a management command.

    Args:
        persistence: A RuntimePersistence-compatible object.
    """
    global _bridge_instance  # noqa: PLW0603
    from .engine_bridge import EngineBridge

    _bridge_instance = EngineBridge(persistence)


# ---------------------------------------------------------------------- #
# Response envelope helper
# ---------------------------------------------------------------------- #


def _envelope(
    data: Any,
    tick: int | None = None,
    session_id: str | None = None,
    http_status: int = 200,
) -> JsonResponse:
    """Wrap data in the standard API response envelope."""
    body: dict[str, Any] = {"status": "ok", "data": data}
    if tick is not None:
        body["tick"] = tick
    if session_id is not None:
        body["session_id"] = session_id
    return JsonResponse(body, status=http_status)


def _error(message: str, http_status: int = 400) -> JsonResponse:
    """Return an error response envelope."""
    return JsonResponse(
        {"status": "error", "message": message},
        status=http_status,
    )


def _error_with_code(
    message: str,
    code: str,
    http_status: int = 400,
) -> JsonResponse:
    """Return an error response with a machine-readable error code (Spec 040 §5.1)."""
    return JsonResponse(
        {"status": "error", "error": message, "code": code},
        status=http_status,
    )


def _action_rejected(exc: ValueError, *, session_id: object) -> Response:
    """Log a rejected-action exception server-side and return a generic client error.

    The bridge raises :class:`ValueError` carrying internal validation detail; per the
    CodeQL ``py/stack-trace-exposure`` hardening that detail is logged, never surfaced to
    the client, which receives a stable, non-revealing message.

    :param exc: The ``ValueError`` raised while submitting the action.
    :param session_id: The game session id, for the server-side log line only.
    :returns: A 400 DRF ``Response`` with the standard error envelope.
    """
    logger.info("Action rejected session=%s: %s", session_id, exc)
    return Response(
        {
            "status": "error",
            "message": "Action rejected: the request was not valid for the current game state.",
        },
        status=status.HTTP_400_BAD_REQUEST,
    )


# ---------------------------------------------------------------------- #
# Server-rendered pages (Django templates + @login_required)
# ---------------------------------------------------------------------- #


@login_required
def game_list_page(request: HttpRequest) -> HttpResponseBase:
    """Server-rendered game list page.

    Shows all games for the logged-in user with status, scenario,
    and current tick. Links to the SPA for each active game.
    """
    sessions = GameSession.objects.filter(player_id=request.user.id).order_by("-created_at")[:50]
    scenarios_by_key = {s["key"]: s for s in SCENARIO_CATALOG}
    games = [
        {
            "id": str(s.id),
            "scenario": s.scenario,
            "scenario_name": scenarios_by_key.get(s.scenario, {}).get("name", s.scenario),
            "current_tick": s.current_tick,
            "status": s.status,
            "created_at": s.created_at,
        }
        for s in sessions
    ]
    return render(
        request,
        "game/game_list.html",
        {
            "games": games,
            "scenarios": SCENARIO_CATALOG,
            "username": request.user.username,
        },
    )


# ---------------------------------------------------------------------- #
# Game lifecycle endpoints
# ---------------------------------------------------------------------- #


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def game_list(request: Request) -> JsonResponse:
    """GET: List player's games. POST: Create a new game."""
    if request.method == "GET":
        sessions = GameSession.objects.filter(player_id=request.user.id).order_by("-created_at")[
            :50
        ]
        session_data: list[dict[str, Any]] = [
            {
                "id": s.id,
                "scenario": s.scenario,
                "current_tick": s.current_tick,
                "status": s.status,
                "created_at": s.created_at,
            }
            for s in sessions
        ]
        list_serializer = GameSessionListSerializer(session_data, many=True)  # type: ignore[arg-type]
        return _envelope(list_serializer.data)

    # POST: Create a new game
    create_serializer = CreateGameSerializer(data=request.data)
    if not create_serializer.is_valid():
        logger.warning(
            "Invalid create game request from user=%s: %s",
            request.user.id,
            create_serializer.errors,
        )
        return _error(str(create_serializer.errors))

    bridge = _get_bridge()
    session_id = bridge.create_game(
        scenario=create_serializer.validated_data["scenario"],
        config=create_serializer.validated_data.get("config"),
        defines=create_serializer.validated_data.get("defines"),
        rng_seed=create_serializer.validated_data.get("rng_seed", 0),
        player_id=request.user.id,
    )
    logger.info(
        "Game created session=%s scenario=%s user=%s",
        session_id,
        create_serializer.validated_data["scenario"],
        request.user.id,
    )
    log_game_event(
        category="game_create",
        message=f"Game created: scenario={create_serializer.validated_data['scenario']}",
        session_id=session_id,
        user_id=request.user.id,
        correlation_id=getattr(request, "correlation_id", None),
    )
    return _envelope(
        {"session_id": str(session_id)},
        session_id=str(session_id),
        http_status=status.HTTP_201_CREATED,
    )


# ---------------------------------------------------------------------- #
# Scenario catalog
# ---------------------------------------------------------------------- #

SCENARIO_CATALOG: list[dict[str, Any]] = [
    {
        "key": "wayne_county",
        "name": "Wayne County Organizer",
        "description": (
            "Organize in Wayne County, Michigan. 81 H3 hexes covering Detroit, "
            "Dearborn, Downriver, and the suburbs. 4 social classes, 1 player org. "
            "52-tick (1-year) game arc."
        ),
        "territory_count": 81,
    },
    {
        "key": "us_nationwide",
        "name": "United States — Nationwide",
        "description": "Full CONUS simulation with ~1,100 H3 territories",
        "territory_count": 1100,
    },
    {
        "key": "imperial_circuit",
        "name": "Imperial Circuit",
        "description": "6-class imperial circuit with core/periphery dynamics",
        "territory_count": 2,
    },
    {
        "key": "two_node",
        "name": "Two-Node Dialectic",
        "description": "Minimal scenario: one worker, one owner, one territory",
        "territory_count": 1,
    },
]

# Spec-109 A3: derived from the one map-metric contract — every accepted
# lens is actually emitted on /map/ features (see map_contract.py). The old
# hand-maintained set advertised consciousness/wealth/rent/biocapacity,
# none of which any feature carried: a silently blank overlay (III.11).
VALID_MAP_LAYERS: frozenset[str] = frozenset(MAP_METRIC_PROPERTIES)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def scenario_list(request: Request) -> JsonResponse:
    """GET /api/scenarios/ — List available game scenarios."""
    return _envelope(SCENARIO_CATALOG)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def game_detail(request: Request, game_id: str) -> JsonResponse:
    """GET /api/games/{id}/ — Get game session metadata."""
    session = _get_session_or_none(game_id, request.user.id)
    if session is None:
        return _error("Game not found", http_status=404)

    data = {
        "id": str(session.id),
        "scenario": session.scenario,
        "current_tick": session.current_tick,
        "status": session.status,
        "created_at": session.created_at.isoformat() if session.created_at else None,
    }
    return _envelope(data, tick=session.current_tick, session_id=str(session.id))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def game_pause(request: Request, game_id: str) -> JsonResponse:
    """POST /api/games/{id}/pause/ — Pause a running game."""
    session = _get_session_or_none(game_id, request.user.id)
    if session is None:
        return _error("Game not found", http_status=404)
    if session.status != "active":
        return _error(f"Cannot pause game in '{session.status}' status")
    GameSession.objects.filter(id=session.id).update(status="paused", updated_at=timezone.now())
    return _envelope({"status": "paused"}, session_id=str(session.id))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def game_resume(request: Request, game_id: str) -> JsonResponse:
    """POST /api/games/{id}/resume/ — Resume a paused game."""
    session = _get_session_or_none(game_id, request.user.id)
    if session is None:
        return _error("Game not found", http_status=404)
    if session.status != "paused":
        return _error(f"Cannot resume game in '{session.status}' status")
    GameSession.objects.filter(id=session.id).update(status="active", updated_at=timezone.now())
    return _envelope({"status": "active"}, session_id=str(session.id))


# C.13: a worker killed mid-resolve leaves status='resolving' with no
# surviving process to restore it. Sessions resolving longer than this
# are considered wedged and eligible for recovery.
RESOLVING_STALE_SECONDS: int = getattr(django_settings, "GAME_RESOLVING_STALE_SECONDS", 120)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def game_recover(request: Request, game_id: str) -> JsonResponse:
    """POST /api/games/{id}/recover/ — Recover a session wedged in 'resolving'.

    A worker killed mid-resolve (OOM, SIGKILL, deploy restart) commits
    status='resolving' and never restores it (C.13). Once the staleness
    threshold passes, the owner can reset the session to 'active' and retry.
    """
    session = _get_session_or_none(game_id, request.user.id)
    if session is None:
        return _error("Game not found", http_status=404)
    if session.status != "resolving":
        return _error(f"Cannot recover game in '{session.status}' status")
    age_seconds = (timezone.now() - session.updated_at).total_seconds()
    if age_seconds < RESOLVING_STALE_SECONDS:
        return _error(
            "Tick resolution appears to be in progress; retry later",
            http_status=409,
        )
    # Conditional filter makes this race-safe: a resolve that completed
    # concurrently already set 'active', so this update matches 0 rows.
    GameSession.objects.filter(id=session.id, status="resolving").update(
        status="active", updated_at=timezone.now()
    )
    logger.warning("Recovered wedged session=%s (resolving for %.0fs)", session.id, age_seconds)
    log_game_event(
        category="game_recover",
        message=f"Recovered from wedged 'resolving' after {age_seconds:.0f}s",
        session_id=session.id,
        user_id=request.user.id,
        tick=session.current_tick,
        correlation_id=getattr(request, "correlation_id", None),
    )
    return _envelope({"status": "active"}, session_id=str(session.id))


# ---------------------------------------------------------------------- #
# State endpoints
# ---------------------------------------------------------------------- #


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def game_state(request: Request, game_id: str) -> JsonResponse:
    """GET /api/games/{id}/state/ — Full game state snapshot."""
    session = _get_session_or_none(game_id, request.user.id)
    if session is None:
        return _error("Game not found", http_status=404)

    bridge = _get_bridge()
    snapshot = bridge.get_snapshot(uuid.UUID(str(session.id)))
    serializer = GameSnapshotSerializer(snapshot)
    return _envelope(
        serializer.data,
        tick=snapshot.get("tick"),
        session_id=str(session.id),
    )


# ---- Zoom levels for multi-resolution map --------------------------------
# Tier hierarchy: state → bea_ea → msa → county → cz → hex
VALID_ZOOM_LEVELS: frozenset[str] = frozenset(
    ["state", "bea", "bea_ea", "msa", "county", "cz", "hex"]
)
DEFAULT_ZOOM = "county"


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def game_map(request: Request, game_id: str) -> JsonResponse:
    """GET /api/games/{id}/map/ — Hex map state snapshot.

    Query parameters:
        tick (int, optional): Tick to query. Default: current tick.
        lens (str, optional): Metric to overlay.
        zoom (str, optional): Spatial aggregation level.
            One of: state, bea, msa, county, hex. Default: county.
    """
    session = _get_session_or_none(game_id, request.user.id)
    if session is None:
        return _error("Game not found", http_status=404)

    try:
        tick_query = request.query_params.get("tick")
        tick = int(tick_query) if tick_query is not None else None
    except ValueError:
        return _error("Invalid tick parameter", http_status=400)

    lens = request.query_params.get("lens")
    zoom = request.query_params.get("zoom", DEFAULT_ZOOM)
    if zoom not in VALID_ZOOM_LEVELS:
        return _error(
            f"Invalid zoom '{zoom}'. Valid levels: {sorted(VALID_ZOOM_LEVELS)}",
            http_status=400,
        )
    # Spec-109 A3 (III.11): reject unknown lenses loudly — the old behavior
    # silently returned unfiltered features for a typo'd lens.
    if lens and lens not in VALID_MAP_LAYERS:
        return _error(
            f"Invalid lens '{lens}'. Valid metrics: {sorted(VALID_MAP_LAYERS)}",
            http_status=400,
        )

    bridge = _get_bridge()
    snapshot = bridge.get_map_snapshot(
        uuid.UUID(str(session.id)),
        tick=tick,
        _layer=lens,
        zoom=zoom,
    )

    if lens:
        # Filter properties to only include the requested layer metric plus identifying fields
        keep_keys = {"h3_index", "county_fips", "county_name", lens}
        filtered_features = []
        for feature in snapshot.get("features", []):
            original_props = feature.get("properties", {})
            filtered_props = {k: v for k, v in original_props.items() if k in keep_keys}
            filtered_features.append(
                {
                    "type": feature.get("type", "Feature"),
                    "id": feature.get("id"),
                    "geometry": feature.get("geometry"),
                    "properties": filtered_props,
                }
            )

        snapshot = {
            "type": "FeatureCollection",
            "metadata": {
                **snapshot.get("metadata", {}),
                "layer": lens,
            },
            "features": filtered_features,
        }
    return _envelope(
        snapshot,
        tick=snapshot.get("metadata", {}).get("tick", session.current_tick),
        session_id=str(session.id),
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def game_map_history(request: Request, game_id: str) -> JsonResponse:
    """GET /api/games/{id}/map/history/ — per-tick map-metric replay frames.

    Program 17 Wave 3 (Backend-W3R3): the map lens scrubber's real data
    source. See ``EngineBridge.get_map_history``'s docstring for the
    verified replayable/non-replayable metric split — only
    ``MAP_HISTORY_REPLAYABLE_METRICS`` (``heat``/``population``/
    ``profit_rate``/``exploitation_rate``) has a genuine per-tick
    historical source; the other 9 ``MAP_METRIC_PROPERTIES`` 422 rather
    than serve a frame of fabricated nulls (Constitution III.11).

    Query parameters:
        metric (str, required): One of ``MAP_METRIC_PROPERTIES``. 400 if
            missing or unknown; 422 if known but not historically
            replayable.
        from_tick / to_tick (int, optional): Inclusive tick bounds.
            Default: a window ending at the latest committed tick, capped
            at ``EngineBridge``'s window cap (``capped: true`` in the
            response when the served range is narrower than requested).
    """
    session = _get_session_or_none(game_id, request.user.id)
    if session is None:
        return _error("Game not found", http_status=404)

    metric = request.query_params.get("metric")
    if not metric:
        return _error(
            f"metric query parameter is required. Valid metrics: {sorted(VALID_MAP_LAYERS)}",
            http_status=400,
        )
    if metric not in VALID_MAP_LAYERS:
        return _error(
            f"Invalid metric '{metric}'. Valid metrics: {sorted(VALID_MAP_LAYERS)}",
            http_status=400,
        )

    try:
        from_tick_query = request.query_params.get("from_tick")
        from_tick = int(from_tick_query) if from_tick_query is not None else None
        to_tick_query = request.query_params.get("to_tick")
        to_tick = int(to_tick_query) if to_tick_query is not None else None
    except ValueError:
        return _error("Invalid from_tick/to_tick parameter", http_status=400)

    if (from_tick is not None and from_tick < 0) or (to_tick is not None and to_tick < 0):
        return _error("from_tick/to_tick must be non-negative", http_status=400)
    if from_tick is not None and to_tick is not None and from_tick > to_tick:
        return _error("from_tick must be <= to_tick", http_status=400)

    bridge = _get_bridge()
    data = bridge.get_map_history(
        uuid.UUID(str(session.id)), metric=metric, from_tick=from_tick, to_tick=to_tick
    )

    error = data.get("error")
    if error == "unknown_metric":
        # Unreachable given the VALID_MAP_LAYERS gate above — defense in
        # depth, matches the bridge's own honest-error contract (III.11).
        return _error(data["message"], http_status=400)
    if error == "not_replayable":
        return _error(data["message"], http_status=422)

    return _envelope(data, tick=session.current_tick, session_id=str(session.id))


# ---------------------------------------------------------------------- #
# Dashboards and Analytics
# ---------------------------------------------------------------------- #


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def game_summary(request: Request, game_id: str) -> JsonResponse:
    """GET /api/games/{id}/summary/ - Top-bar aggregate."""
    session = _get_session_or_none(game_id, request.user.id)
    if session is None:
        return _error("Game not found", http_status=404)
    bridge = _get_bridge()
    data = bridge.get_game_summary(uuid.UUID(str(session.id)))
    return _envelope(data, tick=session.current_tick, session_id=str(session.id))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def game_timeseries(request: Request, game_id: str) -> JsonResponse:
    """GET /api/games/{id}/timeseries/ - Per-tick history for charts."""
    session = _get_session_or_none(game_id, request.user.id)
    if session is None:
        return _error("Game not found", http_status=404)
    bridge = _get_bridge()
    data = bridge.get_game_timeseries(uuid.UUID(str(session.id)))
    return _envelope(data, tick=session.current_tick, session_id=str(session.id))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def game_economy(request: Request, game_id: str) -> JsonResponse:
    """GET /api/games/{id}/economy/[?territory_id=] - Economy panel.

    Spec 093: with ``?territory_id=``, returns Territory Detail's real
    per-territory economic summary (:meth:`EngineBridge.get_economy`).
    Without it, falls back to the dashboard-wide summary
    (:meth:`EngineBridge.get_economy_dashboard`, spec 109 A4).
    """
    session = _get_session_or_none(game_id, request.user.id)
    if session is None:
        return _error("Game not found", http_status=404)
    bridge = _get_bridge()
    territory_id = request.query_params.get("territory_id")
    data = bridge.get_economy(uuid.UUID(str(session.id)), territory_id=territory_id)
    return _envelope(data, tick=session.current_tick, session_id=str(session.id))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def game_communities(request: Request, game_id: str) -> JsonResponse:
    """GET /api/games/{id}/communities/ - Communities left-panel dashboard."""
    session = _get_session_or_none(game_id, request.user.id)
    if session is None:
        return _error("Game not found", http_status=404)
    bridge = _get_bridge()
    data = bridge.get_communities_dashboard(uuid.UUID(str(session.id)))
    return _envelope(data, tick=session.current_tick, session_id=str(session.id))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def game_organizations(request: Request, game_id: str) -> JsonResponse:
    """GET /api/games/{id}/organizations/ - Organizations left-panel dashboard."""
    session = _get_session_or_none(game_id, request.user.id)
    if session is None:
        return _error("Game not found", http_status=404)
    bridge = _get_bridge()
    player_only = request.query_params.get("player_only", "false").lower() == "true"
    data = bridge.get_organizations_dashboard(uuid.UUID(str(session.id)), player_only=player_only)
    return _envelope(data, tick=session.current_tick, session_id=str(session.id))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def game_edges(request: Request, game_id: str) -> JsonResponse:
    """GET /api/games/{id}/edges/ - Edges left-panel dashboard."""
    session = _get_session_or_none(game_id, request.user.id)
    if session is None:
        return _error("Game not found", http_status=404)
    bridge = _get_bridge()
    data = bridge.get_edges_dashboard(uuid.UUID(str(session.id)))
    return _envelope(data, tick=session.current_tick, session_id=str(session.id))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def game_state_apparatus(request: Request, game_id: str) -> JsonResponse:
    """GET /api/games/{id}/state-apparatus/ - State-apparatus left-panel dashboard."""
    session = _get_session_or_none(game_id, request.user.id)
    if session is None:
        return _error("Game not found", http_status=404)
    bridge = _get_bridge()
    data = bridge.get_state_apparatus_dashboard(uuid.UUID(str(session.id)))
    return _envelope(data, tick=session.current_tick, session_id=str(session.id))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def game_journal(request: Request, game_id: str) -> JsonResponse:
    """GET /api/games/{id}/journal/ - Journal left-panel dashboard."""
    session = _get_session_or_none(game_id, request.user.id)
    if session is None:
        return _error("Game not found", http_status=404)
    bridge = _get_bridge()
    data = bridge.get_journal_dashboard(uuid.UUID(str(session.id)))
    return _envelope(data, tick=session.current_tick, session_id=str(session.id))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def game_alerts(request: Request, game_id: str) -> JsonResponse:
    """GET /api/games/{id}/alerts/ - Alerts left-panel dashboard."""
    session = _get_session_or_none(game_id, request.user.id)
    if session is None:
        return _error("Game not found", http_status=404)
    bridge = _get_bridge()
    data = bridge.get_alerts_dashboard(uuid.UUID(str(session.id)))
    return _envelope(data, tick=session.current_tick, session_id=str(session.id))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def game_wire(request: Request, game_id: str) -> JsonResponse:
    """GET /api/games/{id}/wire/ - The Wire feed (spec 094).

    Returns a WireFeed dict produced by the DeterministicNarrator over the
    session's journal events. Constitution III: narrator is a pure function
    with no engine state writes.
    """
    session = _get_session_or_none(game_id, request.user.id)
    if session is None:
        return _error("Game not found", http_status=404)
    bridge = _get_bridge()
    data = bridge.get_wire_feed(uuid.UUID(str(session.id)))
    return _envelope(data, tick=session.current_tick, session_id=str(session.id))


# ---------------------------------------------------------------------- #
# Spec 095: Endgame Chronicle + Journal + Dialectic screen
# ---------------------------------------------------------------------- #


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def game_contradiction(request: Request, game_id: str) -> JsonResponse:
    """GET /api/games/{id}/contradiction/ — live contradiction snapshot.

    Spec 095 FR-095-04. The Dialectic screen's feed. Reads
    ``contradiction_field`` rows and graph attributes (contradiction_frames,
    dialectical_regime). Constitution III: pure read — surfaces dialectical
    state the engine already computed, never computes it.
    """
    session = _get_session_or_none(game_id, request.user.id)
    if session is None:
        return _error("Game not found", http_status=404)
    bridge = _get_bridge()
    data = bridge.get_contradiction_snapshot(uuid.UUID(str(session.id)))
    return _envelope(data, tick=session.current_tick, session_id=str(session.id))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def game_endgame(request: Request, game_id: str) -> JsonResponse:
    """GET /api/games/{id}/endgame/ — terminal outcome + chronicle stat cards.

    Spec 095 FR-095-05. Reads the latest snapshot's endgame block. All 5
    GameOutcome terminal types are recognized (FR-095-02). Returns
    ``outcome: null`` when the game is still in progress.
    """
    session = _get_session_or_none(game_id, request.user.id)
    if session is None:
        return _error("Game not found", http_status=404)
    bridge = _get_bridge()
    data = bridge.get_endgame_state(uuid.UUID(str(session.id)))
    return _envelope(data, tick=session.current_tick, session_id=str(session.id))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def game_objectives(request: Request, game_id: str) -> JsonResponse:
    """GET /api/games/{id}/objectives/ — Vic3-style objectives tracker.

    Spec 095 FR-095-06. Derives objective progress from the current game
    state, mapping the 5 endgame conditions to trackable objectives.
    """
    session = _get_session_or_none(game_id, request.user.id)
    if session is None:
        return _error("Game not found", http_status=404)
    bridge = _get_bridge()
    data = bridge.get_journal_objectives(uuid.UUID(str(session.id)))
    return _envelope(data, tick=session.current_tick, session_id=str(session.id))


# ---------------------------------------------------------------------- #
# Spec 103: Trade surfaces — Wire INDEX per-bloc lines, Territory Detail
# import-exposure breakdown, Analysis trade panel.
# ---------------------------------------------------------------------- #


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def game_field_state(request: Request, game_id: str) -> JsonResponse:
    """GET /api/games/{id}/field_state/ — the System-19/20 contradiction-field stack.

    Program 19/20 (Wave 3 Round 1). Reads ``contradiction_fields``/
    ``field_derivatives`` (ContradictionFieldSystem @19 / FieldDerivativeSystem
    @20), ``fascist_alignment``, and the graph-level ``principal_field``/
    ``dialectical_regime`` attrs. Distinct from ``/contradiction/`` (Spec 095's
    System-18 opposition gap/rate snapshot) — a different concept, never
    reused under this name. Constitution III: pure read — surfaces field
    state the engine already computed, never computes it.
    """
    session = _get_session_or_none(game_id, request.user.id)
    if session is None:
        return _error("Game not found", http_status=404)
    bridge = _get_bridge()
    data = bridge.get_field_state(uuid.UUID(str(session.id)))
    return _envelope(data, tick=session.current_tick, session_id=str(session.id))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def game_trade_flows(request: Request, game_id: str) -> JsonResponse:
    """GET /api/games/{id}/trade-flows/ — per-bloc price/flow lines.

    Spec 103 FR-103-04. The Wire INDEX tab's trade section. Reads
    ``boundary_flow_register`` + ``dynamic_external_node_state`` via the
    persistence pool. Constitution III: pure read.
    """
    session = _get_session_or_none(game_id, request.user.id)
    if session is None:
        return _error("Game not found", http_status=404)
    bridge = _get_bridge()
    data = bridge.get_trade_flows(uuid.UUID(str(session.id)))
    return _envelope(data, tick=session.current_tick, session_id=str(session.id))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def game_county_exposure(request: Request, game_id: str) -> JsonResponse:
    """GET /api/games/{id}/exposure/?county_fips= — import-exposure breakdown.

    Spec 103 FR-103-05. Territory Detail's import-exposure provenance panel.
    A BabylonScriptValue-style breakdown over spec-100 weights + live
    ``boundary_flow_register`` flows, with a drill-down chain ending at
    reference-data citations.
    """
    session = _get_session_or_none(game_id, request.user.id)
    if session is None:
        return _error("Game not found", http_status=404)
    county_fips = request.query_params.get("county_fips")
    if not county_fips:
        return _error("county_fips query parameter is required", http_status=400)
    bridge = _get_bridge()
    data = bridge.get_county_import_exposure(uuid.UUID(str(session.id)), county_fips)
    return _envelope(data, tick=session.current_tick, session_id=str(session.id))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def game_trade_panel(request: Request, game_id: str) -> JsonResponse:
    """GET /api/games/{id}/trade-panel/ — aggregate trade panel.

    Spec 103 FR-103-06. The Analysis page's trade panel. Session-cumulative
    Φ inflow, per-bloc breakdown, and flow-type summary.
    """
    session = _get_session_or_none(game_id, request.user.id)
    if session is None:
        return _error("Game not found", http_status=404)
    bridge = _get_bridge()
    data = bridge.get_trade_panel(uuid.UUID(str(session.id)))
    return _envelope(data, tick=session.current_tick, session_id=str(session.id))


# ---------------------------------------------------------------------- #
# Spatial Multi-Scale Endpoints
# ---------------------------------------------------------------------- #


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def org_network(request: Request, game_id: str) -> JsonResponse:
    """GET /api/games/{id}/orgs/network/ — Org-network graph.

    Returns nodes (orgs, institutions, territories) and edges
    (PRESENCE, SOLIDARITY, EXPLOITATION, etc.) for the topology graph panel.

    Query parameters:
        territory (str, optional): Filter to orgs operating in this territory.
    """
    session = _get_session_or_none(game_id, request.user.id)
    if session is None:
        return _error("Game not found", http_status=404)
    bridge = _get_bridge()
    territory_filter = request.query_params.get("territory")
    data = bridge.get_org_network(
        uuid.UUID(str(session.id)),
        territory_filter=territory_filter,
    )
    return _envelope(data, tick=session.current_tick, session_id=str(session.id))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def hypergraph_communities(request: Request, game_id: str) -> JsonResponse:
    """GET /api/games/{id}/hypergraph/communities/ — Hyperedge data.

    Returns N-ary community memberships for compound-node graph rendering.

    Query parameters:
        territory (str, optional): Filter to communities with members in this territory.
    """
    session = _get_session_or_none(game_id, request.user.id)
    if session is None:
        return _error("Game not found", http_status=404)
    bridge = _get_bridge()
    territory_filter = request.query_params.get("territory")
    data = bridge.get_hypergraph_communities(
        uuid.UUID(str(session.id)),
        territory_filter=territory_filter,
    )
    return _envelope(data, tick=session.current_tick, session_id=str(session.id))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def game_infrastructure(request: Request, game_id: str) -> JsonResponse:
    """GET /api/games/{id}/infrastructure/ — Infrastructure network.

    Returns nodes (hubs) and edges (corridors) for map overlay rendering.
    Future phase — currently returns empty collections.
    """
    session = _get_session_or_none(game_id, request.user.id)
    if session is None:
        return _error("Game not found", http_status=404)
    bridge = _get_bridge()
    data = bridge.get_infrastructure(uuid.UUID(str(session.id)))
    return _envelope(data, tick=session.current_tick, session_id=str(session.id))


# ---------------------------------------------------------------------- #
# Inspector Endpoints (Drill-Downs)
# ---------------------------------------------------------------------- #


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def inspector_node(request: Request, game_id: str, node_id: str) -> JsonResponse:
    """GET /api/games/{id}/node/{node_id}/ - Node inspector."""
    session = _get_session_or_none(game_id, request.user.id)
    if session is None:
        return _error("Game not found", http_status=404)
    bridge = _get_bridge()
    data = bridge.get_inspector_node(uuid.UUID(str(session.id)), node_id)
    return _envelope(data, tick=session.current_tick, session_id=str(session.id))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def inspector_org(request: Request, game_id: str, org_id: str) -> JsonResponse:
    """GET /api/games/{id}/org/{org_id}/ - Org inspector."""
    session = _get_session_or_none(game_id, request.user.id)
    if session is None:
        return _error("Game not found", http_status=404)
    bridge = _get_bridge()
    data = bridge.get_inspector_org(uuid.UUID(str(session.id)), org_id)
    return _envelope(data, tick=session.current_tick, session_id=str(session.id))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def inspector_community(request: Request, game_id: str, hyperedge_id: str) -> JsonResponse:
    """GET /api/games/{id}/community/{hyperedge_id}/ - Community inspector."""
    session = _get_session_or_none(game_id, request.user.id)
    if session is None:
        return _error("Game not found", http_status=404)
    bridge = _get_bridge()
    data = bridge.get_inspector_community(uuid.UUID(str(session.id)), hyperedge_id)
    return _envelope(data, tick=session.current_tick, session_id=str(session.id))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def inspector_edge(request: Request, game_id: str, edge_id: str) -> JsonResponse:
    """GET /api/games/{id}/edge/{edge_id}/ - Edge inspector."""
    session = _get_session_or_none(game_id, request.user.id)
    if session is None:
        return _error("Game not found", http_status=404)
    bridge = _get_bridge()
    data = bridge.get_inspector_edge(uuid.UUID(str(session.id)), edge_id)
    return _envelope(data, tick=session.current_tick, session_id=str(session.id))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def inspector_hex(request: Request, game_id: str, h3_index: str) -> JsonResponse:
    """GET /api/games/{id}/hex/{h3_index}/ - Hex inspector."""
    session = _get_session_or_none(game_id, request.user.id)
    if session is None:
        return _error("Game not found", http_status=404)
    bridge = _get_bridge()
    data = bridge.get_inspector_hex(uuid.UUID(str(session.id)), h3_index)
    return _envelope(data, tick=session.current_tick, session_id=str(session.id))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def inspector_org_history(request: Request, game_id: str, org_id: str) -> JsonResponse:
    """GET /api/games/{id}/org/{org_id}/history/ - Org per-tick history (spec 111 C2)."""
    session = _get_session_or_none(game_id, request.user.id)
    if session is None:
        return _error("Game not found", http_status=404)
    bridge = _get_bridge()
    data = bridge.get_org_history(uuid.UUID(str(session.id)), org_id)
    return _envelope(data, tick=session.current_tick, session_id=str(session.id))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def inspector_territory_history(request: Request, game_id: str, county_fips: str) -> JsonResponse:
    """GET /api/games/{id}/territory/{county_fips}/history/ - Territory per-tick
    history (spec 111 C2)."""
    session = _get_session_or_none(game_id, request.user.id)
    if session is None:
        return _error("Game not found", http_status=404)
    bridge = _get_bridge()
    data = bridge.get_territory_history(uuid.UUID(str(session.id)), county_fips)
    return _envelope(data, tick=session.current_tick, session_id=str(session.id))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def inspector_node_history(request: Request, game_id: str, node_id: str) -> JsonResponse:
    """GET /api/games/{id}/node/{node_id}/history/ - Survival duel chart
    history (Program 17 Wave 2 W2.5b, owner ruling 3).

    Rides the generic node-inspector URL shape (social_class has no
    dedicated ``/class/`` route, unlike org/territory); the bridge always
    resolves ``node_id`` against ``class_snapshot`` regardless of the
    node's real type — an id that never had a class row simply returns an
    honest empty history/ruptures pair, never a 404 (matches
    ``inspector_org_history``/``inspector_territory_history``'s unknown-id
    behavior).
    """
    session = _get_session_or_none(game_id, request.user.id)
    if session is None:
        return _error("Game not found", http_status=404)
    bridge = _get_bridge()
    data = bridge.get_class_history(uuid.UUID(str(session.id)), node_id)
    return _envelope(data, tick=session.current_tick, session_id=str(session.id))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def inspector_edge_history(request: Request, game_id: str, edge_id: str) -> JsonResponse:
    """GET /api/games/{id}/edge/{edge_id}/history/ - Edge-weight history
    sparkline (audit Wave 4 straggler, task #76).

    Rides the same ``edge_id`` id scheme (``"{source}->{target}"``)
    ``inspector_edge`` already uses; an id that never had an edge_snapshot
    row simply returns an honest empty history, never a 404 (matches
    ``inspector_org_history``/``inspector_territory_history``'s unknown-id
    behavior).
    """
    session = _get_session_or_none(game_id, request.user.id)
    if session is None:
        return _error("Game not found", http_status=404)
    bridge = _get_bridge()
    data = bridge.get_edge_history(uuid.UUID(str(session.id)), edge_id)
    return _envelope(data, tick=session.current_tick, session_id=str(session.id))


def _explain_result_to_dict(result: Any) -> dict[str, Any]:
    """Project a :class:`game.provenance.ExplainResult` onto the
    ``/explain/`` response body (architecture.md §2.4)."""
    inputs = [
        {"name": i.name, "label": i.label, "value": i.value, "kind": i.kind, "ref": i.ref}
        for i in result.inputs
    ]
    constants = [row for row in inputs if row["kind"] == "constant"]
    return {
        "metric": result.metric,
        "scope": result.scope,
        "value": result.value,
        "formula": {
            "name": result.formula_name,
            "expression": result.expression,
            "doc": result.doc,
        },
        "inputs": inputs,
        "constants": constants,
    }


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def game_explain(request: Request, game_id: str) -> JsonResponse:
    """GET /api/games/{id}/explain/?metric=<name>&scope=<scope> — Formula
    provenance for one metric (spec-113 Lane D, architecture.md §2.4).

    Backs InspectionStack's terminal FormulaCard frame: expression, real
    per-scope input values, constants with provenance. ``scope`` grammar:
    ``global`` | ``hex:<h3>`` | ``org:<id>``.

    Errors (Constitution III.11 — loud, not silent):
        400: missing/malformed ``metric``/``scope``, or a scope kind this
            metric does not support (body names the supported kinds).
        404: unknown ``metric``, or a well-formed scope naming a hex/org
            that does not exist in this game.
    """
    session = _get_session_or_none(game_id, request.user.id)
    if session is None:
        return _error("Game not found", http_status=404)

    metric = request.query_params.get("metric")
    raw_scope = request.query_params.get("scope")
    if not metric:
        return _error("Missing required query parameter 'metric'", http_status=400)
    if not raw_scope:
        return _error("Missing required query parameter 'scope'", http_status=400)

    from .provenance import (
        METRIC_PROVENANCE,
        SUPPORTED_SCOPE_KINDS,
        ScopeEntityNotFoundError,
        UnknownMetricError,
        UnsupportedScopeError,
        explain_metric,
        parse_scope,
    )

    scope = parse_scope(raw_scope)
    if scope.kind not in SUPPORTED_SCOPE_KINDS:
        return _error(
            f"Invalid scope kind {scope.kind!r}. Valid kinds: {sorted(SUPPORTED_SCOPE_KINDS)}",
            http_status=400,
        )

    bridge = _get_bridge()
    session_uuid = uuid.UUID(str(session.id))

    if hasattr(bridge, "hydrate_state"):
        try:
            state, graph = bridge.hydrate_state(session_uuid)
        except Exception:  # noqa: BLE001 — diagnostic; surfaced as a clean 404
            logger.exception("game_explain: failed to hydrate state for session=%s", session_uuid)
            return _error("Game state not available", http_status=404)
        try:
            result = explain_metric(state, graph, metric, scope)
        except UnknownMetricError:
            return _error(
                f"Unknown metric {metric!r}. Valid metrics: {sorted(METRIC_PROVENANCE)}",
                http_status=404,
            )
        except UnsupportedScopeError as exc:
            return _error(
                f"Metric {metric!r} does not support scope kind {exc.kind!r}. "
                f"Supported: {sorted(exc.supported)}",
                http_status=400,
            )
        except ScopeEntityNotFoundError as exc:
            return _error(
                f"No {exc.kind} found for id {exc.entity_id!r} in this game",
                http_status=404,
            )
        data = _explain_result_to_dict(result)
    else:
        # StubEngineBridge (no Postgres/engine): its own self-contained
        # mock manifest, same metric catalog and response shape, but no
        # per-scope validation (see StubEngineBridge.get_explain's docstring).
        data = bridge.get_explain(session_uuid, metric, raw_scope)
        if data is None:
            return _error(
                f"Unknown metric {metric!r}. Valid metrics: {sorted(METRIC_PROVENANCE)}",
                http_status=404,
            )

    return _envelope(data, tick=session.current_tick, session_id=str(session.id))


# ---------------------------------------------------------------------- #
# Action endpoints
# ---------------------------------------------------------------------- #


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def actions_available(request: Request, game_id: str) -> JsonResponse:
    """GET /api/games/{id}/actions/available/ — Available actions for current tick."""
    session = _get_session_or_none(game_id, request.user.id)
    if session is None:
        return _error("Game not found", http_status=404)

    bridge = _get_bridge()
    actions = bridge.get_available_actions(uuid.UUID(str(session.id)))
    return _envelope(
        actions,
        tick=session.current_tick,
        session_id=str(session.id),
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def actions_preview(request: Request, game_id: str) -> JsonResponse:
    """POST /api/games/{id}/actions/preview/ — Preview estimated action effects.

    Read-only estimation. Does not modify game state.
    """
    session = _get_session_or_none(game_id, request.user.id)
    if session is None:
        return _error("Game not found", http_status=404)

    serializer = SubmitActionSerializer(data=request.data)
    if not serializer.is_valid():
        return _error(str(serializer.errors))

    org_id = serializer.validated_data["org_id"]
    verb = serializer.validated_data["verb"]
    target_id = serializer.validated_data.get("target_id")

    from game.engine_bridge import CANONICAL_VERBS

    if verb not in CANONICAL_VERBS:
        return _error(f"Invalid verb '{verb}'. Valid verbs: {sorted(CANONICAL_VERBS)}")

    bridge = _get_bridge()
    preview = bridge.preview_action(
        session_id=uuid.UUID(str(session.id)),
        org_id=org_id,
        verb=verb,
        target_id=target_id,
    )
    return _envelope(
        preview,
        tick=session.current_tick,
        session_id=str(session.id),
    )


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def action_delete(request: Request, game_id: str, action_id: int) -> JsonResponse:
    """DELETE /api/games/{id}/actions/{action_id}/ — Cancel a pending action."""
    session = _get_session_or_none(game_id, request.user.id)
    if session is None:
        return _error("Game not found", http_status=404)

    try:
        action = PlayerAction.objects.get(
            id=action_id,
            session_id=session.id,
            tick=session.current_tick,
            resolved=False,
        )
        action.delete()
        return _envelope(
            {"status": "deleted", "action_id": action_id},
            tick=session.current_tick,
            session_id=str(session.id),
        )
    except PlayerAction.DoesNotExist:
        return _error("Action not found or already resolved", http_status=404)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def actions_list(request: Request, game_id: str) -> JsonResponse:
    """GET: Pending actions. POST: Submit a new action."""
    session = _get_session_or_none(game_id, request.user.id)
    if session is None:
        return _error("Game not found", http_status=404)

    if request.method == "GET":
        pending = PlayerAction.objects.filter(
            session_id=session.id,
            tick=session.current_tick,
            resolved=False,
        )
        data = [
            {
                "id": a.id,
                "org_id": a.org_id,
                "verb": a.verb,
                "action_type": a.action_type,
                "target_id": a.target_id,
                "tick": a.tick,
            }
            for a in pending
        ]
        return _envelope(data, tick=session.current_tick, session_id=str(session.id))

    # POST: Submit action
    serializer = SubmitActionSerializer(data=request.data)
    if not serializer.is_valid():
        logger.warning(
            "Invalid action submission session=%s: %s",
            sanitize_for_log(game_id),
            sanitize_for_log(serializer.errors),
        )
        return _error(str(serializer.errors))

    # T017: Server-side verb validation against canonical verb set
    from game.engine_bridge import CANONICAL_VERBS

    submitted_verb = serializer.validated_data.get("verb", "")
    if submitted_verb not in CANONICAL_VERBS:
        logger.warning(
            "Invalid verb '%s' submitted session=%s",
            sanitize_for_log(submitted_verb),
            sanitize_for_log(game_id),
        )
        return _error(
            f"Invalid verb '{submitted_verb}'. Valid verbs: {sorted(CANONICAL_VERBS)}",
            http_status=400,
        )

    bridge = _get_bridge()
    try:
        turn_id = bridge.submit_action(
            session_id=uuid.UUID(str(session.id)),
            tick=session.current_tick,
            org_id=serializer.validated_data["org_id"],
            verb=serializer.validated_data["verb"],
            action_type=serializer.validated_data.get("action_type"),
            target_id=serializer.validated_data.get("target_id"),
            target_community=serializer.validated_data.get("target_community"),
            params_json=serializer.validated_data.get("params_json"),
        )
    except ValueError as exc:
        logger.info(
            "Action rejected (affordability) session=%s: %s", sanitize_for_log(game_id), exc
        )
        return _error(
            "Action rejected: the request was not valid for the current game state.",
            http_status=400,
        )
    logger.info(
        "Action submitted session=%s tick=%d org=%s verb=%s turn_id=%d",
        session.id,
        session.current_tick,
        serializer.validated_data["org_id"],
        serializer.validated_data["verb"],
        turn_id,
    )
    log_game_event(
        category="action_submit",
        message=f"Action: {serializer.validated_data['verb']} by {serializer.validated_data['org_id']}",
        session_id=session.id,
        user_id=request.user.id,
        tick=session.current_tick,
        details={
            "org_id": serializer.validated_data["org_id"],
            "verb": serializer.validated_data["verb"],
        },
        correlation_id=getattr(request, "correlation_id", None),
    )
    return _envelope(
        {"turn_id": turn_id},
        tick=session.current_tick,
        session_id=str(session.id),
        http_status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def resolve_tick(request: Request, game_id: str) -> JsonResponse:
    """POST /api/games/{id}/resolve/ — Resolve the current tick.

    Uses select_for_update() within transaction.atomic() to prevent
    concurrent resolution of the same tick (T018 idempotency guard).
    """
    from django.db import transaction

    session = _get_session_or_none(game_id, request.user.id)
    if session is None:
        return _error("Game not found", http_status=404)
    if session.status != "active":
        return _error(f"Cannot resolve tick for game in '{session.status}' status")

    # T018: Atomic idempotency guard — lock the row and set status to "resolving"
    try:
        with transaction.atomic():
            locked = GameSession.objects.select_for_update().get(id=session.id, status="active")
            GameSession.objects.filter(id=locked.id).update(
                status="resolving", updated_at=timezone.now()
            )
    except GameSession.DoesNotExist:
        return _error("Game is already being resolved or is no longer active", http_status=409)

    bridge = _get_bridge()
    logger.info("Resolving tick session=%s current_tick=%d", session.id, session.current_tick)

    try:
        snapshot = resolve_game_tick(bridge, uuid.UUID(str(session.id)))
    except Exception:
        # Restore status on failure so the game can be retried
        GameSession.objects.filter(id=session.id).update(status="active", updated_at=timezone.now())
        logger.exception("Tick resolution failed session=%s", session.id)
        return _error("Tick resolution failed", http_status=500)

    # Update session tick and restore active status
    new_tick = snapshot.get("tick", session.current_tick + 1)
    GameSession.objects.filter(id=session.id).update(
        current_tick=new_tick, status="active", updated_at=timezone.now()
    )

    logger.info("Tick resolved session=%s new_tick=%d", session.id, new_tick)
    log_game_event(
        category="tick_resolve",
        message=f"Tick resolved: {session.current_tick} -> {new_tick}",
        session_id=session.id,
        user_id=request.user.id,
        tick=new_tick,
        correlation_id=getattr(request, "correlation_id", None),
    )
    return _envelope(
        snapshot,
        tick=new_tick,
        session_id=str(session.id),
    )


# ---------------------------------------------------------------------- #
# Results endpoints
# ---------------------------------------------------------------------- #


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def tick_results(request: Request, game_id: str, tick: int) -> JsonResponse:
    """GET /api/games/{id}/results/{tick}/ — Action results for a tick."""
    session = _get_session_or_none(game_id, request.user.id)
    if session is None:
        return _error("Game not found", http_status=404)

    results = ActionResult.objects.filter(
        session_id=session.id,
        tick=tick,
    )
    result_data: list[dict[str, Any]] = [
        {
            "org_id": r.org_id,
            "action_type": r.action_type,
            "target_id": r.target_id,
            "initiative_score": r.initiative_score,
            "action_cost": r.action_cost,
            "success": r.success,
            "consciousness_delta": r.consciousness_delta,
            "heat_delta": r.heat_delta,
            "details": r.details,
        }
        for r in results
    ]
    result_serializer = ActionResultSerializer(result_data, many=True)  # type: ignore[arg-type]
    return _envelope(result_serializer.data, tick=tick, session_id=str(session.id))


# ---------------------------------------------------------------------- #
# Helpers
# ---------------------------------------------------------------------- #


def _get_session_or_none(game_id: str, user_id: int | None) -> GameSession | None:
    """Look up a game session by ID, scoped to the requesting user."""
    try:
        parsed_id = uuid.UUID(game_id)
    except ValueError:
        return None
    try:
        session: GameSession = GameSession.objects.get(id=parsed_id, player_id=user_id)
        return session
    except GameSession.DoesNotExist:
        return None


# ---------------------------------------------------------------------- #
# Per-verb action endpoints (Spec 040)
# ---------------------------------------------------------------------- #

# Common base fields that all verb serializers share — everything
# else in validated_data is a verb-specific parameter.
_COMMON_FIELDS = frozenset({"org_id", "target_id"})


class BaseVerbActionView(APIView):
    """Base for all per-verb action endpoints (Spec 040 §6.3).

    Subclasses set ``serializer_class`` and ``verb``. The base handles:
    - Authentication (``IsAuthenticated``)
    - Game session lookup and active-status check
    - Serializer validation
    - ``PlayerAction`` creation via ``EngineBridge.submit_action``
    - Cost/warning preview via ``EngineBridge.preview_action``
    """

    permission_classes = [IsAuthenticated]
    serializer_class: type[BaseActionSerializer] | None = None
    verb: str | None = None

    def post(self, request: Request, game_id: str) -> JsonResponse:
        """Handle POST — validate, persist action, return confirmation."""
        session = _get_session_or_none(game_id, request.user.id)
        if session is None:
            return _error("Game not found", http_status=404)

        if session.status != "active":
            return _error_with_code(
                f"Cannot submit actions for game in '{session.status}' status",
                "ACTION_GAME_NOT_ACTIVE",
            )

        if self.serializer_class is None or self.verb is None:
            raise ImproperlyConfigured(
                f"{type(self).__name__} must define serializer_class and verb"
            )

        serializer = self.serializer_class(
            data=request.data,
            context={"game": session, "request": request},
        )
        if not serializer.is_valid():
            return _error_with_code(
                str(serializer.errors),
                "ACTION_INVALID_PARAMS",
            )

        # Extract verb-specific params (everything except common fields)
        verb_params = {
            k: v for k, v in serializer.validated_data.items() if k not in _COMMON_FIELDS
        }

        bridge = _get_bridge()
        try:
            turn_id = bridge.submit_action(
                session_id=uuid.UUID(str(session.id)),
                tick=session.current_tick,
                org_id=serializer.validated_data["org_id"],
                verb=self.verb,
                target_id=serializer.validated_data["target_id"],
                params_json=verb_params if verb_params else None,
            )
        except ValueError as exc:
            logger.info(
                "Action rejected session=%s verb=%s: %s",
                sanitize_for_log(game_id),
                self.verb,
                exc,
            )
            return _error(
                "Action rejected: the request was not valid for the current game state.",
                http_status=400,
            )

        # Compute cost preview and warnings (read-only)
        preview = bridge.preview_action(
            session_id=uuid.UUID(str(session.id)),
            org_id=serializer.validated_data["org_id"],
            verb=self.verb,
            target_id=serializer.validated_data["target_id"],
        )

        logger.info(
            "Per-verb action submitted session=%s tick=%d verb=%s org=%s turn_id=%s",
            session.id,
            session.current_tick,
            self.verb,
            serializer.validated_data["org_id"],
            turn_id,
        )
        log_game_event(
            category="action_submit",
            message=f"Action: {self.verb} by {serializer.validated_data['org_id']}",
            session_id=session.id,
            user_id=request.user.id,
            tick=session.current_tick,
            details={
                "org_id": serializer.validated_data["org_id"],
                "verb": self.verb,
                "target_id": serializer.validated_data["target_id"],
            },
            correlation_id=getattr(request, "correlation_id", None),
        )

        return _envelope(
            {
                "turn_id": turn_id,
                "verb": self.verb,
                "org_id": serializer.validated_data["org_id"],
                "target_id": serializer.validated_data["target_id"],
                "tick": session.current_tick,
                "ap_cost": preview.get("action_point_cost", 1),
                "resource_cost": preview.get("resource_cost", {}),
                "warnings": preview.get("warnings", []),
            },
            tick=session.current_tick,
            session_id=str(session.id),
            http_status=status.HTTP_201_CREATED,
        )


class EducateVerbView(APIView):
    """GET/POST /api/games/{id}/verbs/educate/"""

    def get(self, request: Request, game_id: UUID) -> Response:
        session = get_object_or_404(GameSession, id=game_id)
        org_id = request.query_params.get("org_id")
        if not org_id:
            return Response(
                {"status": "error", "message": "org_id query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        bridge = _get_bridge()
        data = bridge.get_educate_targets(session.id, org_id)
        if data.get("status") == "error":
            return Response(data, status=status.HTTP_400_BAD_REQUEST)

        serializer = EducateAvailableSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request: Request, game_id: UUID) -> Response:
        session = get_object_or_404(GameSession, id=game_id)

        serializer = EducateSubmitSerializer(
            data=request.data, context={"game": session, "request": request}
        )
        if not serializer.is_valid():
            return Response(
                {"status": "error", "message": "Validation failed", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        org_id = data["org_id"]
        target_community_id = data["target_community_id"]
        params = data.get("params", {})

        bridge = _get_bridge()
        try:
            action_id = bridge.submit_action(
                session_id=session.id,
                tick=session.current_tick,
                org_id=org_id,
                verb="educate",
                target_community=target_community_id,
                params_json=params,
            )
        except ValueError as e:
            return _action_rejected(e, session_id=session.id)

        return Response(
            {
                "status": "ok",
                "tick": session.current_tick,
                "verb": "educate",
                "action_id": action_id,
                "acting_org_id": org_id,
                "target_community_id": target_community_id,
            },
            status=status.HTTP_201_CREATED,
        )


class AidVerbView(APIView):
    """GET/POST /api/games/{id}/verbs/aid/"""

    def get(self, request: Request, game_id: UUID) -> Response:
        session = get_object_or_404(GameSession, id=game_id)
        org_id = request.query_params.get("org_id")
        if not org_id:
            return Response(
                {"status": "error", "message": "org_id query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        bridge = _get_bridge()
        data = bridge.get_aid_targets(session.id, org_id)
        if data.get("status") == "error":
            return Response(data, status=status.HTTP_400_BAD_REQUEST)

        serializer = AidAvailableSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request: Request, game_id: UUID) -> Response:
        session = get_object_or_404(GameSession, id=game_id)

        serializer = AidSubmitSerializer(
            data=request.data, context={"game": session, "request": request}
        )
        if not serializer.is_valid():
            return Response(
                {"status": "error", "message": "Validation failed", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        org_id = data["org_id"]
        target_id = data["target_id"]
        params = data.get("params", {})

        bridge = _get_bridge()
        try:
            action_id = bridge.submit_action(
                session_id=session.id,
                tick=session.current_tick,
                org_id=org_id,
                verb="aid",
                target_id=target_id,
                params_json=params,
            )
        except ValueError as e:
            return _action_rejected(e, session_id=session.id)

        return Response(
            {
                "status": "ok",
                "tick": session.current_tick,
                "verb": "aid",
                "action_id": action_id,
                "acting_org_id": org_id,
                "target_id": target_id,
            },
            status=status.HTTP_201_CREATED,
        )


class AttackVerbView(APIView):
    """GET/POST /api/games/{id}/verbs/attack/"""

    def get(self, request: Request, game_id: UUID) -> Response:
        session = get_object_or_404(GameSession, id=game_id)
        org_id = request.query_params.get("org_id")
        if not org_id:
            return Response(
                {"status": "error", "message": "org_id query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        bridge = _get_bridge()
        data = bridge.get_attack_targets(session.id, org_id)
        if data.get("status") == "error":
            return Response(data, status=status.HTTP_400_BAD_REQUEST)

        serializer = AttackAvailableSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request: Request, game_id: UUID) -> Response:
        session = get_object_or_404(GameSession, id=game_id)

        serializer = AttackSubmitSerializer(
            data=request.data, context={"game": session, "request": request}
        )
        if not serializer.is_valid():
            return Response(
                {"status": "error", "message": "Validation failed", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        org_id = data["org_id"]
        target_id = data["target_id"]
        params = data.get("params", {})

        bridge = _get_bridge()
        try:
            action_id = bridge.submit_action(
                session_id=session.id,
                tick=session.current_tick,
                org_id=org_id,
                verb="attack",
                target_id=target_id,
                params_json=params,
            )
        except ValueError as e:
            return _action_rejected(e, session_id=session.id)

        return Response(
            {
                "status": "ok",
                "tick": session.current_tick,
                "verb": "attack",
                "action_id": action_id,
                "acting_org_id": org_id,
                "target_id": target_id,
            },
            status=status.HTTP_201_CREATED,
        )


class MobilizeVerbView(APIView):
    """GET/POST /api/games/{id}/verbs/mobilize/"""

    def get(self, request: Request, game_id: UUID) -> Response:
        session = get_object_or_404(GameSession, id=game_id)
        org_id = request.query_params.get("org_id")
        if not org_id:
            return Response(
                {"status": "error", "message": "org_id query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        bridge = _get_bridge()
        data = bridge.get_mobilize_targets(session.id, org_id)
        if data.get("status") == "error":
            return Response(data, status=status.HTTP_400_BAD_REQUEST)

        serializer = MobilizeAvailableSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request: Request, game_id: UUID) -> Response:
        session = get_object_or_404(GameSession, id=game_id)

        serializer = MobilizeSubmitSerializer(
            data=request.data, context={"game": session, "request": request}
        )
        if not serializer.is_valid():
            return Response(
                {"status": "error", "message": "Validation failed", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        org_id = data["org_id"]
        target_id = data["target_id"]
        params = data.get("params", {})

        bridge = _get_bridge()
        try:
            action_id = bridge.submit_action(
                session_id=session.id,
                tick=session.current_tick,
                org_id=org_id,
                verb="mobilize",
                target_id=target_id,
                params_json=params,
            )
        except ValueError as e:
            return _action_rejected(e, session_id=session.id)

        return Response(
            {
                "status": "ok",
                "tick": session.current_tick,
                "verb": "mobilize",
                "action_id": action_id,
                "acting_org_id": org_id,
                "target_id": target_id,
            },
            status=status.HTTP_201_CREATED,
        )


class CampaignActionView(BaseVerbActionView):
    """POST /api/games/{id}/actions/campaign/."""

    serializer_class = CampaignActionSerializer
    verb = "campaign"


class MoveVerbView(APIView):
    """GET/POST /api/games/{id}/verbs/move/"""

    def get(self, request: Request, game_id: UUID) -> Response:
        session = get_object_or_404(GameSession, id=game_id)
        org_id = request.query_params.get("org_id")
        if not org_id:
            return Response(
                {"status": "error", "message": "org_id query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        bridge = _get_bridge()
        data = bridge.get_move_targets(session.id, org_id)
        if data.get("status") == "error":
            return Response(data, status=status.HTTP_400_BAD_REQUEST)

        serializer = MoveAvailableSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request: Request, game_id: UUID) -> Response:
        session = get_object_or_404(GameSession, id=game_id)

        serializer = MoveSubmitSerializer(
            data=request.data, context={"game": session, "request": request}
        )
        if not serializer.is_valid():
            return Response(
                {"status": "error", "message": "Validation failed", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        org_id = data["org_id"]
        target_id = data["target_id"]
        params = data.get("params", {})

        bridge = _get_bridge()
        try:
            action_id = bridge.submit_action(
                session_id=session.id,
                tick=session.current_tick,
                org_id=org_id,
                verb="move",
                target_id=target_id,
                params_json=params,
            )
        except ValueError as e:
            return _action_rejected(e, session_id=session.id)

        return Response(
            {
                "status": "ok",
                "tick": session.current_tick,
                "verb": "move",
                "action_id": action_id,
                "acting_org_id": org_id,
                "target_id": target_id,
            },
            status=status.HTTP_201_CREATED,
        )


class InvestigateVerbView(APIView):
    """GET/POST /api/games/{id}/verbs/investigate/"""

    def get(self, request: Request, game_id: UUID) -> Response:
        session = get_object_or_404(GameSession, id=game_id)
        org_id = request.query_params.get("org_id")
        if not org_id:
            return Response(
                {"status": "error", "message": "org_id query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        bridge = _get_bridge()
        data = bridge.get_investigate_targets(session.id, org_id)
        if data.get("status") == "error":
            return Response(data, status=status.HTTP_400_BAD_REQUEST)

        serializer = InvestigateAvailableSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request: Request, game_id: UUID) -> Response:
        session = get_object_or_404(GameSession, id=game_id)

        serializer = InvestigateSubmitSerializer(
            data=request.data, context={"game": session, "request": request}
        )
        if not serializer.is_valid():
            return Response(
                {"status": "error", "message": "Validation failed", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        org_id = data["org_id"]
        target_id = data.get("target_id", None)
        params = data.get("params", {})

        bridge = _get_bridge()
        try:
            action_id = bridge.submit_action(
                session_id=session.id,
                tick=session.current_tick,
                org_id=org_id,
                verb="investigate",
                target_id=target_id,
                params_json=params,
            )
        except ValueError as e:
            return _action_rejected(e, session_id=session.id)

        return Response(
            {
                "status": "ok",
                "tick": session.current_tick,
                "verb": "investigate",
                "action_id": action_id,
                "acting_org_id": org_id,
                "target_id": target_id,
            },
            status=status.HTTP_201_CREATED,
        )


class ReproduceVerbView(APIView):
    """GET/POST /api/games/{id}/verbs/reproduce/"""

    def get(self, request: Request, game_id: UUID) -> Response:
        session = get_object_or_404(GameSession, id=game_id)
        org_id = request.query_params.get("org_id")
        if not org_id:
            return Response(
                {"status": "error", "message": "org_id query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        bridge = _get_bridge()
        data = bridge.get_reproduce_targets(session.id, org_id)
        if data.get("status") == "error":
            return Response(data, status=status.HTTP_400_BAD_REQUEST)

        serializer = ReproduceAvailableSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request: Request, game_id: UUID) -> Response:
        session = get_object_or_404(GameSession, id=game_id)

        serializer = ReproduceSubmitSerializer(
            data=request.data, context={"game": session, "request": request}
        )
        if not serializer.is_valid():
            return Response(
                {"status": "error", "message": "Validation failed", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        org_id = data["org_id"]
        target_id = data.get("target_id", None)
        params = data.get("params", {})

        bridge = _get_bridge()
        try:
            action_id = bridge.submit_action(
                session_id=session.id,
                tick=session.current_tick,
                org_id=org_id,
                verb="reproduce",
                target_id=target_id,
                params_json=params,
            )
        except ValueError as e:
            return _action_rejected(e, session_id=session.id)

        return Response(
            {
                "status": "ok",
                "tick": session.current_tick,
                "verb": "reproduce",
                "action_id": action_id,
                "acting_org_id": org_id,
                "target_id": target_id,
            },
            status=status.HTTP_201_CREATED,
        )


class NegotiateVerbView(APIView):
    """GET/POST /api/games/{id}/verbs/negotiate/"""

    def get(self, request: Request, game_id: UUID) -> Response:
        session = get_object_or_404(GameSession, id=game_id)
        org_id = request.query_params.get("org_id")
        if not org_id:
            return Response(
                {"status": "error", "message": "org_id query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        bridge = _get_bridge()
        data = bridge.get_negotiate_targets(session.id, org_id)
        if data.get("status") == "error":
            return Response(data, status=status.HTTP_400_BAD_REQUEST)

        serializer = NegotiateAvailableSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request: Request, game_id: UUID) -> Response:
        session = get_object_or_404(GameSession, id=game_id)

        serializer = NegotiateSubmitSerializer(
            data=request.data, context={"game": session, "request": request}
        )
        if not serializer.is_valid():
            return Response(
                {"status": "error", "message": "Validation failed", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        org_id = data["org_id"]
        target_id = data["target_id"]
        params = data.get("params", {})

        bridge = _get_bridge()
        try:
            action_id = bridge.submit_action(
                session_id=session.id,
                tick=session.current_tick,
                org_id=org_id,
                verb="negotiate",
                target_id=target_id,
                params_json=params,
            )
        except ValueError as e:
            return _action_rejected(e, session_id=session.id)

        return Response(
            {
                "status": "ok",
                "tick": session.current_tick,
                "verb": "negotiate",
                "action_id": action_id,
                "acting_org_id": org_id,
                "target_id": target_id,
            },
            status=status.HTTP_201_CREATED,
        )
