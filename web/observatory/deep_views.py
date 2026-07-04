"""Observatory deep-pane endpoints (spec-099), source-aware (live|archive).

Reuses spec-096's gating (``observatory_enabled_or_404`` → 404 when off before
auth/DB), auth, and clean-error helpers. Each endpoint opens a reader for the
chosen source and runs the reader-based deep queries. All read-only.
"""

from __future__ import annotations

from typing import Any

from django.db import DatabaseError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request

from .deep_queries import (
    read_boundary,
    read_commit_chain,
    read_conservation,
    read_national_series,
    read_tick_range,
    verify_chain,
)
from .queries import DEFAULT_MAX_TICK_SPAN
from .sources import Source, SourceReadError, open_reader, parse_source
from .views import (
    _BadRequest,
    _err,
    _ok,
    _parse_int,
    _sim_unavailable,
    _valid_uuid,
    observatory_enabled_or_404,
)

_CONSERVATION_SEVERITY = {"all", "non_ok"}


def _resolve_reader_range(
    reader: Any,
    session_id: str,
    from_tick: int | None,
    to_tick: int | None,
) -> tuple[int, int] | None:
    """Default the tick window to the committed range and cap the span."""
    if from_tick is None or to_tick is None:
        rng = read_tick_range(reader, session_id)
        if rng is None:
            return None
        from_tick = rng[0] if from_tick is None else from_tick
        to_tick = rng[1] if to_tick is None else to_tick
    if from_tick > to_tick:
        raise _BadRequest("from_tick must be <= to_tick")
    return from_tick, min(to_tick, from_tick + DEFAULT_MAX_TICK_SPAN)


def _parse_common(request: Request, session_id: str) -> tuple[str, Source, int | None, int | None]:
    """Parse the session id, source, and optional tick window (raises _BadRequest)."""
    sid = _valid_uuid(session_id)
    try:
        source = parse_source(request.query_params.get("source"))
    except ValueError as exc:
        raise _BadRequest(str(exc)) from exc
    from_tick = _parse_int(request.query_params.get("from_tick"), "from_tick")
    to_tick = _parse_int(request.query_params.get("to_tick"), "to_tick")
    return sid, source, from_tick, to_tick


@observatory_enabled_or_404
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def observatory_verify(request: Request, session_id: str) -> Any:
    """GET /api/observatory/sessions/<id>/verify/ — commit-chain integrity."""
    try:
        sid, source, _f, _t = _parse_common(request, session_id)
    except _BadRequest as exc:
        return _err(str(exc), 400)
    try:
        with open_reader(source, sid) as reader:
            rng = read_tick_range(reader, sid)
            chain = [] if rng is None else read_commit_chain(reader, sid, rng[0], rng[1])
    except DatabaseError:
        return _sim_unavailable()
    except SourceReadError:
        return _err("Archive read failed", 503)
    verdict = verify_chain(chain)
    verdict["session_id"] = sid
    verdict["source"] = source.value
    return _ok(verdict)


@observatory_enabled_or_404
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def observatory_boundary(request: Request, session_id: str) -> Any:
    """GET /api/observatory/sessions/<id>/boundary/ — cross-boundary flows."""
    try:
        sid, source, from_tick, to_tick = _parse_common(request, session_id)
    except _BadRequest as exc:
        return _err(str(exc), 400)
    try:
        with open_reader(source, sid) as reader:
            window = _resolve_reader_range(reader, sid, from_tick, to_tick)
            if window is None:
                data: dict[str, Any] = {"by_flow_type": [], "rows": []}
                lo = hi = 0
            else:
                lo, hi = window
                data = read_boundary(reader, sid, lo, hi)
    except _BadRequest as exc:
        return _err(str(exc), 400)
    except DatabaseError:
        return _sim_unavailable()
    except SourceReadError:
        return _err("Archive read failed", 503)
    return _ok({"session_id": sid, "source": source.value, "from_tick": lo, "to_tick": hi, **data})


