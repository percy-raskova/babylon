"""Generic dirty-entity tracking for the incremental vault baker.

Generalizes :mod:`babylon.persistence.delta`'s spec-089 hex value-tuple
comparison beyond hex rows and beyond one kind: :class:`NodeSnapshotTracker`
answers "did the fields I read change since I last baked this id" for ANY
graph-node-backed projection kind, by snapshotting the node's own
``attributes`` dict and comparing it, id-by-id, to the snapshot recorded the
last time that id was actually baked — exactly the ``last_emitted`` value-key
comparison :func:`~babylon.persistence.delta.select_hex_rows_for_emission`
does, generalized from a curated 9-field tuple to the node's whole attribute
dict (so no per-kind field list needs to be hand-maintained here; the kind's
own ``project_*``/``render_*`` pair is the one place that decides which
fields matter).

A second primitive, :class:`PendingDirtySet`, covers projection kinds with
no single backing graph node to snapshot — a rollup (``state``/``national``,
which aggregate many territories) or a cross-node dependency (a social
class's ``county_class_composition`` reads its *containing* territory, not
just its own node). A caller **marks** an id dirty when something it
depends on changed; the mark survives until the caller explicitly
**clears** it (i.e. the id was actually baked), so a budget-clamped id that
was dirty this tick but not baked stays dirty next tick instead of being
silently forgotten (see :mod:`babylon.projection.vault.incremental_baker`).

Both primitives share one discipline, deliberately split into a
non-mutating query and a mutating record/clear step: **querying "is this
dirty" must never itself consume the dirty flag.** Only recording that an
id was actually baked may clear it — a caller that queried-then-skipped an
id under a per-tick budget must see it dirty again next tick, not have
silently lost track of the pending change.
"""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping

__all__ = ["NodeSnapshotTracker", "PendingDirtySet"]


class NodeSnapshotTracker:
    """Per-``(kind, id)`` attribute-snapshot dirty tracking.

    Mirrors :func:`babylon.persistence.delta.select_hex_rows_for_emission`'s
    ``last_emitted`` dict, generalized from one hex-row value tuple to an
    arbitrary snapshot mapping and from one kind to many.
    """

    def __init__(self) -> None:
        self._last_baked: dict[tuple[str, str], dict[str, Any]] = {}

    def is_dirty(self, kind: str, entity_id: str, snapshot: Mapping[str, Any]) -> bool:
        """True iff ``snapshot`` differs from what was last baked, or nothing was.

        Non-mutating: safe to call for every candidate id every tick,
        whether or not the caller ends up baking it.

        :param kind: The projection kind (``"county"``, ``"organization"``, …).
        :param entity_id: The id within that kind.
        :param snapshot: The current tick's snapshot for this id — normally
            ``dict(node.attributes)`` off the post-tick graph.
        :returns: ``True`` the first time this ``(kind, entity_id)`` is seen
            (the correctness baseline: an id never baked is always dirty)
            or whenever ``snapshot`` differs from the recorded bake.
        """
        previous = self._last_baked.get((kind, entity_id))
        return previous is None or previous != dict(snapshot)

    def record_baked(self, kind: str, entity_id: str, snapshot: Mapping[str, Any]) -> None:
        """Record that ``(kind, entity_id)`` was just baked at ``snapshot``.

        Call ONLY for ids actually baked this tick — an id left dirty by a
        per-kind budget clamp must stay dirty for the next tick, so it must
        NOT be recorded here (see the module docstring's query/mutate split).

        :param kind: The projection kind.
        :param entity_id: The id within that kind.
        :param snapshot: The snapshot the just-completed bake was rendered
            from; deep-copied so a caller mutating its own dict afterward
            cannot corrupt the recorded baseline.
        """
        self._last_baked[(kind, entity_id)] = copy.deepcopy(dict(snapshot))


class PendingDirtySet:
    """Caller-declared dirty flags for ids with no single node to snapshot.

    A rollup kind (``state``/``national``) or a cross-node dependency (a
    social class keyed off its *containing* territory) has no one
    ``attributes`` dict whose equality answers "did this change" — the
    caller already knows the reason (a constituent territory changed) and
    just needs the flag to survive a budget-clamped tick. :meth:`is_dirty`
    also reports ``True`` for an id never :meth:`clear`-ed, so the first
    bake of every id is unconditional exactly like
    :class:`NodeSnapshotTracker`'s "never baked" case.
    """

    def __init__(self) -> None:
        self._pending: set[tuple[str, str]] = set()
        self._ever_baked: set[tuple[str, str]] = set()

    def mark(self, kind: str, entity_id: str) -> None:
        """Flag ``(kind, entity_id)`` dirty until it is next :meth:`clear`-ed."""
        self._pending.add((kind, entity_id))

    def is_dirty(self, kind: str, entity_id: str) -> bool:
        """True iff pending, or never baked at all.

        Non-mutating, matching :meth:`NodeSnapshotTracker.is_dirty`.
        """
        key = (kind, entity_id)
        return key in self._pending or key not in self._ever_baked

    def clear(self, kind: str, entity_id: str) -> None:
        """Record that ``(kind, entity_id)`` was just baked — call ONLY then."""
        key = (kind, entity_id)
        self._pending.discard(key)
        self._ever_baked.add(key)
