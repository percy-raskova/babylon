"""Unit tests for Bug C — substrate apportionment (spec-066 US5).

Spec: 066-marx-coherence-fixes (T061-T063).

Energy reserves follow population (where consumption + storage happens).
Raw material stocks follow geological / land area (where mining happens).
Currently both substrate stocks fall back to population-weighted because
the area-weighted branch was never wired. This bug fix splits the two:

- energy_stock         = state_energy_value × (county_population / state_population)
- raw_material_stock   = state_nonfuel_mineral_value × (county_area / state_area)

Verifies that ≥50% of counties show distinct values for the two substrate
stocks after the fix.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.unit]


def test_energy_population_weighted() -> None:
    """T061: energy_stock follows population_share.

    For a 2-county scenario with population_share=(0.7, 0.3) and
    state_energy_value=1000, energy_stocks should be (700, 300).
    """
    pytest.skip("WIP — implemented in spec-066 US5 phase (T065-T067)")


def test_raw_material_area_weighted() -> None:
    """T062: raw_material_stock follows area_share.

    For a 2-county scenario with area_share=(0.4, 0.6) and
    state_nonfuel_mineral_value=1000, raw_material_stocks should be (400, 600).
    """
    pytest.skip("WIP — implemented in spec-066 US5 phase (T065-T067)")


def test_energy_neq_raw_material_majority() -> None:
    """T063: for the 83-county Michigan scope, >=42 counties show
    energy_stock != raw_material_stock at tick 0."""
    pytest.skip("WIP — implemented in spec-066 US5 phase (T065-T067)")