@observatory_enabled_or_404
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def observatory_conservation(request: Request, session_id: str) -> Any:
    """GET /api/observatory/sessions/<id>/conservation/ — audit-log browser."""
    try:
        sid, source, from_tick, to_tick = _parse_common(request, session_id)
        severity = request.query_params.get("severity", "all")
        if severity not in _CONSERVATION_SEVERITY:
            raise _BadRequest(f"severity must be one of {sorted(_CONSERVATION_SEVERITY)}")
    except _BadRequest as exc:
        return _err(str(exc), 400)
    try:
        with open_reader(source, sid) as reader:
            window = _resolve_reader_range(reader, sid, from_tick, to_tick)
            if window is None:
                rows: list[dict[str, Any]] = []
                lo = hi = 0
            else:
                lo, hi = window
                rows = read_conservation(reader, sid, lo, hi, non_ok_only=severity == "non_ok")
    except _BadRequest as exc:
        return _err(str(exc), 400)
    except DatabaseError:
        return _sim_unavailable()
    except SourceReadError:
        return _err("Archive read failed", 503)
    return _ok(
        {"session_id": sid, "source": source.value, "from_tick": lo, "to_tick": hi, "rows": rows}
    )


@observatory_enabled_or_404
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def observatory_diff(request: Request) -> Any:
    """GET /api/observatory/diff/?a=&b=&source= — two-session comparison."""
    try:
        sid_a = _valid_uuid(request.query_params.get("a", ""))
        sid_b = _valid_uuid(request.query_params.get("b", ""))
        try:
            source = parse_source(request.query_params.get("source"))
        except ValueError as exc:
            raise _BadRequest(str(exc)) from exc
    except _BadRequest as exc:
        return _err(str(exc), 400)
    try:
        with open_reader(source, sid_a) as reader_a:
            series_a = _full_national(reader_a, sid_a)
            chain_a = _chain_summary(reader_a, sid_a)
        with open_reader(source, sid_b) as reader_b:
            series_b = _full_national(reader_b, sid_b)
            chain_b = _chain_summary(reader_b, sid_b)
    except DatabaseError:
        return _sim_unavailable()
    except SourceReadError:
        return _err("Archive read failed", 503)
    return _ok(
        {
            "a": sid_a,
            "b": sid_b,
            "source": source.value,
            "national": _align_series(series_a, series_b),
            "commits": {
                "a": chain_a,
                "b": chain_b,
                "tick_count_delta": chain_a["tick_count"] - chain_b["tick_count"],
                "range_delta": (chain_a["max_tick"] or 0) - (chain_b["max_tick"] or 0),
            },
        }
    )


def _full_national(reader: Any, session_id: str) -> list[dict[str, Any]]:
    rng = read_tick_range(reader, session_id)
    if rng is None:
        return []
    return read_national_series(reader, session_id, rng[0], rng[1])


def _chain_summary(reader: Any, session_id: str) -> dict[str, Any]:
    rng = read_tick_range(reader, session_id)
    if rng is None:
        return {"min_tick": None, "max_tick": None, "tick_count": 0}
    chain = read_commit_chain(reader, session_id, rng[0], rng[1])
    return {"min_tick": rng[0], "max_tick": rng[1], "tick_count": len(chain)}


def _align_series(
    series_a: list[dict[str, Any]], series_b: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Outer-join two national series by tick with a per-tick v_sum delta."""
    a_by_tick = {int(p["tick"]): float(p["v_sum"]) for p in series_a}
    b_by_tick = {int(p["tick"]): float(p["v_sum"]) for p in series_b}
    return [
        {
            "tick": tick,
            "a_v_sum": a_by_tick.get(tick),
            "b_v_sum": b_by_tick.get(tick),
            "delta": a_by_tick.get(tick, 0.0) - b_by_tick.get(tick, 0.0),
        }
        for tick in sorted(set(a_by_tick) | set(b_by_tick))
    ]
