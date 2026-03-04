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

from django.http import JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request

from game.models import ActionResult, GameSession, PlayerAction

from .log_handler import log_game_event
from .serializers import (
    ActionResultSerializer,
    CreateGameSerializer,
    GameSessionListSerializer,
    GameSnapshotSerializer,
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
    In production, initializes from PostgresRuntime.
    """
    global _bridge_instance  # noqa: PLW0603
    if _bridge_instance is None:
        # Lazy import — only instantiate if actually serving API requests
        # In production, the persistence layer is injected via settings
        # For now, raise if called without explicit initialization
        msg = (
            "EngineBridge not initialized. Call game.api.init_bridge(persistence) "
            "or set game.api._bridge_instance in tests."
        )
        raise RuntimeError(msg)
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
