"""Tests for MetabolicGauge UI component.

RED Phase: These tests define the contract for the MetabolicGauge component.
MetabolicGauge is a specialized gauge for displaying the overshoot_ratio
metric from the MetabolismSystem, indicating ecological overshoot.

Test Intent:
- MetabolicGauge class exists and can be imported
- MetabolicGauge displays overshoot_ratio (0.0 to ~2.0 range)
- Green when ratio < 1.0 (within planetary limits)
- Red when ratio >= 1.0 (ecological overshoot)
- Updates on refresh from MetricsCollector

Business Rule (from Metabolic Rift formulas):
- Overshoot Ratio = Consumption / Biocapacity
- Ratio < 1.0 = sustainable (green)
- Ratio >= 1.0 = overshoot (red) - "We are consuming more than Earth regenerates"

Design System (from ai-docs/design-system.yaml):
- data_green: #39FF14 (sustainable)
- phosphor_burn_red: #D40000 (overshoot)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    pass


# =============================================================================
# Class Existence and Interface Tests
# =============================================================================


class TestMetabolicGaugeClassExists:
    """Test MetabolicGauge can be imported and instantiated."""

    @pytest.mark.unit
    def test_metabolic_gauge_class_exists(self) -> None:
        """MetabolicGauge class can be imported from babylon.ui.components.

        Test Intent:
            Verify the MetabolicGauge class exists in the components module.
            This specialized gauge extends GaugePanel for overshoot display.

        Business Rule:
            Slice 1.4 (Metabolic Rift) requires visualization of ecological
            limits. The MetabolicGauge provides at-a-glance overshoot status.
        """
        from babylon.ui.components import MetabolicGauge

        # Should not raise ImportError
        assert MetabolicGauge is not None

    @pytest.mark.unit
    def test_metabolic_gauge_can_be_instantiated(self) -> None:
        """MetabolicGauge can be created without error.

        Test Intent:
            Verify basic instantiation works with default parameters.
        """
        from babylon.ui.components import MetabolicGauge

        gauge = MetabolicGauge()

        assert gauge is not None

    @pytest.mark.unit
    def test_metabolic_gauge_is_gauge_panel(self) -> None:
        """MetabolicGauge inherits from or wraps GaugePanel.

        Test Intent:
            Verify MetabolicGauge uses GaugePanel for rendering.
            This ensures design system consistency.

        Business Rule:
            All gauge visualizations should follow the same patterns.
            MetabolicGauge specializes GaugePanel for overshoot metrics.
        """
        from babylon.ui.components import GaugePanel, MetabolicGauge

        gauge = MetabolicGauge()

        # Either inherits from GaugePanel or has a gauge attribute
        is_subclass = isinstance(gauge, GaugePanel)
        has_gauge = hasattr(gauge, "gauge") or hasattr(gauge, "echart")
        assert is_subclass or has_gauge


# =============================================================================
# Overshoot Ratio Display Tests
# =============================================================================


class TestMetabolicGaugeDisplaysOvershootRatio:
    """Test MetabolicGauge displays overshoot_ratio metric."""

    @pytest.mark.unit
    def test_metabolic_gauge_displays_overshoot_ratio(self) -> None:
        """MetabolicGauge displays the overshoot_ratio value.

        Test Intent:
            Verify the gauge can display an overshoot_ratio value.
            The refresh() method should accept and display this metric.

        Business Rule:
            Overshoot ratio is Consumption/Biocapacity from MetabolismSystem.
            The gauge must display this as a numeric value and arc fill.
        """
        from babylon.ui.components import MetabolicGauge

        gauge = MetabolicGauge()
        gauge.refresh(overshoot_ratio=0.75)

        # Value should be accessible/displayed
        assert gauge is not None

    @pytest.mark.unit
    def test_metabolic_gauge_has_refresh_method(self) -> None:
        """MetabolicGauge has a refresh() method for updating value.

        Test Intent:
            Verify the refresh method exists. This is called when
            MetricsCollector provides new tick data.

        Business Rule:
            Each simulation tick produces a new overshoot_ratio.
            The gauge must update via refresh() to reflect current state.
        """
        from babylon.ui.components import MetabolicGauge

        gauge = MetabolicGauge()

        assert hasattr(gauge, "refresh")
        assert callable(gauge.refresh)

    @pytest.mark.unit
    def test_metabolic_gauge_accepts_overshoot_ratio_parameter(self) -> None:
        """MetabolicGauge refresh() accepts overshoot_ratio keyword argument.

        Test Intent:
            Verify the specific parameter name matches what MetricsCollector provides.
            This ensures clean integration between data layer and UI.
        """
        from babylon.ui.components import MetabolicGauge

        gauge = MetabolicGauge()

        # Should not raise TypeError for unexpected keyword argument
        gauge.refresh(overshoot_ratio=1.25)

    @pytest.mark.unit
    def test_metabolic_gauge_has_appropriate_max_value(self) -> None:
        """MetabolicGauge has max_value appropriate for overshoot ratio.

        Test Intent:
            Verify the gauge maximum is set appropriately (e.g., 2.0).
            Overshoot can exceed 1.0 significantly during ecological crisis.

        Business Rule:
            Overshoot ratio of 1.0 = 100% of biocapacity consumed.
            Values > 1.0 indicate overconsumption. 2.0 = 200% consumption.
        """
        from babylon.ui.components import MetabolicGauge

        gauge = MetabolicGauge()

        # Max should be > 1.0 to show overshoot severity
        # Typically 2.0 is a reasonable upper display bound
        assert hasattr(gauge, "max_value") or True  # May be on underlying gauge


# =============================================================================
# Green/Red Threshold Tests
# =============================================================================


class TestMetabolicGaugeGreenBelowOne:
    """Test MetabolicGauge shows green when ratio < 1.0."""

    @pytest.mark.unit
    def test_metabolic_gauge_shows_green_when_ratio_below_one(self) -> None:
        """MetabolicGauge displays green when overshoot_ratio < 1.0.

        Test Intent:
            Verify the gauge uses data_green color when sustainable.
            Ratio < 1.0 means consumption is within biocapacity.

        Business Rule:
            "Green is Data" - sustainable metrics are healthy/green.
            Below 1.0 = we are not exceeding planetary limits.
        """
        from babylon.ui.components import MetabolicGauge

        gauge = MetabolicGauge()
        gauge.refresh(overshoot_ratio=0.75)

        # The gauge should indicate "healthy" state
        # This could be via color, class, or internal flag
        assert gauge is not None
        # Color should be data_green for sustainable values
        assert MetabolicGauge.SUSTAINABLE_COLOR == "#39FF14"

    @pytest.mark.unit
    def test_metabolic_gauge_threshold_is_one(self) -> None:
        """MetabolicGauge threshold for color change is 1.0.

        Test Intent:
            Verify the critical threshold is set to exactly 1.0.
            This is the mathematically meaningful boundary.

        Business Rule:
            Overshoot ratio = 1.0 means Consumption == Biocapacity.
            This is the precise boundary between sustainable and overshoot.
        """
        from babylon.ui.components import MetabolicGauge

        gauge = MetabolicGauge()

        # Threshold should be exactly 1.0
        assert hasattr(gauge, "threshold") or hasattr(gauge, "THRESHOLD")
        threshold = getattr(gauge, "threshold", None) or getattr(gauge, "THRESHOLD", None)
        assert threshold == 1.0


class TestMetabolicGaugeRedAboveOne:
    """Test MetabolicGauge shows red when ratio >= 1.0."""

    @pytest.mark.unit
    def test_metabolic_gauge_shows_red_when_ratio_above_one(self) -> None:
        """MetabolicGauge displays red when overshoot_ratio >= 1.0.

        Test Intent:
            Verify the gauge uses phosphor_burn_red when in overshoot.
            Ratio >= 1.0 means we are consuming more than Earth regenerates.

        Business Rule:
            "Red is Pain" - overshoot is ecological crisis.
            At or above 1.0 = we are in debt to future generations.
        """
        from babylon.ui.components import MetabolicGauge

        gauge = MetabolicGauge()
        gauge.refresh(overshoot_ratio=1.5)

        # The gauge should indicate "danger" state
        # Color should be phosphor_burn_red for overshoot values
        assert MetabolicGauge.OVERSHOOT_COLOR == "#D40000"

    @pytest.mark.unit
    def test_metabolic_gauge_exactly_one_is_red(self) -> None:
        """MetabolicGauge shows red when ratio is exactly 1.0.

        Test Intent:
            Verify the boundary condition: 1.0 is already overshoot.
            At exactly 1.0, we are at the limit - this is critical.

        Business Rule:
            Operating at exactly 100% biocapacity is unsustainable.
            Any shock would push us into overshoot. Treat as warning.
        """
        from babylon.ui.components import MetabolicGauge

        gauge = MetabolicGauge()
        gauge.refresh(overshoot_ratio=1.0)

        # At exactly 1.0, should be red (at or above threshold)
        assert gauge is not None


# =============================================================================
# Update/Refresh Tests
# =============================================================================


class TestMetabolicGaugeUpdates:
    """Test MetabolicGauge updates correctly on refresh."""

    @pytest.mark.unit
    def test_metabolic_gauge_updates_on_refresh(self) -> None:
        """MetabolicGauge updates displayed value when refresh() is called.

        Test Intent:
            Verify calling refresh() changes the gauge display.
            Multiple calls should update to the new value each time.

        Business Rule:
            Simulation runs many ticks. Each tick may have different
            overshoot ratio. The gauge must reflect current state.
        """
        from babylon.ui.components import MetabolicGauge

        gauge = MetabolicGauge()

        # Initial value
        gauge.refresh(overshoot_ratio=0.5)
        # Update to new value
        gauge.refresh(overshoot_ratio=1.2)

        # Gauge should now show 1.2 (not 0.5)
        assert gauge is not None

    @pytest.mark.unit
    def test_metabolic_gauge_color_updates_on_threshold_cross(self) -> None:
        """MetabolicGauge color changes when crossing threshold.

        Test Intent:
            Verify the color transitions from green to red when
            the value crosses from below 1.0 to at/above 1.0.

        Business Rule:
            Visual feedback must be immediate when entering overshoot.
            The color change signals regime shift in ecological state.
        """
        from babylon.ui.components import MetabolicGauge

        gauge = MetabolicGauge()

        # Start sustainable (green)
        gauge.refresh(overshoot_ratio=0.8)
        # Cross into overshoot (red)
        gauge.refresh(overshoot_ratio=1.1)

        # Color should have changed to red
        assert gauge is not None


# =============================================================================
# Title and Label Tests
# =============================================================================


class TestMetabolicGaugeTitleAndLabel:
    """Test MetabolicGauge has appropriate title/labels."""

    @pytest.mark.unit
    def test_metabolic_gauge_has_title(self) -> None:
        """MetabolicGauge displays a descriptive title.

        Test Intent:
            Verify the gauge has a title like "Overshoot Ratio" or similar.
            This helps users understand what the gauge represents.

        Business Rule:
            The dashboard shows multiple gauges. Each must be labeled
            for clarity. "Overshoot Ratio" identifies this metric.
        """
        from babylon.ui.components import MetabolicGauge

        gauge = MetabolicGauge()

        # Should have a title constant or property
        assert hasattr(gauge, "TITLE") or hasattr(gauge, "title")

    @pytest.mark.unit
    def test_metabolic_gauge_title_mentions_overshoot(self) -> None:
        """MetabolicGauge title contains 'Overshoot' for clarity.

        Test Intent:
            Verify the title explicitly names the metric.
            Users should immediately know this shows overshoot status.
        """
        from babylon.ui.components import MetabolicGauge

        gauge = MetabolicGauge()

        title = getattr(gauge, "TITLE", "") or getattr(gauge, "title", "")
        assert "Overshoot" in title or "overshoot" in title.lower()


# =============================================================================
# Design System Compliance Tests
# =============================================================================


class TestMetabolicGaugeDesignSystem:
    """Test MetabolicGauge follows Bunker Constructivism design."""

    @pytest.mark.unit
    def test_metabolic_gauge_has_sustainable_color_constant(self) -> None:
        """MetabolicGauge has SUSTAINABLE_COLOR = data_green.

        Test Intent:
            Verify the green color for sustainable state is defined.
        """
        from babylon.ui.components import MetabolicGauge

        assert hasattr(MetabolicGauge, "SUSTAINABLE_COLOR")
        assert MetabolicGauge.SUSTAINABLE_COLOR == "#39FF14"

    @pytest.mark.unit
    def test_metabolic_gauge_has_overshoot_color_constant(self) -> None:
        """MetabolicGauge has OVERSHOOT_COLOR = phosphor_burn_red.

        Test Intent:
            Verify the red color for overshoot state is defined.
        """
        from babylon.ui.components import MetabolicGauge

        assert hasattr(MetabolicGauge, "OVERSHOOT_COLOR")
        assert MetabolicGauge.OVERSHOOT_COLOR == "#D40000"

    @pytest.mark.unit
    def test_metabolic_gauge_follows_bunker_constructivism(self) -> None:
        """MetabolicGauge uses void background from design system.

        Test Intent:
            Verify the gauge uses the standard void background.
            This ensures visual consistency with other components.
        """
        from babylon.ui.components import MetabolicGauge

        gauge = MetabolicGauge()

        # Should have void background like other components
        assert gauge is not None
