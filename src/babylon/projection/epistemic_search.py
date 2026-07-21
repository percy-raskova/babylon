"""Epistemic search — the org searches what it knows, nothing else (WO-43).

Two ways of knowing compose the known-entity set (charter P0 batch:
FTS-over-known-only, no global oracle):

1. **Spatial**: :func:`~babylon.projection.fog.reach.organizing_reach` —
   the PRESENCE → TENANCY → SOLIDARITY traversal rooted at the player org.
2. **Historical**: every node id the org has ever INVESTIGATEd — the
   :class:`~babylon.projection.fog.ledger.IntelLedger`'s observed ids.
   Intel never expires *as knowledge-of-existence*: staleness ages the
   VALUES (``read_intel`` tiers), but a place once seen stays on the map.

``/`` search executes as an in-process filter over that set — entity
counts at session scope are small, and the registry's ``fts_columns``
declarations (:class:`~babylon.projection.registry.DeclaredView`) name
the searchable text surface per view
(:func:`searchable_text_for_row` executes exactly that declaration).
A Postgres ``to_tsvector`` lane can replace the filter later without
moving the contract: the *set* being searched is the epistemic boundary,
not the matcher. Anything outside the set is not a result — the TUI
renders it as a redlink (``babylon.tui.wikilinks``), which is the honest
"you don't know this yet", never a fabricated stub.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict

from babylon.projection.fog.reach import organizing_reach

if TYPE_CHECKING:
    from collections.abc import Mapping
    from collections.abc import Set as AbstractSet

    from babylon.kernel import GraphProtocol
    from babylon.projection.fog.ledger import IntelLedger
    from babylon.projection.registry import DeclaredView

__all__ = [
    "SearchHit",
    "known_entity_ids",
    "search_known",
    "searchable_text_for_row",
]


class SearchHit(BaseModel):
    """One search result: a known entity and the text it matched through."""

    model_config = ConfigDict(frozen=True)

    entity_id: str
    matched_text: str


def known_entity_ids(
    graph: GraphProtocol,
    player_org_id: str | None,
    *,
    ledger: IntelLedger,
    radius: int,
) -> frozenset[str]:
    """The org's entire knowable id set: ``reach ∪ intel``.

    :param graph: the hydrated session graph.
    :param player_org_id: the canonical player-org id, or ``None`` for
        sessions with no player org (an empty spatial axis, not an error).
    :param radius: the SOLIDARITY-hop depth, passed through to
        :func:`~babylon.projection.fog.reach.organizing_reach` (callers
        supply ``GameDefines.epistemic_horizon.organizing_reach_radius``).
    :param ledger: the session's INVESTIGATE history; every entry's
        ``node_id`` is known regardless of the entry's age.
    :returns: the union, deterministic and hashable.
    """
    observed = frozenset(entry.node_id for entry in ledger.entries)
    return organizing_reach(graph, player_org_id, radius) | observed


def searchable_text_for_row(view: DeclaredView, row: Mapping[str, Any]) -> str:
    """One row's declared search surface: its ``fts_columns`` values, joined.

    Executes the registry declaration in-process: columns OUTSIDE
    ``view.fts_columns`` never contribute text, and absent/``None`` values
    contribute nothing (honest absence, not the string ``"None"``).

    :param view: the declared view the row came from.
    :param row: one row, keyed by column name.
    :returns: the space-joined searchable text (possibly empty).
    """
    parts = [str(row[column]) for column in view.fts_columns if row.get(column) is not None]
    return " ".join(parts)


def search_known(
    query: str,
    corpus: Mapping[str, str],
    known: AbstractSet[str],
) -> tuple[SearchHit, ...]:
    """Case-insensitive substring search, restricted to the known set.

    The epistemic contract lives HERE: even when ``corpus`` carries text
    for an entity outside ``known`` (a caller passing a global corpus by
    mistake), that entity is never surfaced. An entity's own id is always
    part of its searchable text, so id fragments match without a corpus
    entry.

    :param query: the search text; blank returns no hits (search is a
        question, not an enumeration of everything known).
    :param corpus: entity id → searchable text (e.g. built via
        :func:`searchable_text_for_row`); ids absent from it search by id
        alone.
    :param known: the epistemic boundary (:func:`known_entity_ids`).
    :returns: hits sorted by ``entity_id`` — deterministic display order.
    """
    needle = query.strip().casefold()
    if not needle:
        return ()
    hits: list[SearchHit] = []
    for entity_id in sorted(known):
        text = corpus.get(entity_id, "")
        haystack = f"{entity_id} {text}".casefold()
        if needle in haystack:
            hits.append(SearchHit(entity_id=entity_id, matched_text=text or entity_id))
    return tuple(hits)
