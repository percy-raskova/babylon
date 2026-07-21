"""Contract tests for :mod:`babylon.projection.topology.choropleth` +
:mod:`babylon.projection.topology.choropleth_aggregation` (WO-33).

Fixture-fed, hand-constructed rows shaped exactly like the registered
:class:`~babylon.persistence.postgres_aggregation.CountyValueAggregate` and
:class:`~babylon.persistence.hex_state.DynamicHexState` Pydantic row-models —
no database, no engine. Unlike ``project_county``'s fixture (harvested from a
live ``single_county`` scenario run), the ``county``/``state`` aggregate views
this module reads are themselves Postgres ``SUM`` views over
``dynamic_hex_state`` with no in-process, DB-free engine equivalent
(``SubstrateSystem`` hex persistence only happens through the full headless
runner + a live Postgres connection) — so there is no harvester to mirror
here; these rows are the honest fixture shape instead.

The two source modules are split deliberately (see
``choropleth_aggregation``'s module docstring): ``choropleth`` is
persistence-free (importable from ``babylon.tui``), ``choropleth_aggregation``
imports the persistence row-models above and must never be imported from
``babylon.tui`` (the ``import-linter`` "tui client reads projections only"
contract). This test file, being test-only code outside both packages'
layering scope, is free to exercise both.
"""

from __future__ import annotations

from uuid import UUID

import pytest
from pydantic import ValidationError

from babylon.persistence.hex_state import DynamicHexState
from babylon.persistence.postgres_aggregation import CountyValueAggregate
from babylon.projection.topology.choropleth import ChoroplethCell, select_render_tier
from babylon.projection.topology.choropleth_aggregation import (
    county_choropleth_cells,
    ea_choropleth_cells,
    state_choropleth_cells_from_hex_rows,
)

_SESSION = UUID("00000000-0000-0000-0000-000000000001")


def _county_row(fips: str, *, v_sum: float, s_sum: float) -> CountyValueAggregate:
    return CountyValueAggregate(
        session_id=_SESSION,
        tick=847,
        county_fips=fips,
        c_sum=100.0,
        v_sum=v_sum,
        s_sum=s_sum,
        k_sum=50.0,
        biocapacity_sum=10.0,
        hex_count=3,
    )


def _hex_row(
    h3_index: str,
    *,
    state_fips: str,
    v: float,
    s: float,
    tick: int = 847,
) -> DynamicHexState:
    """Build a hex row shaped like one ``v_hex_state_asof`` result row.

    No ``written_at_tick`` parameter: the currently-registered
    :class:`~babylon.persistence.hex_state.DynamicHexState` row-model does not
    declare that field (a pre-existing registry gap — the view projects it,
    the model doesn't surface it — out of WO-33's scope to close). The
    fill-forward semantics ``written_at_tick`` would otherwise diagnose are
    exercised structurally instead: two DIFFERENT hexes sharing one ``tick``
    (see ``TestStateChoroplethCellsFromHexRows``), which is exactly the shape
    an as-of read of a sparse table produces regardless of which hex was
    genuinely rewritten that tick.
    """
    return DynamicHexState(
        session_id=_SESSION,
        tick=tick,
        h3_index=h3_index,
        county_fips=f"{state_fips}163",
        state_fips=state_fips,
        region_id="detroit-metro",
        c=1.0,
        v=v,
        s=s,
        k=1.0,
        biocapacity_stock=1.0,
        energy_stock=1.0,
        raw_material_stock=1.0,
        internet_access_pct=0.5,
        surveillance_coupling=0.1,
    )


class TestRenderTierSelection:
    """The charter's P0 batch ruling: cell-art at EA/state, flag-gated at county."""

    def test_ea_tier_is_always_glyph(self) -> None:
        assert select_render_tier("ea", requested="glyph") == "glyph"
        assert select_render_tier("ea", requested="pixel") == "glyph"

    def test_state_tier_is_always_glyph(self) -> None:
        assert select_render_tier("state", requested="glyph") == "glyph"
        assert select_render_tier("state", requested="pixel") == "glyph"

    def test_county_tier_honors_the_request(self) -> None:
        assert select_render_tier("county", requested="glyph") == "glyph"
        assert select_render_tier("county", requested="pixel") == "pixel"

    def test_county_tier_defaults_off_when_caller_requests_glyph(self) -> None:
        """ "Default OFF -> cell-art fallback" means an explicit glyph request
        never upgrades to raster, even at the one tier that can."""
        assert select_render_tier("county", requested="glyph") == "glyph"


