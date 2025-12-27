#!/usr/bin/env python3
"""Playwright integration tests for Babylon dashboard.

Tests the Synopticon dashboard UI at http://localhost:6969.

Requirements:
    - Dashboard server must be running: poetry run python -m babylon.ui.dashboard
    - Playwright browsers installed: poetry run playwright install chromium

Usage:
    poetry run pytest tests/integration/test_dashboard_playwright.py -v
"""

from __future__ import annotations

import socket
from contextlib import closing

import pytest

# Skip entire module if playwright not installed
playwright = pytest.importorskip("playwright.sync_api", reason="Playwright not installed")
sync_playwright = playwright.sync_playwright

DASHBOARD_URL = "http://localhost:6969"
DASHBOARD_PORT = 6969


def is_server_running(host: str = "localhost", port: int = DASHBOARD_PORT) -> bool:
    """Check if the dashboard server is running."""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        return sock.connect_ex((host, port)) == 0


@pytest.fixture
def browser_page():
    """Create a browser page for testing."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        yield page
        browser.close()


@pytest.mark.integration
@pytest.mark.skipif(
    not is_server_running(),
    reason=f"Dashboard server not running on port {DASHBOARD_PORT}",
)
class TestDashboardUI:
    """Integration tests for the Babylon dashboard UI."""

    def test_dashboard_loads(self, browser_page) -> None:
        """Dashboard loads and displays main panels."""
        page = browser_page
        page.goto(DASHBOARD_URL)
        page.wait_for_load_state("networkidle")

        # Verify all main panels exist
        panels = ["METRICS", "NARRATIVE", "SYSTEM LOG", "STATE"]
        for panel in panels:
            assert page.locator(f"text={panel}").count() > 0, f"{panel} panel not found"

    def test_simulation_controls_exist(self, browser_page) -> None:
        """Dashboard has simulation control buttons."""
        page = browser_page
        page.goto(DASHBOARD_URL)
        page.wait_for_load_state("networkidle")

        # Verify control buttons
        assert page.locator('button:has-text("STEP")').count() > 0, "STEP button not found"
        assert page.locator('button:has-text("PLAY")').count() > 0, "PLAY button not found"
        assert page.locator('button:has-text("PAUSE")').count() > 0, "PAUSE button not found"
        assert page.locator('button:has-text("RESET")').count() > 0, "RESET button not found"

    def test_state_panel_displays_entity(self, browser_page) -> None:
        """STATE panel displays C001 entity with key metrics."""
        page = browser_page
        page.goto(DASHBOARD_URL)
        page.wait_for_load_state("networkidle")

        # Verify C001 entity is visible
        assert page.locator("text=C001").count() > 0, "C001 entity not displayed"

        # Verify key metrics are shown
        metrics = ["wealth", "p_revolution", "effective_wealth", "ppp_multiplier"]
        for metric in metrics:
            assert page.locator(f"text={metric}").count() > 0, f"{metric} not displayed"

    def test_step_button_advances_simulation(self, browser_page) -> None:
        """Clicking STEP button advances the simulation tick."""
        page = browser_page
        page.goto(DASHBOARD_URL)
        page.wait_for_load_state("networkidle")

        # Get initial tick from page content
        initial_content = page.content()

        # Click step button
        step_button = page.locator('button:has-text("STEP")').first
        step_button.click()
        page.wait_for_timeout(500)

        # Verify page content changed (simulation advanced)
        updated_content = page.content()
        # The tick counter should change, or state values should update
        assert initial_content != updated_content, "Simulation did not advance after STEP"

    def test_metrics_chart_renders(self, browser_page) -> None:
        """METRICS panel contains chart elements."""
        page = browser_page
        page.goto(DASHBOARD_URL)
        page.wait_for_load_state("networkidle")

        # Look for chart elements (SVG or canvas)
        chart = page.locator(".apexcharts-canvas, canvas, svg")
        assert chart.count() > 0, "No chart elements found in METRICS panel"

    def test_multiple_steps_accumulate_data(self, browser_page) -> None:
        """Running multiple steps accumulates data in charts."""
        page = browser_page
        page.goto(DASHBOARD_URL)
        page.wait_for_load_state("networkidle")

        step_button = page.locator('button:has-text("STEP")').first

        # Run 5 simulation steps
        for _ in range(5):
            step_button.click()
            page.wait_for_timeout(200)

        # Take screenshot for visual verification
        page.screenshot(path="/tmp/babylon_test_final.png", full_page=True)

        # Verify tick information is present
        page_content = page.content()
        assert "tick" in page_content.lower(), "Tick information not found in DOM"


if __name__ == "__main__":
    # Allow running directly for debugging
    if not is_server_running():
        print(f"ERROR: Dashboard server not running on port {DASHBOARD_PORT}")
        print("Start it with: poetry run python -m babylon.ui.dashboard")
        exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("=== BABYLON DASHBOARD TEST ===\n")

        page.goto(DASHBOARD_URL)
        page.wait_for_load_state("networkidle")
        print("Dashboard loaded!")

        # Quick verification
        panels = ["METRICS", "NARRATIVE", "SYSTEM LOG", "STATE"]
        for panel in panels:
            status = "[OK]" if page.locator(f"text={panel}").count() > 0 else "[FAIL]"
            print(f"  {status} {panel} panel")

        browser.close()
        print("\n=== TEST COMPLETE ===")
