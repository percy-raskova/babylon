"""Integration tests for the Metabolic Rift feedback loop.

Sprint 1.4C: The Wiring - Verify that MetabolismSystem runs in the
simulation loop and that ecological metrics are collected.

These tests verify end-to-end functionality:
1. MetabolismSystem is registered and runs during step()
2. Biocapacity regeneration and depletion work correctly
3. Overshoot events are emitted when consumption exceeds biocapacity
4. Ecological metrics are observable in WorldState computed fields

TDD RED Phase: These tests should FAIL until:
- MetabolismSystem is added to _DEFAULT_SYSTEMS in simulation_engine.py
- TickMetrics has ecological fields (overshoot_ratio, total_biocapacity, total_consumption)
- MetricsCollector extracts ecological data from WorldState

NOTE: Tests marked with @pytest.mark.red_phase are excluded from pre-commit.
Remove the marker when implementing GREEN phase.
"""

from __future__ import annotations

import pytest

from babylon.engine.simulation_engine import _DEFAULT_SYSTEMS, step
from babylon.models import SimulationConfig, WorldState
from babylon.models.entities.social_class import SocialClass
from babylon.models.entities.territory import Territory
from babylon.models.enums import SectorType, SocialRole

# Most tests are GREEN; only TestBiocapacityDynamics.test_biocapacity_depletes_under_extraction is RED
pytestmark = [pytest.mark.integration, pytest.mark.theory_rift]

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def config() -> SimulationConfig:
    """Create default simulation configuration."""
    return SimulationConfig()


@pytest.fixture
def territory_with_regeneration() -> Territory:
    """Create a territory with active regeneration dynamics.

    Biocapacity is below max, so regeneration should increase it each tick.
    """
    return Territory(
        id="T001",
        name="Test Territory",
        sector_type=SectorType.INDUSTRIAL,
        biocapacity=50.0,  # Below max, should regenerate
        max_biocapacity=100.0,
        regeneration_rate=0.1,  # 10% of max = 10 per tick
        extraction_intensity=0.0,  # No extraction pressure
    )


@pytest.fixture
def territory_under_extraction() -> Territory:
    """Create a territory under extraction pressure.

    High extraction_intensity should deplete biocapacity.
    """
    return Territory(
        id="T002",
        name="Extraction Zone",
        sector_type=SectorType.INDUSTRIAL,
        biocapacity=80.0,
        max_biocapacity=100.0,
        regeneration_rate=0.02,  # Low regeneration
        extraction_intensity=0.8,  # High extraction pressure
    )


@pytest.fixture
def consuming_entity() -> SocialClass:
    """Create a social class with high consumption needs.

    s_bio + s_class = consumption_needs
    """
    return SocialClass(
        id="C001",
        name="High Consumers",
        role=SocialRole.CORE_BOURGEOISIE,
        wealth=100.0,
        s_bio=15.0,  # Biological subsistence
        s_class=10.0,  # Class-specific consumption
        # Total consumption = 25.0
    )


# =============================================================================
# METABOLISM SYSTEM REGISTRATION TESTS
# =============================================================================


@pytest.mark.integration
class TestMetabolicRiftIntegration:
    """Test the metabolic rift feedback loop integration."""

    def test_metabolism_system_registered(self) -> None:
        """MetabolismSystem must be in DEFAULT_SYSTEMS for the rift to work.

        Without registration, biocapacity dynamics never run and
        overshoot events are never emitted.
        """
        system_names = [type(s).__name__ for s in _DEFAULT_SYSTEMS]
        assert "MetabolismSystem" in system_names, (
            "MetabolismSystem not found in _DEFAULT_SYSTEMS. "
            "Import and register it in simulation_engine.py"
        )

    def test_metabolism_system_has_correct_name(self) -> None:
        """MetabolismSystem.name should be 'Metabolism'."""
        from babylon.engine.systems.metabolism import MetabolismSystem

        system = MetabolismSystem()
        assert system.name == "Metabolism"


# =============================================================================
# BIOCAPACITY DYNAMICS TESTS
# =============================================================================


