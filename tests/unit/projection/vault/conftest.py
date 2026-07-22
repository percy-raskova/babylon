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
    EconomyView,
    IndustryView,
    NationalView,
    SocialClassView,
    hydrate_county,
    hydrate_economy,
    hydrate_industry,
    hydrate_national,
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


@pytest.fixture
def usa_economy_view() -> EconomyView:
    """A fully-populated ``EconomyView`` (T3 U2 spine-C economy dossier).

    ``energy_beta_j`` is the ONE field that is never present, even here —
    genuinely absent tree-wide by design (see ``EconomyView``'s docstring).
    """
    return hydrate_economy(
        {
            "kind": "economy",
            "economy_id": "USA",
            "verified_tick": 500,
            "wage_balance": 0.18,
            "labor_aristocracy_verdict": True,
            "class_phi_readings": [
                {
                    "entity_id": "C001",
                    "w_paid": 120.0,
                    "v_produced": 100.0,
                    "phi_absolute": 20.0,
                    "phi_relative": 0.2,
                    "labor_aristocracy_ratio": 1.2,
                    "is_labor_aristocracy": True,
                }
            ],
            "phi_unequal_exchange": 12.0,
            "phi_reproduction": 8.0,
            "phi_domestic": 5.0,
            "phi_iii_report": 2.0,
            "phi_decomposition_total": 25.0,
            "surplus_produced": 1500.0,
            "profit_of_enterprise": 600.0,
            "interest_burden": 150.0,
            "ground_rent": 450.0,
            "taxes_on_surplus": 300.0,
            "rentier_share": 0.3,
            "financialization_share": 0.1,
            "total_consumption": 900.0,
            "total_biocapacity": 1000.0,
            "overshoot_ratio": 0.9,
            "biocapacity_ceiling": 1200.0,
        }
    )


@pytest.fixture
def usa_economy_view_with_absences() -> EconomyView:
    """The same economy with only the Fundamental Theorem verdict attributed.

    Only ``wage_balance``/``labor_aristocracy_verdict`` are present; every
    other optional field hydrates to ``None``.
    """
    return hydrate_economy(
        {
            "kind": "economy",
            "economy_id": "USA",
            "verified_tick": 500,
            "wage_balance": 0.18,
            "labor_aristocracy_verdict": True,
        }
    )


@pytest.fixture
def manufacturing_industry_view() -> IndustryView:
    """A fully-populated ``IndustryView`` shaped like NAICS 31-33 (Manufacturing)."""
    return hydrate_industry(
        {
            "kind": "industry",
            "industry_id": "ind_31-33",
            "verified_tick": 500,
            "naics_2digit": "31-33",
            "naics_label": "Manufacturing",
            "total_employment": 2000,
            "total_wages": 100000.0,
            "profit_rate": 1.0 / 3.0,
            "occ": 2.0,
            "department_weights": {
                "dept_I": 0.4,
                "dept_IIa": 0.3,
                "dept_IIb": 0.2,
                "dept_III": 0.1,
            },
            "member_business_count": 2,
            "member_worker_block_count": 1,
            "county_fips": ["26125", "26163"],
        }
    )


@pytest.fixture
def manufacturing_industry_view_with_absences() -> IndustryView:
    """The same industry with most optional fields honestly unattributed.

    Only ``naics_2digit``, ``naics_label``, and ``total_employment`` are
    present; every other optional field hydrates to ``None``.
    """
    return hydrate_industry(
        {
            "kind": "industry",
            "industry_id": "ind_31-33",
            "verified_tick": 500,
            "naics_2digit": "31-33",
            "naics_label": "Manufacturing",
            "total_employment": 2000,
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
