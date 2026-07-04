"""Read-only DRF endpoints for the Observatory (spec-096), under ``/api/observatory/``.

Every endpoint is:
- **flag-gated**: 404 when ``settings.OBSERVATORY_ENABLED`` is False (checked
  before auth/DB — security through obscurity, mirroring ``/health/detail/``);
- **auth-gated**: requires an authenticated session (FR-019);
- **read-only**: queries the ``sim`` alias via ``connections["sim"]`` only.

Response envelope matches the product: ``{"status": "ok", "data": ...}`` on
success, ``{"status": "error", "message": ...}`` on error. The CSV endpoint
streams ``text/csv`` instead.
"""

from __future__ import annotations

import csv
import functools
import re
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

from django.conf import settings
from django.db import OperationalError, connections
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseBase, JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request

from .queries import (
    DEFAULT_MAX_TICK_SPAN,
    SCOPE_VIEWS,
    fetch_commits,
    fetch_hex_frame,
    fetch_series,
    fetch_sessions,
    fetch_tick_range,
)

SIM_ALIAS = "sim"

_SCOPE_ID_PATTERNS = {"state": re.compile(r"^\d{2}$"), "county": re.compile(r"^\d{5}$")}
_SERIES_COLUMNS = ["tick", "c_sum", "v_sum", "s_sum", "k_sum", "biocapacity_sum", "hex_count"]


# --------------------------------------------------------------------------- #
# Envelope + gating helpers
# --------------------------------------------------------------------------- #


def _ok(data: Any, http_status: int = 200) -> JsonResponse:
    return JsonResponse({"status": "ok", "data": data}, status=http_status)


def _err(message: str, http_status: int) -> JsonResponse:
    return JsonResponse({"status": "error", "message": message}, status=http_status)


def observatory_enabled_or_404(
    view: Callable[..., HttpResponseBase],
) -> Callable[..., HttpResponseBase]:
    """Return a wrapper that 404s when the Observatory feature flag is off.

    Applied as the OUTERMOST decorator so the flag is checked before DRF's
    authentication runs — a disabled Observatory is invisible to everyone.
    """

    @functools.wraps(view)
    def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        if not getattr(settings, "OBSERVATORY_ENABLED", False):
            raise Http404("Observatory is disabled")
        return view(request, *args, **kwargs)

    return wrapper


@contextmanager
def _sim_cursor() -> Iterator[Any]:
    """Yield a cursor on the read-only ``sim`` alias."""
    with connections[SIM_ALIAS].cursor() as cursor:
        yield cursor


class _BadRequest(Exception):
    """Raised by validators to short-circuit into a 400 response."""


def _valid_uuid(session_id: str) -> str:
    try:
        return str(uuid.UUID(session_id))
    except (ValueError, AttributeError, TypeError) as exc:
        raise _BadRequest(f"invalid session id: {session_id!r}") from exc


def _resolve_scope_id(scope: str, raw: str | None) -> str:
    """Validate/normalise the scope identifier for a scope."""
    if scope == "national":
        return SCOPE_VIEWS["national"][2] or "USA"
    if not raw:
        raise _BadRequest(f"scope_id is required for scope={scope}")
    pattern = _SCOPE_ID_PATTERNS[scope]
    if not pattern.match(raw):
        raise _BadRequest(f"invalid scope_id {raw!r} for scope={scope}")
    return raw


def _parse_int(raw: str | None, name: str) -> int | None:
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except ValueError as exc:
        raise _BadRequest(f"{name} must be an integer") from exc


def _resolve_range(
    cursor: Any,
    session_id: str,
    from_tick: int | None,
    to_tick: int | None,
) -> tuple[int, int] | None:
    """Fill in default tick bounds from the session's committed range + clamp.

    Returns ``None`` when the session has no committed ticks (→ empty series).
    """
    if from_tick is None or to_tick is None:
        rng = fetch_tick_range(cursor, session_id)
        if rng is None:
            return None
        from_tick = rng["min_tick"] if from_tick is None else from_tick
        to_tick = rng["max_tick"] if to_tick is None else to_tick
    if from_tick > to_tick:
        raise _BadRequest("from_tick must be <= to_tick")
    to_tick = min(to_tick, from_tick + DEFAULT_MAX_TICK_SPAN)
    return from_tick, to_tick


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #


@observatory_enabled_or_404
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def observatory_status(request: Request) -> JsonResponse:
    """GET /api/observatory/status/ — feature-flag probe for the frontend."""
    return _ok({"enabled": True, "sim_alias": SIM_ALIAS})


