"""Static coherence check for the declared-assumptions ledger.

Proves, without importing or running anything above the sentinels' layer-0.5
boundary, that every row in
:data:`babylon.sentinels.assumptions.registry.DECLARED_ASSUMPTIONS` cites a
``code_ref`` that still exists on disk. This is the mechanical guard against a
declared assumption silently outliving the code it describes — a file moved,
renamed, or deleted while the ledger row still vouches for it (Constitution
III.11 Loud Failure).

**Scope.** This check proves only that the cited *file* exists — it is
deliberately file-grain, not symbol-grain (see
:class:`~babylon.sentinels.assumptions.registry.Assumption`'s docstring for
why). It does not re-verify that the claimed behavior is still accurate; that
is a matter for human review when the cited file changes.
"""

from __future__ import annotations

from pathlib import Path

from babylon.sentinels.assumptions.registry import DECLARED_ASSUMPTIONS, Assumption

#: Repo root (this file is ``<root>/src/babylon/sentinels/assumptions/checks.py``).
_REPO_ROOT: Path = Path(__file__).resolve().parents[4]


def check_code_refs_exist(
    registry: tuple[Assumption, ...] = DECLARED_ASSUMPTIONS,
) -> list[str]:
    """Every declared assumption's ``code_ref`` must exist as a real file.

    :param registry: The rows to check (defaults to the real
        :data:`DECLARED_ASSUMPTIONS`; injectable so tests can supply a
        deliberately broken row to prove the check reds).
    :returns: Sorted violation strings (empty when every row's ``code_ref``
        resolves to a real file).
    """
    violations: list[str] = []
    for row in registry:
        path = _REPO_ROOT / row.code_ref
        if not path.is_file():
            violations.append(
                f"assumption {row.id!r} cites code_ref {row.code_ref!r} but no such file "
                "exists (moved/renamed/deleted? the assumption is orphaned from its cited "
                "code location)"
            )
    return sorted(violations)
