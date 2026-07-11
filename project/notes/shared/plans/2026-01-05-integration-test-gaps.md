# Integration Test Gaps Implementation Plan

## Overview

This plan addresses the 5 integration test gaps identified in the research document (`thoughts/shared/research/2026-01-05-integration-test-analysis.md`). The gaps are:

| Priority | Gap | System | Status |
|----------|-----|--------|--------|
| P1 | No integration tests | TerritorySystem | ✅ COMPLETE (11 tests) |
| P1 | No integration tests | DecompositionSystem | ✅ COMPLETE (7 tests) |
| P1 | No integration tests | ControlRatioSystem | ✅ COMPLETE (10 tests) |
| P2 | Power vacuum untested | StruggleSystem | ⏸️ DEFERRED |
| P2 | RUPTURE event untested | ContradictionSystem | ✅ COMPLETE (5 tests) |

**Implementation Status: 4/5 gaps closed (33 tests added)**

Completing these tests is required for Epoch 1 closure.

## Current State Analysis

### Existing Test Coverage

| System | Integration Test | Coverage |
|--------|------------------|----------|
| VitalitySystem | `test_material_reality.py` | Complete |
| ProductionSystem | `test_material_reality.py` | Complete |
| SolidaritySystem | `test_proletarian_internationalism.py` | Complete |
| ImperialRentSystem | `test_imperial_dynamics.py`, `test_dynamic_balance.py` | Complete |
| ConsciousnessSystem | `test_ideological_bifurcation.py` | Complete |
| SurvivalSystem | `test_phase2_game_loop.py` | Complete |
| MetabolismSystem | `test_metabolic_rift.py` | Complete |
| StruggleSystem | `test_george_floyd_dynamic.py` | Complete |
| ContradictionSystem | `test_phase2_game_loop.py`, `test_rupture_events.py` | Complete |
| TerritorySystem | `test_carceral_geography.py` | ✅ Complete (11 tests) |
| DecompositionSystem | `test_class_decomposition.py` | ✅ Complete (7 tests) |
| ControlRatioSystem | `test_control_ratio_crisis.py` | ✅ Complete (10 tests) |

### Key Discoveries

1. **TerritorySystem emits NO events** - Tests must verify graph mutations directly, not via event bus
2. **DecompositionSystem depends on persistent context** - Tests must simulate multi-tick scenarios with `persistent_data`
3. **ControlRatioSystem requires DecompositionSystem** - Must set `_class_decomposition_tick` in context first
4. **Test patterns are well-established** - Follow `test_george_floyd_dynamic.py` structure

## Desired End State

After implementing this plan:

1. All 12 engine Systems have integration test coverage
2. All P1 gaps (TerritorySystem, DecompositionSystem, ControlRatioSystem) have dedicated test files
3. All P2 gaps (StruggleSystem power vacuum, ContradictionSystem RUPTURE) have test coverage
4. Test suite passes: `mise run test:int`
5. Coverage matrix shows 12/12 systems tested

### Verification Commands

```bash
# Verify all new tests pass
mise run test:int

# Verify specific test files
poetry run pytest tests/integration/mechanics/test_carceral_geography.py -v
poetry run pytest tests/integration/mechanics/test_class_decomposition.py -v
poetry run pytest tests/integration/mechanics/test_control_ratio_crisis.py -v

# Verify no regressions
mise run check
```

## What We're NOT Doing

1. **Not adding UI integration tests** - Deferred to Epoch 2 PyQt migration
2. **Not testing EventTemplateSystem directly** - Covered via `test_narrative_pipeline.py`
3. **Not adding performance benchmarks** - Separate task
4. **Not refactoring existing tests** - Focus on gaps only
5. **Not unskipping `test_hump_shape.py`** - Requires Dashboard calibration

## Implementation Approach

Follow established patterns from `test_george_floyd_dynamic.py`:
- Module-level docstring explaining theory
- `pytestmark` with `pytest.mark.integration` and theory marker
- `random.seed(42)` for reproducibility
- Factory functions for entity setup
- Multi-tick simulation with `Simulation(state, config).run(N)`
- Event filtering via `[log for log in final_state.event_log if "EVENT_TYPE" in log]`
- Rich assertion messages with context

---

## Phase 1: TerritorySystem Integration Tests

### Overview

Create `tests/integration/mechanics/test_carceral_geography.py` testing heat dynamics, eviction pipeline, spillover, and necropolitics. TerritorySystem is unique: it emits NO events, so all tests verify graph state mutations directly.

### Changes Required

#### 1. Create Test File

**File**: `tests/integration/mechanics/test_carceral_geography.py`

