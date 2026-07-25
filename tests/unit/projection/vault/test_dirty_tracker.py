"""Unit tests for the generic dirty-entity primitives (Unit T4-core/C5).

Pure logic, no graph/world fixtures needed: :class:`NodeSnapshotTracker` and
:class:`PendingDirtySet` only ever see plain dicts and ``(kind, id)`` pairs.
"""

from __future__ import annotations

from babylon.projection.vault.dirty_tracker import NodeSnapshotTracker, PendingDirtySet


class TestNodeSnapshotTracker:
    def test_never_baked_is_dirty(self) -> None:
        tracker = NodeSnapshotTracker()
        assert tracker.is_dirty("county", "26163", {"tick_median_wage": 19.0})

    def test_unchanged_snapshot_after_baking_is_clean(self) -> None:
        tracker = NodeSnapshotTracker()
        snapshot = {"tick_median_wage": 19.0}
        tracker.record_baked("county", "26163", snapshot)
        assert not tracker.is_dirty("county", "26163", snapshot)

    def test_changed_snapshot_after_baking_is_dirty(self) -> None:
        tracker = NodeSnapshotTracker()
        tracker.record_baked("county", "26163", {"tick_median_wage": 19.0})
        assert tracker.is_dirty("county", "26163", {"tick_median_wage": 20.0})

    def test_is_dirty_never_mutates_state(self) -> None:
        """Querying must not itself consume the dirty flag (budget-clamp safety)."""
        tracker = NodeSnapshotTracker()
        snapshot = {"tick_median_wage": 19.0}
        assert tracker.is_dirty("county", "26163", snapshot)
        # Querying again without recording a bake still reports dirty.
        assert tracker.is_dirty("county", "26163", snapshot)

    def test_recorded_snapshot_is_deep_copied(self) -> None:
        """Mutating the caller's dict after recording must not corrupt the baseline.

        If ``record_baked`` only shallow-copied, the nested dict would be
        shared with the caller's, so mutating it afterward would silently
        rewrite the recorded baseline too — the still-0.5 query below
        would then read back as dirty against the now-0.9 "baseline",
        a false positive this deep copy exists to prevent.
        """
        tracker = NodeSnapshotTracker()
        snapshot = {"tick_class_distribution": {"proletariat": 0.5}}
        tracker.record_baked("county", "26163", snapshot)
        snapshot["tick_class_distribution"]["proletariat"] = 0.9  # mutate caller's own dict
        assert not tracker.is_dirty(
            "county", "26163", {"tick_class_distribution": {"proletariat": 0.5}}
        )
        assert tracker.is_dirty(
            "county", "26163", {"tick_class_distribution": {"proletariat": 0.9}}
        )

    def test_kinds_are_independent(self) -> None:
        tracker = NodeSnapshotTracker()
        tracker.record_baked("county", "26163", {"x": 1})
        assert tracker.is_dirty("organization", "26163", {"x": 1})

    def test_ids_are_independent(self) -> None:
        tracker = NodeSnapshotTracker()
        tracker.record_baked("county", "26163", {"x": 1})
        assert tracker.is_dirty("county", "26099", {"x": 1})


class TestPendingDirtySet:
    def test_never_cleared_is_dirty(self) -> None:
        pending = PendingDirtySet()
        assert pending.is_dirty("state", "26")

    def test_marked_is_dirty(self) -> None:
        pending = PendingDirtySet()
        pending.clear("state", "26")
        assert not pending.is_dirty("state", "26")
        pending.mark("state", "26")
        assert pending.is_dirty("state", "26")

    def test_clear_without_mark_after_first_bake_is_clean(self) -> None:
        pending = PendingDirtySet()
        pending.clear("state", "26")
        assert not pending.is_dirty("state", "26")

    def test_mark_survives_a_query(self) -> None:
        """Querying must not itself clear the pending flag (budget-clamp safety)."""
        pending = PendingDirtySet()
        pending.clear("state", "26")
        pending.mark("state", "26")
        assert pending.is_dirty("state", "26")
        assert pending.is_dirty("state", "26")

    def test_kinds_and_ids_are_independent(self) -> None:
        pending = PendingDirtySet()
        pending.clear("state", "26")
        assert pending.is_dirty("national", "26")
        assert pending.is_dirty("state", "17")
