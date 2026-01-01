"""TDD tests for tune_parameters.py parameter sensitivity analysis tool.

Phase 1: RED - These tests verify the tune_parameters tool performs
sensitivity analysis on GameDefines parameters.

Test Classes:
    TestModuleStructure: Verify module exists and has required functions
    TestParameterInjection: Verify GameDefines can be modified for sweeps
    TestSimulationRunner: Verify simulation runs with modified parameters
    TestDeathDetection: Verify wealth depletion detection logic
    TestOutputFormatting: Verify output table formatting
    TestSweepFunction: Verify complete sweep functionality
"""

from __future__ import annotations

import importlib.util
import inspect
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

# Path to the tune_parameters tool
TUNE_PARAMETERS_PATH = Path(__file__).parent.parent.parent.parent / "tools" / "tune_parameters.py"


def load_tune_parameters_module() -> Any:
    """Load the tune_parameters module dynamically.

    Returns:
        The loaded module object

    Raises:
        FileNotFoundError: If tune_parameters.py does not exist
    """
    if not TUNE_PARAMETERS_PATH.exists():
        pytest.skip(f"tune_parameters.py not found at {TUNE_PARAMETERS_PATH}")

    spec = importlib.util.spec_from_file_location("tune_parameters", TUNE_PARAMETERS_PATH)
    if spec is None or spec.loader is None:
        pytest.fail("Failed to load tune_parameters module spec")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestModuleStructure:
    """Test that tune_parameters.py has the required structure."""

    def test_module_exists(self) -> None:
        """Verify tune_parameters.py exists at expected path."""
        assert TUNE_PARAMETERS_PATH.exists(), (
            f"tune_parameters.py not found at {TUNE_PARAMETERS_PATH}"
        )

    def test_run_sweep_function_exists(self) -> None:
        """Verify run_sweep function exists in module."""
        module = load_tune_parameters_module()
        assert hasattr(module, "run_sweep"), "Module missing 'run_sweep' function"
        assert callable(module.run_sweep), "'run_sweep' is not callable"

    def test_run_sweep_signature(self) -> None:
        """Verify run_sweep has correct parameter signature."""
        module = load_tune_parameters_module()
        sig = inspect.signature(module.run_sweep)
        param_names = list(sig.parameters.keys())

        assert "param_path" in param_names, "Missing 'param_path' parameter"
        assert "start" in param_names, "Missing 'start' parameter"
        assert "end" in param_names, "Missing 'end' parameter"
        assert "step" in param_names, "Missing 'step' parameter"

    def test_has_main_block(self) -> None:
        """Verify module has if __name__ == '__main__' block."""
        source_code = TUNE_PARAMETERS_PATH.read_text()
        assert "if __name__" in source_code, "Missing main execution block"
        assert "__main__" in source_code, "Missing __main__ check"


class TestParameterInjection:
    """Test GameDefines parameter injection functionality."""

    def test_inject_nested_parameter_function_exists(self) -> None:
        """Verify function to inject nested parameters exists."""
        module = load_tune_parameters_module()
        # Could be named inject_parameter, create_defines_with_override, etc.
        has_injection = (
            hasattr(module, "inject_parameter")
            or hasattr(module, "create_defines_with_override")
            or hasattr(module, "update_nested_param")
        )
        assert has_injection, (
            "Module needs a function to inject nested parameters "
            "(inject_parameter, create_defines_with_override, or update_nested_param)"
        )

    def test_economy_extraction_efficiency_injection(self) -> None:
        """Verify economy.extraction_efficiency can be injected."""
        module = load_tune_parameters_module()

        # Find the injection function
        inject_fn: Callable[..., Any] | None = None
        for name in [
            "inject_parameter",
            "create_defines_with_override",
            "update_nested_param",
        ]:
            if hasattr(module, name):
                inject_fn = getattr(module, name)
                break

        assert inject_fn is not None, "No parameter injection function found"

        # Import GameDefines for testing
        from babylon.config.defines import GameDefines

        base_defines = GameDefines()
        new_defines = inject_fn(base_defines, "economy.extraction_efficiency", 0.3)

        assert isinstance(new_defines, GameDefines), (
            f"Expected GameDefines, got {type(new_defines)}"
        )
        assert new_defines.economy.extraction_efficiency == 0.3, (
            f"Expected extraction_efficiency=0.3, got {new_defines.economy.extraction_efficiency}"
        )

    def test_original_defines_unchanged(self) -> None:
        """Verify original GameDefines is not mutated by injection."""
        module = load_tune_parameters_module()

        inject_fn: Callable[..., Any] | None = None
        for name in [
            "inject_parameter",
            "create_defines_with_override",
            "update_nested_param",
        ]:
            if hasattr(module, name):
                inject_fn = getattr(module, name)
                break

        assert inject_fn is not None, "No parameter injection function found"

        from babylon.config.defines import GameDefines

        base_defines = GameDefines()
        original_value = base_defines.economy.extraction_efficiency

        _new_defines = inject_fn(base_defines, "economy.extraction_efficiency", 0.1)

        # Original should be unchanged (frozen model)
        assert base_defines.economy.extraction_efficiency == original_value, (
            "Original GameDefines was mutated!"
        )


