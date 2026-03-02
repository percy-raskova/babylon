"""Unit tests for LEGISLATE consumption effects (Feature 039 Phase 10C).

Tests consume_legal_framework_effects computation of effective capabilities
from active LegalFramework records.

See Also:
    ``specs/039-state-apparatus-ai/spec.md``: FR-B09.
    :mod:`babylon.ooda.state_ai.legislate_effects`: Implementation.
"""

from __future__ import annotations

from typing import Any

import pytest

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


class TestConsumeLegalFrameworkEffects:
    """Unit tests for consume_legal_framework_effects."""

    def test_no_frameworks_returns_baseline(self) -> None:
        defines = _make_defines()
        baseline = _make_baseline()
        result = consume_legal_framework_effects([], baseline, defines)
        assert result == baseline
        assert result is not baseline  # New dict

    def test_emergency_powers_doubles_thread_pool(self) -> None:
        defines = _make_defines(emergency_powers_thread_multiplier=2.0)
        baseline = _make_baseline(thread_pool_max=8)
        frameworks = [_make_framework("EMERGENCY_POWERS")]
        result = consume_legal_framework_effects(frameworks, baseline, defines)
        assert result["thread_pool_max"] == 16

    def test_emergency_powers_enables_liquidate_in_core(self) -> None:
        defines = _make_defines(emergency_powers_liquidate_in_core=True)
        baseline = _make_baseline(liquidate_in_core=False)
        frameworks = [_make_framework("EMERGENCY_POWERS")]
        result = consume_legal_framework_effects(frameworks, baseline, defines)
        assert result["liquidate_in_core"] is True

    def test_surveillance_expansion_adds_intel_bonus(self) -> None:
        defines = _make_defines(surveillance_expansion_intel_bonus=0.1)
        baseline = _make_baseline(intel_bonus=0.0)
        frameworks = [_make_framework("SURVEILLANCE_EXPANSION")]
        result = consume_legal_framework_effects(frameworks, baseline, defines)
        assert result["intel_bonus"] == pytest.approx(0.1)

    def test_multiple_frameworks_stack(self) -> None:
        defines = _make_defines(
            emergency_powers_thread_multiplier=2.0,
            surveillance_expansion_intel_bonus=0.1,
        )
        baseline = _make_baseline(thread_pool_max=8, intel_bonus=0.0)
        frameworks = [
            _make_framework("EMERGENCY_POWERS"),
            _make_framework("SURVEILLANCE_EXPANSION", framework_id="law_002"),
        ]
        result = consume_legal_framework_effects(frameworks, baseline, defines)
        assert result["thread_pool_max"] == 16
        assert result["intel_bonus"] == pytest.approx(0.1)
        assert result["liquidate_in_core"] is True

    def test_does_not_mutate_inputs(self) -> None:
        defines = _make_defines()
        baseline = _make_baseline()
        frameworks = [_make_framework("EMERGENCY_POWERS")]
        orig_baseline = dict(baseline)
        orig_fw = [dict(f) for f in frameworks]
        _ = consume_legal_framework_effects(frameworks, baseline, defines)
        assert baseline == orig_baseline
        assert frameworks == orig_fw

    def test_unknown_law_type_passes_through(self) -> None:
        defines = _make_defines()
        baseline = _make_baseline()
        frameworks = [_make_framework("MARTIAL_LAW")]
        result = consume_legal_framework_effects(frameworks, baseline, defines)
        assert result["thread_pool_max"] == baseline["thread_pool_max"]
        assert result["liquidate_in_core"] is False

    def test_duplicate_emergency_powers_idempotent(self) -> None:
        defines = _make_defines(emergency_powers_thread_multiplier=2.0)
        baseline = _make_baseline(thread_pool_max=8)
        frameworks = [
            _make_framework("EMERGENCY_POWERS", framework_id="law_001"),
            _make_framework("EMERGENCY_POWERS", framework_id="law_002"),
        ]
        result = consume_legal_framework_effects(frameworks, baseline, defines)
        # Should only apply once: 8 * 2 = 16, NOT 8 * 2 * 2 = 32
        assert result["thread_pool_max"] == 16
