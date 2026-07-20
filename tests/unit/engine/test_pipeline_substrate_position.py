"""Pipeline-position tests for SubstrateSystem (T082 / T086 / US7; #39 T6).

Verifies:
  - SubstrateSystem is inserted into the canonical _DEFAULT_SYSTEMS pipeline.
  - It runs between TerritorySystem (slot 2) and ProductionSystem (slot 3).

#39 T6 retired the old hex-grain pass-through MVP (``TestSubstrateZeroPropagation``,
which asserted a zeroed ``raw_material_stock`` on a ``NodeType.HEX`` node
propagates unchanged into Production the same tick) -- ``ProductionSystem``
has never read ``raw_material_stock`` (grepped: zero references), so that
"propagation" property had no real behavioral content once the pass-through
became real depletion math. The real same-tick-ordering property SubstrateSystem
now has -- it reads last tick's ``extraction_intensity`` (written by
Production, which runs AFTER Substrate) -- is covered by
``tests/unit/engine/systems/test_substrate.py::TestOneTickLag``.
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
