"""The ``babylon_meta`` epistemic store (Program 24 WO-46, charter P0 ruling 3).

CLIENT-owned state: the Archive TUI is the only writer and the only reader.
The engine never touches ``babylon_meta.*`` and no tick-hash input derives
from it — player knowledge (campaign catalog, watchlist, jumplist,
breadcrumbs) lives outside the deterministic Ledger by construction
(the epistemic / material partition). The DDL source of truth is
:data:`babylon.persistence.postgres_schema.BABYLON_META_DDL`; migration
``0037_babylon_meta.sql`` mirrors it for existing databases.

The store lives in the persistence layer, NOT in ``babylon.tui`` — the
import-linter contract forbids the TUI from importing persistence. The
composition root (client boot) constructs a :class:`BabylonMetaStore` and
injects it where the TUI's seams expect one; in particular this class
structurally satisfies :class:`babylon.tui.watchlist.WatchlistPersistence`
via :meth:`load` / :meth:`save` without either module importing the other.

Usage::

    from psycopg_pool import ConnectionPool
    from babylon.persistence.babylon_meta import BabylonMetaStore

    pool = ConnectionPool(conninfo="dbname=babylon")
    store = BabylonMetaStore(pool)
    store.ensure_schema()
    campaign = store.create_campaign(
        slug="rust-belt-dawn", engine_version="0.24.0", defines_hash="…"
    )
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from psycopg import sql
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from pydantic import BaseModel, ConfigDict, Field

from babylon.persistence.postgres_schema import BABYLON_META_DDL, ensure_ddl_applied

__all__ = ["BabylonMetaStore", "CampaignRecord", "CampaignStatus"]

#: Campaign lifecycle states (WO-49 lobby: reversible soft-delete).
CampaignStatus = Literal["ACTIVE", "ABANDONED"]

#: The session-scoped ordered-list tables. A whitelist, not a convention:
#: every dynamic table name below is validated against this set before it
#: is composed into SQL (and composition uses ``sql.Identifier`` besides).
_NAV_TABLES = frozenset({"watchlist", "jumplist", "breadcrumb"})

_CAMPAIGN_COLUMNS = sql.SQL(
    "campaign_id, slug, engine_version, defines_hash, last_tick, status, last_played_at, created_at"
)


class CampaignRecord(BaseModel):
    """One row of the ``babylon_meta.campaign`` catalog.

    :param campaign_id: The campaign's minted UUID (primary key).
    :param slug: Unique human-readable codename shown in the lobby.
    :param engine_version: Engine version the campaign was created under.
    :param defines_hash: Hash of the ``GameDefines`` the campaign runs on.
    :param last_tick: Highest tick the player has reached (>= 0).
    :param status: Lifecycle state — ``ACTIVE`` or ``ABANDONED`` (the
        reversible soft-delete WO-49's lobby exposes).
    :param last_played_at: When the campaign was last progressed, or
        ``None`` if never played past creation.
    :param created_at: When the campaign was minted.
    """

    model_config = ConfigDict(frozen=True)

    campaign_id: UUID
    slug: str
    engine_version: str
    defines_hash: str
    last_tick: int = Field(ge=0)
    status: CampaignStatus
    last_played_at: datetime | None
    created_at: datetime


class BabylonMetaStore:
    """Postgres-backed accessor for the ``babylon_meta`` epistemic tier.

    Campaign catalog CRUD plus the three session-scoped navigation lists
    (watchlist / jumplist / breadcrumb). All SQL is schema-qualified
    ``babylon_meta.*`` — the structural boundary that keeps this tier out
    of the engine's public-schema Ledger.

    Error policy (logic-layer loud failure): constraint violations
    (duplicate slug, foreign key to a missing campaign) bubble as
    ``psycopg`` errors; updates targeting a missing campaign raise
    :class:`LookupError`. Nothing is silently swallowed.

    :param pool: An open psycopg connection pool for the runtime database.
    """

    def __init__(self, pool: ConnectionPool) -> None:
        self._pool = pool

    def ensure_schema(self) -> bool:
        """Apply the ``babylon_meta`` DDL exactly once (digest-stamped).

        Idempotent via :func:`~babylon.persistence.postgres_schema.
        ensure_ddl_applied`: a repeat call fast-paths on the stamp without
        taking any DDL lock.

        :returns: ``True`` if the DDL was executed, ``False`` if it was
            already applied.
        """
        with self._pool.connection() as conn:
            conn.autocommit = True
            return ensure_ddl_applied(conn, BABYLON_META_DDL)

    # ─── Campaign catalog ───────────────────────────────────────────

    def create_campaign(
        self, *, slug: str, engine_version: str, defines_hash: str
    ) -> CampaignRecord:
        """Mint a new campaign and return its catalog row.

        :param slug: Unique codename; a duplicate raises
            ``psycopg.errors.UniqueViolation`` (loud, not renamed).
        :param engine_version: Engine version stamped on the campaign.
        :param defines_hash: ``GameDefines`` hash stamped on the campaign.
        :returns: The freshly inserted row, defaults included.
        """
        with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                sql.SQL(
                    "INSERT INTO babylon_meta.campaign "
                    "(campaign_id, slug, engine_version, defines_hash) "
                    "VALUES (%s, %s, %s, %s) RETURNING {columns}"
                ).format(columns=_CAMPAIGN_COLUMNS),
                (uuid4(), slug, engine_version, defines_hash),
            )
            row = cur.fetchone()
            if row is None:  # pragma: no cover — RETURNING on INSERT always yields a row
                msg = "INSERT ... RETURNING produced no row"
                raise RuntimeError(msg)
            return CampaignRecord(**row)

    def get_campaign(self, campaign_id: UUID) -> CampaignRecord | None:
        """Return one catalog row, or ``None`` if the campaign is unknown.

        :param campaign_id: The campaign to fetch.
        :returns: The row, or an honest ``None`` — never a fabricated default.
        """
        with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                sql.SQL(
                    "SELECT {columns} FROM babylon_meta.campaign WHERE campaign_id = %s"
                ).format(columns=_CAMPAIGN_COLUMNS),
                (campaign_id,),
            )
            row = cur.fetchone()
            return None if row is None else CampaignRecord(**row)

    def list_campaigns(self) -> tuple[CampaignRecord, ...]:
        """Return the full catalog, newest-created first (deterministic order).

        :returns: All campaigns ordered by ``created_at`` descending with
            ``campaign_id`` as the tiebreak, so equal timestamps cannot
            reorder the lobby between renders.
        """
        with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                sql.SQL(
                    "SELECT {columns} FROM babylon_meta.campaign "
                    "ORDER BY created_at DESC, campaign_id"
                ).format(columns=_CAMPAIGN_COLUMNS)
            )
            return tuple(CampaignRecord(**row) for row in cur.fetchall())

    def record_progress(self, campaign_id: UUID, *, last_tick: int) -> None:
        """Record that the player reached ``last_tick`` just now.

        :param campaign_id: The campaign that progressed.
        :param last_tick: The tick reached (>= 0; the CHECK constraint
            rejects negatives loudly).
        :raises LookupError: If the campaign does not exist.
        """
        with self._pool.connection() as conn:
            cur = conn.execute(
                "UPDATE babylon_meta.campaign "
                "SET last_tick = %s, last_played_at = now() "
                "WHERE campaign_id = %s",
                (last_tick, campaign_id),
            )
            if cur.rowcount != 1:
                msg = f"no campaign {campaign_id} to record progress against"
                raise LookupError(msg)

    def set_status(self, campaign_id: UUID, status: CampaignStatus) -> None:
        """Set the campaign's lifecycle status (reversible soft-delete).

        :param campaign_id: The campaign to transition.
        :param status: ``ACTIVE`` or ``ABANDONED``.
        :raises LookupError: If the campaign does not exist.
        """
        with self._pool.connection() as conn:
            cur = conn.execute(
                "UPDATE babylon_meta.campaign SET status = %s WHERE campaign_id = %s",
                (status, campaign_id),
            )
            if cur.rowcount != 1:
                msg = f"no campaign {campaign_id} to set status on"
                raise LookupError(msg)

    def delete_campaign(self, campaign_id: UUID) -> bool:
        """Hard-delete a campaign; navigation lists cascade with it.

        The lobby's reversible path is :meth:`set_status`; this is the
        arm-then-confirm terminal delete.

        :param campaign_id: The campaign to delete.
        :returns: ``True`` if a row was deleted, ``False`` if none existed.
        """
        with self._pool.connection() as conn:
            cur = conn.execute(
                "DELETE FROM babylon_meta.campaign WHERE campaign_id = %s",
                (campaign_id,),
            )
            return cur.rowcount == 1

    # ─── Watchlist seam (babylon.tui.watchlist.WatchlistPersistence) ─

    def load(self, session_id: str) -> tuple[str, ...]:
        """Return the recorded watchlist pin order for ``session_id``.

        Satisfies ``WatchlistPersistence.load`` structurally: the seam's
        session key IS the campaign UUID as a string.

        :param session_id: The campaign UUID (string form) to load for; a
            string that is not a UUID raises ``ValueError`` (caller bug).
        :returns: The pin order, oldest-pinned first, or ``()`` for a
            campaign with no recorded watchlist.
        """
        return self._load_list("watchlist", UUID(session_id))

    def save(self, session_id: str, pinned_ids: tuple[str, ...]) -> None:
        """Persist ``pinned_ids`` (in order) as the campaign's watchlist.

        Satisfies ``WatchlistPersistence.save``. Replaces the full list;
        a campaign that does not exist raises
        ``psycopg.errors.ForeignKeyViolation`` (loud — a watchlist cannot
        outlive its campaign).

        :param session_id: The campaign UUID (string form) to save under.
        :param pinned_ids: The full current pin order.
        """
        self._save_list("watchlist", UUID(session_id), pinned_ids)

    # ─── Jumplist / breadcrumbs (WO-47 navigation shell) ────────────

    def load_jumplist(self, campaign_id: UUID) -> tuple[str, ...]:
        """Return the persisted jumplist stack, oldest entry first.

        :param campaign_id: The campaign whose jumplist to load.
        :returns: The stack, or ``()`` if none was recorded.
        """
        return self._load_list("jumplist", campaign_id)

    def save_jumplist(self, campaign_id: UUID, entity_ids: tuple[str, ...]) -> None:
        """Replace the persisted jumplist stack.

        Repeats are legal — a back-stack revisits pages.

        :param campaign_id: The campaign to save under.
        :param entity_ids: The full stack, oldest entry first.
        """
        self._save_list("jumplist", campaign_id, entity_ids)

    def load_breadcrumbs(self, campaign_id: UUID) -> tuple[str, ...]:
        """Return the persisted breadcrumb trail, oldest entry first.

        :param campaign_id: The campaign whose trail to load.
        :returns: The trail, or ``()`` if none was recorded.
        """
        return self._load_list("breadcrumb", campaign_id)

    def save_breadcrumbs(self, campaign_id: UUID, entity_ids: tuple[str, ...]) -> None:
        """Replace the persisted breadcrumb trail.

        :param campaign_id: The campaign to save under.
        :param entity_ids: The full trail, oldest entry first.
        """
        self._save_list("breadcrumb", campaign_id, entity_ids)

    # ─── Shared ordered-list plumbing ───────────────────────────────

    def _load_list(self, table: str, campaign_id: UUID) -> tuple[str, ...]:
        """Read one navigation table's entries in position order."""
        if table not in _NAV_TABLES:
            msg = f"not a babylon_meta navigation table: {table!r}"
            raise ValueError(msg)
        with self._pool.connection() as conn:
            cur = conn.execute(
                sql.SQL(
                    "SELECT entity_id FROM babylon_meta.{table} "
                    "WHERE campaign_id = %s ORDER BY position"
                ).format(table=sql.Identifier(table)),
                (campaign_id,),
            )
            return tuple(row[0] for row in cur.fetchall())

    def _save_list(self, table: str, campaign_id: UUID, entity_ids: tuple[str, ...]) -> None:
        """Atomically replace one navigation table's entries for a campaign."""
        if table not in _NAV_TABLES:
            msg = f"not a babylon_meta navigation table: {table!r}"
            raise ValueError(msg)
        with self._pool.connection() as conn:
            conn.execute(
                sql.SQL("DELETE FROM babylon_meta.{table} WHERE campaign_id = %s").format(
                    table=sql.Identifier(table)
                ),
                (campaign_id,),
            )
            with conn.cursor() as cur:
                cur.executemany(
                    sql.SQL(
                        "INSERT INTO babylon_meta.{table} "
                        "(campaign_id, position, entity_id) VALUES (%s, %s, %s)"
                    ).format(table=sql.Identifier(table)),
                    [
                        (campaign_id, position, entity_id)
                        for position, entity_id in enumerate(entity_ids)
                    ],
                )
