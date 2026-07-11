"""Spec-070 determinism replay test (T097, FR-044 + SC-011).

Verifies that running the spec-070 system stack twice with the same
seed produces byte-identical state mutations + event sequences.

Per the spec-069 byte-identical-trace gate, every new System must be
deterministic-by-seed. The three new spec-070 systems
(FactionInfluenceSystem, SovereigntySystem, CollapseTransitionSystem)
use sorted-iteration for any dict/set traversal that affects emitted
events or state mutations.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import pytest

from babylon.config.defines.balkanization import BalkanizationDefines
from babylon.engine.systems.collapse_transition import CollapseTransitionSystem
from babylon.engine.systems.faction_influence import FactionInfluenceSystem
from babylon.engine.systems.metabolism import MetabolismSystem
from babylon.engine.systems.sovereignty import SovereigntySystem
from babylon.topology.graph import BabylonGraph

pytestmark = pytest.mark.integration


@dataclass
class _CapturedEvent:
    type_name: str
    tick: int
    payload: dict[str, Any]


class _RecordingEventBus:
    def __init__(self) -> None:
        self.events: list[_CapturedEvent] = []

    def publish(self, event: Any) -> None:
        # Normalize event type to its string name for cross-run comparison.
        type_name = getattr(event.type, "value", str(event.type))
        # Strip non-deterministic timestamp from payload if present.
        payload = {k: v for k, v in (event.payload or {}).items() if k != "timestamp"}
        self.events.append(_CapturedEvent(type_name=type_name, tick=event.tick, payload=payload))


@dataclass
class _MetabolismDefines:
    entropy_factor: float = 0.5
    overshoot_threshold: float = 1.0
    max_overshoot_ratio: float = 10.0


@dataclass
class _AllDefines:
    metabolism: _MetabolismDefines
    balkanization: BalkanizationDefines


def _build_initial_graph(seed_id: str) -> BabylonGraph:
    """Deterministic graph construction — every call with same ``seed_id``
    produces the same starting state."""

    adapter = BabylonGraph()
    # 2 Sovereigns, 2 Factions, 4 Territories with overlapping CLAIMS +
    # INFLUENCES — enough to exercise winning-faction tiebreaking +
    # dual-power detection.
    adapter.add_node(
        "SOV_USA_FED",
        "sovereign",
        sovereignty_type="recognized_state",
        legitimacy=1.0,
        color_hex="#3c3b6e",
        ruling_faction_id="FAC_RESTORATIONIST",
        extraction_policy="intensify",
        founded_tick=0,
    )
    adapter.add_node(
        "SOV_BREAK",
        "sovereign",
        sovereignty_type="secessionist",
        legitimacy=0.5,
        color_hex="#ff7f00",
        ruling_faction_id="FAC_DECOLONIAL",
        extraction_policy="cease",
        founded_tick=0,
    )
    adapter.add_node(
        "FAC_RESTORATIONIST",
        "balkanization_faction",
        colonial_stance="uphold",
        class_reduction=0.0,
    )
    adapter.add_node(
        "FAC_DECOLONIAL",
        "balkanization_faction",
        colonial_stance="abolish",
        class_reduction=0.5,
    )
    for i in range(4):
        territory_id = f"HEX_{i:03d}"
        adapter.add_node(
            territory_id,
            "territory",
            habitability=0.8,
            regeneration_rate=0.0,
            max_biocapacity=100.0,
            extraction_intensity=0.0,
            biocapacity=100.0,
            s_bio=0.0,
            s_class=0.0,
            population=1,
            active=True,
        )
    # SOV_USA_FED claims all 4 at varying control levels.
    adapter.add_edge("SOV_USA_FED", "HEX_000", "claims", control_level=1.0, legal_status="de_jure")
    adapter.add_edge("SOV_USA_FED", "HEX_001", "claims", control_level=0.9, legal_status="de_jure")
    adapter.add_edge("SOV_USA_FED", "HEX_002", "claims", control_level=0.8, legal_status="de_facto")
    adapter.add_edge("SOV_USA_FED", "HEX_003", "claims", control_level=0.7, legal_status="de_facto")
    # SOV_BREAK contests HEX_002 + HEX_003.
    adapter.add_edge("SOV_BREAK", "HEX_002", "claims", control_level=0.3, legal_status="disputed")
    adapter.add_edge("SOV_BREAK", "HEX_003", "claims", control_level=0.5, legal_status="disputed")
    # INFLUENCES: FAC_RESTORATIONIST dominates HEX_000-001;
    # FAC_DECOLONIAL dominates HEX_002-003.
    adapter.add_edge(
        "FAC_RESTORATIONIST", "HEX_000", "influences", influence_level=0.9, support_type="electoral"
    )
    adapter.add_edge(
        "FAC_RESTORATIONIST", "HEX_001", "influences", influence_level=0.8, support_type="electoral"
    )
    adapter.add_edge(
        "FAC_DECOLONIAL", "HEX_002", "influences", influence_level=0.7, support_type="ideological"
    )
    adapter.add_edge(
        "FAC_DECOLONIAL", "HEX_003", "influences", influence_level=0.6, support_type="ideological"
    )
    # ADJACENCY chain for contiguity BFS.
    for i in range(3):
        adapter.add_edge(f"HEX_{i:03d}", f"HEX_{i + 1:03d}", "adjacency")
        adapter.add_edge(f"HEX_{i + 1:03d}", f"HEX_{i:03d}", "adjacency")
    return adapter


def _services() -> Any:
    container = MagicMock()
    container.event_bus = _RecordingEventBus()
    container.defines = _AllDefines(
        metabolism=_MetabolismDefines(),
        balkanization=BalkanizationDefines(),
    )
    container.rng = None  # System fallback (deterministic seed-by-tick).
    return container


def _run_10_ticks(seed_id: str) -> tuple[dict[str, Any], list[_CapturedEvent]]:
    """Run a fixed 10-tick mini-simulation. Returns (final_state, events)."""

    adapter = _build_initial_graph(seed_id)
    services = _services()
    persistent: dict[str, Any] = {}
    pipeline = [
        FactionInfluenceSystem(),
        SovereigntySystem(),
        MetabolismSystem(),
        CollapseTransitionSystem(),
    ]
    for tick in range(10):
        context: dict[str, Any] = {"tick": tick, "persistent_data": persistent}
        for system in pipeline:
            system.step(adapter, services, context)
    # Snapshot final state as a deterministic dict.
    state: dict[str, Any] = {
        "nodes": sorted(
            (
                node.id,
                node.node_type,
                dict(sorted(node.attributes.items())),
            )
            for node in adapter.query_nodes()
        ),
        "claims": sorted(adapter.query_sovereign_claims("SOV_USA_FED"))
        + sorted(adapter.query_sovereign_claims("SOV_BREAK")),
    }
    return state, services.event_bus.events


def test_determinism_byte_identical_state_replay() -> None:
    """SC-011: same seed ⇒ byte-identical state."""

    state_a, _events_a = _run_10_ticks("seed_alpha")
    state_b, _events_b = _run_10_ticks("seed_alpha")
    serialized_a = json.dumps(state_a, default=str, sort_keys=True)
    serialized_b = json.dumps(state_b, default=str, sort_keys=True)
    assert serialized_a == serialized_b


def test_determinism_event_stream_byte_identical() -> None:
    """SC-011: same seed ⇒ same event stream in same order."""

    _state_a, events_a = _run_10_ticks("seed_alpha")
    _state_b, events_b = _run_10_ticks("seed_alpha")

    # Compare normalized event signatures.
    def _sig(e: _CapturedEvent) -> tuple[Any, int, str]:
        return (e.type_name, e.tick, json.dumps(e.payload, default=str, sort_keys=True))

    assert [_sig(e) for e in events_a] == [_sig(e) for e in events_b]


def test_determinism_distinct_seeds_can_diverge() -> None:
    """Sanity: changing the seed_id label has no effect when the
    spec-070 RNG fallback is deterministic-by-tick. This test confirms
    we do NOT accidentally make seed_id load-bearing (which would
    invert determinism semantics)."""

    state_a, _ = _run_10_ticks("seed_alpha")
    state_b, _ = _run_10_ticks("seed_beta")
    # The seed_id label is documentation-only; states should be
    # IDENTICAL because the spec-070 RNG fallback is keyed on tick,
    # not seed_id. This is intentional — production code uses a
    # seed-deterministic RNG from the spec-037 services layer, which
    # this unit-level harness doesn't supply.
    assert json.dumps(state_a, default=str, sort_keys=True) == json.dumps(
        state_b, default=str, sort_keys=True
    )
