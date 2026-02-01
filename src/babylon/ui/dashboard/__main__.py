"""Entry point for running God Mode Dashboard.

This module allows the dashboard to be launched via:
    python -m babylon.ui.dashboard

Feature: 007-god-mode-dashboard
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QApplication  # type: ignore[import-not-found,unused-ignore]

from babylon.engine.simulation import Simulation
from babylon.protocols import SimulationState
from babylon.ui.dashboard.main_window import DashboardWindow
from babylon.ui.dashboard.testing import MockSimulation

if TYPE_CHECKING:
    pass

# Detroit metropolitan area FIPS codes
DETROIT_FIPS = ["26163", "26125", "26099"]  # Wayne, Oakland, Macomb counties


def parse_args() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        prog="python -m babylon.ui.dashboard",
        description="God Mode Dashboard - Babylon Simulation Visualization",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Launch with demo Detroit territories (no real simulation)",
    )
    return parser.parse_args()


def setup_logging(debug: bool = False) -> None:
    """Configure logging for the dashboard.

    Args:
        debug: Enable DEBUG level logging if True.
    """
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
    )


def main() -> int:
    """Main entry point for the dashboard.

    Returns:
        Exit code (0 for success).
    """
    args = parse_args()
    setup_logging(args.debug)

    logger = logging.getLogger(__name__)
    logger.info("Starting God Mode Dashboard")

    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("Babylon God Mode Dashboard")

    # Create simulation
    simulation: SimulationState
    if args.demo:
        logger.info("Demo mode: Using MockSimulation with Detroit territories")
        simulation = MockSimulation.with_detroit_territories()
    else:
        # Production: Use real QCEW/BEA data from SQLite reference database
        logger.info("Loading real simulation from SQLite database (FIPS: %s)", DETROIT_FIPS)
        simulation = Simulation.from_sqlite(DETROIT_FIPS, year=2022)

    # Create and show dashboard
    window = DashboardWindow(simulation=simulation)
    window.show()

    logger.info("Dashboard window displayed")

    # Run event loop
    exit_code: int = app.exec()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
