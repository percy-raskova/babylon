"""Age-15 disaggregation and domestic county roster boundaries."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

import make_national_age_reference as builder  # type: ignore[import-not-found]  # noqa: E402


def census_cells() -> dict[int, int]:
    cells = dict.fromkeys(range(1, 50), 0)
    cells.update({1: 80, 2: 39, 26: 41, 3: 5, 6: 4, 7: 25, 20: 5, 27: 5, 30: 5, 31: 25, 44: 6})
    return cells


def test_published_16_plus_resolves_age_15_within_the_combined_band() -> None:
    assert builder.age_bands("01001", census_cells(), (80, 67)) == (13, 6, 50, 11)
    with pytest.raises(builder.ReferenceBuildError, match="age_15_17"):
        builder.age_bands("01001", census_cells(), (80, 71))


def test_county_and_sex_controls_are_enforced() -> None:
    cells = census_cells()
    cells.update({2: 40, 26: 40})
    with pytest.raises(builder.ReferenceBuildError, match="sex_partition"):
        builder.age_bands("01001", cells, (80, 67))
    with pytest.raises(builder.ReferenceBuildError, match="population_control"):
        builder.age_bands("01001", census_cells(), (81, 67))
    with pytest.raises(builder.ReferenceBuildError, match="county_coverage"):
        builder.validate_roster({"01001", "72001"}, {"01001", "01003"})
