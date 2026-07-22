"""Tests for the real LODES hydration kwarg supplier (Vol II Program, Unit U2).

:func:`resolve_lodes_hydration_kwargs` is the production supplier that closes
the `initialize_session` LODES gate (program prompt §2a: nothing in ``src/``
ever supplied ``lodes_root`` / ``lodes_crosswalk`` / ``lodes_study_area_hexes``
/ ``lodes_study_area_states``, so the hydration block was permanently
unreachable). These tests pin its honest-absence behavior (Constitution
III.8) and its real-value shape for scopes that DO touch the checked-in
Detroit tri-county artifact.
"""

from __future__ import annotations

import pytest

from babylon.domain.economics.lodes_study_area import (
    LODES_ARTIFACT_CROSSWALK,
    LODES_ARTIFACT_ROOT,
    LODES_STUDY_AREA_STATES,
)
from babylon.engine.headless_runner.lodes_hydration import resolve_lodes_hydration_kwargs
from babylon.engine.headless_runner.scopes import DETROIT_TRI_COUNTY_FIPS, MICHIGAN_FIPS

pytestmark = pytest.mark.unit

_EXPECTED_KEYS = frozenset(
    {"lodes_root", "lodes_crosswalk", "lodes_study_area_hexes", "lodes_study_area_states"}
)


def test_detroit_tri_county_scope_gets_real_kwargs() -> None:
    kwargs = resolve_lodes_hydration_kwargs(DETROIT_TRI_COUNTY_FIPS)
    assert kwargs is not None
    assert set(kwargs) == _EXPECTED_KEYS
    assert kwargs["lodes_root"] == LODES_ARTIFACT_ROOT
    assert kwargs["lodes_crosswalk"] == LODES_ARTIFACT_CROSSWALK
    assert kwargs["lodes_study_area_states"] == LODES_STUDY_AREA_STATES
    assert len(kwargs["lodes_study_area_hexes"]) > 0


def test_michigan_statewide_scope_gets_real_kwargs() -> None:
    """A broader scope that still contains the tri-county area also wires up —
    the LODES artifact only covers tri-county, but the scope superset case must
    not be treated as absent."""
    kwargs = resolve_lodes_hydration_kwargs(MICHIGAN_FIPS)
    assert kwargs is not None
    assert set(kwargs) == _EXPECTED_KEYS


def test_disjoint_scope_returns_none_honest_absence() -> None:
    """Constitution III.8: a scope that never touches Michigan gets no
    fabricated LODES hydration — honest ``None``, not synthetic data."""
    california_scope = frozenset({"06001", "06075"})  # Alameda, San Francisco
    assert resolve_lodes_hydration_kwargs(california_scope) is None


def test_empty_scope_returns_none() -> None:
    assert resolve_lodes_hydration_kwargs(frozenset()) is None
