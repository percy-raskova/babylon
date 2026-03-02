"""Contract tests for REPRESS effects (Feature 039 Phase 10D).

Behavioral contracts for INFILTRATE, RAID, PROSECUTE, LIQUIDATE actions.
Verifies escalation pipeline and consciousness dialectic.

See Also:
    :mod:`babylon.ooda.state_ai.repress_effects`: Implementation.
    ``specs/039-state-apparatus-ai/spec.md``: FR-B06.
"""

from __future__ import annotations

from typing import Any

import pytest

from babylon.config.defines import StateApparatusAIDefines
from babylon.ooda.state_ai.repress_effects import (
    resolve_infiltrate,
    resolve_liquidate,
    resolve_prosecute,
    resolve_raid,
)


def _make_defines(**overrides: object) -> StateApparatusAIDefines:
    return StateApparatusAIDefines(**overrides)  # type: ignore[arg-type]


def _make_org(**overrides: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "id": "org_player_1",
        "coherence": 0.8,
        "key_figure_ids": ["fig_a", "fig_b"],
    }
    defaults.update(overrides)
    return defaults


def _make_thread(**overrides: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "thread_id": "thread_001",
        "intel_completeness": 0.0,
        "phase": "MONITORING",
    }
    defaults.update(overrides)
    return defaults


def _make_territory(**overrides: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "collective_identity": 0.5,
        "community_infrastructure_quality": 0.5,
        "territory_type": "PERIPHERY",
    }
    defaults.update(overrides)
    return defaults


# ===========================================================================
# BC-REP-01: INFILTRATE intel_completeness grows monotonically
# ===========================================================================


class TestInfiltrateMono:
    """INFILTRATE grows intel_completeness monotonically."""

    def test_infiltrate_5_ticks_monotonic(self) -> None:
        """5 ticks of INFILTRATE monotonically increase intel_completeness."""
        defines = _make_defines(infiltrate_informant_intel_rate=0.05)
        thread = _make_thread(intel_completeness=0.0)
        previous: float = 0.0

        max_ticks: int = 5
        for tick in range(max_ticks):
            thread, _, _ = resolve_infiltrate(
                _make_org(), thread, "INFORMANT", defines, rng_seed=100 + tick, current_tick=tick
            )
            current: float = thread["intel_completeness"]
            assert current >= previous, f"Intel should grow: {previous:.4f} -> {current:.4f}"
            previous = current

        assert thread["intel_completeness"] == pytest.approx(0.25)


# ===========================================================================
# BC-REP-02: Thread phase gates RAID availability
# ===========================================================================


class TestThreadPhaseGatesRaid:
    """Only threads at sufficient intel can meaningfully RAID."""

    def test_high_intel_effective_raid(self) -> None:
        """Thread with high intel produces effective RAID (captures likely)."""
        defines = _make_defines(
            raid_key_figure_capture_base=0.3,
            raid_force_multiplier_swat=1.5,
        )
        org = _make_org()
        # High intel = effective raid
        result_org, _, captured, _ = resolve_raid(
            org,
            _make_territory(),
            "TARGETED",
            "SWAT",
            0.8,
            ["fig_a", "fig_b"],
            defines,
            rng_seed=42,
        )
        # With P(capture) = 0.3 * 1.5 * 0.8 = 0.36 per figure, at least coherence drops
        assert result_org["coherence"] < org["coherence"]

    def test_zero_intel_ineffective_raid(self) -> None:
        """Thread with zero intel captures nobody."""
        defines = _make_defines(raid_key_figure_capture_base=0.3)
        _, _, captured, _ = resolve_raid(
            _make_org(),
            _make_territory(),
            "TARGETED",
            "POLICE",
            0.0,
            ["fig_a", "fig_b"],
            defines,
            rng_seed=42,
        )
        assert captured == []


# ===========================================================================
# BC-REP-03: RAID high-CI territory increases CI (consciousness dialectic)
# ===========================================================================


class TestRaidConsciousnessDialectic:
    """RAID against high-CI territory radicalizes (COINTELPRO double bind)."""

    def test_high_ci_radicalized_by_raid(self) -> None:
        """Raiding a territory with CI > 0.5 increases CI."""
        defines = _make_defines(
            raid_ci_radicalization_threshold=0.5,
            raid_ci_radicalization_boost=0.1,
        )
        territory = _make_territory(collective_identity=0.7)
        _, result_terr, _, _ = resolve_raid(
            _make_org(), territory, "TARGETED", "POLICE", 0.5, [], defines, rng_seed=42
        )
        assert result_terr["collective_identity"] > 0.7

    def test_low_ci_suppressed_by_raid(self) -> None:
        """Raiding a territory with CI < 0.5 decreases CI."""
        defines = _make_defines(
            raid_ci_radicalization_threshold=0.5,
            raid_ci_suppression_rate=0.15,
        )
        territory = _make_territory(collective_identity=0.3)
        _, result_terr, _, _ = resolve_raid(
            _make_org(), territory, "TARGETED", "POLICE", 0.5, [], defines, rng_seed=42
        )
        assert result_terr["collective_identity"] < 0.3


