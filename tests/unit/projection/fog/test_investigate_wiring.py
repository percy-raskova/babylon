"""Contract tests for INVESTIGATE intel wiring (WO-40).

Write side: a successful MAP_NETWORK resolution freezes the TRUE post-tick
values of the revealed fields off the live graph — frozen forever after,
never recomputed at a later fog read (that distinction is the whole point
of the staleness tiers). Read side: the ledger reconstructs
deterministically from persisted ``action_result`` rows — a worker restart
rebuilds the exact same ledger, and partial rows are skipped, never
fabricated into entries (Constitution III.11). Ports the disabled
``test_engine_bridge.py::TestInvestigateFieldSnapshot`` /
``TestDeriveIntelLedger*`` assertions.
"""

from __future__ import annotations

from typing import Any

from babylon.config.defines import GameDefines
from babylon.models.enums import ActionType
from babylon.models.enums.topology import NodeType
from babylon.projection.fog.filter import political_field_group
from babylon.projection.fog.investigate import (
    INTEL_FIELD_GROUP_KEY,
    INTEL_VALUE_SNAPSHOT_KEY,
    derive_intel_ledger,
    investigate_field_snapshot,
    stash_intel_details,
)
from babylon.projection.fog.ledger import read_intel
from babylon.topology import BabylonGraph

TARGET = "T001"


def _graph(**attrs: Any) -> BabylonGraph:
    graph = BabylonGraph()
    graph.add_node(TARGET, NodeType.TERRITORY, heat=0.42, rent_level=0.7, **attrs)
    return graph


def _revealed(*fields: str) -> dict[str, Any]:
    return {"scan_type": "network", "revealed": {TARGET: list(fields)}}


class TestInvestigateFieldSnapshot:
    def test_successful_investigate_freezes_true_post_tick_values(self) -> None:
        graph = _graph()
        snapshot = investigate_field_snapshot(
            ActionType.MAP_NETWORK, TARGET, _revealed("heat", "rent_level"), graph
        )
        assert snapshot is not None
        assert snapshot["value_snapshot"] == {"heat": 0.42, "rent_level": 0.7}

        # Frozen: mutating the graph afterwards must not touch the snapshot.
        graph.update_node(TARGET, heat=0.99)
        assert snapshot["value_snapshot"]["heat"] == 0.42

    def test_field_group_comes_from_the_target_node_type(self) -> None:
        snapshot = investigate_field_snapshot(
            ActionType.MAP_NETWORK, TARGET, _revealed("heat"), _graph()
        )
        assert snapshot is not None
        assert snapshot["field_group"]  # the fog filter's group for territory

    def test_non_investigate_actions_yield_no_snapshot(self) -> None:
        assert (
            investigate_field_snapshot(ActionType.EDUCATE, TARGET, _revealed("heat"), _graph())
            is None
        )

    def test_failed_investigate_with_no_revealed_fields_yields_none(self) -> None:
        assert investigate_field_snapshot(ActionType.MAP_NETWORK, TARGET, {}, _graph()) is None

    def test_since_removed_target_yields_none(self) -> None:
        assert (
            investigate_field_snapshot(
                ActionType.MAP_NETWORK, "T-gone", {"revealed": {"T-gone": ["heat"]}}, _graph()
            )
            is None
        )

    def test_revealed_fields_absent_from_the_node_yield_none(self) -> None:
        assert (
            investigate_field_snapshot(
                ActionType.MAP_NETWORK, TARGET, _revealed("no_such_field"), _graph()
            )
            is None
        )


class TestStashAndDerive:
    """The persisted-details round trip: stash → rows → ledger."""

    def _row(self, tick: int, snapshot: dict[str, Any] | None) -> dict[str, Any]:
        details = stash_intel_details(snapshot) if snapshot else {}
        return {"tick": tick, "target_id": TARGET, "details": details}

    def test_round_trip_reconstructs_the_ledger_deterministically(self) -> None:
        snapshot = investigate_field_snapshot(
            ActionType.MAP_NETWORK, TARGET, _revealed("heat"), _graph()
        )
        rows = [self._row(3, snapshot)]

        first = derive_intel_ledger(rows)
        second = derive_intel_ledger(rows)  # the "worker restart"
        assert first == second

        horizon = GameDefines().epistemic_horizon
        reading = read_intel(
            first,
            TARGET,
            political_field_group(NodeType.TERRITORY.value),
            tick=3,
            staleness_ticks=horizon.intel_staleness_ticks,
            unknown_ticks=horizon.intel_unknown_ticks,
        )
        assert reading.tier == "exact"
        assert reading.value_snapshot is not None
        assert reading.value_snapshot["heat"] == 0.42

    def test_rows_without_intel_details_are_skipped_never_fabricated(self) -> None:
        rows = [
            self._row(1, None),
            {"tick": 2, "target_id": TARGET, "details": {INTEL_FIELD_GROUP_KEY: "political"}},
            {"tick": 3, "target_id": TARGET},
        ]
        ledger = derive_intel_ledger(rows)
        assert ledger == derive_intel_ledger([])

    def test_stash_uses_the_bridge_compatible_detail_keys(self) -> None:
        """The persisted key names are a cross-process contract — the legacy
        bridge wrote intel_field_group/intel_value_snapshot; the Archive
        reader must fold rows either wrote."""
        stashed = stash_intel_details({"field_group": "g", "value_snapshot": {"x": 1}})
        assert stashed == {
            INTEL_FIELD_GROUP_KEY: "g",
            INTEL_VALUE_SNAPSHOT_KEY: {"x": 1},
        }
        assert INTEL_FIELD_GROUP_KEY == "intel_field_group"
        assert INTEL_VALUE_SNAPSHOT_KEY == "intel_value_snapshot"
