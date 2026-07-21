"""Absence sentinel: every sqlite connect site carries a cited disposition.

Instance of the Sentinel pattern guarding the "auto-create masks absence"
invariant (task #64): ``sqlite3.connect(path)``/SQLAlchemy's
``create_engine("sqlite:///path")`` both silently CREATE an empty database
when ``path`` does not exist, turning a loud, actionable absence into a
baffling downstream ``no such table: X`` two systems later (the 2026-07-20
G1 nightly incident this sentinel is named for). Part A of task #64 closed
the one constitutional entry point this bit
(``babylon.reference.database.get_reference_session``); this static scanner
is the growth mechanism that keeps every OTHER sqlite connect site honest --
:mod:`babylon.sentinels.absence.registry` is the declared-invariant registry,
this module is the check.

Three gating rules, all read statically from source (no engine import, no DB
connection of its own -- cheap enough for the always-on fast gate):

**(1) Growth gate.** Every file under ``src/babylon`` containing a
non-memory sqlite connect site (:func:`find_connect_sites`) must have a
:class:`~babylon.sentinels.absence.registry.ConnectionDisposition` row. An
unregistered file is exactly how the founding incident happened: nobody
looked at the site, so nobody noticed it could silently create an empty DB.

**(2) Backslide gate.** A file registered ``"readonly_uri"`` must have
EVERY one of its connect sites classified read-only (a resolved ``mode=ro``
URI literal). A new writable call added to an otherwise-read-only file is a
silent regression of the declared safety property.

**(3) Stale-row gate.** A registry row whose file no longer contains ANY
connect site (the code moved, was deleted, or was refactored away) is a
violation -- the row describes a call site that no longer exists, the same
"declaration outlived its target" drift the vocabulary/unconsumed families
already guard against for their own registries.

Classification (per connect site, :func:`find_connect_sites`):

- ``:memory:`` (an exact literal) -- auto-pass, never counted as a "hit" for
  gates (1)/(2), though it still counts toward gate (3)'s "does this file
  still have ANY site" liveness check.
- a resolved literal/f-string containing ``"mode=ro"`` -- ``"readonly"``.
- everything else (an unresolvable dynamic argument, or a resolved literal
  without ``mode=ro``) -- ``"writable"``, the disposition-requiring case.

Scope note: only ``sqlite3.connect(...)`` calls and ``create_engine(...)``
calls whose first argument is PROVABLY sqlite (a literal/f-string containing
``"sqlite"``, or a bare module-level Name resolved to one) are considered --
a ``create_engine(url)`` call over an opaque parameter (e.g.
``persistence/database.py``'s generic ``DatabaseConnection`` wrapper, whose
default is a sqlite URL but whose actual argument at any call site is an
unresolvable parameter) is invisible to this static scan by design, the same
"cannot resolve without value-flow analysis" limitation the dangling/inert
sentinels document for their own computed-name cases.
"""

from __future__ import annotations

import argparse
import ast
import sys
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Final, Literal, NamedTuple

from babylon.sentinels._ast import parse_module
from babylon.sentinels.absence.registry import CONNECTION_DISPOSITIONS, ConnectionDisposition
from babylon.sentinels.base import LabelledCheck, SentinelCheckError, run_sensor
from babylon.sentinels.report import finding

__all__ = [
    "ConnectSite",
    "check_readonly_backslide",
    "check_stale_dispositions",
    "check_unregistered_connections",
    "find_connect_sites",
    "main",
]

#: Repo root (this file is ``<root>/src/babylon/sentinels/absence/checks.py``,
#: the same nesting depth as ``aggregation/checks.py``).
_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[4]

#: The one tree this sentinel scans -- narrower than vocabulary/inert's
#: ``src``/``web``/``tests`` sweep, because every sqlite connect site in this
#: codebase lives under ``src/babylon`` (verified by the ``rg`` census the
#: registry cites).
_SCAN_ROOT: Final[str] = "src/babylon"

#: The exact-literal argument that marks a connect call as memory-only --
#: never a disposition risk (nothing to create on disk).
_MEMORY_LITERAL: Final[str] = ":memory:"

#: Substring that marks a resolved literal/f-string as opening a read-only URI.
_READONLY_MARKER: Final[str] = "mode=ro"