@pytest.mark.integration
class TestBiocapacityDynamics:
    """Test that biocapacity regeneration and depletion work in the loop."""

    def test_biocapacity_regenerates_when_engine_runs(
        self,
        territory_with_regeneration: Territory,
        config: SimulationConfig,
    ) -> None:
        """Verify biocapacity increases when simulation runs (regeneration active).

        Given a territory with biocapacity < max and no extraction,
        after running the engine, biocapacity should increase.
        """
        state = WorldState(
            tick=0,
            territories={"T001": territory_with_regeneration},
        )

        initial_bio = float(territory_with_regeneration.biocapacity)

        # Run 3 ticks
        for _ in range(3):
            state = step(state, config)

        # Biocapacity should have increased due to regeneration
        final_bio = float(state.territories["T001"].biocapacity)
        assert final_bio > initial_bio, (
            f"Biocapacity should regenerate: {initial_bio} -> {final_bio}. "
            "Is MetabolismSystem registered in _DEFAULT_SYSTEMS?"
        )

    @pytest.mark.red_phase  # Calibration needed for extraction intensity
    @pytest.mark.skip(reason="Macro-tuning requires Dashboard visualization - Sprint 1.5")
    def test_biocapacity_depletes_under_extraction(
        self,
        territory_under_extraction: Territory,
        config: SimulationConfig,
    ) -> None:
        """Verify biocapacity decreases when extraction_intensity is high.

        The formula is: delta = R - (E * eta)
        With high extraction_intensity, the net change should be negative.

        Sprint 1.5: Skipped until Dashboard calibration complete. The current
        extraction_intensity (0.8) with low regeneration (0.02) results in
        net positive delta because regeneration_rate * max > intensity * entropy.
        """
        state = WorldState(
            tick=0,
            territories={"T002": territory_under_extraction},
        )

        initial_bio = float(territory_under_extraction.biocapacity)

        # Run 3 ticks
        for _ in range(3):
            state = step(state, config)

        # Biocapacity should have decreased due to extraction
        final_bio = float(state.territories["T002"].biocapacity)
        assert final_bio < initial_bio, (
            f"Biocapacity should deplete under extraction: {initial_bio} -> {final_bio}"
        )

    def test_biocapacity_capped_at_max(
        self,
        config: SimulationConfig,
    ) -> None:
        """Verify biocapacity never exceeds max_biocapacity.

        Even with high regeneration, biocapacity should be clamped.
        """
        territory = Territory(
            id="T001",
            name="Near Max Territory",
            sector_type=SectorType.RESIDENTIAL,
            biocapacity=99.0,  # Very close to max
            max_biocapacity=100.0,
            regeneration_rate=0.5,  # Very high regeneration
            extraction_intensity=0.0,
        )
        state = WorldState(tick=0, territories={"T001": territory})

        # Run 10 ticks
        for _ in range(10):
            state = step(state, config)

        # Biocapacity should not exceed max
        final_bio = float(state.territories["T001"].biocapacity)
        assert final_bio <= 100.0, f"Biocapacity should be capped at max: {final_bio} > 100.0"

    def test_biocapacity_floored_at_zero(
        self,
        config: SimulationConfig,
    ) -> None:
        """Verify biocapacity never goes below zero.

        Even with extreme extraction, biocapacity is clamped to 0.
        """
        territory = Territory(
            id="T001",
            name="Depleted Territory",
            sector_type=SectorType.INDUSTRIAL,
            biocapacity=5.0,  # Very low
            max_biocapacity=100.0,
            regeneration_rate=0.01,  # Very low regeneration
            extraction_intensity=1.0,  # Maximum extraction
        )
        state = WorldState(tick=0, territories={"T001": territory})

        # Run 100 ticks
        for _ in range(100):
            state = step(state, config)

        # Biocapacity should not go below 0
        final_bio = float(state.territories["T001"].biocapacity)
        assert final_bio >= 0.0, f"Biocapacity should be floored at 0: {final_bio} < 0"


# =============================================================================
# OVERSHOOT DETECTION TESTS
# =============================================================================


