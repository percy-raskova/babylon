"""Contract tests for LEGISLATE consumption (Feature 039 Phase 10C).

Behavioral contracts verifying that LEGISLATE creates framework effects
and REVOKE removes them, with EMERGENCY_POWERS enabling LIQUIDATE in core.

See Also:
    :mod:`babylon.ooda.state_ai.legislate_effects`: Implementation.
    ``specs/039-state-apparatus-ai/spec.md``: FR-B09.
"""

from __future__ import annotations

from typing import Any

from babylon.config.defines import StateApparatusAIDefines
from babylon.ooda.state_ai.legislate_effects import (
    consume_legal_framework_effects,
)


def _make_defines(**overrides: object) -> StateApparatusAIDefines:
    return StateApparatusAIDefines(**overrides)  # type: ignore[arg-type]


def _make_baseline(**overrides: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "thread_pool_max": 8,
        "liquidate_in_core": False,
        "intel_bonus": 0.0,
    }
    defaults.update(overrides)
    return defaults


def _make_framework(law_type: str, **overrides: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "framework_id": "law_001",
        "law_type": law_type,
        "scope": "municipal",
        "severity": 0.5,
        "effects": {},
        "created_tick": 0,
        "creating_apparatus_id": "apparatus_detroit_pd",
    }
    defaults.update(overrides)
    return defaults


# ===========================================================================
# BC-LEG-01: LEGISLATE -> consume -> verify capabilities changed
# ===========================================================================


class TestLegislateConsumption:
    """LEGISLATE creates frameworks that change effective capabilities."""

    def test_legislate_then_consume(self) -> None:
        """Active EMERGENCY_POWERS changes thread_pool_max and enables liquidate."""
        defines = _make_defines(emergency_powers_thread_multiplier=2.0)
        baseline = _make_baseline(thread_pool_max=8, liquidate_in_core=False)
        frameworks = [_make_framework("EMERGENCY_POWERS")]

        caps = consume_legal_framework_effects(frameworks, baseline, defines)
        assert caps["thread_pool_max"] == 16
        assert caps["liquidate_in_core"] is True


# ===========================================================================
# BC-LEG-02: REVOKE -> consume -> capabilities revert to baseline
# ===========================================================================


class TestRevokeRestoresBaseline:
    """REVOKE removes frameworks, restoring baseline capabilities."""

    def test_revoke_restores_baseline(self) -> None:
        """After REVOKE removes all frameworks, capabilities match baseline."""
        defines = _make_defines()
        baseline = _make_baseline()

        # With framework active
        active = [_make_framework("EMERGENCY_POWERS")]
        caps_active = consume_legal_framework_effects(active, baseline, defines)
        assert caps_active["thread_pool_max"] != baseline["thread_pool_max"]

        # After revoke (empty list)
        caps_revoked = consume_legal_framework_effects([], baseline, defines)
        assert caps_revoked["thread_pool_max"] == baseline["thread_pool_max"]
        assert caps_revoked["liquidate_in_core"] == baseline["liquidate_in_core"]


# ===========================================================================
# BC-LEG-03: EMERGENCY_POWERS enables LIQUIDATE only in core territories
# ===========================================================================


class TestEmergencyPowersLiquidateGate:
    """EMERGENCY_POWERS is the gate for LIQUIDATE in core territories."""

    def test_without_emergency_powers_liquidate_disabled(self) -> None:
        """Without EMERGENCY_POWERS, liquidate_in_core stays False."""
        defines = _make_defines()
        baseline = _make_baseline(liquidate_in_core=False)
        caps = consume_legal_framework_effects([], baseline, defines)
        assert caps["liquidate_in_core"] is False

    def test_with_emergency_powers_liquidate_enabled(self) -> None:
        """With EMERGENCY_POWERS, liquidate_in_core becomes True."""
        defines = _make_defines()
        baseline = _make_baseline(liquidate_in_core=False)
        frameworks = [_make_framework("EMERGENCY_POWERS")]
        caps = consume_legal_framework_effects(frameworks, baseline, defines)
        assert caps["liquidate_in_core"] is True

    def test_surveillance_expansion_does_not_enable_liquidate(self) -> None:
        """SURVEILLANCE_EXPANSION alone does not enable liquidate."""
        defines = _make_defines()
        baseline = _make_baseline(liquidate_in_core=False)
        frameworks = [_make_framework("SURVEILLANCE_EXPANSION")]
        caps = consume_legal_framework_effects(frameworks, baseline, defines)
        assert caps["liquidate_in_core"] is False
