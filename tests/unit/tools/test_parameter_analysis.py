"""TDD tests for parameter_analysis.py trace command.

Phase 1: RED - These tests verify the parameter_analysis tool can trace
simulation state over time and output to CSV.

Test Classes:
    TestModuleStructure: Verify module exists and has required functions
    TestRunTrace: Verify trace execution returns correct data structure
    TestWriteCsv: Verify CSV output functionality
    TestCLI: Verify command-line interface works correctly

Integration tests (TestIntegration) relocated to tests/integration/tools/.

Note:
    TestExtractSweepSummary tests are skipped pending refactor to use
    TickStateRecorder instead of manual trace_data extraction.
"""

from __future__ import annotations

import csv
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
# Postgres are gated behind ``BABYLON_TEST_PG_DSN``; tests against the
# old TickStateRecorder-shaped result are skipped because the contract
# is gone (the new ``extract_sweep_summary(value, result_dict)`` no
# longer accepts a collector).
_NO_PG = os.environ.get("BABYLON_TEST_PG_DSN") is None
_SKIP_LEGACY_RECORDER = pytest.mark.skip(
    reason="spec-064: extract_sweep_summary now accepts (value, result_dict); "
    "TickStateRecorder-shaped tests retired with the legacy in-memory engine path",
)
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


@_SKIP_LEGACY_RECORDER
class TestRunTrace:
    """Test the run_trace function.

    Spec-064: ``run_trace`` no longer returns
    ``(TickStateRecorder, SimulationConfig, GameDefines)``; it returns
    ``(Path, GameDefines)`` (path to the headless runner's trace.csv).
    The TickStateRecorder-shaped tests below are retired with the
    legacy in-memory engine path.
    """

    def test_run_trace_returns_collector_config_defines(self) -> None:
        """Verify run_trace returns (TickStateRecorder, SimulationConfig, GameDefines)."""
        from babylon.config.defines import GameDefines
        from babylon.engine.observers.metrics import TickStateRecorder
        from babylon.models.config import SimulationConfig

        module = load_parameter_analysis_module()

        collector, config, defines = module.run_trace(max_ticks=3)

        assert isinstance(collector, TickStateRecorder), (
            f"Expected TickStateRecorder, got {type(collector)}"
        )
        assert isinstance(config, SimulationConfig), (
            f"Expected SimulationConfig, got {type(config)}"
        )
        assert isinstance(defines, GameDefines), f"Expected GameDefines, got {type(defines)}"

        # to_csv_rows() should return list of dicts
        rows = collector.to_csv_rows()
        assert isinstance(rows, list), "to_csv_rows should return list"
        assert len(rows) > 0, "Should have at least one row"
        assert all(isinstance(item, dict) for item in rows), "All items should be dicts"

    def test_run_trace_respects_tick_limit(self) -> None:
        """Verify run_trace stops at max_ticks."""
        module = load_parameter_analysis_module()

        collector, _config, _defines = module.run_trace(max_ticks=5)
        result = collector.to_csv_rows()

        # Should have at most 5 ticks (could be fewer if entity dies)
        assert len(result) <= 5, f"Expected <= 5 ticks, got {len(result)}"
        assert len(result) > 0, "Should have at least 1 tick"

    def test_run_trace_tick_numbers_sequential(self) -> None:
        """Verify tick numbers in result are sequential starting from 0."""
        module = load_parameter_analysis_module()

        collector, _config, _defines = module.run_trace(max_ticks=5)
        result = collector.to_csv_rows()

        # Tick numbers should be 0, 1, 2, ... in order
        for i, tick_data in enumerate(result):
            assert tick_data["tick"] == i, f"Expected tick {i}, got {tick_data['tick']}"

    def test_run_trace_with_custom_param(self) -> None:
        """Verify run_trace can inject a custom parameter value."""
        module = load_parameter_analysis_module()

        # Run with default extraction
        collector_default, _, _ = module.run_trace(max_ticks=10)
        result_default = collector_default.to_csv_rows()

        # Run with very low extraction (should survive longer)
        collector_low, _, _ = module.run_trace(
            param_path="economy.extraction_efficiency",
            param_value=0.01,
            max_ticks=10,
        )
        result_low = collector_low.to_csv_rows()

        # Both should produce results
        assert len(result_default) > 0, "Default trace should produce results"
        assert len(result_low) > 0, "Low extraction trace should produce results"


