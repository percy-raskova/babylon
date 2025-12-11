"""TDD tests for vertical_slice.py Imperial Circuit refactoring.

Phase 1: RED - These tests verify the vertical_slice tool uses
the 4-node Imperial Circuit scenario instead of the 2-node scenario.

Test Classes:
    TestImports: Verify correct scenario import
    TestStructuredLoggerImperialCircuit: Updated log_tick signature
    TestDisplayTickStateImperialCircuit: 4-entity Rich Table
    TestDisplayFinalSummaryImperialCircuit: Extraction/Bribery analysis
"""

from __future__ import annotations

import ast
import inspect
from io import StringIO
from pathlib import Path
from typing import Any

import pytest
from rich.console import Console

# We need to import the module to inspect its functions
# The tests will fail initially because the signatures don't match

# Get the path to vertical_slice.py
VERTICAL_SLICE_PATH = Path(__file__).parent.parent.parent.parent / "tools" / "vertical_slice.py"


class TestImports:
    """Test that vertical_slice.py imports the correct scenario function."""

    def test_imports_imperial_circuit_scenario(self) -> None:
        """Verify vertical_slice imports create_imperial_circuit_scenario."""
        source_code = VERTICAL_SLICE_PATH.read_text()
        tree = ast.parse(source_code)

        # Find all ImportFrom nodes
        imports_from_scenarios = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "babylon.engine.scenarios":
                for alias in node.names:
                    imports_from_scenarios.append(alias.name)

        assert "create_imperial_circuit_scenario" in imports_from_scenarios, (
            f"Expected 'create_imperial_circuit_scenario' in imports from babylon.engine.scenarios, "
            f"found: {imports_from_scenarios}"
        )

    def test_does_not_import_two_node_scenario(self) -> None:
        """Verify vertical_slice does NOT import create_two_node_scenario."""
        source_code = VERTICAL_SLICE_PATH.read_text()
        tree = ast.parse(source_code)

        # Find all ImportFrom nodes
        imports_from_scenarios = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "babylon.engine.scenarios":
                for alias in node.names:
                    imports_from_scenarios.append(alias.name)

        assert "create_two_node_scenario" not in imports_from_scenarios, (
            "Expected 'create_two_node_scenario' to NOT be imported, "
            "but it was found in imports from babylon.engine.scenarios"
        )


class TestStructuredLoggerImperialCircuit:
    """Test StructuredLogger.log_tick() signature for 4-node Imperial Circuit."""

    @pytest.fixture
    def logger_class(self) -> type[Any]:
        """Get StructuredLogger class from vertical_slice module."""
        import importlib.util

        spec = importlib.util.spec_from_file_location("vertical_slice", VERTICAL_SLICE_PATH)
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.StructuredLogger

    def test_log_tick_accepts_four_entity_wealths(
        self, logger_class: type[Any], tmp_path: Path
    ) -> None:
        """Verify log_tick accepts p_w_wealth, p_c_wealth, c_b_wealth, c_w_wealth."""
        log_path = tmp_path / "test.json"
        logger = logger_class(log_path)

        sig = inspect.signature(logger.log_tick)
        param_names = list(sig.parameters.keys())

        # Must have all 4 entity wealth parameters
        assert "p_w_wealth" in param_names, f"Missing 'p_w_wealth' in {param_names}"
        assert "p_c_wealth" in param_names, f"Missing 'p_c_wealth' in {param_names}"
        assert "c_b_wealth" in param_names, f"Missing 'c_b_wealth' in {param_names}"
        assert "c_w_wealth" in param_names, f"Missing 'c_w_wealth' in {param_names}"

        # Must NOT have old 2-node parameters
        assert "worker_wealth" not in param_names, "Old 'worker_wealth' param should be removed"
        assert "owner_wealth" not in param_names, "Old 'owner_wealth' param should be removed"

    def test_log_tick_accepts_imperial_rent_pool(
        self, logger_class: type[Any], tmp_path: Path
    ) -> None:
        """Verify log_tick accepts imperial_rent_pool parameter."""
        log_path = tmp_path / "test.json"
        logger = logger_class(log_path)

        sig = inspect.signature(logger.log_tick)
        param_names = list(sig.parameters.keys())

        assert "imperial_rent_pool" in param_names, f"Missing 'imperial_rent_pool' in {param_names}"

    def test_log_tick_accepts_super_wage_rate(
        self, logger_class: type[Any], tmp_path: Path
    ) -> None:
        """Verify log_tick accepts super_wage_rate parameter."""
        log_path = tmp_path / "test.json"
        logger = logger_class(log_path)

        sig = inspect.signature(logger.log_tick)
        param_names = list(sig.parameters.keys())

        assert "super_wage_rate" in param_names, f"Missing 'super_wage_rate' in {param_names}"

    def test_log_tick_output_structure(self, logger_class: type[Any], tmp_path: Path) -> None:
        """Verify log_tick produces correct JSON structure with 4 entities."""
        import json

        log_path = tmp_path / "test.json"
        logger = logger_class(log_path)

        # Call log_tick with 4-node signature
        logger.log_tick(
            tick=1,
            p_w_wealth=0.08,
            p_c_wealth=0.24,
            c_b_wealth=0.92,
            c_w_wealth=0.20,
            imperial_rent_pool=98.5,
            super_wage_rate=0.2,
            tension=0.1,
            value_flow=0.02,
            events=["SURPLUS_EXTRACTION: test"],
        )

        # Read and verify log structure
        log_data = json.loads(log_path.read_text())
        tick_event = [e for e in log_data["events"] if e["event_type"] == "simulation_tick"][0]

        # Verify entities structure
        assert "entities" in tick_event["data"], "Missing 'entities' in tick data"
        entities = tick_event["data"]["entities"]
        assert "C001_periphery_worker" in entities
        assert "C002_comprador" in entities
        assert "C003_core_bourgeoisie" in entities
        assert "C004_labor_aristocracy" in entities

        # Verify economy structure
        assert "economy" in tick_event["data"], "Missing 'economy' in tick data"
        economy = tick_event["data"]["economy"]
        assert "imperial_rent_pool" in economy
        assert "super_wage_rate" in economy


