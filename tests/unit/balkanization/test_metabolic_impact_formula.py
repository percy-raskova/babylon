"""Spec-070 calculate_metabolic_impact unit tests (T012 / FR-004).

Verifies the canonical mapping ExtractionPolicy → metabolic_impact:

- INTENSIFY → -0.02
- CONTINUE  → -0.005
- CEASE     → +0.01

Plus the BalkanizationDefines override path.
"""

from __future__ import annotations

import pytest

from babylon.config.defines.balkanization import BalkanizationDefines
from babylon.formulas.balkanization import calculate_metabolic_impact
from babylon.models.enums import ExtractionPolicy

pytestmark = pytest.mark.math


def test_intensify_returns_minus_002() -> None:
    assert calculate_metabolic_impact(ExtractionPolicy.INTENSIFY) == pytest.approx(-0.02)


def test_continue_returns_minus_0005() -> None:
    assert calculate_metabolic_impact(ExtractionPolicy.CONTINUE) == pytest.approx(-0.005)


def test_cease_returns_plus_001() -> None:
    assert calculate_metabolic_impact(ExtractionPolicy.CEASE) == pytest.approx(0.01)


def test_defines_override_path() -> None:
    """Override defaults via BalkanizationDefines (no magic numbers — III.1)."""

    overrides = BalkanizationDefines(
        metabolic_impact_intensify=-0.05,
        metabolic_impact_continue=-0.01,
        metabolic_impact_cease=0.02,
    )
    assert calculate_metabolic_impact(
        ExtractionPolicy.INTENSIFY, defines=overrides
    ) == pytest.approx(-0.05)
    assert calculate_metabolic_impact(
        ExtractionPolicy.CONTINUE, defines=overrides
    ) == pytest.approx(-0.01)
    assert calculate_metabolic_impact(ExtractionPolicy.CEASE, defines=overrides) == pytest.approx(
        0.02
    )


def test_unknown_policy_raises() -> None:
    """Exhaustive enum coverage — non-enum input fails loud."""

    with pytest.raises((KeyError, ValueError, TypeError)):
        calculate_metabolic_impact("not_a_policy")  # type: ignore[arg-type]
