"""Capability-gated verb sub-modes — P25 U11 commit G (ADR137).

The reformist fork gives stances real *verbs*, not just tags. These tests pin
the three sub-modes and their gate:

* ``Campaign(Election, mode=election:run)`` — the Debs road: mass work at
  ``debs_solidarity_efficiency``.
* ``Campaign(Election, mode=election:boycott)`` — principled abstention: hope
  converted only where a disillusion window is LIVE, paid for in MASS_LINK.
* ``Negotiate(mode=coalition)`` — entryism: no leverage gate, CO_OPTIVE debt.
* ``Mobilize(sub_mode=canvass)`` — paper membership at a discounted weight.

The gate itself is the subject: a sub-mode the acting org has not acquired is
refused LOUDLY (Constitution III.11), never silently downgraded to the classic
path — a silent fallback is exactly the "green test over a dead feature" shape
this estate gates against.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from babylon.config.defines import GameDefines
from babylon.engine.actions._capability import (
    decouples_cadre_valve,
    grants_edge_type,
    grants_verb_mode,
)
from babylon.engine.actions.campaign import resolve_campaign
from babylon.engine.actions.mobilize import resolve_mobilize
from babylon.engine.actions.negotiate import resolve_negotiate
from babylon.models.enums import ActionType, EdgeMode, EdgeType, NodeType, OrgType
from babylon.models.enums.doctrine import DoctrineTag
from babylon.ooda.types import Action
from babylon.topology import BabylonGraph

ORG = "org_line"
CLASS = "prole"
HOST = "host_party"

#: Every stance the reformist fork ships, by the capability it is asked for.
_RUN_STANCE = "class_struggle_elections"
_BOYCOTT_STANCE = "abstention_boycott"
_ENTRY_STANCE = "entryism"


def _graph(acquired: tuple[str, ...] = (), mass_link: float = 0.5) -> BabylonGraph:
    """An org with a doctrine line, a class to work on, and a host party."""
    graph = BabylonGraph()
    graph.add_node(
        ORG,
        NodeType.ORGANIZATION,
        id=ORG,
        org_type=OrgType.POLITICAL_FACTION.value,
        cadre_level=0.5,
        cohesion=0.5,
        acquired_doctrine_ids=list(acquired),
        doctrine_tags={DoctrineTag.MASS_LINK.value: mass_link},
    )
    graph.add_node(
        CLASS,
        NodeType.SOCIAL_CLASS,
        id=CLASS,
        ideology={"agitation": 0.1, "class_consciousness": 0.2},
    )
    graph.add_node(
        HOST,
        NodeType.ORGANIZATION,
        id=HOST,
        org_type=OrgType.POLITICAL_FACTION.value,
        cadre_level=0.9,
        cohesion=0.9,
    )
    return graph


def _org_attrs(graph: BabylonGraph, org_id: str = ORG) -> dict[str, Any]:
    node = graph.nodes.get(org_id)
    assert node is not None
    return dict(node)


def _services() -> MagicMock:
    services = MagicMock()
    services.defines = GameDefines()
    services.event_bus = MagicMock()
    return services


def _action(action_type: ActionType, target_id: str, **params: Any) -> Action:
    return Action(
        org_id=ORG,
        action_type=action_type,
        target_id=target_id,
        params=params,
    )


class TestCapabilityGate:
    """The gate reads the tree, never a hardcoded stance list."""

    def test_unacquired_org_grants_nothing(self) -> None:
        assert grants_verb_mode({}, "campaign:election:run") is False
        assert grants_edge_type({}, EdgeType.MEMBERSHIP.value) is False
        assert decouples_cadre_valve({}) is False

    def test_run_stance_grants_only_its_own_mode(self) -> None:
        attrs = {"acquired_doctrine_ids": (_RUN_STANCE,)}
        assert grants_verb_mode(attrs, "campaign:election:run") is True
        assert grants_verb_mode(attrs, "campaign:election:boycott") is False
        assert grants_verb_mode(attrs, "negotiate:coalition") is False

    def test_entryism_grants_both_run_and_coalition(self) -> None:
        attrs = {"acquired_doctrine_ids": (_ENTRY_STANCE,)}
        assert grants_verb_mode(attrs, "campaign:election:run") is True
        assert grants_verb_mode(attrs, "negotiate:coalition") is True
        assert grants_edge_type(attrs, EdgeType.MEMBERSHIP.value) is True

    def test_only_abstention_decouples_the_cadre_valve(self) -> None:
        assert decouples_cadre_valve({"acquired_doctrine_ids": (_BOYCOTT_STANCE,)}) is True
        assert decouples_cadre_valve({"acquired_doctrine_ids": (_ENTRY_STANCE,)}) is False

    def test_unknown_acquired_id_is_ignored_not_fatal(self) -> None:
        """A save from an older tree must not crash the gate."""
        assert grants_verb_mode({"acquired_doctrine_ids": ("no_such_node",)}, "x") is False


class TestCampaignElectionRun:
    """The Debs road: standing candidates IS mass work, at η_cse."""

    def test_ungated_org_is_refused_loudly(self) -> None:
        graph = _graph()
        result = resolve_campaign(
            _action(ActionType.PROPAGANDIZE, CLASS, mode="election:run"),
            _org_attrs(graph),
            graph,
            _services(),
        )
        assert result.success is False
        assert "campaign:election:run" in (result.failure_reason or "")
        assert graph.get_edge(ORG, CLASS, EdgeType.SOLIDARITY.value) is None

    def test_unknown_mode_is_refused_before_the_gate(self) -> None:
        graph = _graph(acquired=(_RUN_STANCE,))
        result = resolve_campaign(
            _action(ActionType.PROPAGANDIZE, CLASS, mode="election:coup"),
            _org_attrs(graph),
            graph,
            _services(),
        )
        assert result.success is False
        assert "unknown election mode" in (result.failure_reason or "")

    def test_run_mints_solidarity_below_the_mass_work_base(self) -> None:
        """η_cse < 1: a real recruitment engine, but below direct mass work."""
        services = _services()
        base_graph = _graph(acquired=(_RUN_STANCE,))
        resolve_campaign(
            _action(ActionType.PROPAGANDIZE, CLASS),
            _org_attrs(base_graph),
            base_graph,
            services,
        )
        base_edge = base_graph.get_edge(ORG, CLASS, EdgeType.SOLIDARITY.value)
        assert base_edge is not None
        base_strength = float(base_edge.attributes["solidarity_strength"])

        run_graph = _graph(acquired=(_RUN_STANCE,))
        result = resolve_campaign(
            _action(ActionType.PROPAGANDIZE, CLASS, mode="election:run"),
            _org_attrs(run_graph),
            run_graph,
            services,
        )
        run_edge = run_graph.get_edge(ORG, CLASS, EdgeType.SOLIDARITY.value)
        assert run_edge is not None
        run_strength = float(run_edge.attributes["solidarity_strength"])

        efficiency = services.defines.politics.debs_solidarity_efficiency
        assert result.success is True
        assert result.direct_effects["election_mode"] == "election:run"
        assert 0.0 < run_strength < base_strength
        assert run_strength == pytest.approx(base_strength * efficiency)

    def test_run_keeps_the_five_factor_consciousness_pathway(self) -> None:
        graph = _graph(acquired=(_RUN_STANCE,))
        result = resolve_campaign(
            _action(ActionType.PROPAGANDIZE, CLASS, mode="election:run"),
            _org_attrs(graph),
            graph,
            _services(),
        )
        assert result.consciousness_delta is not None


class TestCampaignElectionBoycott:
    """Abstention converts broken hope; where hope is intact it only isolates."""

    def test_boycott_without_a_live_window_converts_nothing(self) -> None:
        graph = _graph(acquired=(_BOYCOTT_STANCE,))
        before = float(graph.nodes[CLASS]["ideology"]["agitation"])
        result = resolve_campaign(
            _action(ActionType.PROPAGANDIZE, CLASS, mode="election:boycott"),
            _org_attrs(graph),
            graph,
            _services(),
        )
        assert result.success is True
        assert result.direct_effects["disillusion_window_live"] is False
        assert result.direct_effects["boycott_conversion"] == 0.0
        assert float(graph.nodes[CLASS]["ideology"]["agitation"]) == before

    def test_boycott_into_a_live_window_routes_agitation(self) -> None:
        services = _services()
        graph = _graph(acquired=(_BOYCOTT_STANCE,))
        graph.set_graph_attr(
            "electoral_disillusion",
            {CLASS: {"opened_tick": 3, "window_ticks": 7, "bridges_present": True}},
        )
        before = float(graph.nodes[CLASS]["ideology"]["agitation"])

        result = resolve_campaign(
            _action(ActionType.PROPAGANDIZE, CLASS, mode="election:boycott"),
            _org_attrs(graph),
            graph,
            services,
        )

        conversion = services.defines.politics.boycott_conversion
        assert result.direct_effects["disillusion_window_live"] is True
        assert result.direct_effects["agitation_delta"] == pytest.approx(conversion)
        assert float(graph.nodes[CLASS]["ideology"]["agitation"]) == pytest.approx(
            before + conversion
        )

    def test_boycott_always_pays_the_sect_isolation_price(self) -> None:
        """The MASS_LINK decay fires whether or not the conversion lands."""
        services = _services()
        graph = _graph(acquired=(_BOYCOTT_STANCE,), mass_link=0.5)
        result = resolve_campaign(
            _action(ActionType.PROPAGANDIZE, CLASS, mode="election:boycott"),
            _org_attrs(graph),
            graph,
            services,
        )
        rate = services.defines.politics.sect_isolation_rate
        assert result.direct_effects["mass_link_decay"] == pytest.approx(rate)
        assert float(graph.nodes[ORG]["doctrine_tags"][DoctrineTag.MASS_LINK]) == pytest.approx(
            0.5 - rate
        )

    def test_sect_isolation_never_drives_mass_link_negative(self) -> None:
        graph = _graph(acquired=(_BOYCOTT_STANCE,), mass_link=0.0)
        result = resolve_campaign(
            _action(ActionType.PROPAGANDIZE, CLASS, mode="election:boycott"),
            _org_attrs(graph),
            graph,
            _services(),
        )
        assert result.direct_effects["mass_link_decay"] == 0.0

    def test_boycott_is_refused_without_the_stance(self) -> None:
        graph = _graph(acquired=(_RUN_STANCE,))
        result = resolve_campaign(
            _action(ActionType.PROPAGANDIZE, CLASS, mode="election:boycott"),
            _org_attrs(graph),
            graph,
            _services(),
        )
        assert result.success is False
        assert "campaign:election:boycott" in (result.failure_reason or "")


class TestNegotiateCoalition:
    """Entryism buys a seat it cannot win, and owes the host for it."""

    def test_coalition_needs_no_leverage_but_stamps_co_optive(self) -> None:
        services = _services()
        graph = _graph(acquired=(_ENTRY_STANCE,))
        graph.update_node(ORG, cadre_level=0.0, cohesion=0.0)  # zero leverage

        result = resolve_negotiate(
            _action(ActionType.PROPOSE_ALLIANCE, HOST, mode="coalition"),
            _org_attrs(graph),
            graph,
            services,
        )

        assert result.success is True
        assert result.direct_effects["edge_mode"] == EdgeMode.CO_OPTIVE.value
        edge = graph.get_edge_data(ORG, HOST)
        assert edge is not None
        assert edge["edge_mode"] == EdgeMode.CO_OPTIVE.value
        assert edge["co_optive_dependence"] == pytest.approx(
            services.defines.politics.entryism_cooptation_rate
        )

    def test_repeat_entry_accrues_dependence(self) -> None:
        services = _services()
        graph = _graph(acquired=(_ENTRY_STANCE,))
        action = _action(ActionType.PROPOSE_ALLIANCE, HOST, mode="coalition")
        resolve_negotiate(action, _org_attrs(graph), graph, services)
        second = resolve_negotiate(action, _org_attrs(graph), graph, services)
        rate = services.defines.politics.entryism_cooptation_rate
        assert second.direct_effects["co_optive_dependence"] == pytest.approx(2 * rate)

    def test_coalition_is_refused_without_the_stance(self) -> None:
        graph = _graph(acquired=(_RUN_STANCE,))
        result = resolve_negotiate(
            _action(ActionType.PROPOSE_ALLIANCE, HOST, mode="coalition"),
            _org_attrs(graph),
            graph,
            _services(),
        )
        assert result.success is False
        assert "negotiate:coalition" in (result.failure_reason or "")
        assert graph.get_edge_data(ORG, HOST) is None

    def test_base_negotiate_path_is_untouched_by_the_sub_mode(self) -> None:
        """No ``mode`` param => the pre-U11 leverage-gated flip, unchanged."""
        graph = _graph()
        result = resolve_negotiate(
            _action(ActionType.PROPOSE_ALLIANCE, HOST),
            _org_attrs(graph),
            graph,
            _services(),
        )
        assert result.success is True
        assert result.direct_effects["edge_created"] is True
        edge = graph.get_edge_data(ORG, HOST)
        assert edge is not None
        assert "edge_mode" not in edge


class TestMobilizeCanvass:
    """The surge is real; the power is discounted."""

    def test_canvass_mints_membership_at_the_paper_weight(self) -> None:
        services = _services()
        graph = _graph(acquired=(_ENTRY_STANCE,))
        result = resolve_mobilize(
            _action(ActionType.PROTEST, CLASS, sub_mode="canvass", sl_committed=1.0),
            _org_attrs(graph),
            graph,
            services,
        )
        weight = services.defines.politics.entryism_membership_weight
        assert result.success is True
        assert result.direct_effects["membership_minted"] == pytest.approx(
            result.direct_effects["turnout"] * weight
        )
        edge = graph.get_edge(ORG, CLASS, EdgeType.MEMBERSHIP.value)
        assert edge is not None
        assert float(edge.attributes["membership_weight"]) == pytest.approx(
            result.direct_effects["membership_minted"]
        )

    def test_canvass_writes_no_heat_and_no_agitation(self) -> None:
        """Fieldwork is not a demonstration — it makes lists, not heat."""
        graph = _graph(acquired=(_ENTRY_STANCE,))
        before = float(graph.nodes[CLASS]["ideology"]["agitation"])
        resolve_mobilize(
            _action(ActionType.PROTEST, CLASS, sub_mode="canvass"),
            _org_attrs(graph),
            graph,
            _services(),
        )
        assert float(graph.nodes[CLASS]["ideology"]["agitation"]) == before

    def test_canvass_is_refused_without_the_membership_capability(self) -> None:
        graph = _graph(acquired=(_RUN_STANCE,))
        result = resolve_mobilize(
            _action(ActionType.PROTEST, CLASS, sub_mode="canvass"),
            _org_attrs(graph),
            graph,
            _services(),
        )
        assert result.success is False
        assert "membership" in (result.failure_reason or "")
        assert graph.get_edge(ORG, CLASS, EdgeType.MEMBERSHIP.value) is None

    def test_canvass_refuses_to_clobber_a_foreign_edge(self) -> None:
        graph = _graph(acquired=(_ENTRY_STANCE,))
        graph.add_edge(ORG, CLASS, edge_type=EdgeType.SOLIDARITY.value, solidarity_strength=0.4)
        result = resolve_mobilize(
            _action(ActionType.PROTEST, CLASS, sub_mode="canvass"),
            _org_attrs(graph),
            graph,
            _services(),
        )
        assert result.success is False
        assert "clobber" in (result.failure_reason or "")
        solidarity = graph.get_edge(ORG, CLASS, EdgeType.SOLIDARITY.value)
        assert solidarity is not None
        assert float(solidarity.attributes["solidarity_strength"]) == pytest.approx(0.4)

    def test_unknown_sub_mode_is_refused(self) -> None:
        graph = _graph(acquired=(_ENTRY_STANCE,))
        result = resolve_mobilize(
            _action(ActionType.PROTEST, CLASS, sub_mode="doorknock"),
            _org_attrs(graph),
            graph,
            _services(),
        )
        assert result.success is False
        assert "unknown sub_mode" in (result.failure_reason or "")

    def test_base_mobilize_path_is_untouched_by_the_sub_mode(self) -> None:
        graph = _graph()
        result = resolve_mobilize(
            _action(ActionType.PROTEST, CLASS, sl_committed=1.0),
            _org_attrs(graph),
            graph,
            _services(),
        )
        assert result.success is True
        assert "turnout" in result.direct_effects
        assert graph.get_edge(ORG, CLASS, EdgeType.MEMBERSHIP.value) is None
