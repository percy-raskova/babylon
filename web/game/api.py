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

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponseBase, JsonResponse
from django.shortcuts import get_object_or_404, render
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from game.models import ActionResult, GameSession, PlayerAction

from .log_handler import log_game_event
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

    Returns a mock-friendly ``Any`` so tests can replace ``_bridge_instance``.
    In production, initializes from PostgresRuntime via ``GameConfig.ready()``.
    Falls back to ``StubEngineBridge`` when no real bridge is configured
    (e.g., during development without Postgres).
    """
    global _bridge_instance  # noqa: PLW0603
    if _bridge_instance is None:
        from .stub_bridge import StubEngineBridge

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
    GameSession.objects.filter(id=session.id).update(status="paused")
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
    GameSession.objects.filter(id=session.id).update(status="active")
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


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def game_map(request: Request, game_id: str) -> JsonResponse:
    """GET /api/games/{id}/map/ — Hex map state snapshot."""
    session = _get_session_or_none(game_id, request.user.id)
    if session is None:
        return _error("Game not found", http_status=404)

    try:
        tick_query = request.query_params.get("tick")
        tick = int(tick_query) if tick_query is not None else None
    except ValueError:
        return _error("Invalid tick parameter", http_status=400)

    bridge = _get_bridge()
    snapshot = bridge.get_map_snapshot(uuid.UUID(str(session.id)), tick=tick)
    return _envelope(
        snapshot,
        tick=snapshot.get("metadata", {}).get("tick", session.current_tick),
        session_id=str(session.id),
    )


# The 6 canonical map layers matching the frontend MapLayer type
VALID_MAP_LAYERS: frozenset[str] = frozenset(
    ["heat", "consciousness", "wealth", "rent", "biocapacity", "population"]
)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def game_map_layer(request: Request, game_id: str, layer: str) -> JsonResponse:
    """GET /api/games/{id}/map/{layer}/ — Per-layer GeoJSON data.

    Returns a GeoJSON FeatureCollection with properties filtered
    to include only the requested metric plus the identifying fields
    (h3_index, county_fips, county_name).

    Valid layers: heat, consciousness, wealth, rent, biocapacity, population.
    """
    if layer not in VALID_MAP_LAYERS:
        return _error(
            f"Invalid layer '{layer}'. Valid layers: {sorted(VALID_MAP_LAYERS)}",
            http_status=400,
        )

    session = _get_session_or_none(game_id, request.user.id)
    if session is None:
        return _error("Game not found", http_status=404)

    try:
        tick_query = request.query_params.get("tick")
        tick = int(tick_query) if tick_query is not None else None
    except ValueError:
        return _error("Invalid tick parameter", http_status=400)

    bridge = _get_bridge()
    snapshot = bridge.get_map_snapshot(
        uuid.UUID(str(session.id)),
        tick=tick,
        layer=layer,
    )

    # Filter properties to only include the requested layer metric
    # plus identifying fields (h3_index, county_fips, county_name)
    keep_keys = {"h3_index", "county_fips", "county_name", layer}
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

    result = {
        "type": "FeatureCollection",
        "metadata": {
            **snapshot.get("metadata", {}),
            "layer": layer,
        },
        "features": filtered_features,
    }

    return _envelope(
        result,
        tick=snapshot.get("metadata", {}).get("tick", session.current_tick),
        session_id=str(session.id),
    )


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
        logger.warning("Invalid action submission session=%s: %s", game_id, serializer.errors)
        return _error(str(serializer.errors))

    # T017: Server-side verb validation against canonical verb set
    from game.engine_bridge import CANONICAL_VERBS

    submitted_verb = serializer.validated_data.get("verb", "")
    if submitted_verb not in CANONICAL_VERBS:
        logger.warning("Invalid verb '%s' submitted session=%s", submitted_verb, game_id)
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
        logger.info("Action rejected (affordability) session=%s: %s", game_id, exc)
        return _error(str(exc), http_status=400)
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
            GameSession.objects.filter(id=locked.id).update(status="resolving")
    except GameSession.DoesNotExist:
        return _error("Game is already being resolved or is no longer active", http_status=409)

    bridge = _get_bridge()
    logger.info("Resolving tick session=%s current_tick=%d", session.id, session.current_tick)

    try:
        snapshot = resolve_game_tick(bridge, uuid.UUID(str(session.id)))
    except Exception:
        # Restore status on failure so the game can be retried
        GameSession.objects.filter(id=session.id).update(status="active")
        logger.exception("Tick resolution failed session=%s", session.id)
        return _error("Tick resolution failed", http_status=500)

    # Update session tick and restore active status
    new_tick = snapshot.get("tick", session.current_tick + 1)
    GameSession.objects.filter(id=session.id).update(current_tick=new_tick, status="active")

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

        assert self.serializer_class is not None
        assert self.verb is not None

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
                game_id,
                self.verb,
                exc,
            )
            return _error(str(exc), http_status=400)

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
            return Response(
                {"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

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
            return Response(
                {"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

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
            return Response(
                {"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

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
            return Response(
                {"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

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
            return Response(
                {"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

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
            return Response(
                {"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

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
            return Response(
                {"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

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
            return Response(
                {"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

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
