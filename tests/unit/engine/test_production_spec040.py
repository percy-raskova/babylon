"""Tests for ProductionSystem Spec 040 compliance.

Verifies that the ProductionSystem pilot correctly declares:
- invariants (Discipline 1)
- phase (Discipline 4)
"""

from __future__ import annotations

from babylon.engine.phase import Phase
from babylon.engine.systems.production import ProductionSystem


class TestProductionSystemSpec040:
    """Verify ProductionSystem Spec 040 attributes."""

    def test_declares_invariants(self) -> None:
        """ProductionSystem has at least one invariant."""
        system = ProductionSystem()
        assert len(system.invariants) >= 1

    def test_invariant_is_non_negative_wealth(self) -> None:
        """First invariant is NonNegativeWealth."""
        system = ProductionSystem()
        assert system.invariants[0].name == "non_negative_wealth"

    def test_declares_production_phase(self) -> None:
        """ProductionSystem operates in PRODUCTION phase."""
        system = ProductionSystem()
        assert system.phase == Phase.PRODUCTION
