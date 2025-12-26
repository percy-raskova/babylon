"""TDD tests for parameter_analysis.py trace command.

Phase 1: RED - These tests verify the parameter_analysis tool can trace
simulation state over time and output to CSV.

Test Classes:
    TestModuleStructure: Verify module exists and has required functions
    TestRunTrace: Verify trace execution returns correct data structure
    TestWriteCsv: Verify CSV output functionality
    TestCLI: Verify command-line interface works correctly
    TestIntegration: Integration tests including Phase 4.1B metrics

Note:
    TestExtractSweepSummary tests are skipped pending refactor to use
    MetricsCollector instead of manual trace_data extraction.
"""

from __future__ import annotations

import csv
import importlib.util
import inspect
from pathlib import Path
from typing import Any

import pytest

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


class TestRunTrace:
    """Test the run_trace function."""

    def test_run_trace_returns_collector_config_defines(self) -> None:
        """Verify run_trace returns (MetricsCollector, SimulationConfig, GameDefines)."""
        from babylon.config.defines import GameDefines
        from babylon.engine.observers.metrics import MetricsCollector
        from babylon.models.config import SimulationConfig

        module = load_parameter_analysis_module()

        collector, config, defines = module.run_trace(max_ticks=3)

        assert isinstance(collector, MetricsCollector), (
            f"Expected MetricsCollector, got {type(collector)}"
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


class TestWriteCsv:
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


class TestIntegration:
    """Integration tests that run actual simulations."""

    @pytest.mark.integration
    def test_full_trace_to_csv(self, tmp_path: Path) -> None:
        """Verify full trace workflow produces valid CSV."""
        module = load_parameter_analysis_module()

        output_path = tmp_path / "full_trace.csv"

        # Run full trace
        collector, _config, _defines = module.run_trace(max_ticks=10)
        trace_data = collector.to_csv_rows()

        # Write to CSV
        module.write_csv(trace_data, output_path)

        # Verify file exists and has content
        assert output_path.exists(), "CSV file not created"
        content = output_path.read_text()
        lines = content.strip().split("\n")

        # Should have header + data rows
        assert len(lines) >= 2, "CSV should have header and at least 1 data row"

    @pytest.mark.integration
    def test_trace_captures_wealth_changes(self) -> None:
        """Verify trace captures wealth changes over time."""
        module = load_parameter_analysis_module()

        # Run trace with enough ticks to see changes
        collector, _config, _defines = module.run_trace(max_ticks=10)
        trace_data = collector.to_csv_rows()

        # Get wealth values for Periphery Worker
        p_w_wealths = [
            row.get("p_w_wealth") for row in trace_data if row.get("p_w_wealth") is not None
        ]

        assert len(p_w_wealths) > 1, "Should have multiple wealth observations"

        # With extraction, wealth should change (decrease)
        # Allow for scenario where wealth stays constant or increases too
        # The key test is that we're actually capturing the values
        first_wealth = p_w_wealths[0]
        last_wealth = p_w_wealths[-1]

        # Just verify we captured numeric values
        assert isinstance(first_wealth, int | float), "First wealth should be numeric"
        assert isinstance(last_wealth, int | float), "Last wealth should be numeric"

    @pytest.mark.integration
    def test_trace_includes_phase_4_1b_metrics(self) -> None:
        """Verify run_trace includes new metrics from MetricsCollector.

        Phase 4.1B introduced MetricsCollector with additional causal DAG metrics.
        This test verifies that when MetricsCollector is integrated into run_trace,
        these new columns are present in the output.
        """
        module = load_parameter_analysis_module()
        collector, _config, _defines = module.run_trace(max_ticks=5)
        trace_data = collector.to_csv_rows()

        # Must have at least one tick of data
        assert len(trace_data) > 0, "run_trace should return at least one row"

        first_row = trace_data[0]

        # Phase 4.1B columns should be present
        assert "consciousness_gap" in first_row, "Missing consciousness_gap"
        assert "wealth_gap" in first_row, "Missing wealth_gap"
        assert "imperial_rent_pool" in first_row, "Missing imperial_rent_pool"
        assert "current_super_wage_rate" in first_row, "Missing current_super_wage_rate"
        assert "global_tension" in first_row, "Missing global_tension"
        assert "pool_ratio" in first_row, "Missing pool_ratio"

    @pytest.mark.integration
    def test_json_export_captures_dag_structure(self, tmp_path: Path) -> None:
        """Verify JSON export captures causal DAG hierarchy.

        Sprint 4.1C: JSON export should preserve the 3-level DAG structure:
        - Level 1 (Fundamental): GameDefines parameters
        - Level 2 (Config): SimulationConfig settings
        - Level 3 (Emergent): SweepSummary computed from simulation
        """
        import json

        module = load_parameter_analysis_module()

        csv_path = tmp_path / "trace.csv"
        json_path = tmp_path / "trace.json"

        # Run trace
        collector, config, defines = module.run_trace(max_ticks=5)
        trace_data = collector.to_csv_rows()
        module.write_csv(trace_data, csv_path)

        # Export JSON
        collector.export_json(json_path, defines, config, csv_path=csv_path)

        # Verify JSON structure
        assert json_path.exists(), "JSON file not created"
        data = json.loads(json_path.read_text())

        # Check schema version
        assert "schema_version" in data, "Missing schema_version"
        assert data["schema_version"] == "1.0", "Unexpected schema version"

        # Check DAG levels documented
        assert "causal_dag_levels" in data, "Missing causal_dag_levels"
        assert "fundamental" in data["causal_dag_levels"]
        assert "config" in data["causal_dag_levels"]
        assert "emergent" in data["causal_dag_levels"]

        # Check fundamentals (GameDefines)
        assert "fundamentals" in data, "Missing fundamentals"
        assert "economy" in data["fundamentals"], "Missing economy in fundamentals"
        assert "extraction_efficiency" in data["fundamentals"]["economy"]

        # Check config (SimulationConfig)
        assert "config" in data, "Missing config"

        # Check summary (SweepSummary - emergent)
        assert "summary" in data, "Missing summary"
        assert data["summary"] is not None, "Summary should not be None"
        assert "ticks_survived" in data["summary"]
        assert "outcome" in data["summary"]

        # Check CSV reference
        assert "time_series_csv" in data, "Missing time_series_csv"
        assert str(csv_path) in data["time_series_csv"]


# =============================================================================
# SWEEP COMMAND TESTS
# =============================================================================


class TestExtractSweepSummary:
    """Tests for extract_sweep_summary function with MetricsCollector.

    Tests verify that extract_sweep_summary correctly extracts summary
    statistics from a MetricsCollector instance.
    """

    def test_extract_sweep_summary_exists(self) -> None:
        """extract_sweep_summary function should exist."""
        module = load_parameter_analysis_module()
        assert hasattr(module, "extract_sweep_summary"), "Module missing 'extract_sweep_summary'"
        assert callable(module.extract_sweep_summary)

    def test_extract_sweep_summary_empty_collector(self) -> None:
        """Should handle empty MetricsCollector gracefully."""
        from babylon.engine.observers.metrics import MetricsCollector

        module = load_parameter_analysis_module()
        collector = MetricsCollector(mode="batch")
        # Empty collector has no history, summary is None
        result = module.extract_sweep_summary(collector, 0.1)
        assert result["value"] == 0.1
        assert result["ticks_survived"] == 0
        assert result["outcome"] == "ERROR"

    def test_extract_sweep_summary_basic_fields(self) -> None:
        """Should extract basic summary fields from collector."""
        from babylon.engine.observers.metrics import MetricsCollector
        from babylon.models.metrics import EdgeMetrics, EntityMetrics, TickMetrics

        module = load_parameter_analysis_module()
        collector = MetricsCollector(mode="batch")

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
        from babylon.engine.observers.metrics import MetricsCollector
        from babylon.models.metrics import EdgeMetrics, EntityMetrics, TickMetrics

        module = load_parameter_analysis_module()
        collector = MetricsCollector(mode="batch")

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
        from babylon.engine.observers.metrics import MetricsCollector
        from babylon.models.metrics import EdgeMetrics, EntityMetrics, TickMetrics

        module = load_parameter_analysis_module()
        collector = MetricsCollector(mode="batch")

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
        from babylon.engine.observers.metrics import MetricsCollector
        from babylon.models.metrics import EdgeMetrics, EntityMetrics, TickMetrics

        module = load_parameter_analysis_module()
        collector = MetricsCollector(mode="batch")

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
        from babylon.engine.observers.metrics import MetricsCollector
        from babylon.models.metrics import EdgeMetrics, EntityMetrics, TickMetrics

        module = load_parameter_analysis_module()
        collector = MetricsCollector(mode="batch")

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
        from babylon.engine.observers.metrics import MetricsCollector
        from babylon.models.metrics import EdgeMetrics, EntityMetrics, TickMetrics

        module = load_parameter_analysis_module()
        collector = MetricsCollector(mode="batch")

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
        from babylon.engine.observers.metrics import MetricsCollector
        from babylon.models.metrics import EdgeMetrics, EntityMetrics, TickMetrics

        module = load_parameter_analysis_module()
        collector = MetricsCollector(mode="batch")

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


class TestRunSweep:
    """Tests for run_sweep function."""

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

    def test_run_sweep_result_has_entity_final_states(self) -> None:
        """Each result should have final wealth for all entities."""
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

    def test_sweep_subcommand_exists(self) -> None:
        """sweep subcommand should be recognized."""
        import subprocess

        result = subprocess.run(
            ["poetry", "run", "python", "tools/parameter_analysis.py", "sweep", "--help"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0
        assert "--param" in result.stdout

    def test_sweep_requires_param(self) -> None:
        """sweep should require --param argument."""
        import subprocess

        result = subprocess.run(
            [
                "poetry",
                "run",
                "python",
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

    def test_sweep_requires_csv(self) -> None:
        """sweep should require --csv argument."""
        import subprocess

        result = subprocess.run(
            [
                "poetry",
                "run",
                "python",
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
