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
import logging
import re
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

from django.conf import settings
from django.db import DatabaseError, connections
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseBase, JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request

from .deep_queries import read_commit_chain, read_national_series, read_tick_range
from .queries import (
    DEFAULT_HEX_LIMIT,
    DEFAULT_MAX_TICK_SPAN,
    MAX_HEX_LIMIT,
    SCOPE_VIEWS,
    fetch_commits,
    fetch_hex_frame,
    fetch_series,
    fetch_sessions,
    fetch_tick_range,
)
from .sources import (
    SIM_ALIAS,
    Source,
    SourceReadError,
    list_archive_session_ids,
    open_reader,
    parse_source,
)

logger = logging.getLogger(__name__)

#: Postgres INT4 bounds — tick columns are INT4; a value outside this range
#: raises DataError, so tick params are rejected as 400 before reaching the DB.
_INT4_MIN = -(2**31)
_INT4_MAX = 2**31 - 1

_SCOPE_ID_PATTERNS = {"state": re.compile(r"^\d{2}$"), "county": re.compile(r"^\d{5}$")}
_SERIES_COLUMNS = ["tick", "c_sum", "v_sum", "s_sum", "k_sum", "biocapacity_sum", "hex_count"]


# --------------------------------------------------------------------------- #
# Envelope + gating helpers
# --------------------------------------------------------------------------- #


def _ok(data: Any, http_status: int = 200) -> JsonResponse:
    return JsonResponse({"status": "ok", "data": data}, status=http_status)


def _err(message: str, http_status: int) -> JsonResponse:
    return JsonResponse({"status": "error", "message": message}, status=http_status)


def _sim_unavailable() -> JsonResponse:
    """Log the DB error server-side (with traceback) and return a clean 503.

    The client-facing body carries NO internals — the traceback (which may
    reference SQL/relation names) stays in the server log only.
    """
    logger.exception("Observatory sim-DB query failed")
    return _err("Simulation database unavailable", 503)


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
        value = int(raw)
    except ValueError as exc:
        raise _BadRequest(f"{name} must be an integer") from exc
    if not _INT4_MIN <= value <= _INT4_MAX:
        raise _BadRequest(f"{name} out of range")
    return value


def _parse_limit(raw: str | None) -> int:
    """Parse the hex page-size limit, defaulting and hard-capping it."""
    if raw is None or raw == "":
        return DEFAULT_HEX_LIMIT
    try:
        value = int(raw)
    except ValueError as exc:
        raise _BadRequest("limit must be an integer") from exc
    if value < 1:
        raise _BadRequest("limit must be >= 1")
    return min(value, MAX_HEX_LIMIT)


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


def _source_or_400(request: Request) -> Source:
    try:
        return parse_source(request.query_params.get("source"))
    except ValueError as exc:
        raise _BadRequest(str(exc)) from exc


def _archive_sessions() -> list[dict[str, Any]]:
    """Session summaries reconstructed from archived Parquet (per-session dir)."""
    out: list[dict[str, Any]] = []
    for sid in list_archive_session_ids():
        with open_reader(Source.ARCHIVE, sid) as reader:
            rng = read_tick_range(reader, sid)
            if rng is None:
                continue
            chain = read_commit_chain(reader, sid, rng[0], rng[1])
        out.append(
            {
                "session_id": sid,
                "min_tick": rng[0],
                "max_tick": rng[1],
                "tick_count": len(chain),
                "checkpoint_count": sum(1 for c in chain if c["is_checkpoint"]),
                "latest_hash": chain[-1]["determinism_hash"] if chain else None,
                "scenario": None,
                "status": None,
                "created_at": None,
            }
        )
    return out


def _window(
    rng: tuple[int, int] | None, from_tick: int | None, to_tick: int | None
) -> tuple[int, int] | None:
    """Resolve a bounded, span-capped tick window from a committed range."""
    if rng is None:
        return None
    lo = rng[0] if from_tick is None else from_tick
    hi = rng[1] if to_tick is None else to_tick
    if lo > hi:
        raise _BadRequest("from_tick must be <= to_tick")
    return lo, min(hi, lo + DEFAULT_MAX_TICK_SPAN)


def _archive_tick_range(sid: str) -> dict[str, Any] | None:
    with open_reader(Source.ARCHIVE, sid) as reader:
        rng = read_tick_range(reader, sid)
        if rng is None:
            return None
        chain = read_commit_chain(reader, sid, rng[0], rng[1])
    return {
        "session_id": sid,
        "min_tick": rng[0],
        "max_tick": rng[1],
        "tick_count": len(chain),
        "checkpoint_ticks": [c["tick"] for c in chain if c["is_checkpoint"]],
    }


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
    """GET /api/observatory/sessions/?source= — sessions with >=1 committed tick."""
    try:
        source = _source_or_400(request)
    except _BadRequest as exc:
        return _err(str(exc), 400)
    try:
        if source is Source.ARCHIVE:
            data = _archive_sessions()
        else:
            with _sim_cursor() as cursor:
                data = fetch_sessions(cursor)
    except DatabaseError:
        return _sim_unavailable()
    except SourceReadError:
        return _err("Archive read failed", 503)
    return _ok(data)


