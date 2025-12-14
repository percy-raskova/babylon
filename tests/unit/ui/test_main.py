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
