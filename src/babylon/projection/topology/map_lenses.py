"""The M5 map's value-lens and state-tier helpers (contract §1, graph-first).

Built entirely on :func:`~babylon.projection.topology.tension.
territory_value_records` — the single shared reader — so the value and
tension lenses can never disagree about which territories exist. The state
tier groups counties by ``county_fips[:2]`` and aggregates RATIO-OF-SUMS
over the recovered extensives (``v = s/e``), never a mean of county rates
(the intensive-aggregation law). Absence discipline is the tension
module's: the stamp block's ``0.0`` no-hydration fallback and missing
stamps surface as ``None`` cells; a tier with no data at all is ``None``
outright (Constitution III.11).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from babylon.kernel.graph_protocol import GraphProtocol
from babylon.projection.fog.county_status import county_fog_status
from babylon.projection.fog.ledger import IntelLedger, VisibilityTier
from babylon.projection.topology.tension import TensionCell, territory_value_records

__all__ = [
    "ValueCell",
    "county_value_cells",
    "state_fog_status",
    "state_tension_cells",
    "state_value_cells",
]

_TIER_RANK: dict[VisibilityTier, int] = {"exact": 2, "approximate": 1, "unknown": 0}


class ValueCell(BaseModel):
    """One value-lens cell: a region id and its exploitation rate.

    :param region_id: County FIPS (county tier) or 2-digit state FIPS
        prefix (state tier).
    :param value: ``s/v`` for the region — ``float("inf")`` is a PRESENT
        value at ``v == 0`` (the ledger lens's own convention) — or
        ``None`` for honest absence.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    region_id: str = Field(min_length=1)
    value: float | None = None


def _grouped(
    graph: GraphProtocol, key_len: int
) -> tuple[dict[str, list[tuple[float | None, float | None]]], set[str]]:
    """Records grouped by ``fips[:key_len]`` plus the full region-key set."""
    groups: dict[str, list[tuple[float | None, float | None]]] = {}
    regions: set[str] = set()
    for fips, e, s in territory_value_records(graph):
        key = fips[:key_len]
        regions.add(key)
        groups.setdefault(key, []).append((e, s))
    return groups, regions


def _recovered_sums(
    members: list[tuple[float | None, float | None]],
) -> tuple[float, float] | None:
    """``(v_sum, s_sum)`` over the recoverable members (``s > 0 and e > 0``,
    the poisoned-fallback exclusion), or ``None`` when nothing recovers."""
    v_sum = 0.0
    s_sum = 0.0
    any_recovered = False
    for e, s in members:
        if e is None or s is None or s <= 0.0 or e <= 0.0:
            continue
        v_sum += s / e
        s_sum += s
        any_recovered = True
    return (v_sum, s_sum) if any_recovered else None


def _value_cells(graph: GraphProtocol, key_len: int) -> tuple[ValueCell, ...] | None:
    groups, regions = _grouped(graph, key_len)
    if not regions:
        return None
    cells: list[ValueCell] = []
    for key in sorted(regions):
        members = groups[key]
        if len(members) == 1:
            # A group of one needs no recovery: its own rate is honest
            # even when ``s`` is absent.
            e, _s = members[0]
            value = e if e is not None and e > 0.0 else None
        else:
            sums = _recovered_sums(members)
            value = None
            if sums is not None:
                v_sum, s_sum = sums
                value = float("inf") if v_sum == 0.0 else s_sum / v_sum
        cells.append(ValueCell(region_id=key, value=value))
    return tuple(cells)


def county_value_cells(graph: GraphProtocol) -> tuple[ValueCell, ...] | None:
    """The value lens at county grain: one cell per ``county_fips``.

    :param graph: Any graph-protocol implementer; read-only.
    :returns: Cells sorted by FIPS, or ``None`` when the graph carries no
        county-bearing territories at all.
    """
    return _value_cells(graph, key_len=5)


def state_value_cells(graph: GraphProtocol) -> tuple[ValueCell, ...] | None:
    """The value lens at state grain: ratio-of-sums per ``fips[:2]``."""
    return _value_cells(graph, key_len=2)


def state_tension_cells(graph: GraphProtocol) -> tuple[TensionCell, ...] | None:
    """The tension lens at state grain: per-state ``phi`` against the SAME
    national ``theta`` the county tier uses (ADR170 — the norm never
    changes with the zoom level).

    :param graph: Any graph-protocol implementer; read-only.
    :returns: Cells sorted by state prefix, or ``None`` when no county
        bears data (no norm exists).
    """
    groups, regions = _grouped(graph, key_len=2)
    if not regions:
        return None
    recovered = {key: _recovered_sums(members) for key, members in groups.items()}
    total_v = sum(v for sums in recovered.values() if sums is not None for v in (sums[0],))
    total_new = sum(sums[0] + sums[1] for sums in recovered.values() if sums is not None)
    if total_new <= 0.0:
        return None
    theta = total_v / total_new
    cells: list[TensionCell] = []
    for key in sorted(regions):
        sums = recovered[key]
        if sums is None:
            cells.append(TensionCell(region_id=key, w=None))
            continue
        v_sum, s_sum = sums
        phi = v_sum / (v_sum + s_sum)
        denom = phi + theta
        w = 0.0 if denom <= 1e-9 else (phi - theta) / denom
        cells.append(TensionCell(region_id=key, w=max(-1.0, min(1.0, w))))
    return tuple(cells)


def state_fog_status(
    graph: GraphProtocol,
    player_org_id: str | None,
    ledger: IntelLedger,
    tick: int,
    *,
    radius: int,
    staleness_ticks: int,
    unknown_ticks: int,
) -> dict[str, VisibilityTier]:
    """The fog lens at state grain: most-informed-wins over the state's
    counties (one county in reach lights its state ``exact`` — the same
    fold rule the county producer applies across a county's territories).
    """
    county = county_fog_status(
        graph,
        player_org_id,
        ledger,
        tick,
        radius=radius,
        staleness_ticks=staleness_ticks,
        unknown_ticks=unknown_ticks,
    )
    status: dict[str, VisibilityTier] = {}
    for fips, tier in county.items():
        key = fips[:2]
        if key not in status or _TIER_RANK[tier] > _TIER_RANK[status[key]]:
            status[key] = tier
    return status
