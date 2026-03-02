"""Contract tests for ADMINISTER effects (Feature 039 Phase 10B).

Behavioral contracts for FUND, STAFF, and AUDIT actions. Verifies that
ADMINISTER builds state capacity monotonically and that the pipeline
FUND -> STAFF -> AUDIT operates correctly in sequence.

See Also:
    :mod:`babylon.ooda.state_ai.administer_effects`: Implementation.
    ``specs/039-state-apparatus-ai/spec.md``: FR-B02.
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
        "violence_capacity": 0.0,
        "surveillance_capacity": 0.0,
        "service_delivery": 0.0,
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
# BC-ADM-01: FUND Increases Capacity Monotonically
# ===========================================================================


class TestFundMonotonic:
    """FUND increases capacity monotonically over repeated applications."""

    def test_fund_10_iterations_monotonic(self) -> None:
        """10 FUND applications monotonically increase surveillance_capacity."""
        defines = _make_defines(fund_capacity_increment=0.05)
        apparatus = _make_apparatus(surveillance_capacity=0.0)

        previous: float = 0.0
        max_iters: int = 10
        for _ in range(max_iters):
            apparatus = resolve_fund(apparatus, "surveillance", defines)
            current: float = apparatus["surveillance_capacity"]
            assert current >= previous, f"FUND should be monotonic: {previous:.4f} -> {current:.4f}"
            previous = current

        assert apparatus["surveillance_capacity"] == pytest.approx(0.5)


# ===========================================================================
# BC-ADM-02: STAFF Grows Pool Only When surveillance_capacity > 0
# ===========================================================================


class TestStaffRequiresSurveillance:
    """STAFF grows pool only when surveillance_capacity > 0."""

    def test_staff_blocked_without_surveillance(self) -> None:
        """Zero surveillance_capacity prevents all STAFF growth."""
        defines = _make_defines()
        apparatus = _make_apparatus(surveillance_capacity=0.0)
        _, pool = resolve_staff(apparatus, 3, 2, defines)
        assert pool == 3

    def test_staff_works_with_surveillance(self) -> None:
        """Positive surveillance_capacity allows STAFF growth."""
        defines = _make_defines(staff_max_per_tick=2, thread_pool_max=10)
        apparatus = _make_apparatus(surveillance_capacity=0.1)
        _, pool = resolve_staff(apparatus, 3, 2, defines)
        assert pool == 5


# ===========================================================================
# BC-ADM-03: AUDIT Detection Increases With Depth
# ===========================================================================


class TestAuditDepthProgression:
    """AUDIT detection probability increases with depth level."""

    def test_deep_detects_more_than_routine(self) -> None:
        """DEEP audit detects more than ROUTINE over same infiltrations."""
        defines = _make_defines()
        infiltrations = [_make_infiltration() for _ in range(50)]

        _, routine_detected = resolve_audit(
            _make_apparatus(), infiltrations, "ROUTINE", defines, rng_seed=42
        )
        _, thorough_detected = resolve_audit(
            _make_apparatus(), infiltrations, "THOROUGH", defines, rng_seed=42
        )
        _, deep_detected = resolve_audit(
            _make_apparatus(), infiltrations, "DEEP", defines, rng_seed=42
        )

        assert len(routine_detected) <= len(thorough_detected) <= len(deep_detected), (
            f"Detection should increase with depth: "
            f"ROUTINE={len(routine_detected)}, "
            f"THOROUGH={len(thorough_detected)}, "
            f"DEEP={len(deep_detected)}"
        )


# ===========================================================================
# BC-ADM-04: FUND -> STAFF -> AUDIT Pipeline
# ===========================================================================


class TestAdministerPipeline:
    """Full ADMINISTER pipeline: fund surveillance, staff threads, audit."""

    def test_fund_then_staff_then_audit(self) -> None:
        """Pipeline: FUND surveillance -> STAFF threads -> AUDIT detects."""
        defines = _make_defines(
            fund_capacity_increment=0.1,
            staff_max_per_tick=2,
            thread_pool_max=10,
            audit_deep_detection_chance=0.8,
        )
        apparatus = _make_apparatus(surveillance_capacity=0.0)
        pool_size = 3

        # Step 1: FUND surveillance capacity
        apparatus = resolve_fund(apparatus, "surveillance", defines)
        assert apparatus["surveillance_capacity"] > 0.0

        # Step 2: STAFF (now possible with surveillance > 0)
        apparatus, pool_size = resolve_staff(apparatus, pool_size, 2, defines)
        assert pool_size == 5

        # Step 3: AUDIT detected enemy infiltrations
        infiltrations = [_make_infiltration() for _ in range(5)]
        apparatus, detected = resolve_audit(apparatus, infiltrations, "DEEP", defines, rng_seed=42)
        assert len(detected) > 0
        assert apparatus["counter_intel_score"] > 0.0