@observatory_enabled_or_404
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def observatory_sessions(request: Request) -> JsonResponse:
    """GET /api/observatory/sessions/ — sessions with >=1 committed tick."""
    try:
        with _sim_cursor() as cursor:
            data = fetch_sessions(cursor)
    except OperationalError:
        return _err("Simulation database unavailable", 503)
    return _ok(data)


@observatory_enabled_or_404
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def observatory_ticks(request: Request, session_id: str) -> JsonResponse:
    """GET /api/observatory/sessions/<id>/ticks/ — committed range + checkpoints."""
    try:
        sid = _valid_uuid(session_id)
    except _BadRequest as exc:
        return _err(str(exc), 400)
    try:
        with _sim_cursor() as cursor:
            data = fetch_tick_range(cursor, sid)
    except OperationalError:
        return _err("Simulation database unavailable", 503)
    if data is None:
        return _err("Session has no committed ticks", 404)
    return _ok(data)


@observatory_enabled_or_404
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def observatory_series(request: Request, session_id: str) -> JsonResponse:
    """GET /api/observatory/sessions/<id>/series/ — value-aggregate time-series."""
    try:
        payload = _series_payload(request, session_id)
    except _BadRequest as exc:
        return _err(str(exc), 400)
    except OperationalError:
        return _err("Simulation database unavailable", 503)
    return _ok(payload)


@observatory_enabled_or_404
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def observatory_series_csv(request: Request, session_id: str) -> HttpResponseBase:
    """GET /api/observatory/sessions/<id>/series.csv/ — same data as CSV."""
    try:
        payload = _series_payload(request, session_id)
    except _BadRequest as exc:
        return _err(str(exc), 400)
    except OperationalError:
        return _err("Simulation database unavailable", 503)
    filename = f"{payload['session_id']}_{payload['scope']}_{payload['scope_id']}.csv"
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    writer.writerow(_SERIES_COLUMNS)
    for point in payload["points"]:
        writer.writerow([point[column] for column in _SERIES_COLUMNS])
    return response


def _series_payload(request: Request, session_id: str) -> dict[str, Any]:
    """Shared parse + fetch for the JSON and CSV series endpoints."""
    sid = _valid_uuid(session_id)
    scope = request.query_params.get("scope", "national")
    if scope not in SCOPE_VIEWS:
        raise _BadRequest(f"unknown scope: {scope!r}")
    scope_id = _resolve_scope_id(scope, request.query_params.get("scope_id"))
    from_tick = _parse_int(request.query_params.get("from_tick"), "from_tick")
    to_tick = _parse_int(request.query_params.get("to_tick"), "to_tick")
    with _sim_cursor() as cursor:
        window = _resolve_range(cursor, sid, from_tick, to_tick)
        if window is None:
            points: list[dict[str, Any]] = []
            lo = hi = 0
        else:
            lo, hi = window
            points = fetch_series(cursor, scope, sid, scope_id, lo, hi)
    return {
        "session_id": sid,
        "scope": scope,
        "scope_id": scope_id,
        "from_tick": lo,
        "to_tick": hi,
        "points": points,
    }


@observatory_enabled_or_404
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def observatory_commits(request: Request, session_id: str) -> JsonResponse:
    """GET /api/observatory/sessions/<id>/commits/ — commit hash chain summary."""
    try:
        sid = _valid_uuid(session_id)
    except _BadRequest as exc:
        return _err(str(exc), 400)
    try:
        with _sim_cursor() as cursor:
            data = fetch_commits(cursor, sid)
    except OperationalError:
        return _err("Simulation database unavailable", 503)
    return _ok(data)


@observatory_enabled_or_404
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def observatory_hex(request: Request, session_id: str) -> JsonResponse:
    """GET /api/observatory/sessions/<id>/hex/ — reconstructed hex frame at a tick."""
    try:
        sid = _valid_uuid(session_id)
        tick = _parse_int(request.query_params.get("tick"), "tick")
        if tick is None:
            raise _BadRequest("tick is required")
        county_fips = request.query_params.get("county_fips") or None
        if county_fips is not None and not _SCOPE_ID_PATTERNS["county"].match(county_fips):
            raise _BadRequest(f"invalid county_fips {county_fips!r}")
    except _BadRequest as exc:
        return _err(str(exc), 400)
    try:
        with _sim_cursor() as cursor:
            hexes = fetch_hex_frame(cursor, sid, tick, county_fips)
    except OperationalError:
        return _err("Simulation database unavailable", 503)
    return _ok({"session_id": sid, "tick": tick, "county_fips": county_fips, "hexes": hexes})