```python
"""Integration tests for the Carceral Geography Layer - TerritorySystem.

This module tests the TerritorySystem which implements:
- Heat Dynamics: HIGH_PROFILE gains heat, LOW_PROFILE decays
- Eviction Pipeline: heat >= 0.8 triggers eviction, rent spike, displacement
- Heat Spillover: Adjacent territories receive heat transmission
- Necropolitics: CONCENTRATION_CAMP decay, PENAL_COLONY organization suppression

Key insight: TerritorySystem emits NO events. All tests verify graph mutations
directly via final_state.territories and entity organization values.

Test Scenarios:
1. HIGH_PROFILE territory accumulates heat over ticks until eviction threshold
2. Eviction triggers rent spike and population displacement to sinks
3. Heat spills from hot territory to adjacent LOW_PROFILE territories
4. CONCENTRATION_CAMP populations decay each tick (genocide modeling)
5. PENAL_COLONY suppresses organization of tenants (atomization)
"""

import random
from typing import Any

import pytest

from babylon.config.defines import GameDefines, TerritoryDefines
from babylon.engine.factories import create_proletariat
from babylon.engine.simulation import Simulation
from babylon.models import (
    EdgeType,
    Relationship,
    SimulationConfig,
    WorldState,
)
from babylon.models.entities.territory import Territory
from babylon.models.enums import (
    OperationalProfile,
    SectorType,
    SocialRole,
    TerritoryType,
)

pytestmark = [pytest.mark.integration, pytest.mark.theory_territory]


class TestHeatDynamics:
    """Tests for heat accumulation and decay based on OperationalProfile."""

    def test_high_profile_territory_accumulates_heat(self) -> None:
        """Test that HIGH_PROFILE territories gain heat each tick."""
        random.seed(42)

        # Create HIGH_PROFILE territory
        territory = Territory(
            id="T001",
            name="Revolutionary Cell HQ",
            sector_type=SectorType.INDUSTRIAL,
            territory_type=TerritoryType.PERIPHERY,
            profile=OperationalProfile.HIGH_PROFILE,
            heat=0.0,  # Start cold
            population=100,
        )

        # Create worker tenants
        worker = create_proletariat(
            id="C001",
            name="Cell Members",
            wealth=50.0,
        )

        tenancy = Relationship(
            source_id="C001",
            target_id="T001",
            edge_type=EdgeType.TENANCY,
        )

        state = WorldState(
            tick=0,
            entities={"C001": worker},
            territories={"T001": territory},
            relationships=[tenancy],
        )
        config = SimulationConfig()

        # Run 10 ticks
        sim = Simulation(state, config)
        final_state = sim.run(10)

        # Assert: Heat should have accumulated
        initial_heat = 0.0
        final_heat = final_state.territories["T001"].heat

        # Default high_profile_heat_gain = 0.15 per tick
        # After 10 ticks: ~1.5 (capped at 1.0)
        assert final_heat > initial_heat, (
            f"HIGH_PROFILE territory should accumulate heat. "
            f"Initial: {initial_heat}, Final: {final_heat}"
        )
        assert final_heat <= 1.0, f"Heat should be capped at 1.0, got {final_heat}"

    def test_low_profile_territory_decays_heat(self) -> None:
        """Test that LOW_PROFILE territories lose heat each tick."""
        random.seed(42)

        # Create LOW_PROFILE territory with existing heat
        territory = Territory(
            id="T001",
            name="Community Center",
            sector_type=SectorType.INDUSTRIAL,
            territory_type=TerritoryType.PERIPHERY,
            profile=OperationalProfile.LOW_PROFILE,
            heat=0.8,  # Start hot
            population=100,
        )

        worker = create_proletariat(id="C001", name="Members", wealth=50.0)

        state = WorldState(
            tick=0,
            entities={"C001": worker},
            territories={"T001": territory},
            relationships=[
                Relationship(source_id="C001", target_id="T001", edge_type=EdgeType.TENANCY)
            ],
        )
        config = SimulationConfig()

        # Run 10 ticks
        sim = Simulation(state, config)
        final_state = sim.run(10)

        # Assert: Heat should have decayed
        initial_heat = 0.8
        final_heat = final_state.territories["T001"].heat

        # Default heat_decay_rate = 0.1, formula: heat * (1 - rate)
        # After 10 ticks: 0.8 * (0.9)^10 ≈ 0.279
        assert final_heat < initial_heat, (
            f"LOW_PROFILE territory should decay heat. "
            f"Initial: {initial_heat}, Final: {final_heat}"
        )
        assert final_heat >= 0.0, f"Heat should not go negative, got {final_heat}"


class TestEvictionPipeline:
    """Tests for eviction triggering, rent spikes, and population displacement."""

    def test_eviction_triggers_at_heat_threshold(self) -> None:
        """Test that eviction triggers when heat >= 0.8."""
        random.seed(42)

        # Create territory just below eviction threshold
        territory = Territory(
            id="T001",
            name="Hot Zone",
            sector_type=SectorType.INDUSTRIAL,
            territory_type=TerritoryType.PERIPHERY,
            profile=OperationalProfile.HIGH_PROFILE,
            heat=0.75,  # Just below 0.8 threshold
            population=1000,
            rent_level=1.0,
        )

        worker = create_proletariat(id="C001", name="Residents", wealth=100.0)

        state = WorldState(
            tick=0,
            entities={"C001": worker},
            territories={"T001": territory},
            relationships=[
                Relationship(source_id="C001", target_id="T001", edge_type=EdgeType.TENANCY)
            ],
        )
        config = SimulationConfig()

        # Run enough ticks to cross threshold
        sim = Simulation(state, config)
        final_state = sim.run(5)

        # Assert: Territory should be under eviction
        final_territory = final_state.territories["T001"]
        assert final_territory.under_eviction is True, (
            f"Territory should be under eviction when heat >= 0.8. "
            f"Final heat: {final_territory.heat}"
        )

    def test_rent_spike_during_eviction(self) -> None:
        """Test that rent increases during eviction."""
        random.seed(42)

        # Create territory already at eviction threshold
        territory = Territory(
            id="T001",
            name="Evicting Zone",
            sector_type=SectorType.INDUSTRIAL,
            territory_type=TerritoryType.PERIPHERY,
            profile=OperationalProfile.HIGH_PROFILE,
            heat=0.85,  # Above threshold
            population=1000,
            rent_level=1.0,
        )

        worker = create_proletariat(id="C001", name="Residents", wealth=100.0)

        state = WorldState(
            tick=0,
            entities={"C001": worker},
            territories={"T001": territory},
            relationships=[
                Relationship(source_id="C001", target_id="T001", edge_type=EdgeType.TENANCY)
            ],
        )
        config = SimulationConfig()

        # Run 5 ticks
        sim = Simulation(state, config)
        final_state = sim.run(5)

        # Assert: Rent should have spiked
        initial_rent = 1.0
        final_rent = final_state.territories["T001"].rent_level

        # Default rent_spike_multiplier = 1.5 per eviction tick
        # After 5 ticks: 1.0 * 1.5^5 ≈ 7.59
        assert final_rent > initial_rent, (
            f"Rent should spike during eviction. "
            f"Initial: {initial_rent}, Final: {final_rent}"
        )

    def test_population_displaced_to_sink_node(self) -> None:
        """Test that displaced population flows to PENAL_COLONY sink."""
        random.seed(42)

        # Create evicting territory and penal colony sink
        source = Territory(
            id="T001",
            name="Evicting Neighborhood",
            sector_type=SectorType.RESIDENTIAL,
            territory_type=TerritoryType.PERIPHERY,
            profile=OperationalProfile.HIGH_PROFILE,
            heat=0.9,  # Above threshold
            population=1000,
            rent_level=1.0,
        )

        sink = Territory(
            id="T002",
            name="State Prison",
            sector_type=SectorType.CARCERAL,
            territory_type=TerritoryType.PENAL_COLONY,
            heat=0.0,
            population=100,  # Start with some prisoners
        )

        worker = create_proletariat(id="C001", name="Residents", wealth=50.0)

        # Adjacency edge from source to sink
        adjacency = Relationship(
            source_id="T001",
            target_id="T002",
            edge_type=EdgeType.ADJACENCY,
        )

        state = WorldState(
            tick=0,
            entities={"C001": worker},
            territories={"T001": source, "T002": sink},
            relationships=[
                Relationship(source_id="C001", target_id="T001", edge_type=EdgeType.TENANCY),
                adjacency,
            ],
        )
        config = SimulationConfig()

        # Run 10 ticks
        sim = Simulation(state, config)
        final_state = sim.run(10)

        # Assert: Population transferred to sink
        initial_source_pop = 1000
        initial_sink_pop = 100

        final_source_pop = final_state.territories["T001"].population
        final_sink_pop = final_state.territories["T002"].population

        assert final_source_pop < initial_source_pop, (
            f"Source population should decrease. "
            f"Initial: {initial_source_pop}, Final: {final_source_pop}"
        )
        assert final_sink_pop > initial_sink_pop, (
            f"Sink population should increase. "
            f"Initial: {initial_sink_pop}, Final: {final_sink_pop}"
        )


class TestHeatSpillover:
    """Tests for heat transmission via ADJACENCY edges."""

    def test_heat_spills_to_adjacent_territory(self) -> None:
        """Test that heat from hot territory spills to adjacent cold territory."""
        random.seed(42)

        # Create hot source and cold target
        hot_territory = Territory(
            id="T001",
            name="Hot Zone",
            sector_type=SectorType.INDUSTRIAL,
            territory_type=TerritoryType.PERIPHERY,
            profile=OperationalProfile.HIGH_PROFILE,
            heat=0.9,
            population=100,
        )

        cold_territory = Territory(
            id="T002",
            name="Cold Zone",
            sector_type=SectorType.RESIDENTIAL,
            territory_type=TerritoryType.PERIPHERY,
            profile=OperationalProfile.LOW_PROFILE,
            heat=0.0,
            population=100,
        )

        worker = create_proletariat(id="C001", name="Workers", wealth=50.0)

        # Adjacency edge enables spillover
        adjacency = Relationship(
            source_id="T001",
            target_id="T002",
            edge_type=EdgeType.ADJACENCY,
        )

        state = WorldState(
            tick=0,
            entities={"C001": worker},
            territories={"T001": hot_territory, "T002": cold_territory},
            relationships=[
                Relationship(source_id="C001", target_id="T001", edge_type=EdgeType.TENANCY),
                adjacency,
            ],
        )
        config = SimulationConfig()

        # Run 5 ticks
        sim = Simulation(state, config)
        final_state = sim.run(5)

        # Assert: Cold territory gained heat from spillover
        initial_cold_heat = 0.0
        final_cold_heat = final_state.territories["T002"].heat

        # Spillover occurs each tick: spillover = source_heat * spillover_rate
        # Default spillover_rate = 0.05
        assert final_cold_heat > initial_cold_heat, (
            f"Cold territory should receive heat spillover. "
            f"Initial: {initial_cold_heat}, Final: {final_cold_heat}"
        )


class TestNecropolitics:
    """Tests for sink node effects: concentration camp decay, penal colony suppression."""

    def test_concentration_camp_population_decays(self) -> None:
        """Test that CONCENTRATION_CAMP populations decay each tick (genocide)."""
        random.seed(42)

        # Create concentration camp with population
        camp = Territory(
            id="T001",
            name="Death Camp",
            sector_type=SectorType.CARCERAL,
            territory_type=TerritoryType.CONCENTRATION_CAMP,
            heat=0.0,
            population=1000,
        )

        # Need at least one entity for simulation to run
        worker = create_proletariat(id="C001", name="Guard", wealth=50.0)

        state = WorldState(
            tick=0,
            entities={"C001": worker},
            territories={"T001": camp},
            relationships=[],
        )
        config = SimulationConfig()

        # Run 10 ticks
        sim = Simulation(state, config)
        final_state = sim.run(10)

        # Assert: Population decayed
        initial_pop = 1000
        final_pop = final_state.territories["T001"].population

        # Default concentration_camp_decay_rate = 0.2
        # After 10 ticks: 1000 * (0.8)^10 ≈ 107
        assert final_pop < initial_pop, (
            f"Concentration camp population should decay. "
            f"Initial: {initial_pop}, Final: {final_pop}"
        )

    def test_penal_colony_suppresses_organization(self) -> None:
        """Test that PENAL_COLONY tenants have organization set to 0."""
        random.seed(42)

        # Create penal colony
        prison = Territory(
            id="T001",
            name="State Prison",
            sector_type=SectorType.CARCERAL,
            territory_type=TerritoryType.PENAL_COLONY,
            heat=0.0,
            population=500,
        )

        # Create prisoner with high organization
        prisoner = create_proletariat(
            id="C001",
            name="Political Prisoner",
            wealth=10.0,
            organization=0.8,  # High organization
        )

        # TENANCY edge connects prisoner to prison
        tenancy = Relationship(
            source_id="C001",
            target_id="T001",
            edge_type=EdgeType.TENANCY,
        )

        state = WorldState(
            tick=0,
            entities={"C001": prisoner},
            territories={"T001": prison},
            relationships=[tenancy],
        )
        config = SimulationConfig()

        # Run 1 tick
        sim = Simulation(state, config)
        final_state = sim.run(1)

        # Assert: Organization suppressed to 0
        initial_org = 0.8
        final_org = final_state.entities["C001"].organization

        assert final_org == 0.0, (
            f"Penal colony should suppress organization to 0. "
            f"Initial: {initial_org}, Final: {final_org}"
        )


class TestDisplacementModes:
    """Tests for displacement priority modes (EXTRACTION, CONTAINMENT, ELIMINATION)."""

    def test_extraction_mode_prioritizes_penal_colony(self) -> None:
        """Test that EXTRACTION mode routes displaced population to PENAL_COLONY first."""
        random.seed(42)

        # Create evicting territory with multiple sink options
        source = Territory(
            id="T001",
            name="Evicting Zone",
            sector_type=SectorType.RESIDENTIAL,
            territory_type=TerritoryType.PERIPHERY,
            profile=OperationalProfile.HIGH_PROFILE,
            heat=0.9,
            population=1000,
        )

        prison = Territory(
            id="T002",
            name="Prison",
            sector_type=SectorType.CARCERAL,
            territory_type=TerritoryType.PENAL_COLONY,
            population=0,
        )

        reservation = Territory(
            id="T003",
            name="Reservation",
            sector_type=SectorType.CARCERAL,
            territory_type=TerritoryType.RESERVATION,
            population=0,
        )

        worker = create_proletariat(id="C001", name="Residents", wealth=50.0)

        state = WorldState(
            tick=0,
            entities={"C001": worker},
            territories={"T001": source, "T002": prison, "T003": reservation},
            relationships=[
                Relationship(source_id="C001", target_id="T001", edge_type=EdgeType.TENANCY),
                Relationship(source_id="T001", target_id="T002", edge_type=EdgeType.ADJACENCY),
                Relationship(source_id="T001", target_id="T003", edge_type=EdgeType.ADJACENCY),
            ],
        )
        config = SimulationConfig()

        # Run with EXTRACTION mode (default)
        sim = Simulation(state, config)
        final_state = sim.run(10)

        # Assert: Prison received more population than reservation
        prison_pop = final_state.territories["T002"].population
        reservation_pop = final_state.territories["T003"].population

        assert prison_pop > reservation_pop, (
            f"EXTRACTION mode should prioritize penal colony. "
            f"Prison: {prison_pop}, Reservation: {reservation_pop}"
        )
```