@_SKIP_LEGACY_RECORDER
class TestWriteCsv:
    """Spec-064: write_csv tests exercise the legacy
    TickStateRecorder-derived CSV shape (entity_id/edge columns); the
    headless runner emits a different 22-column trace.csv contract."""

    """Test CSV writing functionality."""

    def test_write_csv_creates_file(self, tmp_path: Path) -> None:
        """Verify write_csv creates a CSV file at the specified path."""
        module = load_parameter_analysis_module()

        output_path = tmp_path / "test_trace.csv"
        data = [
            {"tick": 0, "p_w_wealth": 10.0, "p_c_wealth": 20.0},
            {"tick": 1, "p_w_wealth": 9.5, "p_c_wealth": 20.5},
        ]

        module.write_csv(data, output_path)

        assert output_path.exists(), f"CSV file not created at {output_path}"

    def test_csv_has_required_columns(self, tmp_path: Path) -> None:
        """Verify CSV output has the required column headers."""
        module = load_parameter_analysis_module()

        output_path = tmp_path / "test_columns.csv"

        # Run a trace and write to CSV
        collector, _config, _defines = module.run_trace(max_ticks=3)
        trace_data = collector.to_csv_rows()
        module.write_csv(trace_data, output_path)

        # Read CSV and check columns
        with open(output_path, newline="") as f:
            reader = csv.DictReader(f)
            columns = reader.fieldnames or []

        # Required columns
        required_columns = [
            "tick",
            "p_w_wealth",
            "p_w_consciousness",
            "p_w_psa",
            "p_w_psr",
            "p_w_organization",
            "p_c_wealth",
            "c_b_wealth",
            "c_w_wealth",
            "c_w_consciousness",
        ]

        for col in required_columns:
            assert col in columns, f"CSV missing required column: {col}"

    def test_csv_data_readable(self, tmp_path: Path) -> None:
        """Verify CSV data can be read and parsed correctly."""
        module = load_parameter_analysis_module()

        output_path = tmp_path / "test_readable.csv"

        # Run a trace and write to CSV
        collector, _config, _defines = module.run_trace(max_ticks=3)
        trace_data = collector.to_csv_rows()
        module.write_csv(trace_data, output_path)

        # Read CSV and verify we can parse rows
        with open(output_path, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) > 0, "CSV should have data rows"
        assert len(rows) <= 3, "CSV should have at most 3 rows (max_ticks=3)"

        # First row should have tick=0
        assert rows[0]["tick"] == "0", f"First row tick should be 0, got {rows[0]['tick']}"


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