class TestCountyChoroplethCells:
    """County-tier cells reuse the already-summed v_county_value_aggregate."""

    def test_projects_the_exploitation_rate(self) -> None:
        rows = [_county_row("26163", v_sum=200.0, s_sum=100.0)]
        cells = county_choropleth_cells(rows)

        assert cells == (ChoroplethCell(region_id="26163", exploitation_rate=0.5),)

    def test_zero_variable_capital_is_present_infinity_not_absence(self) -> None:
        """v_sum == 0 is a present, degenerate value (mirrors
        ValueTensor4x3.exploitation_rate) — never collapsed to None."""
        rows = [_county_row("26163", v_sum=0.0, s_sum=0.0)]
        cells = county_choropleth_cells(rows)

        assert cells[0].exploitation_rate == float("inf")

    def test_sorted_by_county_fips_regardless_of_input_order(self) -> None:
        rows = [
            _county_row("26999", v_sum=10.0, s_sum=5.0),
            _county_row("26001", v_sum=10.0, s_sum=5.0),
            _county_row("26163", v_sum=10.0, s_sum=5.0),
        ]
        cells = county_choropleth_cells(rows)

        assert [cell.region_id for cell in cells] == ["26001", "26163", "26999"]

    def test_empty_rows_yield_empty_cells(self) -> None:
        assert county_choropleth_cells([]) == ()


class TestStateChoroplethCellsFromHexRows:
    """State-tier cells sum hex-level v_hex_state_asof rows by state_fips."""

    def test_sums_v_and_s_across_hexes_in_the_same_state(self) -> None:
        rows = [
            _hex_row("8a2a1072b59ffff", state_fips="26", v=100.0, s=50.0),
            _hex_row("8a2a1072b5bffff", state_fips="26", v=100.0, s=30.0),
        ]
        cells = state_choropleth_cells_from_hex_rows(rows)

        assert cells == (ChoroplethCell(region_id="26", exploitation_rate=0.4),)

    def test_trusts_the_as_of_read_as_given_never_re_derives_fill_forward(self) -> None:
        """v_hex_state_asof already resolved fill-forward before these rows
        exist — one row per hex at the requested tick, regardless of whether
        that hex was genuinely rewritten this tick or is carrying forward an
        earlier write. This function has no way to distinguish the two (its
        signature takes no ``written_at_tick``-shaped input at all) and must
        not need to: it just sums whatever the as-of read handed it."""
        rows = [
            _hex_row("8a2a1072b59ffff", state_fips="26", v=100.0, s=50.0, tick=10),
            _hex_row("8a2a1072b5bffff", state_fips="26", v=100.0, s=50.0, tick=10),
        ]
        cells = state_choropleth_cells_from_hex_rows(rows)

        assert cells == (ChoroplethCell(region_id="26", exploitation_rate=0.5),)

    def test_separate_states_yield_separate_cells_sorted_by_state_fips(self) -> None:
        rows = [
            _hex_row("8a2a1072b59ffff", state_fips="27", v=10.0, s=10.0),
            _hex_row("8a2a1072b5bffff", state_fips="26", v=10.0, s=5.0),
        ]
        cells = state_choropleth_cells_from_hex_rows(rows)

        assert [cell.region_id for cell in cells] == ["26", "27"]

    def test_rejects_rows_spanning_more_than_one_tick(self) -> None:
        """A mixed-tick slice cannot be a single as-of read."""
        rows = [
            _hex_row("8a2a1072b59ffff", state_fips="26", v=10.0, s=5.0, tick=10),
            _hex_row("8a2a1072b5bffff", state_fips="26", v=10.0, s=5.0, tick=11),
        ]
        with pytest.raises(ValueError, match="multiple ticks"):
            state_choropleth_cells_from_hex_rows(rows)

    def test_empty_rows_yield_empty_cells(self) -> None:
        assert state_choropleth_cells_from_hex_rows([]) == ()


class TestEaChoroplethCellsHonestAbsence:
    """No BEA Economic Area DeclaredView exists — the gap is explicit, not papered over."""

    def test_returns_none(self) -> None:
        assert ea_choropleth_cells() is None


class TestChoroplethCellModel:
    """Frozen, extra-forbid view-model — matches the keel's CountyView discipline."""

    def test_is_frozen(self) -> None:
        cell = ChoroplethCell(region_id="26163", exploitation_rate=0.5)
        with pytest.raises(ValidationError):
            cell.exploitation_rate = 0.9  # type: ignore[misc]

    def test_rejects_unknown_fields(self) -> None:
        with pytest.raises(ValidationError):
            ChoroplethCell(region_id="26163", exploitation_rate=0.5, bogus=1)  # type: ignore[call-arg]

    def test_absence_is_a_real_none_not_a_default_zero(self) -> None:
        cell = ChoroplethCell(region_id="26163")
        assert cell.exploitation_rate is None
