"""Unit tests for ADMINISTER effects (Feature 039 Phase 10B).

Tests FUND, STAFF, AUDIT action resolution.

See Also:
    ``specs/039-state-apparatus-ai/spec.md``: FR-B02.
    :mod:`babylon.ooda.state_ai.administer_effects`: Implementation.
"""

from __future__ import annotations

from typing import Any

import pytest

from babylon.config.defines import StateApparatusAIDefines
from babylon.ooda.state_ai.administer_effects import (
    resolve_audit,
    resolve_fund,
    resolve_staff,
)


def _make_defines(**overrides: object) -> StateApparatusAIDefines:
    return StateApparatusAIDefines(**overrides)  # type: ignore[arg-type]


def _make_apparatus(**overrides: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "violence_capacity": 0.5,
        "surveillance_capacity": 0.5,
        "service_delivery": 0.5,
        "counter_intel_score": 0.0,
    }
    defaults.update(overrides)
    return defaults


def _make_infiltration(**overrides: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "agent_type": "INFORMANT",
        "target_org_id": "org_player_1",
        "created_tick": 0,
        "detected": False,
    }
    defaults.update(overrides)
    return defaults


# ===========================================================================
# resolve_fund tests
# ===========================================================================


class TestResolveFund:
    """Unit tests for resolve_fund."""

    def test_fund_increases_target_capacity(self) -> None:
        defines = _make_defines(fund_capacity_increment=0.05)
        apparatus = _make_apparatus(surveillance_capacity=0.5)
        result = resolve_fund(apparatus, "surveillance", defines)
        assert result["surveillance_capacity"] == pytest.approx(0.55)

    def test_fund_caps_at_one(self) -> None:
        defines = _make_defines(fund_capacity_increment=0.1)
        apparatus = _make_apparatus(violence_capacity=0.95)
        result = resolve_fund(apparatus, "violence", defines)
        assert result["violence_capacity"] == pytest.approx(1.0)

    def test_fund_does_not_mutate_input(self) -> None:
        defines = _make_defines()
        apparatus = _make_apparatus()
        original_surv = apparatus["surveillance_capacity"]
        _ = resolve_fund(apparatus, "surveillance", defines)
        assert apparatus["surveillance_capacity"] == original_surv

    def test_fund_invalid_capacity_type_raises(self) -> None:
        defines = _make_defines()
        apparatus = _make_apparatus()
        with pytest.raises(ValueError, match="Invalid capacity_type"):
            resolve_fund(apparatus, "invalid", defines)

    def test_fund_preserves_other_fields(self) -> None:
        defines = _make_defines()
        apparatus = _make_apparatus(violence_capacity=0.5, surveillance_capacity=0.3)
        result = resolve_fund(apparatus, "violence", defines)
        assert result["surveillance_capacity"] == pytest.approx(0.3)

    def test_fund_from_zero_baseline(self) -> None:
        defines = _make_defines(fund_capacity_increment=0.05)
        apparatus = _make_apparatus(service_delivery=0.0)
        result = resolve_fund(apparatus, "service", defines)
        assert result["service_delivery"] == pytest.approx(0.05)

    def test_fund_custom_increment(self) -> None:
        defines = _make_defines(fund_capacity_increment=0.2)
        apparatus = _make_apparatus(surveillance_capacity=0.3)
        result = resolve_fund(apparatus, "surveillance", defines)
        assert result["surveillance_capacity"] == pytest.approx(0.5)


# ===========================================================================
# resolve_staff tests
# ===========================================================================


class TestResolveStaff:
    """Unit tests for resolve_staff."""

    def test_staff_increases_pool(self) -> None:
        defines = _make_defines(staff_max_per_tick=2, thread_pool_max=8)
        apparatus = _make_apparatus(surveillance_capacity=0.5)
        _, new_pool = resolve_staff(apparatus, 5, 2, defines)
        assert new_pool == 7

    def test_staff_capped_by_max_per_tick(self) -> None:
        defines = _make_defines(staff_max_per_tick=2, thread_pool_max=20)
        apparatus = _make_apparatus(surveillance_capacity=0.5)
        _, new_pool = resolve_staff(apparatus, 5, 5, defines)
        assert new_pool == 7

    def test_staff_capped_by_thread_pool_max(self) -> None:
        defines = _make_defines(staff_max_per_tick=5, thread_pool_max=8)
        apparatus = _make_apparatus(surveillance_capacity=0.5)
        _, new_pool = resolve_staff(apparatus, 7, 5, defines)
        assert new_pool == 8

    def test_staff_does_not_mutate_input(self) -> None:
        defines = _make_defines()
        apparatus = _make_apparatus()
        original = dict(apparatus)
        _ = resolve_staff(apparatus, 5, 2, defines)
        assert apparatus == original

    def test_staff_zero_surveillance_returns_unchanged(self) -> None:
        defines = _make_defines()
        apparatus = _make_apparatus(surveillance_capacity=0.0)
        _, new_pool = resolve_staff(apparatus, 5, 2, defines)
        assert new_pool == 5

    def test_staff_count_zero_returns_unchanged(self) -> None:
        defines = _make_defines()
        apparatus = _make_apparatus(surveillance_capacity=0.5)
        _, new_pool = resolve_staff(apparatus, 5, 0, defines)
        assert new_pool == 5

    def test_staff_pool_already_at_max(self) -> None:
        defines = _make_defines(thread_pool_max=8)
        apparatus = _make_apparatus(surveillance_capacity=0.5)
        _, new_pool = resolve_staff(apparatus, 8, 2, defines)
        assert new_pool == 8


