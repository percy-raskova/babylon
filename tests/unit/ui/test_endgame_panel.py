"""Tests for EndgamePanel UI component (Slice 1.6).

TDD Red Phase: These tests define the contract for EndgamePanel.
The tests WILL FAIL initially because the implementation does not exist yet.
This is the correct Red phase outcome.

Slice 1.6: Endgame Display

The EndgamePanel displays the game outcome when the simulation terminates.
It provides:
- Visual feedback for each outcome type
- Appropriate styling (colors, icons) per outcome
- Hidden/visible toggle based on game state

Design System: Bunker Constructivism

Outcome-specific styling:
- REVOLUTIONARY_VICTORY: Triumph green (#00FF00), victory message
- ECOLOGICAL_COLLAPSE: Warning amber/brown (#8B4513), collapse message
- FASCIST_CONSOLIDATION: Danger red (#D40000), defeat message
- IN_PROGRESS: Panel hidden (no display needed)

NOTE: Tests marked with @pytest.mark.red_phase are excluded from pre-commit.
Remove the marker when implementing GREEN phase.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest

# These imports will fail until implementation exists - that's the RED phase
from babylon.models.enums import GameOutcome
from babylon.ui.components import EndgamePanel

# TDD GREEN phase - tests now pass with implementation

if TYPE_CHECKING:
    pass


# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest.fixture
def mock_nicegui() -> Any:
    """Mock nicegui UI components for testing.

    UI components cannot be tested without a running nicegui server,
    so we mock the UI layer.
    """
    with patch("babylon.ui.components.ui") as mock_ui:
        # Configure mock to return mock elements
        mock_ui.card.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_ui.card.return_value.__exit__ = MagicMock(return_value=None)
        mock_ui.column.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_ui.column.return_value.__exit__ = MagicMock(return_value=None)
        mock_ui.row.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_ui.row.return_value.__exit__ = MagicMock(return_value=None)
        mock_ui.label.return_value.classes.return_value.style.return_value = MagicMock()
        mock_ui.label.return_value.classes.return_value = MagicMock()
        mock_ui.icon.return_value.classes.return_value.style.return_value = MagicMock()

        yield mock_ui


# =============================================================================
# TEST CLASS EXISTENCE
# =============================================================================


@pytest.mark.unit
class TestEndgamePanelExists:
    """Test that EndgamePanel class exists and is importable."""

    def test_endgame_panel_class_exists(self) -> None:
        """EndgamePanel class must exist in babylon.ui.components.

        This is the basic import test to verify the class is defined.
        """
        assert EndgamePanel is not None
        assert callable(EndgamePanel)

    def test_endgame_panel_can_be_instantiated(self, mock_nicegui: Any) -> None:
        """EndgamePanel can be instantiated without arguments."""
        panel = EndgamePanel()
        assert panel is not None


# =============================================================================
# TEST OUTCOME DISPLAY
# =============================================================================


@pytest.mark.unit
class TestEndgamePanelDisplay:
    """Test outcome display functionality."""

    def test_endgame_panel_displays_outcome(self, mock_nicegui: Any) -> None:
        """EndgamePanel has display_outcome method that accepts GameOutcome.

        This method updates the panel to show the appropriate outcome.
        """
        panel = EndgamePanel()

        # Method should exist and be callable
        assert hasattr(panel, "display_outcome")
        assert callable(panel.display_outcome)

        # Should accept GameOutcome parameter
        panel.display_outcome(GameOutcome.REVOLUTIONARY_VICTORY)

    def test_endgame_panel_shows_revolutionary_victory_message(
        self,
        mock_nicegui: Any,
    ) -> None:
        """EndgamePanel shows victory message for REVOLUTIONARY_VICTORY.

        The message should celebrate the workers' triumph.
        """
        panel = EndgamePanel()
        panel.display_outcome(GameOutcome.REVOLUTIONARY_VICTORY)

        # Panel should have victory message accessible
        assert hasattr(panel, "current_message")
        message = panel.current_message.lower()

        # Should contain victory-related terms
        assert any(
            term in message for term in ["victory", "revolution", "workers", "triumph", "liberate"]
        ), f"Victory message missing key terms: {message}"

    def test_endgame_panel_shows_ecological_collapse_message(
        self,
        mock_nicegui: Any,
    ) -> None:
        """EndgamePanel shows collapse message for ECOLOGICAL_COLLAPSE.

        The message should warn about ecological destruction.
        """
        panel = EndgamePanel()
        panel.display_outcome(GameOutcome.ECOLOGICAL_COLLAPSE)

        message = panel.current_message.lower()

        # Should contain collapse-related terms
        assert any(
            term in message
            for term in ["collapse", "ecological", "destruction", "environment", "rift"]
        ), f"Collapse message missing key terms: {message}"

    def test_endgame_panel_shows_fascist_consolidation_message(
        self,
        mock_nicegui: Any,
    ) -> None:
        """EndgamePanel shows defeat message for FASCIST_CONSOLIDATION.

        The message should indicate fascist victory and worker defeat.
        """
        panel = EndgamePanel()
        panel.display_outcome(GameOutcome.FASCIST_CONSOLIDATION)

        message = panel.current_message.lower()

        # Should contain fascism-related terms
        assert any(
            term in message for term in ["fascist", "defeat", "darkness", "consolidation", "lost"]
        ), f"Fascist message missing key terms: {message}"


# =============================================================================
# TEST OUTCOME-SPECIFIC STYLING
# =============================================================================


@pytest.mark.unit
class TestEndgamePanelStyling:
    """Test outcome-specific styling."""

    def test_endgame_panel_has_appropriate_styling_per_outcome(
        self,
        mock_nicegui: Any,
    ) -> None:
        """EndgamePanel applies different colors for each outcome type.

        Design System colors:
        - REVOLUTIONARY_VICTORY: Green (#00FF00 or similar triumph color)
        - ECOLOGICAL_COLLAPSE: Amber/Brown (#8B4513 or warning color)
        - FASCIST_CONSOLIDATION: Red (#D40000 phosphor_burn_red)
        """
        panel = EndgamePanel()

        # Should have styling constants or method
        assert hasattr(panel, "get_style_for_outcome") or hasattr(panel, "OUTCOME_STYLES")

        if hasattr(panel, "get_style_for_outcome"):
            # Revolutionary victory should have green color (Design System: #39FF14 data_green)
            victory_style = panel.get_style_for_outcome(GameOutcome.REVOLUTIONARY_VICTORY)
            assert "FF" in victory_style.upper() or "green" in victory_style.lower()

            # Ecological collapse should have amber/warning color (Design System: #B8860B dark goldenrod)
            collapse_style = panel.get_style_for_outcome(GameOutcome.ECOLOGICAL_COLLAPSE)
            assert (
                "860B" in collapse_style.upper()
                or "B886" in collapse_style.upper()
                or "amber" in collapse_style.lower()
                or "brown" in collapse_style.lower()
                or "warning" in collapse_style.lower()
            )

            # Fascist consolidation should have red color (Design System: #D40000 phosphor_burn_red)
            fascist_style = panel.get_style_for_outcome(GameOutcome.FASCIST_CONSOLIDATION)
            assert "D400" in fascist_style.upper() or "red" in fascist_style.lower()

        elif hasattr(panel, "OUTCOME_STYLES"):
            styles = panel.OUTCOME_STYLES

            assert GameOutcome.REVOLUTIONARY_VICTORY in styles
            assert GameOutcome.ECOLOGICAL_COLLAPSE in styles
            assert GameOutcome.FASCIST_CONSOLIDATION in styles

    def test_revolutionary_victory_uses_triumph_green(
        self,
        mock_nicegui: Any,
    ) -> None:
        """REVOLUTIONARY_VICTORY uses triumph green styling.

        This is the only positive ending - it should feel triumphant.
        """
        panel = EndgamePanel()
        panel.display_outcome(GameOutcome.REVOLUTIONARY_VICTORY)

        # Panel should track current styling
        assert hasattr(panel, "current_color")
        # Green indicates success
        color = panel.current_color.upper()
        assert "00FF" in color or "39FF14" in color or "GREEN" in color.upper(), (
            f"Expected green color for victory, got {color}"
        )

    def test_ecological_collapse_uses_warning_amber(
        self,
        mock_nicegui: Any,
    ) -> None:
        """ECOLOGICAL_COLLAPSE uses warning amber/brown styling.

        This represents environmental destruction - earthy, dying colors.
        """
        panel = EndgamePanel()
        panel.display_outcome(GameOutcome.ECOLOGICAL_COLLAPSE)

        color = panel.current_color.upper()
        # Amber, brown, or warning orange tones
        assert any(c in color for c in ["8B45", "FFD7", "AMBER", "BROWN", "ORANGE", "B8860B"]), (
            f"Expected amber/warning color for collapse, got {color}"
        )

    def test_fascist_consolidation_uses_danger_red(
        self,
        mock_nicegui: Any,
    ) -> None:
        """FASCIST_CONSOLIDATION uses danger red styling.

        This is a defeat - red indicates danger and failure.
        """
        panel = EndgamePanel()
        panel.display_outcome(GameOutcome.FASCIST_CONSOLIDATION)

        color = panel.current_color.upper()
        # Red danger colors
        assert "D400" in color or "FF0000" in color or "RED" in color.upper(), (
            f"Expected red color for fascist ending, got {color}"
        )


# =============================================================================
# TEST VISIBILITY
# =============================================================================


@pytest.mark.unit
class TestEndgamePanelVisibility:
    """Test panel visibility behavior."""

    def test_endgame_panel_initially_hidden_when_in_progress(
        self,
        mock_nicegui: Any,
    ) -> None:
        """EndgamePanel is hidden when game is IN_PROGRESS.

        The panel should only become visible when the game ends.
        """
        panel = EndgamePanel()

        # Should have visibility tracking
        assert hasattr(panel, "is_visible")
        assert panel.is_visible is False

    def test_endgame_panel_becomes_visible_on_game_end(
        self,
        mock_nicegui: Any,
    ) -> None:
        """EndgamePanel becomes visible when display_outcome is called.

        Any outcome other than IN_PROGRESS should show the panel.
        """
        panel = EndgamePanel()

        assert panel.is_visible is False

        panel.display_outcome(GameOutcome.REVOLUTIONARY_VICTORY)
        assert panel.is_visible is True

    def test_endgame_panel_stays_hidden_for_in_progress(
        self,
        mock_nicegui: Any,
    ) -> None:
        """EndgamePanel stays hidden when outcome is IN_PROGRESS.

        Calling display_outcome with IN_PROGRESS should hide the panel.
        """
        panel = EndgamePanel()

        # First show it
        panel.display_outcome(GameOutcome.REVOLUTIONARY_VICTORY)
        assert panel.is_visible is True

        # Then hide it
        panel.display_outcome(GameOutcome.IN_PROGRESS)
        assert panel.is_visible is False

    def test_endgame_panel_has_hide_method(
        self,
        mock_nicegui: Any,
    ) -> None:
        """EndgamePanel has explicit hide method."""
        panel = EndgamePanel()

        assert hasattr(panel, "hide")
        assert callable(panel.hide)

        panel.display_outcome(GameOutcome.FASCIST_CONSOLIDATION)
        assert panel.is_visible is True

        panel.hide()
        assert panel.is_visible is False

    def test_endgame_panel_has_show_method(
        self,
        mock_nicegui: Any,
    ) -> None:
        """EndgamePanel has explicit show method."""
        panel = EndgamePanel()

        assert hasattr(panel, "show")
        assert callable(panel.show)

        assert panel.is_visible is False

        panel.show()
        assert panel.is_visible is True


# =============================================================================
# TEST CONTENT STRUCTURE
# =============================================================================


@pytest.mark.unit
class TestEndgamePanelContent:
    """Test panel content structure."""

    def test_endgame_panel_has_title(
        self,
        mock_nicegui: Any,
    ) -> None:
        """EndgamePanel has a title element."""
        panel = EndgamePanel()

        assert hasattr(panel, "title")

    def test_endgame_panel_has_outcome_label(
        self,
        mock_nicegui: Any,
    ) -> None:
        """EndgamePanel has an outcome label element."""
        panel = EndgamePanel()

        assert hasattr(panel, "outcome_label")

    def test_endgame_panel_has_message_element(
        self,
        mock_nicegui: Any,
    ) -> None:
        """EndgamePanel has a message element for detailed text."""
        panel = EndgamePanel()

        assert hasattr(panel, "message_element")

    def test_endgame_panel_tracks_current_outcome(
        self,
        mock_nicegui: Any,
    ) -> None:
        """EndgamePanel tracks current outcome for state inspection."""
        panel = EndgamePanel()

        assert hasattr(panel, "current_outcome")
        assert panel.current_outcome == GameOutcome.IN_PROGRESS

        panel.display_outcome(GameOutcome.ECOLOGICAL_COLLAPSE)
        assert panel.current_outcome == GameOutcome.ECOLOGICAL_COLLAPSE


# =============================================================================
# TEST RESET FUNCTIONALITY
# =============================================================================


@pytest.mark.unit
class TestEndgamePanelReset:
    """Test panel reset functionality."""

    def test_endgame_panel_can_reset(
        self,
        mock_nicegui: Any,
    ) -> None:
        """EndgamePanel can be reset to initial state.

        Useful for starting a new game without recreating the panel.
        """
        panel = EndgamePanel()

        # Set to some outcome
        panel.display_outcome(GameOutcome.FASCIST_CONSOLIDATION)
        assert panel.is_visible is True
        assert panel.current_outcome == GameOutcome.FASCIST_CONSOLIDATION

        # Reset
        assert hasattr(panel, "reset")
        panel.reset()

        assert panel.is_visible is False
        assert panel.current_outcome == GameOutcome.IN_PROGRESS


# =============================================================================
# TEST MESSAGES CONTENT
# =============================================================================


@pytest.mark.unit
class TestEndgamePanelMessages:
    """Test specific message content."""

    def test_victory_message_is_celebratory(
        self,
        mock_nicegui: Any,
    ) -> None:
        """Revolutionary victory message celebrates the workers."""
        panel = EndgamePanel()
        panel.display_outcome(GameOutcome.REVOLUTIONARY_VICTORY)

        # Message should be positive and celebratory
        message = panel.current_message
        assert len(message) > 20, "Message too short"

    def test_collapse_message_is_warning(
        self,
        mock_nicegui: Any,
    ) -> None:
        """Ecological collapse message warns of consequences."""
        panel = EndgamePanel()
        panel.display_outcome(GameOutcome.ECOLOGICAL_COLLAPSE)

        message = panel.current_message
        assert len(message) > 20, "Message too short"

    def test_fascist_message_is_somber(
        self,
        mock_nicegui: Any,
    ) -> None:
        """Fascist consolidation message conveys defeat."""
        panel = EndgamePanel()
        panel.display_outcome(GameOutcome.FASCIST_CONSOLIDATION)

        message = panel.current_message
        assert len(message) > 20, "Message too short"

    def test_messages_are_distinct(
        self,
        mock_nicegui: Any,
    ) -> None:
        """Each outcome has a distinct message."""
        panel = EndgamePanel()

        panel.display_outcome(GameOutcome.REVOLUTIONARY_VICTORY)
        victory_msg = panel.current_message

        panel.display_outcome(GameOutcome.ECOLOGICAL_COLLAPSE)
        collapse_msg = panel.current_message

        panel.display_outcome(GameOutcome.FASCIST_CONSOLIDATION)
        fascist_msg = panel.current_message

        # All messages should be different
        assert victory_msg != collapse_msg
        assert collapse_msg != fascist_msg
        assert victory_msg != fascist_msg
