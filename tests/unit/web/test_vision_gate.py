"""EH Phase 2 — reveal gating at the class-inspector boundary (Wave 5).

The corpus reveal table (``ai/epochs/epoch3/fog-of-war.yaml`` §visibility):
political knowledge (agitation, organization strength, allegiance) is what
the masses hold — Desert withholds it, Mud approximates it (±0.2), Water
shows it exactly. Phase 2 is bridge/presentation-side ONLY: the persisted
snapshots keep TRUE values (the DB is the engine's ledger, not the player's
view), and Desert WITHHOLDS (None + marker) — falsification is Phase 3
(needs ruling 2). Gating applies only when a vision_state has actually been
computed for the class's territory (Constitution III.11: never gate on a
fabricated default vision).
"""

from __future__ import annotations

import pytest

from babylon.models.enums import EdgeType
from babylon.topology.graph import BabylonGraph

pytestmark = pytest.mark.unit


def _graph_with_class_in(vision_state: str | None) -> BabylonGraph:
    graph = BabylonGraph()
    territory_attrs: dict[str, object] = {"_node_type": "territory", "id": "T001"}
    if vision_state is not None:
        territory_attrs["vision_state"] = vision_state
    graph.add_node("T001", **territory_attrs)
    graph.add_node("C001", _node_type="social_class", id="C001")
    graph.add_edge("C001", "T001", edge_type=EdgeType.TENANCY)
    return graph


def _payload() -> dict[str, object]:
    return {
        "class_consciousness": 0.73,
        "national_identity": 0.41,
        "agitation": 0.57,
        "organization": 0.62,
        "p_revolution": 0.33,
        "consciousness": {"revolutionary": 0.5, "liberal": 0.3, "fascist": 0.2},
        "wealth": 120.0,
    }


class TestClassVisionState:
    def test_max_vision_across_territories(self) -> None:
        """A class tenanting a mud AND a water territory is known at WATER
        level — the masses in the best-organized territory tell you."""
        from game.engine_bridge import _class_vision_state

        graph = _graph_with_class_in("mud")
        graph.add_node("T002", _node_type="territory", id="T002", vision_state="water")
        graph.add_edge("C001", "T002", edge_type=EdgeType.TENANCY)

        assert _class_vision_state(graph, "C001") == "water"

    def test_no_computed_vision_is_none(self) -> None:
        from game.engine_bridge import _class_vision_state

        assert _class_vision_state(_graph_with_class_in(None), "C001") is None


