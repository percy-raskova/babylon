"""Unit + law tests for the scale adjunction ``allocate ⊣ aggregate`` (Phase D3).

Pins the adjunction laws (``aggregate∘allocate = id`` because per-parent
shares sum to 1; ``allocate∘aggregate`` idempotent — the closure), the
extensive/intensive split, and — the §9.1 earn-its-keep targets — the H3
aggregation as a **sheaf**: gluing = conservation, and functoriality
``A_{6→5}∘A_{7→6} = A_{7→5}`` over real ``h3`` parentage. The naturality
squares are the ``conservation_audit`` invariant families (hex→county→state→
national sums for c/v/s/k), one parametrized law test each.
"""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from babylon.domain.dialectics.instances.scale import ScaleAdjunction

pytestmark = [pytest.mark.unit, pytest.mark.math, pytest.mark.topology]


# --------------------------------------------------------------------------- #
# Hypothesis strategy: a random (mapping, values) partition.                  #
# --------------------------------------------------------------------------- #
@st.composite
def _partition(draw: st.DrawFn) -> tuple[ScaleAdjunction, dict[str, float]]:
    """A random child→parent partition with normalized shares + parent values."""
    n_parents = draw(st.integers(min_value=1, max_value=4))
    parents = [f"p{i}" for i in range(n_parents)]
    mapping: dict[str, str] = {}
    child_id = 0
    for parent in parents:
        n_children = draw(st.integers(min_value=1, max_value=4))
        for _ in range(n_children):
            mapping[f"c{child_id}"] = parent
            child_id += 1
    adjunction = ScaleAdjunction.uniform(mapping)
    by_parent = {
        parent: draw(st.floats(min_value=-1e6, max_value=1e6, allow_nan=False))
        for parent in parents
    }
    return adjunction, by_parent


class TestValidation:
    """Per-parent shares must sum to 1; mapping and shares must align."""

    def test_shares_must_sum_to_one_per_parent(self) -> None:
        # This is the mutation-probe (c) killer: strip normalization/validation
        # and this construction stops raising.
        with pytest.raises(ValueError, match="sum to"):
            ScaleAdjunction(
                mapping={"c0": "p0", "c1": "p0"},
                shares={"c0": 0.3, "c1": 0.3},  # sums to 0.6, not 1.0
            )

    def test_mapping_and_shares_must_cover_same_children(self) -> None:
        with pytest.raises(ValueError, match="same children"):
            ScaleAdjunction(mapping={"c0": "p0"}, shares={"c0": 1.0, "c1": 1.0})

    def test_negative_share_rejected(self) -> None:
        with pytest.raises(ValueError, match="negative"):
            ScaleAdjunction(mapping={"c0": "p0", "c1": "p0"}, shares={"c0": 1.5, "c1": -0.5})

    def test_uniform_shares_sum_to_one(self) -> None:
        adj = ScaleAdjunction.uniform({"a": "P", "b": "P", "c": "P"})
        assert sum(adj.shares.values()) == pytest.approx(1.0)


class TestAdjunctionLaws:
    """allocate ⊣ aggregate: unit is identity; closure is idempotent."""

    @given(_partition())
    @settings(max_examples=200, deadline=None)
    def test_aggregate_after_allocate_is_identity(
        self, case: tuple[ScaleAdjunction, dict[str, float]]
    ) -> None:
        adjunction, by_parent = case
        round_trip = adjunction.aggregate(adjunction.allocate(by_parent))
        for parent, value in by_parent.items():
            assert round_trip[parent] == pytest.approx(value, rel=1e-9, abs=1e-9)

    @given(_partition())
    @settings(max_examples=200, deadline=None)
    def test_allocate_after_aggregate_is_idempotent(
        self, case: tuple[ScaleAdjunction, dict[str, float]]
    ) -> None:
        adjunction, by_parent = case
        by_child = adjunction.allocate(by_parent)  # any child-level field
        once = adjunction.allocate(adjunction.aggregate(by_child))
        twice = adjunction.allocate(adjunction.aggregate(once))
        for child in by_child:
            assert twice[child] == pytest.approx(once[child], rel=1e-9, abs=1e-9)


class TestExtensiveIntensive:
    """Extensive quantities SUM; intensive quantities weighted-mean."""

    def test_extensive_aggregate_sums_children(self) -> None:
        adj = ScaleAdjunction.uniform({"a": "P", "b": "P"})
        assert adj.aggregate({"a": 3.0, "b": 4.0})["P"] == pytest.approx(7.0)

    def test_intensive_aggregate_of_constant_is_the_constant(self) -> None:
        # Weighted mean of a constant field is the constant (intensive law).
        adj = ScaleAdjunction(mapping={"a": "P", "b": "P"}, shares={"a": 0.25, "b": 0.75})
        assert adj.aggregate_intensive({"a": 5.0, "b": 5.0})["P"] == pytest.approx(5.0)

    def test_intensive_aggregate_is_share_weighted(self) -> None:
        adj = ScaleAdjunction(mapping={"a": "P", "b": "P"}, shares={"a": 0.25, "b": 0.75})
        # 0.25*8 + 0.75*4 = 2 + 3 = 5.
        assert adj.aggregate_intensive({"a": 8.0, "b": 4.0})["P"] == pytest.approx(5.0)


