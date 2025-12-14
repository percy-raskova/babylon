"""Tests for main.py to prevent NiceGUI mode conflicts.

NiceGUI has two mutually exclusive modes:
1. Script Mode - UI in global scope, no @ui.page decorator
2. Page Mode - @ui.page decorator OR ui.run(root_func)

Mixing modes causes RuntimeError. These tests ensure we stay in one mode.
"""

import ast
from pathlib import Path


class TestNiceGUIModeSafety:
    """Tests to prevent NiceGUI mode conflicts."""

    def test_main_module_does_not_use_page_decorator(self) -> None:
        """Verify no @ui.page decorator is used.

        The root function pattern (ui.run(root_func)) is preferred.
        Using @ui.page with any global-scope UI causes RuntimeError.
        """
        main_path = Path("src/babylon/ui/main.py")
        source = main_path.read_text()
        tree = ast.parse(source)

        # Look for any function with @ui.page or @...page decorator
        has_page_decorator = False
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    # Check for @ui.page(...) call syntax
                    is_page_call = (
                        isinstance(decorator, ast.Call)
                        and isinstance(decorator.func, ast.Attribute)
                        and decorator.func.attr == "page"
                    )
                    # Check for @ui.page without call
                    is_page_attr = isinstance(decorator, ast.Attribute) and decorator.attr == "page"
                    if is_page_call or is_page_attr:
                        has_page_decorator = True
                        break

        assert not has_page_decorator, (
            "Do not use @ui.page decorator in main.py. "
            "Use ui.run(root_func) pattern instead to avoid mode conflicts. "
            "See ai-docs/decisions.yaml:ADR026_nicegui_root_function_pattern"
        )

    def test_ui_run_receives_root_function(self) -> None:
        """Verify ui.run() is called with a root function argument.

        The pattern ui.run(main_page, ...) ensures all UI is inside
        the root function, preventing mode conflicts.
        """
        main_path = Path("src/babylon/ui/main.py")
        source = main_path.read_text()
        tree = ast.parse(source)

        ui_run_has_positional_arg = False
        for node in ast.walk(tree):
            is_ui_run_call = (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "run"
                and node.args  # Has positional argument (root function)
            )
            if is_ui_run_call:
                ui_run_has_positional_arg = True
                break

        assert ui_run_has_positional_arg, (
            "ui.run() must receive a root function as first argument. "
            "Use ui.run(main_page, title=...) pattern. "
            "This ensures all UI elements are created inside the root function."
        )


class TestSynopticonLayout:
    """Test 4-panel Synopticon layout structure.

    These tests verify that main.py declares the necessary module-level
    globals for the Synopticon dashboard components.
    """

    def test_main_module_has_trend_plotter_global(self) -> None:
        """main.py declares trend_plotter global variable."""
        import babylon.ui.main as main_module

        assert hasattr(main_module, "trend_plotter"), (
            "main.py must declare 'trend_plotter' global for TrendPlotter component"
        )

    def test_main_module_has_system_log_global(self) -> None:
        """main.py declares system_log global variable."""
        import babylon.ui.main as main_module

        assert hasattr(main_module, "system_log"), (
            "main.py must declare 'system_log' global for SystemLog component"
        )

    def test_main_module_has_state_inspector_global(self) -> None:
        """main.py declares state_inspector global variable."""
        import babylon.ui.main as main_module

        assert hasattr(main_module, "state_inspector"), (
            "main.py must declare 'state_inspector' global for StateInspector component"
        )

    def test_main_module_has_last_event_index_global(self) -> None:
        """main.py declares last_event_index for event tracking."""
        import babylon.ui.main as main_module

        assert hasattr(main_module, "last_event_index"), (
            "main.py must declare 'last_event_index' global for event tracking"
        )


class TestRefreshUIHelpers:
    """Test helper functions for refresh_ui().

    These functions calculate derived metrics and map event types to log levels.
    """

    def test_calculate_global_tension_with_empty_relationships(self) -> None:
        """_calculate_global_tension returns 0.0 for empty relationships."""
        from babylon.models.world_state import WorldState
        from babylon.ui.main import _calculate_global_tension

        state = WorldState(tick=0, entities={}, relationships=[])
        result = _calculate_global_tension(state)

        assert result == 0.0, f"Expected 0.0 for empty relationships, got {result}"

    def test_calculate_global_tension_averages_tension_values(self) -> None:
        """_calculate_global_tension returns average of relationship tensions."""
        from babylon.models.entities.relationship import Relationship
        from babylon.models.entities.social_class import SocialClass
        from babylon.models.enums import EdgeType, SocialRole
        from babylon.models.world_state import WorldState
        from babylon.ui.main import _calculate_global_tension

        # Create two entities
        worker = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=50.0,
        )
        owner = SocialClass(
            id="C002",
            name="Owner",
            role=SocialRole.CORE_BOURGEOISIE,
            wealth=500.0,
        )

        # Create relationships with known tensions
        rel1 = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.EXPLOITATION,
            tension=0.4,
        )
        rel2 = Relationship(
            source_id="C002",
            target_id="C001",
            edge_type=EdgeType.REPRESSION,
            tension=0.6,
        )

        state = WorldState(
            tick=0,
            entities={"C001": worker, "C002": owner},
            relationships=[rel1, rel2],
        )

        result = _calculate_global_tension(state)

        # Average of 0.4 and 0.6 should be 0.5
        assert result == 0.5, f"Expected 0.5 (average of 0.4 and 0.6), got {result}"

    def test_event_to_log_level_returns_info_by_default(self) -> None:
        """_event_to_log_level returns INFO for normal events."""
        from babylon.models.events import ExtractionEvent
        from babylon.ui.main import _event_to_log_level

        event = ExtractionEvent(
            tick=1,
            source_id="C001",
            target_id="C002",
            amount=10.0,
        )

        result = _event_to_log_level(event)

        assert result == "INFO", f"Expected 'INFO' for SURPLUS_EXTRACTION event, got '{result}'"

    def test_event_to_log_level_returns_error_for_crisis(self) -> None:
        """_event_to_log_level returns ERROR for ECONOMIC_CRISIS."""
        from babylon.models.events import CrisisEvent
        from babylon.ui.main import _event_to_log_level

        event = CrisisEvent(
            tick=10,
            pool_ratio=0.15,
            aggregate_tension=0.7,
            decision="CRISIS",
            wage_delta=-0.05,
        )

        result = _event_to_log_level(event)

        assert result == "ERROR", f"Expected 'ERROR' for ECONOMIC_CRISIS event, got '{result}'"

    def test_event_to_log_level_returns_warn_for_excessive_force(self) -> None:
        """_event_to_log_level returns WARN for EXCESSIVE_FORCE."""
        from babylon.models.events import SparkEvent
        from babylon.ui.main import _event_to_log_level

        event = SparkEvent(
            tick=5,
            node_id="C001",
            repression=0.8,
            spark_probability=0.4,
        )

        result = _event_to_log_level(event)

        assert result == "WARN", f"Expected 'WARN' for EXCESSIVE_FORCE event, got '{result}'"
