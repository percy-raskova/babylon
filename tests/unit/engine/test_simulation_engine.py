"""Unit tests for babylon.engine.simulation_engine.

Tests that do not require running the full simulation engine pipeline.
Integration tests that exercise step() with all Systems running have been
relocated to tests/integration/engine/test_simulation_engine.py.
"""

import pytest

from babylon.engine.simulation_engine import step
from babylon.models import (
    Relationship,
    SimulationConfig,
    SocialClass,
    WorldState,
)
from babylon.models.entity_registry import (
    COMPRADOR_ID,
    PERIPHERY_WORKER_ID,
)
from tests.factories import DomainFactory

# =============================================================================
# FIXTURES (using DomainFactory)
# =============================================================================

_factory = DomainFactory()


@pytest.fixture
def worker() -> SocialClass:
    """Create a periphery worker social class."""
    return _factory.create_worker(name="Periphery Worker")


@pytest.fixture
def owner() -> SocialClass:
    """Create a core owner social class.

    CRITICAL: This fixture uses non-standard values from the original test:
    - wealth=0.5 (DomainFactory default is 10.0)
    - ideology=0.0 (DomainFactory default is 0.5)
    - organization=0.8 (DomainFactory default is 0.7)
    """
    return _factory.create_owner(
        name="Core Owner",
        wealth=0.5,
        ideology=0.0,
        organization=0.8,
    )


@pytest.fixture
def exploitation_edge() -> Relationship:
    """Create an exploitation relationship from worker to owner."""
    return _factory.create_relationship()


@pytest.fixture
def two_node_state(
    worker: SocialClass,
    owner: SocialClass,
    exploitation_edge: Relationship,
) -> WorldState:
    """Create a minimal WorldState with two nodes and one edge."""
    return _factory.create_world_state(
        entities={PERIPHERY_WORKER_ID: worker, COMPRADOR_ID: owner},
        relationships=[exploitation_edge],
    )


@pytest.fixture
def config() -> SimulationConfig:
    """Create default simulation config."""
    return SimulationConfig()


# =============================================================================
# METABOLISM SYSTEM REGISTRATION TESTS (Sprint 1.4C)
# =============================================================================


class TestMetabolismSystemRegistration:
    """Test that MetabolismSystem is registered in DEFAULT_SYSTEMS.

    Sprint 1.4C: The Wiring - MetabolismSystem must be included in the
    default system list for the metabolic rift feedback loop to function.
    """

    def test_metabolism_system_in_default_systems(self) -> None:
        """MetabolismSystem should be registered in _DEFAULT_SYSTEMS.

        The metabolic rift dynamics (biocapacity regeneration, overshoot
        detection) only run if MetabolismSystem is in the engine's system list.
        """
        from babylon.engine.simulation_engine import _DEFAULT_SYSTEMS

        system_types = [type(s).__name__ for s in _DEFAULT_SYSTEMS]
        assert "MetabolismSystem" in system_types, (
            "MetabolismSystem not found in _DEFAULT_SYSTEMS. "
            "Import and register it in simulation_engine.py after TerritorySystem."
        )

    def test_metabolism_system_runs_after_territory_system(self) -> None:
        """MetabolismSystem should run after TerritorySystem.

        Ecological dynamics depend on territory state, so MetabolismSystem
        must be ordered after TerritorySystem in the system list.
        """
        from babylon.engine.simulation_engine import _DEFAULT_SYSTEMS
        from babylon.engine.systems.metabolism import MetabolismSystem
        from babylon.engine.systems.territory import TerritorySystem

        # Find positions of both systems
        territory_idx = None
        metabolism_idx = None

        for i, system in enumerate(_DEFAULT_SYSTEMS):
            if isinstance(system, TerritorySystem):
                territory_idx = i
            if isinstance(system, MetabolismSystem):
                metabolism_idx = i

        assert territory_idx is not None, "TerritorySystem not in _DEFAULT_SYSTEMS"
        assert metabolism_idx is not None, "MetabolismSystem not in _DEFAULT_SYSTEMS"
        assert metabolism_idx > territory_idx, (
            f"MetabolismSystem (idx={metabolism_idx}) should run after "
            f"TerritorySystem (idx={territory_idx})"
        )


# =============================================================================
# COST-CHECKING TESTS (Epoch 1: Political Economy of Liquidity)
# =============================================================================


