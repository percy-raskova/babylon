"""Cross-validation tests for the OODA coefficient derivation chain.

Verifies that all derived coefficients maintain their mathematical
relationships to source primitives and empirical irreducibles.

Level 0 → Level 1: Source primitives derive from 5 empirical irreducibles.
Level 1 → Level 2: OODA coefficients derive from source primitives.

See Also:
    ``docs/reference/ooda-coefficients.rst``: Full derivation tree.
"""

from __future__ import annotations

import math

import pytest

from babylon.config.defines import GameDefines


class TestLevel0ToLevel1:
    """Source primitives derive from empirical irreducibles."""

    COIN_HALFLIFE_WEEKS = 7  # FM 3-24 political half-life

    @pytest.fixture()
    def defines(self) -> GameDefines:
        return GameDefines()

    # --- IR-1: Political Half-Life (τ½ = 7 weeks) ---

    def test_decay_lambda_from_coin_halflife(self, defines: GameDefines) -> None:
        """λ = ln(2)/7 (7-week COIN political half-life, FM 3-24)."""
        expected = math.log(2) / self.COIN_HALFLIFE_WEEKS
        assert abs(defines.consciousness.decay_lambda - expected) < 0.005

    def test_agitation_decay_equals_decay_lambda(self, defines: GameDefines) -> None:
        """Agitation entropy operates on same half-life as consciousness."""
        assert defines.consciousness.agitation_decay_rate == defines.consciousness.decay_lambda

    def test_routing_scale_doubles_decay_lambda_spec_066(self, defines: GameDefines) -> None:
        """Spec-066 bump: routing_scale = 2 × decay_lambda for drift visibility.

        Historical invariant was routing_scale == decay_lambda (same 7-week
        half-life). Spec-066 doubled it to 0.2 because the spec-065 e2e run
        showed <0.1% ideology drift across 520 ticks, well below the SC-005
        >=5% threshold. See spec-066 FR-027 + Phase 0 R4.
        """
        assert defines.consciousness.routing_scale == pytest.approx(
            2 * defines.consciousness.decay_lambda
        )

    def test_heat_decay_equals_decay_lambda(self, defines: GameDefines) -> None:
        """Territory heat entropy on same half-life as consciousness."""
        assert defines.territory.heat_decay_rate == defines.consciousness.decay_lambda

    # --- IR-1 + IR-2: Sensitivity derivation ---

    def test_sensitivity_from_decay_and_extraction(self, defines: GameDefines) -> None:
        """k = λ / (1 - α): full consciousness at full exploitation."""
        lam = defines.consciousness.decay_lambda
        alpha = defines.economy.extraction_efficiency
        expected = lam / (1 - alpha)
        assert abs(defines.consciousness.sensitivity - expected) < 0.001

    # --- IR-2: Imperial Extraction Rate (α = 0.8) ---

    def test_eviction_threshold_equals_extraction(self, defines: GameDefines) -> None:
        """Eviction triggers at extraction capacity α."""
        assert defines.territory.eviction_heat_threshold == defines.economy.extraction_efficiency

    # --- IR-3: Network Percolation Threshold (p_c ≈ 0.3) ---

    def test_activation_threshold_is_percolation(self, defines: GameDefines) -> None:
        """p_c ≈ 0.3: site percolation on social network with ⟨k⟩ ≈ 3-4."""
        assert 0.25 <= defines.solidarity.activation_threshold <= 0.35

    # --- IR-4: Gentrification Rent Premium (1.5×) ---

    def test_heat_gain_from_rent_spike_and_decay(self, defines: GameDefines) -> None:
        """gain = rent_spike × heat_decay (FM 3-24 clear-phase timeline)."""
        expected = defines.territory.rent_spike_multiplier * defines.territory.heat_decay_rate
        assert abs(defines.territory.high_profile_heat_gain - expected) < 0.001

    def test_heat_spillover_is_half_decay(self, defines: GameDefines) -> None:
        """Ink-spot spillover at half the decay rate."""
        expected = defines.territory.heat_decay_rate / 2
        assert abs(defines.territory.heat_spillover_rate - expected) < 0.001

    # --- Cross-system consistency ---

    def test_solidarity_scaling_equals_sensitivity(self, defines: GameDefines) -> None:
        """Solidarity transmission at same scale as material sensitivity."""
        assert defines.solidarity.scaling_factor == defines.consciousness.sensitivity


