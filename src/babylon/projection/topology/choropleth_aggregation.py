"""Per-tier choropleth cell derivation from persistence row-models (WO-33).

Split out of :mod:`babylon.projection.topology.choropleth` deliberately: this
module imports :mod:`babylon.persistence` row-models
(:class:`~babylon.persistence.hex_state.DynamicHexState`,
:class:`~babylon.persistence.postgres_aggregation.CountyValueAggregate`), so
it must never be imported from :mod:`babylon.tui` — the
``"tui client reads projections only"`` import-linter contract forbids
``babylon.tui`` from importing ``babylon.persistence`` even transitively.
Callers that need the choropleth's tier-selection logic or the
:class:`~babylon.projection.topology.choropleth.ChoroplethCell` shape without
this persistence dependency should import
:mod:`babylon.projection.topology.choropleth` instead; only projection- or
engine-adjacent callers (never the TUI directly) call the functions here.

**One producer per tier, honestly:**

.. list-table:: Tier-producer rulings
   :header-rows: 1

   * - Tier
     - Producer
   * - ``county``
     - :class:`~babylon.persistence.postgres_aggregation.CountyValueAggregate`
       rows (the registered ``v_county_value_aggregate`` view, II.11) —
       already-summed, no re-derivation needed.
   * - ``state``
     - :class:`~babylon.persistence.hex_state.DynamicHexState` rows (the
       registered ``v_hex_state_asof`` view) grouped by ``state_fips``,
       summed here. ``v_hex_state_asof`` is **SPARSE** (spec-089 delta
       persistence): the view's own ``LEAD()``-window fill-forward guarantees
       exactly one row per ``(session, tick, hex)`` even for a hex not
       rewritten that tick (the view additionally projects the diagnostic
       ``written_at_tick`` column the currently-registered
       :class:`~babylon.persistence.hex_state.DynamicHexState` row-model does
       not yet surface as a field — a pre-existing registry gap, not this
       WO's to close). This module never re-derives fill-forward itself and
       never accepts a raw multi-tick slice
       (:func:`state_choropleth_cells_from_hex_rows` raises if the rows it is
       handed span more than one ``tick`` — a caller that mixed ticks almost
       certainly meant ``WHERE tick = N`` on the raw ``dynamic_hex_state``
       table, the exact anti-pattern the as-of view exists to prevent).
   * - ``ea`` (BEA Economic Area)
     - **No producer exists yet.** See :func:`ea_choropleth_cells`.

The metric colouring every cell — the rate of exploitation ``s/v`` (Marx's
``e = s/v``; the same ratio
:attr:`~babylon.domain.economics.tensor.ValueTensor4x3.exploitation_rate`
computes, reused here rather than inventing a new metric) — is an
*intensive* quantity; the weather-grammar law the map room must obey
(``DESIGN_BIBLE`` §11, law 1: "extensive renders as stuff, intensive renders
as color") makes a rate the correct choropleth fill, not a raw
``c``/``v``/``s``/``k`` sum.

Absence discipline (Constitution III.11): :func:`ea_choropleth_cells` returns
``None`` — honest absence, never a fabricated aggregate — because no
:class:`~babylon.projection.registry.DeclaredView` reads BEA Economic Areas.
"""

from __future__ import annotations

from collections.abc import Sequence

from babylon.persistence.hex_state import DynamicHexState
from babylon.persistence.postgres_aggregation import CountyValueAggregate
from babylon.projection.topology.choropleth import ChoroplethCell

__all__ = [
    "county_choropleth_cells",
    "ea_choropleth_cells",
    "state_choropleth_cells_from_hex_rows",
]


def _exploitation_rate(*, v_sum: float, s_sum: float) -> float:
    """``s/v``, or ``float("inf")`` when ``v_sum`` is zero.

    Mirrors :attr:`~babylon.domain.economics.tensor.ValueTensor4x3.exploitation_rate`'s
    own zero-guard exactly — the same present-but-degenerate convention, not
    a different one invented for the choropleth.

    :param v_sum: Summed variable capital.
    :param s_sum: Summed surplus value.
    :returns: The exploitation rate, or ``inf`` when ``v_sum == 0.0``.
    """
    if v_sum == 0.0:
        return float("inf")
    return s_sum / v_sum


