"""The county tension lens producer — ``county_extraction`` rendered (ADR170).

The Director-ruled principal opposition for the map's tension lens
(``reports/spatial-tension-proposal.md``, rulings 2026-07-28): per county the
poles are ``a = theta * (v + s)`` (the wage entitlement at the national norm)
and ``b = v`` (the wage actually commanded), with witness
``w = (b - a) / (a + b)``. Dividing through by the county's new value
``(v + s)`` gives the equivalent form computed here::

    phi   = v / (v + s) = 1 / (1 + e)          # the county wage share
    theta = sum(v) / sum(v + s)                # RATIO OF SUMS, never a mean
    w     = (phi - theta) / (phi + theta)      # in [-1, 1]

``w < 0`` is a net Phi-SOURCE (bled; crimson), ``w > 0`` a net Phi-RECIPIENT
(bribed; gold) — the diverging channel IS the ruled rendering, so ``w`` ships
raw and no damping factor is applied.

**Data honesty (Constitution III.11).** The extensive poles are recovered
from the TickDynamics stamps every county-bearing territory may carry:
``e = tick_exploitation_rate`` and ``s = tick_total_surplus`` give
``v = s / e``. The stamp block writes ``0.0`` for BOTH when a county's
``TensorRegistry`` was never hydrated (``graph_bridge.py``'s no-hydration
fallback), so a contribution requires ``s > 0 and e > 0`` — the poisoned
fallback surfaces as ``w=None`` (absence), never a fabricated zero. A graph
with NO data-bearing county yields ``None`` outright: no norm exists, the
whole lens is absent (the envelope's ``lens_absent_reason`` case).

Computed at PROJECTION time from the graph — the engine tick hash is
untouched; the constitutional ``BoundOpposition``/shadow registration is the
chartered engine-train W-𝔇 motion, deliberately NOT this module (ADR170).
Like :mod:`babylon.projection.fog.reach`, this module types against
:class:`~babylon.kernel.graph_protocol.GraphProtocol` only.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from babylon.kernel.graph_protocol import GraphProtocol
from babylon.models.enums import NodeType

__all__ = ["TensionCell", "county_tension_cells"]

#: Below this, ``phi + theta`` is treated as the degenerate all-bled-dry
#: limit and ``w`` collapses to ``0.0`` — the shared measure kernel's own
#: ``a + b <= 1e-9`` honest-degeneracy convention
#: (:func:`babylon.formulas.contradiction.calculate_wealth_asymmetry_gap`).
_DEGENERATE_EPS = 1e-9


class TensionCell(BaseModel):
    """One tension-lens cell: a county FIPS and its witness value.

    :param region_id: The county's 5-digit FIPS code.
    :param w: The ruled witness ``(phi - theta)/(phi + theta)`` in
        ``[-1, 1]`` — negative = Phi-source (crimson), positive =
        Phi-recipient (gold) — or ``None`` when the county carries no
        honest data this tick (absence, never a fabricated zero).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    region_id: str = Field(min_length=1)
    w: float | None = None


def territory_value_records(
    graph: GraphProtocol,
) -> tuple[tuple[str, float | None, float | None], ...]:
    """The shared extensive-recovery fold: one ``(county_fips, e, s)`` row
    per county-bearing territory node.

    ``e`` (``tick_exploitation_rate``) and ``s`` (``tick_total_surplus``)
    pass through as-present; non-numeric or missing stamps become ``None``.
    Consumers apply their own recovery/exclusion rules — this fold only
    normalizes shape (it is the single reader both the tension and value
    lenses build on, so the two lenses can never disagree about which
    territories exist).

    :param graph: Any graph-protocol implementer; read-only.
    :returns: Records in graph iteration order (callers sort).
    """
    records: list[tuple[str, float | None, float | None]] = []
    for node in graph.query_nodes(node_type=NodeType.TERRITORY.value):
        fips = node.get_attr("county_fips")
        if fips is None:
            continue
        e = node.get_attr("tick_exploitation_rate")
        s = node.get_attr("tick_total_surplus")
        e_val = float(e) if isinstance(e, (int, float)) else None
        s_val = float(s) if isinstance(s, (int, float)) else None
        records.append((fips, e_val, s_val))
    return tuple(records)


def county_tension_cells(graph: GraphProtocol) -> tuple[TensionCell, ...] | None:
    """Derive one :class:`TensionCell` per county-bearing territory group.

    Folds every ``territory`` node carrying a ``county_fips``: extensive
    ``v = s/e`` and ``s`` SUM within a county before the share is taken
    (the intensive-aggregation law — never a mean of territory shares),
    ``theta`` is the ratio of sums across all data-bearing counties, and
    every known county is emitted — data-bearing counties with their
    witness, the rest with ``w=None``.

    :param graph: Any :class:`~babylon.kernel.graph_protocol.GraphProtocol`
        implementer; read-only.
    :returns: Cells sorted by FIPS, or ``None`` when no county carries
        honest data (no norm exists — whole-lens absence).
    """
    v_by_county: dict[str, float] = {}
    new_value_by_county: dict[str, float] = {}
    all_counties: set[str] = set()

    for node in graph.query_nodes(node_type=NodeType.TERRITORY.value):
        fips = node.get_attr("county_fips")
        if fips is None:
            continue
        all_counties.add(fips)
        e = node.get_attr("tick_exploitation_rate")
        s = node.get_attr("tick_total_surplus")
        if not isinstance(e, (int, float)) or not isinstance(s, (int, float)):
            continue
        if s <= 0.0 or e <= 0.0:
            # Includes the stamp block's 0.0 no-hydration fallback — poisoned
            # data reads as absence, never as zero tension.
            continue
        v = s / e  # 0.0 at e=inf: the bled-dry limit is a PRESENT value.
        v_by_county[fips] = v_by_county.get(fips, 0.0) + v
        new_value_by_county[fips] = new_value_by_county.get(fips, 0.0) + v + s

    if not v_by_county:
        return None

    total_v = sum(v_by_county[f] for f in sorted(v_by_county))
    total_new_value = sum(new_value_by_county[f] for f in sorted(new_value_by_county))
    theta = total_v / total_new_value

    cells: list[TensionCell] = []
    for fips in sorted(all_counties):
        if fips not in v_by_county:
            cells.append(TensionCell(region_id=fips, w=None))
            continue
        phi = v_by_county[fips] / new_value_by_county[fips]
        denom = phi + theta
        w = 0.0 if denom <= _DEGENERATE_EPS else (phi - theta) / denom
        cells.append(TensionCell(region_id=fips, w=max(-1.0, min(1.0, w))))
    return tuple(cells)