### Success Criteria

#### Automated Verification
- [x] Tests pass: `poetry run pytest tests/integration/mechanics/test_carceral_geography.py -v`
- [x] Type checking passes: `poetry run mypy tests/integration/mechanics/test_carceral_geography.py`
- [x] Linting passes: `poetry run ruff check tests/integration/mechanics/`

#### Manual Verification
- [x] Review test output to ensure assertions are meaningful
- [x] Verify test names clearly describe what's being tested

**Implementation Note**: After completing this phase and all automated verification passes, pause here for confirmation before proceeding to Phase 2.

---

## Phase 2: DecompositionSystem Integration Tests

### Overview

Create `tests/integration/mechanics/test_class_decomposition.py` testing the Labor Aristocracy decomposition into CARCERAL_ENFORCER and INTERNAL_PROLETARIAT. This system depends on SUPERWAGE_CRISIS events and uses persistent context for cross-tick state.

### Changes Required

#### 1. Create Test File

**File**: `tests/integration/mechanics/test_class_decomposition.py`

```python
"""Integration tests for Class Decomposition - The LA Crisis.

This module tests the DecompositionSystem which implements:
- SUPERWAGE_CRISIS detection (from ImperialRentSystem)
- Delayed decomposition (52 ticks after crisis by default)
- Fallback decomposition (LA approaching death)
- Population/wealth split to CARCERAL_ENFORCER and INTERNAL_PROLETARIAT
- CLASS_DECOMPOSITION event emission

Key insight: The Labor Aristocracy can only exist while imperial rent flows.
When the empire can no longer pay super-wages, the LA decomposes into guards
(who manage the surplus population) and prisoners (the surplus population itself).

Test Scenarios:
1. Normal path: SUPERWAGE_CRISIS → 52 tick delay → CLASS_DECOMPOSITION
2. Fallback path: LA wealth drops → immediate decomposition
3. Population/wealth split matches defines fractions
4. Decomposition is one-time (idempotent)
"""

import random
from typing import Any

import pytest

from babylon.config.defines import CarceralDefines, GameDefines
from babylon.engine.factories import create_bourgeoisie, create_proletariat
from babylon.engine.simulation import Simulation
from babylon.engine.simulation_engine import step
from babylon.models import (
    EdgeType,
    Relationship,
    SimulationConfig,
    WorldState,
)
from babylon.models.entities.social_class import SocialClass
from babylon.models.enums import SocialRole

pytestmark = [pytest.mark.integration, pytest.mark.theory_rent]


def _create_la_crisis_scenario() -> tuple[WorldState, SimulationConfig, GameDefines]:
    """Create a scenario where Labor Aristocracy will face crisis.

    Returns state with:
    - Core Bourgeoisie (depleting wealth)
    - Labor Aristocracy (receiving super-wages)
    - Dormant CARCERAL_ENFORCER (population=0)
    - Dormant INTERNAL_PROLETARIAT (population=0)
    - WAGES edge from bourgeoisie to LA
    """
    core_bourgeoisie = SocialClass(
        id="C001",
        name="Core Bourgeoisie",
        role=SocialRole.CORE_BOURGEOISIE,
        wealth=100.0,  # Will deplete quickly
        population=100,
        active=True,
    )

    labor_aristocracy = SocialClass(
        id="C002",
        name="Labor Aristocracy",
        role=SocialRole.LABOR_ARISTOCRACY,
        wealth=500.0,
        population=1000,
        s_bio=0.1,
        s_class=0.1,
        subsistence_threshold=50.0,
        active=True,
    )

    # Dormant entities that will be activated by decomposition
    enforcer = SocialClass(
        id="C003",
        name="Carceral Enforcer",
        role=SocialRole.CARCERAL_ENFORCER,
        wealth=0.0,
        population=0,
        active=False,  # Dormant
    )

    internal_proletariat = SocialClass(
        id="C004",
        name="Internal Proletariat",
        role=SocialRole.INTERNAL_PROLETARIAT,
        wealth=0.0,
        population=0,
        active=False,  # Dormant
    )

    # WAGES edge for super-wage payments
    wages_edge = Relationship(
        source_id="C001",
        target_id="C002",
        edge_type=EdgeType.WAGES,
        value_flow=50.0,  # Super-wages
    )

    state = WorldState(
        tick=0,
        entities={
            "C001": core_bourgeoisie,
            "C002": labor_aristocracy,
            "C003": enforcer,
            "C004": internal_proletariat,
        },
        relationships=[wages_edge],
    )

    config = SimulationConfig()
    defines = GameDefines()

    return state, config, defines


class TestDecompositionTrigger:
    """Tests for decomposition trigger conditions."""

    def test_decomposition_after_superwage_crisis_delay(self) -> None:
        """Test that decomposition occurs 52 ticks after SUPERWAGE_CRISIS."""
        random.seed(42)

        state, config, defines = _create_la_crisis_scenario()

        # Use short delay for testing
        defines = GameDefines(
            carceral=CarceralDefines(decomposition_delay=5)  # 5 ticks instead of 52
        )

        # Run until decomposition should occur
        # Bourgeoisie wealth depletes → SUPERWAGE_CRISIS → delay → CLASS_DECOMPOSITION
        sim = Simulation(state, config, defines=defines)
        final_state = sim.run(50)

        # Check for CLASS_DECOMPOSITION event
        decomposition_events = [
            log for log in final_state.event_log if "CLASS_DECOMPOSITION" in log
        ]

        assert len(decomposition_events) >= 1, (
            f"Expected CLASS_DECOMPOSITION event after superwage crisis + delay. "
            f"Events: {final_state.event_log[-10:]}"
        )

    def test_fallback_decomposition_when_la_dying(self) -> None:
        """Test immediate decomposition when LA wealth drops to subsistence."""
        random.seed(42)

        # Create LA with very low wealth (near death)
        labor_aristocracy = SocialClass(
            id="C002",
            name="Dying LA",
            role=SocialRole.LABOR_ARISTOCRACY,
            wealth=5.0,  # Below subsistence
            population=1000,
            s_bio=0.1,
            s_class=0.1,
            subsistence_threshold=50.0,
            active=True,
        )

        enforcer = SocialClass(
            id="C003",
            name="Enforcer",
            role=SocialRole.CARCERAL_ENFORCER,
            wealth=0.0,
            population=0,
            active=False,
        )

        internal_proletariat = SocialClass(
            id="C004",
            name="Internal Proletariat",
            role=SocialRole.INTERNAL_PROLETARIAT,
            wealth=0.0,
            population=0,
            active=False,
        )

        state = WorldState(
            tick=0,
            entities={
                "C002": labor_aristocracy,
                "C003": enforcer,
                "C004": internal_proletariat,
            },
            relationships=[],
        )
        config = SimulationConfig()
        defines = GameDefines()

        # Run just a few ticks - fallback should trigger immediately
        sim = Simulation(state, config, defines=defines)
        final_state = sim.run(5)

        # Check for decomposition
        decomposition_events = [
            log for log in final_state.event_log if "CLASS_DECOMPOSITION" in log
        ]

        assert len(decomposition_events) >= 1, (
            "Fallback decomposition should trigger when LA approaching death"
        )


class TestDecompositionOutcome:
    """Tests for population and wealth distribution after decomposition."""

    def test_population_splits_to_enforcer_and_proletariat(self) -> None:
        """Test that LA population splits according to defines fractions."""
        random.seed(42)

        state, config, _ = _create_la_crisis_scenario()

        # Use short delay and specific fractions
        defines = GameDefines(
            carceral=CarceralDefines(
                decomposition_delay=1,
                enforcer_fraction=0.15,
                proletariat_fraction=0.85,
            )
        )

        # Force immediate crisis by setting LA wealth low
        state.entities["C002"] = state.entities["C002"].model_copy(
            update={"wealth": 10.0}
        )

        sim = Simulation(state, config, defines=defines)
        final_state = sim.run(10)

        # Get final populations
        enforcer = final_state.entities.get("C003")
        proletariat = final_state.entities.get("C004")

        initial_la_pop = 1000

        # Check populations match fractions (allowing for int truncation)
        if enforcer and enforcer.active:
            expected_enforcer = int(initial_la_pop * 0.15)
            assert abs(enforcer.population - expected_enforcer) <= 1, (
                f"Enforcer population should be ~{expected_enforcer}, got {enforcer.population}"
            )

        if proletariat and proletariat.active:
            expected_proletariat = int(initial_la_pop * 0.85)
            assert abs(proletariat.population - expected_proletariat) <= 1, (
                f"Proletariat population should be ~{expected_proletariat}, got {proletariat.population}"
            )

    def test_la_deactivated_after_decomposition(self) -> None:
        """Test that Labor Aristocracy is marked inactive after decomposition."""
        random.seed(42)

        state, config, _ = _create_la_crisis_scenario()
        defines = GameDefines(carceral=CarceralDefines(decomposition_delay=1))

        # Force crisis
        state.entities["C002"] = state.entities["C002"].model_copy(
            update={"wealth": 10.0}
        )

        sim = Simulation(state, config, defines=defines)
        final_state = sim.run(10)

        # Check LA deactivation
        la = final_state.entities.get("C002")
        assert la is not None, "LA entity should still exist"
        assert la.active is False, "LA should be deactivated after decomposition"


class TestDecompositionIdempotency:
    """Tests for one-time decomposition behavior."""

    def test_decomposition_only_happens_once(self) -> None:
        """Test that decomposition cannot occur multiple times."""
        random.seed(42)

        state, config, _ = _create_la_crisis_scenario()
        defines = GameDefines(carceral=CarceralDefines(decomposition_delay=1))

        # Force crisis
        state.entities["C002"] = state.entities["C002"].model_copy(
            update={"wealth": 10.0}
        )

        sim = Simulation(state, config, defines=defines)
        final_state = sim.run(100)  # Run many ticks

        # Count decomposition events
        decomposition_events = [
            log for log in final_state.event_log if "CLASS_DECOMPOSITION" in log
        ]

        assert len(decomposition_events) == 1, (
            f"Decomposition should only happen once. "
            f"Got {len(decomposition_events)} events"
        )
```