@_SKIP_LEGACY_RECORDER
class TestExtractSweepSummary:
    """Tests for extract_sweep_summary function with TickStateRecorder.

    Tests verify that extract_sweep_summary correctly extracts summary
    statistics from a TickStateRecorder instance.
    """

    def test_extract_sweep_summary_exists(self) -> None:
        """extract_sweep_summary function should exist."""
        module = load_parameter_analysis_module()
        assert hasattr(module, "extract_sweep_summary"), "Module missing 'extract_sweep_summary'"
        assert callable(module.extract_sweep_summary)

    def test_extract_sweep_summary_empty_collector(self) -> None:
        """Should handle empty TickStateRecorder gracefully."""
        from babylon.engine.observers.metrics import TickStateRecorder

        module = load_parameter_analysis_module()
        collector = TickStateRecorder(mode="batch")
        # Empty collector has no history, summary is None
        result = module.extract_sweep_summary(collector, 0.1)
        assert result["value"] == 0.1
        assert result["ticks_survived"] == 0
        assert result["outcome"] == "ERROR"

    def test_extract_sweep_summary_basic_fields(self) -> None:
        """Should extract basic summary fields from collector."""
        from babylon.engine.observers.metrics import TickStateRecorder
        from babylon.models.metrics import EdgeMetrics, EntityMetrics, TickMetrics

        module = load_parameter_analysis_module()
        collector = TickStateRecorder(mode="batch")

        # Manually populate history for testing
        tick0 = TickMetrics(
            tick=0,
            p_w=EntityMetrics(
                wealth=0.5,
                consciousness=0.3,
                national_identity=0.5,
                agitation=0.0,
                p_acquiescence=0.8,
                p_revolution=0.1,
                organization=0.2,
            ),
            p_c=EntityMetrics(
                wealth=0.2,
                consciousness=0.0,
                national_identity=0.5,
                agitation=0.0,
                p_acquiescence=0.9,
                p_revolution=0.05,
                organization=0.1,
            ),
            c_b=EntityMetrics(
                wealth=0.9,
                consciousness=0.1,
                national_identity=0.8,
                agitation=0.0,
                p_acquiescence=0.95,
                p_revolution=0.01,
                organization=0.05,
            ),
            c_w=EntityMetrics(
                wealth=0.3,
                consciousness=0.2,
                national_identity=0.6,
                agitation=0.0,
                p_acquiescence=0.85,
                p_revolution=0.08,
                organization=0.15,
            ),
            edges=EdgeMetrics(exploitation_tension=0.1, exploitation_rent=0.05),
        )
        tick1 = TickMetrics(
            tick=1,
            p_w=EntityMetrics(
                wealth=0.4,
                consciousness=0.35,
                national_identity=0.5,
                agitation=0.1,
                p_acquiescence=0.75,
                p_revolution=0.15,
                organization=0.25,
            ),
            p_c=EntityMetrics(
                wealth=0.15,
                consciousness=0.0,
                national_identity=0.5,
                agitation=0.0,
                p_acquiescence=0.88,
                p_revolution=0.06,
                organization=0.1,
            ),
            c_b=EntityMetrics(
                wealth=0.95,
                consciousness=0.1,
                national_identity=0.8,
                agitation=0.0,
                p_acquiescence=0.95,
                p_revolution=0.01,
                organization=0.05,
            ),
            c_w=EntityMetrics(
                wealth=0.28,
                consciousness=0.22,
                national_identity=0.6,
                agitation=0.05,
                p_acquiescence=0.82,
                p_revolution=0.1,
                organization=0.18,
            ),
            edges=EdgeMetrics(exploitation_tension=0.15, exploitation_rent=0.06),
        )

        # Populate collector history
        collector._history = [tick0, tick1]

        result = module.extract_sweep_summary(collector, 0.2)
        assert result["value"] == 0.2
        assert result["ticks_survived"] == 2
        assert result["outcome"] == "SURVIVED"
        assert result["final_p_w_wealth"] == 0.4

    def test_extract_sweep_summary_detects_death(self) -> None:
        """Should detect DIED outcome when wealth <= 0.001."""
        from babylon.engine.observers.metrics import TickStateRecorder
        from babylon.models.metrics import EdgeMetrics, EntityMetrics, TickMetrics

        module = load_parameter_analysis_module()
        collector = TickStateRecorder(mode="batch")

        tick0 = TickMetrics(
            tick=0,
            p_w=EntityMetrics(
                wealth=0.1,
                consciousness=0.3,
                national_identity=0.5,
                agitation=0.0,
                p_acquiescence=0.8,
                p_revolution=0.1,
                organization=0.2,
            ),
            edges=EdgeMetrics(),
        )
        tick1 = TickMetrics(
            tick=1,
            p_w=EntityMetrics(
                wealth=0.0005,  # Dead
                consciousness=0.3,
                national_identity=0.5,
                agitation=0.0,
                p_acquiescence=0.8,
                p_revolution=0.1,
                organization=0.2,
            ),
            edges=EdgeMetrics(),
        )

        collector._history = [tick0, tick1]
        result = module.extract_sweep_summary(collector, 0.3)
        assert result["outcome"] == "DIED"

    def test_extract_sweep_summary_calculates_crossover(self) -> None:
        """Should detect crossover tick when P(S|R) > P(S|A)."""
        from babylon.engine.observers.metrics import TickStateRecorder
        from babylon.models.metrics import EdgeMetrics, EntityMetrics, TickMetrics

        module = load_parameter_analysis_module()
        collector = TickStateRecorder(mode="batch")

        ticks = [
            TickMetrics(
                tick=0,
                p_w=EntityMetrics(
                    wealth=0.5,
                    consciousness=0.3,
                    national_identity=0.5,
                    agitation=0.0,
                    p_acquiescence=0.5,
                    p_revolution=0.1,
                    organization=0.2,
                ),
                edges=EdgeMetrics(),
            ),
            TickMetrics(
                tick=1,
                p_w=EntityMetrics(
                    wealth=0.4,
                    consciousness=0.4,
                    national_identity=0.5,
                    agitation=0.1,
                    p_acquiescence=0.4,
                    p_revolution=0.3,
                    organization=0.3,
                ),
                edges=EdgeMetrics(),
            ),
            TickMetrics(
                tick=2,  # Crossover!
                p_w=EntityMetrics(
                    wealth=0.3,
                    consciousness=0.5,
                    national_identity=0.5,
                    agitation=0.2,
                    p_acquiescence=0.3,
                    p_revolution=0.6,
                    organization=0.4,
                ),
                edges=EdgeMetrics(),
            ),
        ]

        collector._history = ticks
        result = module.extract_sweep_summary(collector, 0.2)
        assert result["crossover_tick"] == 2

    def test_extract_sweep_summary_no_crossover(self) -> None:
        """Should return None for crossover_tick if no crossover."""
        from babylon.engine.observers.metrics import TickStateRecorder
        from babylon.models.metrics import EdgeMetrics, EntityMetrics, TickMetrics

        module = load_parameter_analysis_module()
        collector = TickStateRecorder(mode="batch")

        ticks = [
            TickMetrics(
                tick=0,
                p_w=EntityMetrics(
                    wealth=0.5,
                    consciousness=0.3,
                    national_identity=0.5,
                    agitation=0.0,
                    p_acquiescence=0.5,
                    p_revolution=0.1,
                    organization=0.2,
                ),
                edges=EdgeMetrics(),
            ),
            TickMetrics(
                tick=1,
                p_w=EntityMetrics(
                    wealth=0.5,
                    consciousness=0.35,
                    national_identity=0.5,
                    agitation=0.05,
                    p_acquiescence=0.6,
                    p_revolution=0.2,
                    organization=0.25,
                ),
                edges=EdgeMetrics(),
            ),
        ]

        collector._history = ticks
        result = module.extract_sweep_summary(collector, 0.2)
        assert result["crossover_tick"] is None

    def test_extract_sweep_summary_cumulative_rent(self) -> None:
        """Should calculate cumulative rent extracted."""
        from babylon.engine.observers.metrics import TickStateRecorder
        from babylon.models.metrics import EdgeMetrics, EntityMetrics, TickMetrics

        module = load_parameter_analysis_module()
        collector = TickStateRecorder(mode="batch")

        ticks = [
            TickMetrics(
                tick=0,
                p_w=EntityMetrics(
                    wealth=0.5,
                    consciousness=0.3,
                    national_identity=0.5,
                    agitation=0.0,
                    p_acquiescence=0.8,
                    p_revolution=0.1,
                    organization=0.2,
                ),
                edges=EdgeMetrics(exploitation_rent=0.1),
            ),
            TickMetrics(
                tick=1,
                p_w=EntityMetrics(
                    wealth=0.4,
                    consciousness=0.35,
                    national_identity=0.5,
                    agitation=0.05,
                    p_acquiescence=0.75,
                    p_revolution=0.15,
                    organization=0.25,
                ),
                edges=EdgeMetrics(exploitation_rent=0.15),
            ),
            TickMetrics(
                tick=2,
                p_w=EntityMetrics(
                    wealth=0.3,
                    consciousness=0.4,
                    national_identity=0.5,
                    agitation=0.1,
                    p_acquiescence=0.7,
                    p_revolution=0.2,
                    organization=0.3,
                ),
                edges=EdgeMetrics(exploitation_rent=0.12),
            ),
        ]

        collector._history = ticks
        result = module.extract_sweep_summary(collector, 0.2)
        assert abs(result["cumulative_rent"] - 0.37) < 0.001

    def test_extract_sweep_summary_peak_consciousness(self) -> None:
        """Should track peak consciousness values."""
        from babylon.engine.observers.metrics import TickStateRecorder
        from babylon.models.metrics import EdgeMetrics, EntityMetrics, TickMetrics

        module = load_parameter_analysis_module()
        collector = TickStateRecorder(mode="batch")

        ticks = [
            TickMetrics(
                tick=0,
                p_w=EntityMetrics(
                    wealth=0.5,
                    consciousness=0.4,
                    national_identity=0.5,
                    agitation=0.0,
                    p_acquiescence=0.8,
                    p_revolution=0.1,
                    organization=0.2,
                ),
                c_w=EntityMetrics(
                    wealth=0.3,
                    consciousness=0.3,
                    national_identity=0.6,
                    agitation=0.0,
                    p_acquiescence=0.85,
                    p_revolution=0.08,
                    organization=0.15,
                ),
                edges=EdgeMetrics(),
            ),
            TickMetrics(
                tick=1,
                p_w=EntityMetrics(
                    wealth=0.4,
                    consciousness=0.6,  # Peak
                    national_identity=0.5,
                    agitation=0.1,
                    p_acquiescence=0.7,
                    p_revolution=0.2,
                    organization=0.3,
                ),
                c_w=EntityMetrics(
                    wealth=0.28,
                    consciousness=0.5,  # Peak
                    national_identity=0.6,
                    agitation=0.05,
                    p_acquiescence=0.8,
                    p_revolution=0.12,
                    organization=0.2,
                ),
                edges=EdgeMetrics(),
            ),
            TickMetrics(
                tick=2,
                p_w=EntityMetrics(
                    wealth=0.3,
                    consciousness=0.5,  # Lower than peak
                    national_identity=0.5,
                    agitation=0.15,
                    p_acquiescence=0.65,
                    p_revolution=0.25,
                    organization=0.35,
                ),
                c_w=EntityMetrics(
                    wealth=0.26,
                    consciousness=0.4,  # Lower than peak
                    national_identity=0.6,
                    agitation=0.08,
                    p_acquiescence=0.75,
                    p_revolution=0.15,
                    organization=0.25,
                ),
                edges=EdgeMetrics(),
            ),
        ]

        collector._history = ticks
        result = module.extract_sweep_summary(collector, 0.2)
        assert result["peak_p_w_consciousness"] == 0.6
        assert result["peak_c_w_consciousness"] == 0.5

    def test_extract_sweep_summary_max_tension(self) -> None:
        """Should track max tension."""
        from babylon.engine.observers.metrics import TickStateRecorder
        from babylon.models.metrics import EdgeMetrics, EntityMetrics, TickMetrics

        module = load_parameter_analysis_module()
        collector = TickStateRecorder(mode="batch")

        ticks = [
            TickMetrics(
                tick=0,
                p_w=EntityMetrics(
                    wealth=0.5,
                    consciousness=0.3,
                    national_identity=0.5,
                    agitation=0.0,
                    p_acquiescence=0.8,
                    p_revolution=0.1,
                    organization=0.2,
                ),
                edges=EdgeMetrics(exploitation_tension=0.01),
            ),
            TickMetrics(
                tick=1,
                p_w=EntityMetrics(
                    wealth=0.4,
                    consciousness=0.35,
                    national_identity=0.5,
                    agitation=0.05,
                    p_acquiescence=0.75,
                    p_revolution=0.15,
                    organization=0.25,
                ),
                edges=EdgeMetrics(exploitation_tension=0.05),  # Max
            ),
            TickMetrics(
                tick=2,
                p_w=EntityMetrics(
                    wealth=0.3,
                    consciousness=0.4,
                    national_identity=0.5,
                    agitation=0.1,
                    p_acquiescence=0.7,
                    p_revolution=0.2,
                    organization=0.3,
                ),
                edges=EdgeMetrics(exploitation_tension=0.03),
            ),
        ]

        collector._history = ticks
        result = module.extract_sweep_summary(collector, 0.2)
        assert result["max_tension"] == 0.05


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

    @_SKIP_LEGACY_RECORDER
    def test_run_sweep_result_has_entity_final_states(self) -> None:
        """Each result should have final wealth for all entities.

        Spec-064: per-entity final wealth keys (final_p_w_wealth,
        final_p_c_wealth, final_c_b_wealth, final_c_w_wealth) are gone
        with the legacy in-memory imperial-circuit scenario. The new
        result dict only carries scope-level ``final_wealth``.
        """
        module = load_parameter_analysis_module()
        result = module.run_sweep(
            param_path="economy.extraction_efficiency",
            start=0.1,
            end=0.1,
            step_size=0.1,
            max_ticks=5,
        )
        assert "final_p_w_wealth" in result[0]
        assert "final_p_c_wealth" in result[0]
        assert "final_c_b_wealth" in result[0]
        assert "final_c_w_wealth" in result[0]


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
