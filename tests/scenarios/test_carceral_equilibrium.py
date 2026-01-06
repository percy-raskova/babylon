"""Scenario tests for the Carceral Equilibrium trajectory.

This module validates the "null hypothesis" - the default trajectory of
the Babylon simulation when no player intervention occurs. It tests the
theoretical claims from:
- ai-docs/carceral-equilibrium.md: The 70-Year Arc
- ai-docs/theory.md: Core MLM-TW theoretical framework

The test verifies that the simulation progresses through the following
phases IN ORDER (phase sequence validation, not exact tick timing):

1. Imperial Extraction (hollow stability)
2. Metabolic Rift Opens (overshoot > 1.0)
3. SUPERWAGE_CRISIS (rent pool exhausted)
4. CLASS_DECOMPOSITION (LA -> Enforcers + Prisoners)
5. CONTROL_RATIO_CRISIS (prisoners exceed capacity)
6. TERMINAL_DECISION(genocide) -> Stable Necropolis

Without player organization (org < 0.5), the system resolves to genocide,
not revolution. This is the "lose condition" shown mechanically.

Sprint: Terminal Crisis Dynamics
ADR: ADR033_scenario_layer_test_taxonomy

TDD Status: RED PHASE
The trajectory test defines the expected behavior per carceral-equilibrium.md.
Initial conditions may need tuning to trigger all phase transitions.
GREEN phase will adjust parameters to produce the expected sequence.
"""

from __future__ import annotations

import pytest

from babylon.engine.observers import MetricsCollector
from babylon.engine.simulation import Simulation
from babylon.models import SimulationConfig, WorldState
from babylon.models.enums import EventType, SocialRole

from .conftest import create_imperial_circuit_state

MAX_TICKS = 5200  # 100 years (52 ticks/year)

# Phase staggering requirements (RED phase TDD)
# Imperial collapse is a process, not an instant. Phases must be temporally separated.
TICKS_PER_YEAR = 52
MIN_PHASE_SPREAD_TICKS = 104  # 2 years minimum between first and last carceral phase
MIN_PHASE_GAP_TICKS = 1  # Each phase transition must have at least 1 tick gap


