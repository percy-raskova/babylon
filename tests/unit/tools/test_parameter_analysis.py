"""TDD tests for parameter_analysis.py trace command.

Phase 1: RED - These tests verify the parameter_analysis tool can trace
simulation state over time and output to CSV.

Test Classes:
    TestModuleStructure: Verify module exists and has required functions
    TestCLI: Verify command-line interface works correctly

Integration tests (TestIntegration) relocated to tests/integration/tools/.
"""

from __future__ import annotations

import importlib.util
import inspect
import os
import sys
from pathlib import Path
from typing import Any

import pytest

# Spec-064 transition: classes that exercise the legacy in-memory
# `run_trace` / `run_sweep` / `extract_sweep_summary` contracts now run
# through the headless Postgres-backed runner instead. Tests that hit
# Postgres are gated behind ``BABYLON_TEST_PG_DSN``.
_NO_PG = os.environ.get("BABYLON_TEST_PG_DSN") is None
_SKIP_NEEDS_PG = pytest.mark.skipif(
    _NO_PG,
    reason="spec-064: run_trace/run_sweep route through headless_runner; "
    "BABYLON_TEST_PG_DSN required",
)

# Path to the project root (babylon/)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

# Path to the parameter_analysis tool
PARAMETER_ANALYSIS_PATH = PROJECT_ROOT / "tools" / "parameter_analysis.py"


def load_parameter_analysis_module() -> Any:
    """Load the parameter_analysis module dynamically.

    Returns:
        The loaded module object

    Raises:
        FileNotFoundError: If parameter_analysis.py does not exist
    """
    if not PARAMETER_ANALYSIS_PATH.exists():
        pytest.skip(f"parameter_analysis.py not found at {PARAMETER_ANALYSIS_PATH}")

    spec = importlib.util.spec_from_file_location("parameter_analysis", PARAMETER_ANALYSIS_PATH)
    if spec is None or spec.loader is None:
        pytest.fail("Failed to load parameter_analysis module spec")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestModuleStructure:
    """Test that parameter_analysis.py has the required structure."""

    def test_module_exists(self) -> None:
        """Verify parameter_analysis.py exists at expected path."""
        assert PARAMETER_ANALYSIS_PATH.exists(), (
            f"parameter_analysis.py not found at {PARAMETER_ANALYSIS_PATH}"
        )

    def test_run_trace_function_exists(self) -> None:
        """Verify run_trace function exists in module."""
        module = load_parameter_analysis_module()
        assert hasattr(module, "run_trace"), "Module missing 'run_trace' function"
        assert callable(module.run_trace), "'run_trace' is not callable"

    def test_write_csv_function_exists(self) -> None:
        """Verify write_csv function exists in module."""
        module = load_parameter_analysis_module()
        assert hasattr(module, "write_csv"), "Module missing 'write_csv' function"
        assert callable(module.write_csv), "'write_csv' is not callable"

    def test_main_function_exists(self) -> None:
        """Verify main function exists for CLI entry point."""
        module = load_parameter_analysis_module()
        assert hasattr(module, "main"), "Module missing 'main' function"
        assert callable(module.main), "'main' is not callable"

    def test_run_trace_signature(self) -> None:
        """Verify run_trace has correct parameter signature."""
        module = load_parameter_analysis_module()
        sig = inspect.signature(module.run_trace)
        param_names = list(sig.parameters.keys())

        assert "param_path" in param_names, "Missing 'param_path' parameter"
        assert "param_value" in param_names, "Missing 'param_value' parameter"
        assert "max_ticks" in param_names, "Missing 'max_ticks' parameter"

    def test_entity_ids_constant(self) -> None:
        """Verify ENTITY_IDS constant is defined with expected values."""
        module = load_parameter_analysis_module()
        assert hasattr(module, "ENTITY_IDS"), "Module missing 'ENTITY_IDS' constant"
        assert "C001" in module.ENTITY_IDS, "ENTITY_IDS missing C001 (Periphery Worker)"
        assert "C002" in module.ENTITY_IDS, "ENTITY_IDS missing C002 (Comprador)"
        assert "C003" in module.ENTITY_IDS, "ENTITY_IDS missing C003 (Core Bourgeoisie)"
        assert "C004" in module.ENTITY_IDS, "ENTITY_IDS missing C004 (Labor Aristocracy)"

    def test_has_main_block(self) -> None:
        """Verify module has if __name__ == '__main__' block."""
        source_code = PARAMETER_ANALYSIS_PATH.read_text()
        assert "if __name__" in source_code, "Missing main execution block"
        assert "__main__" in source_code, "Missing __main__ check"


