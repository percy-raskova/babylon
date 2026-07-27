"""The superstructure-register round-trip carrier (P25 U13, ADR140).

U8-U12 built the ambient political machine on eleven graph-level registers
(``set_graph_attr``), read/written across ticks on the ONE graph the headless
runner mutates in place. The ``simulation_engine.step()`` API round-trips
``WorldState`` <-> graph every tick, and ``to_graph``/``from_graph`` carried
none of the eleven — every register silently reset each ``step()`` call, so
the electoral machine was amnesiac through the exact API the qa:regression
harness uses. The carrier is a declared ``WorldState.superstructure_registers``
field riding the round-trip (the ``field_stack`` precedent), giving ``step()``
parity with the runner's persistent graph.

Byte-safety for the original six qa:regression scenarios: no party-less
scenario ever writes a register (the parties-exist / empty-register guards),
so the field stays empty, ``to_graph`` stamps nothing, and ``from_graph``
harvests nothing — honest absence, never a fabricated empty register
(Constitution III.11).
"""

from __future__ import annotations

import pytest

from babylon.models.superstructure import SUPERSTRUCTURE_REGISTERS
from babylon.models.world_state import WorldState

pytestmark = pytest.mark.unit


class TestCanonicalRegisterSet:
    """The models-layer tuple is the single source of truth for the set."""

    def test_the_eleven_registers_are_declared(self) -> None:
        assert set(SUPERSTRUCTURE_REGISTERS) == {
            "policy_agenda",
            "policy_overlays",
            "sovereign_fiscal",
            "policy_delivery",
            "governance_endgame",
            "electoral_governments",
            "electoral_disillusion",
            "electoral_derecognized",
            "popular_front",
            "political_form_org_positions",
            "political_labor_share",
        }

    def test_no_duplicates(self) -> None:
        assert len(SUPERSTRUCTURE_REGISTERS) == len(set(SUPERSTRUCTURE_REGISTERS))

    def test_matches_the_sentinel_owner_map(self) -> None:
        """The superstructure sentinel's owner map and the carrier agree.

        A register with an owner but no carriage would be amnesiac through
        ``step()``; a carried name without an owner would be an unlicensed
        write surface. The two declarations must cover the same set.
        """
        from babylon.sentinels.superstructure.registry import (
            SUPERSTRUCTURE_ATTR_OWNERS,
        )

        assert set(SUPERSTRUCTURE_REGISTERS) == set(SUPERSTRUCTURE_ATTR_OWNERS)

    def test_matches_the_engine_constants(self) -> None:
        """Every engine-side ``*_ATTR`` constant names a carried register."""
        from babylon.engine.systems.electoral import (
            ELECTORAL_DERECOGNIZED_ATTR,
            ELECTORAL_DISILLUSION_ATTR,
            ELECTORAL_GOVERNMENTS_ATTR,
            POPULAR_FRONT_ATTR,
        )
        from babylon.engine.systems.policy import (
            GOVERNANCE_ENDGAME_ATTR,
            POLICY_AGENDA_ATTR,
            POLICY_DELIVERY_ATTR,
            POLICY_OVERLAYS_ATTR,
            SOVEREIGN_FISCAL_ATTR,
        )

        constants = {
            POLICY_AGENDA_ATTR,
            POLICY_OVERLAYS_ATTR,
            SOVEREIGN_FISCAL_ATTR,
            POLICY_DELIVERY_ATTR,
            GOVERNANCE_ENDGAME_ATTR,
            ELECTORAL_GOVERNMENTS_ATTR,
            ELECTORAL_DISILLUSION_ATTR,
            ELECTORAL_DERECOGNIZED_ATTR,
            POPULAR_FRONT_ATTR,
        }
        assert constants <= set(SUPERSTRUCTURE_REGISTERS)


class TestRoundTrip:
    """Seeded registers survive WorldState -> graph -> WorldState."""

    def test_to_graph_stamps_each_seeded_register(self) -> None:
        state = WorldState(
            superstructure_registers={
                "electoral_governments": {
                    "SOV_USA_FED": {
                        "party_id": "org/party-socdem",
                        "formed_tick": 0,
                        "share": 0.55,
                    }
                },
                "policy_agenda": [{"sovereign_id": "SOV_USA_FED"}],
            }
        )
        graph = state.to_graph()
        assert graph.get_graph_attr("electoral_governments") == {
            "SOV_USA_FED": {
                "party_id": "org/party-socdem",
                "formed_tick": 0,
                "share": 0.55,
            }
        }
        assert graph.get_graph_attr("policy_agenda") == [{"sovereign_id": "SOV_USA_FED"}]

    def test_from_graph_harvests_present_registers(self) -> None:
        graph = WorldState().to_graph()
        graph.set_graph_attr("political_labor_share", 0.25)
        graph.set_graph_attr("electoral_derecognized", ("org/party-entryist",))
        state = WorldState.from_graph(graph, tick=0)
        assert state.superstructure_registers["political_labor_share"] == 0.25
        assert state.superstructure_registers["electoral_derecognized"] == ("org/party-entryist",)

    def test_full_round_trip_preserves_registers(self) -> None:
        seeded = WorldState(
            superstructure_registers={
                "sovereign_fiscal": {
                    "SOV_USA_FED": {
                        "sovereign_id": "SOV_USA_FED",
                        "debt_stock": 12.5,
                        "last_borrowed": 3.0,
                    }
                }
            }
        )
        state = WorldState.from_graph(seeded.to_graph(), tick=0)
        assert state.superstructure_registers == seeded.superstructure_registers

    def test_harvest_copies_do_not_alias_the_graph(self) -> None:
        """A frozen WorldState must not alias the graph's live dicts."""
        graph = WorldState().to_graph()
        live = {"SOV_USA_FED": {"party_id": "org/party-socdem"}}
        graph.set_graph_attr("electoral_governments", live)
        state = WorldState.from_graph(graph, tick=0)
        harvested = state.superstructure_registers["electoral_governments"]
        assert harvested == live
        assert harvested is not live


class TestHonestAbsence:
    """Absence carries as absence — never a fabricated empty register."""

    def test_empty_field_stamps_no_graph_attrs(self) -> None:
        graph = WorldState().to_graph()
        for name in SUPERSTRUCTURE_REGISTERS:
            assert graph.get_graph_attr(name, None) is None

    def test_bare_graph_harvests_to_empty_field(self) -> None:
        state = WorldState.from_graph(WorldState().to_graph(), tick=0)
        assert state.superstructure_registers == {}
