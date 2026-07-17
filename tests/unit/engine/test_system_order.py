"""Tests for materialist causality system ordering.

The simulation engine executes systems in a fixed order that encodes
historical materialism: material conditions (biological, spatial, economic)
must be computed before social/ideological effects can be derived.

ADR032: Materialist Causality System Order

Spec 056 (F6=α, 2026-05-07) reordered OODASystem from the last position
(formerly position 21) to position 14, immediately between MetabolismSystem
and SurvivalSystem. This makes the engine's actual execution order match
ADR032's documented Material Base → Action Phase → Consequences partition.
The expected_order list below was updated accordingly; all other ordering
assertions (Vitality first, Survival after Metabolism, etc.) hold under
the new layout because OODA was inserted between two adjacent groups.
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
    4. TickDynamics (economic state) - Annual economic state evolution
    5. ReserveArmy (wage pressure) - Reserve army disciplines wages (Feature 021)
    6. Solidarity (organization) - Organization affects bargaining
    7. ImperialRent (extraction) - Landlord eats after harvest
    8. DispossessionEvents (value transfer) - Dispossession transfers wealth (Feature 021)
    9. Decomposition (LA crisis) - Class breakdown on super-wage crisis
    10. ControlRatio (terminal decision) - Guard:prisoner ratio + bifurcation
    11. Metabolism (environment) - Ecological residue of production
    12. Survival (risk assessment) - P(S|A), P(S|R) from material state
    13. Struggle (action/revolt) - Agency responds to survival odds
    14. Consciousness (ideology drift) - Ideology responds to material
    15. Contradiction (tension) - Final systemic accounting
    """

    def test_system_order_is_materialist(self) -> None:
        """Verify DEFAULT_SYSTEMS follows materialist causality order
        (per ADR032 + spec-056 F6=α reorder)."""
        # System names as defined by each system's `name` property.
        # Position 14 is OODASystem per spec-056 F6=α (was last/21 before).
        expected_order = [
            # --- Material Base (positions 1-13, plus Substrate at 2.5) ---
            "vitality",  # 1.  VitalitySystem
            "Territory",  # 2.  TerritorySystem
            "substrate",  # 2.5 SubstrateSystem (Spec 062 US7)
            "production",  # 3.  ProductionSystem
            "tick_dynamics",  # 4.  TickDynamicsSystem
            "reserve_army",  # 5.  ReserveArmySystem (Feature 021)
            "community",  # 6.  CommunitySystem (Feature 022)
            "Lifecycle Circuit",  # 7.  LifecycleSystem (Feature 030)
            "Solidarity",  # 8.  SolidaritySystem
            "Imperial Rent",  # 9.  ImperialRentSystem
            "dispossession_events",  # 10. DispossessionEventSystem (Feature 021)
            "Decomposition",  # 11. DecompositionSystem
            "ControlRatio",  # 12. ControlRatioSystem
            "Metabolism",  # 13. MetabolismSystem
            # --- Action Phase (position 14) — Spec 056 F6=α reorder ---
            "ooda",  # 14. OODASystem (Feature 032)
            "FactionInfluence",  # 14.5. FactionInfluenceSystem (Spec 070 FR-021)
            # --- Consequences (positions 15-21) ---
            "Doctrine",  # 14.7. DoctrineSystem (ADR073 — per-org Doctrine Tree)
            "Survival Calculus",  # 15. SurvivalSystem
            "Struggle",  # 16. StruggleSystem
            "Consciousness Drift",  # 17. ConsciousnessSystem
            "Fascist Faction",  # 17.4. FascistFactionSystem (Spec 071 reactionary subject)
            "Sovereignty",  # 17.5. SovereigntySystem (Spec 070 FR-019, FR-043)
            "Contradiction Tension",  # 18. ContradictionSystem
            "contradiction_field",  # 19. ContradictionFieldSystem (Feature 002)
            "field_derivative",  # 20. FieldDerivativeSystem (Feature 002)
            "CollapseTransition",  # 20.5. CollapseTransitionSystem (Spec 070 FR-023)
            "edge_transition",  # 21. EdgeTransitionSystem (Feature 002)
            "Wealth Distribution",  # 21.5. WealthDistributionSystem (Program 21 Phase-1 shadow)
            "Epistemic Horizon",  # 22. EpistemicHorizonSystem (Epistemic Horizon Phase 1 shadow)
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
        """ContradictionSystem must run before field topology systems."""
        # ContradictionSystem is at position 12 (0-indexed), followed by
        # ContradictionFieldSystem, FieldDerivativeSystem, EdgeTransitionSystem
        system_names = [s.name for s in _DEFAULT_SYSTEMS]
        contradiction_idx = system_names.index("Contradiction Tension")
        assert contradiction_idx < len(_DEFAULT_SYSTEMS) - 1, (
            "ContradictionSystem must be registered"
        )

    def test_all_twenty_nine_systems_present(self) -> None:
        """All 29 systems must be registered.

        13 core + 2 Volume I + 1 community + 1 lifecycle + 3 field topology
        + 1 OODA + 1 substrate (Spec 062 US7) + 3 Spec-070 systems
        (FactionInfluenceSystem at 14.5 + SovereigntySystem at 17.5 +
        CollapseTransitionSystem at 20.5) + 1 Spec-071 system
        (FascistFactionSystem at 17.4) + 1 DoctrineSystem at 14.7 (ADR073)
        + 1 WealthDistributionSystem at 21.5 (Program 21 Phase-1 shadow, ADR075)
        + 1 Epistemic Horizon Phase 1 system (EpistemicHorizonSystem, last).
        """
        assert len(_DEFAULT_SYSTEMS) == 29, f"Expected 29 systems, got {len(_DEFAULT_SYSTEMS)}"

    def test_epistemic_horizon_runs_last(self) -> None:
        """EpistemicHorizonSystem must be the LAST system in _DEFAULT_SYSTEMS.

        WHY: it computes Mass Receptivity / Intel Confidence from this
        tick's ``p_acquiescence`` (SurvivalSystem, position 15) and
        ``class_consciousness`` (ConsciousnessSystem, position 17) — both
        already mutated earlier in the SAME tick. Running last means it
        observes the fully-settled tick rather than last tick's stale
        values, and (Phase 1 SHADOW ONLY) writes read-only attrs nothing
        else in the engine consumes yet, so its position cannot perturb
        any other system's inputs.
        """
        assert _DEFAULT_SYSTEMS[-1].name == "Epistemic Horizon", (
            "EpistemicHorizonSystem must run last — it observes the fully-mutated "
            "tick (this tick's p_acquiescence/class_consciousness), not last "
            "tick's stale values."
        )