@pytest.mark.ledger
class TestCostChecking:
    """Test fiscal cost-checking in step().

    Epoch 1: The Ledger - Political Economy of Liquidity.
    When a state's treasury falls below its burn_rate, the step() function
    should log a warning. This is the first step toward fiscal crisis mechanics.
    """

    def test_step_logs_warning_when_treasury_below_burn_rate(
        self,
        two_node_state: WorldState,
        config: SimulationConfig,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """step() logs warning when state treasury < burn_rate.

        StateFinance defaults:
        - treasury: 100.0
        - police_budget: 10.0
        - social_reproduction_budget: 15.0
        - burn_rate (computed): 25.0

        When treasury (5.0) < burn_rate (25.0), a warning should be logged.
        """
        import logging

        from babylon.models.entities.state_finance import StateFinance

        # StateFinance with treasury (5.0) < burn_rate (25.0)
        insolvent_finance = StateFinance(treasury=5.0)
        state = two_node_state.model_copy(update={"state_finances": {"USA": insolvent_finance}})

        with caplog.at_level(logging.WARNING):
            step(state, config)

        # Verify warning was logged about USA's fiscal situation
        assert "USA" in caplog.text
        assert "treasury" in caplog.text.lower() or "burn_rate" in caplog.text.lower()

    def test_step_no_warning_when_treasury_sufficient(
        self,
        two_node_state: WorldState,
        config: SimulationConfig,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """step() does not warn when treasury >= burn_rate.

        When treasury (100.0) >= burn_rate (25.0), no warning should be logged.
        """
        import logging

        from babylon.models.entities.state_finance import StateFinance

        # StateFinance with treasury (100.0) >= burn_rate (25.0)
        solvent_finance = StateFinance(treasury=100.0)
        state = two_node_state.model_copy(update={"state_finances": {"USA": solvent_finance}})

        with caplog.at_level(logging.WARNING):
            step(state, config)

        # Should not contain warning about USA treasury
        # (there may be other warnings, so we check specifically for fiscal terms)
        warning_records = [r for r in caplog.records if r.levelno >= logging.WARNING]
        fiscal_warnings = [
            r
            for r in warning_records
            if "USA" in r.message
            and ("treasury" in r.message.lower() or "burn" in r.message.lower())
        ]
        assert len(fiscal_warnings) == 0

    def test_step_handles_empty_state_finances(
        self,
        two_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """step() handles empty state_finances dict without errors.

        Backward compatibility: states without any state_finances should
        continue to work normally without raising exceptions.
        """
        # Default two_node_state has no state_finances (empty dict)
        # This should not raise an exception
        new_state = step(two_node_state, config)

        # Verify step completed normally
        assert new_state.tick == 1

    def test_step_logs_warning_for_each_insolvent_state(
        self,
        two_node_state: WorldState,
        config: SimulationConfig,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """step() logs warnings for each state where treasury < burn_rate.

        If multiple states are insolvent, each should get its own warning.
        """
        import logging

        from babylon.models.entities.state_finance import StateFinance

        # USA is insolvent, UK is solvent
        finances = {
            "USA": StateFinance(treasury=5.0),  # < burn_rate (25.0)
            "UK": StateFinance(treasury=100.0),  # >= burn_rate (25.0)
            "FRANCE": StateFinance(treasury=10.0),  # < burn_rate (25.0)
        }
        state = two_node_state.model_copy(update={"state_finances": finances})

        with caplog.at_level(logging.WARNING):
            step(state, config)

        # USA and FRANCE should have warnings, UK should not
        assert "USA" in caplog.text
        assert "FRANCE" in caplog.text
        # UK should not appear in warnings about insolvency
        warning_records = [r for r in caplog.records if r.levelno >= logging.WARNING]
        uk_fiscal_warnings = [
            r
            for r in warning_records
            if "UK" in r.message
            and ("treasury" in r.message.lower() or "burn" in r.message.lower())
        ]
        assert len(uk_fiscal_warnings) == 0

    def test_step_preserves_state_finances_in_output(
        self,
        two_node_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """step() preserves state_finances in the output WorldState.

        The state_finances dict should flow through the graph transformation
        and be present in the returned WorldState.
        """
        from babylon.models.entities.state_finance import StateFinance

        finances = {"USA": StateFinance(treasury=500.0, police_budget=30.0)}
        state = two_node_state.model_copy(update={"state_finances": finances})

        new_state = step(state, config)

        # state_finances should be preserved
        assert "USA" in new_state.state_finances
        assert new_state.state_finances["USA"].treasury == 500.0
        assert new_state.state_finances["USA"].police_budget == 30.0