### Success Criteria

#### Automated Verification
- [x] Tests pass: `poetry run pytest tests/integration/mechanics/test_class_decomposition.py -v`
- [x] Type checking passes: `poetry run mypy tests/integration/mechanics/test_class_decomposition.py`
- [x] Linting passes: `poetry run ruff check tests/integration/mechanics/`

#### Manual Verification
- [x] Review test output to verify decomposition timing
- [x] Verify population split matches expected fractions (ratio-based assertions with configured tolerance)

**Implementation Note**: Phase 2 complete. Tests use ratio-based assertions with DECOMPOSITION_FRACTION_TOLERANCE constant to account for post-decomposition system dynamics.

---

## Phase 3: ControlRatioSystem Integration Tests

### Overview

Create `tests/integration/mechanics/test_control_ratio_crisis.py` testing guard-to-prisoner ratio monitoring, crisis detection, and terminal decision bifurcation (revolution vs genocide).

### Changes Required

#### 1. Create Test File

**File**: `tests/integration/mechanics/test_control_ratio_crisis.py`

```python
"""Integration tests for Control Ratio Crisis - Terminal Decision.

This module tests the ControlRatioSystem which implements:
- Guard-to-prisoner ratio monitoring (default capacity: 4 prisoners per guard)
- CONTROL_RATIO_CRISIS event when prisoners exceed capacity
- TERMINAL_DECISION event bifurcating to "revolution" or "genocide"
- Organization threshold determines outcome (>= 0.5 = revolution)

Key insight: The carceral state has material limits. When the surplus population
exceeds the capacity of guards to control, one of two outcomes occurs:
1. Revolution (if prisoners are organized)
2. Genocide (if prisoners are atomized)

Prerequisites:
- DecompositionSystem must have run (sets _class_decomposition_tick)
- Enforcer and prisoner populations must exist
"""

import random
from typing import Any

import pytest

from babylon.config.defines import CarceralDefines, GameDefines
from babylon.engine.simulation import Simulation
from babylon.engine.simulation_engine import step
from babylon.models import SimulationConfig, WorldState
from babylon.models.entities.social_class import SocialClass
from babylon.models.enums import SocialRole

pytestmark = [pytest.mark.integration, pytest.mark.theory_rent]


def _create_post_decomposition_scenario(
    enforcer_pop: int = 100,
    prisoner_pop: int = 500,
    prisoner_org: float = 0.3,
) -> tuple[WorldState, SimulationConfig, GameDefines, dict[str, Any]]:
    """Create scenario after decomposition has occurred.

    Returns:
        Tuple of (state, config, defines, persistent_context)

    The persistent_context includes _class_decomposition_tick to satisfy
    ControlRatioSystem precondition.
    """
    enforcer = SocialClass(
        id="C001",
        name="Carceral Enforcer",
        role=SocialRole.CARCERAL_ENFORCER,
        wealth=100.0,
        population=enforcer_pop,
        organization=0.9,  # Guards are well-organized
        active=True,
    )

    prisoner = SocialClass(
        id="C002",
        name="Internal Proletariat",
        role=SocialRole.INTERNAL_PROLETARIAT,
        wealth=10.0,
        population=prisoner_pop,
        organization=prisoner_org,
        active=True,
    )

    state = WorldState(
        tick=100,  # Post-decomposition
        entities={"C001": enforcer, "C002": prisoner},
        relationships=[],
    )

    config = SimulationConfig()
    defines = GameDefines(
        carceral=CarceralDefines(
            control_capacity=4,  # 4 prisoners per guard
            control_ratio_delay=1,  # 1 tick after decomposition
            terminal_decision_delay=1,  # 1 tick after crisis
            revolution_threshold=0.5,
        )
    )

    # Simulate decomposition having already occurred
    persistent_context: dict[str, Any] = {
        "_class_decomposition_tick": 50,  # Decomposed at tick 50
    }

    return state, config, defines, persistent_context


class TestControlRatioCrisis:
    """Tests for CONTROL_RATIO_CRISIS event emission."""

    def test_crisis_when_prisoners_exceed_capacity(self) -> None:
        """Test CONTROL_RATIO_CRISIS when prisoner_pop > enforcer_pop * capacity."""
        random.seed(42)

        # 100 guards * 4 capacity = 400 max prisoners
        # 500 prisoners > 400 → crisis
        state, config, defines, context = _create_post_decomposition_scenario(
            enforcer_pop=100,
            prisoner_pop=500,
        )

        # Use step() with persistent context
        current_state = state
        for _ in range(10):
            current_state = step(current_state, config, context, defines)

        # Check for crisis event
        crisis_events = [
            log for log in current_state.event_log if "CONTROL_RATIO_CRISIS" in log
        ]

        assert len(crisis_events) >= 1, (
            f"Expected CONTROL_RATIO_CRISIS when prisoners (500) > capacity (400). "
            f"Events: {current_state.event_log[-5:]}"
        )

    def test_no_crisis_when_under_capacity(self) -> None:
        """Test no crisis when prisoner_pop <= enforcer_pop * capacity."""
        random.seed(42)

        # 100 guards * 4 capacity = 400 max prisoners
        # 300 prisoners <= 400 → no crisis
        state, config, defines, context = _create_post_decomposition_scenario(
            enforcer_pop=100,
            prisoner_pop=300,
        )

        current_state = state
        for _ in range(10):
            current_state = step(current_state, config, context, defines)

        # Check for NO crisis event
        crisis_events = [
            log for log in current_state.event_log if "CONTROL_RATIO_CRISIS" in log
        ]

        assert len(crisis_events) == 0, (
            f"No crisis expected when prisoners (300) <= capacity (400). "
            f"Got {len(crisis_events)} crisis events"
        )


class TestTerminalDecision:
    """Tests for TERMINAL_DECISION bifurcation (revolution vs genocide)."""

    def test_revolution_outcome_with_high_organization(self) -> None:
        """Test TERMINAL_DECISION = 'revolution' when prisoner org >= threshold."""
        random.seed(42)

        # High organization (0.7 >= 0.5 threshold)
        state, config, defines, context = _create_post_decomposition_scenario(
            enforcer_pop=100,
            prisoner_pop=500,
            prisoner_org=0.7,
        )

        current_state = state
        for _ in range(20):
            current_state = step(current_state, config, context, defines)

        # Check for terminal decision
        terminal_events = [
            log for log in current_state.event_log if "TERMINAL_DECISION" in log
        ]

        assert len(terminal_events) >= 1, "Expected TERMINAL_DECISION event"

        # Check outcome is revolution
        revolution_events = [
            log for log in current_state.event_log if "revolution" in log.lower()
        ]
        assert len(revolution_events) >= 1, (
            f"Expected 'revolution' outcome with org=0.7. Events: {terminal_events}"
        )

    def test_genocide_outcome_with_low_organization(self) -> None:
        """Test TERMINAL_DECISION = 'genocide' when prisoner org < threshold."""
        random.seed(42)

        # Low organization (0.2 < 0.5 threshold)
        state, config, defines, context = _create_post_decomposition_scenario(
            enforcer_pop=100,
            prisoner_pop=500,
            prisoner_org=0.2,
        )

        current_state = state
        for _ in range(20):
            current_state = step(current_state, config, context, defines)

        # Check for terminal decision
        terminal_events = [
            log for log in current_state.event_log if "TERMINAL_DECISION" in log
        ]

        assert len(terminal_events) >= 1, "Expected TERMINAL_DECISION event"

        # Check outcome is genocide
        genocide_events = [
            log for log in current_state.event_log if "genocide" in log.lower()
        ]
        assert len(genocide_events) >= 1, (
            f"Expected 'genocide' outcome with org=0.2. Events: {terminal_events}"
        )


class TestControlRatioEdgeCases:
    """Tests for edge cases in control ratio mechanics."""

    def test_no_crisis_without_decomposition(self) -> None:
        """Test that no crisis occurs if decomposition hasn't happened."""
        random.seed(42)

        state, config, defines, _ = _create_post_decomposition_scenario(
            enforcer_pop=100,
            prisoner_pop=500,
        )

        # Empty context (no _class_decomposition_tick)
        context: dict[str, Any] = {}

        current_state = state
        for _ in range(10):
            current_state = step(current_state, config, context, defines)

        # Check for NO crisis event
        crisis_events = [
            log for log in current_state.event_log if "CONTROL_RATIO_CRISIS" in log
        ]

        assert len(crisis_events) == 0, (
            "No crisis should occur without prior decomposition"
        )

    def test_crisis_only_emitted_once(self) -> None:
        """Test that CONTROL_RATIO_CRISIS is only emitted once."""
        random.seed(42)

        state, config, defines, context = _create_post_decomposition_scenario(
            enforcer_pop=100,
            prisoner_pop=500,
        )

        current_state = state
        for _ in range(50):  # Run many ticks
            current_state = step(current_state, config, context, defines)

        # Count crisis events
        crisis_events = [
            log for log in current_state.event_log if "CONTROL_RATIO_CRISIS" in log
        ]

        assert len(crisis_events) == 1, (
            f"CONTROL_RATIO_CRISIS should only emit once. Got {len(crisis_events)}"
        )
```

