"""Factory contracts for the five electoral goldens (P25 U13, ADR140).

Shape-only pins: each factory builds its §5.5 terrain deterministically —
substrate, party layer, register seeds, stances, bridges. The ARCS are
pinned by ``tests/unit/engine/systems/test_electoral_goldens.py``; the
byte-level determinism contract is the qa:regression baseline pair minted
by the ``blessed(electoral-goldens)`` ceremony.
"""

from __future__ import annotations

import pytest

from babylon.engine.scenarios.electoral_goldens import (
    create_bernie_valve_scenario,
    create_debs_scenario,
    create_mitterrand_scenario,
    create_syriza_scenario,
    create_weimar_scenario,
)
from babylon.models.enums import EdgeType

pytestmark = pytest.mark.unit

_PARTIES = {
    "org/party-liberal",
    "org/party-restorationist",
    "org/party-socdem",
    "org/party-fascist",
}


def _party_ids(state) -> set[str]:
    return {oid for oid in state.organizations if oid.startswith("org/party-")}


class TestWayneGoldens:
    """mitterrand/syriza/bernie stand on the Wayne single_county substrate."""

    def test_mitterrand_opens_seated_with_the_calibration_agenda(self) -> None:
        state, _config, _defines = create_mitterrand_scenario()
        assert _party_ids(state) == _PARTIES
        registers = state.superstructure_registers
        seated = registers["electoral_governments"]["SOV_USA_FED"]
        assert seated["party_id"] == "org/party-socdem"
        agenda = registers["policy_agenda"]
        assert len(agenda) == 24
        assert all(item["axis"] == "social_wage" for item in agenda)
        assert all(item["source_org_id"] == "" for item in agenda)

    def test_syriza_is_captured_with_organs_on_the_terrain(self) -> None:
        state, _config, _defines = create_syriza_scenario()
        socdem = state.organizations["org/party-socdem"]
        assert socdem.institutional_pull == pytest.approx(0.65)
        assert "governance_road" in socdem.acquired_doctrine_ids
        claimants = {
            rel.source_id
            for rel in state.relationships
            if rel.edge_type == EdgeType.CLAIMS and rel.target_id == "T001"
        }
        assert "SOV_MI_STATE" in claimants

    def test_bernie_twins_share_the_base_but_not_the_bridge(self) -> None:
        state, _config, _defines = create_bernie_valve_scenario()
        assert {"C003", "C005", "C006"} <= set(state.entities)
        assert "entryism" in state.organizations["org/party-socdem"].acquired_doctrine_ids
        bridged = {
            (rel.source_id, rel.target_id)
            for rel in state.relationships
            if rel.edge_type == EdgeType.SOLIDARITY
        }
        assert ("C003", "C006") in bridged
        assert not any("C005" in pair for pair in bridged)
        assert "policy_agenda" in state.superstructure_registers


class TestBallotGoldens:
    """weimar/debs stand on the two_node substrate."""

    def test_weimar_carries_the_apparatus_and_the_bonapartist_presidency(self) -> None:
        state, _config, _defines = create_weimar_scenario()
        interior = state.organizations["org/state-interior"]
        assert interior.faction_balance is not None
        assert interior.rng_seed == 0
        presidency = state.institutions["INST_PRESIDENCY"]
        assert presidency.internal_balance.institutionalist_bonapartist > 0.4
        solidarity = [rel for rel in state.relationships if rel.edge_type == EdgeType.SOLIDARITY]
        assert solidarity == []

    def test_debs_runs_the_independent_line_with_a_live_bridge(self) -> None:
        state, _config, _defines = create_debs_scenario()
        socdem = state.organizations["org/party-socdem"]
        assert "independent_ballot_line" in socdem.acquired_doctrine_ids
        bridged = {
            (rel.source_id, rel.target_id)
            for rel in state.relationships
            if rel.edge_type == EdgeType.SOLIDARITY and rel.solidarity_strength
        }
        assert ("C001", "C005") in bridged