class TestValidateDerivations:
    """Runtime validation method on OODADefines."""

    def test_default_defines_have_no_drift(self) -> None:
        """Default GameDefines should pass all derivation checks."""
        defines = GameDefines()
        drifts = defines.ooda.validate_derivations(defines)
        assert drifts == []

    def test_detects_drift_when_extraction_changes(self) -> None:
        """If extraction_efficiency changes, repress backfire drifts."""
        defines = GameDefines(economy={"extraction_efficiency": 0.6})  # type: ignore[arg-type]
        drifts = defines.ooda.validate_derivations(defines)
        assert any("action_base_repress" in d for d in drifts)

    def test_detects_drift_when_decay_lambda_changes(self) -> None:
        """If decay_lambda changes, educate multiplier drifts."""
        defines = GameDefines(consciousness={"decay_lambda": 0.2})  # type: ignore[arg-type]
        drifts = defines.ooda.validate_derivations(defines)
        assert any("action_base_educate" in d for d in drifts)


class TestLevel1ToLevel2:
    """OODA coefficients derive from source primitives."""

    @pytest.fixture()
    def defines(self) -> GameDefines:
        return GameDefines()

    # --- Category A: Direct Substitutions ---

    def test_repress_heat_equals_territory(self, defines: GameDefines) -> None:
        """Repression IS high-profile attention."""
        assert defines.ooda.repress_heat_delta == defines.territory.high_profile_heat_gain

    def test_surveil_heat_equals_spillover(self, defines: GameDefines) -> None:
        """Passive surveillance = background state attention."""
        assert defines.ooda.surveil_heat_delta == defines.territory.heat_spillover_rate

    def test_momentum_bonus_equals_solidarity_gain(self, defines: GameDefines) -> None:
        """Organizational momentum analog of solidarity gain."""
        assert defines.ooda.momentum_success_bonus == defines.struggle.solidarity_gain_per_uprising

    def test_agitation_delta_equals_agitation_decay(self, defines: GameDefines) -> None:
        """Equilibrium: agitate once/tick matches natural decay."""
        assert (
            defines.ooda.agitation_contestation_delta == defines.consciousness.agitation_decay_rate
        )

    # --- Category B: Formula Derivations ---

    def test_momentum_decay(self, defines: GameDefines) -> None:
        """momentum_decay = 1 - 2λ (twice as volatile as consciousness)."""
        expected = 1 - 2 * defines.consciousness.agitation_decay_rate
        assert defines.ooda.momentum_decay == expected

    def test_max_ci_delta(self, defines: GameDefines) -> None:
        """max_ci_delta = λ/2 (half decay rate prevents ODE overwhelm)."""
        expected = defines.consciousness.decay_lambda / 2
        assert defines.ooda.max_ci_delta_per_tick == expected

    def test_educate_multiplier(self, defines: GameDefines) -> None:
        """EDUCATE = 1 + 2λ (overcomes decay plus net positive)."""
        expected = 1 + 2 * defines.consciousness.decay_lambda
        assert abs(defines.ooda.action_base_educate - expected) < 0.001

    def test_propagandize_multiplier(self, defines: GameDefines) -> None:
        """PROPAGANDIZE = 1 - 2λ (symmetric inverse of EDUCATE)."""
        expected = 1 - 2 * defines.consciousness.decay_lambda
        assert abs(defines.ooda.action_base_propagandize - expected) < 0.001

    def test_repress_backfire_equals_extraction(self, defines: GameDefines) -> None:
        """Repression backfire = α (extraction visibility)."""
        assert defines.ooda.action_base_repress == defines.economy.extraction_efficiency

    def test_surveil_backfire_is_extraction_complement(self, defines: GameDefines) -> None:
        """Surveillance backfire = 1 - α (invisible fraction)."""
        expected = 1 - defines.economy.extraction_efficiency
        assert abs(defines.ooda.action_base_surveil - expected) < 0.001

    def test_provide_service_decoupled_post_spec_066(self, defines: GameDefines) -> None:
        """PROVIDE_SERVICE = 0.6 (BPP-empirical) decoupled from k + routing_scale.

        Historical derivation (Category B mnemonic): provide_service = 0.5 + 0.1 = 0.6.
        Spec-066 bumped routing_scale 0.1 -> 0.2 but kept provide_service at the
        BPP-empirical 0.6 since the BPP survival-programs calibration is the
        primary source. See defines/ooda.py docstring + spec-066 R4.
        """
        assert defines.ooda.action_base_provide_service == pytest.approx(0.6)

    def test_organize_equals_sensitivity(self, defines: GameDefines) -> None:
        """ORGANIZE = k (operationalizes material sensitivity)."""
        assert defines.ooda.action_base_organize == defines.consciousness.sensitivity

    def test_recruit_equals_activation_threshold(self, defines: GameDefines) -> None:
        """RECRUIT = p_c (bring recruits to percolation threshold)."""
        assert defines.ooda.action_base_recruit == defines.solidarity.activation_threshold

    def test_contestation_threshold_equals_activation(self, defines: GameDefines) -> None:
        """Contestation tipping point = solidarity activation threshold."""
        assert defines.ooda.contestation_threshold == defines.solidarity.activation_threshold

    def test_agitation_educate_bonus_equals_rent_spike(self, defines: GameDefines) -> None:
        """Crisis amplification factor = gentrification rent premium."""
        assert defines.ooda.agitation_educate_bonus == defines.territory.rent_spike_multiplier

    def test_embeddedness_discount_equals_solidarity_scaling(self, defines: GameDefines) -> None:
        """Community roots discount = solidarity scaling factor."""
        assert defines.ooda.embeddedness_discount == defines.solidarity.scaling_factor

    # --- Category C: Empirically Grounded ---

    def test_elder_legitimacy_from_institutional_weight(self, defines: GameDefines) -> None:
        """Elder legitimacy = 1 + lifecycle.ideology_institutional_weight."""
        expected = 1 + defines.lifecycle.ideology_institutional_weight
        assert abs(defines.ooda.elder_legitimacy_multiplier - expected) < 0.001

    def test_counter_intel_matches_decay(self, defines: GameDefines) -> None:
        """Network disruption rate matches consciousness entropy."""
        assert defines.ooda.counter_intel_increment == defines.consciousness.decay_lambda

    def test_outsider_cost_equals_rent_spike(self, defines: GameDefines) -> None:
        """Outsider penalty = Prebisch-Singer terms-of-trade (rent spike)."""
        assert defines.ooda.outsider_cost_multiplier == defines.territory.rent_spike_multiplier

    # --- Decision mode ordering invariant ---

    def test_decision_mode_ordering(self, defines: GameDefines) -> None:
        """AUTOCRATIC < DELEGATE < DEMOCRATIC < CONSENSUS."""
        assert defines.ooda.decision_mode_base_autocratic < defines.ooda.decision_mode_base_delegate
        assert defines.ooda.decision_mode_base_delegate < defines.ooda.decision_mode_base_democratic
        assert (
            defines.ooda.decision_mode_base_democratic < defines.ooda.decision_mode_base_consensus
        )

    # --- Initiative weight structure ---

    def test_speed_weight_is_highest(self, defines: GameDefines) -> None:
        """Speed weight dominates per Boyd's tempo theory."""
        assert defines.ooda.initiative_weight_speed > defines.ooda.initiative_weight_institutional
        assert defines.ooda.initiative_weight_speed > defines.ooda.initiative_weight_counterintel

    def test_momentum_weight_is_lowest(self, defines: GameDefines) -> None:
        """Momentum weight lowest (most volatile component)."""
        assert (
            defines.ooda.initiative_weight_momentum < defines.ooda.initiative_weight_institutional
        )
        assert defines.ooda.initiative_weight_momentum < defines.ooda.initiative_weight_embeddedness

    # --- Institutional bonus ordering ---

    def test_institutional_bonus_ordering(self, defines: GameDefines) -> None:
        """FEDERAL > STATE > LOCAL > NONSTATE."""
        assert defines.ooda.institutional_bonus_federal > defines.ooda.institutional_bonus_state
        assert defines.ooda.institutional_bonus_state > defines.ooda.institutional_bonus_local
        assert defines.ooda.institutional_bonus_local > defines.ooda.institutional_bonus_nonstate
