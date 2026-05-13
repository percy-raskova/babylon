"""FR-023 FIPS-mapping invariant test (T031d).

For every ``DynamicHexState`` row in a freshly-initialized session:
``state_fips == county_fips[:2]``. The model itself doesn't enforce this
(it's a cross-field invariant), so we test:

  (a) a synthetic well-formed row passes the invariant check helper, and
  (b) a synthetic ill-formed row (state mismatch) is correctly flagged.

The integration-level enforcement (validating against real Census tables)
is owned by the initialization integration tests.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from babylon.persistence.hex_state import DynamicHexState


def _row_with(county_fips: str, state_fips: str) -> DynamicHexState:
    return DynamicHexState(
        session_id=uuid4(),
        tick=0,
        h3_index="872d34a89ffffff",
        county_fips=county_fips,
        state_fips=state_fips,
        region_id="east_north_central",
        c=10.0,
        v=5.0,
        s=3.0,
        k=100.0,
        biocapacity_stock=50.0,
        energy_stock=20.0,
        raw_material_stock=10.0,
        internet_access_pct=0.85,
        surveillance_coupling=0.4,
    )


def _state_fips_matches_county(row: DynamicHexState) -> bool:
    """FR-023 invariant: state_fips == county_fips[:2]."""
    return row.state_fips == row.county_fips[:2]


@pytest.mark.cross_scale
def test_invariant_holds_for_wayne_county_michigan() -> None:
    """26163 -> 26 (Wayne County, MI). Canonical example from Detroit scenario."""
    row = _row_with(county_fips="26163", state_fips="26")
    assert _state_fips_matches_county(row)


@pytest.mark.cross_scale
def test_invariant_holds_for_macomb_county_michigan() -> None:
    """26099 -> 26 (Macomb County, MI)."""
    row = _row_with(county_fips="26099", state_fips="26")
    assert _state_fips_matches_county(row)


@pytest.mark.cross_scale
def test_invariant_holds_for_essex_county_canada_side_when_modeled() -> None:
    """Sanity: cross-county-state pair flagged by the invariant.

    Crossing state lines requires county_fips[:2] == state_fips. A row
    that violates this is caught by the helper. This is the negative
    case for FR-023.
    """
    bad = _row_with(county_fips="26163", state_fips="36")  # MI county, NY state
    assert not _state_fips_matches_county(bad)


@pytest.mark.cross_scale
def test_invariant_detects_truncation_off_by_one() -> None:
    """state_fips must be the FIRST two characters, not arbitrary substring."""
    bad = _row_with(county_fips="26163", state_fips="63")
    assert not _state_fips_matches_county(bad)
