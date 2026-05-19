"""Spec-070 stance-mapping unit tests (T035, FR-003 + FR-007).

Exhaustive table verification of both stance-derivation functions:

- :func:`derive_extraction_policy_from_stance` per FR-003 / data-model.md §3.2
- :func:`derive_default_multipliers_from_stance` per FR-007 / data-model.md §3.1
"""

from __future__ import annotations

import pytest

from babylon.config.defines.balkanization import BalkanizationDefines
from babylon.formulas.balkanization import (
    derive_default_multipliers_from_stance,
    derive_extraction_policy_from_stance,
)
from babylon.models.enums import ColonialStance, ExtractionPolicy

pytestmark = pytest.mark.math


@pytest.mark.parametrize(
    ("stance", "expected_policy"),
    [
        (ColonialStance.UPHOLD, ExtractionPolicy.INTENSIFY),
        (ColonialStance.IGNORE, ExtractionPolicy.CONTINUE),
        (ColonialStance.ABOLISH, ExtractionPolicy.CEASE),
    ],
)
def test_derive_extraction_policy_table(
    stance: ColonialStance, expected_policy: ExtractionPolicy
) -> None:
    assert derive_extraction_policy_from_stance(stance) is expected_policy


def test_derive_extraction_policy_is_deterministic() -> None:
    assert derive_extraction_policy_from_stance(
        ColonialStance.UPHOLD
    ) is derive_extraction_policy_from_stance(ColonialStance.UPHOLD)


@pytest.mark.parametrize(
    ("stance", "expected"),
    [
        (ColonialStance.UPHOLD, (1.5, 2.0, 0.0, -0.5)),
        (ColonialStance.IGNORE, (0.8, 0.5, 0.7, 0.0)),
        (ColonialStance.ABOLISH, (0.0, 0.3, 0.5, 0.8)),
    ],
)
def test_derive_default_multipliers_table(
    stance: ColonialStance, expected: tuple[float, float, float, float]
) -> None:
    got = derive_default_multipliers_from_stance(stance)
    assert got == pytest.approx(expected)


def test_derive_default_multipliers_respects_defines_override() -> None:
    overrides = BalkanizationDefines(
        stance_extraction_modifier={"uphold": 9.9, "ignore": 0.8, "abolish": 0.0},
        stance_violence_modifier={"uphold": 8.8, "ignore": 0.5, "abolish": 0.3},
        stance_class_reduction={"uphold": 0.7, "ignore": 0.7, "abolish": 0.5},
        stance_metabolic_reduction={"uphold": 0.6, "ignore": 0.0, "abolish": 0.8},
    )
    got = derive_default_multipliers_from_stance(ColonialStance.UPHOLD, defines=overrides)
    assert got == pytest.approx((9.9, 8.8, 0.7, 0.6))