class TestDisplayTickStateImperialCircuit:
    """Test display_tick_state function for 4-entity Rich Table."""

    @pytest.fixture
    def display_function(self) -> Any:
        """Get display_tick_state function from vertical_slice module."""
        import importlib.util

        spec = importlib.util.spec_from_file_location("vertical_slice", VERTICAL_SLICE_PATH)
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.display_tick_state

    def test_display_accepts_four_entity_wealths(self, display_function: Any) -> None:
        """Verify display_tick_state accepts 4 entity wealth parameters."""
        sig = inspect.signature(display_function)
        param_names = list(sig.parameters.keys())

        # Must have all 4 entity wealth parameters
        assert "p_w_wealth" in param_names, f"Missing 'p_w_wealth' in {param_names}"
        assert "p_c_wealth" in param_names, f"Missing 'p_c_wealth' in {param_names}"
        assert "c_b_wealth" in param_names, f"Missing 'c_b_wealth' in {param_names}"
        assert "c_w_wealth" in param_names, f"Missing 'c_w_wealth' in {param_names}"

        # Must NOT have old 2-node parameters
        assert "worker_wealth" not in param_names, "Old 'worker_wealth' param should be removed"
        assert "owner_wealth" not in param_names, "Old 'owner_wealth' param should be removed"

    def test_display_accepts_global_economy_params(self, display_function: Any) -> None:
        """Verify display_tick_state accepts global economy parameters."""
        sig = inspect.signature(display_function)
        param_names = list(sig.parameters.keys())

        assert "imperial_rent_pool" in param_names, f"Missing 'imperial_rent_pool' in {param_names}"
        assert "super_wage_rate" in param_names, f"Missing 'super_wage_rate' in {param_names}"

    def test_display_shows_four_entities_in_table(self, display_function: Any) -> None:
        """Verify display_tick_state produces table with 4 entity rows."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)

        # Call with 4-node signature
        display_function(
            console=console,
            tick=1,
            p_w_wealth=0.08,
            p_c_wealth=0.24,
            c_b_wealth=0.92,
            c_w_wealth=0.20,
            p_w_p_acquiescence=0.3,
            p_w_p_revolution=0.2,
            imperial_rent_pool=98.5,
            super_wage_rate=0.2,
            tension=0.1,
            value_flow=0.02,
        )

        rendered = output.getvalue()

        # Verify all 4 entity IDs appear
        assert "C001" in rendered, "Missing C001 (Periphery Worker) in output"
        assert "C002" in rendered, "Missing C002 (Comprador) in output"
        assert "C003" in rendered, "Missing C003 (Core Bourgeoisie) in output"
        assert "C004" in rendered, "Missing C004 (Labor Aristocracy) in output"

    def test_display_shows_global_economy_panel(self, display_function: Any) -> None:
        """Verify display_tick_state shows Global Economy panel."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)

        display_function(
            console=console,
            tick=1,
            p_w_wealth=0.08,
            p_c_wealth=0.24,
            c_b_wealth=0.92,
            c_w_wealth=0.20,
            p_w_p_acquiescence=0.3,
            p_w_p_revolution=0.2,
            imperial_rent_pool=98.5,
            super_wage_rate=0.2,
            tension=0.1,
            value_flow=0.02,
        )

        rendered = output.getvalue()

        # Verify Global Economy section appears
        assert "Global Economy" in rendered or "Imperial Rent Pool" in rendered, (
            "Missing Global Economy panel in output"
        )


