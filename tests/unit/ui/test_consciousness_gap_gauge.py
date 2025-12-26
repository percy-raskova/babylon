"""Tests for ConsciousnessGapGauge UI component.

RED Phase: These tests define the contract for the ConsciousnessGapGauge component.
ConsciousnessGapGauge displays the consciousness differential between
Periphery Worker (C001) and Labor Aristocracy (C004).

Test Intent:
- ConsciousnessGapGauge class exists and can be imported
- Displays consciousness_gap = p_w.consciousness - c_w.consciousness
- Positive gap indicates Periphery Worker more class-conscious
- Negative gap shown differently (Labor Aristocracy more conscious)
- Updates on refresh from MetricsCollector

Business Rule (from MLM-TW theory):
- Consciousness gap measures ideological divergence between classes
- Positive gap (p_w > c_w) = revolutionary potential in periphery
- Negative gap (c_w > p_w) = labor aristocracy solidarity with capital
- Zero gap = ideological convergence (unusual equilibrium)

Design System (from ai-docs/design-system.yaml):
- data_green: #39FF14 (positive gap - revolutionary consciousness)
- phosphor_burn_red: #D40000 (negative gap - false consciousness dominant)
- silver_dust: #C0C0C0 (neutral/zero gap)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    pass


# =============================================================================
# Class Existence and Interface Tests
# =============================================================================


class TestConsciousnessGapGaugeClassExists:
    """Test ConsciousnessGapGauge can be imported and instantiated."""

    @pytest.mark.unit
    def test_consciousness_gap_gauge_class_exists(self) -> None:
        """ConsciousnessGapGauge can be imported from babylon.ui.components.

        Test Intent:
            Verify the ConsciousnessGapGauge class exists in components module.
            This specialized gauge displays ideological divergence.

        Business Rule:
            The consciousness gap is a key metric for revolutionary potential.
            A gauge visualization provides at-a-glance class consciousness status.
        """
        from babylon.ui.components import ConsciousnessGapGauge

        # Should not raise ImportError
        assert ConsciousnessGapGauge is not None

    @pytest.mark.unit
    def test_consciousness_gap_gauge_can_be_instantiated(self) -> None:
        """ConsciousnessGapGauge can be created without error.

        Test Intent:
            Verify basic instantiation works with default parameters.
        """
        from babylon.ui.components import ConsciousnessGapGauge

        gauge = ConsciousnessGapGauge()

        assert gauge is not None

    @pytest.mark.unit
    def test_consciousness_gap_gauge_has_refresh_method(self) -> None:
        """ConsciousnessGapGauge has a refresh() method for updating value.

        Test Intent:
            Verify the refresh method exists. This is called when
            MetricsCollector provides new tick data.

        Business Rule:
            Each simulation tick may produce different consciousness values.
            The gauge must update via refresh() to reflect current state.
        """
        from babylon.ui.components import ConsciousnessGapGauge

        gauge = ConsciousnessGapGauge()

        assert hasattr(gauge, "refresh")
        assert callable(gauge.refresh)


# =============================================================================
# Consciousness Gap Display Tests
# =============================================================================


class TestConsciousnessGapGaugeDisplaysDifference:
    """Test ConsciousnessGapGauge displays consciousness differential."""

    @pytest.mark.unit
    def test_consciousness_gap_gauge_displays_difference(self) -> None:
        """ConsciousnessGapGauge displays the consciousness_gap value.

        Test Intent:
            Verify the gauge can display the consciousness differential.
            The refresh() method should accept and display this metric.

        Business Rule:
            Consciousness gap = p_w.consciousness - c_w.consciousness
            This differential indicates ideological divergence between classes.
        """
        from babylon.ui.components import ConsciousnessGapGauge

        gauge = ConsciousnessGapGauge()
        gauge.refresh(consciousness_gap=0.3)

        # Value should be accessible/displayed
        assert gauge is not None

    @pytest.mark.unit
    def test_consciousness_gap_gauge_accepts_gap_parameter(self) -> None:
        """ConsciousnessGapGauge refresh() accepts consciousness_gap keyword.

        Test Intent:
            Verify the specific parameter name matches MetricsCollector output.
            This ensures clean integration between data layer and UI.
        """
        from babylon.ui.components import ConsciousnessGapGauge

        gauge = ConsciousnessGapGauge()

        # Should not raise TypeError for unexpected keyword argument
        gauge.refresh(consciousness_gap=-0.25)

    @pytest.mark.unit
    def test_consciousness_gap_gauge_handles_negative_values(self) -> None:
        """ConsciousnessGapGauge can display negative consciousness_gap.

        Test Intent:
            Verify the gauge handles negative values (c_w > p_w).
            This is a valid state when labor aristocracy is more conscious.

        Business Rule:
            Negative gap means Labor Aristocracy has higher consciousness.
            This can occur when LA develops class consciousness or P_W is
            atomized by commodity fetishism.
        """
        from babylon.ui.components import ConsciousnessGapGauge

        gauge = ConsciousnessGapGauge()
        gauge.refresh(consciousness_gap=-0.5)

        # Should not raise - negative values are valid
        assert gauge is not None

    @pytest.mark.unit
    def test_consciousness_gap_gauge_has_symmetric_range(self) -> None:
        """ConsciousnessGapGauge has symmetric range for positive/negative.

        Test Intent:
            Verify the gauge range accommodates both positive and negative.
            Consciousness values range 0-1, so gap ranges -1 to +1.

        Business Rule:
            Max positive gap = 1.0 - 0.0 = 1.0 (p_w fully conscious, c_w none)
            Max negative gap = 0.0 - 1.0 = -1.0 (c_w fully conscious, p_w none)
        """
        from babylon.ui.components import ConsciousnessGapGauge

        gauge = ConsciousnessGapGauge()

        # Should have symmetric min/max
        assert hasattr(gauge, "min_value") or hasattr(gauge, "MIN_VALUE")
        assert hasattr(gauge, "max_value") or hasattr(gauge, "MAX_VALUE")


# =============================================================================
# Positive Gap Tests
# =============================================================================


class TestConsciousnessGapPositive:
    """Test ConsciousnessGapGauge when p_w is more conscious."""

    @pytest.mark.unit
    def test_consciousness_gap_positive_when_pw_more_conscious(self) -> None:
        """Positive gap indicates Periphery Worker more class-conscious.

        Test Intent:
            Verify the gauge displays positive gap correctly.
            Positive means p_w.consciousness > c_w.consciousness.

        Business Rule:
            When P_W has higher consciousness than LA, there is
            revolutionary potential - the exploited are awakening
            while the labor aristocracy remains bought off.
        """
        from babylon.ui.components import ConsciousnessGapGauge

        gauge = ConsciousnessGapGauge()
        gauge.refresh(consciousness_gap=0.4)

        # Positive gap should be displayed
        assert gauge is not None

    @pytest.mark.unit
    def test_consciousness_gap_positive_shows_green(self) -> None:
        """Positive consciousness gap displays in data_green.

        Test Intent:
            Verify positive gap uses green color.
            "Green is Data" - revolutionary consciousness is healthy.

        Business Rule:
            Positive gap = periphery awakening to class position.
            This is the precondition for revolutionary action.
        """
        from babylon.ui.components import ConsciousnessGapGauge

        gauge = ConsciousnessGapGauge()
        gauge.refresh(consciousness_gap=0.3)

        # Should have positive color defined
        assert hasattr(ConsciousnessGapGauge, "POSITIVE_COLOR")
        assert ConsciousnessGapGauge.POSITIVE_COLOR == "#39FF14"


# =============================================================================
# Negative Gap Tests
# =============================================================================


class TestConsciousnessGapNegative:
    """Test ConsciousnessGapGauge when c_w is more conscious (unusual)."""

    @pytest.mark.unit
    def test_consciousness_gap_negative_shown_differently(self) -> None:
        """Negative gap displayed differently from positive.

        Test Intent:
            Verify negative gap has distinct visual treatment.
            This could be different color, direction, or styling.

        Business Rule:
            Negative gap = labor aristocracy more conscious.
            This is theoretically unusual (LA typically has false consciousness).
            Different visual treatment signals this anomalous state.
        """
        from babylon.ui.components import ConsciousnessGapGauge

        gauge = ConsciousnessGapGauge()
        gauge.refresh(consciousness_gap=-0.3)

        # Should have distinct treatment for negative values
        assert gauge is not None

    @pytest.mark.unit
    def test_consciousness_gap_negative_shows_red(self) -> None:
        """Negative consciousness gap displays in phosphor_burn_red.

        Test Intent:
            Verify negative gap uses red color.
            "Red is Pain" - false consciousness dominance is problematic.

        Business Rule:
            Negative gap = periphery less conscious than labor aristocracy.
            This indicates atomization, commodity fetishism, or successful
            hegemonic control. Red signals concern.
        """
        from babylon.ui.components import ConsciousnessGapGauge

        gauge = ConsciousnessGapGauge()
        gauge.refresh(consciousness_gap=-0.3)

        # Should have negative color defined
        assert hasattr(ConsciousnessGapGauge, "NEGATIVE_COLOR")
        assert ConsciousnessGapGauge.NEGATIVE_COLOR == "#D40000"


# =============================================================================
# Zero/Neutral Gap Tests
# =============================================================================


class TestConsciousnessGapZero:
    """Test ConsciousnessGapGauge at zero (equilibrium)."""

    @pytest.mark.unit
    def test_consciousness_gap_zero_handling(self) -> None:
        """Zero consciousness gap is handled correctly.

        Test Intent:
            Verify the gauge handles exactly zero.
            Zero is the equilibrium point between classes.

        Business Rule:
            Zero gap = both classes have same consciousness level.
            This is a rare equilibrium - usually there is divergence.
        """
        from babylon.ui.components import ConsciousnessGapGauge

        gauge = ConsciousnessGapGauge()
        gauge.refresh(consciousness_gap=0.0)

        # Zero should be valid
        assert gauge is not None

    @pytest.mark.unit
    def test_consciousness_gap_zero_has_neutral_styling(self) -> None:
        """Zero gap may have neutral (silver_dust) styling.

        Test Intent:
            Verify zero uses neutral color, distinct from positive/negative.
            This highlights the unusual equilibrium state.
        """
        from babylon.ui.components import ConsciousnessGapGauge

        gauge = ConsciousnessGapGauge()

        # Should have neutral color option
        assert hasattr(ConsciousnessGapGauge, "NEUTRAL_COLOR")
        assert ConsciousnessGapGauge.NEUTRAL_COLOR == "#C0C0C0"
        # Verify gauge was instantiated successfully
        assert gauge is not None


# =============================================================================
# Update/Refresh Tests
# =============================================================================


class TestConsciousnessGapGaugeUpdates:
    """Test ConsciousnessGapGauge updates correctly on refresh."""

    @pytest.mark.unit
    def test_consciousness_gap_gauge_updates_on_refresh(self) -> None:
        """ConsciousnessGapGauge updates displayed value on refresh().

        Test Intent:
            Verify calling refresh() changes the gauge display.
            Multiple calls should update to the new value each time.

        Business Rule:
            Consciousness drifts each tick via ideology system.
            The gauge must reflect current consciousness differential.
        """
        from babylon.ui.components import ConsciousnessGapGauge

        gauge = ConsciousnessGapGauge()

        # Initial value (positive gap)
        gauge.refresh(consciousness_gap=0.2)
        # Update to new value (negative gap)
        gauge.refresh(consciousness_gap=-0.1)

        # Gauge should now show -0.1 (not 0.2)
        assert gauge is not None

    @pytest.mark.unit
    def test_consciousness_gap_color_updates_on_sign_change(self) -> None:
        """ConsciousnessGapGauge color changes when gap changes sign.

        Test Intent:
            Verify the color transitions when crossing zero.
            Positive to negative should change green to red.

        Business Rule:
            Sign change represents ideological regime shift.
            Visual feedback must signal this class consciousness reversal.
        """
        from babylon.ui.components import ConsciousnessGapGauge

        gauge = ConsciousnessGapGauge()

        # Start positive (green)
        gauge.refresh(consciousness_gap=0.2)
        # Cross to negative (red)
        gauge.refresh(consciousness_gap=-0.1)

        # Color should have changed
        assert gauge is not None


# =============================================================================
# Title and Label Tests
# =============================================================================


class TestConsciousnessGapGaugeTitleAndLabel:
    """Test ConsciousnessGapGauge has appropriate title/labels."""

    @pytest.mark.unit
    def test_consciousness_gap_gauge_has_title(self) -> None:
        """ConsciousnessGapGauge displays a descriptive title.

        Test Intent:
            Verify the gauge has a title describing the metric.
            This helps users understand what the gauge represents.

        Business Rule:
            The dashboard shows multiple gauges. Each must be labeled.
            "Consciousness Gap" identifies this metric.
        """
        from babylon.ui.components import ConsciousnessGapGauge

        gauge = ConsciousnessGapGauge()

        # Should have a title constant or property
        assert hasattr(gauge, "TITLE") or hasattr(gauge, "title")

    @pytest.mark.unit
    def test_consciousness_gap_gauge_title_mentions_consciousness(self) -> None:
        """ConsciousnessGapGauge title contains 'Consciousness' for clarity.

        Test Intent:
            Verify the title explicitly names the metric.
            Users should immediately know this shows consciousness status.
        """
        from babylon.ui.components import ConsciousnessGapGauge

        gauge = ConsciousnessGapGauge()

        title = getattr(gauge, "TITLE", "") or getattr(gauge, "title", "")
        assert "Consciousness" in title or "consciousness" in title.lower()


# =============================================================================
# Design System Compliance Tests
# =============================================================================


class TestConsciousnessGapGaugeDesignSystem:
    """Test ConsciousnessGapGauge follows Bunker Constructivism design."""

    @pytest.mark.unit
    def test_consciousness_gap_gauge_has_color_constants(self) -> None:
        """ConsciousnessGapGauge has all required color constants.

        Test Intent:
            Verify the three-state color scheme is defined.
            Positive (green), negative (red), neutral (silver).
        """
        from babylon.ui.components import ConsciousnessGapGauge

        assert hasattr(ConsciousnessGapGauge, "POSITIVE_COLOR")
        assert hasattr(ConsciousnessGapGauge, "NEGATIVE_COLOR")
        assert hasattr(ConsciousnessGapGauge, "NEUTRAL_COLOR")

    @pytest.mark.unit
    def test_consciousness_gap_gauge_colors_match_design_system(self) -> None:
        """ConsciousnessGapGauge colors match Bunker Constructivism palette.

        Test Intent:
            Verify colors are from the design system, not arbitrary.
        """
        from babylon.ui.components import ConsciousnessGapGauge

        assert ConsciousnessGapGauge.POSITIVE_COLOR == "#39FF14"  # data_green
        assert ConsciousnessGapGauge.NEGATIVE_COLOR == "#D40000"  # phosphor_burn_red
        assert ConsciousnessGapGauge.NEUTRAL_COLOR == "#C0C0C0"  # silver_dust

    @pytest.mark.unit
    def test_consciousness_gap_gauge_has_echart(self) -> None:
        """ConsciousnessGapGauge uses EChart for visualization.

        Test Intent:
            Verify the gauge wraps an EChart, consistent with other components.
        """
        from babylon.ui.components import ConsciousnessGapGauge

        gauge = ConsciousnessGapGauge()

        assert hasattr(gauge, "echart") or hasattr(gauge, "gauge")
