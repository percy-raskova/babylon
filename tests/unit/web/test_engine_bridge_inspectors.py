"""Program 17 / Item 1d: the 5 ``get_inspector_*`` bridge methods.

Red-phase (before the fix): every one of the 5 methods
(``get_inspector_node``/``org``/``community``/``edge``/``hex``) on
``EngineBridge`` unconditionally ``return {}``. This suite drives them
against a REAL ``wayne_county`` tick-0 graph (via
``game.engine_bridge._build_initial_state_for_scenario`` — the same
scenario-seeding pipeline the bridge itself uses, no mocking of engine
internals — matching the established pattern in
``tests/unit/web/test_provenance.py``), so every assertion is against real,
named scenario data (C002 Suburban Petty Bourgeoisie, C003 Wayne County
Bourgeoisie, ORG001 Wayne County Organizing Committee).
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


def _wayne_bridge() -> tuple[Any, Any]:
    from game.engine_bridge import EngineBridge, _build_initial_state_for_scenario

    state = _build_initial_state_for_scenario("wayne_county")
    graph = state.to_graph()
    mock_persistence = MagicMock()
    mock_persistence.hydrate_graph.return_value = graph
    return EngineBridge(mock_persistence), graph


def _imperial_circuit_bridge() -> tuple[Any, Any]:
    """The canonical 4-node imperial-circuit scenario (all 4 SocialRole slots
    filled: C001 periphery_proletariat, C002 comprador_bourgeoisie, C003
    core_bourgeoisie, C004 labor_aristocracy) — used by the W1.6 circuit_flows
    tests to prove all 3 hops render when a scenario actually seeds every role,
    contrasting wayne_county's partial (comprador-less) roster."""
    from game.engine_bridge import EngineBridge, _build_initial_state_for_scenario

    state = _build_initial_state_for_scenario("imperial_circuit")
    graph = state.to_graph()
    mock_persistence = MagicMock()
    mock_persistence.hydrate_graph.return_value = graph
    return EngineBridge(mock_persistence), graph