@observatory_enabled_or_404
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def observatory_ticks(request: Request, session_id: str) -> JsonResponse:
    """GET /api/observatory/sessions/<id>/ticks/?source= — range + checkpoints."""
    try:
        sid = _valid_uuid(session_id)
        source = _source_or_400(request)
    except _BadRequest as exc:
        return _err(str(exc), 400)
    try:
        if source is Source.ARCHIVE:
            data = _archive_tick_range(sid)
        else:
            with _sim_cursor() as cursor:
                data = fetch_tick_range(cursor, sid)
    except DatabaseError:
        return _sim_unavailable()
    except SourceReadError:
        return _err("Archive read failed", 503)
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
    except DatabaseError:
        return _sim_unavailable()
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
    except DatabaseError:
        return _sim_unavailable()
    filename = f"{payload['session_id']}_{payload['scope']}_{payload['scope_id']}.csv"
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    writer.writerow(_SERIES_COLUMNS)
    for point in payload["points"]:
        writer.writerow([point[column] for column in _SERIES_COLUMNS])
    return response


def _series_payload(request: Request, session_id: str) -> dict[str, Any]:
    """Shared parse + fetch for the JSON and CSV series endpoints (source-aware).

    Archive source supports the national scope only (archives carry no
    ``hex_spatial_map``, so state/county grouping is unavailable) — a documented
    empty result for those scopes.
    """
    sid = _valid_uuid(session_id)
    source = _source_or_400(request)
    scope = request.query_params.get("scope", "national")
    if scope not in SCOPE_VIEWS:
        raise _BadRequest(f"unknown scope: {scope!r}")
    scope_id = _resolve_scope_id(scope, request.query_params.get("scope_id"))
    from_tick = _parse_int(request.query_params.get("from_tick"), "from_tick")
    to_tick = _parse_int(request.query_params.get("to_tick"), "to_tick")
    points: list[dict[str, Any]]
    if source is Source.ARCHIVE:
        with open_reader(Source.ARCHIVE, sid) as reader:
            window = _window(read_tick_range(reader, sid), from_tick, to_tick)
            if window is None or scope != "national":
                points, lo, hi = [], (window[0] if window else 0), (window[1] if window else 0)
            else:
                lo, hi = window
                points = read_national_series(reader, sid, lo, hi)
    else:
        with _sim_cursor() as cursor:
            window = _resolve_range(cursor, sid, from_tick, to_tick)
            if window is None:
                points, lo, hi = [], 0, 0
            else:
                lo, hi = window
                points = fetch_series(cursor, scope, sid, scope_id, lo, hi)
    return {
        "session_id": sid,
        "scope": scope,
        "scope_id": scope_id,
        "source": source.value,
        "from_tick": lo,
        "to_tick": hi,
        "points": points,
    }


@observatory_enabled_or_404
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def observatory_commits(request: Request, session_id: str) -> JsonResponse:
    """GET /api/observatory/sessions/<id>/commits/ — commit hash chain summary.

    Bounded like ``series/``: optional ``from_tick``/``to_tick`` default to the
    session's committed range and the span is capped, so a national
    multi-hundred-tick run cannot return the whole chain unbounded per call.
    """
    try:
        sid = _valid_uuid(session_id)
        source = _source_or_400(request)
        from_tick = _parse_int(request.query_params.get("from_tick"), "from_tick")
        to_tick = _parse_int(request.query_params.get("to_tick"), "to_tick")
    except _BadRequest as exc:
        return _err(str(exc), 400)
    try:
        if source is Source.ARCHIVE:
            with open_reader(Source.ARCHIVE, sid) as reader:
                window = _window(read_tick_range(reader, sid), from_tick, to_tick)
                data = (
                    []
                    if window is None
                    else [
                        {**c, "created_at_utc": None}
                        for c in read_commit_chain(reader, sid, window[0], window[1])
                    ]
                )
        else:
            with _sim_cursor() as cursor:
                window = _resolve_range(cursor, sid, from_tick, to_tick)
                data = [] if window is None else fetch_commits(cursor, sid, window[0], window[1])
    except _BadRequest as exc:
        return _err(str(exc), 400)
    except DatabaseError:
        return _sim_unavailable()
    except SourceReadError:
        return _err("Archive read failed", 503)
    return _ok(data)


@observatory_enabled_or_404
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def observatory_hex(request: Request, session_id: str) -> JsonResponse:
    """GET /api/observatory/sessions/<id>/hex/ — bounded reconstructed hex frame.

    Bounded by ``limit`` (default/cap :data:`DEFAULT_HEX_LIMIT` /
    :data:`MAX_HEX_LIMIT`) and paged forward by the ``after_h3`` cursor. The
    response signals ``truncated`` + ``next_h3`` so a national res-7 frame is
    fetched page-by-page instead of buffered whole.
    """
    try:
        sid = _valid_uuid(session_id)
        tick = _parse_int(request.query_params.get("tick"), "tick")
        if tick is None:
            raise _BadRequest("tick is required")
        county_fips = request.query_params.get("county_fips") or None
        if county_fips is not None and not _SCOPE_ID_PATTERNS["county"].match(county_fips):
            raise _BadRequest(f"invalid county_fips {county_fips!r}")
        limit = _parse_limit(request.query_params.get("limit"))
        after_h3 = request.query_params.get("after_h3") or None
    except _BadRequest as exc:
        return _err(str(exc), 400)
    try:
        with _sim_cursor() as cursor:
            hexes, truncated, next_h3 = fetch_hex_frame(
                cursor, sid, tick, county_fips, limit=limit, after_h3=after_h3
            )
    except DatabaseError:
        return _sim_unavailable()
    return _ok(
        {
            "session_id": sid,
            "tick": tick,
            "county_fips": county_fips,
            "limit": limit,
            "hexes": hexes,
            "truncated": truncated,
            "next_h3": next_h3,
        }
    )
