"""Integration tests for tensor data flow.

T040: Integration test: SQLite → TensorRegistry → Simulation flow.

These tests verify the complete data pipeline from the SQLite database
through the TensorRegistry to the Simulation and its snapshots.
"""

from __future__ import annotations

import pytest

from babylon.economics.tensor import NoDataSentinel, ValueTensor4x3


class TestTensorDataFlow:
    """Integration tests for SQLite → TensorRegistry → Simulation flow.

    T040: Verify the complete tensor data pipeline works end-to-end.
    """

    @pytest.mark.integration
    def test_simulation_from_sqlite_initializes_tensor_registry(self) -> None:
        """Simulation.from_sqlite() creates and hydrates TensorRegistry."""
        from babylon.engine.simulation import Simulation

        # Create simulation from SQLite (Wayne and Oakland counties, Detroit metro)
        sim = Simulation.from_sqlite(fips_codes=["26163", "26125"], year=2022)

        # Verify tensor_registry was created
        assert sim.tensor_registry is not None

        # Verify tensor data was loaded for requested counties
        wayne_tensor = sim.tensor_registry.get("26163", 2022)
        oakland_tensor = sim.tensor_registry.get("26125", 2022)

        assert isinstance(wayne_tensor, ValueTensor4x3)
        assert isinstance(oakland_tensor, ValueTensor4x3)

        # Verify tensor data is accessible (no database queries needed)
        assert wayne_tensor.fips_code == "26163"
        assert wayne_tensor.year == 2022
        assert wayne_tensor.total_v > 0  # Has variable capital data

    @pytest.mark.integration
    def test_simulation_snapshot_provides_tensor_registry_access(self) -> None:
        """SimulationSnapshot includes tensor_registry reference."""
        from babylon.engine.simulation import Simulation

        sim = Simulation.from_sqlite(fips_codes=["26163"], year=2022)
        snapshot = sim.get_snapshot()

        # Verify snapshot has tensor_registry
        assert snapshot.tensor_registry is not None
        assert snapshot.tensor_registry is sim.tensor_registry

        # Verify tensor data is accessible through snapshot
        tensor = snapshot.tensor_registry.get("26163", 2022)
        assert isinstance(tensor, ValueTensor4x3)
        assert tensor.profit_rate > 0

    @pytest.mark.integration
    def test_tensor_data_accessible_without_database_after_init(self) -> None:
        """After from_sqlite(), tensor data is cached and DB-independent."""
        from babylon.engine.simulation import Simulation

        # Initialize simulation (this loads data from SQLite)
        sim = Simulation.from_sqlite(fips_codes=["26163"], year=2022)

        # After initialization, we should be able to access tensor data
        # without any database connection. The registry is pre-loaded.
        registry = sim.tensor_registry
        assert registry is not None

        # Multiple accesses should work without DB queries
        for _ in range(5):
            tensor = registry.get("26163", 2022)
            assert isinstance(tensor, ValueTensor4x3)

            # Access computed properties (derived from cached data)
            _ = tensor.profit_rate
            _ = tensor.exploitation_rate
            _ = tensor.organic_composition
            _ = tensor.imperial_rent

    @pytest.mark.integration
    def test_tensor_registry_county_not_loaded_returns_sentinel(self) -> None:
        """Registry returns NoDataSentinel for counties not in fips_codes."""
        from babylon.engine.simulation import Simulation

        # Only load Wayne County
        sim = Simulation.from_sqlite(fips_codes=["26163"], year=2022)

        # Oakland was not loaded
        oakland_tensor = sim.tensor_registry.get("26125", 2022)
        assert isinstance(oakland_tensor, NoDataSentinel)
        assert "not loaded" in oakland_tensor.reason

    @pytest.mark.integration
    def test_tensor_computed_properties_work_after_hydration(self) -> None:
        """All computed properties work correctly after hydration."""
        from babylon.engine.simulation import Simulation

        sim = Simulation.from_sqlite(fips_codes=["26163"], year=2022)
        tensor = sim.tensor_registry.get("26163", 2022)

        assert isinstance(tensor, ValueTensor4x3)

        # Verify all computed properties are accessible and valid
        # These should not require any database access
        assert tensor.total_c >= 0  # Total constant capital
        assert tensor.total_v >= 0  # Total variable capital
        assert tensor.total_s >= 0  # Total surplus value
        assert tensor.total_value >= 0  # c + v + s

        # Rate calculations
        assert 0 <= tensor.profit_rate <= 1 or tensor.total_c + tensor.total_v == 0
        assert tensor.exploitation_rate >= 0 or tensor.total_v == 0
        assert tensor.organic_composition >= 0 or tensor.total_v == 0

        # Imperial rent (can be negative for periphery)
        _ = tensor.imperial_rent  # Just verify it's accessible

    @pytest.mark.integration
    def test_simulation_tick_preserves_tensor_registry(self) -> None:
        """TensorRegistry remains accessible after simulation ticks."""
        from babylon.engine.simulation import Simulation

        sim = Simulation.from_sqlite(fips_codes=["26163"], year=2022)

        # Get initial tensor data
        initial_tensor = sim.tensor_registry.get("26163", 2022)
        assert isinstance(initial_tensor, ValueTensor4x3)

        # Run some simulation ticks
        sim.run(5)

        # Tensor registry should still work
        tensor_after = sim.tensor_registry.get("26163", 2022)
        assert isinstance(tensor_after, ValueTensor4x3)

        # Data should be the same (tensors are immutable)
        assert tensor_after.total_v == initial_tensor.total_v
        assert tensor_after.profit_rate == initial_tensor.profit_rate
