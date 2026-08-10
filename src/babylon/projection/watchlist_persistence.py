"""The watchlist persistence seam — a storage contract, not a rendering one.

Relocated from ``babylon.tui.watchlist`` by the Amendment AF (ADR186)
deletion ceremony: that module bundled this Protocol with the deleted
client's own watchlist domain state (``WatchlistState``, pin/unpin
mechanics) and page-level Rich rendering (``render_watchlist``,
``watchlist_rows``) — none of which had a consumer outside the deleted
client and its own tests. Only :class:`WatchlistPersistence` survives:
:class:`~babylon.persistence.babylon_meta.BabylonMetaStore` structurally
satisfies it (Program 24 P3 WO-46's ``babylon_meta``-backed store), pinned
by ``tests/unit/persistence/test_babylon_meta.py``'s own
``isinstance(store, WatchlistPersistence)`` contract test — a real,
durable seam independent of any specific client's watchlist UI.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

__all__ = ["WatchlistPersistence"]


@runtime_checkable
class WatchlistPersistence(Protocol):
    """The seam Program 24 P3 WO-46's ``babylon_meta``-backed store implements.

    Structural (``@runtime_checkable``): any object exposing these two
    methods satisfies this Protocol, so tests exercise the seam with a
    trivial in-memory fake with zero dependency on Postgres/``babylon_meta``.
    WO-46's real implementation persists to the ``watchlist`` table that
    charter P0 ruling 3 names.
    """

    def load(self, session_id: str) -> tuple[str, ...]:
        """Return the recorded pin order for ``session_id``.

        :param session_id: the campaign/session key WO-46's schema scopes
            ``watchlist`` rows by.
        :returns: the recorded pin order, oldest-pinned-first, or ``()`` if
            ``session_id`` has no recorded watchlist (an honest empty
            result, never a fabricated default pin list).
        """
        ...

    def save(self, session_id: str, pinned_ids: tuple[str, ...]) -> None:
        """Persist ``pinned_ids`` (in order) as ``session_id``'s watchlist.

        :param session_id: the campaign/session key to persist under.
        :param pinned_ids: the full current pin order to record.
        """
        ...
