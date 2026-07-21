"""Contract tests for the projection view-models (CountyView + hydration)."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from babylon.projection.view_models import (
    ClassComposition,
    ConsciousnessSimplex,
    CountyView,
    hydrate_county,
    hydrate_record,
)


def _wayne_county_dict() -> dict[str, Any]:
    """A fully-populated source dict shaped like Wayne County (FIPS 26163)."""
    return {
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


def test_golden_wayne_county_hydration() -> None:
    """A Wayne-County dict hydrates into a fully-populated ``CountyView``."""
    view = hydrate_county(_wayne_county_dict())

    assert view.kind == "county"
    assert view.county_fips == "26163"
    assert view.verified_tick == 500
    assert view.population == 1749343
    assert view.median_wage == pytest.approx(18.5)
    assert view.imperial_rent_phi == pytest.approx(4.2)
    assert view.legitimacy == pytest.approx(0.42)
    assert view.p_acquiescence == pytest.approx(0.7)
    assert view.p_revolution == pytest.approx(0.25)
    assert view.bifurcation_score == pytest.approx(-0.35)
    assert view.sovereign_id == "SOV_USA"

    assert isinstance(view.class_composition, ClassComposition)
    assert view.class_composition.proletariat == pytest.approx(0.55)
    assert isinstance(view.consciousness, ConsciousnessSimplex)
    assert view.consciousness.liberal == pytest.approx(0.6)


def test_hydrate_record_dispatches_on_kind() -> None:
    """The discriminated union routes a ``county`` payload to ``CountyView``."""
    record = hydrate_record(_wayne_county_dict())
    assert isinstance(record, CountyView)
    assert record.kind == "county"


def test_hydrate_record_rejects_unknown_kind() -> None:
    """A payload with an unknown discriminator is rejected."""
    payload = _wayne_county_dict()
    payload["kind"] = "state"
    with pytest.raises(ValidationError):
        hydrate_record(payload)


def test_county_view_is_frozen() -> None:
    """A hydrated view is immutable — projections are read-only records."""
    view = hydrate_county(_wayne_county_dict())
    with pytest.raises(ValidationError):
        view.county_fips = "00000"  # type: ignore[misc]


def test_absent_fog_field_hydrates_to_none() -> None:
    """A withheld value-axis field (imperial rent Φ) hydrates to ``None``."""
    payload = _wayne_county_dict()
    del payload["imperial_rent_phi"]
    view = hydrate_county(payload)
    assert view.imperial_rent_phi is None


def test_explicit_null_is_honest_absence() -> None:
    """An explicit ``None`` is absence, distinct from any defaulted zero."""
    payload = _wayne_county_dict()
    payload["population"] = None
    view = hydrate_county(payload)
    assert view.population is None


def test_minimal_record_defaults_optionals_to_none() -> None:
    """Only identity and provenance are required; every other field is absent."""
    view = hydrate_county({"kind": "county", "county_fips": "26163", "verified_tick": 1})
    assert view.population is None
    assert view.class_composition is None
    assert view.consciousness is None
    assert view.bifurcation_score is None
    assert view.sovereign_id is None


def test_extra_keys_are_rejected() -> None:
    """A payload carrying an undeclared field is a loud shape mismatch."""
    payload = _wayne_county_dict()
    payload["undeclared_field"] = 1
    with pytest.raises(ValidationError):
        hydrate_county(payload)


def test_county_fips_pattern_is_enforced() -> None:
    """A malformed FIPS code is rejected — identity must be well-formed."""
    payload = _wayne_county_dict()
    payload["county_fips"] = "2616"  # four digits
    with pytest.raises(ValidationError):
        hydrate_county(payload)


def test_bifurcation_score_is_bounded_to_the_axis() -> None:
    """The bifurcation score lives on ``[-1, +1]`` (Ideology)."""
    payload = _wayne_county_dict()
    payload["bifurcation_score"] = 1.5
    with pytest.raises(ValidationError):
        hydrate_county(payload)


def test_class_composition_must_sum_to_one() -> None:
    """Five class shares that do not sum to one are a malformed composition."""
    with pytest.raises(ValidationError):
        ClassComposition(
            bourgeoisie=0.5,
            petit_bourgeoisie=0.5,
            labor_aristocracy=0.5,
            proletariat=0.5,
            lumpenproletariat=0.5,
        )


def test_consciousness_simplex_must_sum_to_one() -> None:
    """Three consciousness poles that do not sum to one are rejected."""
    with pytest.raises(ValidationError):
        ConsciousnessSimplex(revolutionary=0.5, liberal=0.5, fascist=0.5)
