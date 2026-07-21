"""Shared CountyView/NationalView fixtures for vault materializer tests.

Both County fixtures share the Wayne County (FIPS 26163) identity from the
WO-2 contract tests (``tests/unit/projection/test_view_models.py``); the
"absences" variant leaves several optional fields unattributed to exercise
the {absence} block path honestly rather than via a fabricated payload. The
National fixtures (WO-17) follow the identical pattern one tier up.
"""

from __future__ import annotations

import pytest

from babylon.projection.view_models import (
    CountyView,
    NationalView,
    hydrate_county,
    hydrate_national,
)


@pytest.fixture
def wayne_county_view() -> CountyView:
    """A fully-populated ``CountyView`` shaped like Wayne County."""
    return hydrate_county(
        {
            "kind": "county",
            "county_fips": "26163",
            "verified_tick": 500,
            "population": 1749343,
            "class_composition": {
                "bourgeoisie": 0.02,
                "petit_bourgeoisie": 0.08,
                "labor_aristocracy": 0.30,
                "proletariat": 0.55,
                "lumpenproletariat": 0.05,
            },
            "median_wage": 18.5,
            "imperial_rent_phi": 4.2,
            "consciousness": {
                "revolutionary": 0.3,
                "liberal": 0.6,
                "fascist": 0.1,
            },
            "legitimacy": 0.42,
            "p_acquiescence": 0.7,
            "p_revolution": 0.25,
            "bifurcation_score": -0.35,
            "sovereign_id": "SOV_USA",
        }
    )


@pytest.fixture
def wayne_county_view_with_absences() -> CountyView:
    """The same county with most optional fields honestly unattributed.

    Only ``population``, ``median_wage``, and ``imperial_rent_phi`` are
    present; every other optional field hydrates to ``None``.
    """
    return hydrate_county(
        {
            "kind": "county",
            "county_fips": "26163",
            "verified_tick": 500,
            "population": 1749343,
            "median_wage": 18.5,
            "imperial_rent_phi": 4.2,
        }
    )


@pytest.fixture
def usa_national_view() -> NationalView:
    """A fully-populated ``NationalView`` (WO-17)."""
    return hydrate_national(
        {
            "kind": "national",
            "national_id": "USA",
            "verified_tick": 500,
            "population": 331000000,
            "class_composition": {
                "bourgeoisie": 0.03,
                "petit_bourgeoisie": 0.10,
                "labor_aristocracy": 0.28,
                "proletariat": 0.50,
                "lumpenproletariat": 0.09,
            },
            "median_wage": 22.0,
            "imperial_rent_pool": 100.0,
            "consciousness": {
                "revolutionary": 0.25,
                "liberal": 0.65,
                "fascist": 0.10,
            },
            "legitimacy": 0.48,
            "p_acquiescence": 0.65,
            "p_revolution": 0.30,
            "bifurcation_score": -0.10,
            "sovereign_id": "SOV_USA",
            "c_sum": 1_000_000.0,
            "v_sum": 500_000.0,
            "s_sum": 250_000.0,
            "k_sum": 2_000_000.0,
            "biocapacity_sum": 750_000.0,
            "hex_count": 3156,
        }
    )


@pytest.fixture
def usa_national_view_with_absences() -> NationalView:
    """The same nation with most optional fields honestly unattributed.

    Only ``population`` and ``median_wage`` are present beyond the
    always-materialized ``imperial_rent_pool``; every other optional field
    hydrates to ``None``.
    """
    return hydrate_national(
        {
            "kind": "national",
            "national_id": "USA",
            "verified_tick": 500,
            "population": 331000000,
            "median_wage": 22.0,
            "imperial_rent_pool": 100.0,
        }
    )