# ===========================================================================
# BC-REP-04: PROSECUTE conviction rate bounded [0, 1]
# ===========================================================================


class TestProsecuteConvictionBounded:
    """PROSECUTE conviction outcomes are binary (convicted or not)."""

    def test_conviction_is_boolean(self) -> None:
        """Conviction result is always a boolean."""
        defines = _make_defines()
        max_seeds: int = 20
        for seed in range(max_seeds):
            _, record, legitimacy = resolve_prosecute(
                _make_org(), "fig_a", "CONSPIRACY", defines, rng_seed=seed
            )
            assert isinstance(record["convicted"], bool)
            # Legitimacy is always +/- the boost amount
            assert abs(legitimacy) == pytest.approx(defines.prosecute_legitimacy_boost_success)


# ===========================================================================
# BC-REP-05: LIQUIDATE requires EMERGENCY_POWERS for core territory
# ===========================================================================


class TestLiquidateEmergencyGate:
    """LIQUIDATE in core requires EMERGENCY_POWERS."""

    def test_core_without_powers_blocked(self) -> None:
        with pytest.raises(ValueError, match="EMERGENCY_POWERS"):
            resolve_liquidate(
                _make_org(),
                "fig_a",
                "ASSASSINATION",
                0.5,
                "CORE",
                liquidate_available_in_core=False,
                is_singleton=False,
                defines=_make_defines(),
            )

    def test_core_with_powers_allowed(self) -> None:
        result_org, cost, _ = resolve_liquidate(
            _make_org(),
            "fig_a",
            "ASSASSINATION",
            0.5,
            "CORE",
            liquidate_available_in_core=True,
            is_singleton=False,
            defines=_make_defines(),
        )
        assert result_org["coherence"] < 0.8
        assert cost > 0.0

    def test_periphery_always_allowed(self) -> None:
        result_org, cost, _ = resolve_liquidate(
            _make_org(),
            "fig_a",
            "ASSASSINATION",
            0.5,
            "PERIPHERY",
            liquidate_available_in_core=False,
            is_singleton=False,
            defines=_make_defines(),
        )
        assert result_org["coherence"] < 0.8
        assert cost > 0.0


# ===========================================================================
# BC-REP-06: INFILTRATE -> RAID -> PROSECUTE escalation pipeline
# ===========================================================================


class TestEscalationPipeline:
    """INFILTRATE -> RAID -> PROSECUTE: each step depends on prior intelligence."""

    def test_full_escalation_pipeline(self) -> None:
        """Intel gathering → raid → prosecution with captured figures."""
        defines = _make_defines(
            infiltrate_informant_intel_rate=0.1,
            raid_org_coherence_damage=0.2,
            raid_key_figure_capture_base=0.5,
            prosecute_org_morale_damage=0.1,
            prosecute_key_figure_removal_chance=0.8,
        )
        org = _make_org(coherence=1.0)
        thread = _make_thread(intel_completeness=0.0)

        # Phase 1: INFILTRATE (5 ticks to build intel)
        max_infil_ticks: int = 5
        for tick in range(max_infil_ticks):
            thread, _, _ = resolve_infiltrate(
                org, thread, "INFORMANT", defines, rng_seed=200 + tick, current_tick=tick
            )

        intel = thread["intel_completeness"]
        assert intel == pytest.approx(0.5)

        # Phase 2: RAID using gathered intel
        result_org, territory, captured, _ = resolve_raid(
            org,
            _make_territory(collective_identity=0.3),
            "TARGETED",
            "SWAT",
            intel,
            ["fig_a", "fig_b"],
            defines,
            rng_seed=42,
        )
        assert result_org["coherence"] < org["coherence"]

        # Phase 3: PROSECUTE captured figure (if any)
        if captured:
            result_org, record, _ = resolve_prosecute(
                result_org, captured[0], "CONSPIRACY", defines, rng_seed=42
            )
            assert result_org["coherence"] < org["coherence"]
            assert isinstance(record["convicted"], bool)
