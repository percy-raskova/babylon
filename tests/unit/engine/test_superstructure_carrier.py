"""Cross-tick register survival through ``simulation_engine.step()`` (ADR140).

The qa:regression harness advances scenarios with ``state = step(state, ...)``
— a full WorldState <-> graph round-trip every tick. Before the U13 carrier,
every superstructure register reset at each tick boundary through this API:
an agenda seeded with two items would enact the first and silently lose the
second, a seeded government would evaporate before its first delivery. These
tests drive the REAL engine (all systems, the electoral fixture's party
terrain) through consecutive ``step()`` calls and pin the cross-tick arc the
runner's persistent graph has always provided.
"""

from __future__ import annotations

import pytest

from babylon.domain.politics.policy import PolicyAgendaItem
from babylon.engine.scenarios.electoral_fixture import create_electoral_fixture_scenario
from babylon.engine.simulation_engine import step
from babylon.models.enums.politics import PolicyAxis

pytestmark = pytest.mark.unit


def _item(axis: PolicyAxis, tick: int) -> dict[str, object]:
    return PolicyAgendaItem(
        sovereign_id="SOV_USA_FED",
        axis=axis,
        magnitude=0.05,
        promised=0.0,
        drafted_tick=tick,
        source_org_id="",
    ).model_dump(mode="json")


class TestAgendaSurvivesTheTickBoundary:
    """A two-item agenda drains over two ticks at policy_agenda_rate=1."""

    def test_second_item_enacts_on_the_second_tick(self) -> None:
        state, config, defines = create_electoral_fixture_scenario()
        state = state.model_copy(
            update={
                "superstructure_registers": {
                    "policy_agenda": [
                        _item(PolicyAxis.WAGE_FLOOR, 0),
                        _item(PolicyAxis.LABOR_LAW, 0),
                    ],
                    "electoral_governments": {
                        "SOV_USA_FED": {
                            "party_id": "org/party-socdem",
                            "formed_tick": 0,
                            "share": 0.55,
                        }
                    },
                }
            }
        )
        persistent: dict[str, object] = {}

        state = step(state, config, persistent, defines)
        registers = state.superstructure_registers
        overlays = registers["policy_overlays"]["SOV_USA_FED"]
        assert overlays["wage_floor"]["magnitude"] == pytest.approx(0.05)
        assert "labor_law" not in overlays
        assert len(registers["policy_agenda"]) == 1

        state = step(state, config, persistent, defines)
        registers = state.superstructure_registers
        overlays = registers["policy_overlays"]["SOV_USA_FED"]
        assert overlays["labor_law"]["magnitude"] == pytest.approx(0.05)
        assert registers["policy_agenda"] == []

    def test_legitimation_refresh_survives_the_tick_boundary(self) -> None:
        """The election-day consent refresh persists (L-SUSPEND's premise).

        legitimation_index was an excluded graph-only attr — every electoral
        refresh died at the next tick's round-trip, so legitimation could
        never decay below the suspension floor through step(). As a declared
        Territory field the written value round-trips; absence stays None
        (III.11).
        """
        from babylon.models.world_state import WorldState

        state, _config, _defines = create_electoral_fixture_scenario()
        assert state.territories["T001"].legitimation_index is None

        graph = state.to_graph()
        graph.update_node("T001", legitimation_index=0.31)
        rebuilt = WorldState.from_graph(graph, tick=1)
        assert rebuilt.territories["T001"].legitimation_index == pytest.approx(0.31)
        round_tripped = rebuilt.to_graph()
        assert round_tripped.get_node("T001").attributes["legitimation_index"] == pytest.approx(
            0.31
        )

    def test_seeded_government_survives_both_ticks(self) -> None:
        state, config, defines = create_electoral_fixture_scenario()
        state = state.model_copy(
            update={
                "superstructure_registers": {
                    "electoral_governments": {
                        "SOV_USA_FED": {
                            "party_id": "org/party-socdem",
                            "formed_tick": 0,
                            "share": 0.55,
                        }
                    }
                }
            }
        )
        persistent: dict[str, object] = {}
        state = step(state, config, persistent, defines)
        state = step(state, config, persistent, defines)
        governments = state.superstructure_registers["electoral_governments"]
        assert governments["SOV_USA_FED"]["party_id"] == "org/party-socdem"
