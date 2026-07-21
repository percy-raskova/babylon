"""The incremental dirty-entity vault baker (Program v1.0.0, Unit T4-core/C5).

:class:`~babylon.projection.vault.tick_baker.ArchiveTickBaker` (the
"full-bake loop" this module demotes to correctness baseline + Wayne CI
golden path, per BD ruling 3) re-projects and re-renders EVERY enumerable
kind at EVERY committed tick, unconditionally — fine at Wayne-tri-county
scale, prohibitive at the shipping NATIONWIDE default (3,191 counties):
:func:`~babylon.projection.county.project_county` alone does an
``O(entities)`` attribution scan per county, so the full loop costs
``O(counties × entities)`` every single tick regardless of how much
actually changed.

:class:`IncrementalArchiveTickBaker` re-projects and re-renders only what
changed, generalizing spec-089's hex delta-persistence
(:mod:`babylon.persistence.delta`) from "which hex rows enter this tick's
DB envelope" to "which dossier pages are worth re-baking this tick":

* **Dirty-entity-driven re-projection** — graph-node-backed kinds
  (county/organization/institution/sovereign/industry/social_class) are
  re-baked only when the backing node's attribute snapshot changed since
  its last bake (:class:`~babylon.projection.vault.dirty_tracker.
  NodeSnapshotTracker`, the generalized ``hex_value_key`` comparison).
* **Derived dirtiness for rollups** — ``state``/``national`` have no
  single backing node (they aggregate every territory in scope); they are
  dirty whenever ANY constituent county is (:class:`~babylon.projection.
  vault.dirty_tracker.PendingDirtySet`, which — unlike a same-tick
  derivation — survives a budget-clamped tick so a rollup is never
  silently left stale).
* **Cross-node dependency** — a social class's ``county_class_composition``
  field reads its *containing* territory (:mod:`babylon.projection.
  social_class`'s own field-producer table), so a social class is ALSO
  dirty whenever its county is, via the same :class:`PendingDirtySet`.
* **Lazy bake-on-visit** for kinds with no backing node at all —
  ``community`` is never a graph node (Amendment U: the lattice is a
  projection over ``world.entities`` memberships), so there is no cheap
  per-id signal to track proactively; :meth:`bake_page_on_visit` bakes one
  page on demand instead (a client opening a stale community dossier),
  reusing :class:`~babylon.projection.vault.materializer.VaultMaterializer`'s
  existing single-page ``bake_*`` methods.
* **Per-kind budgets** (:class:`BakeBudgets`) bound worst-case per-tick
  cost when many entities go dirty at once (e.g. a nationwide shock):
  candidates are clamped to the first ``budget`` ids in SORTED order — never
  set-iteration order, so a repeat run over identical dirty sets picks the
  identical subset. Anything past the budget stays dirty (not recorded as
  baked) and is reconsidered — again in sorted order — next tick, so a
  spike is caught up over a few ticks rather than lost.
* **One batched commit per tick** — every kind's newly-baked pages land in
  the SAME ``pages`` dict handed to :meth:`~babylon.projection.vault.
  materializer.VaultMaterializer.bake_tick`, so a tick with nothing dirty
  costs no commit at all (the existing WO-44 content-hash-skip contract);
  this module changes what gets INTO that dict, never how it is committed.

Determinism: identical dirty entity sets (recorded track history +
identical post-tick graph/world) produce identical vault bytes — every
candidate enumeration and every budget clamp iterates a SORTED sequence.

Documented scope boundary (read literally, not a silent gap): a node's
attribute snapshot only catches changes THAT node's own graph attributes
carry. ``county``'s population/consciousness/survival aggregates
(:mod:`babylon.projection.county`) and a ``sovereign``'s CLAIMS-edge-derived
``claimed_county_fips`` (:mod:`babylon.projection.sovereign`) can move
without a tracked node attribute moving in lockstep; this mirrors spec-089's
own hex value-tuple, which tracks a DEFINED set of fields, not an
exhaustive dependency closure. The full-bake path remains the correctness
baseline for exactly this reason (BD ruling 3).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

from babylon.models.enums.topology import NodeType
from babylon.projection.community import project_community
from babylon.projection.county import project_county
from babylon.projection.industry import project_industry
from babylon.projection.institution import project_institution
from babylon.projection.national import project_national
from babylon.projection.organization import project_organization
from babylon.projection.social_class import project_social_class
from babylon.projection.sovereign import project_sovereign
from babylon.projection.state import project_state
from babylon.projection.vault.dirty_tracker import NodeSnapshotTracker, PendingDirtySet
from babylon.projection.vault.render import render_county, render_sovereign
from babylon.projection.vault.render_industry import render_industry
from babylon.projection.vault.render_institution import render_institution
from babylon.projection.vault.render_national import render_national
from babylon.projection.vault.render_organization import render_organization
from babylon.projection.vault.render_social_class import render_social_class
from babylon.projection.vault.render_state import render_state
from babylon.projection.vault.tick_baker import _NATIONAL_ID, _node_ids

if TYPE_CHECKING:
    from collections.abc import Callable

    from babylon.projection.vault.materializer import VaultMaterializer

__all__ = ["BakeBudgets", "IncrementalArchiveTickBaker"]


class BakeBudgets(BaseModel):
    """Per-kind ceilings on how many dirty entities bake in one tick.

    ``None`` (the default for every field) means unbounded — the kind's
    whole dirty set bakes every tick, matching the full-bake loop's
    behavior exactly when nothing is set. A budget bounds worst-case
    per-tick cost, not correctness: anything past the budget stays dirty
    and is picked up (in sorted order) on a later tick.
    """

    model_config = ConfigDict(frozen=True)

    county: int | None = Field(default=None, ge=0)
    state: int | None = Field(default=None, ge=0)
    national: int | None = Field(default=None, ge=0)
    organization: int | None = Field(default=None, ge=0)
    institution: int | None = Field(default=None, ge=0)
    sovereign: int | None = Field(default=None, ge=0)
    industry: int | None = Field(default=None, ge=0)
    social_class: int | None = Field(default=None, ge=0)


def _clamp(sorted_ids: list[str], budget: int | None) -> list[str]:
    """The first ``budget`` ids of an already-sorted sequence, or all of it."""
    if budget is None:
        return sorted_ids
    return sorted_ids[:budget]


def _node_snapshot(graph: Any, node_id: str) -> dict[str, Any]:
    """A node's attribute dict, or ``{}`` when the node doesn't exist."""
    node = graph.get_node(node_id)
    return dict(node.attributes) if node is not None else {}


class IncrementalArchiveTickBaker:
    """Bake only what changed at each committed tick (WO required unit C5).

    Structurally satisfies the engine's ``TickCommitObserver`` seam exactly
    like :class:`~babylon.projection.vault.tick_baker.ArchiveTickBaker`
    (duck-typed ``on_tick_committed``) — a drop-in replacement at the same
    seam, differing only in HOW MUCH work each tick does, never in what the
    vault eventually contains (see the module's full-vs-incremental
    equivalence tests).

    :param materializer: The vault materializer to bake through.
    :param county_fips: The county FIPS codes in scope, processed in
        sorted order for deterministic bake order.
    :param budgets: Per-kind per-tick bake ceilings; defaults to unbounded
        for every kind (see :class:`BakeBudgets`).
    """

    def __init__(
        self,
        materializer: VaultMaterializer,
        county_fips: tuple[str, ...],
        budgets: BakeBudgets | None = None,
    ) -> None:
        self._materializer = materializer
        self._county_fips = tuple(sorted(county_fips))
        self._budgets = budgets if budgets is not None else BakeBudgets()
        self._tracker = NodeSnapshotTracker()
        self._pending = PendingDirtySet()

    def on_tick_committed(self, *, tick: int, world: Any, graph: Any) -> None:
        """Re-project and re-render only the entities dirty this tick.

        :param tick: The committed tick number.
        :param world: The post-tick world state.
        :param graph: The post-tick engine graph.
        """
        pages: dict[str, str] = {}

        county_dirty_raw = self._bake_counties(tick=tick, world=world, graph=graph, pages=pages)
        self._bake_rollups(
            tick=tick, world=world, graph=graph, pages=pages, county_dirty_raw=county_dirty_raw
        )
        self._bake_simple_kind(
            kind="organization",
            node_type=NodeType.ORGANIZATION,
            project_fn=lambda oid: project_organization(oid, graph=graph, world=world, tick=tick),
            render_fn=lambda view: render_organization(view, verified_tick=tick),
            path_fn=lambda oid: f"organization/{oid}.md",
            budget=self._budgets.organization,
            graph=graph,
            pages=pages,
        )
        self._bake_simple_kind(
            kind="institution",
            node_type=NodeType.INSTITUTION,
            project_fn=lambda iid: project_institution(iid, graph=graph, tick=tick),
            render_fn=lambda view: render_institution(view, verified_tick=tick),
            path_fn=lambda iid: f"institution/{iid}.md",
            budget=self._budgets.institution,
            graph=graph,
            pages=pages,
        )
        self._bake_simple_kind(
            kind="sovereign",
            node_type=NodeType.SOVEREIGN,
            project_fn=lambda sid: project_sovereign(sid, graph=graph, world=world, tick=tick),
            render_fn=lambda view: render_sovereign(view, verified_tick=tick),
            path_fn=lambda sid: f"sovereign/{sid}.md",
            budget=self._budgets.sovereign,
            graph=graph,
            pages=pages,
        )
        self._bake_simple_kind(
            kind="industry",
            node_type=NodeType.INDUSTRY,
            project_fn=lambda iid: project_industry(iid, graph=graph, world=world, tick=tick),
            render_fn=lambda view: render_industry(view, verified_tick=tick),
            path_fn=lambda iid: f"industry/{iid}.md",
            budget=self._budgets.industry,
            graph=graph,
            pages=pages,
        )
        county_dirty_set = frozenset(county_dirty_raw)
        self._bake_simple_kind(
            kind="social_class",
            node_type=NodeType.SOCIAL_CLASS,
            project_fn=lambda cid: project_social_class(cid, graph=graph, world=world, tick=tick),
            render_fn=lambda view: render_social_class(view, verified_tick=tick),
            path_fn=lambda cid: f"social_class/{cid}.md",
            budget=self._budgets.social_class,
            graph=graph,
            pages=pages,
            extra_dirty_predicate=lambda _cid, snapshot: (
                snapshot.get("county_fips") in county_dirty_set
            ),
        )

        self._materializer.bake_tick(pages, tick=tick)

    def _bake_counties(
        self, *, tick: int, world: Any, graph: Any, pages: dict[str, str]
    ) -> list[str]:
        """Bake dirty counties; returns the FULL raw dirty set (pre-budget).

        The raw set (not the budget-clamped bake list) is what
        state/national dirtiness derives from — a county that changed but
        was clamped out of THIS tick's bake still makes its state/national
        rollup dirty, because those rollups read the live graph directly,
        not the county's cached page (see the module docstring).
        """
        territory_snapshots = _territory_snapshots_by_county_fips(graph)
        dirty_raw: list[str] = []
        for fips in self._county_fips:
            snapshot = territory_snapshots.get(fips, {})
            if self._tracker.is_dirty("county", fips, snapshot):
                dirty_raw.append(fips)

        for fips in _clamp(dirty_raw, self._budgets.county):
            view = project_county(fips, graph=graph, world=world, tick=tick)
            pages[f"county/{fips}.md"] = render_county(view, verified_tick=tick)
            self._tracker.record_baked("county", fips, territory_snapshots.get(fips, {}))
        return dirty_raw

    def _bake_rollups(
        self,
        *,
        tick: int,
        world: Any,
        graph: Any,
        pages: dict[str, str],
        county_dirty_raw: list[str],
    ) -> None:
        """Bake dirty ``state``/``national`` rollups (derived dirtiness)."""
        for fips in county_dirty_raw:
            self._pending.mark("state", fips[:2])
            self._pending.mark("national", _NATIONAL_ID)

        state_prefixes = sorted({fips[:2] for fips in self._county_fips})
        state_dirty = [p for p in state_prefixes if self._pending.is_dirty("state", p)]
        for prefix in _clamp(state_dirty, self._budgets.state):
            state = project_state(prefix, graph=graph, world=world, tick=tick)
            pages[f"state/{prefix}.md"] = render_state(state, verified_tick=tick)
            self._pending.clear("state", prefix)

        national_dirty = [_NATIONAL_ID] if self._pending.is_dirty("national", _NATIONAL_ID) else []
        for national_id in _clamp(national_dirty, self._budgets.national):
            national = project_national(national_id, graph=graph, world=world, tick=tick)
            pages[f"national/{national_id}.md"] = render_national(national, verified_tick=tick)
            self._pending.clear("national", national_id)

    def _bake_simple_kind(
        self,
        *,
        kind: str,
        node_type: NodeType,
        project_fn: Callable[[str], Any],
        render_fn: Callable[[Any], str],
        path_fn: Callable[[str], str],
        budget: int | None,
        graph: Any,
        pages: dict[str, str],
        extra_dirty_predicate: Callable[[str, dict[str, Any]], bool] | None = None,
    ) -> None:
        """Bake a graph-node-backed kind's dirty ids (own-snapshot ± extra reason).

        :param extra_dirty_predicate: An optional secondary dirtiness
            reason beyond this id's own node attributes (e.g. a social
            class's containing county) — evaluated against the id's own
            snapshot; when it fires, the id is marked pending via
            :class:`~babylon.projection.vault.dirty_tracker.PendingDirtySet`
            so the reason survives a budget-clamped tick exactly like the
            rollup kinds do.
        """
        ids = _node_ids(graph, node_type)
        dirty_raw: list[str] = []
        snapshots: dict[str, dict[str, Any]] = {}
        for entity_id in ids:
            snapshot = _node_snapshot(graph, entity_id)
            snapshots[entity_id] = snapshot
            if extra_dirty_predicate is not None and extra_dirty_predicate(entity_id, snapshot):
                self._pending.mark(kind, entity_id)
            own_dirty = self._tracker.is_dirty(kind, entity_id, snapshot)
            if own_dirty or self._pending.is_dirty(kind, entity_id):
                dirty_raw.append(entity_id)

        for entity_id in _clamp(sorted(dirty_raw), budget):
            view = project_fn(entity_id)
            pages[path_fn(entity_id)] = render_fn(view)
            self._tracker.record_baked(kind, entity_id, snapshots[entity_id])
            self._pending.clear(kind, entity_id)

    def bake_page_on_visit(
        self, kind: str, entity_id: str, *, world: Any, graph: Any, tick: int
    ) -> None:
        """Bake one page on demand — the lazy path for kinds never dirty-tracked.

        ``community`` has no backing graph node (Amendment U: the lattice
        is a projection over ``world.entities`` memberships, never a node),
        so there is no cheap per-id signal :meth:`on_tick_committed` could
        track proactively; a client opening a community dossier calls this
        instead, landing ONE single-page commit via the existing
        :class:`~babylon.projection.vault.materializer.VaultMaterializer`
        ``bake_*`` methods (no separate rendering path to maintain).

        :param kind: Currently only ``"community"`` is wired.
        :param entity_id: The community id (a ``CommunityType`` value).
        :param world: The post-tick world state.
        :param graph: The post-tick engine graph (unused for ``community``,
            accepted for a uniform call signature with future kinds).
        :param tick: The committed tick this bake is projected from.
        :raises ValueError: for any ``kind`` other than ``"community"`` —
            every other kind is already dirty-tracked by
            :meth:`on_tick_committed`, so visiting it lazily would risk
            re-baking with a stale ``tick`` and silently masking a real
            dirty-tracking gap rather than failing loud.
        """
        del graph
        if kind != "community":
            raise ValueError(
                f"bake_page_on_visit only serves 'community' (no backing graph node); "
                f"'{kind}' is dirty-tracked every tick by on_tick_committed"
            )
        view = project_community(entity_id, world=world, tick=tick)
        self._materializer.bake_community(view, tick=tick)


def _territory_snapshots_by_county_fips(graph: Any) -> dict[str, dict[str, Any]]:
    """Every territory's attribute snapshot, keyed by its ``county_fips``.

    ONE ``O(#territories)`` pass over the graph per tick — the substrate
    this module's whole per-county-tick cost bound rests on. Calling
    :mod:`babylon.projection.county`'s private ``_resolve_territory`` once
    per county here (as the full-bake loop's own per-county
    ``project_county`` call does internally) would be
    ``O(counties × territories)``, silently reintroducing at the
    snapshot-comparison layer the exact quadratic blowup this baker exists
    to eliminate at the projection layer — so this precomputes the whole
    map once instead, applying :func:`~babylon.projection.county.
    project_county`'s own deterministic tie-break (lexicographically
    smallest node id wins a shared ``county_fips``) without importing that
    private helper (mirrors :mod:`babylon.projection.social_class`'s own
    documented choice to duplicate its territory lookup rather than reach
    into a sibling module's private surface).
    """
    winning_node_id: dict[str, str] = {}
    snapshot_by_fips: dict[str, dict[str, Any]] = {}
    for node in graph.query_nodes(node_type=NodeType.TERRITORY.value):
        fips = node.attributes.get("county_fips")
        if fips is None:
            continue
        current_winner = winning_node_id.get(fips)
        if current_winner is None or node.id < current_winner:
            winning_node_id[fips] = node.id
            snapshot_by_fips[fips] = dict(node.attributes)
    return snapshot_by_fips