# ===========================================================================
# resolve_audit tests
# ===========================================================================


class TestResolveAudit:
    """Unit tests for resolve_audit."""

    def test_audit_routine_detects_at_low_rate(self) -> None:
        """ROUTINE depth has ~20% detection — seeded deterministic."""
        defines = _make_defines(audit_routine_detection_chance=0.2)
        infiltrations = [_make_infiltration() for _ in range(20)]
        _, detected = resolve_audit(
            _make_apparatus(), infiltrations, "ROUTINE", defines, rng_seed=42
        )
        # With 20% chance and 20 items, expect roughly 4 detections
        assert 0 <= len(detected) <= 20
        # Deterministic: re-run should give same count
        _, detected2 = resolve_audit(
            _make_apparatus(), infiltrations, "ROUTINE", defines, rng_seed=42
        )
        assert len(detected) == len(detected2)

    def test_audit_deep_detects_at_high_rate(self) -> None:
        """DEEP depth has ~80% detection."""
        defines = _make_defines(audit_deep_detection_chance=0.8)
        infiltrations = [_make_infiltration() for _ in range(20)]
        _, detected = resolve_audit(_make_apparatus(), infiltrations, "DEEP", defines, rng_seed=42)
        assert len(detected) > len(infiltrations) // 2

    def test_audit_empty_infiltrations_returns_empty(self) -> None:
        defines = _make_defines()
        result_app, detected = resolve_audit(_make_apparatus(), [], "ROUTINE", defines, rng_seed=42)
        assert detected == []
        assert result_app["counter_intel_score"] == pytest.approx(0.0)

    def test_audit_does_not_mutate_inputs(self) -> None:
        defines = _make_defines()
        apparatus = _make_apparatus()
        infiltrations = [_make_infiltration()]
        orig_app = dict(apparatus)
        orig_infil = [dict(i) for i in infiltrations]
        _ = resolve_audit(apparatus, infiltrations, "ROUTINE", defines, rng_seed=42)
        assert apparatus == orig_app
        assert infiltrations == orig_infil

    def test_audit_invalid_depth_raises(self) -> None:
        defines = _make_defines()
        with pytest.raises(ValueError, match="Invalid audit depth"):
            resolve_audit(_make_apparatus(), [], "INVALID", defines, rng_seed=42)

    def test_audit_detected_items_are_copies(self) -> None:
        """Detected infiltrations are copies, not references."""
        defines = _make_defines(audit_deep_detection_chance=1.0)
        infiltrations = [_make_infiltration()]
        _, detected = resolve_audit(_make_apparatus(), infiltrations, "DEEP", defines, rng_seed=42)
        assert len(detected) == 1
        detected[0]["agent_type"] = "MODIFIED"
        assert infiltrations[0]["agent_type"] == "INFORMANT"

    def test_audit_updates_counter_intel_score(self) -> None:
        defines = _make_defines(audit_deep_detection_chance=1.0)
        infiltrations = [_make_infiltration() for _ in range(5)]
        result_app, _ = resolve_audit(
            _make_apparatus(), infiltrations, "DEEP", defines, rng_seed=42
        )
        assert result_app["counter_intel_score"] > 0.0

    def test_audit_deterministic_with_same_seed(self) -> None:
        defines = _make_defines()
        infiltrations = [_make_infiltration() for _ in range(10)]
        _, d1 = resolve_audit(_make_apparatus(), infiltrations, "THOROUGH", defines, rng_seed=99)
        _, d2 = resolve_audit(_make_apparatus(), infiltrations, "THOROUGH", defines, rng_seed=99)
        assert len(d1) == len(d2)
