"""Contract tests for :mod:`babylon.projection.topology.hex_habitability` (T3 U6).

Fixture-fed: a hand-built ``BabylonGraph`` with ``territory`` nodes plus
hand-constructed :class:`~babylon.persistence.hex_state.DynamicHexState` rows
shaped exactly like ``test_choropleth.py``'s own fixture helper — no engine
tick, no database.
"""

from __future__ import annotations

from uuid import UUID

import pytest
from pydantic import ValidationError

from babylon.models.enums.topology import NodeType
from babylon.persistence.hex_state import DynamicHexState
from babylon.projection.topology.hex_habitability import (
    HexHabitabilityCell,
    hex_habitability_by_county_inheritance,
)
from babylon.topology import BabylonGraph

_SESSION = UUID("00000000-0000-0000-0000-000000000001")
WAYNE = "26163"
OTHER = "26125"


def _hex_row(h3_index: str, *, county_fips: str, tick: int = 847) -> DynamicHexState:
    """Build a hex row shaped like one ``v_hex_state_asof`` result row."""
    return DynamicHexState(
        session_id=_SESSION,
        tick=tick,
        h3_index=h3_index,
        county_fips=county_fips,
        state_fips=county_fips[:2],
        region_id="detroit-metro",
        c=1.0,
        v=1.0,
        s=1.0,
        k=1.0,
        biocapacity_stock=1.0,
        energy_stock=1.0,
        raw_material_stock=1.0,
        internet_access_pct=0.5,
        surveillance_coupling=0.1,
    )


def _graph_with_habitability(county_fips: str, habitability: float) -> BabylonGraph:
    graph = BabylonGraph()
    graph.add_node("T001", NodeType.TERRITORY, county_fips=county_fips, habitability=habitability)
    return graph


class TestCountyInheritance:
    """A hex's habitability is its parent county territory's LIVE reading."""

    def test_hex_inherits_its_parent_countys_live_habitability(self) -> None:
        graph = _graph_with_habitability(WAYNE, 0.83)
        rows = [_hex_row("8a2a1072b59ffff", county_fips=WAYNE)]

        cells = hex_habitability_by_county_inheritance(rows, graph=graph)

        assert cells == (
            HexHabitabilityCell(h3_index="8a2a1072b59ffff", county_fips=WAYNE, habitability=0.83),
        )

    def test_every_hex_under_the_same_county_gets_the_same_broadcast_value(self) -> None:
        graph = _graph_with_habitability(WAYNE, 0.6)
        rows = [
            _hex_row("8a2a1072b5bffff", county_fips=WAYNE),
            _hex_row("8a2a1072b59ffff", county_fips=WAYNE),
        ]

        cells = hex_habitability_by_county_inheritance(rows, graph=graph)

        assert [cell.habitability for cell in cells] == [pytest.approx(0.6), pytest.approx(0.6)]

    def test_two_different_counties_do_not_leak_into_each_other(self) -> None:
        graph = BabylonGraph()
        graph.add_node("T001", NodeType.TERRITORY, county_fips=WAYNE, habitability=0.9)
        graph.add_node("T002", NodeType.TERRITORY, county_fips=OTHER, habitability=0.2)
        rows = [
            _hex_row("8a2a1072b59ffff", county_fips=WAYNE),
            _hex_row("8a2a1072b5bffff", county_fips=OTHER),
        ]

        cells = hex_habitability_by_county_inheritance(rows, graph=graph)
        by_hex = {cell.h3_index: cell.habitability for cell in cells}

        assert by_hex["8a2a1072b59ffff"] == pytest.approx(0.9)
        assert by_hex["8a2a1072b5bffff"] == pytest.approx(0.2)

    def test_sorted_by_h3_index_regardless_of_input_order(self) -> None:
        graph = _graph_with_habitability(WAYNE, 0.5)
        rows = [
            _hex_row("8a2a1072b5bffff", county_fips=WAYNE),
            _hex_row("8a2a1072b59ffff", county_fips=WAYNE),
        ]

        cells = hex_habitability_by_county_inheritance(rows, graph=graph)

        assert [cell.h3_index for cell in cells] == ["8a2a1072b59ffff", "8a2a1072b5bffff"]

    def test_empty_rows_yield_empty_cells(self) -> None:
        assert hex_habitability_by_county_inheritance([], graph=BabylonGraph()) == ()


class TestHonestAbsence:
    """Absent county habitability propagates as None, never a fabricated zero."""

    def test_no_territory_for_the_county_projects_none(self) -> None:
        """The no-such-county case: no territory node carries this FIPS at all."""
        graph = BabylonGraph()
        rows = [_hex_row("8a2a1072b59ffff", county_fips=WAYNE)]

        cells = hex_habitability_by_county_inheritance(rows, graph=graph)

        assert cells[0].habitability is None

    def test_territory_present_but_no_habitability_attr_yet_projects_none(self) -> None:
        """Tick 0 / MetabolismSystem has never run this session — honest
        absence, never a fabricated 0.0 (nor the 1.0 some mean-aggregators,
        e.g. endgame_detector.py, default an unattributed reading to)."""
        graph = BabylonGraph()
        graph.add_node("T001", NodeType.TERRITORY, county_fips=WAYNE)
        rows = [_hex_row("8a2a1072b59ffff", county_fips=WAYNE)]

        cells = hex_habitability_by_county_inheritance(rows, graph=graph)

        assert cells[0].habitability is None


class TestHexHabitabilityCellModel:
    """Frozen, extra-forbid view-model — matches the keel's ChoroplethCell discipline."""

    def test_is_frozen(self) -> None:
        cell = HexHabitabilityCell(h3_index="8a2a1072b59ffff", county_fips=WAYNE, habitability=0.5)
        with pytest.raises(ValidationError):
            cell.habitability = 0.9  # type: ignore[misc]

    def test_rejects_unknown_fields(self) -> None:
        with pytest.raises(ValidationError):
            HexHabitabilityCell(
                h3_index="8a2a1072b59ffff",
                county_fips=WAYNE,
                habitability=0.5,
                bogus=1,  # type: ignore[call-arg]
            )

    def test_out_of_range_habitability_raises(self) -> None:
        with pytest.raises(ValidationError):
            HexHabitabilityCell(h3_index="8a2a1072b59ffff", county_fips=WAYNE, habitability=1.5)

    def test_absence_is_a_real_none_not_a_default_zero(self) -> None:
        cell = HexHabitabilityCell(h3_index="8a2a1072b59ffff", county_fips=WAYNE)
        assert cell.habitability is None
