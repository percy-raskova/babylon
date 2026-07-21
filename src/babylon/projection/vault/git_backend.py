"""dulwich vault repository wrapper: sim-time-pinned commits (Constitution III.13).

Every commit's author/committer timestamp derives solely from the
simulation tick via :func:`babylon.kernel.sim_clock.sim_datetime` — never
wall-clock — with a fixed author/committer identity, so two independent
bakes of identical page content at the same tick produce byte-identical
commit shas (proven by the P0 spike, ``scratchpad/archive-spike/tests/
test_vault_git.py``).

dulwich 1.2 API drift (ADR099): ``stage()``/``commit()`` live on
``repo.get_worktree()``, not on ``Repo`` directly.

dulwich is imported lazily (function-local) so importing this module never
pulls it into ``sys.modules`` merely by being on the import path.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Mapping

from babylon.kernel.sim_clock import sim_datetime

#: Fixed author/committer identity for every vault commit — the vault has
#: one author, The Archive itself, never a wall-clock-derived human identity.
_IDENTITY: Final[bytes] = b"The Archive <archive@babylon.local>"

#: In-process single-writer discipline: the narrator side process (WO-42)
#: commits from its worker thread while the tick baker commits from the
#: main thread, and dulwich's stage/commit sequence is not safe against a
#: concurrent writer on the same index file. One process, one committer at
#: a time — cross-process writers remain out of contract.
_COMMIT_LOCK: Final[threading.Lock] = threading.Lock()


def init_vault(root: Path) -> None:
    """Initialize a dulwich repository at ``root`` if one isn't already there.

    Idempotent: a vault is created once and reused across many bakes over a
    run's lifetime, so a repeat call against an already-initialized root is
    a no-op rather than an error.

    :param root: the vault repository root directory; created if absent.
    """
    from dulwich.repo import Repo

    root.mkdir(parents=True, exist_ok=True)
    if (root / ".git").exists():
        return
    Repo.init(str(root)).close()


def commit_page(
    root: Path,
    relative_path: str,
    content: str,
    *,
    tick: int,
    message: str,
) -> bytes:
    """Write ``content`` to ``relative_path`` under ``root`` and commit it.

    :param root: an initialized vault repo root (see :func:`init_vault`).
    :param relative_path: the page path relative to ``root``, POSIX-style
        (e.g. ``"county/26163.md"``); parent directories are created as
        needed.
    :param content: the exact page content to write — the caller
        (:mod:`babylon.projection.vault.render`) is responsible for
        determinism; this function makes no changes to it.
    :param tick: the simulation tick driving the commit's author/committer
        timestamp via :func:`~babylon.kernel.sim_clock.sim_datetime` —
        never wall-clock.
    :param message: the commit message.
    :returns: the resulting commit sha (40 hex-character bytes).
    """
    from dulwich.repo import Repo

    with _COMMIT_LOCK:
        page_path = root / relative_path
        page_path.parent.mkdir(parents=True, exist_ok=True)
        page_path.write_text(content, encoding="utf8")

        epoch_seconds = int(sim_datetime(tick).timestamp())
        repo = Repo(str(root))
        try:
            worktree = repo.get_worktree()
            worktree.stage([relative_path])
            return worktree.commit(
                message=message.encode("utf8"),
                committer=_IDENTITY,
                author=_IDENTITY,
                commit_timestamp=epoch_seconds,
                commit_timezone=0,
                author_timestamp=epoch_seconds,
                author_timezone=0,
            )
        finally:
            repo.close()


def commit_pages(
    root: Path,
    pages: Mapping[str, str],
    *,
    tick: int,
    message: str,
) -> bytes | None:
    """Write many pages and commit ALL changes as ONE commit (WO-44).

    The vault-at-scale contract: national scope bakes ~3,156 pages per
    tick, so per-page commits would compound into ~1.64M commits over a
    campaign. Two guards keep the repository proportional to *change*,
    not to scope size:

    * **Content-hash skip:** a page whose rendered bytes equal what is
      already on disk is neither rewritten nor staged — an unchanged
      county costs nothing.
    * **One commit per tick:** every page that DID change is staged
      together and committed once. No changes at all → no commit
      (``None``), never an empty commit.

    Determinism: pages are staged in sorted-path order, and the commit
    metadata pins to sim time exactly as :func:`commit_page` — two
    independent bakes of identical content produce identical shas (or
    identically skip).

    :param root: an initialized vault repo root (see :func:`init_vault`).
    :param pages: relative POSIX page path → exact page content.
    :param tick: the simulation tick driving the commit timestamp.
    :param message: the commit message.
    :returns: the commit sha, or ``None`` when every page was unchanged.
    """
    from dulwich.repo import Repo

    with _COMMIT_LOCK:
        changed: list[str] = []
        for relative_path in sorted(pages):
            content_bytes = pages[relative_path].encode("utf8")
            page_path = root / relative_path
            if page_path.exists() and page_path.read_bytes() == content_bytes:
                continue
            page_path.parent.mkdir(parents=True, exist_ok=True)
            page_path.write_bytes(content_bytes)
            changed.append(relative_path)
        if not changed:
            return None

        epoch_seconds = int(sim_datetime(tick).timestamp())
        repo = Repo(str(root))
        try:
            worktree = repo.get_worktree()
            worktree.stage(changed)
            return worktree.commit(
                message=message.encode("utf8"),
                committer=_IDENTITY,
                author=_IDENTITY,
                commit_timestamp=epoch_seconds,
                commit_timezone=0,
                author_timestamp=epoch_seconds,
                author_timezone=0,
            )
        finally:
            repo.close()


__all__ = ["init_vault", "commit_page", "commit_pages"]
