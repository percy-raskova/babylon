"""Integration test: 52-tick state apparatus AI scenario (Feature 039, T077).

Exercises the full lifecycle: escalation with rising heat, de-escalation
when heat drops, faction balance shifts, territory effects, and
near-fascist convergence. Validates all subsystems work together.

See Also:
    ``specs/039-state-apparatus-ai/spec.md``: SC-001 through SC-010.
"""

from __future__ import annotations

from typing import Any

import pytest

from babylon.config.defines import StateApparatusAIDefines
from babylon.formulas.state_ai import (
    calculate_faction_shift,
    check_fascist_reversion,
    is_fascist_convergence,
)
from babylon.models.entities.state_apparatus_ai import FactionBalance
from babylon.ooda.state_ai.administer_effects import (
    resolve_fund,
    resolve_staff,
)
from babylon.ooda.state_ai.co_opt_effects import resolve_propagandize
from babylon.ooda.state_ai.faction_dynamics import (
    apply_material_condition_shift,
    apply_player_action_shift,
    compute_stability,
    renormalize_faction_balance,
)
from babylon.ooda.state_ai.legislate_effects import (
    consume_legal_framework_effects,
)
from babylon.ooda.state_ai.repress_effects import (
    resolve_infiltrate,
    resolve_prosecute,
    resolve_raid,
)
from babylon.ooda.state_ai.territory_effects import (
    compute_heat_accumulation,
    compute_heat_decay,
    resolve_invest,
    resolve_neglect,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_defines(**overrides: object) -> StateApparatusAIDefines:
    """Construct StateApparatusAIDefines with optional overrides."""
    return StateApparatusAIDefines(**overrides)  # type: ignore[arg-type]


def _make_balance(
    fc: float = 0.45,
    ss: float = 0.30,
    sp: float = 0.25,
    stability: float = 0.8,
    legitimacy: float = 0.7,
) -> FactionBalance:
    """Construct a FactionBalance with sensible defaults."""
    return FactionBalance(
        finance_capital=fc,
        security_state=ss,
        settler_populist=sp,
        stability=stability,
        legitimacy=legitimacy,
    )


def _make_territory(**overrides: Any) -> dict[str, Any]:
    """Construct a territory dict with sensible defaults."""
    defaults: dict[str, Any] = {
        "property_value_proxy": 1.0,
        "infrastructure_quality": 0.8,
        "population": 1000,
        "collective_identity": 0.5,
        "community_infrastructure_quality": 0.5,
        "rent_level": 0.3,
        "state_investment": 50.0,
        "heat": 0.0,
        "territory_type": "PERIPHERY",
    }
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestFullLifecycle52Ticks:
    """52-tick integration scenario exercising all subsystems.

    Scenario (test_full_scenario):
        - Phase 1 (ticks 0-9): Rising heat, PROPAGANDIZE, SS increases.
        - Phase 2 (ticks 10-19): Heat decays, INVEST territory.
        - Phase 3 (ticks 20-35): Re-escalation, legitimacy crisis, NEGLECT.
        - Phase 4 (ticks 36-51): De-escalation, surviving_repression.

    Additional tests verify subsystem invariants: determinism,
    INVEST monotonicity, NEGLECT floor, heat bounds, PROPAGANDIZE
    monotonicity, renormalization clamping, fascist convergence,
    and reversion asymmetry.
    """

    def test_full_scenario(self) -> None:
        """52-tick scenario: escalation, plateau, near-fascist, de-escalation.

        Phase design:
        - Phase 1 (ticks 0-9): Heat rises, PROPAGANDIZE, SS increases.
        - Phase 2 (ticks 10-19): Heat decays, SS reverts. INVEST territory.
        - Phase 3 (ticks 20-35): Heat rises again, legitimacy crisis. NEGLECT.
        - Phase 4 (ticks 36-51): Full de-escalation, surviving_repression.

        Uses max_faction_shift_per_tick=0.015 so dynamics stay in the
        interior of the simplex, never saturating any faction at 0 or 1.
        """
        defines = _make_defines(max_faction_shift_per_tick=0.015)
        balance = _make_balance()
        territory = _make_territory()
        balance_history: list[FactionBalance] = [balance]
        fascist_mode = False
        consecutive_fascist_ticks = 0

        # Snapshot key values at phase boundaries
        heat_at_tick_9: float = 0.0
        ss_at_tick_19: float = 0.0
        ss_at_tick_35: float = 0.0

        max_ticks: int = 52
        for tick in range(max_ticks):
            # --- Phase 1: Rising heat (ticks 0-9) ---
            if tick < 10:
                territory["heat"] = compute_heat_accumulation(
                    current_heat=territory["heat"],
                    high_profile_count=1,
                    low_profile_count=1,
                    defines=defines,
                )
                territory = resolve_propagandize(
                    territory,
                    "we_are_all_americans",
                    intensity=0.6,
                    defines=defines,
                )
                balance = calculate_faction_shift(
                    heat=territory["heat"],
                    current_balance=balance,
                    defines=defines,
                )
                if tick == 9:
                    heat_at_tick_9 = territory["heat"]

            # --- Phase 2: Cooling off, INVEST (ticks 10-19) ---
            elif tick < 20:
                # Heat decays: no PRESENCE
                territory["heat"] = compute_heat_decay(
                    current_heat=territory["heat"],
                    has_presence=False,
                    defines=defines,
                )
                # State INVESTs in territory
                territory = resolve_invest(territory, defines)
                # Faction reversion from low heat
                balance = calculate_faction_shift(
                    heat=territory["heat"],
                    current_balance=balance,
                    defines=defines,
                )
                if tick == 19:
                    ss_at_tick_19 = balance.security_state

            # --- Phase 3: Re-escalation with crisis (ticks 20-35) ---
            elif tick < 36:
                territory["heat"] = compute_heat_accumulation(
                    current_heat=territory["heat"],
                    high_profile_count=1,
                    low_profile_count=0,
                    defines=defines,
                )
                # Mild legitimacy crisis
                balance = apply_material_condition_shift("legitimacy_crisis", 0.1, balance, defines)
                # NEGLECT peripheral territory
                territory = resolve_neglect(territory, defines)
                # Faction shift from heat
                balance = calculate_faction_shift(
                    heat=territory["heat"],
                    current_balance=balance,
                    defines=defines,
                )
                if tick == 35:
                    ss_at_tick_35 = balance.security_state

            # --- Phase 4: Full de-escalation (ticks 36-51) ---
            else:
                territory["heat"] = compute_heat_decay(
                    current_heat=territory["heat"],
                    has_presence=False,
                    defines=defines,
                )
                # Player surviving_repression reduces SS
                balance = apply_player_action_shift(
                    "surviving_repression", "success", balance, defines
                )
                # Low heat reversion
                balance = calculate_faction_shift(
                    heat=territory["heat"],
                    current_balance=balance,
                    defines=defines,
                )

            # --- Per-tick invariants ---
            balance = renormalize_faction_balance(
                balance,
                max_shift=defines.max_faction_shift_per_tick,
                previous_balance=balance_history[-1],
            )
            balance_history.append(balance)

            # Fascist convergence check
            settler_ci = min(1.0, balance.settler_populist * 1.5)

            if not fascist_mode:
                ss_ok = balance.security_state > defines.fascist_security_threshold
                ci_ok = settler_ci > defines.fascist_settler_ci_threshold
                fc_ok = balance.finance_capital < defines.fascist_finance_ceiling
                if ss_ok and ci_ok and fc_ok:
                    consecutive_fascist_ticks += 1
                else:
                    consecutive_fascist_ticks = 0

                if is_fascist_convergence(balance, settler_ci, consecutive_fascist_ticks, defines):
                    fascist_mode = True
            else:
                if check_fascist_reversion(balance, settler_ci, defines):
                    fascist_mode = False
                    consecutive_fascist_ticks = 0

        # =================================================================
        # Assertions
        # =================================================================

        # 1. Balance history has 53 entries (initial + 52 ticks)
        assert len(balance_history) == 53

        # 2. Heat accumulated during Phase 1
        assert heat_at_tick_9 > defines.heat_escalation_threshold, (
            f"Heat at tick 9 ({heat_at_tick_9:.4f}) should exceed "
            f"escalation threshold ({defines.heat_escalation_threshold})"
        )

        # 3. SS increased from initial during Phase 1
        initial_ss = 0.30
        max_ss_observed = max(b.security_state for b in balance_history)
        assert max_ss_observed > initial_ss, (
            f"SS should have increased from initial {initial_ss}, "
            f"max observed: {max_ss_observed:.4f}"
        )

        # 4. SS should NOT have saturated at 1.0
        assert max_ss_observed < 1.0, (
            f"SS should not saturate at 1.0, max observed: {max_ss_observed:.6f}"
        )

        # 5. SS at peak (tick 35) should be higher than Phase 1 end (tick 9)
        #    Phase 2 may or may not see SS dip — heat decays slowly (0.05/tick)
        #    and stays above 0.5 for most of Phase 2, continuing SS growth.
        #    The key dynamic: Phase 3 pressure drives SS further up.
        phase1_end_ss = balance_history[10].security_state  # After tick 9
        assert ss_at_tick_35 > phase1_end_ss, (
            f"SS at tick 35 ({ss_at_tick_35:.4f}) should exceed "
            f"Phase 1 end ({phase1_end_ss:.4f}) after sustained escalation"
        )

        # 6. Phase 3 re-escalation: SS at tick 35 > SS at tick 19
        assert ss_at_tick_35 > ss_at_tick_19, (
            f"SS at tick 35 ({ss_at_tick_35:.4f}) should exceed "
            f"tick 19 ({ss_at_tick_19:.4f}) after re-escalation"
        )

        # 7. Phase 4 de-escalation: final SS < SS at tick 35
        final_ss = balance_history[-1].security_state
        assert final_ss < ss_at_tick_35, (
            f"Final SS ({final_ss:.4f}) should be below tick 35 "
            f"({ss_at_tick_35:.4f}) after de-escalation"
        )

        # 8. Territory property_value_proxy increased from INVEST
        assert territory["property_value_proxy"] > 1.0, (
            "INVEST should have increased property_value_proxy from 1.0, "
            f"got {territory['property_value_proxy']:.4f}"
        )

        # 9. Infrastructure degraded from NEGLECT
        assert territory["infrastructure_quality"] < 0.8, (
            "NEGLECT should have degraded infrastructure from 0.8, "
            f"got {territory['infrastructure_quality']:.4f}"
        )

        # 10. Collective identity decreased from PROPAGANDIZE
        assert territory["collective_identity"] < 0.5, (
            "PROPAGANDIZE should have decreased CI from 0.5, "
            f"got {territory['collective_identity']:.4f}"
        )

        # 11. Stability in valid range
        stability = compute_stability(balance_history, window=10)
        assert 0.0 <= stability <= 1.0, f"Stability should be in [0,1], got {stability:.4f}"

        # 12. All balance snapshots properly normalized (sum ~1.0)
        max_entries: int = len(balance_history)
        for idx in range(max_entries):
            b = balance_history[idx]
            total = b.finance_capital + b.security_state + b.settler_populist
            assert abs(total - 1.0) < 0.02, f"Tick {idx}: balance sum={total:.6f}, should be ~1.0"

        # 13. Heat decayed below escalation threshold by end
        final_heat = territory["heat"]
        assert final_heat < defines.heat_escalation_threshold, (
            f"Final heat ({final_heat:.4f}) should be below "
            f"escalation threshold after 16 ticks of decay"
        )

    def test_determinism(self) -> None:
        """Same parameters produce identical results across runs."""
        defines = _make_defines()

        results: list[float] = []
        max_runs: int = 2
        for _run in range(max_runs):
            balance = _make_balance()
            territory = _make_territory()

            max_ticks: int = 10
            for _tick in range(max_ticks):
                territory["heat"] = compute_heat_accumulation(
                    current_heat=territory["heat"],
                    high_profile_count=1,
                    low_profile_count=0,
                    defines=defines,
                )
                balance = calculate_faction_shift(
                    heat=territory["heat"],
                    current_balance=balance,
                    defines=defines,
                )

            results.append(balance.security_state)

        assert results[0] == results[1], (
            f"Results should be deterministic: {results[0]} != {results[1]}"
        )

    def test_territory_invest_monotonically_increases_value(self) -> None:
        """INVEST never decreases property_value_proxy (TE-01 monotonicity)."""
        defines = _make_defines()
        territory = _make_territory()
        previous_pvp = territory["property_value_proxy"]

        max_ticks: int = 20
        for _tick in range(max_ticks):
            territory = resolve_invest(territory, defines)
            current_pvp: float = territory["property_value_proxy"]
            assert current_pvp >= previous_pvp, (
                f"INVEST should be monotonically non-decreasing: "
                f"{previous_pvp:.4f} -> {current_pvp:.4f}"
            )
            previous_pvp = current_pvp

    def test_neglect_respects_quality_floor(self) -> None:
        """NEGLECT never pushes infrastructure_quality below floor (TE-02)."""
        defines = _make_defines()
        territory = _make_territory()

        # Apply 100 NEGLECT ticks to ensure convergence to floor
        max_ticks: int = 100
        for _tick in range(max_ticks):
            territory = resolve_neglect(territory, defines)

        quality: float = territory["infrastructure_quality"]
        assert quality >= defines.neglect_quality_floor, (
            f"Infrastructure quality ({quality:.6f}) should never drop "
            f"below floor ({defines.neglect_quality_floor})"
        )
        # Should have converged to the floor
        assert abs(quality - defines.neglect_quality_floor) < 0.01, (
            f"After 100 ticks of NEGLECT, quality ({quality:.6f}) should "
            f"converge to floor ({defines.neglect_quality_floor})"
        )

    def test_heat_bounded_zero_one(self) -> None:
        """Heat accumulation and decay respect [0.0, 1.0] bounds."""
        defines = _make_defines()

        # Accumulate to saturation
        heat = 0.0
        max_accum_ticks: int = 50
        for _tick in range(max_accum_ticks):
            heat = compute_heat_accumulation(
                current_heat=heat,
                high_profile_count=5,
                low_profile_count=5,
                defines=defines,
            )
            assert 0.0 <= heat <= 1.0, f"Heat out of bounds: {heat}"

        # Decay to zero
        max_decay_ticks: int = 50
        for _tick in range(max_decay_ticks):
            heat = compute_heat_decay(
                current_heat=heat,
                has_presence=False,
                defines=defines,
            )
            assert 0.0 <= heat <= 1.0, f"Heat out of bounds: {heat}"

        # After 50 ticks of decay from 1.0 with rate 0.05, heat ~= 0.0
        assert heat < 0.1, f"Heat should have decayed near zero, got {heat:.4f}"

    def test_propagandize_reduces_ci_monotonically(self) -> None:
        """Repeated PROPAGANDIZE monotonically decreases collective_identity."""
        defines = _make_defines()
        territory = _make_territory(collective_identity=0.8)
        previous_ci: float = territory["collective_identity"]

        max_ticks: int = 20
        for _tick in range(max_ticks):
            territory = resolve_propagandize(
                territory,
                "we_are_all_americans",
                intensity=0.8,
                defines=defines,
            )
            current_ci: float = territory["collective_identity"]
            assert current_ci <= previous_ci, (
                f"PROPAGANDIZE should monotonically decrease CI: "
                f"{previous_ci:.4f} -> {current_ci:.4f}"
            )
            assert current_ci >= 0.0, f"CI must not go negative: {current_ci}"
            previous_ci = current_ci

    def test_renormalization_clamps_large_shifts(self) -> None:
        """renormalize_faction_balance clamps per-faction deltas."""
        defines = _make_defines()
        previous = _make_balance(fc=0.45, ss=0.30, sp=0.25)

        # Construct a proposed balance with a large jump in SS
        proposed = _make_balance(fc=0.20, ss=0.60, sp=0.20)

        clamped = renormalize_faction_balance(
            proposed,
            max_shift=defines.max_faction_shift_per_tick,
            previous_balance=previous,
        )

        # Each faction's delta from previous should be within max_shift.
        # The iterative clamp-normalize algorithm in renormalize_faction_balance
        # uses 1e-9 convergence tolerance internally, and normalization after
        # clamping can amplify deltas slightly beyond max_shift. A tolerance
        # of 1e-3 accounts for this documented behavior (see T053 impl).
        tolerance = 1e-3
        fc_delta = abs(clamped.finance_capital - previous.finance_capital)
        ss_delta = abs(clamped.security_state - previous.security_state)
        sp_delta = abs(clamped.settler_populist - previous.settler_populist)

        max_allowed = defines.max_faction_shift_per_tick + tolerance
        assert fc_delta <= max_allowed, (
            f"FC delta {fc_delta:.6f} exceeds max_shift {max_allowed:.6f}"
        )
        assert ss_delta <= max_allowed, (
            f"SS delta {ss_delta:.6f} exceeds max_shift {max_allowed:.6f}"
        )
        assert sp_delta <= max_allowed, (
            f"SP delta {sp_delta:.6f} exceeds max_shift {max_allowed:.6f}"
        )

        # Result should still be normalized
        total = clamped.finance_capital + clamped.security_state + clamped.settler_populist
        assert abs(total - 1.0) < 0.02, f"Clamped balance sum={total:.6f}"

    def test_fascist_convergence_requires_sustained_conditions(self) -> None:
        """Fascist convergence requires consecutive ticks, not a single tick."""
        defines = _make_defines()

        # Balance that meets SS and FC thresholds
        balance = _make_balance(fc=0.15, ss=0.50, sp=0.35)
        settler_ci = 0.8  # Above fascist_settler_ci_threshold (0.6)

        # Single tick: should not converge
        assert not is_fascist_convergence(balance, settler_ci, 0, defines), (
            "Should not converge after 0 consecutive ticks"
        )
        assert not is_fascist_convergence(balance, settler_ci, 1, defines), (
            "Should not converge after 1 consecutive tick "
            f"(need {defines.convergence_confirmation_ticks})"
        )

        # After enough consecutive ticks: should converge
        assert is_fascist_convergence(
            balance,
            settler_ci,
            defines.convergence_confirmation_ticks,
            defines,
        ), f"Should converge after {defines.convergence_confirmation_ticks} consecutive ticks"

    def test_fascist_reversion_asymmetric_thresholds(self) -> None:
        """Fascist reversion thresholds are harder to reach than entry."""
        defines = _make_defines()

        # Entry thresholds: SS > 0.4, FC < 0.25
        # Reversion thresholds: SS < 0.25, settler_ci < 0.30
        # A balance that qualifies for entry should NOT qualify for reversion
        entry_balance = _make_balance(fc=0.15, ss=0.50, sp=0.35)
        entry_ci = 0.8
        assert not check_fascist_reversion(entry_balance, entry_ci, defines), (
            "Entry-qualifying balance should not qualify for reversion"
        )

        # Balance that qualifies for reversion
        exit_balance = _make_balance(fc=0.55, ss=0.20, sp=0.25)
        exit_ci = 0.2
        assert check_fascist_reversion(exit_balance, exit_ci, defines), (
            "Low SS + low CI should qualify for reversion"
        )


def _make_apparatus(**overrides: Any) -> dict[str, Any]:
    """Construct an apparatus dict with sensible defaults."""
    defaults: dict[str, Any] = {
        "id": "apparatus_detroit_pd",
        "violence_capacity": 0.0,
        "surveillance_capacity": 0.0,
        "service_delivery": 0.3,
        "counter_intel_score": 0.0,
    }
    defaults.update(overrides)
    return defaults


def _make_org(**overrides: Any) -> dict[str, Any]:
    """Construct a target organization dict."""
    defaults: dict[str, Any] = {
        "id": "org_player_1",
        "coherence": 0.9,
        "key_figure_ids": ["fig_a", "fig_b"],
    }
    defaults.update(overrides)
    return defaults


def _make_thread_dict(**overrides: Any) -> dict[str, Any]:
    """Construct an attention thread dict."""
    defaults: dict[str, Any] = {
        "thread_id": "thread_001",
        "intel_completeness": 0.0,
        "phase": "MONITORING",
    }
    defaults.update(overrides)
    return defaults


@pytest.mark.integration
class TestAdministerRepressPipeline:
    """10-tick integration: ADMINISTER builds capacity, REPRESS uses it.

    Scenario:
        - Ticks 1-2: FUND surveillance capacity (0.0 -> 0.1)
        - Tick 3: STAFF adds 2 threads
        - Tick 4: INFILTRATE target org
        - Ticks 5-7: Continued INFILTRATE (thread gains intel)
        - Tick 8: LEGISLATE EMERGENCY_POWERS
        - Tick 9: RAID target org (consciousness dialectic)
        - Tick 10: PROSECUTE captured key figure
    """

    def test_full_administer_repress_pipeline(self) -> None:
        """10-tick ADMINISTER -> REPRESS pipeline with budget tracking."""
        defines = _make_defines(
            fund_capacity_increment=0.05,
            staff_max_per_tick=2,
            thread_pool_max=10,
            infiltrate_informant_intel_rate=0.1,
            raid_org_coherence_damage=0.2,
            raid_ci_radicalization_threshold=0.5,
            raid_ci_radicalization_boost=0.1,
            raid_key_figure_capture_base=0.5,
            prosecute_org_morale_damage=0.1,
            emergency_powers_thread_multiplier=2.0,
        )

        apparatus = _make_apparatus()
        org = _make_org(coherence=0.9)
        territory = _make_territory(collective_identity=0.6)
        thread = _make_thread_dict()
        pool_size = 3
        budget = 100.0
        legitimacy = 0.7
        active_frameworks: list[dict[str, Any]] = []
        captured_figures: list[str] = []

        # --- Tick 1-2: FUND surveillance capacity ---
        fund_cost = 8.0
        max_fund_ticks: int = 2
        for _ in range(max_fund_ticks):
            apparatus = resolve_fund(apparatus, "surveillance", defines)
            budget -= fund_cost

        assert apparatus["surveillance_capacity"] == pytest.approx(0.1)
        assert budget == pytest.approx(84.0)

        # --- Tick 3: STAFF adds threads ---
        staff_cost = 5.0
        apparatus, pool_size = resolve_staff(apparatus, pool_size, 2, defines)
        budget -= staff_cost

        assert pool_size == 5
        assert budget == pytest.approx(79.0)

        # --- Ticks 4-7: INFILTRATE target org ---
        infiltrate_cost = 5.0
        max_infil_ticks: int = 4
        for tick in range(max_infil_ticks):
            thread, _, _ = resolve_infiltrate(
                org, thread, "INFORMANT", defines, rng_seed=300 + tick, current_tick=tick + 3
            )
            budget -= infiltrate_cost

        assert thread["intel_completeness"] == pytest.approx(0.4)
        assert budget == pytest.approx(59.0)

        # --- Tick 8: LEGISLATE EMERGENCY_POWERS ---
        legislate_cost = 3.0
        active_frameworks.append(
            {
                "framework_id": "law_ep_001",
                "law_type": "EMERGENCY_POWERS",
                "scope": "municipal",
                "severity": 0.8,
                "effects": {},
                "created_tick": 8,
                "creating_apparatus_id": "apparatus_detroit_pd",
            }
        )
        budget -= legislate_cost

        # Consume legal framework effects
        baseline_caps: dict[str, Any] = {
            "thread_pool_max": defines.thread_pool_max,
            "liquidate_in_core": False,
            "intel_bonus": 0.0,
        }
        effective_caps = consume_legal_framework_effects(active_frameworks, baseline_caps, defines)
        assert effective_caps["thread_pool_max"] == defines.thread_pool_max * 2
        assert effective_caps["liquidate_in_core"] is True
        assert budget == pytest.approx(56.0)

        # --- Tick 9: RAID target org ---
        raid_cost = 10.0
        org, territory, captured_figures, raid_legitimacy = resolve_raid(
            org,
            territory,
            "TARGETED",
            "SWAT",
            thread["intel_completeness"],
            org["key_figure_ids"],
            defines,
            rng_seed=42,
        )
        budget -= raid_cost
        legitimacy -= raid_legitimacy

        # Coherence damaged
        assert org["coherence"] < 0.9
        # Consciousness dialectic: CI was 0.6 (> 0.5), should radicalize
        assert territory["collective_identity"] > 0.6
        assert budget == pytest.approx(46.0)

        # --- Tick 10: PROSECUTE captured figure ---
        prosecute_cost = 7.0
        if captured_figures:
            org, prosecution_record, leg_delta = resolve_prosecute(
                org, captured_figures[0], "CONSPIRACY", defines, rng_seed=42, current_tick=10
            )
            budget -= prosecute_cost
            legitimacy += leg_delta
            assert isinstance(prosecution_record["convicted"], bool)
            assert org["coherence"] < 0.9
        else:
            # No captures — prosecute org generally
            org, prosecution_record, leg_delta = resolve_prosecute(
                org, None, "CONSPIRACY", defines, rng_seed=42, current_tick=10
            )
            budget -= prosecute_cost
            legitimacy += leg_delta

        # --- Final assertions ---
        assert budget < 100.0, "Budget should be decremented"
        assert 0.0 < legitimacy < 1.0, f"Legitimacy should be in valid range: {legitimacy}"
        assert thread["intel_completeness"] > 0.0, "Thread should have gathered intel"
        assert org["coherence"] < 0.9, "Org coherence should be degraded"