class TestSimulationRunner:
    """Test simulation execution with modified parameters."""

    def test_run_simulation_function_exists(self) -> None:
        """Verify function to run single simulation exists."""
        module = load_tune_parameters_module()
        has_runner = hasattr(module, "run_simulation") or hasattr(module, "run_single_simulation")
        assert has_runner, (
            "Module needs a function to run simulations (run_simulation or run_single_simulation)"
        )

    def test_simulation_returns_result_dict(self) -> None:
        """Verify simulation returns a structured result."""
        module = load_tune_parameters_module()

        run_fn: Callable[..., Any] | None = None
        for name in ["run_simulation", "run_single_simulation"]:
            if hasattr(module, name):
                run_fn = getattr(module, name)
                break

        assert run_fn is not None, "No simulation runner function found"

        from babylon.config.defines import GameDefines

        defines = GameDefines()
        result = run_fn(defines, max_ticks=5)

        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert "ticks_survived" in result, "Result missing 'ticks_survived'"
        assert "max_tension" in result, "Result missing 'max_tension'"
        assert "outcome" in result, "Result missing 'outcome'"


class TestDeathDetection:
    """Test wealth depletion (death) detection logic."""

    def test_death_threshold_constant(self) -> None:
        """Verify DEATH_THRESHOLD constant is defined."""
        module = load_tune_parameters_module()
        assert hasattr(module, "DEATH_THRESHOLD"), "Module missing 'DEATH_THRESHOLD' constant"
        assert module.DEATH_THRESHOLD <= 0.001, (
            f"DEATH_THRESHOLD should be <= 0.001, got {module.DEATH_THRESHOLD}"
        )

    def test_periphery_worker_id_constant(self) -> None:
        """Verify PERIPHERY_WORKER_ID constant is defined."""
        module = load_tune_parameters_module()
        assert hasattr(module, "PERIPHERY_WORKER_ID"), (
            "Module missing 'PERIPHERY_WORKER_ID' constant"
        )
        # Should be C001 based on imperial_circuit scenario
        assert module.PERIPHERY_WORKER_ID == "C001", (
            f"Expected 'C001', got {module.PERIPHERY_WORKER_ID}"
        )

    def test_is_dead_function_exists(self) -> None:
        """Verify death detection function exists."""
        module = load_tune_parameters_module()
        has_death_check = (
            hasattr(module, "is_dead_by_wealth")
            or hasattr(module, "is_dead")
            or hasattr(module, "check_death")
        )
        assert has_death_check, "Module needs death detection function"

    def test_death_detection_at_threshold(self) -> None:
        """Verify death is detected when wealth <= DEATH_THRESHOLD."""
        module = load_tune_parameters_module()

        check_fn: Callable[..., bool] | None = None
        for name in ["is_dead_by_wealth", "is_dead", "check_death"]:
            if hasattr(module, name):
                check_fn = getattr(module, name)
                break

        assert check_fn is not None, "No death check function found"

        # Test at threshold
        assert check_fn(0.001) is True, "Should detect death at threshold"
        assert check_fn(0.0005) is True, "Should detect death below threshold"
        assert check_fn(0.002) is False, "Should not detect death above threshold"


class TestOutputFormatting:
    """Test output table formatting."""

    def test_format_results_function_exists(self) -> None:
        """Verify format_results or similar function exists."""
        module = load_tune_parameters_module()
        has_formatter = (
            hasattr(module, "format_results")
            or hasattr(module, "format_table")
            or hasattr(module, "print_results")
        )
        assert has_formatter, (
            "Module needs output formatting function "
            "(format_results, format_table, or print_results)"
        )

    def test_output_contains_required_columns(self) -> None:
        """Verify output table contains Value, Ticks, Tension, Outcome columns."""
        module = load_tune_parameters_module()

        format_fn: Callable[..., str] | None = None
        for name in ["format_results", "format_table"]:
            if hasattr(module, name):
                format_fn = getattr(module, name)
                break

        if format_fn is None:
            pytest.skip("No format function found (may use print_results)")

        # Create sample results
        results = [
            {"value": 0.1, "ticks_survived": 50, "max_tension": 0.5, "outcome": "SURVIVED"},
            {"value": 0.2, "ticks_survived": 25, "max_tension": 0.8, "outcome": "DIED"},
        ]

        output = format_fn(results)

        assert "Value" in output, "Output missing 'Value' column"
        assert "Ticks" in output or "Survived" in output, "Output missing ticks column"
        assert "Tension" in output, "Output missing 'Tension' column"
        assert "Outcome" in output, "Output missing 'Outcome' column"