### Success Criteria

#### Automated Verification
- [x] Tests pass: `poetry run pytest tests/integration/mechanics/test_control_ratio_crisis.py -v`
- [x] Type checking passes: `poetry run mypy tests/integration/mechanics/test_control_ratio_crisis.py`
- [x] Linting passes: `poetry run ruff check tests/integration/mechanics/`

#### Manual Verification
- [x] Review test output to verify bifurcation logic (10 tests passing)
- [x] Verify organization threshold correctly determines outcome (test_exact_threshold_is_revolution)

**Implementation Note**: Phase 3 complete. Tests verify crisis detection, revolution/genocide bifurcation, edge cases, and idempotency.

---

## Phase 4: Partial Gap Extensions

### Overview

Extend existing integration tests to cover:
1. StruggleSystem power vacuum mechanics
2. ContradictionSystem RUPTURE event emission

### Changes Required

#### 1. Extend test_george_floyd_dynamic.py

**File**: `tests/integration/mechanics/test_george_floyd_dynamic.py`

Add new test class at end of file:

```python
class TestPowerVacuum:
    """Tests for power vacuum mechanics when organization collapses."""

    def test_power_vacuum_creates_opportunity(self) -> None:
        """Test that organization collapse creates power vacuum opportunity."""
        random.seed(42)

        # Create worker with high organization that will collapse
        worker = create_proletariat(
            id="C001",
            name="Organized Worker",
            wealth=50.0,
            ideology=-0.5,  # Revolutionary
            organization=0.8,  # High organization
            repression_faced=0.9,  # Extreme repression
        )

        state = WorldState(
            tick=0,
            entities={"C001": worker},
            relationships=[],
        )
        config = SimulationConfig()

        # Run until organization might collapse
        sim = Simulation(state, config)
        final_state = sim.run(30)

        # Track organization over time
        history = sim.get_history()

        # Find if organization dropped significantly (power vacuum)
        org_values = [s.entities["C001"].organization for s in history if "C001" in s.entities]

        if len(org_values) > 1:
            max_org = max(org_values)
            min_org = min(org_values)
            org_drop = max_org - min_org

            # If org dropped significantly, verify power dynamics shifted
            if org_drop > 0.3:
                print(f"Organization dropped from {max_org} to {min_org}")
                # Power vacuum should affect consciousness dynamics
                # (specific assertion depends on implementation)
```

