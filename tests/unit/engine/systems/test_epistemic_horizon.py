"""Tests for EpistemicHorizonSystem — Phase 1 SHADOW ONLY (fog of war).

Program: project/research/epistemic-horizon-program-proposal.md.
Formulas + worked examples: ai/epochs/epoch3/fog-of-war.yaml lines 86-330.

Phase 1 scope (binding): shadow attrs only. NO masking, NO reveal gating,
NO Investigate changes. The system computes ``mass_receptivity`` (M_r),
``intel_confidence`` (I_c), and ``vision_state`` per territory and writes
them as transient graph attrs — nothing reads them back yet.

Constitution III.11 honest-null: a territory with no tenant classes (or
only zero-population tenants) gets NO shadow attrs at all — never a
fabricated 0.0.
"""

from __future__ import annotations

import pytest

from babylon.config.defines import GameDefines
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.epistemic_horizon import EpistemicHorizonSystem
from babylon.models.enums import EdgeType
from babylon.topology.graph import BabylonGraph

pytestmark = pytest.mark.unit


def _territory(graph: BabylonGraph, tid: str) -> None:
    graph.add_node(tid, _node_type="territory", id=tid, name=tid)


def _tenant(
    graph: BabylonGraph,
    cid: str,
    tid: str,
    *,
    role: str,
    population: float,
    p_acquiescence: float,
    class_consciousness: float,
) -> None:
    """Add a social_class node TENANCY-linked to ``tid``.

    Mirrors ``TerritorySystem._suppress_organization``'s TENANCY resolution
    (source=class, target=territory) — the engine-side precedent for
    class<->territory membership.
    """
    graph.add_node(
        cid,
        _node_type="social_class",
        id=cid,
        role=role,
        population=population,
        p_acquiescence=p_acquiescence,
        ideology={
            "class_consciousness": class_consciousness,
            "national_identity": 0.5,
            "agitation": 0.0,
        },
    )
    graph.add_edge(cid, tid, edge_type=EdgeType.TENANCY)


def _player_org_presence(graph: BabylonGraph, org_id: str, tid: str, *, is_player: bool) -> None:
    graph.add_node(org_id, _node_type="organization", id=org_id, is_player=is_player)
    graph.add_edge(org_id, tid, edge_type=EdgeType.PRESENCE)


class TestDefinesDefaults:
    """The EpistemicHorizonDefines category matches the corpus's stated values."""

    def test_defaults_match_corpus(self) -> None:
        defines = GameDefines().epistemic_horizon
        assert defines.base_observation == 0.1
        assert defines.desert_threshold == 0.2
        assert defines.water_threshold == 0.8
        assert defines.class_factor_periphery_proletariat == 1.0
        assert defines.class_factor_lumpenproletariat == 1.0
        assert defines.class_factor_petty_bourgeoisie == 0.3
        assert defines.class_factor_labor_aristocracy == 0.2
        assert defines.class_factor_default == 0.0