class TestGetInspectorNode:
    def test_social_class_pairs_wage_with_value_and_apologist_refutation(self) -> None:
        bridge, graph = _wayne_bridge()
        # C003 (Wayne Bourgeoisie) --WAGES--> C002 (Suburban Petty
        # Bourgeoisie, role=LABOR_ARISTOCRACY, wealth=0.65) is seeded at
        # value_flow=0.0 (tick 0); overwrite to a deterministic positive
        # gap for this test.
        graph.add_edge("C003", "C002", edge_type="wages", value_flow=1.0, tension=0.0)

        result = bridge.get_inspector_node(uuid.uuid4(), "C002")

        assert result["type"] == "social_class"
        assert result["wealth"] == pytest.approx(0.65)
        assert result["core_wages"] == pytest.approx(1.0)
        assert result["imperial_rent_gap"] == pytest.approx(0.35)
        assert "skill premium" in result["apologist_claim"]
        assert "0.35" in result["apologist_refutation"]

    def test_negative_gap_is_signed_not_clamped(self) -> None:
        """C001 (Detroit Proletariat) receives no WAGES edge at all — core
        wages 0.0, wealth 0.15 — the gap is negative (exploited, not
        subsidized). Signed, not clamped to zero (owner ruling)."""
        bridge, _graph = _wayne_bridge()

        result = bridge.get_inspector_node(uuid.uuid4(), "C001")

        assert result["core_wages"] == pytest.approx(0.0)
        assert result["wealth"] == pytest.approx(0.15)
        assert result["imperial_rent_gap"] == pytest.approx(-0.15)
        assert "no imperial subsidy" in result["apologist_refutation"].lower()

    def test_generic_fallback_for_non_social_class_node(self) -> None:
        """Organization nodes (and any other non-social_class type) fall
        through to the honest generic enum-normalized dump."""
        bridge, _graph = _wayne_bridge()

        result = bridge.get_inspector_node(uuid.uuid4(), "ORG001")

        assert result["type"] == "organization"
        assert result["id"] == "ORG001"
        assert "core_wages" not in result  # social_class-only field

    def test_unknown_node_id_returns_empty_dict(self) -> None:
        bridge, _graph = _wayne_bridge()
        assert bridge.get_inspector_node(uuid.uuid4(), "NOPE") == {}

    def test_ternary_consciousness_computed_via_the_shared_bridge_mapping(self) -> None:
        """Program 17 Wave 1 / W1.4: reuses (not duplicates) the canonical
        ``_ideology_to_ternary`` bridge mapping from
        ``babylon.persistence.county_aggregation``, fed the node's real
        ``ideology.class_consciousness``/``ideology.national_identity``.
        C002: cc=0.3, ni=0.7 -> r=0.09, f=0.49, l=0.42."""
        bridge, _graph = _wayne_bridge()

        result = bridge.get_inspector_node(uuid.uuid4(), "C002")

        assert result["consciousness"] == {
            "revolutionary": pytest.approx(0.09),
            "liberal": pytest.approx(0.42),
            "fascist": pytest.approx(0.49),
        }

    def test_ternary_consciousness_is_null_when_ideology_is_absent(self) -> None:
        """Honest null, never a fabricated 0.0-computed ternary (III.11): a
        synthetic social_class node with no ``ideology`` dict at all gets
        ``consciousness: None``, not a ternary computed from defaulted axes."""
        bridge, graph = _wayne_bridge()
        graph.add_node(
            "C999",
            _node_type="social_class",
            name="Synthetic No-Ideology Class",
            wealth=0.0,
        )

        result = bridge.get_inspector_node(uuid.uuid4(), "C999")

        assert result["consciousness"] is None

    def test_inequality_reads_the_real_graph_field(self) -> None:
        """Program 17 Wave 1 / W1.4: ``inequality`` is a real ``SocialClass``
        field (Gini coefficient, ``VitalitySystem`` reads it for attrition) —
        not a mock. Mutate the real graph attribute and prove it round-trips."""
        bridge, graph = _wayne_bridge()
        graph.nodes["C002"]["inequality"] = 0.42

        result = bridge.get_inspector_node(uuid.uuid4(), "C002")

        assert result["inequality"] == pytest.approx(0.42)

    def test_inequality_is_none_when_absent_not_a_fabricated_zero(self) -> None:
        bridge, graph = _wayne_bridge()
        graph.add_node(
            "C999",
            _node_type="social_class",
            name="Synthetic No-Inequality Class",
            wealth=0.0,
        )

        result = bridge.get_inspector_node(uuid.uuid4(), "C999")

        assert result["inequality"] is None

    def test_class_position_ships_as_a_clearly_badged_mock(self) -> None:
        """Owner's mock doctrine (Program 17 Wave 1 / W1.4): no real
        class-position taxonomy exists in the codebase yet, so the row ships
        with an explicit ``class_position_mock: True`` flag — a visible mock,
        never a fabricated value presented as real."""
        bridge, _graph = _wayne_bridge()

        result = bridge.get_inspector_node(uuid.uuid4(), "C002")

        assert result["class_position_mock"] is True
        assert isinstance(result["class_position"], str)
        assert result["class_position"] != ""


