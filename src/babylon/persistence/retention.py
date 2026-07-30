"""Session retention enforcement — one live session, in code (ADR176 r.32).

The standing direction ("1 live session + parquet export") is load-bearing
twice over: for the planner (every extra live session multiplies the LIST
partitions any unpruned query must lock — the brief's D5: 693 partitions is
a retention failure, steady state is 9) and for the player's disk. This
module makes it CODE, not convention: at campaign boot the loader calls
:func:`enforce_single_live_session` with the campaign being played, and
every OTHER session holding live runtime rows is exported (fail-closed
verified) and purged.

Fail-closed by construction: :func:`~babylon.persistence.archival.
purge_session` verifies the freshly-written manifest against the live
database before deleting anything, and an
:class:`~babylon.persistence.archival.ArchiveVerificationError` BUBBLES —
enforcement stops rather than continuing past a session it could not
archive (Constitution III.11; the purge-gate fail-closed fix, ruling 28).

A purged campaign is not lost: its catalog row keeps the replay identity
(``rng_seed`` + ``content_digest``, ruling 28), its history lives in the
parquet archive under ``archive_root/<session_id>/``, and determinism makes
the campaign a pure function of ``(rng_seed, ContentDigest, tick)`` — the
"rebuild save" recovery story.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from babylon.persistence.archival import (
    export_session_to_parquet,
    purge_session,
)

__all__ = ["default_archive_root", "enforce_single_live_session", "live_sessions"]


def default_archive_root() -> Path:
    """The player-tier archive location, beside the logging estate.

    ``~/.local/share/babylon/archives/`` — the same XDG data home the
    client logs already use (``~/.local/share/babylon/logs/``, the
    2026-07-28 Director logging directive).
    """
    return Path.home() / ".local" / "share" / "babylon" / "archives"


def live_sessions(pool: Any) -> tuple[UUID, ...]:
    """Every session holding live runtime rows, in deterministic order.

    "Live" is adjudicated by the two surfaces that carry a session's real
    state: ``tick_commit`` (the commit markers — the only adjudicator of
    progress since the torn-tick fix) unioned with ``node_state`` (the
    adjudicating topology, which pre-marker or torn sessions may hold
    without markers). A session with rows in neither is already retained.
    """
    with pool.connection() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT session_id FROM tick_commit
            UNION
            SELECT DISTINCT session_id FROM node_state
            ORDER BY session_id
            """
        ).fetchall()
    return tuple(UUID(str(r[0])) for r in rows)


def enforce_single_live_session(
    pool: Any,
    *,
    keep: UUID,
    archive_root: Path,
) -> tuple[UUID, ...]:
    """Export-then-purge every live session except ``keep``.

    :param pool: psycopg ConnectionPool for the runtime database.
    :param keep: The session allowed to stay live (the campaign being
        played; it need not itself be live yet — a fresh boot enforces
        before its first tick commits).
    :param archive_root: Directory receiving one ``<session_id>/`` archive
        per purged session (created as needed).
    :returns: The purged session ids, in the order they were processed.
    :raises ArchiveVerificationError: A session's archive could not be
        verified against the live database — NOTHING further is deleted
        and the error bubbles (fail closed; the sessions already purged
        before the failure stay purged, each behind its own verified
        archive).
    """
    purged: list[UUID] = []
    for session_id in live_sessions(pool):  # loop bound: len(live_sessions)
        if session_id == keep:
            continue
        session_dir = archive_root / str(session_id)
        export_session_to_parquet(pool, session_id, session_dir)
        purge_session(pool, session_id, manifest_path=session_dir / "archive_manifest.json")
        purged.append(session_id)
    return tuple(purged)
