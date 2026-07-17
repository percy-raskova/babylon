"""Declared-synthetic-data coherence (static gate).

Proves, without importing or running any of the layers ``babylon.sentinels``
may not reach (``web``, ``babylon.engine``, ``babylon.domain`` — see the
import-linter contract in ``pyproject.toml``), that every declared row in
:data:`babylon.sentinels.synthetic.registry.SYNTHETIC_SOURCES` is
**coherent**: both its ``source_symbol`` (the thing that fabricates/defaults
data) and its ``guard_symbol`` (the thing that keeps that fabrication from
reaching a production run unrecorded) still exist at their declared module
paths. This is Babylon's mechanical guard against a sanctioned synthetic
source silently outliving its guard — a DEBUG check deleted, a tally class
renamed, a scenario ABC moved — while the registry still vouches for it
(Constitution III.11 Loud Failure, VIII.12 no disarmed guardrail).

**Static by contract.** Every check reads its target file with :mod:`ast` (no
import, no execution) — ``web/game/stub_bridge.py`` and
``web/game/api.py`` pull in Django, and ``src/babylon/domain/economics/*`` /
``src/babylon/engine/*`` sit above the sentinels' layer-0.5 import boundary,
so existence is proven against the *file*, mirroring the coverage and seam
Sensor-1 pattern.

**Scope.** This sensor proves *coherence* (the named symbols exist). It does
NOT re-verify the runtime behavior each guard claims (e.g. that ``_get_bridge``
actually raises under ``DEBUG=False``) — that is the job of the dynamic tests
named in each row's ``invariant`` field (e.g.
``tests/unit/web/test_stub_bridge_guard.py``).

Run via the family runner; exit 0 = clean, 1 = incoherent row, 2 =
infrastructure failure (declared file missing/unparseable — itself a loud
failure).
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

from babylon.sentinels.base import LabelledCheck, SentinelCheckError, run_sensor
from babylon.sentinels.synthetic.registry import SYNTHETIC_SOURCES, SyntheticSource

#: Repo root (this file is ``<root>/src/babylon/sentinels/synthetic/checks.py``).
_REPO_ROOT: Path = Path(__file__).resolve().parents[4]


def _parse(path: Path) -> ast.Module:
    """Read and parse ``path`` with :mod:`ast`, raising loudly on failure.

    :param path: Source file to parse.
    :returns: The parsed module.
    :raises SentinelCheckError: If the file is missing or unparseable — an
        infrastructure failure, never swallowed into a false pass.
    """
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SentinelCheckError(f"cannot read {path}: {exc}") from exc
    try:
        return ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        raise SentinelCheckError(f"cannot parse {path}: {exc}") from exc


def _body_names(body: list[ast.stmt]) -> set[str]:
    """Collect the names a statement list binds at its own scope.

    Covers class/function definitions and plain (``Assign``) or annotated
    (``AnnAssign``) name bindings — enough to resolve a module-level constant,
    a dataclass field, a class, or a method/function without importing it.

    :param body: A module's or class's ``.body`` statement list.
    :returns: The set of names bound directly in ``body``.
    """
    names: set[str] = set()
    for node in body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


def _class_def(tree: ast.Module, class_name: str) -> ast.ClassDef | None:
    """Find a module-level ``class_name`` definition, if any.

    :param tree: A parsed module.
    :param class_name: The class name to look up at module scope.
    :returns: The ``ClassDef`` node, or ``None`` if no such top-level class exists.
    """
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    return None


def symbol_exists(path: Path, dotted_symbol: str) -> bool:
    """Statically check that a (possibly one-level-dotted) symbol exists in ``path``.

    Supports a bare module-level name (``"StubEngineBridge"``,
    ``"_DEFAULT_EMPLOYMENT"``) or one level of dotted attribute access into a
    module-level class (``"ServiceContainer.employment_source"``,
    ``"TickDynamicsSystem._compute_national_params"``) — enough to name a
    class, function, module constant, dataclass field, or method without
    importing or running the module.

    :param path: Source file to parse.
    :param dotted_symbol: A bare name, or ``"ClassName.attr"``.
    :returns: Whether the symbol resolves.
    :raises SentinelCheckError: If ``path`` is missing or unparseable.
    """
    tree = _parse(path)
    if "." not in dotted_symbol:
        return dotted_symbol in _body_names(tree.body)
    class_name, _, attr_name = dotted_symbol.partition(".")
    class_node = _class_def(tree, class_name)
    if class_node is None:
        return False
    return attr_name in _body_names(class_node.body)


def check_sources_and_guards_exist(
    registry: tuple[SyntheticSource, ...] = SYNTHETIC_SOURCES,
) -> list[str]:
    """Every declared row's source symbol AND guard symbol must still exist.

    For each row, resolve ``source_file``/``guard_file`` against the repo
    root, parse each, and assert ``source_symbol``/``guard_symbol`` resolve
    (see :func:`symbol_exists`). A row citing a symbol either file no longer
    defines is an incoherent registration — either the fabrication moved
    silently, or worse, its guard did — and reds the gate.

    :param registry: The rows to check (defaults to the real
        :data:`SYNTHETIC_SOURCES`; injectable so tests can supply a
        deliberately broken row to prove the sensor reds).
    :returns: Sorted violation strings (empty when every row is coherent).
    :raises SentinelCheckError: If any declared file is missing or
        unparseable (an infrastructure failure, distinct from an incoherent row).
    """
    violations: list[str] = []
    for row in registry:
        source_path = _REPO_ROOT / row.source_file
        if not symbol_exists(source_path, row.source_symbol):
            violations.append(
                f"source {row.name!r} names source_symbol {row.source_symbol!r} but "
                f"{row.source_file} defines no such symbol (renamed/moved/deleted? "
                "the synthetic source is orphaned from its registry row)"
            )
        guard_path = _REPO_ROOT / row.guard_file
        if not symbol_exists(guard_path, row.guard_symbol):
            violations.append(
                f"source {row.name!r} names guard_symbol {row.guard_symbol!r} but "
                f"{row.guard_file} defines no such symbol (guard renamed/moved/deleted? "
                "this synthetic source may now be UNGUARDED)"
            )
    return sorted(violations)


#: Gating checks: a violation reds the dev fast-gate (exit 1).
_GATING_CHECKS: tuple[LabelledCheck, ...] = (
    (
        "declared synthetic source or its guard no longer exists",
        check_sources_and_guards_exist,
    ),
)

#: No advisory tier yet — every known synthetic/fallback source is registered.
_ADVISORY_CHECKS: tuple[LabelledCheck, ...] = ()


def _summary(advisory_count: int) -> str:
    """Build the clean one-line summary printed when no gating violation occurred.

    :param advisory_count: Number of advisory findings (0 — no advisory tier yet).
    :returns: The summary line naming the count of coherent registered sources.
    """
    summary = (
        f"Declared synthetic data (static): clean — {len(SYNTHETIC_SOURCES)} sanctioned "
        "sources coherent (source + guard symbols exist)."
    )
    if advisory_count:
        summary += f" ({advisory_count} advisory findings above.)"
    return summary


def main(argv: list[str] | None = None) -> int:
    """Run the declared-synthetic-data coherence check and return the exit code.

    :param argv: CLI args (``--check`` is accepted as the CI-mode alias; the
        behavior is always to gate).
    :returns: 0 clean, 1 incoherent row, 2 infrastructure failure.
    """
    parser = argparse.ArgumentParser(
        description="Declared synthetic data — static coherence (III.11 / VIII.12 gate)."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="CI-mode alias; the tool always gates (exit 1 on violations).",
    )
    parser.parse_args(argv)
    return run_sensor("SYNTHETIC", _GATING_CHECKS, _ADVISORY_CHECKS, _summary)


if __name__ == "__main__":
    sys.exit(main())
