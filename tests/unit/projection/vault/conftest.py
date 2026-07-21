"""Shared CountyView/SocialClassView fixtures for vault materializer tests.

Both CountyView fixtures share the Wayne County (FIPS 26163) identity from
the WO-2 contract tests (``tests/unit/projection/test_view_models.py``); the
"absences" variant leaves several optional fields unattributed to exercise
the {absence} block path honestly rather than via a fabricated payload. The
SocialClassView fixtures (Program 24 P2 WO-23) mirror the same pattern for
Wayne County's Labor Aristocracy worker (C004).
"""

from __future__ import annotations

import pytest

from babylon.projection.view_models import (
    CountyView,
    SocialClassView,
    hydrate_county,
    hydrate_social_class,
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
def wayne_social_class_view() -> SocialClassView:
    """A fully-populated ``SocialClassView`` shaped like Wayne's C004 worker."""
    return hydrate_social_class(
        {
            "kind": "social_class",
            "class_id": "C004",
            "verified_tick": 500,
            "role": "labor_aristocracy",
            "county_fips": "26163",
            "population": 1,
            "wealth": 0.563657,
            "organization": 0.4,
            "repression_faced": 0.2,
            "p_acquiescence": 0.933179,
            "p_revolution": 1.0,
            "consciousness": {
                "revolutionary": 0.235071,
                "liberal": 0.5,
                "fascist": 0.264929,
            },
            "county_class_composition": {
                "bourgeoisie": 0.01,
                "petit_bourgeoisie": 0.09,
                "labor_aristocracy": 0.4,
                "proletariat": 0.35,
                "lumpenproletariat": 0.15,
            },
        }
    )


@pytest.fixture
def wayne_social_class_view_with_absences() -> SocialClassView:
    """The same class with most optional fields honestly unattributed.

    Only ``role``, ``county_fips``, and ``population`` are present; every
    other optional field hydrates to ``None``.
    """
    return hydrate_social_class(
        {
            "kind": "social_class",
            "class_id": "C004",
            "verified_tick": 500,
            "role": "labor_aristocracy",
            "county_fips": "26163",
            "population": 1,
        }
    )
