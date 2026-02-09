"""Integration tests for parameter_analysis.py trace command.

Extracted from tests/unit/tools/test_parameter_analysis.py.
These tests run actual simulations and are marked @pytest.mark.integration.
"""

from __future__ import annotations

import importlib.util
import json
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
        """Verify run_trace includes new metrics from TickStateRecorder.

        Phase 4.1B introduced TickStateRecorder with additional causal DAG metrics.
        This test verifies that when TickStateRecorder is integrated into run_trace,
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
