"""WO-39 integration: submit → queue → fold → OODASystem adjudicates.

The full write-side chain the TUI verb plate rides: ``submit_verb`` queues
a structured row (affordability-gated), ``build_player_actions`` folds
pending rows into the engine-injection shape, and the engine's OODASystem
— untouched by this program — consumes ``persistent_data["player_actions"]``
and publishes the result in ``turn_resolution``. No direct graph mutation
anywhere on the read side: the engine adjudicates (Ruling R4, Article V).

In-process engine system, no Postgres — the queue is a structural journal
(the SQL side of ``submit_turn`` is pre-existing, separately covered
persistence code).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

from babylon.config.defines import GameDefines
from babylon.engine.context import TickContext
from babylon.engine.systems.ooda import OODASystem
from babylon.models.enums import OrgType
from babylon.models.enums.topology import NodeType
from babylon.projection.verbs.submit import build_player_actions, submit_verb
from babylon.topology import BabylonGraph

pytestmark = [pytest.mark.integration]

ORG = "rev_workers"
COMMUNITY = "comm_detroit"


class _TurnJournal:
    """Structural TurnSink that plays the game_turn table's role in-memory."""

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


def _graph() -> BabylonGraph:
    """One player faction with a community in reach (OODA-minimal shape)."""
    graph = BabylonGraph()
    graph.add_node(
        ORG,
        NodeType.ORGANIZATION,
        id=ORG,
        org_type=OrgType.POLITICAL_FACTION.value,
        territory_ids=["detroit"],
        consciousness_tendency="revolutionary",
        cadre_level=0.6,
        cohesion=0.6,
        budget=50.0,
        heat=0.1,
        ooda_profile={"action_points": 4, "decision_mode": "autocratic"},
    )
    graph.add_node(
        COMMUNITY,
        NodeType.COMMUNITY,
        id=COMMUNITY,
        collective_identity=0.3,
        ideological_contestation=0.2,
        heat=0.0,
        infrastructure=0.5,
    )
    graph.add_node("detroit", NodeType.TERRITORY)
    return graph


def _services() -> MagicMock:
    services = MagicMock()
    services.defines = GameDefines()
    services.event_bus = MagicMock()
    return services


def test_submitted_verb_reaches_turn_resolution_through_the_engine() -> None:
    """submit → fold → OODASystem.step → the action resolves under our org."""
    graph = _graph()
    journal = _TurnJournal()

    submit_verb(
        journal,
        session_id=uuid4(),
        tick=1,
        org_id=ORG,
        verb="educate",
        graph=graph,
        target_id=COMMUNITY,
    )

    player_actions = build_player_actions(journal.rows)
    context = TickContext(tick=1, persistent_data={"player_actions": player_actions})
    OODASystem().step(graph, _services(), context)

    resolution = context.persistent_data["turn_resolution"]
    ours = [r for r in resolution["action_phase_results"] if r["action"]["org_id"] == ORG]
    assert ours, "the queued player action must resolve in the action phase"
    assert any(r["action"]["action_type"] == "educate" for r in ours)


def test_rejected_submission_never_reaches_the_engine() -> None:
    """An unaffordable verb is refused at the queue door — the engine never
    sees it, and the plate's afford_note copy matches the rejection."""
    graph = _graph()
    graph.update_node(ORG, budget=0.0, cadre_level=0.0, cohesion=0.0)
    journal = _TurnJournal()

    with pytest.raises(ValueError, match="Cannot afford"):
        submit_verb(
            journal,
            session_id=uuid4(),
            tick=1,
            org_id=ORG,
            verb="educate",
            graph=graph,
            target_id=COMMUNITY,
        )

    assert journal.rows == []
    assert build_player_actions(journal.rows) == {}
