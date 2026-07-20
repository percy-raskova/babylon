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

from babylon.sentinels.liveness import checks as checks_module
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


def test_correct_but_inert_check_is_registered_in_advisory_checks() -> None:
    """WIRING: the check function itself sits in the tuple ``main()`` iterates.

    Proves ``check_producers_are_not_inert`` is not merely defined but actually
    reachable from the sensor's own dispatch path — a deleted or mistyped
    ``_ADVISORY_CHECKS`` entry must fail this test even though the check
    function and its direct-call tests above remain untouched.
    """
    wired_checks = [check for _, check in checks_module._ADVISORY_CHECKS]
    assert check_producers_are_not_inert in wired_checks


def test_correct_but_inert_finding_reaches_stderr_through_main(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """WIRING: an inert producer must surface through ``main()``, not just direct calls.

    Drives an injected inert producer through ``main() -> run_sensor ->
    _ADVISORY_CHECKS`` and asserts the ``[correct-but-inert]`` line reaches
    stderr while ``main()`` still returns 0 (advisory). This is the invocation
    proof the direct-call tests above cannot provide: they call
    ``check_producers_are_not_inert`` themselves and would stay green even if
    the sensor's own wiring to it were severed.

    Note: ``check_producers_are_not_inert``'s ``registry`` default binds the
    ``LIVENESS_ROWS`` tuple object at def-time, so monkeypatching the module
    global ``LIVENESS_ROWS`` would never reach it. The stub below instead
    calls the real check with an explicit injected registry and is installed
    as the actual ``_ADVISORY_CHECKS`` entry ``main()`` reads at call time.
    """
    phantom = LivenessRow(
        name="phantom_wiring_proof",
        producer_file="src/babylon/engine/systems/market_scissors.py",
        producer_symbol="PhantomWiringProofSystem",
        output_symbol="phantom_wiring_output",
        consumer_files=(),
        dormant_reason="injected: wiring proof",
        material_relation="injected defect proving the check runs through main()",
    )

    def stub_check() -> list[str]:
        return check_producers_are_not_inert((phantom,))

    monkeypatch.setattr(
        checks_module,
        "_ADVISORY_CHECKS",
        (("producer runs but every output is dormant", stub_check),),
    )

    exit_code = main([])
    captured = capsys.readouterr()

    assert exit_code == 0  # advisory findings never gate
    assert "[correct-but-inert]" in captured.err
    assert "PhantomWiringProofSystem" in captured.err