def county_choropleth_cells(rows: Sequence[CountyValueAggregate]) -> tuple[ChoroplethCell, ...]:
    """County-tier choropleth cells from already-summed aggregate rows.

    Reads :class:`~babylon.persistence.postgres_aggregation.CountyValueAggregate`
    (the registered ``v_county_value_aggregate`` view) directly — no
    re-aggregation from hex rows, since the view already did the sum
    (Constitution II.11: never re-derive what a declared view already
    computes).

    :param rows: County aggregate rows, any order (the FIPS ordering below is
        this function's own determinism guarantee, not a precondition on
        ``rows``).
    :returns: One cell per row, sorted by ``county_fips`` ascending — matching
        the registry's declared ``order_by`` for ``v_county_value_aggregate``
        (Constitution III.13: every projection ends in an explicit order).
    """
    return tuple(
        ChoroplethCell(
            region_id=row.county_fips,
            exploitation_rate=_exploitation_rate(v_sum=row.v_sum, s_sum=row.s_sum),
        )
        for row in sorted(rows, key=lambda row: row.county_fips)
    )


def state_choropleth_cells_from_hex_rows(
    rows: Sequence[DynamicHexState],
) -> tuple[ChoroplethCell, ...]:
    """State-tier choropleth cells, summed from hex-level as-of rows.

    :param rows: Hex-level rows read from ``v_hex_state_asof`` — the SPARSE
        as-of view (spec-089), never a raw ``dynamic_hex_state`` slice
        filtered by ``WHERE tick = N``. Every row must carry the *same*
        ``tick`` (one as-of read) — the sole guard this function can enforce
        against the raw-table anti-pattern; the view already resolved
        fill-forward before these rows ever reach this function, which never
        re-derives it.
    :returns: One cell per distinct ``state_fips``, sorted ascending —
        matching ``v_state_value_aggregate``'s declared ``order_by``.
    :raises ValueError: if ``rows`` spans more than one ``tick`` — a mixed-tick
        slice cannot be a single as-of read and almost always means the
        caller queried the raw table instead of the view.
    """
    if not rows:
        return ()
    ticks = {row.tick for row in rows}
    if len(ticks) > 1:
        msg = (
            "state_choropleth_cells_from_hex_rows received rows spanning "
            f"multiple ticks {sorted(ticks)} — pass exactly one as-of read "
            "(v_hex_state_asof at a single tick), never a raw multi-tick slice"
        )
        raise ValueError(msg)

    totals: dict[str, list[float]] = {}
    for row in rows:
        bucket = totals.setdefault(row.state_fips, [0.0, 0.0])
        bucket[0] += row.v
        bucket[1] += row.s

    return tuple(
        ChoroplethCell(
            region_id=state_fips,
            exploitation_rate=_exploitation_rate(v_sum=v_sum, s_sum=s_sum),
        )
        for state_fips, (v_sum, s_sum) in sorted(totals.items())
    )


def ea_choropleth_cells() -> tuple[ChoroplethCell, ...] | None:
    """Honest absence for the EA (BEA Economic Area) tier — no producer exists.

    No :class:`~babylon.projection.registry.DeclaredView` reads BEA Economic
    Areas. The committed reference bridge
    (``src/babylon/data/reference/bridge_county_bea_ea.csv`` +
    ``dim_bea_economic_area.csv``) keys counties by the numeric
    ``dim_county.county_id`` surrogate, not ``county_fips`` — resolving it
    to a county-fips-keyed rung requires a live reference-DB join
    (:class:`~babylon.reference.schema.DimCounty`), which no Wave-1
    fixture-first WO may perform (CLAUDE.md machine-safety + fixture-first
    discipline; contrast the DB-free CSV-only :func:`~babylon.domain.
    dialectics.instances.levels.cz_adjunction`, which the bridge's own
    ``county_id`` keying rules out here).

    :func:`~babylon.projection.topology.choropleth.select_render_tier` still
    answers ``"glyph"`` for ``"ea"`` — the *renderer* exists — but the data
    does not: an honest ``None`` (Constitution III.11), never a fabricated
    aggregate. Flagged here for a follow-up WO to close (register an
    EA-keyed ``DeclaredView`` bridging through ``DimCounty``, then wire this
    function), mirroring the WO-21 dead-producer disposition (ship the
    honest gap, don't paper over it).

    :returns: ``None``, always — the ``tuple[ChoroplethCell, ...] | None``
        signature matches the shape a real future producer would have, so
        closing the gap later needs no caller-side change.
    """
    return None
