"""Tests for the computed-but-never-consumed sensor.

Two tiers, per the sentinel contract:

- **Invariant** — the sensor is clean on the real :data:`LIVENESS_ROWS`: every
  non-dormant output is actually mentioned by at least one declared consumer.
- **Efficacy (MUTATION)** — the sensor REDS when the defect it exists to catch
  is injected: a declared consumer that does not in fact read the output, i.e.
  an output computed every tick and consumed by nobody.
"""

from __future__ import annotations

import pytest

from babylon.sentinels.base import SentinelCheckError
from babylon.sentinels.liveness.checks import check_outputs_have_readers
from babylon.sentinels.liveness.registry import LivenessRow

pytestmark = pytest.mark.unit


def test_real_rows_are_consumed() -> None:
    """INVARIANT: every declared non-dormant output has a real reader."""
    assert check_outputs_have_readers() == []


def test_efficacy_reds_when_the_declared_consumer_does_not_read_the_output() -> None:
    """MUTATION: inject an output no consumer mentions — the sensor must red.

    ``web/game/map_contract.py`` is a real, parseable file that contains no
    mention of ``phantom_never_read_output``; the row therefore claims a reader
    that does not exist, which is precisely computed-but-never-consumed.
    """
    injected = LivenessRow(
        name="phantom_output",
        producer_file="src/babylon/engine/systems/market_scissors.py",
        producer_symbol="MarketScissorsSystem",
        output_symbol="phantom_never_read_output",
        consumer_files=("web/game/map_contract.py",),
        material_relation="injected defect for the efficacy proof",
    )
    findings = check_outputs_have_readers((injected,))
    assert len(findings) == 1
    assert findings[0].startswith("[computed-but-never-consumed]")
    assert "phantom_never_read_output" in findings[0]
    assert "web/game/map_contract.py" in findings[0]
    assert "REMEDY:" in findings[0]


def test_dormant_rows_are_not_reported() -> None:
    """A declared-dormant output is silent — dormancy WITH a reason is allowed."""
    dormant = LivenessRow(
        name="declared_dormant",
        producer_file="src/babylon/engine/systems/contradiction.py",
        producer_symbol="ContradictionSystem",
        output_symbol="phantom_never_read_output",
        consumer_files=(),
        dormant_reason="awaiting the Phase 2 consumer; recorded, not hidden",
        material_relation="injected dormant row for the exemption proof",
    )
    assert check_outputs_have_readers((dormant,)) == []


def test_missing_consumer_file_is_infrastructure_failure() -> None:
    """A consumer path that does not exist is exit-2 loud, not a quiet miss."""
    broken = LivenessRow(
        name="bad_path",
        producer_file="src/babylon/engine/systems/market_scissors.py",
        producer_symbol="MarketScissorsSystem",
        output_symbol="price_divergence",
        consumer_files=("web/game/this_file_does_not_exist.py",),
        material_relation="injected infra failure for the loudness proof",
    )
    with pytest.raises(SentinelCheckError, match="cannot read"):
        check_outputs_have_readers((broken,))
