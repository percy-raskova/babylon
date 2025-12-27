"""Tests for Ideological Routing - Wealth Extraction as Crisis Trigger.

TDD Red Phase: Periphery Dynamics Fix.

The current ideology system only triggers consciousness drift when wage_change < 0.
But periphery workers have their wealth EXTRACTED directly via EXPLOITATION edges,
not through wage cuts. Result: periphery is maximally exploited but generates zero
agitation.

This test suite extends the ideological routing formula to recognize wealth
extraction as a crisis condition, enabling periphery workers to develop
revolutionary consciousness from direct exploitation.

Key Formula Extension:
    total_material_loss = |wage_change| + |wealth_change|  (when negative)
    agitation_generated = total_material_loss * LOSS_AVERSION_COEFFICIENT

MLM-TW Theory:
    - Periphery workers experience VALUE EXTRACTION (wealth taken directly)
    - Core workers experience WAGE SUPPRESSION (wages cut during crisis)
    - Both are forms of crisis that should generate agitation
    - The routing (fascism vs revolution) depends on solidarity infrastructure
"""

import pytest

from babylon.systems.formulas import calculate_ideological_routing


@pytest.mark.math
class TestIdeologicalRoutingWealthExtraction:
    """Tests for wealth extraction triggering agitation.

    These tests will FAIL until calculate_ideological_routing() is extended
    to accept a wealth_change parameter. This is the RED phase of TDD.
    """

    def test_wealth_extraction_generates_agitation(self) -> None:
        """Wealth loss (extraction) should generate agitation like wage cuts.

        Periphery workers have wealth extracted directly via EXPLOITATION edges.
        This material loss should generate agitation just like wage cuts do.
        """
        cc, ni, ag = calculate_ideological_routing(
            wage_change=0.0,  # No wage change
            wealth_change=-0.5,  # Wealth extracted!
            solidarity_pressure=0.0,
            current_class_consciousness=0.5,
            current_national_identity=0.5,
            current_agitation=0.0,
        )
        # Agitation should increase from wealth extraction
        assert ag > 0.0, "Wealth extraction should generate agitation"

    def test_wealth_extraction_routes_to_national_identity_without_solidarity(self) -> None:
        """Without solidarity, wealth extraction routes to fascism.

        When workers experience crisis (wealth loss) but have no solidarity
        infrastructure, agitation routes to national_identity (fascist path).
        This is the "socialism or barbarism" bifurcation.
        """
        cc, ni, ag = calculate_ideological_routing(
            wage_change=0.0,
            wealth_change=-0.5,
            solidarity_pressure=0.0,  # No solidarity
            current_class_consciousness=0.5,
            current_national_identity=0.5,
            current_agitation=0.0,
        )
        assert ni > 0.5, "Without solidarity, crisis routes to fascism"
        assert cc == pytest.approx(0.5), "Class consciousness unchanged without solidarity"

    def test_wealth_extraction_routes_to_class_consciousness_with_solidarity(self) -> None:
        """With solidarity, wealth extraction routes to revolution.

        When workers experience crisis (wealth loss) AND have solidarity
        infrastructure, agitation routes to class_consciousness (revolutionary path).
        """
        cc, ni, ag = calculate_ideological_routing(
            wage_change=0.0,
            wealth_change=-0.5,
            solidarity_pressure=0.8,  # High solidarity
            current_class_consciousness=0.5,
            current_national_identity=0.5,
            current_agitation=0.0,
        )
        assert cc > 0.5, "With solidarity, crisis routes to revolution"

    def test_combined_wage_and_wealth_crisis_amplifies_agitation(self) -> None:
        """Both wage cut AND wealth extraction should compound.

        When workers experience BOTH wage cuts and wealth extraction,
        the total material loss compounds. This represents workers in
        extreme crisis conditions (e.g., austerity + dispossession).

        Loss aversion coefficient = 2.25 (Kahneman-Tversky)
        Combined loss = 0.3 + 0.2 = 0.5
        Expected agitation = 0.5 * 2.25 = 1.125
        """
        cc, ni, ag = calculate_ideological_routing(
            wage_change=-0.3,  # Wage cut
            wealth_change=-0.2,  # AND extraction
            solidarity_pressure=0.0,
            current_class_consciousness=0.5,
            current_national_identity=0.5,
            current_agitation=0.0,
        )
        # Combined crisis should generate more agitation than either alone
        assert ag > 1.0, "Combined wage + wealth crisis should generate significant agitation"

    def test_wealth_gain_does_not_generate_agitation(self) -> None:
        """Wealth increase should not generate agitation.

        Only LOSS generates agitation (crisis condition). Wealth gains
        should not trigger the bifurcation logic.
        """
        cc, ni, ag = calculate_ideological_routing(
            wage_change=0.0,
            wealth_change=0.5,  # Wealth GAIN (not extraction)
            solidarity_pressure=0.0,
            current_class_consciousness=0.5,
            current_national_identity=0.5,
            current_agitation=0.0,
        )
        # No new agitation from wealth gain
        # (existing agitation may decay, but no new agitation generated)
        assert ag <= 0.0, "Wealth gain should not generate agitation"

    def test_zero_wealth_change_behaves_like_current_implementation(self) -> None:
        """Zero wealth_change should not affect existing behavior.

        Backward compatibility: when wealth_change=0.0, the formula should
        behave exactly as it did before the extension.
        """
        # Test wage cut without wealth change
        cc, ni, ag = calculate_ideological_routing(
            wage_change=-0.3,
            wealth_change=0.0,  # No wealth change
            solidarity_pressure=0.0,
            current_class_consciousness=0.5,
            current_national_identity=0.5,
            current_agitation=0.0,
        )
        # Should match expected behavior from existing tests
        # wage_change=-0.3, loss_aversion=2.25: 0.3 * 2.25 = 0.675 agitation
        assert ag > 0.5, "Wage cut should still generate agitation with wealth_change=0"


@pytest.mark.math
class TestIdeologicalRoutingBackwardCompatibility:
    """Tests to ensure existing functionality is preserved.

    These tests verify that the wealth_change extension does not break
    existing behavior. They call the function with wealth_change=0.0 to
    simulate the pre-extension behavior.
    """

    def test_wage_cut_still_generates_agitation(self) -> None:
        """Wage cut alone should still generate agitation."""
        cc, ni, ag = calculate_ideological_routing(
            wage_change=-0.4,
            wealth_change=0.0,
            solidarity_pressure=0.0,
            current_class_consciousness=0.5,
            current_national_identity=0.5,
            current_agitation=0.0,
        )
        # 0.4 * 2.25 = 0.9 agitation generated
        assert ag > 0.8, "Wage cut should generate agitation"

    def test_stable_wages_no_extraction_produces_no_new_agitation(self) -> None:
        """No material loss should produce no new agitation."""
        cc, ni, ag = calculate_ideological_routing(
            wage_change=0.0,
            wealth_change=0.0,
            solidarity_pressure=0.5,
            current_class_consciousness=0.5,
            current_national_identity=0.5,
            current_agitation=0.2,  # Pre-existing agitation
        )
        # Agitation should decay (0.2 - 0.1 = 0.1) or stay same
        # No new agitation generated from zero material loss
        assert ag < 0.2, "No material loss should result in agitation decay"