class TestGetInspectorNodeCircuitFlows:
    """Program 17 Wave 1 / W1.6: the 4-node imperial-circuit mini-Sankey data.

    Circuit membership is resolved by :class:`~babylon.models.enums.SocialRole`
    (never a hardcoded id), because scenarios rename/reuse ids — wayne_county's
    C002 is a Labor-Aristocracy-role class named "Suburban Petty Bourgeoisie",
    and wayne_county has NO comprador_bourgeoisie-role class at all.
    """

    def test_wayne_county_omits_the_missing_comprador_role(self) -> None:
        """wayne_county seeds internal_proletariat/labor_aristocracy/
        core_bourgeoisie/periphery_proletariat — no comprador_bourgeoisie.
        The periphery->comprador and comprador->core hops are honestly
        ABSENT (not fabricated); only core_bourgeoisie(C003)->
        labor_aristocracy(C002) WAGES survives as a real edge."""
        bridge, graph = _wayne_bridge()
        graph.add_edge("C003", "C002", edge_type="wages", value_flow=1.0, tension=0.0)

        result = bridge.get_inspector_node(uuid.uuid4(), "C002")

        assert result["circuit_flows"] == {
            "nodes": [
                {
                    "role": "periphery_proletariat",
                    "id": "C004",
                    "name": "Dearborn Industrial Workers",
                },
                {"role": "core_bourgeoisie", "id": "C003", "name": "Wayne County Bourgeoisie"},
                {"role": "labor_aristocracy", "id": "C002", "name": "Suburban Petty Bourgeoisie"},
            ],
            "links": [
                {
                    "source_role": "core_bourgeoisie",
                    "target_role": "labor_aristocracy",
                    "source_id": "C003",
                    "target_id": "C002",
                    "value_flow": 1.0,
                },
            ],
        }

    def test_circuit_flows_is_graph_wide_not_per_queried_node(self) -> None:
        """circuit_flows is whole-graph context for the Sankey, not scoped to
        the clicked node — querying C001 and C002 return the identical block."""
        bridge, _graph = _wayne_bridge()

        by_c001 = bridge.get_inspector_node(uuid.uuid4(), "C001")
        by_c002 = bridge.get_inspector_node(uuid.uuid4(), "C002")

        assert by_c001["circuit_flows"] == by_c002["circuit_flows"]

    def test_full_imperial_circuit_scenario_carries_all_three_hops(self) -> None:
        """The canonical ``imperial_circuit`` scenario seeds all 4 roles and
        all 3 circuit edges (EXPLOITATION/TRIBUTE/WAGES) — every node/link
        present, in canonical role order, all real (seeded) value_flow=0.0."""
        bridge, _graph = _imperial_circuit_bridge()

        result = bridge.get_inspector_node(uuid.uuid4(), "C001")

        assert result["circuit_flows"] == {
            "nodes": [
                {"role": "periphery_proletariat", "id": "C001", "name": "Periphery Worker"},
                {"role": "comprador_bourgeoisie", "id": "C002", "name": "Comprador"},
                {"role": "core_bourgeoisie", "id": "C003", "name": "Core Bourgeoisie"},
                {"role": "labor_aristocracy", "id": "C004", "name": "Labor Aristocracy"},
            ],
            "links": [
                {
                    "source_role": "periphery_proletariat",
                    "target_role": "comprador_bourgeoisie",
                    "source_id": "C001",
                    "target_id": "C002",
                    "value_flow": 0.0,
                },
                {
                    "source_role": "comprador_bourgeoisie",
                    "target_role": "core_bourgeoisie",
                    "source_id": "C002",
                    "target_id": "C003",
                    "value_flow": 0.0,
                },
                {
                    "source_role": "core_bourgeoisie",
                    "target_role": "labor_aristocracy",
                    "source_id": "C003",
                    "target_id": "C004",
                    "value_flow": 0.0,
                },
            ],
        }

    def test_unrelated_edge_types_between_role_nodes_are_not_summed_in(self) -> None:
        """imperial_circuit also seeds a CLIENT_STATE C003->C002 edge (wrong
        direction + wrong type for this hop) and a SOLIDARITY C001->C004 edge
        (wrong type) — neither should leak into the circuit's value_flow sums."""
        bridge, _graph = _imperial_circuit_bridge()

        result = bridge.get_inspector_node(uuid.uuid4(), "C001")

        link_role_pairs = {
            (link["source_role"], link["target_role"]) for link in result["circuit_flows"]["links"]
        }
        assert ("core_bourgeoisie", "comprador_bourgeoisie") not in link_role_pairs
        assert ("periphery_proletariat", "labor_aristocracy") not in link_role_pairs