class TestApplyClassVisionGate:
    def test_desert_withholds_political_fields(self) -> None:
        from game.engine_bridge import _apply_class_vision_gate

        payload = _payload()
        _apply_class_vision_gate(payload, "desert")

        assert payload["agitation"] is None
        assert payload["organization"] is None
        assert payload["class_consciousness"] is None
        assert payload["national_identity"] is None
        assert payload["p_revolution"] is None
        assert payload["consciousness"] is None
        assert payload["class_vision"] == "desert"
        assert "agitation" in payload["vision_masked"]
        # Material/public fields untouched:
        assert payload["wealth"] == 120.0

    def test_mud_quantizes_to_corpus_margin(self) -> None:
        """Mud = ±0.2 margin (corpus fog-of-war.yaml:335). A bucket of width
        W bounds displayed error to W/2, so the quantum is 0.4 — 0.2-wide
        buckets would ship TWICE the precision the corpus allows."""
        from game.engine_bridge import _apply_class_vision_gate

        payload = _payload()
        _apply_class_vision_gate(payload, "mud")

        assert payload["agitation"] == pytest.approx(0.4)  # 0.57 -> 0.4
        assert payload["class_consciousness"] == pytest.approx(0.8)  # 0.73 -> 0.8
        assert payload["national_identity"] == pytest.approx(0.4)  # 0.41 -> 0.4
        assert payload["organization"] == pytest.approx(0.8)  # 0.62 -> 0.8
        assert payload["p_revolution"] == pytest.approx(0.4)  # 0.33 -> 0.4
        assert payload["class_vision"] == "mud"
        assert "agitation" in payload["vision_approx"]
        assert payload["wealth"] == 120.0
        # Every displayed value sits within the corpus margin of the truth.
        for field, truth in (("agitation", 0.57), ("class_consciousness", 0.73)):
            value = payload[field]
            assert isinstance(value, float)
            assert abs(value - truth) <= 0.2

    def test_mud_quantizes_consciousness_ternary(self) -> None:
        """The ternary dict is gated with the same documented round-half-up
        rule — pinned because banker's round() flipped these boundaries by
        IEEE-754 representation accident (the 2026-07-16 verify finding)."""
        from game.engine_bridge import _apply_class_vision_gate

        payload = _payload()
        _apply_class_vision_gate(payload, "mud")

        assert payload["consciousness"] == {
            "revolutionary": pytest.approx(0.4),  # 0.5 -> 0.4 (half-up on 0.4-grid)
            "liberal": pytest.approx(0.4),  # 0.3 -> 0.4
            "fascist": pytest.approx(0.4),  # 0.2 -> 0.4
        }
        assert "consciousness" in payload["vision_approx"]

    def test_mud_boundaries_are_deterministic_and_clamped(self) -> None:
        """Round-half-up (floor(v/Q + 0.5)), clamped to [0, 1]: 1.0 must
        display as 1.0 (not the 1.2 the raw grid would produce), 0.0 as 0.0."""
        from game.engine_bridge import _apply_class_vision_gate

        payload = _payload()
        payload["agitation"] = 1.0
        payload["organization"] = 0.0
        payload["p_revolution"] = 0.2  # exact half -> rounds UP by rule
        _apply_class_vision_gate(payload, "mud")

        assert payload["agitation"] == pytest.approx(1.0)
        assert payload["organization"] == pytest.approx(0.0)
        assert payload["p_revolution"] == pytest.approx(0.4)

    def test_mud_skips_honest_null_fields(self) -> None:
        """A field that is None for honest data-absence reasons is neither
        quantized nor claimed as vision-approximated."""
        from game.engine_bridge import _apply_class_vision_gate

        payload = _payload()
        payload["agitation"] = None
        _apply_class_vision_gate(payload, "mud")

        assert payload["agitation"] is None
        assert "agitation" not in payload["vision_approx"]

    def test_desert_skips_honest_null_fields(self) -> None:
        """Desert must not claim 'the fog hid this' for a field that never
        held a value — vision_masked lists only fields the gate ACTUALLY
        withheld (the 2026-07-16 verify finding: masking an already-None
        field conflates missing data with withheld data)."""
        from game.engine_bridge import _apply_class_vision_gate

        payload = _payload()
        payload["agitation"] = None
        _apply_class_vision_gate(payload, "desert")

        assert payload["agitation"] is None
        assert "agitation" not in payload["vision_masked"]
        assert "organization" in payload["vision_masked"]
        assert payload["organization"] is None

    def test_water_is_exact_with_no_markers(self) -> None:
        from game.engine_bridge import _apply_class_vision_gate

        payload = _payload()
        _apply_class_vision_gate(payload, "water")

        assert payload["agitation"] == pytest.approx(0.57)
        assert payload["class_vision"] == "water"
        assert "vision_masked" not in payload
        assert "vision_approx" not in payload

    def test_unknown_vision_leaves_payload_exact(self) -> None:
        """No computed vision => no gate (III.11: never gate on a
        fabricated default)."""
        from game.engine_bridge import _apply_class_vision_gate

        payload = _payload()
        _apply_class_vision_gate(payload, None)

        assert payload["agitation"] == pytest.approx(0.57)
        assert "class_vision" not in payload


class TestInspectorGateEndToEnd:
    """The gate through the REAL payload builder (2026-07-16 verify finding:
    hand-built-dict unit tests never proved ``_social_class_inspector_fields``
    actually applies the gate to its own payload)."""

    def _political_graph(self, vision_state: str) -> BabylonGraph:
        graph = _graph_with_class_in(vision_state)
        graph.update_node(
            "C001",
            wealth=50.0,
            organization=0.6,
            ideology={
                "class_consciousness": 0.7,
                "national_identity": 0.3,
                "agitation": 0.5,
            },
        )
        return graph

    def test_desert_masks_through_real_inspector_payload(self) -> None:
        from game.engine_bridge import _social_class_inspector_fields

        graph = self._political_graph("desert")
        payload = _social_class_inspector_fields(dict(graph.nodes["C001"]), 10.0, graph)

        assert payload["class_vision"] == "desert"
        assert payload["agitation"] is None
        assert payload["organization"] is None
        assert payload["consciousness"] is None
        assert "agitation" in payload["vision_masked"]
        # Material/public knowledge stays visible in every vision state.
        assert payload["wealth"] == 50.0

    def test_water_is_exact_through_real_inspector_payload(self) -> None:
        from game.engine_bridge import _social_class_inspector_fields

        graph = self._political_graph("water")
        payload = _social_class_inspector_fields(dict(graph.nodes["C001"]), 10.0, graph)

        assert payload["class_vision"] == "water"
        assert payload["agitation"] == pytest.approx(0.5)
        assert payload["organization"] == pytest.approx(0.6)
        assert "vision_masked" not in payload
        assert "vision_approx" not in payload