class ConnectSite(NamedTuple):
    """One AST-detected sqlite connection call site.

    :ivar file: Repo-relative POSIX path of the source file.
    :ivar line: 1-indexed source line of the call.
    :ivar kind: Which call form matched.
    :ivar classification: ``"memory"`` (auto-pass), ``"readonly"`` (a
        resolved ``mode=ro`` literal), or ``"writable"`` (everything else --
        the case a registry row must account for).
    """

    file: str
    line: int
    kind: Literal["sqlite3.connect", "create_engine"]
    classification: Literal["memory", "readonly", "writable"]


def _literal_text(node: ast.expr) -> str | None:
    """Best-effort literal text of an expression.

    Handles a bare string constant and an f-string's constant parts (joined,
    skipping any interpolated ``{...}`` placeholders) -- the same two forms
    every sqlite connect site in this tree actually uses.

    :param node: The expression to resolve.
    :returns: The literal text, or ``None`` if ``node`` is not one of the two
        recognized literal forms.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(
            part.value
            for part in node.values
            if isinstance(part, ast.Constant) and isinstance(part.value, str)
        )
    return None


def _module_level_literals(tree: ast.Module) -> dict[str, str]:
    """Module-level ``NAME = <literal>`` bindings, resolved to literal text.

    A single-hop resolution (module top-level assignments only, never a
    function-local or a chained alias) -- exactly what
    ``reference/database.py``'s own ``NORMALIZED_DATABASE_URL``/
    ``SOURCE_DATABASE_URL`` module constants need to be visible as sqlite
    ``create_engine`` arguments.

    :param tree: A parsed module.
    :returns: Every module-level Name bound to a resolvable literal.
    """
    literals: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        text = _literal_text(node.value)
        if text is None:
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                literals[target.id] = text
    return literals


def _resolve_first_arg(call: ast.Call, module_literals: dict[str, str]) -> str | None:
    """Resolve a call's first positional argument to literal text, if possible.

    :param call: The call node (must have at least one positional arg).
    :param module_literals: This file's :func:`_module_level_literals` map.
    :returns: The resolved literal text, or ``None`` if the argument is
        neither a literal itself nor a Name bound to one at module level.
    """
    arg = call.args[0]
    text = _literal_text(arg)
    if text is not None:
        return text
    if isinstance(arg, ast.Name):
        return module_literals.get(arg.id)
    return None


def _classify(text: str | None) -> Literal["memory", "readonly", "writable"]:
    """Classify a connect site by its resolved argument text.

    :param text: The resolved literal text, or ``None`` if unresolvable.
    :returns: ``"memory"`` for the exact ``:memory:`` literal, ``"readonly"``
        when the resolved text carries a ``mode=ro`` marker, ``"writable"``
        otherwise (including every unresolvable argument -- absence of proof
        of safety is not proof of safety).
    """
    if text == _MEMORY_LITERAL:
        return "memory"
    if text is not None and _READONLY_MARKER in text:
        return "readonly"
    return "writable"


def _is_sqlite3_connect(call: ast.Call) -> bool:
    """True iff ``call`` is ``sqlite3.connect(...)``.

    :param call: The call node to inspect.
    :returns: Whether the call's function is the ``connect`` attribute of a
        bare ``sqlite3`` name.
    """
    return (
        isinstance(call.func, ast.Attribute)
        and call.func.attr == "connect"
        and isinstance(call.func.value, ast.Name)
        and call.func.value.id == "sqlite3"
    )


def _is_create_engine(call: ast.Call) -> bool:
    """True iff ``call`` is a bare ``create_engine(...)`` call.

    :param call: The call node to inspect.
    :returns: Whether the call's function is the bare name ``create_engine``.
    """
    return isinstance(call.func, ast.Name) and call.func.id == "create_engine"


def _iter_scanned_files(repo_root: Path, scan_root: str) -> Iterator[Path]:
    """Yield every ``.py`` file under ``repo_root / scan_root``, sorted.

    :param repo_root: Repository root the scan is relative to.
    :param scan_root: Repo-relative root directory to walk.
    :returns: Source files in a stable order, ``__pycache__`` excluded.
    :raises SentinelCheckError: If the scan root is missing.
    """
    base = repo_root / scan_root
    if not base.is_dir():
        raise SentinelCheckError(f"scan root missing: {base} (cannot verify sqlite connect sites)")
    for path in sorted(base.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        yield path


def find_connect_sites(
    repo_root: Path = _REPO_ROOT, scan_root: str = _SCAN_ROOT
) -> tuple[ConnectSite, ...]:
    """Scan for every sqlite connect call site under ``repo_root / scan_root``.

    :param repo_root: Repository root (injectable so tests can point this at
        a synthetic tree under ``tmp_path``).
    :param scan_root: Repo-relative root directory to walk.
    :returns: Every matched site, sorted (file, then line).
    :raises SentinelCheckError: If the scan root is missing, or a scanned
        file is missing/unparseable when read.
    """
    sites: list[ConnectSite] = []
    for path in _iter_scanned_files(repo_root, scan_root):
        rel = path.relative_to(repo_root).as_posix()
        tree = parse_module(path)
        module_literals = _module_level_literals(tree)
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and node.args):
                continue
            if _is_sqlite3_connect(node):
                text = _resolve_first_arg(node, module_literals)
                sites.append(ConnectSite(rel, node.lineno, "sqlite3.connect", _classify(text)))
            elif _is_create_engine(node):
                text = _resolve_first_arg(node, module_literals)
                if text is None or "sqlite" not in text:
                    continue
                sites.append(ConnectSite(rel, node.lineno, "create_engine", _classify(text)))
    return tuple(sorted(sites))


def _sites_by_file(sites: Iterable[ConnectSite]) -> dict[str, tuple[ConnectSite, ...]]:
    """Group connect sites by their file.

    :param sites: Sites to group.
    :returns: Each file mapped to its sites, in the order they were given.
    """
    by_file: dict[str, list[ConnectSite]] = {}
    for site in sites:
        by_file.setdefault(site.file, []).append(site)
    return {file: tuple(group) for file, group in by_file.items()}


def check_unregistered_connections(
    sites: tuple[ConnectSite, ...] | None = None,
    dispositions: dict[str, ConnectionDisposition] | None = None,
) -> list[str]:
    """Growth gate: every file with a non-memory connect site must be registered.

    :param sites: Connect sites to check (defaults to a fresh
        :func:`find_connect_sites` scan of the real tree; injectable so tests
        can supply a synthetic scan).
    :param dispositions: The registry to check against (defaults to the real
        :data:`~babylon.sentinels.absence.registry.CONNECTION_DISPOSITIONS`).
    :returns: One finding per unregistered file (empty when every file with a
        non-memory hit is registered).
    :raises SentinelCheckError: If the scan root is missing/unparseable.
    """
    if sites is None:
        sites = find_connect_sites()
    if dispositions is None:
        dispositions = CONNECTION_DISPOSITIONS
    by_file = _sites_by_file(site for site in sites if site.classification != "memory")
    findings: list[str] = []
    for file, file_sites in sorted(by_file.items()):
        if file in dispositions:
            continue
        first = min(file_sites, key=lambda site: site.line)
        findings.append(
            finding(
                error_class="unregistered-connection",
                symbol=first.kind,
                file=file,
                line=first.line,
                problem=(
                    "opens a sqlite connection with no ConnectionDisposition row -- an "
                    "absent database file here would silently auto-create instead of "
                    "failing loudly"
                ),
                remedy=(
                    "add a ConnectionDisposition row to "
                    "src/babylon/sentinels/absence/registry.py naming the disposition "
                    "(readonly_uri/guarded/creates_own_store/canonical/declared_debt) and "
                    "citing the evidence"
                ),
            )
        )
    return sorted(findings)


def check_readonly_backslide(
    sites: tuple[ConnectSite, ...] | None = None,
    dispositions: dict[str, ConnectionDisposition] | None = None,
) -> list[str]:
    """Backslide gate: a ``readonly_uri`` file's connect sites must ALL be read-only.

    :param sites: Connect sites to check (see :func:`check_unregistered_connections`).
    :param dispositions: The registry to check against.
    :returns: One finding per writable site inside a ``readonly_uri`` file.
    :raises SentinelCheckError: If the scan root is missing/unparseable.
    """
    if sites is None:
        sites = find_connect_sites()
    if dispositions is None:
        dispositions = CONNECTION_DISPOSITIONS
    by_file = _sites_by_file(sites)
    findings: list[str] = []
    for file, row in sorted(dispositions.items()):
        if row.disposition != "readonly_uri":
            continue
        for site in by_file.get(file, ()):
            if site.classification != "writable":
                continue
            findings.append(
                finding(
                    error_class="readonly-backslide",
                    symbol=site.kind,
                    file=file,
                    line=site.line,
                    problem=(
                        "registered readonly_uri but this connect call cannot be proven "
                        "read-only (no resolvable mode=ro literal) -- a backslide from the "
                        "declared disposition"
                    ),
                    remedy=(
                        "open with a `file:...?mode=ro` URI, matching this file's other "
                        "connect sites, or update the registry disposition if this call is "
                        "legitimately writable"
                    ),
                )
            )
    return sorted(findings)


def check_stale_dispositions(
    sites: tuple[ConnectSite, ...] | None = None,
    dispositions: dict[str, ConnectionDisposition] | None = None,
) -> list[str]:
    """Stale-row gate: a registered file must still contain a connect site.

    :param sites: Connect sites to check (see :func:`check_unregistered_connections`;
        memory sites count here -- ANY site keeps a row live).
    :param dispositions: The registry to check against.
    :returns: One finding per registry row whose file no longer has any site.
    :raises SentinelCheckError: If the scan root is missing/unparseable.
    """
    if sites is None:
        sites = find_connect_sites()
    if dispositions is None:
        dispositions = CONNECTION_DISPOSITIONS
    files_with_any_site = {site.file for site in sites}
    findings: list[str] = []
    for file, row in sorted(dispositions.items()):
        if file in files_with_any_site:
            continue
        findings.append(
            finding(
                error_class="stale-disposition",
                symbol=row.disposition,
                file=file,
                line=0,
                problem=(
                    "registry declares a disposition but the file no longer contains any "
                    "sqlite3.connect/create_engine(sqlite) call -- the row has drifted stale"
                ),
                remedy=(
                    "remove the stale ConnectionDisposition row from registry.py, or verify "
                    "whether the connection moved to another file and register it there instead"
                ),
            )
        )
    return sorted(findings)


#: All three rules gate (task #64: this is the "grows with the codebase"
#: mechanism -- an unregistered/backslid/stale row is a live defect, not
#: advisory noise).
_GATING_CHECKS: Final[tuple[LabelledCheck, ...]] = (
    ("unregistered sqlite connect site", check_unregistered_connections),
    ("readonly_uri backslide", check_readonly_backslide),
    ("stale disposition row", check_stale_dispositions),
)

#: Nothing advisory -- all three rules gate.
_ADVISORY_CHECKS: Final[tuple[LabelledCheck, ...]] = ()


def _summary(advisory_count: int) -> str:
    """Build the clean one-line summary printed when nothing gated.

    :param advisory_count: Number of advisory findings (0 -- no advisory tier).
    :returns: The summary line naming the scan size.
    """
    _ = advisory_count  # This sentinel declares no advisory tier.
    sites = find_connect_sites()
    non_memory_files = {site.file for site in sites if site.classification != "memory"}
    return (
        f"Absence clean: {len(non_memory_files)} file(s) with a non-memory sqlite connect "
        f"site, {len(CONNECTION_DISPOSITIONS)} declared disposition(s) -- every hit is "
        "registered, every readonly_uri file stays read-only, no stale rows."
    )


def main(argv: list[str] | None = None) -> int:
    """Run the absence gate and return the process exit code.

    :param argv: CLI args (``--check`` accepted for family symmetry; this
        sensor always gates regardless).
    :returns: 0 clean, 1 gating violations found, 2 infrastructure failure.
    """
    parser = argparse.ArgumentParser(
        description="Absence -- every sqlite connect site carries a cited disposition.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="CI-mode alias; the tool always gates (exit 1 on violations).",
    )
    parser.parse_args(argv)
    return run_sensor("ABSENCE", _GATING_CHECKS, _ADVISORY_CHECKS, _summary)


if __name__ == "__main__":
    sys.exit(main())