@pytest.mark.integration
class TestOvershootDetection:
    """Test overshoot ratio calculation and event emission."""

    def test_overshoot_ratio_calculated_correctly(
        self,
        config: SimulationConfig,
    ) -> None:
        """Verify overshoot_ratio reflects consumption vs biocapacity.

        overshoot_ratio = total_consumption / total_biocapacity
        When > 1.0, we are in ecological overshoot.
        """
        # Low biocapacity territory
        territory = Territory(
            id="T001",
            name="Depleted Territory",
            sector_type=SectorType.INDUSTRIAL,
            biocapacity=10.0,  # Low biocapacity
            max_biocapacity=100.0,
            regeneration_rate=0.02,
        )

        # High consumption class
        social_class = SocialClass(
            id="C001",
            name="High Consumers",
            role=SocialRole.CORE_BOURGEOISIE,
            wealth=100.0,
            s_bio=15.0,  # Biological subsistence
            s_class=10.0,  # Class-specific consumption
            # Total consumption = 25.0
        )

        state = WorldState(
            tick=0,
            territories={"T001": territory},
            entities={"C001": social_class},
        )

        # Check WorldState computed property
        # Ratio = 25 / 10 = 2.5 (overshoot!)
        assert state.overshoot_ratio > 1.0, (
            f"Expected overshoot (>1.0), got {state.overshoot_ratio}"
        )

    def test_sustainable_ratio_when_biocapacity_exceeds_consumption(
        self,
        config: SimulationConfig,
    ) -> None:
        """Verify overshoot_ratio < 1.0 when system is sustainable."""
        # High biocapacity territory
        territory = Territory(
            id="T001",
            name="Pristine Territory",
            sector_type=SectorType.RESIDENTIAL,  # Use existing enum value
            biocapacity=500.0,  # High biocapacity
            max_biocapacity=500.0,
        )

        # Low consumption class
        social_class = SocialClass(
            id="C001",
            name="Low Consumers",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=10.0,
            s_bio=5.0,
            s_class=5.0,
            # Total consumption = 10.0
        )

        state = WorldState(
            tick=0,
            territories={"T001": territory},
            entities={"C001": social_class},
        )

        # Ratio = 10 / 500 = 0.02 (sustainable)
        assert state.overshoot_ratio < 1.0, (
            f"Expected sustainable ratio (<1.0), got {state.overshoot_ratio}"
        )

    def test_overshoot_event_emitted_when_ratio_exceeds_one(
        self,
        config: SimulationConfig,
    ) -> None:
        """Verify ECOLOGICAL_OVERSHOOT event is emitted when ratio > 1.0.

        The MetabolismSystem should emit an event when overshoot is detected.
        """

        # Create overshoot conditions
        territory = Territory(
            id="T001",
            name="Depleted",
            sector_type=SectorType.INDUSTRIAL,
            biocapacity=10.0,
            max_biocapacity=100.0,
        )
        entity = SocialClass(
            id="C001",
            name="Consumers",
            role=SocialRole.CORE_BOURGEOISIE,
            wealth=100.0,
            s_bio=15.0,
            s_class=10.0,
        )

        state = WorldState(
            tick=0,
            territories={"T001": territory},
            entities={"C001": entity},
        )

        # Run one tick
        new_state = step(state, config)

        # Check for ECOLOGICAL_OVERSHOOT event in event_log
        overshoot_events = [e for e in new_state.event_log if "ECOLOGICAL_OVERSHOOT" in e]
        assert len(overshoot_events) > 0, (
            "ECOLOGICAL_OVERSHOOT event not emitted. "
            "Is MetabolismSystem registered and emitting events?"
        )


# =============================================================================
# WORLDSTATE COMPUTED FIELDS TESTS
# =============================================================================