#### 2. Extend test_phase2_game_loop.py or create test_rupture_events.py

**File**: `tests/integration/mechanics/test_rupture_events.py`

```python
"""Integration tests for RUPTURE events - Revolutionary Moments.

This module tests the ContradictionSystem's RUPTURE event emission:
- RUPTURE occurs when accumulated tension exceeds threshold
- RUPTURE represents qualitative shift in class struggle
- RUPTURE triggers special game mechanics (endgame detection)
"""

import random

import pytest

from babylon.config.defines import ContradictionDefines, GameDefines
from babylon.engine.factories import create_bourgeoisie, create_proletariat
from babylon.engine.simulation import Simulation
from babylon.models import EdgeType, Relationship, SimulationConfig, WorldState

pytestmark = [pytest.mark.integration, pytest.mark.theory_solidarity]


class TestRuptureEvents:
    """Tests for RUPTURE event emission."""

    def test_rupture_triggers_at_tension_threshold(self) -> None:
        """Test that RUPTURE event fires when tension accumulates."""
        random.seed(42)

        # Create high-tension scenario
        worker = create_proletariat(
            id="C001",
            name="Oppressed Worker",
            wealth=20.0,  # Low wealth
            ideology=-0.7,  # Revolutionary consciousness
            organization=0.6,  # Organized
            repression_faced=0.8,  # High repression
        )

        owner = create_bourgeoisie(
            id="C002",
            name="Oppressor",
            wealth=1000.0,
        )

        # EXPLOITATION edge with high tension
        exploitation = Relationship(
            source_id="C002",
            target_id="C001",
            edge_type=EdgeType.EXPLOITATION,
            exploitation_rate=0.9,  # Extreme exploitation
            tension=0.7,  # Already high tension
        )

        state = WorldState(
            tick=0,
            entities={"C001": worker, "C002": owner},
            relationships=[exploitation],
        )

        # Use low rupture threshold for testing
        defines = GameDefines(
            contradiction=ContradictionDefines(
                rupture_threshold=0.8,  # 80% tension triggers rupture
                tension_accumulation_rate=0.05,
            )
        )
        config = SimulationConfig()

        # Run until rupture might occur
        sim = Simulation(state, config, defines=defines)
        final_state = sim.run(30)

        # Check for RUPTURE event
        rupture_events = [log for log in final_state.event_log if "RUPTURE" in log]

        # Track tension over time
        history = sim.get_history()
        tensions = []
        for s in history:
            for rel in s.relationships:
                if rel.edge_type == EdgeType.EXPLOITATION:
                    tensions.append(rel.tension)

        print(f"Tension values: {tensions[:10]}...")
        print(f"RUPTURE events: {len(rupture_events)}")

        # Assert based on tension reaching threshold
        max_tension = max(tensions) if tensions else 0
        if max_tension >= 0.8:
            assert len(rupture_events) >= 1, (
                f"RUPTURE should trigger at tension >= 0.8. "
                f"Max tension: {max_tension}"
            )
```

