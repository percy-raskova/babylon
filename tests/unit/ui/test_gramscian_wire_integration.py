"""RED PHASE: Failing tests for The Gramscian Wire integration.

These tests define the contract for integrating WirePanel into main.py
and polling NarrativeDirector.dual_narratives. All tests should FAIL
initially, as this is the TDD RED phase.

Integration Requirements:
1. DashboardState must have wire_panel: WirePanel | None attribute
2. refresh_ui() must poll dual_narratives (not just narrative_log)
3. main_page() must create WirePanel and label it "THE WIRE"

Sprint 4.2: The Gramscian Wire - dual narrative display showing
"Neutrality is Hegemony" thesis through contrasting perspectives.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import Mock

import pytest

if TYPE_CHECKING:
    pass


# =============================================================================
# DASHBOARD STATE TESTS
# =============================================================================


class TestDashboardStateWirePanel:
    """Tests for WirePanel attribute on DashboardState."""

    @pytest.mark.unit
    def test_dashboard_state_has_wire_panel_attribute(
        self,
        reset_main_module_state: None,
    ) -> None:
        """DashboardState must have wire_panel attribute.

        The WirePanel component displays dual narratives (corporate vs liberated)
        for significant events. DashboardState must hold a reference to it.
        """
        import babylon.ui.main as main

        # DashboardState should have wire_panel attribute
        assert hasattr(main._state, "wire_panel"), (
            "DashboardState must have 'wire_panel' attribute for WirePanel component. "
            "Add 'wire_panel: WirePanel | None' to DashboardState.__init__()"
        )

    @pytest.mark.unit
    def test_dashboard_state_wire_panel_initially_none(
        self,
        reset_main_module_state: None,
    ) -> None:
        """DashboardState.wire_panel should be None initially.

        The WirePanel is created during main_page() execution, so the
        initial value must be None to avoid NiceGUI context errors.
        """

        # Create fresh state
        from babylon.ui.main import DashboardState

        fresh_state = DashboardState()

        assert fresh_state.wire_panel is None, (
            "DashboardState.wire_panel must be None initially. "
            "WirePanel is created during main_page() execution."
        )


# =============================================================================
# REFRESH UI INTEGRATION TESTS
# =============================================================================


class TestRefreshUIDualNarratives:
    """Tests for refresh_ui() polling dual_narratives from NarrativeDirector."""

    @pytest.mark.unit
    def test_refresh_ui_polls_dual_narratives(
        self,
        reset_main_module_state: None,
    ) -> None:
        """refresh_ui() must poll dual_narratives and log to WirePanel.

        When NarrativeDirector.dual_narratives has entries, refresh_ui()
        should extract them and log to the WirePanel component.

        This is the Gramscian Wire integration: showing both corporate
        and liberated perspectives on significant events.
        """
        import babylon.ui.main as main
        from babylon.models.events import ExtractionEvent
        from babylon.ui.components import WirePanel

        main.init_simulation()
        assert main.simulation is not None

        # Create mock NarrativeDirector with dual_narratives
        mock_director = Mock()
        mock_director.name = "NarrativeDirector"

        # Create a sample event and dual narrative entry
        sample_event = ExtractionEvent(
            tick=1,
            source_id="C001",
            target_id="C002",
            amount=10.0,
        )
        mock_director.dual_narratives = {
            1: {
                "event": sample_event,
                "corporate": "Markets stabilized today.",
                "liberated": ">>> Workers robbed again! <<<",
            }
        }
        # Also need narrative_log for backward compat
        mock_director.narrative_log = []

        # Inject mock director into simulation observers
        main.simulation._observers = [mock_director]

        # Create WirePanel
        main._state.wire_panel = WirePanel()

        # Track last_dual_narrative_index (needs to be added to DashboardState)
        assert hasattr(main._state, "last_dual_narrative_index"), (
            "DashboardState must have 'last_dual_narrative_index' for tracking "
            "which dual narratives have been logged to WirePanel."
        )
        main._state.last_dual_narrative_index = 0

        # Call refresh_ui
        main.refresh_ui()

        # WirePanel should have received the dual narrative entry
        assert len(main.wire_panel._entries) > 0, (
            "WirePanel should have entries after refresh_ui() when dual_narratives is populated"
        )

    @pytest.mark.unit
    def test_refresh_ui_updates_last_dual_narrative_index(
        self,
        reset_main_module_state: None,
    ) -> None:
        """refresh_ui() must update last_dual_narrative_index after polling.

        Similar to how last_narrative_index tracks narrative_log polling,
        we need last_dual_narrative_index to track dual_narratives polling.
        """
        import babylon.ui.main as main
        from babylon.models.events import ExtractionEvent
        from babylon.ui.components import WirePanel

        main.init_simulation()
        assert main.simulation is not None

        # Create mock NarrativeDirector with multiple dual narrative entries
        mock_director = Mock()
        mock_director.name = "NarrativeDirector"

        sample_event = ExtractionEvent(
            tick=1,
            source_id="C001",
            target_id="C002",
            amount=10.0,
        )
        mock_director.dual_narratives = {
            1: {
                "event": sample_event,
                "corporate": "Markets stable.",
                "liberated": ">>> Exploitation continues <<<",
            },
            2: {
                "event": sample_event,
                "corporate": "Growth maintained.",
                "liberated": ">>> Resistance rises <<<",
            },
        }
        mock_director.narrative_log = []

        main.simulation._observers = [mock_director]
        main._state.wire_panel = WirePanel()

        # DashboardState must have this tracking index
        assert hasattr(main._state, "last_dual_narrative_index"), (
            "DashboardState must have 'last_dual_narrative_index' attribute"
        )
        main._state.last_dual_narrative_index = 0

        # Call refresh_ui
        main.refresh_ui()

        # The index should have advanced
        assert main._state.last_dual_narrative_index > 0, (
            "last_dual_narrative_index should advance after polling dual_narratives"
        )


# =============================================================================
# MAIN PAGE LAYOUT TESTS
# =============================================================================


class TestMainPageWirePanel:
    """Tests for WirePanel creation in main_page()."""

    @pytest.mark.unit
    def test_main_page_creates_wire_panel(
        self,
        reset_main_module_state: None,
    ) -> None:
        """main_page() must create and assign WirePanel to _state.wire_panel.

        The WirePanel replaces or supplements the NarrativeTerminal for
        displaying AI-generated narratives with dual perspectives.
        """
        import ast
        from pathlib import Path

        main_path = Path("src/babylon/ui/main.py")
        source = main_path.read_text()
        tree = ast.parse(source)

        # Find main_page function
        main_page_func = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "main_page":
                main_page_func = node
                break

        assert main_page_func is not None, "main_page function not found"

        # Look for assignment: _state.wire_panel = WirePanel()
        # or: main._state.wire_panel = WirePanel()
        wire_panel_assigned = False
        for node in ast.walk(main_page_func):
            # Check for attribute assignment pattern
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    # Check for _state.wire_panel or self._state.wire_panel pattern
                    is_wire_panel_attr = (
                        isinstance(target, ast.Attribute) and target.attr == "wire_panel"
                    )
                    if is_wire_panel_attr:
                        wire_panel_assigned = True
                        break

        assert wire_panel_assigned, (
            "main_page() must assign WirePanel to _state.wire_panel:\n"
            "    _state.wire_panel = WirePanel()\n"
            "This is required for The Gramscian Wire dual narrative display."
        )

    @pytest.mark.unit
    def test_wire_panel_label_is_the_wire(
        self,
        reset_main_module_state: None,
    ) -> None:
        """Center panel label should be 'THE WIRE' (not 'NARRATIVE').

        The Gramscian Wire branding requires the center panel to be
        labeled "THE WIRE" to emphasize the dual narrative concept.
        """
        import ast
        from pathlib import Path

        main_path = Path("src/babylon/ui/main.py")
        source = main_path.read_text()
        tree = ast.parse(source)

        # Find main_page function
        main_page_func = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "main_page":
                main_page_func = node
                break

        assert main_page_func is not None, "main_page function not found"

        # Look for ui.label("THE WIRE") call
        has_wire_label = False
        for node in ast.walk(main_page_func):
            is_label_call = (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "label"
            )
            if is_label_call and node.args:
                arg = node.args[0]
                if isinstance(arg, ast.Constant) and arg.value == "THE WIRE":
                    has_wire_label = True
                    break

        assert has_wire_label, (
            "main_page() must include a label 'THE WIRE' for the center panel:\n"
            '    ui.label("THE WIRE").classes(...)\n'
            "This is the branding for The Gramscian Wire dual narrative display."
        )


# =============================================================================
# ON RESET TESTS
# =============================================================================


class TestOnResetDualNarrativeIndex:
    """Tests for on_reset() resetting dual narrative tracking."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_on_reset_resets_dual_narrative_index(
        self,
        main_module_with_mocks: Any,
    ) -> None:
        """on_reset() must reset last_dual_narrative_index to 0.

        When the simulation is reset, the dual narrative tracking index
        must also be reset to avoid skipping narratives on the new run.
        """
        main = main_module_with_mocks

        # Ensure the attribute exists
        assert hasattr(main._state, "last_dual_narrative_index"), (
            "DashboardState must have 'last_dual_narrative_index' attribute"
        )

        # Set a non-zero value
        main._state.last_dual_narrative_index = 5

        await main.on_reset()

        assert main._state.last_dual_narrative_index == 0, (
            "on_reset() must reset last_dual_narrative_index to 0"
        )