@pytest.mark.slow
@pytest.mark.integration
class TestCarceralEquilibrium:
    """Tests for the 70-Year Arc (Default - No Player Intervention).

    These tests validate the theoretical trajectory described in
    ai-docs/carceral-equilibrium.md. The simulation should progress
    through imperial extraction, metabolic rift, superwage crisis,
    LA decomposition, control ratio crisis, and terminal decision.

    Without player organization, the terminal decision should resolve
    to genocide (prisoners eliminated to restore control ratio), not
    revolution (which requires organization >= 0.5).
    """

    def test_default_trajectory_phases(
        self,
        config: SimulationConfig,
        batch_metrics_collector: MetricsCollector,
    ) -> None:
        """70-Year Arc (Default - No Player Intervention).

        Validates the trajectory from ai-docs/carceral-equilibrium.md:
        - Phase 2: Metabolic Rift opens (overshoot > 1.0)
        - Phase 3: SUPERWAGE_CRISIS emitted (rent pool exhausted)
        - Phase 4: LA decomposition into Enforcers/Prisoners
        - Phase 5: CONTROL_RATIO_CRISIS (prisoners > enforcers * 20)
        - Phase 6/7: TERMINAL_DECISION(genocide) - Stable Necropolis

        The test focuses on PHASE SEQUENCE ORDERING, not exact tick timing.
        The theoretical claim is that these phases occur IN THIS ORDER
        as a consequence of imperial collapse mechanics.
        """
        # Create initial state: imperial circuit with NO player organization
        state = create_imperial_circuit_state()
        sim = Simulation(state, config, observers=[batch_metrics_collector])

        # Track phase milestones (tick when first detected)
        milestones: dict[str, int | None] = {
            "metabolic_rift_opened": None,
            "superwage_crisis": None,
            "class_decomposition": None,
            "control_ratio_crisis": None,
            "terminal_decision": None,
        }

        # Track terminal decision outcome
        terminal_outcome: str | None = None

        # Run tick-by-tick, detecting phase transitions
        for tick in range(MAX_TICKS):
            current_state = sim.step()
            latest = batch_metrics_collector.latest

            # Phase 2: Metabolic Rift - overshoot ratio exceeds 1.0
            if (
                milestones["metabolic_rift_opened"] is None
                and latest is not None
                and latest.overshoot_ratio > 1.0
            ):
                milestones["metabolic_rift_opened"] = tick

            # Check events for phase transitions
            for event in current_state.events:
                if (
                    event.event_type == EventType.SUPERWAGE_CRISIS
                    and milestones["superwage_crisis"] is None
                ):
                    milestones["superwage_crisis"] = tick

                elif (
                    event.event_type == EventType.CLASS_DECOMPOSITION
                    and milestones["class_decomposition"] is None
                ):
                    milestones["class_decomposition"] = tick
                    # Verify LA decomposed into enforcers and prisoners
                    self._verify_decomposition_occurred(current_state)

                elif (
                    event.event_type == EventType.CONTROL_RATIO_CRISIS
                    and milestones["control_ratio_crisis"] is None
                ):
                    milestones["control_ratio_crisis"] = tick

                elif (
                    event.event_type == EventType.TERMINAL_DECISION
                    and milestones["terminal_decision"] is None
                ):
                    milestones["terminal_decision"] = tick
                    # TerminalDecisionEvent has outcome as direct attribute
                    terminal_outcome = event.outcome

            # Early exit if terminal decision reached
            if milestones["terminal_decision"] is not None:
                break

        # =================================================================
        # ASSERTIONS: Phase sequence validation
        # =================================================================

        # All phases must occur
        assert milestones["metabolic_rift_opened"] is not None, (
            "Metabolic rift should open (overshoot > 1.0) during simulation. "
            f"Final overshoot: {batch_metrics_collector.latest.overshoot_ratio if batch_metrics_collector.latest else 'N/A'}"
        )
        assert milestones["superwage_crisis"] is not None, (
            "Superwage crisis should occur (rent pool exhausted). "
            f"Final pool: {batch_metrics_collector.latest.imperial_rent_pool if batch_metrics_collector.latest else 'N/A'}"
        )
        assert milestones["class_decomposition"] is not None, (
            "Labor aristocracy should decompose into enforcers/prisoners. "
            "CLASS_DECOMPOSITION event not detected."
        )
        assert milestones["control_ratio_crisis"] is not None, (
            "Control ratio crisis should occur (prisoners exceed capacity). "
            "CONTROL_RATIO_CRISIS event not detected."
        )
        assert milestones["terminal_decision"] is not None, (
            "Terminal decision should be reached. TERMINAL_DECISION event not detected."
        )

        # Phases must occur IN ORDER (key theoretical claim)
        assert milestones["metabolic_rift_opened"] < milestones["superwage_crisis"], (
            f"Metabolic rift (tick {milestones['metabolic_rift_opened']}) "
            f"must precede superwage crisis (tick {milestones['superwage_crisis']})"
        )
        assert milestones["superwage_crisis"] < milestones["class_decomposition"], (
            f"Superwage crisis (tick {milestones['superwage_crisis']}) "
            f"must trigger LA decomposition (tick {milestones['class_decomposition']})"
        )
        assert milestones["class_decomposition"] < milestones["control_ratio_crisis"], (
            f"Decomposition (tick {milestones['class_decomposition']}) "
            f"must precede control ratio crisis (tick {milestones['control_ratio_crisis']})"
        )
        assert milestones["control_ratio_crisis"] < milestones["terminal_decision"], (
            f"Control ratio crisis (tick {milestones['control_ratio_crisis']}) "
            f"must trigger terminal decision (tick {milestones['terminal_decision']})"
        )

        # Terminal decision should be genocide (no organization)
        assert terminal_outcome == "genocide", (
            f"Without player organization, terminal decision should be 'genocide', "
            f"got '{terminal_outcome}'. This suggests organization threshold was exceeded."
        )

    def _verify_decomposition_occurred(self, state: WorldState) -> None:
        """Verify that LA decomposition produced enforcers and prisoners.

        After CLASS_DECOMPOSITION, the simulation should have:
        - At least one CARCERAL_ENFORCER entity (guards)
        - At least one INTERNAL_PROLETARIAT entity (prisoners)

        Args:
            state: WorldState after decomposition event
        """
        roles = {entity.role for entity in state.entities.values() if entity.active}

        # Check for enforcer role
        has_enforcers = SocialRole.CARCERAL_ENFORCER in roles
        # Check for internal proletariat role
        has_prisoners = SocialRole.INTERNAL_PROLETARIAT in roles

        # At least one of these should exist after decomposition
        # (The original LA may be deactivated)
        assert has_enforcers or has_prisoners, (
            "After CLASS_DECOMPOSITION, expected CARCERAL_ENFORCER or "
            f"INTERNAL_PROLETARIAT entities. Found roles: {roles}"
        )

    def _run_and_collect_milestones(
        self,
        config: SimulationConfig,
        batch_metrics_collector: MetricsCollector,
    ) -> dict[str, int | None]:
        """Run simulation and collect phase milestone ticks.

        Returns:
            Dictionary mapping phase names to the tick when first detected,
            or None if phase did not occur.
        """
        state = create_imperial_circuit_state()
        sim = Simulation(state, config, observers=[batch_metrics_collector])

        milestones: dict[str, int | None] = {
            "metabolic_rift_opened": None,
            "superwage_crisis": None,
            "class_decomposition": None,
            "control_ratio_crisis": None,
            "terminal_decision": None,
        }

        for tick in range(MAX_TICKS):
            current_state = sim.step()
            latest = batch_metrics_collector.latest

            # Metabolic rift detection
            if (
                milestones["metabolic_rift_opened"] is None
                and latest is not None
                and latest.overshoot_ratio > 1.0
            ):
                milestones["metabolic_rift_opened"] = tick

            # Event-based phase detection
            for event in current_state.events:
                if (
                    event.event_type == EventType.SUPERWAGE_CRISIS
                    and milestones["superwage_crisis"] is None
                ):
                    milestones["superwage_crisis"] = tick
                elif (
                    event.event_type == EventType.CLASS_DECOMPOSITION
                    and milestones["class_decomposition"] is None
                ):
                    milestones["class_decomposition"] = tick
                elif (
                    event.event_type == EventType.CONTROL_RATIO_CRISIS
                    and milestones["control_ratio_crisis"] is None
                ):
                    milestones["control_ratio_crisis"] = tick
                elif (
                    event.event_type == EventType.TERMINAL_DECISION
                    and milestones["terminal_decision"] is None
                ):
                    milestones["terminal_decision"] = tick

            # Early exit on terminal decision
            if milestones["terminal_decision"] is not None:
                break

        return milestones

    def test_imperial_circuit_initial_state_validity(self) -> None:
        """Verify the imperial circuit initial state is valid.

        The initial state should have:
        - 6 entities: 4 active + 2 dormant carceral (for CLASS_DECOMPOSITION)
        - EXPLOITATION, WAGES, TRIBUTE edges
        - No SOLIDARITY edges (null hypothesis)
        - A territory with biocapacity
        - A GlobalEconomy with rent pool
        """
        state = create_imperial_circuit_state()

        # Verify entities (4 active + 2 dormant)
        assert len(state.entities) == 6, f"Expected 6 entities, got {len(state.entities)}"

        roles = {entity.role for entity in state.entities.values()}
        expected_roles = {
            SocialRole.CORE_BOURGEOISIE,
            SocialRole.LABOR_ARISTOCRACY,
            SocialRole.PERIPHERY_PROLETARIAT,
            SocialRole.COMPRADOR_BOURGEOISIE,
            SocialRole.CARCERAL_ENFORCER,
            SocialRole.INTERNAL_PROLETARIAT,
        }
        assert roles == expected_roles, f"Expected roles {expected_roles}, got {roles}"

        # Verify dormant entities are inactive
        dormant_ids = {"C005", "C006"}
        for entity_id in dormant_ids:
            assert not state.entities[entity_id].active, (
                f"Entity {entity_id} should be dormant (active=False)"
            )

        # Verify no solidarity edges (null hypothesis)
        solidarity_edges = [r for r in state.relationships if r.edge_type.value == "solidarity"]
        assert len(solidarity_edges) == 0, (
            f"Null hypothesis requires NO solidarity edges, found {len(solidarity_edges)}"
        )

        # Verify organization is low (no player intervention)
        for entity in state.entities.values():
            if entity.role in {
                SocialRole.LABOR_ARISTOCRACY,
                SocialRole.PERIPHERY_PROLETARIAT,
            }:
                assert entity.organization < 0.5, (
                    f"Entity {entity.id} ({entity.role}) has organization "
                    f"{entity.organization}, expected < 0.5 for null hypothesis"
                )

        # Verify economy has rent pool
        assert state.economy.imperial_rent_pool > 0, "Economy should start with imperial rent pool"

        # Verify territory exists with biocapacity
        assert len(state.territories) > 0, "Expected at least one territory"
        territory = list(state.territories.values())[0]
        assert territory.biocapacity > 0, "Territory should have biocapacity"

    # =========================================================================
    # Phase Staggering Tests (RED phase TDD)
    # =========================================================================

    def test_phase_spread_minimum_two_years(
        self,
        config: SimulationConfig,
        batch_metrics_collector: MetricsCollector,
    ) -> None:
        """Carceral phases should span at least 2 years of simulation time.

        Imperial collapse is a process, not an instant. The phases represent
        distinct historical moments that unfold over years, not weeks.

        Specifically, the time between SUPERWAGE_CRISIS (first carceral phase)
        and TERMINAL_DECISION (last carceral phase) must be >= 104 ticks.
        """
        milestones = self._run_and_collect_milestones(config, batch_metrics_collector)

        # Get carceral phase ticks (excluding metabolic rift which is pre-carceral)
        carceral_phases = [
            milestones["superwage_crisis"],
            milestones["class_decomposition"],
            milestones["control_ratio_crisis"],
            milestones["terminal_decision"],
        ]

        # Filter out None values (phases that didn't occur)
        occurred_ticks = [t for t in carceral_phases if t is not None]

        # Need at least 2 phases to measure spread
        assert len(occurred_ticks) >= 2, (
            f"Need at least 2 carceral phases to measure spread. Got: {milestones}"
        )

        first_phase = min(occurred_ticks)
        last_phase = max(occurred_ticks)
        spread = last_phase - first_phase

        assert spread >= MIN_PHASE_SPREAD_TICKS, (
            f"Carceral phases should span at least {MIN_PHASE_SPREAD_TICKS} ticks "
            f"({MIN_PHASE_SPREAD_TICKS / TICKS_PER_YEAR:.0f} years), "
            f"got {spread} ticks ({spread / TICKS_PER_YEAR:.1f} years). "
            f"All phases on same tick is unrealistic. "
            f"Milestones: {milestones}"
        )

    def test_each_phase_pair_has_gap(
        self,
        config: SimulationConfig,
        batch_metrics_collector: MetricsCollector,
    ) -> None:
        """Each phase transition must have at least 1 tick gap.

        Even tightly coupled phases (like crisis -> terminal decision) should
        have temporal separation representing social/political response time.

        Phase sequence:
        SUPERWAGE_CRISIS -> CLASS_DECOMPOSITION -> CONTROL_RATIO_CRISIS -> TERMINAL_DECISION
        """
        milestones = self._run_and_collect_milestones(config, batch_metrics_collector)

        # All 4 carceral phases must occur for this test to be meaningful
        required_phases = [
            "superwage_crisis",
            "class_decomposition",
            "control_ratio_crisis",
            "terminal_decision",
        ]
        for phase in required_phases:
            assert milestones[phase] is not None, (
                f"Phase '{phase}' must occur for staggering test. Milestones: {milestones}"
            )

        # Define the canonical phase sequence (carceral phases only)
        phase_sequence = [
            ("superwage_crisis", "class_decomposition"),
            ("class_decomposition", "control_ratio_crisis"),
            ("control_ratio_crisis", "terminal_decision"),
        ]

        for earlier, later in phase_sequence:
            earlier_tick = milestones[earlier]
            later_tick = milestones[later]

            # Both must be non-None at this point (checked above)
            assert earlier_tick is not None and later_tick is not None

            gap = later_tick - earlier_tick

            assert gap >= MIN_PHASE_GAP_TICKS, (
                f"{earlier} -> {later} must have at least {MIN_PHASE_GAP_TICKS} tick gap, "
                f"got {gap} ticks. Phases should not cascade instantly. "
                f"{earlier}={earlier_tick}, {later}={later_tick}"
            )