class TestGetInspectorOrg:
    def test_returns_real_organization_fields_not_class_fields(self) -> None:
        bridge, _graph = _wayne_bridge()

        result = bridge.get_inspector_org(uuid.uuid4(), "ORG001")

        assert result["name"] == "Wayne County Organizing Committee"
        assert result["budget"] == pytest.approx(100.0)
        assert result["cohesion"] == pytest.approx(0.5)
        assert result["class_character"] == "proletarian"
        assert result["type"] == "civil_society"
        # Honest absence — base Organization has no wealth/ideology/
        # 3-way consciousness vector (Constitution III.11).
        assert "wealth" not in result
        assert "ideology" not in result
        assert "labor_aristocracy_ratio" not in result

    def test_attaches_vanguard_resources_for_player_org(self) -> None:
        """Program 17 Wave 1 / W1.3: ORG001 is the wayne_county player org
        (proletarian + civil_society) — same values ``_serialize_organization``
        would compute (cadre_level=0.1, cohesion=0.5, budget=100.0, heat=0.0,
        territory_count=2), reused via :class:`VanguardResources`."""
        bridge, _graph = _wayne_bridge()

        result = bridge.get_inspector_org(uuid.uuid4(), "ORG001")

        assert result["vanguard"] == {
            "cadre_labor": pytest.approx(1.0),
            "sympathizer_labor": pytest.approx(4.0),
            "reputation": None,
            "budget": pytest.approx(100.0),
            "heat": pytest.approx(0.0),
            "max_cadre_labor": pytest.approx(1.0),
            "max_sympathizer_labor": pytest.approx(5.0),
        }

    def test_vanguard_reputation_is_none_not_a_fabricated_zero(self) -> None:
        """Reputation is functionally dead (no from_organization call site
        ever passes reputation=) — never emit a fabricated 0.0."""
        bridge, _graph = _wayne_bridge()

        result = bridge.get_inspector_org(uuid.uuid4(), "ORG001")

        assert result["vanguard"]["reputation"] is None

    def test_attaches_traps_for_player_org(self) -> None:
        """Traps are computed via the SAME ``_compute_traps`` path the main
        snapshot uses — a fresh org with no action history has no active or
        game-over trap, but the full TrapDetectionResult shape is present."""
        bridge, _graph = _wayne_bridge()

        result = bridge.get_inspector_org(uuid.uuid4(), "ORG001")

        assert result["traps"] is not None
        for trap_key in ("liberal", "ultra_left", "rightist"):
            assert result["traps"][trap_key]["trap_type"] == trap_key
            assert "severity" in result["traps"][trap_key]
            assert "score" in result["traps"][trap_key]
        assert result["traps"]["active_trap"] is None
        assert result["traps"]["game_over_trap"] is None

    def test_inspector_read_does_not_persist_session_trap_state(self) -> None:
        """The inspector is a READ — it must never advance trap escalation.

        ``detect_traps`` increments ``ticks_at_moderate`` per call and
        ``_compute_traps`` persists the result, so routing the inspector
        through the persisting path would let polling escalate a MODERATE
        trap toward SEVERE independent of real tick advancement.
        """
        from game.engine_bridge import _session_trap_state

        bridge, _graph = _wayne_bridge()
        session_id = uuid.uuid4()
        try:
            bridge.get_inspector_org(session_id, "ORG001")
            bridge.get_inspector_org(session_id, "ORG001")

            assert session_id not in _session_trap_state
        finally:
            _session_trap_state.pop(session_id, None)

    def test_inspector_returns_tick_persisted_trap_state_verbatim(self) -> None:
        """When a resolved tick has already persisted trap state for the
        session, the inspector reports THAT state — no recompute, no
        ``ticks_at_moderate`` increment, no phantom severity preview."""
        from babylon.engine.trap_detection import (
            TrapDetectionResult,
            TrapSeverity,
            TrapStatus,
            TrapType,
        )
        from game.engine_bridge import _session_trap_state

        bridge, _graph = _wayne_bridge()
        session_id = uuid.uuid4()
        seeded = TrapDetectionResult(
            liberal=TrapStatus(
                trap_type=TrapType.LIBERAL,
                severity=TrapSeverity.MODERATE,
                score=0.7,
                indicators=["seeded"],
                ticks_at_moderate=2,
            ),
            ultra_left=TrapStatus(trap_type=TrapType.ULTRA_LEFT),
            rightist=TrapStatus(trap_type=TrapType.RIGHTIST),
            active_trap=TrapType.LIBERAL,
        )
        _session_trap_state[session_id] = seeded
        try:
            result = bridge.get_inspector_org(session_id, "ORG001")

            assert result["traps"] == seeded.model_dump()
            assert result["traps"]["liberal"]["ticks_at_moderate"] == 2
            assert _session_trap_state[session_id] is seeded
        finally:
            _session_trap_state.pop(session_id, None)

    def test_vanguard_and_traps_none_for_non_player_org(self) -> None:
        """A non-player org (e.g. a state apparatus) gets honest ``None`` for
        both fields — sections the frontend must render as absent, not as
        empty shells."""
        from babylon.models.enums.social import ClassCharacter, OrgType

        bridge, graph = _wayne_bridge()
        graph.add_node(
            "ORG999",
            _node_type="organization",
            name="Wayne County Sheriff's Office",
            class_character=ClassCharacter.BOURGEOIS,
            org_type=OrgType.STATE_APPARATUS,
            budget=500.0,
            cohesion=0.8,
            cadre_level=0.9,
            heat=0.1,
            territory_ids=[],
        )

        result = bridge.get_inspector_org(uuid.uuid4(), "ORG999")

        assert result["name"] == "Wayne County Sheriff's Office"
        assert result["vanguard"] is None
        assert result["traps"] is None

    def test_social_class_id_is_not_shaped_as_an_organization(self) -> None:
        """Deliberately stricter than get_org_status: a social_class id
        must not be coerced into an organization payload."""
        bridge, _graph = _wayne_bridge()
        assert bridge.get_inspector_org(uuid.uuid4(), "C002") == {}

    def test_unknown_org_id_returns_empty_dict(self) -> None:
        bridge, _graph = _wayne_bridge()
        assert bridge.get_inspector_org(uuid.uuid4(), "NOPE") == {}