# =============================================================================
# CONFTEST FIXTURE VERIFICATION
# =============================================================================


class TestWirePanelConftest:
    """Tests verifying conftest.py saves/restores wire_panel state."""

    @pytest.mark.unit
    def test_conftest_saves_wire_panel_state(
        self,
        reset_main_module_state: None,
    ) -> None:
        """conftest.py reset_main_module_state must save/restore wire_panel.

        The conftest fixture should explicitly save and restore wire_panel
        to prevent test pollution. This requires updating conftest.py to
        include wire_panel in the save/restore logic.
        """
        # Read conftest.py and verify it references wire_panel
        from pathlib import Path

        conftest_path = Path("tests/unit/ui/conftest.py")
        source = conftest_path.read_text()

        # Check that conftest saves wire_panel
        assert "original_wire_panel" in source, (
            "conftest.py reset_main_module_state fixture must save wire_panel:\n"
            "    original_wire_panel = main._state.wire_panel\n"
            "and restore it after the test."
        )

    @pytest.mark.unit
    def test_conftest_saves_dual_narrative_index(
        self,
        reset_main_module_state: None,
    ) -> None:
        """conftest.py must save/restore last_dual_narrative_index.

        Similar to last_narrative_index, the dual narrative tracking index
        must be saved and restored to prevent test pollution.
        """
        from pathlib import Path

        conftest_path = Path("tests/unit/ui/conftest.py")
        source = conftest_path.read_text()

        # Check that conftest saves last_dual_narrative_index
        assert "original_last_dual_narrative_index" in source, (
            "conftest.py must save last_dual_narrative_index:\n"
            "    original_last_dual_narrative_index = main._state.last_dual_narrative_index\n"
            "and restore it after the test."
        )
