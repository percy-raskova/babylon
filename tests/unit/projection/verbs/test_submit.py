"""Contract tests for structured verb submission (WO-39).

Submission is a write to the runtime action queue and nothing else: no
direct graph mutation — verbs resolve via OODASystem next tick (Ruling R4,
Article V atomicity). Affordability is gated by the same
:func:`check_can_afford` the plate shows, plus ATTACK's mode-specific
cadre/sympathizer labor costs, ported verbatim from the legacy bridge.
Ports ``test_engine_bridge.py::TestEngineBridgeActions`` submission
assertions. Persistence is a structural stub — no database.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest

from babylon.models.enums.topology import NodeType
from babylon.projection.verbs.submit import build_player_actions, submit_verb
from babylon.topology import BabylonGraph

ORG = "org-player"
SESSION = uuid4()


class _TurnJournal:
    """Structural stand-in for the runtime persistence's submit_turn."""

    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def submit_turn(
        self,
        session_id: UUID,
        tick: int,
        org_id: str,
        verb: str,
        *,
        action_type: str | None = None,
        target_id: str | None = None,
        target_community: str | None = None,
        params_json: dict[str, Any] | None = None,
    ) -> int:
        self.rows.append(
            {
                "session_id": session_id,
                "tick": tick,
                "org_id": org_id,
                "verb": verb,
                "action_type": action_type,
                "target_id": target_id,
                "target_community": target_community,
                "params_json": params_json,
            }
        )
        return len(self.rows)


def _graph(*, budget: float = 50.0, cadre_level: float = 0.6) -> BabylonGraph:
    graph = BabylonGraph()
    graph.add_node(
        ORG,
        NodeType.ORGANIZATION,
        id=ORG,
        name="The Union",
        org_type="political_faction",
        cadre_level=cadre_level,
        cohesion=0.6,
        budget=budget,
        heat=0.1,
        territory_ids=["T001"],
    )
    return graph


class TestSubmitVerb:
    def test_submits_a_structured_row_and_returns_the_turn_id(self) -> None:
        journal = _TurnJournal()
        turn_id = submit_verb(
            journal,
            session_id=SESSION,
            tick=3,
            org_id=ORG,
            verb="educate",
            graph=_graph(),
            target_id="sc-proles",
        )
        assert turn_id == 1
        row = journal.rows[0]
        assert row["verb"] == "educate"
        assert row["target_id"] == "sc-proles"
        assert row["tick"] == 3

    def test_unaffordable_verb_is_rejected_loudly_and_writes_nothing(self) -> None:
        journal = _TurnJournal()
        with pytest.raises(ValueError, match="Cannot afford"):
            submit_verb(
                journal,
                session_id=SESSION,
                tick=0,
                org_id=ORG,
                verb="educate",
                graph=_graph(budget=0.0, cadre_level=0.0),
            )
        assert journal.rows == []

    def test_attack_targeted_mode_gates_on_cadre_labor(self) -> None:
        journal = _TurnJournal()
        with pytest.raises(ValueError, match="targeted.*Need 4.0 CL"):
            submit_verb(
                journal,
                session_id=SESSION,
                tick=0,
                org_id=ORG,
                verb="attack",
                graph=_graph(cadre_level=0.0),
                params_json={"mode": "targeted"},
            )

    def test_attack_mass_mode_gates_on_sympathizer_labor(self) -> None:
        journal = _TurnJournal()
        with pytest.raises(ValueError, match="mass.*Need 15.0 SL"):
            submit_verb(
                journal,
                session_id=SESSION,
                tick=0,
                org_id=ORG,
                verb="attack",
                graph=_graph(cadre_level=0.0),
                params_json={"mode": "mass"},
            )

    def test_unknown_org_skips_the_affordability_gate_like_the_bridge(self) -> None:
        """The legacy bridge only gates affordability when the org exists in
        state — an absent org falls through to persistence (which owns the
        integrity error). Preserved verbatim."""
        journal = _TurnJournal()
        turn_id = submit_verb(
            journal,
            session_id=SESSION,
            tick=0,
            org_id="org-ghost",
            verb="educate",
            graph=_graph(),
        )
        assert turn_id == 1

    def test_non_canonical_verb_raises_before_touching_persistence(self) -> None:
        journal = _TurnJournal()
        with pytest.raises(ValueError, match="not a canonical verb"):
            submit_verb(
                journal,
                session_id=SESSION,
                tick=0,
                org_id=ORG,
                verb="vibe",
                graph=_graph(),
            )
        assert journal.rows == []


class TestBuildPlayerActions:
    """The pending-turn -> engine-injection fold (verbatim bridge port)."""

    def test_folds_rows_by_org_with_engine_action_types(self) -> None:
        pending = [
            {"org_id": ORG, "verb": "educate", "target_id": "sc-1", "params_json": None},
            {"org_id": ORG, "verb": "aid", "target_id": "sc-2", "params_json": {"x": 1}},
            {"org_id": "org-b", "verb": "move", "target_id": "T002", "params_json": None},
        ]
        actions = build_player_actions(pending)
        assert set(actions) == {ORG, "org-b"}
        first, second = actions[ORG]
        assert first == {
            "action_type": "educate",
            "target_id": "sc-1",
            "org_id": ORG,
            "action_point_cost": 1,
            "params": {},
        }
        assert second["action_type"] == "provide_service"
        assert second["params"] == {"x": 1}
        assert actions["org-b"][0]["action_type"] == "move"

    def test_json_null_params_become_an_empty_dict_never_none(self) -> None:
        """A submit without params persists params_json as JSON null; the
        fold must coerce it to {} or Action validation 500s the resolve."""
        actions = build_player_actions([{"org_id": ORG, "verb": "educate", "params_json": None}])
        assert actions[ORG][0]["params"] == {}

    def test_missing_target_defaults_to_the_acting_org(self) -> None:
        actions = build_player_actions([{"org_id": ORG, "verb": "reproduce"}])
        assert actions[ORG][0]["target_id"] == ORG

    def test_unmapped_verb_passes_through_as_its_own_action_type(self) -> None:
        actions = build_player_actions([{"org_id": ORG, "verb": "legacy_special"}])
        assert actions[ORG][0]["action_type"] == "legacy_special"

    def test_empty_pending_folds_to_an_empty_mapping(self) -> None:
        assert build_player_actions([]) == {}