class TestGetInspectorEdge:
    def test_parses_source_target_and_reports_edge_type(self) -> None:
        bridge, _graph = _wayne_bridge()

        result = bridge.get_inspector_edge(uuid.uuid4(), "C003->C002")

        assert result["edge_type"] == "wages"
        assert result["source_id"] == "C003"
        assert result["target_id"] == "C002"

    def test_solidarity_edge_carries_solidarity_strength(self) -> None:
        bridge, _graph = _wayne_bridge()

        result = bridge.get_inspector_edge(uuid.uuid4(), "C001->C004")

        assert result["edge_type"] == "solidarity"
        assert "solidarity_strength" in result

    def test_unknown_edge_returns_empty_dict(self) -> None:
        bridge, _graph = _wayne_bridge()
        assert bridge.get_inspector_edge(uuid.uuid4(), "NOPE->ALSO_NOPE") == {}


class TestGetInspectorCommunity:
    def test_reuses_solidarity_builder_with_fixed_consciousness(self) -> None:
        """Program 17 / Item 1d also fixes _social_class_stats (engine_bridge
        .py) reading a non-existent top-level `class_consciousness` key
        instead of the real nested `ideology.class_consciousness` — before
        the fix, avg_consciousness was always None."""
        bridge, graph = _wayne_bridge()
        from game.engine_bridge import _build_solidarity_communities

        communities = _build_solidarity_communities(graph)
        assert communities, "wayne_county seeds a C001<->C004 SOLIDARITY edge"
        community_id = communities[0]["id"]

        result = bridge.get_inspector_community(uuid.uuid4(), community_id)

        assert result["id"] == community_id
        # (0.6 + 0.55) / 2 for C001 (ideology=-0.2) / C004 (ideology=-0.1).
        assert result["avg_consciousness"] == pytest.approx(0.575)

    def test_unknown_community_id_returns_empty_dict(self) -> None:
        bridge, _graph = _wayne_bridge()
        assert bridge.get_inspector_community(uuid.uuid4(), "NOPE") == {}


class TestGetInspectorHex:
    def test_finds_territory_by_h3_index(self) -> None:
        bridge, _graph = _wayne_bridge()
        from game.engine_bridge import _build_initial_state_for_scenario

        state = _build_initial_state_for_scenario("wayne_county")
        territory = next(iter(state.territories.values()))

        result = bridge.get_inspector_hex(uuid.uuid4(), territory.h3_index)

        assert result["h3_index"] == territory.h3_index
        assert result["id"] == territory.id
        # Honest gap pending Program 17 / Item 1a's data landing.
        assert result["profit_rate"] is None
        assert result["imperial_rent"] is None

    def test_unknown_h3_index_returns_empty_dict(self) -> None:
        bridge, _graph = _wayne_bridge()
        assert bridge.get_inspector_hex(uuid.uuid4(), "nonexistent-h3") == {}


class TestAllFiveDegradeToEmptyDictOnUnknownId:
    """Smoke test matching the ticket's own acceptance criterion: none of
    the 5 methods should ever raise on an unknown id — an honest {}."""

    def test_all_five_return_empty_dict_not_crash(self) -> None:
        bridge, _graph = _wayne_bridge()
        assert bridge.get_inspector_node(uuid.uuid4(), "NOPE") == {}
        assert bridge.get_inspector_org(uuid.uuid4(), "NOPE") == {}
        assert bridge.get_inspector_community(uuid.uuid4(), "NOPE") == {}
        assert bridge.get_inspector_edge(uuid.uuid4(), "NOPE->ALSO_NOPE") == {}
        assert bridge.get_inspector_hex(uuid.uuid4(), "NOPE") == {}