class TestMassReceptivityWorkedExamples:
    """The corpus's three worked M_r examples (fog-of-war.yaml:238-262)."""

    def test_proletarian_slum_is_mud(self) -> None:
        """(1 - 0.2) * 0.7 * 1.0 = 0.56 -> Mud (corpus: 'Mud/Contested')."""
        graph = BabylonGraph()
        _territory(graph, "T001")
        _tenant(
            graph,
            "C001",
            "T001",
            role="periphery_proletariat",
            population=1000.0,
            p_acquiescence=0.2,
            class_consciousness=0.7,
        )
        services = ServiceContainer.create()
        EpistemicHorizonSystem().step(graph, services, {})

        attrs = graph.get_node("T001").attributes
        assert attrs["mass_receptivity"] == pytest.approx(0.56)
        assert attrs["vision_state"] == "mud"

    def test_labor_aristocracy_suburb_is_desert(self) -> None:
        """(1 - 0.9) * 0.3 * 0.2 = 0.006 -> Desert (corpus: 'hostile territory')."""
        graph = BabylonGraph()
        _territory(graph, "T001")
        _tenant(
            graph,
            "C001",
            "T001",
            role="labor_aristocracy",
            population=1000.0,
            p_acquiescence=0.9,
            class_consciousness=0.3,
        )
        services = ServiceContainer.create()
        EpistemicHorizonSystem().step(graph, services, {})

        attrs = graph.get_node("T001").attributes
        assert attrs["mass_receptivity"] == pytest.approx(0.006)
        assert attrs["vision_state"] == "desert"

    def test_base_area_is_mud_not_water_per_threshold_table(self) -> None:
        """(1 - 0.3) * 0.95 * 1.0 = 0.665.

        The corpus's prose calls this example "Water" (fog-of-war.yaml:260),
        but its OWN threshold table (fog-of-war.yaml:264-330) requires
        M_r >= 0.8 for Water. 0.665 < 0.8, so the threshold table this
        system implements literally places it in Mud instead. This is a
        flagged corpus-internal inconsistency (see program report), not an
        implementation bug — we implement the table, not the prose label.
        """
        graph = BabylonGraph()
        _territory(graph, "T001")
        _tenant(
            graph,
            "C001",
            "T001",
            role="periphery_proletariat",
            population=1000.0,
            p_acquiescence=0.3,
            class_consciousness=0.95,
        )
        services = ServiceContainer.create()
        EpistemicHorizonSystem().step(graph, services, {})

        attrs = graph.get_node("T001").attributes
        assert attrs["mass_receptivity"] == pytest.approx(0.665)
        assert attrs["vision_state"] == "mud"  # NOT "water" -- see docstring above


class TestIntelConfidence:
    """I_c = B_o + (C_p * M_r), clamped [0, 1]."""

    def test_intel_confidence_with_player_cadre_presence(self) -> None:
        graph = BabylonGraph()
        _territory(graph, "T001")
        _tenant(
            graph,
            "C001",
            "T001",
            role="periphery_proletariat",
            population=1000.0,
            p_acquiescence=0.2,
            class_consciousness=0.7,
        )
        _player_org_presence(graph, "ORG001", "T001", is_player=True)

        services = ServiceContainer.create()
        EpistemicHorizonSystem().step(graph, services, {})

        attrs = graph.get_node("T001").attributes
        assert attrs["intel_confidence"] == pytest.approx(0.1 + 0.56)

    def test_intel_confidence_without_any_presence_is_base_observation_only(self) -> None:
        graph = BabylonGraph()
        _territory(graph, "T001")
        _tenant(
            graph,
            "C001",
            "T001",
            role="periphery_proletariat",
            population=1000.0,
            p_acquiescence=0.2,
            class_consciousness=0.7,
        )

        services = ServiceContainer.create()
        EpistemicHorizonSystem().step(graph, services, {})

        attrs = graph.get_node("T001").attributes
        assert attrs["intel_confidence"] == pytest.approx(0.1)

    def test_non_player_org_presence_does_not_grant_cadre_presence(self) -> None:
        """A PRESENCE edge from a non-player org (e.g. the State's police
        org) must NOT contribute C_p — only PLAYER-CONTROLLED orgs do."""
        graph = BabylonGraph()
        _territory(graph, "T001")
        _tenant(
            graph,
            "C001",
            "T001",
            role="periphery_proletariat",
            population=1000.0,
            p_acquiescence=0.2,
            class_consciousness=0.7,
        )
        _player_org_presence(graph, "ORG002", "T001", is_player=False)

        services = ServiceContainer.create()
        EpistemicHorizonSystem().step(graph, services, {})

        attrs = graph.get_node("T001").attributes
        assert attrs["intel_confidence"] == pytest.approx(0.1)


class TestHonestAbsence:
    """Constitution III.11: no tenant classes -> no fabricated 0.0."""

    def test_tenant_less_territory_gets_no_shadow_attrs(self) -> None:
        graph = BabylonGraph()
        _territory(graph, "T001")

        services = ServiceContainer.create()
        EpistemicHorizonSystem().step(graph, services, {})

        attrs = graph.get_node("T001").attributes
        assert "mass_receptivity" not in attrs
        assert "intel_confidence" not in attrs
        assert "vision_state" not in attrs

    def test_zero_population_tenant_is_treated_as_tenant_less(self) -> None:
        graph = BabylonGraph()
        _territory(graph, "T001")
        _tenant(
            graph,
            "C001",
            "T001",
            role="periphery_proletariat",
            population=0.0,
            p_acquiescence=0.2,
            class_consciousness=0.7,
        )

        services = ServiceContainer.create()
        EpistemicHorizonSystem().step(graph, services, {})

        attrs = graph.get_node("T001").attributes
        assert "mass_receptivity" not in attrs


