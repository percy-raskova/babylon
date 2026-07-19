"""Tests for the fog-containment sentinel: no political field escapes a mask.

The dynamic Hypothesis harness lives in ``tools/fog_containment_probe.py``
(it must import ``game.fog.filter``/``game.fog.ledger``, ``web.game.*``
modules — see that module's and ``babylon.sentinels.fog``'s own docstrings
for why). These tests import the probe module directly.

- **Liveness** — the real, shipped ``apply_fog`` against 200
  Hypothesis-generated cases: must be clean (the founding grounding: the
  fog gate already masks correctly across the field/value space explored).
- **Efficacy proof** — a deliberately-broken stand-in ``apply_fog`` (a
  truthy check instead of an ``is not None`` check — the classic
  falsy-value footgun: ``0``/``0.0``/``False``/``""`` would wrongly be
  treated as "already masked") proves the property genuinely CAN catch a
  real escape, not merely rubber-stamp anything that runs to completion.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.unit

_TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools"
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

import fog_containment_probe as probe  # type: ignore[import-not-found]  # noqa: E402


def test_live_property_is_clean_against_the_real_apply_fog() -> None:
    """The shipped apply_fog masks every generated case cleanly."""
    assert probe.check_no_political_field_escapes() == []


def _buggy_apply_fog(
    payload: dict[str, Any],
    node_type: str,
    node_id: str,
    reach: frozenset[str],
    ledger: Any,
    tick: int,
    *,
    staleness_ticks: int,
    unknown_ticks: int,
    political_fields: tuple[str, ...] = (),
) -> dict[str, Any]:
    """A deliberately-broken masker: truthy check instead of ``is not None``.

    Fails to mask any FALSY-but-present value (``0``, ``0.0``, ``False``,
    ``""``) — the classic footgun a real regression could reintroduce.
    """
    _ = node_type, ledger, tick, staleness_ticks, unknown_ticks
    result = dict(payload)
    if node_id in reach:
        result["vision_masked"] = []
        result["vision_approx"] = []
        return result
    masked: list[str] = []
    for field in political_fields:
        if field in result and result[field]:  # BUG: should be `is not None`
            result[field] = None
            masked.append(field)
    result["vision_masked"] = masked
    result["vision_approx"] = []
    return result


def test_property_catches_a_genuinely_broken_masker(monkeypatch: pytest.MonkeyPatch) -> None:
    """Swapping in a masker with the falsy-check bug must make the property
    find a violation (proving Hypothesis's generation actually exercises
    the falsy-value shapes, not just the "happy path" truthy ones)."""
    monkeypatch.setattr("game.fog.filter.apply_fog", _buggy_apply_fog)
    violations = probe.check_no_political_field_escapes()
    assert len(violations) == 1
    assert "escaped apply_fog" in violations[0]


def test_property_stays_clean_when_swapped_masker_is_correct(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sanity: swapping in a CORRECT stand-in (is not None check) stays clean
    -- proves the harness itself isn't just always red/always green."""

    def _correct_apply_fog(
        payload: dict[str, Any],
        node_type: str,
        node_id: str,
        reach: frozenset[str],
        ledger: Any,
        tick: int,
        *,
        staleness_ticks: int,
        unknown_ticks: int,
        political_fields: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        _ = node_type, ledger, tick, staleness_ticks, unknown_ticks
        result = dict(payload)
        if node_id in reach:
            result["vision_masked"] = []
            result["vision_approx"] = []
            return result
        masked: list[str] = []
        for field in political_fields:
            if field in result and result[field] is not None:
                result[field] = None
                masked.append(field)
        result["vision_masked"] = masked
        result["vision_approx"] = []
        return result

    monkeypatch.setattr("game.fog.filter.apply_fog", _correct_apply_fog)
    assert probe.check_no_political_field_escapes() == []