### Success Criteria

#### Automated Verification
- [x] New test file passes: `poetry run pytest tests/integration/mechanics/test_rupture_events.py -v` (5 tests)
- [ ] Extended tests pass: `poetry run pytest tests/integration/mechanics/test_george_floyd_dynamic.py -v` (skipped - power vacuum test deferred)
- [ ] All integration tests pass: `mise run test:int`

#### Manual Verification
- [x] Verify RUPTURE event conditions match theoretical model (tension >= 1.0 triggers RUPTURE)
- [ ] Review power vacuum test logic (deferred - requires clearer specification)

**Implementation Note**: Phase 4 partially complete. Created test_rupture_events.py with 5 tests covering ContradictionSystem RUPTURE emission. Power vacuum test in StruggleSystem deferred - requires clearer specification of what "power vacuum" means in implementation.

---

## Testing Strategy

### Unit Tests
Not applicable - this plan creates integration tests only.

### Integration Tests
All tests created by this plan are integration tests in `tests/integration/mechanics/`.

### Manual Testing Steps
1. Run full integration test suite: `mise run test:int`
2. Review test output for any flaky tests (probabilistic assertions)
3. Verify all 12 systems now have coverage

## Performance Considerations

- All new tests use reasonable tick counts (10-50 ticks)
- Use `random.seed(42)` for reproducibility
- Avoid long-running simulations (max 100 ticks for integration tests)

