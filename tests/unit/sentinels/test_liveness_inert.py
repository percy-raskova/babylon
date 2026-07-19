"""Tests for the correct-but-inert sensor and the liveness CLI entry point.

Correct-but-inert is the *producer-level* class: not one dead output, but a
producer whose EVERY declared output is dormant — it runs, it validates, and
the world is unchanged by it. That is Volume III's exact failure mode.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from babylon.sentinels.liveness.checks import check_producers_are_not_inert, main
from babylon.sentinels.liveness.registry import LivenessRow

pytestmark = pytest.mark.unit

_TOOL_PATH = Path(__file__).resolve().parents[3] / "tools" / "sentinel_check.py"


def test_real_producers_are_not_inert() -> None:
    """INVARIANT: no declared producer has an all-dormant output set."""
    assert check_producers_are_not_inert() == []


def test_efficacy_reds_on_a_wholly_dormant_producer() -> None:
    """MUTATION: a producer whose every output is dormant must be reported."""
    inert_a = LivenessRow(
        name="inert_one",
        producer_file="src/babylon/engine/systems/market_scissors.py",
        producer_symbol="PhantomInertSystem",
        output_symbol="phantom_a",
        consumer_files=(),
        dormant_reason="injected: awaiting a consumer",
        material_relation="injected defect for the efficacy proof",
    )
    inert_b = LivenessRow(
        name="inert_two",
        producer_file="src/babylon/engine/systems/market_scissors.py",
        producer_symbol="PhantomInertSystem",
        output_symbol="phantom_b",
        consumer_files=(),
        dormant_reason="injected: awaiting a consumer",
        material_relation="injected defect for the efficacy proof",
    )
    findings = check_producers_are_not_inert((inert_a, inert_b))
    assert len(findings) == 1
    assert findings[0].startswith("[correct-but-inert]")
    assert "PhantomInertSystem" in findings[0]
    assert "phantom_a" in findings[0] and "phantom_b" in findings[0]
    assert "REMEDY:" in findings[0]


def test_a_producer_with_one_live_output_is_not_inert() -> None:
    """One live output is enough — inertness is about the producer, not the row."""
    dormant = LivenessRow(
        name="mixed_dormant",
        producer_file="src/babylon/engine/systems/market_scissors.py",
        producer_symbol="MixedSystem",
        output_symbol="phantom_a",
        consumer_files=(),
        dormant_reason="injected: awaiting a consumer",
        material_relation="injected row",
    )
    live = LivenessRow(
        name="mixed_live",
        producer_file="src/babylon/engine/systems/market_scissors.py",
        producer_symbol="MixedSystem",
        output_symbol="price_divergence",
        consumer_files=("web/game/engine_bridge.py",),
        material_relation="injected row",
    )
    assert check_producers_are_not_inert((dormant, live)) == []


def test_main_exits_zero_because_liveness_is_advisory() -> None:
    """The sensor is advisory: findings print, the process never gates."""
    assert main([]) == 0


def test_cli_dispatches_the_liveness_sensor() -> None:
    """``sentinel_check.py liveness`` routes to this sensor and exits cleanly."""
    result = subprocess.run(
        [sys.executable, str(_TOOL_PATH), "liveness"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "Liveness" in result.stdout