class TestClassFactorDefault:
    """Roles absent from the corpus's 4-entry table get the explicit default."""

    def test_role_absent_from_corpus_table_uses_explicit_default(self) -> None:
        """CORE_BOURGEOISIE is not one of the corpus's named class factors
        (proletariat / lumpenproletariat / petty_bourgeoisie / labor_aristocracy);
        it must fall through to ``class_factor_default`` (0.0), never
        silently inherit 1.0 or 0.3."""
        graph = BabylonGraph()
        _territory(graph, "T001")
        _tenant(
            graph,
            "C001",
            "T001",
            role="core_bourgeoisie",
            population=1000.0,
            p_acquiescence=0.1,
            class_consciousness=0.9,
        )

        services = ServiceContainer.create()
        EpistemicHorizonSystem().step(graph, services, {})

        attrs = graph.get_node("T001").attributes
        assert attrs["mass_receptivity"] == pytest.approx(0.0)
        assert attrs["vision_state"] == "desert"


class TestPopulationWeighting:
    """M_r is a population-weighted mean across all tenant classes."""

    def test_population_weighted_mean_across_two_tenant_classes(self) -> None:
        graph = BabylonGraph()
        _territory(graph, "T001")
        # C001: class M_r = (1-0)*1.0*1.0 = 1.0, weight 100
        _tenant(
            graph,
            "C001",
            "T001",
            role="lumpenproletariat",
            population=100.0,
            p_acquiescence=0.0,
            class_consciousness=1.0,
        )
        # C002: class M_r = (1-1)*0.0*0.2 = 0.0, weight 300
        _tenant(
            graph,
            "C002",
            "T001",
            role="labor_aristocracy",
            population=300.0,
            p_acquiescence=1.0,
            class_consciousness=0.0,
        )

        services = ServiceContainer.create()
        EpistemicHorizonSystem().step(graph, services, {})

        attrs = graph.get_node("T001").attributes
        # (1.0*100 + 0.0*300) / 400 = 0.25
        assert attrs["mass_receptivity"] == pytest.approx(0.25)


class TestDeterminism:
    """Constitution III.7: pure deterministic computation, no RNG."""

    def test_two_runs_produce_identical_shadow_attrs(self) -> None:
        def build() -> BabylonGraph:
            graph = BabylonGraph()
            _territory(graph, "T001")
            _tenant(
                graph,
                "C001",
                "T001",
                role="periphery_proletariat",
                population=1000.0,
                p_acquiescence=0.2,
                class_consciousness=0.7,
            )
            _player_org_presence(graph, "ORG001", "T001", is_player=True)
            return graph

        services = ServiceContainer.create()
        g1 = build()
        EpistemicHorizonSystem().step(g1, services, {})
        g2 = build()
        EpistemicHorizonSystem().step(g2, services, {})

        a1 = g1.get_node("T001").attributes
        a2 = g2.get_node("T001").attributes
        assert a1["mass_receptivity"] == a2["mass_receptivity"]
        assert a1["intel_confidence"] == a2["intel_confidence"]
        assert a1["vision_state"] == a2["vision_state"]


