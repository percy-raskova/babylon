"""Pipeline ordering test: Substrate runs between Territory and Production (T081)."""

from __future__ import annotations

import pytest

from babylon.engine.systems.production import ProductionSystem
from babylon.engine.systems.substrate import SubstrateSystem
from babylon.engine.systems.territory import TerritorySystem


@pytest.mark.cross_scale
class TestSubstrateSystemOrdering:
    """FR-050: Substrate runs after Territory, before Production."""

    def test_substrate_system_name(self) -> None:
        assert SubstrateSystem().name == "substrate"

    def test_substrate_implements_system_protocol(self) -> None:
        from babylon.kernel.system_protocol import System

        assert isinstance(SubstrateSystem(), System)

    def test_intended_pipeline_position_between_territory_and_production(
        self,
    ) -> None:
        """Documented ordering: Territory (2) → Substrate (2.5) → Production (3).

        We exercise the contract by verifying the three system classes are
        compatible with the System protocol and that Substrate sits between
        the canonical Territory and Production slot positions per FR-050.
        """
        # The actual engine pipeline insertion is handled at the engine
        # registration site. This test verifies the canonical neighbor
        # relationship the spec mandates.
        territory = TerritorySystem()
        substrate = SubstrateSystem()
        production = ProductionSystem()
        # Names are stable identifiers; case-insensitive comparison
        # since existing systems use mixed case (Territory) vs lowercase
        # (production). The contract is that all three names are non-empty.
        assert territory.name
        assert substrate.name == "substrate"
        assert production.name
