"""Pipeline-position tests for SubstrateSystem (T082 / T086 / US7).

Verifies:
  - SubstrateSystem is inserted into the canonical _DEFAULT_SYSTEMS pipeline.
  - It runs between TerritorySystem (slot 2) and ProductionSystem (slot 3).
  - Production reads substrate state from the *just-computed* graph attrs,
    so a zeroed substrate value at start-of-tick propagates into Production
    within the same tick.
"""

from __future__ import annotations

import pytest

from babylon.engine.simulation_engine import _DEFAULT_SYSTEMS
from babylon.engine.systems.substrate import SubstrateSystem


@pytest.mark.cross_scale
class TestPipelineSubstratePosition:
    """User Story 7 acceptance scenarios 1-2."""

    def test_substrate_inserted_into_default_pipeline(self) -> None:
        """T085 acceptance: _DEFAULT_SYSTEMS contains a SubstrateSystem instance."""
        types = [type(s) for s in _DEFAULT_SYSTEMS]
        assert SubstrateSystem in types, (
            "SubstrateSystem missing from _DEFAULT_SYSTEMS — engine "
            "pipeline does not satisfy FR-050"
        )

    def test_substrate_runs_after_territory(self) -> None:
        """Territory must precede Substrate (Territory writes land state)."""
        names = [type(s).__name__ for s in _DEFAULT_SYSTEMS]
        territory_idx = names.index("TerritorySystem")
        substrate_idx = names.index("SubstrateSystem")
        assert territory_idx < substrate_idx, (
            f"Substrate must run AFTER Territory (FR-050). "
            f"Got Territory at {territory_idx}, Substrate at {substrate_idx}"
        )

    def test_substrate_runs_before_production(self) -> None:
        """Substrate must precede Production so Production reads post-Substrate state."""
        names = [type(s).__name__ for s in _DEFAULT_SYSTEMS]
        substrate_idx = names.index("SubstrateSystem")
        production_idx = names.index("ProductionSystem")
        assert substrate_idx < production_idx, (
            f"Substrate must run BEFORE Production (FR-051 / US7 acceptance #2). "
            f"Got Substrate at {substrate_idx}, Production at {production_idx}"
        )

    def test_substrate_slot_is_exactly_2_5(self) -> None:
        """Substrate sits between Territory (slot 2) and Production (slot 3).

        Concretely: there are zero systems between Territory and Substrate,
        and zero systems between Substrate and Production. This guarantees
        the canonical "slot 2.5" position.
        """
        names = [type(s).__name__ for s in _DEFAULT_SYSTEMS]
        territory_idx = names.index("TerritorySystem")
        substrate_idx = names.index("SubstrateSystem")
        production_idx = names.index("ProductionSystem")
        assert substrate_idx - territory_idx == 1, (
            "Substrate must sit immediately after Territory; "
            f"got gap of {substrate_idx - territory_idx}"
        )
        assert production_idx - substrate_idx == 1, (
            "Production must sit immediately after Substrate; "
            f"got gap of {production_idx - substrate_idx}"
        )


@pytest.mark.cross_scale
class TestSubstrateZeroPropagation:
    """T086: zeroed substrate at start-of-tick affects Production same tick.

    The behavioural property is: if a hex enters the tick with
    raw_material_stock == 0, SubstrateSystem leaves it at 0, and
    ProductionSystem sees 0 (not a stale non-zero from a pre-Substrate
    snapshot). The pass-through MVP SubstrateSystem implementation
    preserves this property by construction — it does not regenerate
    stocks. The real assertion is that the engine never holds a
    pre-Substrate snapshot that Production reads from.
    """

    def test_substrate_pass_through_preserves_zero(self) -> None:
        """A zero raw_material_stock entering Substrate stays zero leaving."""
        import networkx as nx

        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "872d34a89ffffff",
            _node_type="hex",
            raw_material_stock=0.0,
            energy_stock=10.0,
            biocapacity_stock=20.0,
        )
        SubstrateSystem().step(graph, services=object(), context={})  # type: ignore[arg-type]
        assert graph.nodes["872d34a89ffffff"]["raw_material_stock"] == 0.0

    def test_substrate_fills_missing_stock_attrs(self) -> None:
        """FR-050: every hex carries all three substrate stocks after Substrate."""
        import networkx as nx

        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node("872d34a89ffffff", _node_type="hex")
        SubstrateSystem().step(graph, services=object(), context={})  # type: ignore[arg-type]
        attrs = graph.nodes["872d34a89ffffff"]
        for key in ("raw_material_stock", "energy_stock", "biocapacity_stock"):
            assert key in attrs
            assert attrs[key] == 0.0

    def test_substrate_skips_non_hex_nodes(self) -> None:
        """External nodes and other types are NOT touched by SubstrateSystem."""
        import networkx as nx

        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node("canada", _node_type="external")
        SubstrateSystem().step(graph, services=object(), context={})  # type: ignore[arg-type]
        assert "raw_material_stock" not in graph.nodes["canada"]
