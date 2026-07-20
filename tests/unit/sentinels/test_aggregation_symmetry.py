"""Tests for the aggregation-symmetry sentinel: all-masked -> honest None.

Unlike the other sentinels in this family, this one's dynamic harness lives
in ``tools/aggregation_symmetry_probe.py`` (it must import
``game.engine_bridge``, a Django app layered above ``babylon.*`` — see that
module's and ``babylon.sentinels.aggregation``'s own docstrings for why).
These tests import the probe module directly (the same way
``tests/unit/web/test_map_aggregation.py`` imports ``game.engine_bridge``
under pytest-django) and exercise its check functions plus the two real
aggregation functions with synthetic partial/full-masking input.

- **Liveness** — the real, shipped registry against the real
  ``engine_bridge.py`` functions: both declared rows must be clean (the
  founding grounding: both already implement the honest-None contract).
- **Regression proof** — a synthetic *mixed* (partially masked) group
  proves the aggregation is not merely "always None" — it correctly
  computes a real mean over the VISIBLE members while excluding the masked
  one, and only degrades to None when NOTHING is visible.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.unit

_TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools"
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

import aggregation_symmetry_probe as probe  # type: ignore[import-not-found]  # noqa: E402

from babylon.sentinels.aggregation.registry import DECLARED_AGGREGATES  # noqa: E402


def test_declared_registry_has_the_two_seeded_rows() -> None:
    names = {row.name for row in DECLARED_AGGREGATES}
    assert names == {"hex_features_heat", "state_apparatus_dashboard_heat"}


def test_every_declared_row_has_a_probe_registered() -> None:
    for row in DECLARED_AGGREGATES:
        assert row.name in probe._PROBES, f"{row.name!r} has no probe dispatch entry"


def test_live_registry_is_symmetric_against_the_real_functions() -> None:
    """Both declared aggregates currently satisfy the honest-None contract."""
    assert probe.check_all_declared_aggregates() == []


def test_hex_features_all_masked_yields_none_heat() -> None:
    from game.engine_bridge import EngineBridge
    from game.fog.ledger import IntelLedger

    hex_states = [
        SimpleNamespace(
            h3_index="hex1",
            county_fips="26163",
            state_fips="26",
            bea_ea_code="EA1",
            msa_code="MSA1",
            pop_total=100,
            heat=75.0,
            org_count=0,
            profit_rate=None,
            exploitation_rate=None,
            occ=None,
            imperial_rent=None,
            county_name="Test County",
            attributes={},
            dominant_class=None,
        )
    ]
    features = EngineBridge._aggregate_hex_features(
        hex_states,
        "county",
        reach=frozenset(),
        ledger=IntelLedger(),
        tick=0,
        staleness_ticks=10,
        unknown_ticks=20,
        h3_to_territory={},
    )
    assert features[0]["properties"]["heat"] is None


def test_hex_features_partial_masking_excludes_masked_from_mean() -> None:
    """A group with ONE in-reach hex and ONE out-of-reach hex must average
    only the visible one -- proving heat_pop tracks coverage correctly, not
    merely "always None once anything is masked"."""
    from game.engine_bridge import EngineBridge
    from game.fog.ledger import IntelLedger

    hex_states = [
        SimpleNamespace(
            h3_index="hex_visible",
            county_fips="26163",
            state_fips="26",
            bea_ea_code="EA1",
            msa_code="MSA1",
            pop_total=100,
            heat=80.0,
            org_count=0,
            profit_rate=None,
            exploitation_rate=None,
            occ=None,
            imperial_rent=None,
            county_name="Test County",
            attributes={},
            dominant_class=None,
        ),
        SimpleNamespace(
            h3_index="hex_masked",
            county_fips="26163",
            state_fips="26",
            bea_ea_code="EA1",
            msa_code="MSA1",
            pop_total=100,
            heat=20.0,
            org_count=0,
            profit_rate=None,
            exploitation_rate=None,
            occ=None,
            imperial_rent=None,
            county_name="Test County",
            attributes={},
            dominant_class=None,
        ),
    ]
    # Territory ids so the fog gate can key the reach set (h3 -> territory).
    h3_to_territory = {"hex_visible": "TERR_VISIBLE", "hex_masked": "TERR_MASKED"}
    features = EngineBridge._aggregate_hex_features(
        hex_states,
        "county",
        reach=frozenset({"TERR_VISIBLE"}),
        ledger=IntelLedger(),
        tick=0,
        staleness_ticks=10,
        unknown_ticks=20,
        h3_to_territory=h3_to_territory,
    )
    # Population-weighted mean over ONLY the visible hex (pop 100, heat 80.0)
    # -- never blended with the masked hex's raw 20.0.
    assert features[0]["properties"]["heat"] == 80.0


def test_state_apparatus_dashboard_all_masked_yields_none_total_heat() -> None:
    from babylon.models.world_state import WorldState
    from game.engine_bridge import _build_state_apparatus_dashboard

    state = WorldState(tick=0)
    organizations = [
        {"id": "T1", "org_type": "state_apparatus", "budget": 10.0, "heat": None},
    ]
    dashboard = _build_state_apparatus_dashboard(state, organizations, recent_actions=[])
    assert dashboard["total_heat"] is None
    assert dashboard["heat_orgs_visible"] == 0
    assert dashboard["heat_orgs_masked"] == 1


def test_state_apparatus_dashboard_partial_masking_excludes_masked_from_sum() -> None:
    from babylon.models.world_state import WorldState
    from game.engine_bridge import _build_state_apparatus_dashboard

    state = WorldState(tick=0)
    organizations = [
        {"id": "T1", "org_type": "state_apparatus", "budget": 10.0, "heat": 0.6},
        {"id": "T2", "org_type": "state_apparatus", "budget": 20.0, "heat": None},
    ]
    dashboard = _build_state_apparatus_dashboard(state, organizations, recent_actions=[])
    assert dashboard["total_heat"] == 0.6
    assert dashboard["heat_orgs_visible"] == 1
    assert dashboard["heat_orgs_masked"] == 1