class TestDisplayFinalSummaryImperialCircuit:
    """Test display_final_summary function for 4-entity wealth transfer analysis."""

    @pytest.fixture
    def summary_function(self) -> Any:
        """Get display_final_summary function from vertical_slice module."""
        import importlib.util

        spec = importlib.util.spec_from_file_location("vertical_slice", VERTICAL_SLICE_PATH)
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.display_final_summary

    def test_summary_accepts_four_initial_values(self, summary_function: Any) -> None:
        """Verify display_final_summary accepts 4 initial wealth values."""
        sig = inspect.signature(summary_function)
        param_names = list(sig.parameters.keys())

        # Must have all 4 initial values
        assert "initial_p_w" in param_names, f"Missing 'initial_p_w' in {param_names}"
        assert "initial_p_c" in param_names, f"Missing 'initial_p_c' in {param_names}"
        assert "initial_c_b" in param_names, f"Missing 'initial_c_b' in {param_names}"
        assert "initial_c_w" in param_names, f"Missing 'initial_c_w' in {param_names}"

        # Must NOT have old 2-node parameters
        assert "initial_worker" not in param_names, "Old 'initial_worker' param should be removed"
        assert "initial_owner" not in param_names, "Old 'initial_owner' param should be removed"

    def test_summary_accepts_four_final_values(self, summary_function: Any) -> None:
        """Verify display_final_summary accepts 4 final wealth values."""
        sig = inspect.signature(summary_function)
        param_names = list(sig.parameters.keys())

        # Must have all 4 final values
        assert "final_p_w" in param_names, f"Missing 'final_p_w' in {param_names}"
        assert "final_p_c" in param_names, f"Missing 'final_p_c' in {param_names}"
        assert "final_c_b" in param_names, f"Missing 'final_c_b' in {param_names}"
        assert "final_c_w" in param_names, f"Missing 'final_c_w' in {param_names}"

        # Must NOT have old 2-node parameters
        assert "final_worker" not in param_names, "Old 'final_worker' param should be removed"
        assert "final_owner" not in param_names, "Old 'final_owner' param should be removed"

    def test_summary_accepts_rent_pool_values(self, summary_function: Any) -> None:
        """Verify display_final_summary accepts rent pool parameters."""
        sig = inspect.signature(summary_function)
        param_names = list(sig.parameters.keys())

        assert "initial_rent_pool" in param_names, f"Missing 'initial_rent_pool' in {param_names}"
        assert "final_rent_pool" in param_names, f"Missing 'final_rent_pool' in {param_names}"

    def test_summary_shows_four_entities_with_changes(self, summary_function: Any) -> None:
        """Verify display_final_summary shows all 4 entities with wealth changes."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)

        summary_function(
            console=console,
            initial_p_w=0.10,
            initial_p_c=0.20,
            initial_c_b=0.90,
            initial_c_w=0.18,
            initial_rent_pool=100.0,
            final_p_w=0.06,
            final_p_c=0.25,
            final_c_b=0.95,
            final_c_w=0.22,
            final_rent_pool=95.0,
            narrative_count=5,
        )

        rendered = output.getvalue()

        # Verify all 4 entities appear in summary
        assert "Periphery Worker" in rendered or "P_w" in rendered, (
            "Missing Periphery Worker in summary"
        )
        assert "Comprador" in rendered or "P_c" in rendered, "Missing Comprador in summary"
        assert "Core Bourgeoisie" in rendered or "C_b" in rendered, (
            "Missing Core Bourgeoisie in summary"
        )
        assert "Labor Aristocracy" in rendered or "C_w" in rendered, (
            "Missing Labor Aristocracy in summary"
        )

    def test_summary_shows_rent_pool_change(self, summary_function: Any) -> None:
        """Verify display_final_summary shows rent pool change."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)

        summary_function(
            console=console,
            initial_p_w=0.10,
            initial_p_c=0.20,
            initial_c_b=0.90,
            initial_c_w=0.18,
            initial_rent_pool=100.0,
            final_p_w=0.06,
            final_p_c=0.25,
            final_c_b=0.95,
            final_c_w=0.22,
            final_rent_pool=95.0,
            narrative_count=5,
        )

        rendered = output.getvalue()

        # Verify rent pool appears in output
        assert "Rent Pool" in rendered or "rent_pool" in rendered.lower() or "100" in rendered, (
            "Missing rent pool information in summary"
        )
