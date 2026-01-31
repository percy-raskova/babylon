"""Unit tests for HexBridge QObject.

Tests for the JavaScript-Python bridge that handles hex click events
from the pydeck map and emits Qt signals.

Feature: 007-god-mode-dashboard

TDD Status: RED Phase - These tests are written BEFORE implementation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot

# Import the module that WILL exist - tests will fail initially
try:
    from babylon.ui.dashboard.hex_bridge import HexBridge

    HEX_BRIDGE_EXISTS = True
except ImportError:
    HEX_BRIDGE_EXISTS = False
    HexBridge = None  # type: ignore[misc, assignment]


pytestmark = [
    pytest.mark.skipif(not HEX_BRIDGE_EXISTS, reason="HexBridge not yet implemented"),
]


class TestHexBridgeInitialization:
    """Tests for HexBridge QObject initialization."""

    def test_hex_bridge_is_qobject(self, qtbot: QtBot) -> None:
        """HexBridge should be a QObject subclass."""
        from PyQt6.QtCore import QObject

        from babylon.ui.dashboard.testing import MockSimulation

        mock_sim = MockSimulation.with_detroit_territories()
        bridge = HexBridge(simulation=mock_sim)
        assert isinstance(bridge, QObject)

    def test_hex_bridge_has_hex_selected_signal(self, qtbot: QtBot) -> None:
        """HexBridge should have hex_selected signal."""
        from babylon.ui.dashboard.testing import MockSimulation

        mock_sim = MockSimulation.with_detroit_territories()
        bridge = HexBridge(simulation=mock_sim)

        # Should have the signal
        assert hasattr(bridge, "hex_selected")

    def test_hex_bridge_has_territory_selected_signal(self, qtbot: QtBot) -> None:
        """HexBridge should have territory_selected signal."""
        from babylon.ui.dashboard.testing import MockSimulation

        mock_sim = MockSimulation.with_detroit_territories()
        bridge = HexBridge(simulation=mock_sim)

        assert hasattr(bridge, "territory_selected")

    def test_hex_bridge_has_selection_cleared_signal(self, qtbot: QtBot) -> None:
        """HexBridge should have selection_cleared signal."""
        from babylon.ui.dashboard.testing import MockSimulation

        mock_sim = MockSimulation.with_detroit_territories()
        bridge = HexBridge(simulation=mock_sim)

        assert hasattr(bridge, "selection_cleared")

    def test_hex_bridge_has_unclaimed_hex_clicked_signal(self, qtbot: QtBot) -> None:
        """HexBridge should have unclaimed_hex_clicked signal."""
        from babylon.ui.dashboard.testing import MockSimulation

        mock_sim = MockSimulation.with_detroit_territories()
        bridge = HexBridge(simulation=mock_sim)

        assert hasattr(bridge, "unclaimed_hex_clicked")


class TestHexBridgeOnHexClick:
    """T020: Tests for HexBridge.on_hex_click() slot."""

    def test_on_hex_click_emits_hex_selected(
        self,
        qtbot: QtBot,
    ) -> None:
        """on_hex_click() should emit hex_selected signal with H3 index."""
        from babylon.ui.dashboard.testing import MockSimulation

        mock_sim = MockSimulation.with_detroit_territories()
        bridge = HexBridge(simulation=mock_sim)

        # Set up signal spy
        with qtbot.waitSignal(bridge.hex_selected, timeout=1000) as blocker:
            bridge.on_hex_click("852ab2c7fffffff")

        assert blocker.args == ["852ab2c7fffffff"]

    def test_on_hex_click_emits_territory_selected_for_claimed_hex(
        self,
        qtbot: QtBot,
    ) -> None:
        """on_hex_click() on claimed hex should emit territory_selected."""
        from babylon.ui.dashboard.testing import MockSimulation

        mock_sim = MockSimulation.with_detroit_territories()
        bridge = HexBridge(simulation=mock_sim)

        # 852ab2c7fffffff is claimed by Wayne County (26163)
        with qtbot.waitSignal(bridge.territory_selected, timeout=1000) as blocker:
            bridge.on_hex_click("852ab2c7fffffff")

        # Should emit TerritoryState
        territory = blocker.args[0]
        assert territory.territory_id == "26163"

    def test_on_hex_click_emits_unclaimed_for_unclaimed_hex(
        self,
        qtbot: QtBot,
    ) -> None:
        """on_hex_click() on unclaimed hex should emit unclaimed_hex_clicked."""
        from babylon.ui.dashboard.testing import MockSimulation

        mock_sim = MockSimulation.with_detroit_territories()
        bridge = HexBridge(simulation=mock_sim)

        # 852a1000fffffff is not claimed
        with qtbot.waitSignal(bridge.unclaimed_hex_clicked, timeout=1000) as blocker:
            bridge.on_hex_click("852a1000fffffff")

        assert blocker.args == ["852a1000fffffff"]

    def test_on_hex_click_handles_invalid_h3_gracefully(
        self,
        qtbot: QtBot,
    ) -> None:
        """on_hex_click() with invalid H3 should not crash."""
        from babylon.ui.dashboard.testing import MockSimulation

        mock_sim = MockSimulation.with_detroit_territories()
        bridge = HexBridge(simulation=mock_sim)

        # Should not raise - just log warning
        bridge.on_hex_click("invalid")


class TestHexBridgeTerritoryLookup:
    """T021: Tests for territory lookup via get_node_by_spatial_index()."""

    def test_lookup_claimed_hex_returns_territory(
        self,
        qtbot: QtBot,
    ) -> None:
        """Clicking claimed hex should resolve to correct territory."""
        from babylon.ui.dashboard.testing import MockSimulation

        mock_sim = MockSimulation.with_detroit_territories()
        bridge = HexBridge(simulation=mock_sim)

        # Wayne County hex
        with qtbot.waitSignal(bridge.territory_selected, timeout=1000) as blocker:
            bridge.on_hex_click("852ab2c7fffffff")

        territory = blocker.args[0]
        assert territory.territory_id == "26163"
        assert territory.profit_rate == 0.8

    def test_lookup_different_territory_hexes(
        self,
        qtbot: QtBot,
    ) -> None:
        """Different hexes should resolve to their respective territories."""
        from babylon.ui.dashboard.testing import MockSimulation

        mock_sim = MockSimulation.with_detroit_territories()
        bridge = HexBridge(simulation=mock_sim)

        # Oakland County hex (852ab2dbfffffff)
        with qtbot.waitSignal(bridge.territory_selected, timeout=1000) as blocker:
            bridge.on_hex_click("852ab2dbfffffff")

        territory = blocker.args[0]
        assert territory.territory_id == "26125"  # Oakland

    def test_lookup_unclaimed_hex_returns_none(
        self,
        qtbot: QtBot,
    ) -> None:
        """Clicking unclaimed hex should emit unclaimed signal, not territory."""
        from babylon.ui.dashboard.testing import MockSimulation

        mock_sim = MockSimulation.with_detroit_territories()
        bridge = HexBridge(simulation=mock_sim)

        received_territory = []

        def capture_territory(t):
            received_territory.append(t)

        bridge.territory_selected.connect(capture_territory)

        # Click unclaimed hex
        bridge.on_hex_click("852a1000fffffff")

        # Should NOT have received territory_selected
        assert len(received_territory) == 0


class TestHexBridgeOnBackgroundClick:
    """Tests for HexBridge.on_background_click() slot."""

    def test_on_background_click_emits_selection_cleared(
        self,
        qtbot: QtBot,
    ) -> None:
        """on_background_click() should emit selection_cleared signal."""
        from babylon.ui.dashboard.testing import MockSimulation

        mock_sim = MockSimulation.with_detroit_territories()
        bridge = HexBridge(simulation=mock_sim)

        with qtbot.waitSignal(bridge.selection_cleared, timeout=1000):
            bridge.on_background_click()

    def test_on_background_click_clears_previous_selection(
        self,
        qtbot: QtBot,
    ) -> None:
        """on_background_click() should clear any previous selection state."""
        from babylon.ui.dashboard.testing import MockSimulation

        mock_sim = MockSimulation.with_detroit_territories()
        bridge = HexBridge(simulation=mock_sim)

        # First select a hex
        bridge.on_hex_click("852ab2c7fffffff")

        # Track current selection
        assert bridge.selected_territory_id == "26163"

        # Click background
        bridge.on_background_click()

        # Selection should be cleared
        assert bridge.selected_territory_id is None
