"""Tests for materialist causality system ordering.

The simulation engine executes systems in a fixed order that encodes
historical materialism: material conditions (biological, spatial, economic)
must be computed before social/ideological effects can be derived.

ADR032: Materialist Causality System Order
"""

from __future__ import annotations

import pytest

from babylon.engine.simulation_engine import _DEFAULT_SYSTEMS


@pytest.mark.unit
class TestMaterialistCausalityOrder:
    """Verify systems execute in materialist causal order.

    The order encodes the principle: base before superstructure.

    1. Vitality (biological cost + death) - Dead entities don't work
    2. Territory (land state) - Land conditions affect production
    3. Production (value creation) - Value must exist before extraction
    4. Solidarity (organization) - Organization affects bargaining
    5. ImperialRent (extraction) - Landlord eats after harvest
    6. Decomposition (LA crisis) - Class breakdown on super-wage crisis
    7. ControlRatio (terminal decision) - Guard:prisoner ratio + bifurcation
    8. Metabolism (environment) - Ecological residue of production
    9. Survival (risk assessment) - P(S|A), P(S|R) from material state
    10. Struggle (action/revolt) - Agency responds to survival odds
    11. Consciousness (ideology drift) - Ideology responds to material
    12. Contradiction (tension) - Final systemic accounting
    """

    def test_system_order_is_materialist(self) -> None:
        """Verify DEFAULT_SYSTEMS follows materialist causality order."""
        # System names as defined by each system's `name` property
        expected_order = [
            "vitality",  # VitalitySystem
            "Territory",  # TerritorySystem
            "production",  # ProductionSystem
            "Solidarity",  # SolidaritySystem
            "Imperial Rent",  # ImperialRentSystem
            "Decomposition",  # DecompositionSystem (Terminal Crisis)
            "ControlRatio",  # ControlRatioSystem (Terminal Crisis)
            "Metabolism",  # MetabolismSystem
            "Survival Calculus",  # SurvivalSystem
            "Struggle",  # StruggleSystem
            "Consciousness Drift",  # ConsciousnessSystem
            "Contradiction Tension",  # ContradictionSystem
        ]
        actual_order = [s.name for s in _DEFAULT_SYSTEMS]
        assert actual_order == expected_order, (
            f"System order violates materialist causality.\n"
            f"Expected: {expected_order}\n"
            f"Actual:   {actual_order}"
        )

    def test_vitality_runs_first(self) -> None:
        """VitalitySystem must be first (death before economics)."""
        assert _DEFAULT_SYSTEMS[0].name == "vitality", (
            "VitalitySystem must run first - dead entities cannot participate"
        )

    def test_territory_runs_before_production(self) -> None:
        """TerritorySystem must run before ProductionSystem."""
        names = [s.name for s in _DEFAULT_SYSTEMS]
        territory_idx = names.index("Territory")
        production_idx = names.index("production")
        assert territory_idx < production_idx, (
            "TerritorySystem must run before ProductionSystem - "
            "land conditions determine production capacity"
        )

    def test_production_runs_before_extraction(self) -> None:
        """ProductionSystem must run before ImperialRentSystem."""
        names = [s.name for s in _DEFAULT_SYSTEMS]
        production_idx = names.index("production")
        extraction_idx = names.index("Imperial Rent")
        assert production_idx < extraction_idx, (
            "ProductionSystem must run before ImperialRentSystem - "
            "value must be created before it can be extracted"
        )

    def test_solidarity_runs_before_extraction(self) -> None:
        """SolidaritySystem must run before ImperialRentSystem."""
        names = [s.name for s in _DEFAULT_SYSTEMS]
        solidarity_idx = names.index("Solidarity")
        extraction_idx = names.index("Imperial Rent")
        assert solidarity_idx < extraction_idx, (
            "SolidaritySystem must run before ImperialRentSystem - "
            "organization affects resistance to extraction"
        )

    def test_metabolism_runs_after_extraction(self) -> None:
        """MetabolismSystem must run after ImperialRentSystem."""
        names = [s.name for s in _DEFAULT_SYSTEMS]
        extraction_idx = names.index("Imperial Rent")
        metabolism_idx = names.index("Metabolism")
        assert metabolism_idx > extraction_idx, (
            "MetabolismSystem must run after ImperialRentSystem - "
            "environmental degradation is consequence of extraction"
        )

    def test_survival_runs_after_metabolism(self) -> None:
        """SurvivalSystem must run after MetabolismSystem."""
        names = [s.name for s in _DEFAULT_SYSTEMS]
        metabolism_idx = names.index("Metabolism")
        survival_idx = names.index("Survival Calculus")
        assert survival_idx > metabolism_idx, (
            "SurvivalSystem must run after MetabolismSystem - "
            "survival odds depend on environmental state"
        )

    def test_consciousness_runs_after_struggle(self) -> None:
        """ConsciousnessSystem must run after StruggleSystem."""
        names = [s.name for s in _DEFAULT_SYSTEMS]
        struggle_idx = names.index("Struggle")
        consciousness_idx = names.index("Consciousness Drift")
        assert consciousness_idx > struggle_idx, (
            "ConsciousnessSystem must run after StruggleSystem - "
            "ideology responds to material struggle"
        )

    def test_contradiction_runs_last(self) -> None:
        """ContradictionSystem must run last."""
        assert _DEFAULT_SYSTEMS[-1].name == "Contradiction Tension", (
            "ContradictionSystem must run last - systemic tension aggregates all effects"
        )

    def test_all_twelve_systems_present(self) -> None:
        """All 12 core systems must be registered."""
        assert len(_DEFAULT_SYSTEMS) == 12, f"Expected 12 systems, got {len(_DEFAULT_SYSTEMS)}"
