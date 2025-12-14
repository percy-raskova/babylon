"""Tests for ControlDeck UI component.

RED Phase: These tests define the contract for the ControlDeck component.
The ControlDeck provides simulation control buttons (STEP, PLAY, PAUSE, RESET)
and a tick counter display.

Test Intent:
- ControlDeck renders all required buttons
- Button clicks invoke the appropriate callbacks
- Tick counter displays formatted tick number
- Tick counter updates when update_tick() is called

Aesthetic: "Cybernetic Terminal" - Dark background, green text, monospace font.
"""

from unittest.mock import Mock


class TestControlDeckInitialization:
    """Test ControlDeck instantiation and configuration."""

    def test_control_deck_can_be_instantiated_without_callbacks(self) -> None:
        """ControlDeck can be created without any callbacks (all None)."""
        from babylon.ui.controls import ControlDeck

        # Should not raise
        deck = ControlDeck()
        assert deck is not None

    def test_control_deck_stores_callbacks(self) -> None:
        """ControlDeck stores provided callbacks for later invocation."""
        from babylon.ui.controls import ControlDeck

        on_step = Mock()
        on_play = Mock()
        on_pause = Mock()
        on_reset = Mock()

        deck = ControlDeck(
            on_step=on_step,
            on_play=on_play,
            on_pause=on_pause,
            on_reset=on_reset,
        )

        # Verify callbacks are stored (implementation detail, but important for testing)
        assert deck._on_step is on_step
        assert deck._on_play is on_play
        assert deck._on_pause is on_pause
        assert deck._on_reset is on_reset


class TestControlDeckButtons:
    """Test button rendering and callback invocation."""

    def test_control_deck_has_step_button(self) -> None:
        """ControlDeck creates a STEP button."""
        from babylon.ui.controls import ControlDeck

        deck = ControlDeck()

        # The deck should have a step_button attribute
        assert hasattr(deck, "step_button")
        assert deck.step_button is not None

    def test_control_deck_has_play_button(self) -> None:
        """ControlDeck creates a PLAY button."""
        from babylon.ui.controls import ControlDeck

        deck = ControlDeck()

        assert hasattr(deck, "play_button")
        assert deck.play_button is not None

    def test_control_deck_has_pause_button(self) -> None:
        """ControlDeck creates a PAUSE button."""
        from babylon.ui.controls import ControlDeck

        deck = ControlDeck()

        assert hasattr(deck, "pause_button")
        assert deck.pause_button is not None

    def test_control_deck_has_reset_button(self) -> None:
        """ControlDeck creates a RESET button."""
        from babylon.ui.controls import ControlDeck

        deck = ControlDeck()

        assert hasattr(deck, "reset_button")
        assert deck.reset_button is not None

    def test_step_button_calls_on_step_callback(self) -> None:
        """Clicking STEP button invokes the on_step callback."""
        from babylon.ui.controls import ControlDeck

        callback = Mock()
        deck = ControlDeck(on_step=callback)

        # Simulate button click by calling the internal handler
        deck._handle_step()

        callback.assert_called_once()

    def test_play_button_calls_on_play_callback(self) -> None:
        """Clicking PLAY button invokes the on_play callback."""
        from babylon.ui.controls import ControlDeck

        callback = Mock()
        deck = ControlDeck(on_play=callback)

        deck._handle_play()

        callback.assert_called_once()

    def test_pause_button_calls_on_pause_callback(self) -> None:
        """Clicking PAUSE button invokes the on_pause callback."""
        from babylon.ui.controls import ControlDeck

        callback = Mock()
        deck = ControlDeck(on_pause=callback)

        deck._handle_pause()

        callback.assert_called_once()

    def test_reset_button_calls_on_reset_callback(self) -> None:
        """Clicking RESET button invokes the on_reset callback."""
        from babylon.ui.controls import ControlDeck

        callback = Mock()
        deck = ControlDeck(on_reset=callback)

        deck._handle_reset()

        callback.assert_called_once()

    def test_callback_not_called_when_none(self) -> None:
        """When callback is None, clicking button does not raise."""
        from babylon.ui.controls import ControlDeck

        deck = ControlDeck()  # All callbacks are None

        # Should not raise
        deck._handle_step()
        deck._handle_play()
        deck._handle_pause()
        deck._handle_reset()


class TestTickCounter:
    """Test tick counter display and updates."""

    def test_control_deck_has_tick_counter(self) -> None:
        """ControlDeck creates a tick counter label."""
        from babylon.ui.controls import ControlDeck

        deck = ControlDeck()

        assert hasattr(deck, "tick_counter")
        assert deck.tick_counter is not None

    def test_tick_counter_displays_formatted_tick_at_init(self) -> None:
        """Tick counter initially displays TICK: 000."""
        from babylon.ui.controls import ControlDeck

        deck = ControlDeck()

        # The tick counter should display the formatted tick
        assert deck._current_tick == 0
        assert deck._format_tick(0) == "TICK: 000"

    def test_tick_counter_formats_single_digit(self) -> None:
        """Single digit tick is zero-padded to 3 digits."""
        from babylon.ui.controls import ControlDeck

        deck = ControlDeck()

        assert deck._format_tick(5) == "TICK: 005"

    def test_tick_counter_formats_double_digit(self) -> None:
        """Double digit tick is zero-padded to 3 digits."""
        from babylon.ui.controls import ControlDeck

        deck = ControlDeck()

        assert deck._format_tick(42) == "TICK: 042"

    def test_tick_counter_formats_triple_digit(self) -> None:
        """Triple digit tick displays without padding."""
        from babylon.ui.controls import ControlDeck

        deck = ControlDeck()

        assert deck._format_tick(999) == "TICK: 999"

    def test_tick_counter_formats_beyond_three_digits(self) -> None:
        """Tick beyond 999 displays all digits."""
        from babylon.ui.controls import ControlDeck

        deck = ControlDeck()

        assert deck._format_tick(1234) == "TICK: 1234"

    def test_update_tick_updates_current_tick(self) -> None:
        """update_tick() updates the internal tick value."""
        from babylon.ui.controls import ControlDeck

        deck = ControlDeck()

        deck.update_tick(5)

        assert deck._current_tick == 5

    def test_update_tick_updates_display(self) -> None:
        """update_tick() updates the tick counter display."""
        from babylon.ui.controls import ControlDeck

        deck = ControlDeck()

        deck.update_tick(42)

        # After update, the formatted display should reflect new tick
        assert deck._format_tick(deck._current_tick) == "TICK: 042"


class TestControlDeckContainer:
    """Test the container element that wraps all controls."""

    def test_control_deck_has_container(self) -> None:
        """ControlDeck creates a container element."""
        from babylon.ui.controls import ControlDeck

        deck = ControlDeck()

        assert hasattr(deck, "container")
        assert deck.container is not None
