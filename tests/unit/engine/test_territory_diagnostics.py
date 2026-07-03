"""TerritorySystem diagnostics aggregation tests (T053)."""

from __future__ import annotations

import math

import networkx as nx
import pytest

from babylon.engine.graph import BabylonGraph
from babylon.engine.systems.territory_diagnostics import (
    HexCountyRollup,
    aggregate_counties_by_state,
    aggregate_hexes_by_county,
)


def _add_hex(
    g: nx.DiGraph[str],
    h3: str,
    county: str,
    c: float = 1.0,
    v: float = 1.0,
    s: float = 1.0,
    k: float = 1.0,
) -> None:
    g.add_node(
        h3,
        _node_type="hex",
        county_fips=county,
        c=c,
        v=v,
        s=s,
        k=k,
        biocapacity_stock=2.0,
    )


@pytest.mark.cross_scale
class TestAggregateHexesByCounty:
    def test_empty_graph_returns_empty(self) -> None:
        g = BabylonGraph()
        assert aggregate_hexes_by_county(g) == {}

    def test_single_hex_one_county(self) -> None:
        g = BabylonGraph()
        _add_hex(g, "872d34a89ffffff", "26163", c=10.0, v=5.0, s=3.0, k=100.0)
        rollups = aggregate_hexes_by_county(g)
        assert "26163" in rollups
        r = rollups["26163"]
        assert r.c_sum == 10.0
        assert r.hex_count == 1

    def test_two_hexes_one_county_summed(self) -> None:
        g = BabylonGraph()
        _add_hex(g, "872d34a89ffffff", "26163", c=10.0, v=5.0)
        _add_hex(g, "872d34b0bffffff", "26163", c=20.0, v=15.0)
        r = aggregate_hexes_by_county(g)["26163"]
        assert r.c_sum == 30.0
        assert r.v_sum == 20.0
        assert r.hex_count == 2

    def test_two_counties_isolated(self) -> None:
        g = BabylonGraph()
        _add_hex(g, "872d34a89ffffff", "26163", c=10.0)
        _add_hex(g, "872d34b0bffffff", "26125", c=20.0)
        rollups = aggregate_hexes_by_county(g)
        assert rollups["26163"].c_sum == 10.0
        assert rollups["26125"].c_sum == 20.0
        assert rollups["26163"].hex_count == 1
        assert rollups["26125"].hex_count == 1

    def test_skips_non_hex_nodes(self) -> None:
        g = BabylonGraph()
        _add_hex(g, "872d34a89ffffff", "26163", c=10.0)
        g.add_node("canada", _node_type="external")
        g.add_node("26163", _node_type="county")
        rollups = aggregate_hexes_by_county(g)
        assert len(rollups) == 1
        assert "26163" in rollups
        assert rollups["26163"].hex_count == 1

    def test_hex_without_county_fips_skipped(self) -> None:
        g = BabylonGraph()
        g.add_node("orphan", _node_type="hex", c=1.0, v=1.0, s=1.0, k=1.0)
        assert aggregate_hexes_by_county(g) == {}


@pytest.mark.cross_scale
class TestAggregateCountiesByState:
    def test_canonical_fips_prefix_rule(self) -> None:
        """FR-023: state_fips defaults to county_fips[:2]."""
        rollups = [
            HexCountyRollup(
                county_fips="26163",
                c_sum=10.0,
                v_sum=5.0,
                s_sum=3.0,
                k_sum=100.0,
                biocapacity_sum=20.0,
                hex_count=1,
            ),
            HexCountyRollup(
                county_fips="26125",
                c_sum=20.0,
                v_sum=10.0,
                s_sum=6.0,
                k_sum=200.0,
                biocapacity_sum=40.0,
                hex_count=2,
            ),
        ]
        by_state = aggregate_counties_by_state(rollups)
        assert "26" in by_state
        s = by_state["26"]
        assert math.isclose(s.c_sum, 30.0)
        assert s.hex_count == 3

    def test_explicit_county_to_state_overrides_default(self) -> None:
        rollups = [
            HexCountyRollup(
                county_fips="00001",
                c_sum=10.0,
                v_sum=5.0,
                s_sum=3.0,
                k_sum=100.0,
                biocapacity_sum=20.0,
                hex_count=1,
            ),
        ]
        by_state = aggregate_counties_by_state(rollups, county_to_state={"00001": "99"})
        assert "99" in by_state
        assert "00" not in by_state