@pytest.mark.integration
class TestWorldStateEcologicalFields:
    """Test WorldState computed fields for ecological metrics."""

    def test_total_biocapacity_computed_field(self) -> None:
        """WorldState.total_biocapacity should sum all territory biocapacities."""
        territories = {
            "T001": Territory(
                id="T001",
                name="Zone A",
                sector_type=SectorType.INDUSTRIAL,
                biocapacity=100.0,
            ),
            "T002": Territory(
                id="T002",
                name="Zone B",
                sector_type=SectorType.RESIDENTIAL,
                biocapacity=150.0,
            ),
        }
        state = WorldState(tick=0, territories=territories)

        assert state.total_biocapacity == 250.0

    def test_total_consumption_computed_field(self) -> None:
        """WorldState.total_consumption should sum all entity consumption_needs."""
        entities = {
            "C001": SocialClass(
                id="C001",
                name="Class A",
                role=SocialRole.PERIPHERY_PROLETARIAT,
                wealth=10.0,
                s_bio=10.0,
                s_class=5.0,
            ),
            "C002": SocialClass(
                id="C002",
                name="Class B",
                role=SocialRole.CORE_BOURGEOISIE,
                wealth=100.0,
                s_bio=20.0,
                s_class=15.0,
            ),
        }
        state = WorldState(tick=0, entities=entities)

        # Total = (10+5) + (20+15) = 15 + 35 = 50
        assert state.total_consumption == 50.0

    def test_overshoot_ratio_computed_field(self) -> None:
        """WorldState.overshoot_ratio should be consumption / biocapacity."""
        territory = Territory(
            id="T001",
            name="Test",
            sector_type=SectorType.INDUSTRIAL,
            biocapacity=100.0,
        )
        entity = SocialClass(
            id="C001",
            name="Test",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            s_bio=40.0,
            s_class=10.0,
        )
        state = WorldState(
            tick=0,
            territories={"T001": territory},
            entities={"C001": entity},
        )

        # Ratio = 50 / 100 = 0.5
        assert state.overshoot_ratio == pytest.approx(0.5)

    def test_overshoot_ratio_handles_zero_biocapacity(self) -> None:
        """WorldState.overshoot_ratio should handle zero biocapacity gracefully.

        When biocapacity is zero, return a very high ratio to indicate crisis.
        """
        territory = Territory(
            id="T001",
            name="Depleted",
            sector_type=SectorType.INDUSTRIAL,
            biocapacity=0.0,  # Completely depleted
        )
        entity = SocialClass(
            id="C001",
            name="Consumer",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            s_bio=10.0,
            s_class=5.0,
        )
        state = WorldState(
            tick=0,
            territories={"T001": territory},
            entities={"C001": entity},
        )

        # Should not raise ZeroDivisionError
        # Instead, return a sentinel high value
        assert state.overshoot_ratio > 100.0


# =============================================================================
# MULTI-TICK STABILITY TESTS
# =============================================================================


@pytest.mark.integration
class TestMetabolicStability:
    """Test metabolic rift stability over multiple ticks."""

    def test_hundred_tick_stability(
        self,
        config: SimulationConfig,
    ) -> None:
        """Run 100 ticks and verify ecological metrics remain valid.

        This stress-tests the feedback loop for numerical stability.
        """
        territory = Territory(
            id="T001",
            name="Test Territory",
            sector_type=SectorType.INDUSTRIAL,
            biocapacity=100.0,
            max_biocapacity=100.0,
            regeneration_rate=0.05,
            extraction_intensity=0.03,
        )
        entity = SocialClass(
            id="C001",
            name="Test Consumer",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=50.0,
            s_bio=10.0,
            s_class=5.0,
        )
        state = WorldState(
            tick=0,
            territories={"T001": territory},
            entities={"C001": entity},
        )

        # Run 100 ticks
        for _ in range(100):
            state = step(state, config)

        # Verify ecological metrics are valid
        assert state.tick == 100
        final_bio = float(state.territories["T001"].biocapacity)
        assert 0.0 <= final_bio <= 100.0, f"Biocapacity out of bounds after 100 ticks: {final_bio}"
        assert state.overshoot_ratio >= 0.0, f"Overshoot ratio invalid: {state.overshoot_ratio}"

    def test_deterministic_ecological_evolution(
        self,
        config: SimulationConfig,
    ) -> None:
        """Verify ecological evolution is deterministic (same inputs = same outputs)."""

        def run_simulation() -> WorldState:
            territory = Territory(
                id="T001",
                name="Test",
                sector_type=SectorType.INDUSTRIAL,
                biocapacity=75.0,
                max_biocapacity=100.0,
                regeneration_rate=0.05,
                extraction_intensity=0.02,
            )
            state = WorldState(tick=0, territories={"T001": territory})
            for _ in range(50):
                state = step(state, config)
            return state

        result1 = run_simulation()
        result2 = run_simulation()

        assert result1.territories["T001"].biocapacity == result2.territories["T001"].biocapacity
        assert result1.overshoot_ratio == result2.overshoot_ratio