class TestCLI:
    """Test command-line interface."""

    def test_trace_subcommand_exists(self) -> None:
        """Verify trace is a valid subcommand."""
        source_code = PARAMETER_ANALYSIS_PATH.read_text()

        # Should have trace subcommand defined
        assert "trace" in source_code, "Missing 'trace' subcommand"
        assert "subparsers" in source_code or "add_parser" in source_code, (
            "Missing subparser setup for trace command"
        )

    def test_csv_argument_required_for_trace(self) -> None:
        """Verify --csv argument exists for trace command."""
        source_code = PARAMETER_ANALYSIS_PATH.read_text()

        assert "--csv" in source_code, "Missing --csv argument for trace command"

    def test_ticks_argument_exists(self) -> None:
        """Verify --ticks argument exists for trace command."""
        source_code = PARAMETER_ANALYSIS_PATH.read_text()

        assert "--ticks" in source_code, "Missing --ticks argument for trace command"

    def test_param_argument_exists(self) -> None:
        """Verify --param argument exists for trace command."""
        source_code = PARAMETER_ANALYSIS_PATH.read_text()

        assert "--param" in source_code, "Missing --param argument for trace command"


# =============================================================================
# SWEEP COMMAND TESTS
# =============================================================================


@_SKIP_NEEDS_PG
@pytest.mark.slow
class TestRunSweep:
    """Tests for run_sweep function.

    Marked ``slow``: every method (except the existence check) drives real
    multi-tick engine sweeps through the headless runner — 80-290s each,
    ~1075s total (measured 2026-07-11). They run via ``mise run test:slow``
    locally and the CI heavy shard (``test:rest-ci``), not the fast gate.
    """

    def test_run_sweep_function_exists(self) -> None:
        """run_sweep() function should exist."""
        module = load_parameter_analysis_module()
        assert hasattr(module, "run_sweep"), "Module missing 'run_sweep'"
        assert callable(module.run_sweep)

    def test_run_sweep_returns_list(self) -> None:
        """run_sweep should return a list."""
        module = load_parameter_analysis_module()
        result = module.run_sweep(
            param_path="economy.extraction_efficiency",
            start=0.1,
            end=0.2,
            step_size=0.1,
            max_ticks=5,
        )
        assert isinstance(result, list)

    def test_run_sweep_list_has_correct_length(self) -> None:
        """run_sweep should return one result per parameter value."""
        module = load_parameter_analysis_module()
        result = module.run_sweep(
            param_path="economy.extraction_efficiency",
            start=0.1,
            end=0.3,
            step_size=0.1,
            max_ticks=5,
        )
        # 0.1, 0.2, 0.3 = 3 values
        assert len(result) == 3

    def test_run_sweep_result_has_value_key(self) -> None:
        """Each result dict should have 'value' key."""
        module = load_parameter_analysis_module()
        result = module.run_sweep(
            param_path="economy.extraction_efficiency",
            start=0.1,
            end=0.1,
            step_size=0.1,
            max_ticks=5,
        )
        assert "value" in result[0]
        assert result[0]["value"] == 0.1

    def test_run_sweep_result_has_ticks_survived(self) -> None:
        """Each result dict should have 'ticks_survived' key."""
        module = load_parameter_analysis_module()
        result = module.run_sweep(
            param_path="economy.extraction_efficiency",
            start=0.1,
            end=0.1,
            step_size=0.1,
            max_ticks=5,
        )
        assert "ticks_survived" in result[0]
        assert isinstance(result[0]["ticks_survived"], int)

    def test_run_sweep_result_has_outcome(self) -> None:
        """Each result should have 'outcome' (SURVIVED or DIED)."""
        module = load_parameter_analysis_module()
        result = module.run_sweep(
            param_path="economy.extraction_efficiency",
            start=0.1,
            end=0.1,
            step_size=0.1,
            max_ticks=5,
        )
        assert "outcome" in result[0]
        assert result[0]["outcome"] in ("SURVIVED", "DIED", "ERROR")


class TestSweepCLI:
    """Tests for sweep CLI subcommand."""

    @pytest.mark.slow
    def test_sweep_subcommand_exists(self) -> None:
        """sweep subcommand should be recognized."""
        import subprocess

        result = subprocess.run(
            [sys.executable, "tools/parameter_analysis.py", "sweep", "--help"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0
        assert "--param" in result.stdout

    @pytest.mark.slow
    def test_sweep_requires_param(self) -> None:
        """sweep should require --param argument."""
        import subprocess

        result = subprocess.run(
            [
                sys.executable,
                "tools/parameter_analysis.py",
                "sweep",
                "--start",
                "0.1",
                "--end",
                "0.2",
                "--step",
                "0.1",
                "--csv",
                "/tmp/test.csv",
            ],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode != 0

    @pytest.mark.slow
    def test_sweep_requires_csv(self) -> None:
        """sweep should require --csv argument."""
        import subprocess

        result = subprocess.run(
            [
                sys.executable,
                "tools/parameter_analysis.py",
                "sweep",
                "--param",
                "economy.extraction_efficiency",
                "--start",
                "0.1",
                "--end",
                "0.2",
                "--step",
                "0.1",
            ],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode != 0
