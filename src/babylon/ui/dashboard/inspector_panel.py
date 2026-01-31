"""InspectorPanel widget for territory details display.

This module provides the InspectorPanel widget that displays Value Tensor
properties for the currently selected territory.

Feature: 007-god-mode-dashboard
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt  # type: ignore[import-not-found]
from PyQt6.QtWidgets import (  # type: ignore[import-not-found]
    QFrame,
    QLabel,
    QVBoxLayout,
)

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QWidget

    from babylon.models.snapshots import TerritoryState

logger = logging.getLogger(__name__)


class InspectorPanel(QFrame):  # type: ignore[misc]
    """Territory details panel displaying Value Tensor properties.

    This panel shows detailed information about the currently selected
    territory, including:
    - Territory ID (FIPS code)
    - Controlling polity
    - Profit rate (formatted as percentage)
    - Equilibrium R
    - Hex count
    - Current tick

    The panel supports multiple display modes:
    - territory: Shows full territory details
    - no_selection: Shows "Click to select" instruction
    - unclaimed: Shows unclaimed hex message
    - error: Shows error with red border styling

    Example:
        >>> panel = InspectorPanel()
        >>> panel.display_territory(territory_state)
        >>> panel.display_no_selection()
        >>> panel.display_error("Connection lost")
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize InspectorPanel.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)

        self.setObjectName("inspector")
        self.setFrameShape(QFrame.Shape.StyledPanel)

        # Create layout
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        # Title label
        self._title_label = QLabel("Territory Inspector")
        self._title_label.setObjectName("title")
        layout.addWidget(self._title_label)

        # Detail labels
        self._territory_id_label = QLabel()
        self._controller_label = QLabel()
        self._profit_rate_label = QLabel()
        self._equilibrium_r_label = QLabel()
        self._hex_count_label = QLabel()
        self._tick_label = QLabel()

        # Message label (for no_selection, unclaimed, error states)
        self._message_label = QLabel()
        self._message_label.setWordWrap(True)

        # Add detail labels to layout
        layout.addWidget(self._territory_id_label)
        layout.addWidget(self._controller_label)
        layout.addWidget(self._profit_rate_label)
        layout.addWidget(self._equilibrium_r_label)
        layout.addWidget(self._hex_count_label)
        layout.addWidget(self._tick_label)
        layout.addWidget(self._message_label)

        # Add stretch to push content to top
        layout.addStretch()

        # Track display mode for testing
        self._showing_details = False

        # Start with no selection
        self.display_no_selection()

        logger.debug("InspectorPanel initialized")

    def display_territory(self, territory: TerritoryState) -> None:
        """Display territory details.

        Args:
            territory: Territory state to display.
        """
        # Clear error styling
        self.setObjectName("inspector")
        self.style().unpolish(self)
        self.style().polish(self)

        # Update title
        self._title_label.setText(f"Territory: {territory.territory_id}")

        # Show detail labels
        self._showing_details = True
        self._show_detail_labels(True)
        self._message_label.hide()

        # Populate details
        self._territory_id_label.setText(f"FIPS Code: {territory.territory_id}")
        self._controller_label.setText(f"Controller: {territory.controlling_polity}")
        self._profit_rate_label.setText(f"Profit Rate: {territory.profit_rate * 100:.1f}%")
        self._equilibrium_r_label.setText(f"Equilibrium R: {territory.equilibrium_r:.2f}")
        self._hex_count_label.setText(f"Hex Claims: {len(territory.hex_claims)}")
        self._tick_label.setText(f"Tick: {territory.tick}")

        logger.debug("Displaying territory: %s", territory.territory_id)

    def display_no_selection(self) -> None:
        """Display no selection message."""
        # Clear error styling
        self.setObjectName("inspector")
        self.style().unpolish(self)
        self.style().polish(self)

        self._title_label.setText("Territory Inspector")

        # Hide detail labels
        self._showing_details = False
        self._show_detail_labels(False)

        # Show instruction message
        self._message_label.setText("Click a hexagon on the map to select a territory.")
        self._message_label.show()

        logger.debug("Displaying no selection state")

    def display_unclaimed(self, h3_index: str) -> None:
        """Display unclaimed hex message.

        Args:
            h3_index: H3 index of the unclaimed hex.
        """
        # Clear error styling
        self.setObjectName("inspector")
        self.style().unpolish(self)
        self.style().polish(self)

        self._title_label.setText("Unclaimed Territory")

        # Hide detail labels
        self._showing_details = False
        self._show_detail_labels(False)

        # Show unclaimed message with H3 index
        self._message_label.setText(f"This hex is unclaimed.\n\nH3 Index: {h3_index}")
        self._message_label.show()

        logger.debug("Displaying unclaimed hex: %s", h3_index)

    def display_error(self, message: str) -> None:
        """Display error message with red border styling.

        Args:
            message: Error message to display.
        """
        # Apply error styling (red border via QSS)
        self.setObjectName("inspector_error")
        self.style().unpolish(self)
        self.style().polish(self)

        self._title_label.setText("Error")

        # Hide detail labels
        self._showing_details = False
        self._show_detail_labels(False)

        # Show error message
        self._message_label.setText(message)
        self._message_label.show()

        logger.warning("Displaying error: %s", message)

    def _show_detail_labels(self, show: bool) -> None:
        """Show or hide the detail labels.

        Args:
            show: True to show, False to hide.
        """
        labels = [
            self._territory_id_label,
            self._controller_label,
            self._profit_rate_label,
            self._equilibrium_r_label,
            self._hex_count_label,
            self._tick_label,
        ]
        for label in labels:
            if show:
                label.show()
            else:
                label.hide()

    def _get_display_text(self) -> str:
        """Get all displayed text for testing.

        Returns:
            Concatenated text from all labels based on current display mode.
        """
        texts = []
        texts.append(self._title_label.text())

        # Check display mode based on what's hidden vs shown
        if self._showing_details:
            texts.append(self._territory_id_label.text())
            texts.append(self._controller_label.text())
            texts.append(self._profit_rate_label.text())
            texts.append(self._equilibrium_r_label.text())
            texts.append(self._hex_count_label.text())
            texts.append(self._tick_label.text())
        else:
            texts.append(self._message_label.text())

        return "\n".join(texts)


__all__ = [
    "InspectorPanel",
]
