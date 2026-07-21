"""Shared CountyView fixtures for vault materializer tests.

Both fixtures share the Wayne County (FIPS 26163) identity from the WO-2
contract tests (``tests/unit/projection/test_view_models.py``); the
"absences" variant leaves several optional fields unattributed to exercise
the {absence} block path honestly rather than via a fabricated payload.
"""

from __future__ import annotations

import pytest

from babylon.projection.view_models import CountyView, hydrate_county


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
