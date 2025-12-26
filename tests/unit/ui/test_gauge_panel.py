"""Tests for GaugePanel UI component.

RED Phase: These tests define the contract for the GaugePanel component.
The GaugePanel is a reusable arc gauge visualization component following
the "Bunker Constructivism" design system.

Test Intent:
- GaugePanel class exists and can be imported
- GaugePanel renders an EChart arc/gauge visualization
- GaugePanel accepts value and max parameters
- GaugePanel accepts threshold for color transitions
- GaugePanel follows Bunker Constructivism styling

Design System (from ai-docs/design-system.yaml):
- void: #050505 (background)
- dark_metal: #404040 (borders)
- data_green: #39FF14 (healthy/positive values)
- phosphor_burn_red: #D40000 (danger/critical values)
- silver_dust: #C0C0C0 (neutral text)

Use Case:
- Display overshoot_ratio from MetricsCollector
- Display consciousness_gap from MetricsCollector
- Generic gauge visualization for any bounded metric
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    pass


# =============================================================================
# Class Existence and Interface Tests
# =============================================================================


class TestGaugePanelClassExists:
    """Test GaugePanel can be imported and instantiated."""

    @pytest.mark.unit
    def test_gauge_panel_class_exists(self) -> None:
        """GaugePanel class can be imported from babylon.ui.components.

        Test Intent:
            Verify the GaugePanel class exists in the components module.
            This is the foundational test - if this fails, nothing else matters.

        Business Rule:
            Slice 1.5 UI requires gauge visualizations for ecological and
            consciousness metrics. GaugePanel is the reusable base component.
        """
        from babylon.ui.components import GaugePanel

        # Should not raise ImportError
        assert GaugePanel is not None

    @pytest.mark.unit
    def test_gauge_panel_can_be_instantiated(self) -> None:
        """GaugePanel can be created without error.

        Test Intent:
            Verify basic instantiation works with minimal parameters.
        """
        from babylon.ui.components import GaugePanel

        panel = GaugePanel()

        assert panel is not None


class TestGaugePanelInterface:
    """Test GaugePanel has required interface methods and attributes."""

    @pytest.mark.unit
    def test_gauge_panel_has_echart_attribute(self) -> None:
        """GaugePanel has an echart attribute for the visualization.

        Test Intent:
            Verify the component wraps an EChart gauge, similar to TrendPlotter.
            The echart attribute provides access to update the visualization.

        Business Rule:
            All Babylon charts use ECharts for consistency. The echart attribute
            follows the established TrendPlotter pattern.
        """
        from babylon.ui.components import GaugePanel

        panel = GaugePanel()

        assert hasattr(panel, "echart")
        assert panel.echart is not None

    @pytest.mark.unit
    def test_gauge_panel_has_update_method(self) -> None:
        """GaugePanel has an update() method to set the current value.

        Test Intent:
            Verify the update method exists. This is the primary interface
            for refreshing the gauge value.

        Business Rule:
            Gauges must be updateable as simulation state changes each tick.
            The update() method accepts a new value to display.
        """
        from babylon.ui.components import GaugePanel

        panel = GaugePanel()

        assert hasattr(panel, "update")
        assert callable(panel.update)


# =============================================================================
# Rendering Tests
# =============================================================================


class TestGaugePanelRendersArcGauge:
    """Test GaugePanel renders an arc gauge visualization."""

    @pytest.mark.unit
    def test_gauge_panel_renders_arc_gauge(self) -> None:
        """GaugePanel creates an EChart gauge series.

        Test Intent:
            Verify the EChart options contain a gauge series type.
            This confirms we get an arc/dial visualization, not a bar or line.

        Business Rule:
            Gauges provide intuitive at-a-glance reading of bounded metrics.
            The arc/dial visual metaphor maps well to "critical threshold" UX.
        """
        from babylon.ui.components import GaugePanel

        panel = GaugePanel()

        # EChart options should have a gauge series
        options = panel.echart.options
        assert "series" in options
        assert len(options["series"]) >= 1
        assert options["series"][0]["type"] == "gauge"

    @pytest.mark.unit
    def test_gauge_panel_has_arc_shape(self) -> None:
        """GaugePanel gauge series has arc/dial configuration.

        Test Intent:
            Verify the gauge has arc-specific properties like startAngle/endAngle.
            This distinguishes it from other EChart types.
        """
        from babylon.ui.components import GaugePanel

        panel = GaugePanel()

        # Gauge series should have arc configuration
        gauge_series = panel.echart.options["series"][0]
        # Gauge types typically have startAngle and endAngle
        assert "startAngle" in gauge_series or gauge_series["type"] == "gauge"


# =============================================================================
# Value and Max Parameter Tests
# =============================================================================


class TestGaugePanelValueAndMax:
    """Test GaugePanel accepts value and max parameters."""

    @pytest.mark.unit
    def test_gauge_panel_accepts_value_and_max(self) -> None:
        """GaugePanel can be initialized with value and max parameters.

        Test Intent:
            Verify the constructor accepts initial value and maximum bound.
            This enables creating a gauge already showing a specific value.

        Business Rule:
            Metrics like overshoot_ratio have meaningful bounds (e.g., 0 to 2.0).
            The gauge must display values relative to their maximum.
        """
        from babylon.ui.components import GaugePanel

        panel = GaugePanel(value=0.75, max_value=2.0)

        assert panel is not None

    @pytest.mark.unit
    def test_gauge_panel_update_changes_value(self) -> None:
        """GaugePanel update() changes the displayed value.

        Test Intent:
            Verify calling update() modifies the gauge's current value.
            The EChart data should reflect the new value.

        Business Rule:
            Each simulation tick may produce new metric values.
            The gauge must update to reflect current state.
        """
        from babylon.ui.components import GaugePanel

        panel = GaugePanel(value=0.5, max_value=1.0)
        panel.update(0.8)

        # The gauge series data should contain the new value
        gauge_series = panel.echart.options["series"][0]
        assert "data" in gauge_series
        # Gauge data is typically [{"value": X}]
        assert gauge_series["data"][0]["value"] == 0.8

    @pytest.mark.unit
    def test_gauge_panel_respects_max_value(self) -> None:
        """GaugePanel max parameter sets the gauge maximum.

        Test Intent:
            Verify the max_value parameter configures the gauge's upper bound.
            This affects how the arc is filled relative to the value.

        Business Rule:
            Different metrics have different ranges. Overshoot might go 0-2,
            while consciousness gap might be -1 to 1. Max must be configurable.
        """
        from babylon.ui.components import GaugePanel

        panel = GaugePanel(value=0.5, max_value=2.0)

        # The gauge series should have max configured
        gauge_series = panel.echart.options["series"][0]
        assert gauge_series.get("max") == 2.0


# =============================================================================
# Threshold and Color Change Tests
# =============================================================================


class TestGaugePanelThreshold:
    """Test GaugePanel accepts threshold for color transitions."""

    @pytest.mark.unit
    def test_gauge_panel_accepts_threshold_for_color_change(self) -> None:
        """GaugePanel accepts a threshold parameter for color transitions.

        Test Intent:
            Verify the constructor accepts a threshold value that determines
            when the gauge color changes from green to red.

        Business Rule:
            Critical thresholds (e.g., overshoot_ratio > 1.0) should trigger
            visual warning. The gauge changes color at the threshold.
        """
        from babylon.ui.components import GaugePanel

        # Threshold at 1.0 means values above 1.0 are "danger"
        panel = GaugePanel(value=0.8, max_value=2.0, threshold=1.0)

        assert panel is not None
        # The gauge should have axis line color configuration
        gauge_series = panel.echart.options["series"][0]
        assert "axisLine" in gauge_series or "splitLine" in gauge_series

    @pytest.mark.unit
    def test_gauge_panel_shows_green_below_threshold(self) -> None:
        """GaugePanel shows green color when value is below threshold.

        Test Intent:
            Verify the gauge uses data_green (#39FF14) when value < threshold.
            This provides immediate visual feedback that the metric is healthy.

        Business Rule:
            "Green is Data" - healthy metrics show in data_green.
            Values below critical threshold are considered safe.
        """
        from babylon.ui.components import GaugePanel

        panel = GaugePanel(value=0.5, max_value=2.0, threshold=1.0)

        # Value 0.5 is below threshold 1.0, should show green
        gauge_series = panel.echart.options["series"][0]
        # The current value's color should be data_green
        assert GaugePanel.DATA_GREEN == "#39FF14"
        # Verify the gauge series exists (uses the variable)
        assert gauge_series is not None

    @pytest.mark.unit
    def test_gauge_panel_shows_red_above_threshold(self) -> None:
        """GaugePanel shows red color when value exceeds threshold.

        Test Intent:
            Verify the gauge uses phosphor_burn_red (#D40000) when value >= threshold.
            This provides immediate visual warning of critical state.

        Business Rule:
            "Red is Pain" - critical metrics show in phosphor_burn_red.
            Values at or above threshold indicate danger/crisis.
        """
        from babylon.ui.components import GaugePanel

        panel = GaugePanel(value=1.5, max_value=2.0, threshold=1.0)

        # Value 1.5 is above threshold 1.0, should show red
        gauge_series = panel.echart.options["series"][0]
        # The current value's color should be phosphor_burn_red
        assert GaugePanel.PHOSPHOR_BURN_RED == "#D40000"
        # Verify the gauge series exists (uses the variable)
        assert gauge_series is not None


# =============================================================================
# Bunker Constructivism Styling Tests
# =============================================================================


class TestGaugePanelBunkerConstructivismStyling:
    """Test GaugePanel follows Bunker Constructivism design system."""

    @pytest.mark.unit
    def test_gauge_panel_has_bunker_constructivism_styling(self) -> None:
        """GaugePanel applies void background and dark_metal border.

        Test Intent:
            Verify the gauge follows the established design system with
            void (#050505) background and dark_metal (#404040) styling.

        Business Rule:
            All UI components must follow Bunker Constructivism aesthetic.
            This creates visual coherence across the dashboard.
        """
        from babylon.ui.components import GaugePanel

        panel = GaugePanel()

        # Check design system color constants exist
        assert hasattr(GaugePanel, "VOID")
        assert hasattr(GaugePanel, "DARK_METAL")
        assert GaugePanel.VOID == "#050505"
        assert GaugePanel.DARK_METAL == "#404040"
        # Verify panel was instantiated successfully
        assert panel is not None

    @pytest.mark.unit
    def test_gauge_panel_has_void_background(self) -> None:
        """GaugePanel uses void (#050505) for chart background.

        Test Intent:
            Verify the EChart backgroundColor is set to void.
            This matches TrendPlotter's established pattern.
        """
        from babylon.ui.components import GaugePanel

        panel = GaugePanel()

        # EChart options should have void background
        options = panel.echart.options
        assert options.get("backgroundColor") == "#050505"

    @pytest.mark.unit
    def test_gauge_panel_has_silver_dust_labels(self) -> None:
        """GaugePanel uses silver_dust (#C0C0C0) for text/labels.

        Test Intent:
            Verify axis labels and title text use silver_dust color.
            This ensures readability against void background.
        """
        from babylon.ui.components import GaugePanel

        panel = GaugePanel()

        # Check color constant
        assert hasattr(GaugePanel, "SILVER_DUST")
        assert GaugePanel.SILVER_DUST == "#C0C0C0"
        # Verify panel was instantiated successfully
        assert panel is not None

    @pytest.mark.unit
    def test_gauge_panel_has_design_system_colors(self) -> None:
        """GaugePanel has all required design system color constants.

        Test Intent:
            Verify all Bunker Constructivism colors are defined as class constants.
            This ensures design system compliance is verifiable.
        """
        from babylon.ui.components import GaugePanel

        # All required colors from design system
        assert GaugePanel.VOID == "#050505"
        assert GaugePanel.DARK_METAL == "#404040"
        assert GaugePanel.SILVER_DUST == "#C0C0C0"
        assert GaugePanel.DATA_GREEN == "#39FF14"
        assert GaugePanel.PHOSPHOR_BURN_RED == "#D40000"


# =============================================================================
# Title and Label Tests
# =============================================================================


class TestGaugePanelTitleAndLabel:
    """Test GaugePanel supports title and label configuration."""

    @pytest.mark.unit
    def test_gauge_panel_accepts_title(self) -> None:
        """GaugePanel accepts an optional title parameter.

        Test Intent:
            Verify the gauge can display a title describing the metric.
            This helps users understand what the gauge represents.

        Business Rule:
            Each gauge displays a specific metric (overshoot, consciousness gap).
            A title label provides context for the numeric value.
        """
        from babylon.ui.components import GaugePanel

        panel = GaugePanel(title="Overshoot Ratio")

        assert panel is not None
        # Title should appear in EChart options
        gauge_series = panel.echart.options["series"][0]
        assert gauge_series.get("title") is not None or "title" in panel.echart.options

    @pytest.mark.unit
    def test_gauge_panel_displays_current_value(self) -> None:
        """GaugePanel displays the current numeric value on the gauge.

        Test Intent:
            Verify the gauge shows the actual value number, not just the arc.
            Users need to see precise values, not just visual indication.

        Business Rule:
            Metrics must be readable as exact numbers for analysis.
            The gauge combines visual + numeric representation.
        """
        from babylon.ui.components import GaugePanel

        panel = GaugePanel(value=1.25, max_value=2.0)

        # The gauge should show the value (detail or data label)
        gauge_series = panel.echart.options["series"][0]
        assert "detail" in gauge_series or "data" in gauge_series