class TestSheafConditions:
    """H3 aggregation as a sheaf: gluing = conservation; functoriality (§9.1)."""

    def test_sheaf_gluing_conservation(self) -> None:
        # Gluing: the sum over children equals the sum over parents — the
        # local sections glue to a global one with no leakage.
        adj = ScaleAdjunction.uniform({"a": "P", "b": "P", "c": "Q"})
        by_child = {"a": 1.5, "b": 2.5, "c": 4.0}
        aggregated = adj.aggregate(by_child)
        assert sum(aggregated.values()) == pytest.approx(sum(by_child.values()))

    def test_sheaf_functoriality_h3(self) -> None:
        # A_{6→5} ∘ A_{7→6} == A_{7→5} over REAL h3 parentage.
        h3 = pytest.importorskip("h3")
        center = h3.latlng_to_cell(42.33, -83.05, 7)
        res7 = sorted(h3.grid_disk(center, 2))

        map_76 = {c: h3.cell_to_parent(c, 6) for c in res7}
        res6 = sorted(set(map_76.values()))
        map_65 = {c: h3.cell_to_parent(c, 5) for c in res6}
        map_75 = {c: h3.cell_to_parent(c, 5) for c in res7}

        adj_76 = ScaleAdjunction.uniform(map_76)
        adj_65 = ScaleAdjunction.uniform(map_65)
        adj_75 = ScaleAdjunction.uniform(map_75)

        values7 = {c: float(i + 1) for i, c in enumerate(res7)}

        composite = adj_65.aggregate(adj_76.aggregate(values7))
        direct = adj_75.aggregate(values7)

        assert set(composite) == set(direct)
        for res5_cell, total in direct.items():
            assert composite[res5_cell] == pytest.approx(total)


# --------------------------------------------------------------------------- #
# Naturality squares = the conservation_audit invariant families.             #
# conservation_audit.py:158-180 names hex→county, county→state, state→national #
# sums for c/v/s/k. Each is a square FAMILY; one parametrized law test each.   #
# Phase D does NOT wire register_invariant (that is spec-062) — these tests    #
# ARE the square, over fixture data.                                           #
# --------------------------------------------------------------------------- #
_SQUARE_FAMILIES = [
    pytest.param(
        {"h1": "c1", "h2": "c1", "h3": "c2"},
        "hex_to_county",
        id="hex_to_county_sum",
    ),
    pytest.param(
        {"c1": "s1", "c2": "s1", "c3": "s2"},
        "county_to_state",
        id="county_to_state_sum",
    ),
    pytest.param(
        {"s1": "USA", "s2": "USA"},
        "state_to_national",
        id="state_to_national_sum",
    ),
]


class TestNaturalitySquares:
    """Each c/v/s/k sum family is a naturality square over ScaleAdjunction."""

    @pytest.mark.parametrize(("mapping", "family"), _SQUARE_FAMILIES)
    def test_cvsk_sums_conserve_per_family(self, mapping: dict[str, str], family: str) -> None:
        adj = ScaleAdjunction.uniform(mapping)
        children = list(mapping)
        # Distinct per-child c/v/s/k so a wrong projection cannot pass by luck.
        quantities = {
            "c": {child: float(i + 1) for i, child in enumerate(children)},
            "v": {child: float(2 * i + 1) for i, child in enumerate(children)},
            "s": {child: float(3 * i + 1) for i, child in enumerate(children)},
            "k": {child: float(5 * i + 1) for i, child in enumerate(children)},
        }
        for name, by_child in quantities.items():
            aggregated = adj.aggregate(by_child)
            # Conservation (gluing) for this quantity in this family.
            assert sum(aggregated.values()) == pytest.approx(sum(by_child.values())), (
                f"{family}_sum_{name} not conserved"
            )
            # Each parent equals the sum of exactly its own children.
            for parent in set(mapping.values()):
                expected = sum(by_child[c] for c, p in mapping.items() if p == parent)
                assert aggregated[parent] == pytest.approx(expected)


class TestGeographicAggregatorAgreement:
    """ScaleAdjunction.aggregate agrees with DefaultGeographicAggregator (bind, not rewrite)."""

    def test_agrees_with_default_geographic_aggregator(self) -> None:
        from babylon.domain.economics.tensor_hierarchy.geographic_flow import (
            DefaultGeographicAggregator,
        )
        from babylon.domain.economics.tensor_hierarchy.types import GeographicFlow

        areas = ["A1", "A2", "B1"]
        matrix = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]], dtype=np.float64)
        flow = GeographicFlow(year=2020, areas=areas, flow_matrix=matrix)
        mapping = {"A1": "A", "A2": "A", "B1": "B"}

        aggregated_flow = DefaultGeographicAggregator().aggregate(flow, mapping)
        target_idx = {t: i for i, t in enumerate(aggregated_flow.areas)}
        geo_outflow = {
            t: float(aggregated_flow.flow_matrix[target_idx[t]].sum())
            for t in aggregated_flow.areas
        }

        # ScaleAdjunction aggregate of per-area outflow (row sums) over the
        # same mapping must reproduce the aggregator's per-target outflow.
        outflow = {area: float(matrix[i].sum()) for i, area in enumerate(areas)}
        scale_outflow = ScaleAdjunction.uniform(mapping).aggregate(outflow)

        assert set(scale_outflow) == set(geo_outflow)
        for target, value in geo_outflow.items():
            assert scale_outflow[target] == pytest.approx(value)
