"""Tests for WirePanel UI component (The Gramscian Wire).

RED Phase: These tests define the contract for the WirePanel component.
The WirePanel displays side-by-side Corporate vs Liberated narratives
for significant simulation events, demonstrating the thesis that
"neutrality is hegemony."

Test Intent:
- WirePanel class exists and can be imported
- WirePanel has log() method and scroll_area attribute
- Styling constants match Design System specification
- log() accepts event-only or event+narratives parameters
- Dual narrative rendering vs single narrative fallback

Layout (from ai-docs/gramscian-wire-mvp.yaml):
    +----------------------+--------------------------+
    |  THE STATE           |  THE UNDERGROUND         |
    +----------------------+--------------------------+
    |  [Corporate text]    |  [Liberated text]        |
    +----------------------+--------------------------+

Styling (from ai-docs/gramscian-wire-mvp.yaml):
- Corporate: bg=#1a1a1a, text=#ffffff, border-left: 3px solid #4a90d9
- Liberated: bg=#0d0d0d, text=#00ff88, border-left: 3px solid #9b59b6

Aesthetic: "Bunker Constructivism" - Dual-channel wire service.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    pass


# =============================================================================
# Class Existence and Interface Tests
# =============================================================================


class TestWirePanelClassExists:
    """Test WirePanel can be imported and instantiated."""

    @pytest.mark.unit
    def test_wire_panel_class_exists(self) -> None:
        """WirePanel class can be imported from babylon.ui.components.

        Test Intent:
            Verify the WirePanel class exists in the components module.
            This is the foundational test - if this fails, nothing else matters.

        Business Rule:
            The Gramscian Wire MVP requires a WirePanel component for
            dual narrative display (Slice 1.5).
        """
        from babylon.ui.components import WirePanel

        # Should not raise ImportError
        assert WirePanel is not None

    @pytest.mark.unit
    def test_wire_panel_can_be_instantiated(self) -> None:
        """WirePanel can be created without error.

        Test Intent:
            Verify basic instantiation works without parameters.
        """
        from babylon.ui.components import WirePanel

        panel = WirePanel()

        assert panel is not None


class TestWirePanelInterface:
    """Test WirePanel has required interface methods and attributes."""

    @pytest.mark.unit
    def test_wire_panel_has_log_method(self) -> None:
        """WirePanel has a log() method.

        Test Intent:
            Verify the log() method exists. This is the primary interface
            for adding events to the wire display.

        Business Rule:
            Events are logged to the WirePanel, which then renders them
            in either single or dual narrative mode.
        """
        from babylon.ui.components import WirePanel

        panel = WirePanel()

        assert hasattr(panel, "log")
        assert callable(panel.log)

    @pytest.mark.unit
    def test_wire_panel_has_scroll_area(self) -> None:
        """WirePanel has a scroll_area attribute.

        Test Intent:
            Verify scroll_area exists for auto-scrolling behavior.
            Similar to SystemLog's scroll_area pattern.
        """
        from babylon.ui.components import WirePanel

        panel = WirePanel()

        assert hasattr(panel, "scroll_area")
        assert panel.scroll_area is not None


# =============================================================================
# Styling Constants Tests (Design System Compliance)
# =============================================================================


class TestWirePanelCorporateStyling:
    """Test Corporate channel styling constants match Design System."""

    @pytest.mark.unit
    def test_wire_panel_corporate_bg_color(self) -> None:
        """Corporate background color is #1a1a1a.

        Design System Source: ai-docs/gramscian-wire-mvp.yaml
        - Corporate aesthetic: background: "#1a1a1a"
        """
        from babylon.ui.components import WirePanel

        expected_color = "#1a1a1a"

        assert expected_color == WirePanel.CORPORATE_BG

    @pytest.mark.unit
    def test_wire_panel_corporate_text_color(self) -> None:
        """Corporate text color is #ffffff (white).

        Design System Source: ai-docs/gramscian-wire-mvp.yaml
        - Corporate aesthetic: text_color: "#ffffff"
        """
        from babylon.ui.components import WirePanel

        expected_color = "#ffffff"

        assert expected_color == WirePanel.CORPORATE_TEXT

    @pytest.mark.unit
    def test_wire_panel_corporate_border_color(self) -> None:
        """Corporate border accent color is #4a90d9 (blue - authority).

        Design System Source: ai-docs/gramscian-wire-mvp.yaml
        - Corporate aesthetic: accent_color: "#4a90d9"
        - CSS: border-left: 3px solid #4a90d9
        """
        from babylon.ui.components import WirePanel

        expected_color = "#4a90d9"

        assert expected_color == WirePanel.CORPORATE_BORDER


class TestWirePanelLiberatedStyling:
    """Test Liberated channel styling constants match Design System."""

    @pytest.mark.unit
    def test_wire_panel_liberated_bg_color(self) -> None:
        """Liberated background color is #0d0d0d.

        Design System Source: ai-docs/gramscian-wire-mvp.yaml
        - Liberated aesthetic: background: "#0d0d0d"
        """
        from babylon.ui.components import WirePanel

        expected_color = "#0d0d0d"

        assert expected_color == WirePanel.LIBERATED_BG

    @pytest.mark.unit
    def test_wire_panel_liberated_text_color(self) -> None:
        """Liberated text color is #00ff88 (data_green).

        Design System Source: ai-docs/gramscian-wire-mvp.yaml
        - Liberated aesthetic: text_color: "#00ff88" (data_green)
        """
        from babylon.ui.components import WirePanel

        expected_color = "#00ff88"

        assert expected_color == WirePanel.LIBERATED_TEXT

    @pytest.mark.unit
    def test_wire_panel_liberated_border_color(self) -> None:
        """Liberated border accent color is #9b59b6 (purple - grow_light).

        Design System Source: ai-docs/gramscian-wire-mvp.yaml
        - Liberated aesthetic: accent_color: "#9b59b6"
        - CSS: border-left: 3px solid #9b59b6
        """
        from babylon.ui.components import WirePanel

        expected_color = "#9b59b6"

        assert expected_color == WirePanel.LIBERATED_BORDER


# =============================================================================
# Log Method Signature Tests
# =============================================================================


class TestWirePanelLogMethod:
    """Test log() method accepts various parameter combinations."""

    @pytest.mark.unit
    def test_log_accepts_event_only(self) -> None:
        """log() can be called with just an event (no narratives).

        Test Intent:
            Events without dual narratives should still be displayable.
            This is the fallback for non-significant events.

        Business Rule:
            Only significant events (UPRISING, EXCESSIVE_FORCE, etc) get
            dual narratives. Other events use single narrative display.
        """
        from babylon.models.enums import EventType
        from babylon.models.events import SimulationEvent
        from babylon.ui.components import WirePanel

        panel = WirePanel()
        event = SimulationEvent(event_type=EventType.SURPLUS_EXTRACTION, tick=5)

        # Should not raise - event-only is valid
        panel.log(event)

    @pytest.mark.unit
    def test_log_accepts_event_and_narratives(self) -> None:
        """log() can be called with event and narratives dict.

        Test Intent:
            Significant events include a narratives dict with both
            "corporate" and "liberated" keys.

        Business Rule:
            Dual narrative display is triggered when narratives dict
            is provided with both perspectives.
        """
        from babylon.models.events import UprisingEvent
        from babylon.ui.components import WirePanel

        panel = WirePanel()
        event = UprisingEvent(
            tick=8,
            node_id="C001",
            trigger="spark",
            agitation=0.9,
            repression=0.7,
        )
        narratives = {
            "corporate": "Authorities responded to disturbances...",
            "liberated": ">>> COMRADES RISE <<<",
        }

        # Should not raise - event + narratives is valid
        panel.log(event, narratives=narratives)

    @pytest.mark.unit
    def test_log_with_narratives_stores_entry(self) -> None:
        """log() with narratives stores entry in internal state.

        Test Intent:
            Verify that calling log() actually persists the entry.
            Similar to SystemLog's _entries pattern.

        Business Rule:
            Entries must be stored for potential replay, history display,
            or debugging.
        """
        from babylon.models.events import UprisingEvent
        from babylon.ui.components import WirePanel

        panel = WirePanel()
        event = UprisingEvent(
            tick=8,
            node_id="C001",
            trigger="spark",
            agitation=0.9,
            repression=0.7,
        )
        narratives = {
            "corporate": "Official response text...",
            "liberated": ">>> Revolutionary signal <<<",
        }

        panel.log(event, narratives=narratives)

        # Internal state should have one entry
        assert len(panel._entries) == 1

    @pytest.mark.unit
    def test_log_without_narratives_stores_entry(self) -> None:
        """log() without narratives also stores entry.

        Test Intent:
            Event-only calls should also persist entries.
        """
        from babylon.models.enums import EventType
        from babylon.models.events import SimulationEvent
        from babylon.ui.components import WirePanel

        panel = WirePanel()
        event = SimulationEvent(event_type=EventType.SURPLUS_EXTRACTION, tick=5)

        panel.log(event)

        # Internal state should have one entry
        assert len(panel._entries) == 1


# =============================================================================
# Rendering Mode Tests
# =============================================================================


class TestWirePanelRenderingModes:
    """Test dual vs single narrative rendering logic."""

    @pytest.mark.unit
    def test_render_dual_called_when_narratives_provided(self) -> None:
        """When narratives dict is provided, dual view is rendered.

        Test Intent:
            Verify the rendering path branches correctly when narratives
            are provided. The _render_dual method (or equivalent) should
            be invoked.

        Business Rule:
            Significant events with dual narratives show side-by-side
            Corporate/Liberated view - this IS the thesis demonstration.
        """
        from babylon.models.events import SparkEvent
        from babylon.ui.components import WirePanel

        panel = WirePanel()
        event = SparkEvent(
            tick=5,
            node_id="C001",
            repression=0.8,
            spark_probability=0.4,
        )
        narratives = {
            "corporate": "Police action in progress...",
            "liberated": ">>> STATE VIOLENCE <<<",
        }

        panel.log(event, narratives=narratives)

        # Entry should be marked as dual narrative
        entry = panel._entries[0]
        assert entry.has_dual_narrative is True

    @pytest.mark.unit
    def test_render_single_called_when_no_narratives(self) -> None:
        """When narratives=None, single view is rendered.

        Test Intent:
            Verify the fallback rendering path for events without
            dual narratives.

        Business Rule:
            Non-significant events use simple single-line display,
            similar to SystemLog behavior.
        """
        from babylon.models.enums import EventType
        from babylon.models.events import SimulationEvent
        from babylon.ui.components import WirePanel

        panel = WirePanel()
        event = SimulationEvent(event_type=EventType.SURPLUS_EXTRACTION, tick=5)

        panel.log(event)

        # Entry should NOT be marked as dual narrative
        entry = panel._entries[0]
        assert entry.has_dual_narrative is False


# =============================================================================
# Internal State Tests
# =============================================================================


class TestWirePanelInternalState:
    """Test internal state management."""

    @pytest.mark.unit
    def test_initializes_with_empty_entries(self) -> None:
        """WirePanel starts with an empty _entries list.

        Test Intent:
            Verify clean initialization state, similar to SystemLog pattern.
        """
        from babylon.ui.components import WirePanel

        panel = WirePanel()

        assert hasattr(panel, "_entries")
        assert panel._entries == []
        assert len(panel._entries) == 0

    @pytest.mark.unit
    def test_multiple_logs_maintain_order(self) -> None:
        """Multiple log() calls maintain chronological order.

        Test Intent:
            Entries should appear in the order they were logged.
        """
        from babylon.models.enums import EventType
        from babylon.models.events import SimulationEvent, SparkEvent
        from babylon.ui.components import WirePanel

        panel = WirePanel()

        event1 = SimulationEvent(event_type=EventType.SURPLUS_EXTRACTION, tick=1)
        event2 = SparkEvent(
            tick=2,
            node_id="C001",
            repression=0.5,
            spark_probability=0.3,
        )
        event3 = SimulationEvent(event_type=EventType.SURPLUS_EXTRACTION, tick=3)

        panel.log(event1)
        panel.log(event2, narratives={"corporate": "...", "liberated": "..."})
        panel.log(event3)

        assert len(panel._entries) == 3
        # Verify chronological order via tick
        assert panel._entries[0].event.tick == 1
        assert panel._entries[1].event.tick == 2
        assert panel._entries[2].event.tick == 3