class TestPlayerOrgIdChannel:
    """EH ruling 6 (owner 2026-07-16): C_p becomes player-relative via
    ``WorldState.player_org_id`` riding graph metadata — no per-org flag
    needed. The legacy ``is_player`` attr path stays honored (PoliticalFaction
    already exposes it)."""

    def _mud_tenant_graph(self) -> BabylonGraph:
        graph = BabylonGraph()
        _territory(graph, "T001")
        _tenant(
            graph,
            "C001",
            "T001",
            role="periphery_proletariat",
            population=1000.0,
            p_acquiescence=0.2,
            class_consciousness=0.7,
        )
        return graph

    def test_player_org_id_metadata_grants_cadre_presence(self) -> None:
        """An org WITHOUT is_player still counts as C_p=1 when it IS the
        player org per graph metadata: I_c = 0.1 + 1.0*0.56 = 0.66."""
        graph = self._mud_tenant_graph()
        graph.add_node("ORG001", _node_type="organization", id="ORG001")
        graph.add_edge("ORG001", "T001", edge_type=EdgeType.PRESENCE)
        graph.graph["player_org_id"] = "ORG001"

        EpistemicHorizonSystem().step(graph, ServiceContainer.create(), {"tick": 1})

        assert graph.nodes["T001"]["intel_confidence"] == pytest.approx(0.66)

    def test_non_player_org_presence_does_not_grant_cp(self) -> None:
        """A different org's PRESENCE edge is not the player's eyes:
        I_c stays at base_observation 0.1."""
        graph = self._mud_tenant_graph()
        graph.add_node("ORG002", _node_type="organization", id="ORG002")
        graph.add_edge("ORG002", "T001", edge_type=EdgeType.PRESENCE)
        graph.graph["player_org_id"] = "ORG001"

        EpistemicHorizonSystem().step(graph, ServiceContainer.create(), {"tick": 1})

        assert graph.nodes["T001"]["intel_confidence"] == pytest.approx(0.1)

    def test_legacy_is_player_attr_still_honored(self) -> None:
        """PoliticalFaction's is_player=True path keeps working with NO
        metadata pointer set (backward compat with Phase 1)."""
        graph = self._mud_tenant_graph()
        _player_org_presence(graph, "ORG001", "T001", is_player=True)

        EpistemicHorizonSystem().step(graph, ServiceContainer.create(), {"tick": 1})

        assert graph.nodes["T001"]["intel_confidence"] == pytest.approx(0.66)


class TestInvestigationIntel:
    """EH Phase 2: Investigate finally raises I_c through its own channel.

    ``resolve_investigate`` (player org only) writes ``investigation_intel``
    onto the target territory; ``compute_epistemic_horizon`` adds it into
    I_c (clamped). Decay is Phase 3 — the boost persists until then
    (documented in the resolver).
    """

    def _graph(self) -> BabylonGraph:
        graph = BabylonGraph()
        _territory(graph, "T001")
        _tenant(
            graph,
            "C001",
            "T001",
            role="periphery_proletariat",
            population=1000.0,
            p_acquiescence=0.2,
            class_consciousness=0.7,
        )
        graph.add_node("ORG001", _node_type="organization", id="ORG001", cohesion=0.5)
        graph.graph["player_org_id"] = "ORG001"
        return graph

    def _investigate(self, graph: BabylonGraph, org_id: str) -> None:
        from babylon.engine.actions.investigate import resolve_investigate
        from babylon.models.enums import ActionType
        from babylon.ooda.types import Action

        action = Action(
            org_id=org_id,
            action_type=ActionType.MAP_NETWORK,
            target_id="T001",
            params={},
        )
        resolve_investigate(action, {}, graph, ServiceContainer.create())

    def test_player_investigate_writes_intel(self) -> None:
        graph = self._graph()
        self._investigate(graph, "ORG001")

        boost = GameDefines().epistemic_horizon.investigate_intel_boost
        assert graph.nodes["T001"]["investigation_intel"] == pytest.approx(boost)

    def test_non_player_investigate_writes_nothing(self) -> None:
        graph = self._graph()
        graph.add_node("ORG002", _node_type="organization", id="ORG002", cohesion=0.5)
        self._investigate(graph, "ORG002")

        assert "investigation_intel" not in graph.nodes["T001"]

    def test_intel_raises_i_c(self) -> None:
        """No PRESENCE edge (C_p=0) => I_c = base 0.1; after a player
        investigation I_c = 0.1 + boost."""
        graph = self._graph()
        system = EpistemicHorizonSystem()
        system.step(graph, ServiceContainer.create(), {"tick": 1})
        assert graph.nodes["T001"]["intel_confidence"] == pytest.approx(0.1)

        self._investigate(graph, "ORG001")
        system.step(graph, ServiceContainer.create(), {"tick": 2})

        boost = GameDefines().epistemic_horizon.investigate_intel_boost
        assert graph.nodes["T001"]["intel_confidence"] == pytest.approx(0.1 + boost)
