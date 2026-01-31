"""DashboardWindow interface contract.

This module defines the expected interface for the main dashboard window.
Implementation goes in src/babylon/ui/dashboard/main_window.py.

Feature: 007-god-mode-dashboard
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QWidget

    from babylon.protocols import SimulationControl, SimulationState


class DashboardWindowProtocol(Protocol):
    """Main dashboard window interface.

    The DashboardWindow is the top-level container that:
    1. Creates and lays out MapViewport and InspectorPanel
    2. Connects to simulation via observer pattern
    3. Routes hex clicks from map to inspector
    4. Manages cleanup on close

    Example:
        >>> from babylon.engine.simulation import Simulation
        >>> sim = Simulation()
        >>> dashboard = DashboardWindow(sim)
        >>> dashboard.show()
    """

    def __init__(
        self,
        simulation: SimulationState & SimulationControl,
        parent: QWidget | None = None,
    ) -> None:
        """Create dashboard window.

        Args:
            simulation: Object implementing both SimulationState (for queries)
                and SimulationControl (for observer registration).
            parent: Optional parent widget.

        The constructor:
        1. Creates MapViewport with initial snapshot
        2. Creates InspectorPanel (initially no selection)
        3. Sets up QSplitter layout (70% map, 30% inspector)
        4. Registers DashboardObserver with simulation
        5. Applies Bunker Constructivism theme
        """
        ...

    def show(self) -> None:
        """Show the dashboard window.

        Standard QMainWindow.show() behavior.
        Window appears at default position/size (1460×820).
        """
        ...

    def close(self) -> bool:
        """Close the dashboard window.

        Cleanup sequence:
        1. Unregister observer from simulation
        2. Clean up QWebChannel
        3. Release WebGL resources
        4. Close window

        Returns:
            True if close succeeded.
        """
        ...


# Type alias for implementations
DashboardWindow = DashboardWindowProtocol

__all__ = ["DashboardWindowProtocol", "DashboardWindow"]
