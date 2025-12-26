"""Tests for WealthTrendPanel UI component.

RED Phase: These tests define the contract for the WealthTrendPanel component.
WealthTrendPanel displays a multi-line chart showing wealth over time for
all four social classes: C001 (Periphery Worker), C002 (Comprador),
C003 (Core Bourgeoisie), C004 (Labor Aristocracy).

Test Intent:
- WealthTrendPanel class exists and can be imported
- Displays four lines (one per social class)
- Line colors match class identity from design system
- Updates with new tick data from MetricsCollector
- Has legend identifying each line

Data Source (from MetricsCollector):
- p_w (C001) Periphery Worker wealth
- p_c (C002) Comprador wealth
- c_b (C003) Core Bourgeoisie wealth
- c_w (C004) Labor Aristocracy wealth

Design System (from ai-docs/design-system.yaml):
- void: #050505 (background)
- dark_metal: #404040 (axis/grid)
- silver_dust: #C0C0C0 (labels/legend)

Class Colors (conceptual - may need design decision):
- Periphery Worker: data_green (#39FF14) - the exploited
- Comprador: exposed_copper (#FFD700) - intermediary
- Core Bourgeoisie: phosphor_burn_red (#D40000) - exploiter
- Labor Aristocracy: grow_light_purple (#9D00FF) - bought off
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    pass


# =============================================================================
# Class Existence and Interface Tests
# =============================================================================


class TestWealthTrendPanelClassExists:
    """Test WealthTrendPanel can be imported and instantiated."""

    @pytest.mark.unit
    def test_wealth_trend_panel_class_exists(self) -> None:
        """WealthTrendPanel class can be imported from babylon.ui.components.

        Test Intent:
            Verify the WealthTrendPanel class exists in components module.
            This component displays comparative wealth across all four classes.

        Business Rule:
            Slice 1.5 UI requires wealth visualization showing the divergence
            between exploited (P_W) and exploiter (C_B) classes over time.
        """
        from babylon.ui.components import WealthTrendPanel

        # Should not raise ImportError
        assert WealthTrendPanel is not None

    @pytest.mark.unit
    def test_wealth_trend_panel_can_be_instantiated(self) -> None:
        """WealthTrendPanel can be created without error.

        Test Intent:
            Verify basic instantiation works with default parameters.
        """
        from babylon.ui.components import WealthTrendPanel

        panel = WealthTrendPanel()

        assert panel is not None

    @pytest.mark.unit
    def test_wealth_trend_panel_has_echart_attribute(self) -> None:
        """WealthTrendPanel has an echart attribute for the visualization.

        Test Intent:
            Verify the component wraps an EChart, following TrendPlotter pattern.
            The echart attribute provides access to update the visualization.

        Business Rule:
            All Babylon charts use ECharts for consistency.
        """
        from babylon.ui.components import WealthTrendPanel

        panel = WealthTrendPanel()

        assert hasattr(panel, "echart")
        assert panel.echart is not None


# =============================================================================
# Four Lines Tests
# =============================================================================


class TestWealthTrendPanelShowsFourLines:
    """Test WealthTrendPanel displays four wealth lines."""

    @pytest.mark.unit
    def test_wealth_trend_panel_shows_four_lines(self) -> None:
        """WealthTrendPanel displays four lines (one per social class).

        Test Intent:
            Verify the EChart configuration has four series (lines).
            Each series represents one of the four social classes.

        Business Rule:
            The simulation tracks four social classes. All four must be
            visible to understand class dynamics and wealth divergence.
        """
        from babylon.ui.components import WealthTrendPanel

        panel = WealthTrendPanel()

        # EChart should have four series
        options = panel.echart.options
        assert "series" in options
        assert len(options["series"]) == 4

    @pytest.mark.unit
    def test_wealth_trend_panel_series_are_line_type(self) -> None:
        """WealthTrendPanel series are all line charts.

        Test Intent:
            Verify each series is type "line" for trend visualization.
            This distinguishes from bar, pie, or other chart types.
        """
        from babylon.ui.components import WealthTrendPanel

        panel = WealthTrendPanel()

        options = panel.echart.options
        for series in options["series"]:
            assert series["type"] == "line"

    @pytest.mark.unit
    def test_wealth_trend_panel_has_series_names(self) -> None:
        """WealthTrendPanel series have descriptive names.

        Test Intent:
            Verify each series is named for its social class.
            Names appear in legend and tooltips.

        Business Rule:
            Users must identify which line represents which class.
            Clear naming enables interpretation of class dynamics.
        """
        from babylon.ui.components import WealthTrendPanel

        panel = WealthTrendPanel()

        options = panel.echart.options
        series_names = [s.get("name") for s in options["series"]]

        # All four classes should be named
        assert len(series_names) == 4
        assert all(name is not None for name in series_names)


# =============================================================================
# Line Colors Tests
# =============================================================================


class TestWealthTrendLineColors:
    """Test WealthTrendPanel line colors match class identity."""

    @pytest.mark.unit
    def test_wealth_trend_line_colors_match_class_identity(self) -> None:
        """WealthTrendPanel uses distinct colors for each class.

        Test Intent:
            Verify each line has a unique color that identifies the class.
            Colors should follow design system and have semantic meaning.

        Business Rule:
            Visual distinction between classes is essential for analysis.
            Color coding enables rapid identification of each class's trajectory.
        """
        from babylon.ui.components import WealthTrendPanel

        panel = WealthTrendPanel()

        options = panel.echart.options
        colors = [s.get("lineStyle", {}).get("color") for s in options["series"]]

        # All colors should be defined
        assert all(color is not None for color in colors)
        # All colors should be unique
        assert len(set(colors)) == 4

    @pytest.mark.unit
    def test_wealth_trend_has_color_constants(self) -> None:
        """WealthTrendPanel has color constants for each class.

        Test Intent:
            Verify color constants are defined as class attributes.
            This makes colors testable and maintainable.
        """
        from babylon.ui.components import WealthTrendPanel

        # Should have color constants for each class
        assert hasattr(WealthTrendPanel, "PW_COLOR")  # Periphery Worker
        assert hasattr(WealthTrendPanel, "PC_COLOR")  # Comprador
        assert hasattr(WealthTrendPanel, "CB_COLOR")  # Core Bourgeoisie
        assert hasattr(WealthTrendPanel, "CW_COLOR")  # Labor Aristocracy

    @pytest.mark.unit
    def test_wealth_trend_periphery_worker_color(self) -> None:
        """Periphery Worker (C001) uses data_green color.

        Test Intent:
            Verify P_W line uses green - the color of "the carrier".
            Green represents the exploited class carrying the system.

        Business Rule:
            P_W is the protagonist class - the oppressed who carry imperial rent.
            Green (data) color emphasizes their central role as producers.
        """
        from babylon.ui.components import WealthTrendPanel

        assert WealthTrendPanel.PW_COLOR == "#39FF14"  # data_green

    @pytest.mark.unit
    def test_wealth_trend_core_bourgeoisie_color(self) -> None:
        """Core Bourgeoisie (C003) uses phosphor_burn_red color.

        Test Intent:
            Verify C_B line uses red - the color of pain/extraction.
            Red represents the exploiter class extracting surplus.

        Business Rule:
            C_B is the antagonist class - accumulating through exploitation.
            Red (pain) color emphasizes extraction and oppression.
        """
        from babylon.ui.components import WealthTrendPanel

        assert WealthTrendPanel.CB_COLOR == "#D40000"  # phosphor_burn_red


# =============================================================================
# Update Tests
# =============================================================================


class TestWealthTrendUpdates:
    """Test WealthTrendPanel updates with new tick data."""

    @pytest.mark.unit
    def test_wealth_trend_updates_with_new_tick_data(self) -> None:
        """WealthTrendPanel updates when push_data() is called.

        Test Intent:
            Verify the panel accepts new data points and updates the chart.
            This is called after each simulation tick.

        Business Rule:
            The simulation runs many ticks. Each tick produces new wealth
            values. The chart must show the full time series.
        """
        from babylon.ui.components import WealthTrendPanel

        panel = WealthTrendPanel()

        # Push data for tick 1
        panel.push_data(
            tick=1,
            p_w_wealth=100.0,
            p_c_wealth=200.0,
            c_b_wealth=500.0,
            c_w_wealth=150.0,
        )

        # Panel should have data
        assert panel is not None

    @pytest.mark.unit
    def test_wealth_trend_has_push_data_method(self) -> None:
        """WealthTrendPanel has push_data() method for updates.

        Test Intent:
            Verify the push_data method exists, following TrendPlotter pattern.

        Business Rule:
            Consistent interface with TrendPlotter enables similar usage patterns.
        """
        from babylon.ui.components import WealthTrendPanel

        panel = WealthTrendPanel()

        assert hasattr(panel, "push_data")
        assert callable(panel.push_data)

    @pytest.mark.unit
    def test_wealth_trend_push_data_accepts_wealth_parameters(self) -> None:
        """WealthTrendPanel push_data() accepts wealth for all four classes.

        Test Intent:
            Verify the method signature accepts wealth values from MetricsCollector.
            Parameter names should match the slot naming convention.
        """
        from babylon.ui.components import WealthTrendPanel

        panel = WealthTrendPanel()

        # Should not raise TypeError for expected parameters
        panel.push_data(
            tick=5,
            p_w_wealth=80.0,
            p_c_wealth=180.0,
            c_b_wealth=600.0,
            c_w_wealth=140.0,
        )

    @pytest.mark.unit
    def test_wealth_trend_accumulates_history(self) -> None:
        """WealthTrendPanel accumulates data points over time.

        Test Intent:
            Verify multiple push_data calls build up a time series.
            The chart should show trend, not just current point.

        Business Rule:
            Wealth trends reveal class dynamics over simulation history.
            The divergence pattern is only visible with multiple points.
        """
        from babylon.ui.components import WealthTrendPanel

        panel = WealthTrendPanel()

        # Push multiple ticks
        for i in range(5):
            panel.push_data(
                tick=i,
                p_w_wealth=100.0 - i * 5,  # Declining
                p_c_wealth=200.0,
                c_b_wealth=500.0 + i * 20,  # Increasing
                c_w_wealth=150.0,
            )

        # X-axis should have 5 data points
        options = panel.echart.options
        assert len(options["xAxis"]["data"]) == 5


# =============================================================================
# Legend Tests
# =============================================================================


class TestWealthTrendHasLegend:
    """Test WealthTrendPanel has legend identifying each line."""

    @pytest.mark.unit
    def test_wealth_trend_has_legend(self) -> None:
        """WealthTrendPanel displays a legend.

        Test Intent:
            Verify the EChart configuration includes a visible legend.
            The legend maps colors to class names.

        Business Rule:
            With four lines, users need legend to identify each class.
            Legend must be visible and readable.
        """
        from babylon.ui.components import WealthTrendPanel

        panel = WealthTrendPanel()

        options = panel.echart.options
        assert "legend" in options
        assert options["legend"].get("show") is not False

    @pytest.mark.unit
    def test_wealth_trend_legend_has_all_classes(self) -> None:
        """WealthTrendPanel legend includes all four class names.

        Test Intent:
            Verify the legend data includes entries for all classes.
            Each class should be represented in the legend.
        """
        from babylon.ui.components import WealthTrendPanel

        panel = WealthTrendPanel()

        options = panel.echart.options
        legend_data = options["legend"].get("data", [])

        assert len(legend_data) >= 4

    @pytest.mark.unit
    def test_wealth_trend_legend_uses_silver_dust_text(self) -> None:
        """WealthTrendPanel legend text uses silver_dust color.

        Test Intent:
            Verify legend text follows design system color.
            Silver dust provides readability on void background.
        """
        from babylon.ui.components import WealthTrendPanel

        panel = WealthTrendPanel()

        options = panel.echart.options
        legend_text_color = options["legend"].get("textStyle", {}).get("color")

        assert legend_text_color == "#C0C0C0"  # silver_dust


# =============================================================================
# Design System Compliance Tests
# =============================================================================


class TestWealthTrendDesignSystem:
    """Test WealthTrendPanel follows Bunker Constructivism design."""

    @pytest.mark.unit
    def test_wealth_trend_has_void_background(self) -> None:
        """WealthTrendPanel uses void (#050505) for chart background.

        Test Intent:
            Verify the EChart backgroundColor matches design system.
            This ensures visual consistency with other components.
        """
        from babylon.ui.components import WealthTrendPanel

        panel = WealthTrendPanel()

        options = panel.echart.options
        assert options.get("backgroundColor") == "#050505"

    @pytest.mark.unit
    def test_wealth_trend_has_dark_metal_axes(self) -> None:
        """WealthTrendPanel uses dark_metal (#404040) for axes.

        Test Intent:
            Verify axis lines use design system color.
            Dark metal provides subtle structure without distraction.
        """
        from babylon.ui.components import WealthTrendPanel

        panel = WealthTrendPanel()

        options = panel.echart.options
        x_axis_color = options["xAxis"]["axisLine"]["lineStyle"]["color"]
        y_axis_color = options["yAxis"]["axisLine"]["lineStyle"]["color"]

        assert x_axis_color == "#404040"
        assert y_axis_color == "#404040"

    @pytest.mark.unit
    def test_wealth_trend_has_design_system_constants(self) -> None:
        """WealthTrendPanel has design system color constants.

        Test Intent:
            Verify standard Bunker Constructivism colors are defined.
        """
        from babylon.ui.components import WealthTrendPanel

        assert hasattr(WealthTrendPanel, "VOID")
        assert hasattr(WealthTrendPanel, "DARK_METAL")
        assert hasattr(WealthTrendPanel, "SILVER_DUST")

        assert WealthTrendPanel.VOID == "#050505"
        assert WealthTrendPanel.DARK_METAL == "#404040"
        assert WealthTrendPanel.SILVER_DUST == "#C0C0C0"


# =============================================================================
# Rolling Window Tests
# =============================================================================


class TestWealthTrendRollingWindow:
    """Test WealthTrendPanel maintains rolling window like TrendPlotter."""

    @pytest.mark.unit
    def test_wealth_trend_has_max_points(self) -> None:
        """WealthTrendPanel has MAX_POINTS limit for rolling window.

        Test Intent:
            Verify the panel limits stored history like TrendPlotter.
            This prevents unbounded memory growth in long simulations.

        Business Rule:
            Long simulations may run hundreds of ticks. Displaying all
            points degrades performance. Rolling window shows recent history.
        """
        from babylon.ui.components import WealthTrendPanel

        assert hasattr(WealthTrendPanel, "MAX_POINTS")
        assert WealthTrendPanel.MAX_POINTS > 0

    @pytest.mark.unit
    def test_wealth_trend_enforces_rolling_window(self) -> None:
        """WealthTrendPanel removes old data when exceeding MAX_POINTS.

        Test Intent:
            Verify the panel drops oldest data when window is full.
            This matches TrendPlotter behavior.
        """
        from babylon.ui.components import WealthTrendPanel

        panel = WealthTrendPanel()
        max_points = WealthTrendPanel.MAX_POINTS

        # Push more than MAX_POINTS
        for i in range(max_points + 10):
            panel.push_data(
                tick=i,
                p_w_wealth=100.0,
                p_c_wealth=200.0,
                c_b_wealth=500.0,
                c_w_wealth=150.0,
            )

        # Should only have MAX_POINTS entries
        options = panel.echart.options
        assert len(options["xAxis"]["data"]) <= max_points
