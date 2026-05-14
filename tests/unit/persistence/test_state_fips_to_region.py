"""Unit tests for the FIPS state code → Census division mapping (Spec-063 closure)."""

from __future__ import annotations

import pytest

from babylon.persistence.state_fips_to_region import (
    STATE_FIPS_TO_CENSUS_DIVISION,
    region_for_state_fips,
)

pytestmark = [pytest.mark.unit]


def test_michigan_maps_to_east_north_central() -> None:
    """Spec-063 hex hydrator depends on this exact mapping (quickstart_062 precedent)."""
    assert region_for_state_fips("26") == "east_north_central"
    assert STATE_FIPS_TO_CENSUS_DIVISION["26"] == "east_north_central"


def test_all_50_states_plus_dc_covered() -> None:
    """All US states + DC (51 entries with FIPS codes 01..56 excluding gaps) present."""
    expected_state_fips = {f"{n:02d}" for n in range(1, 57) if n not in (3, 7, 14, 43, 52)}
    assert expected_state_fips.issubset(set(STATE_FIPS_TO_CENSUS_DIVISION))


def test_five_territories_covered() -> None:
    """LODES+QCEW enumerate American Samoa, Guam, NMI, PR, VI."""
    for fips in ("60", "66", "69", "72", "78"):
        assert STATE_FIPS_TO_CENSUS_DIVISION[fips] == "territory"


def test_unknown_state_returns_unknown_sentinel() -> None:
    """Defensive default: unknown FIPS codes don't crash, just return 'unknown'."""
    assert region_for_state_fips("99") == "unknown"
    assert region_for_state_fips("") == "unknown"


@pytest.mark.parametrize(
    ("state_fips", "expected_division"),
    [
        ("09", "new_england"),  # CT
        ("36", "middle_atlantic"),  # NY
        ("17", "east_north_central"),  # IL
        ("19", "west_north_central"),  # IA
        ("12", "south_atlantic"),  # FL
        ("21", "east_south_central"),  # KY
        ("48", "west_south_central"),  # TX
        ("04", "mountain"),  # AZ
        ("06", "pacific"),  # CA
    ],
)
def test_sample_states_per_division(state_fips: str, expected_division: str) -> None:
    """Sanity-check one state from each of the 9 Census divisions."""
    assert region_for_state_fips(state_fips) == expected_division
