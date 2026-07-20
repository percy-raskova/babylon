"""E5a: a defines_hash mismatch FAILS the gate and names the ceremony."""

from __future__ import annotations

import pytest
from tools.regression_test import BaselineData, compare_baselines

pytestmark = pytest.mark.unit


def _baseline(defines_hash: str) -> BaselineData:
    return BaselineData(
        scenario="s",
        description="d",
        generated_at="2026-01-01T00:00:00+00:00",
        defines_hash=defines_hash,
        max_ticks=1,
        checkpoints=[],
        final_outcome="SURVIVED",
        ticks_survived=1,
    )


def test_hash_mismatch_fails_and_names_the_ceremony() -> None:
    passed, diffs = compare_baselines(_baseline("aaaa"), _baseline("bbbb"))
    assert passed is False
    joined = "\n".join(diffs)
    assert "defines_hash" in joined
    assert "qa:regression-generate-dense" in joined


def test_hash_match_passes() -> None:
    passed, _ = compare_baselines(_baseline("aaaa"), _baseline("aaaa"))
    assert passed is True
