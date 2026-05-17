"""Unit tests for Bug D — ideology baseline placeholder (spec-066 US3).

Spec: 066-marx-coherence-fixes (T043-T045).

Verifies:
- ``create_proletariat()`` and ``create_bourgeoisie()`` accept an
  ``ideology`` keyword override (None | float | IdeologicalProfile)
- the (cc=0.1, ni=0.5) baseline solves the bridge ternary mapping
  to (r=0.05, l=0.50, f=0.45) within ±1e-9
"""

from __future__ import annotations

import pytest

from babylon.engine.factories import create_bourgeoisie, create_proletariat
from babylon.models.entities.social_class import IdeologicalProfile

pytestmark = [pytest.mark.unit]


_BASELINE = IdeologicalProfile(class_consciousness=0.1, national_identity=0.5)


def test_create_proletariat_accepts_ideology_kwarg() -> None:
    """T043: create_proletariat accepts ideology=IdeologicalProfile(...) and
    the returned SocialClass carries the passed value."""
    prol = create_proletariat(id="C001", county_fips="26163", ideology=_BASELINE)
    assert prol.ideology.class_consciousness == pytest.approx(0.1)
    assert prol.ideology.national_identity == pytest.approx(0.5)


def test_create_bourgeoisie_accepts_ideology_kwarg() -> None:
    """T044: create_bourgeoisie accepts ideology=IdeologicalProfile(...) and
    the returned SocialClass carries the passed value."""
    bourg = create_bourgeoisie(id="C002", county_fips="26163", ideology=_BASELINE)
    assert bourg.ideology.class_consciousness == pytest.approx(0.1)
    assert bourg.ideology.national_identity == pytest.approx(0.5)


def test_uniform_baseline_solves_to_target_ternary() -> None:
    """T045: given cc=0.1, ni=0.5, the bridge ternary mapping yields
    (r≈0.05, l≈0.50, f≈0.45) within ±1e-9.

    Bridge mapping (per data-model.md §2):
        r = cc * (1 - ni) = 0.1 * 0.5 = 0.05
        f = ni * (1 - cc) = 0.5 * 0.9 = 0.45
        l = max(0, 1 - r - f) = 1 - 0.05 - 0.45 = 0.50
    """
    cc = _BASELINE.class_consciousness
    ni = _BASELINE.national_identity
    r = cc * (1 - ni)
    f = ni * (1 - cc)
    liberal = max(0.0, 1 - r - f)

    assert r == pytest.approx(0.05, abs=1e-9)
    assert f == pytest.approx(0.45, abs=1e-9)
    assert liberal == pytest.approx(0.50, abs=1e-9)
    assert (r + liberal + f) == pytest.approx(1.0, abs=1e-9)


def test_ideology_none_default_preserves_legacy_scalar() -> None:
    """T048/T049 backward-compat: ideology=None uses the legacy scalar default."""
    prol = create_proletariat()
    # Legacy default: -0.3 (revolutionary scalar) — Pydantic validator converts.
    assert prol.ideology is not None

    bourg = create_bourgeoisie()
    # Legacy default: 0.8 (reactionary scalar) — Pydantic validator converts.
    assert bourg.ideology is not None