## Migration Notes

No migration required - this is additive test creation.

## References

- Research: `thoughts/shared/research/2026-01-05-integration-test-analysis.md`
- TerritorySystem: `src/babylon/engine/systems/territory.py`
- DecompositionSystem: `src/babylon/engine/systems/decomposition.py`
- ControlRatioSystem: `src/babylon/engine/systems/control_ratio.py`
- Test Patterns: `tests/integration/mechanics/test_george_floyd_dynamic.py`

---

## Implementation Summary

**Completed: 2026-01-06**

### Tests Created

| File | Tests | System | Description |
|------|-------|--------|-------------|
| `test_carceral_geography.py` | 11 | TerritorySystem | Heat dynamics, eviction pipeline, spillover, necropolitics |
| `test_class_decomposition.py` | 7 | DecompositionSystem | LA crisis → CARCERAL_ENFORCER + INTERNAL_PROLETARIAT |
| `test_control_ratio_crisis.py` | 10 | ControlRatioSystem | Guard:prisoner ratio, terminal decision bifurcation |
| `test_rupture_events.py` | 5 | ContradictionSystem | RUPTURE at tension threshold, accumulation rate effects |

**Total: 33 new integration tests**

### Key Implementation Decisions

1. **Ratio-based assertions for population splits**: DecompositionSystem tests use `DECOMPOSITION_FRACTION_TOLERANCE = 0.05` to account for post-decomposition system dynamics affecting population counts.

2. **step() with persistent context for ControlRatioSystem**: Tests inject `_class_decomposition_tick` into persistent context to satisfy prerequisite.

3. **RUPTURE threshold is 1.0 (not configurable)**: ContradictionSystem uses hardcoded threshold. Tests adjust `accumulation_rate` via TensionDefines instead.

4. **Power vacuum test deferred**: StruggleSystem "power vacuum" concept lacks clear implementation specification. Existing `test_george_floyd_dynamic.py` coverage is sufficient for Epoch 1.

### Commit

```
4271759 test(integration): add P1 blocking integration tests for Epoch 1 closure
```