class TestSweepFunction:
    """Test the complete run_sweep functionality."""

    def test_sweep_iterates_correct_range(self) -> None:
        """Verify sweep iterates from start to end by step."""
        module = load_tune_parameters_module()

        # We'll count how many times simulation is called
        call_count = 0
        original_run = None

        # Find the run function
        for name in ["run_simulation", "run_single_simulation"]:
            if hasattr(module, name):
                original_run = getattr(module, name)
                break

        if original_run is None:
            pytest.skip("No simulation runner found")

        def mock_run(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            return {
                "ticks_survived": 50,
                "max_tension": 0.3,
                "outcome": "SURVIVED",
            }

        # Patch the run function
        for name in ["run_simulation", "run_single_simulation"]:
            if hasattr(module, name):
                setattr(module, name, mock_run)
                break

        try:
            # Run sweep from 0.05 to 0.20 with step 0.05 -> 4 iterations
            module.run_sweep("economy.extraction_efficiency", 0.05, 0.20, 0.05)

            # Should have called simulation 4 times (0.05, 0.10, 0.15, 0.20)
            assert call_count == 4, f"Expected 4 iterations, got {call_count}"
        finally:
            # Restore original
            if original_run is not None:
                for name in ["run_simulation", "run_single_simulation"]:
                    if hasattr(module, name):
                        setattr(module, name, original_run)
                        break

    def test_sweep_returns_results_list(self) -> None:
        """Verify run_sweep returns a list of results."""
        module = load_tune_parameters_module()

        # Mock the simulation to return quickly
        def mock_run(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
            return {
                "ticks_survived": 50,
                "max_tension": 0.3,
                "outcome": "SURVIVED",
            }

        original_run = None
        for name in ["run_simulation", "run_single_simulation"]:
            if hasattr(module, name):
                original_run = getattr(module, name)
                setattr(module, name, mock_run)
                break

        try:
            results = module.run_sweep("economy.extraction_efficiency", 0.1, 0.2, 0.1)

            assert isinstance(results, list), f"Expected list, got {type(results)}"
            assert len(results) > 0, "Expected non-empty results list"

            # Check each result has required fields
            for result in results:
                assert "value" in result, "Result missing 'value'"
                assert "ticks_survived" in result, "Result missing 'ticks_survived'"
        finally:
            if original_run is not None:
                for name in ["run_simulation", "run_single_simulation"]:
                    if hasattr(module, name):
                        setattr(module, name, original_run)
                        break


class TestIntegration:
    """Integration tests that run actual simulations (slower)."""

    @pytest.mark.integration
    def test_actual_sweep_with_low_extraction(self) -> None:
        """Verify sweep runs actual simulation with low extraction values."""
        module = load_tune_parameters_module()

        # Run a minimal sweep with low extraction (should survive longer)
        results = module.run_sweep(
            "economy.extraction_efficiency",
            start=0.1,
            end=0.2,
            step=0.1,
        )

        assert len(results) >= 2, "Expected at least 2 results"

        # With low extraction, periphery should survive longer
        low_extraction_result = results[0]  # 0.1
        assert low_extraction_result["ticks_survived"] > 0, (
            "Periphery should survive some ticks with low extraction"
        )

    @pytest.mark.integration
    def test_high_extraction_causes_earlier_death(self) -> None:
        """Verify high extraction causes death sooner than low extraction."""
        module = load_tune_parameters_module()

        results = module.run_sweep(
            "economy.extraction_efficiency",
            start=0.1,
            end=0.9,
            step=0.4,  # Test 0.1, 0.5, 0.9
        )

        # Find results for low and high extraction
        low_result = next((r for r in results if r["value"] == 0.1), None)
        high_result = next((r for r in results if r["value"] == 0.9), None)

        assert low_result is not None, "Missing result for extraction=0.1"
        assert high_result is not None, "Missing result for extraction=0.9"

        # High extraction should cause death sooner (fewer ticks survived)
        assert low_result["ticks_survived"] >= high_result["ticks_survived"], (
            f"Low extraction ({low_result['ticks_survived']} ticks) should survive >= "
            f"high extraction ({high_result['ticks_survived']} ticks)"
        )
