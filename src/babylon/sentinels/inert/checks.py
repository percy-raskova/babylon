"""Inert-sentinel checks: a declared construct must be reachable from production.

Three gating rules, all read statically from source (no engine import, no
Django, no DB — cheap enough for the always-on dev fast-gate):

**(a) Store with no writer.** Every :class:`~babylon.sentinels.inert.registry.
DeclaredStore` row's ``writer_methods`` must have >=1 call site in production
code where the receiver is statically knowable as an instance of the store's
class. This is the founding bug, reconstructed: :class:`IntelLedger`'s
``append()`` had real, passing unit tests and zero production callers, so
every read answered ``"unknown"`` forever.

**(b) Declared-but-uncalled producer.** Every :class:`~babylon.sentinels.
inert.registry.DeclaredProducer` row's ``symbol`` must have >=1 reference in
production code — a direct call, or an indirect one (passed into a registry
dict, handed to a callback parameter) — that is not merely an import alias or
a name inside ``__all__``.

**(c) Undeclared accumulator shape (growth).** Any class in
``PRODUCTION_ROOTS`` shaped like an immutable accumulator/ledger — a frozen
Pydantic model with a method that returns a NEW instance of its own class —
that is NOT named in :data:`~babylon.sentinels.inert.registry.
DECLARED_STORES` is itself a violation: a newly-written store of exactly the
founding shape must be declared (with its real writer verified) before it can
pass review, the same way the vocabulary sentinel forces a new ``_node_type``
string to be declared in the :class:`NodeType` enum first.

**Test files never count as callers** (excluded by :func:`is_test_source`,
regardless of which root they sit under — ``web/game/tests/*.py`` counts the
same as top-level ``tests/``). A test-only caller satisfying rule (a) or (b)
would silently reproduce the exact bug this sentinel exists to catch.

**Scope and known limitations (read before extending).**

- Rule (a)'s receiver-typing is a best-effort static heuristic: a name is
  "typed" as ``class_name`` if it is a direct constructor-call assignment
  (``x = ClassName(...)``), a type-annotated assignment/parameter mentioning
  ``class_name`` anywhere in the annotation (``x: ClassName``, ``x:
  ClassName | None``), or the result of chaining a declared writer method off
  an already-typed name (a bounded fixed-point pass, since the immutable
  pattern returns the same class). It does **not** perform real type
  inference, so a name that only becomes typed via a helper function's return
  type, or via unpacking/destructuring, is invisible to it — a FALSE NEGATIVE
  (the check could under-report a real caller as absent). Given the
  documented founding case has zero callers of any shape, this limitation is
  currently unexercised; if a future row's writer is called only through such
  a path and this check wrongly reds, extend :func:`_typed_receivers` rather
  than silence the row.
- Rule (b) does NOT resolve ``getattr(module, "symbol_name")`` string-keyed
  indirection (the string is indistinguishable from an unrelated string
  literal without value-flow analysis) — a real caller reached ONLY that way
  would be invisible. No known production code uses this pattern for the
  seeded row; documented here rather than silently assumed absent.
- Rule (b) checks *the function is referenced*, not that its RETURN VALUE is
  ever read downstream. ``compute_reification_buffer`` has exactly one
  production caller (``ideology.py``, writing into
  ``material_conditions["reification_buffer"]``), which satisfies this rule
  — but nothing downstream reads that dict key yet. That "computed but never
  consumed" gap is a *different*, not-yet-built sentinel (see the registry
  module's docstring); conflating the two here would make this sentinel lie
  about what it actually proves.
- Rule (c)'s shape detector is intentionally narrow (frozen model + a
  self-returning method) to keep its false-positive rate at zero: verified
  against the current tree, it matches exactly the two rows already in
  :data:`DECLARED_STORES` and nothing else. It does not attempt to detect
  every possible "store" shape (a mutable, non-Pydantic accumulator; a
  frozen-dataclass ledger; a store expressed as a bare dict) — extending
  detection to those shapes is future work, not silently claimed here.
"""

from __future__ import annotations

import argparse
import ast
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Final

from babylon.sentinels.base import LabelledCheck, SentinelCheckError, run_sensor
from babylon.sentinels.inert.registry import (
    DECLARED_PRODUCERS,
    DECLARED_STORES,
    INERT_EXEMPTIONS,
    PRODUCTION_ROOTS,
    DeclaredProducer,
    DeclaredStore,
)

__all__ = [
    "detect_accumulator_classes",
    "is_test_source",
    "main",
    "producer_reference_sites",
    "producers_without_production_caller",
    "store_writer_call_sites",
    "stores_without_production_writer",
    "undeclared_accumulator_stores",
]

#: Repo root (this file is ``<root>/src/babylon/sentinels/inert/checks.py``).
_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[4]

#: A fixed, statically-provable upper bound on the writer-method chaining
#: fixed-point (Constitution "no unbounded loop" discipline) — five passes is
#: far more than any real immutable-update chain in this codebase needs.
_MAX_CHAIN_PASSES: Final[int] = 5

_WHY_STORE: Final[str] = (
    "WHY THIS FAILS: a store whose only callers are tests is a closed loop with no "
    "external referent -- every production read answers the empty/default value "
    "forever, and the tests stay green because they exercise the READ path over data "
    "they themselves wrote. This is not hypothetical: IntelLedger.append() had 8 "
    "passing test files and zero production callers, so read_intel() could only ever "
    "answer 'unknown'."
)

_WHY_PRODUCER: Final[str] = (
    "WHY THIS FAILS: a function only tests call is dead code with a heartbeat -- it "
    "computes a real value that nothing in a live run will ever ask for. "
    "Constitution III.10 (Earn-Its-Keep) requires a construct ship with a LAW, a "
    "PREDICTION, or a COMPUTATION that something ELSE consumes -- never as vocabulary "
    "that only its own tests invoke."
)

_WHY_GROWTH: Final[str] = (
    "WHY THIS FAILS: this class matches the exact shape of the founding bug (a frozen "
    "model whose update method returns a new instance) -- undeclared, nothing proves "
    "its writer is real, which is precisely how IntelLedger went unnoticed. Declare it "
    "so the sentinel can verify it, the same way a new graph node type must be added "
    "to NodeType before it can be stamped or queried."
)


def is_test_source(path: Path) -> bool:
    """True iff ``path`` is a test file by pytest convention.

    Matches on the file's own name (``conftest.py``, ``test_*.py``,
    ``*_test.py``) OR any ancestor directory literally named ``tests`` —
    catching nested test trees (``web/game/tests/*.py``), not just a
    top-level ``tests/`` root.

    :param path: The file to classify.
    :returns: Whether the file is a test file (and must never count as a
        production caller).
    """
    return (
        path.name == "conftest.py"
        or path.stem.startswith("test_")
        or path.stem.endswith("_test")
        or "tests" in path.parts
    )


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


def _production_files(roots: tuple[str, ...] = PRODUCTION_ROOTS) -> Iterator[Path]:
    """Yield every non-test ``.py`` file under ``roots``, sorted (deterministic).

    :param roots: Repo-relative root directories to walk.
    :returns: Production (non-test) Python files, in a stable order.
    :raises SentinelCheckError: If a root directory is missing.
    """
    for root in roots:
        base = _REPO_ROOT / root
        if not base.is_dir():
            raise SentinelCheckError(f"scan root missing: {base} (cannot verify reachability)")
        for path in sorted(base.rglob("*.py")):
            if is_test_source(path):
                continue
            if "node_modules" in path.parts or "__pycache__" in path.parts:
                continue
            yield path


def _dotted_name(node: ast.expr) -> str | None:
    """Render a ``Name`` or a simple attribute chain (``self.x``, ``a.b.c``)
    as a dotted string, or ``None`` if ``node`` is neither.

    :param node: The expression to render.
    :returns: The dotted-name string, or ``None``.
    """
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted_name(node.value)
        return f"{base}.{node.attr}" if base is not None else None
    return None


def _mentions_class(annotation: ast.expr | None, class_name: str) -> bool:
    """True iff a type annotation mentions ``class_name`` anywhere in it.

    Handles the bare form (``ClassName``) and any container/union form
    (``ClassName | None``, ``Optional[ClassName]``, ``list[ClassName]``) by
    walking the whole annotation subtree for a matching :class:`ast.Name`.

    :param annotation: The annotation expression (``None`` if absent).
    :param class_name: The class name to look for.
    :returns: Whether the annotation mentions the class.
    """
    if annotation is None:
        return False
    return any(
        isinstance(node, ast.Name) and node.id == class_name for node in ast.walk(annotation)
    )


def _directly_typed_names(tree: ast.Module, class_name: str) -> tuple[set[str], list[ast.Assign]]:
    """Names typed by a constructor-call assignment or a type annotation.

    :param tree: A parsed module.
    :param class_name: The store's class name.
    :returns: ``(typed_names, all_assign_nodes)`` — the assigns are returned
        alongside so :func:`_close_writer_chains` need not re-walk the tree.
    """
    typed: set[str] = set()
    assigns: list[ast.Assign] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            assigns.append(node)
            if (
                isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id == class_name
            ):
                for target in node.targets:
                    dotted = _dotted_name(target)
                    if dotted:
                        typed.add(dotted)
        elif isinstance(node, ast.AnnAssign) and _mentions_class(node.annotation, class_name):
            dotted = _dotted_name(node.target)
            if dotted:
                typed.add(dotted)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            all_args = (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)
            for arg in all_args:
                if _mentions_class(arg.annotation, class_name):
                    typed.add(arg.arg)
    return typed, assigns


def _close_writer_chains(
    typed: set[str], assigns: list[ast.Assign], writer_methods: tuple[str, ...]
) -> None:
    """Extend ``typed`` in place over writer-method chains, to a fixed point.

    ``y = x.writer_method(...)`` also types ``y``, since the immutable-update
    pattern returns the same class — bounded to :data:`_MAX_CHAIN_PASSES`
    passes (Constitution: no unbounded loop).

    :param typed: The already-typed dotted names (mutated in place).
    :param assigns: Every ``Assign`` node in the file.
    :param writer_methods: The store's declared writer method names.
    """
    for _pass in range(_MAX_CHAIN_PASSES):
        grew = False
        for node in assigns:
            if not (
                isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Attribute)
                and node.value.func.attr in writer_methods
            ):
                continue
            receiver = _dotted_name(node.value.func.value)
            if receiver not in typed:
                continue
            for target in node.targets:
                dotted = _dotted_name(target)
                if dotted and dotted not in typed:
                    typed.add(dotted)
                    grew = True
        if not grew:
            break


def _typed_receivers(
    tree: ast.Module, class_name: str, writer_methods: tuple[str, ...]
) -> set[str]:
    """Best-effort set of dotted names statically known to hold a
    ``class_name`` instance within one file.

    Three sources, in order: a direct constructor-call assignment
    (``x = ClassName(...)``); a type-annotated assignment or function
    parameter whose annotation mentions ``class_name``; and a bounded
    fixed-point closure over writer-method chains — see the module
    docstring's Scope section for what this heuristic does NOT catch.

    :param tree: A parsed module.
    :param class_name: The store's class name.
    :param writer_methods: The store's declared writer method names.
    :returns: The set of dotted names known to hold a ``class_name`` instance.
    """
    typed, assigns = _directly_typed_names(tree, class_name)
    _close_writer_chains(typed, assigns, writer_methods)
    return typed


def store_writer_call_sites(
    path: Path, class_name: str, writer_methods: tuple[str, ...]
) -> list[int]:
    """Line numbers in ``path`` where a ``class_name`` receiver calls a writer.

    :param path: Source file to parse.
    :param class_name: The store's class name.
    :param writer_methods: The store's declared writer method names.
    :returns: Sorted, de-duplicated line numbers of matching call sites.
    :raises SentinelCheckError: If ``path`` is missing or unparseable.
    """
    tree = _parse(path)
    typed = _typed_receivers(tree, class_name, writer_methods)
    sites: set[int] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in writer_methods
        ):
            receiver = _dotted_name(node.func.value)
            if receiver is not None and receiver in typed:
                sites.add(node.lineno)
    return sorted(sites)


def producer_reference_sites(path: Path, symbol: str, def_file: str) -> list[int]:
    """Line numbers in ``path`` where ``symbol`` is referenced as production code.

    Counts any :class:`ast.Name` or :class:`ast.Attribute` node matching
    ``symbol`` in a ``Load`` context — a direct call (``symbol(...)``), an
    indirect reference (``registry.register("x", symbol)``,
    ``module.symbol``), or a bare pass-as-callback. Import aliases and
    ``__all__`` string entries are never :class:`ast.Name`/:class:`ast.
    Attribute` nodes, so they are structurally excluded already — a bare
    import or re-export does not, by itself, count as reachability.

    When ``path`` IS ``def_file`` (the symbol's own declaring file), any
    reference inside that symbol's own top-level ``def``/``class`` body is
    excluded: a function referencing itself recursively is not evidence that
    anything ELSE reaches it.

    :param path: Source file to parse.
    :param symbol: The producer's bare module-level name.
    :param def_file: The producer's declared ``def_file`` (repo-relative).
    :returns: Sorted, de-duplicated line numbers of matching reference sites.
    :raises SentinelCheckError: If ``path`` is missing or unparseable.
    """
    tree = _parse(path)
    # Resolved-path comparison (not relative_to()) so this also works when
    # `path` sits outside `_REPO_ROOT` entirely (a tmp_path fixture in the
    # unit tests) -- relative_to() would raise ValueError in that case.
    is_own_file = path.resolve() == (_REPO_ROOT / def_file).resolve()
    skip_ranges: list[tuple[int, int]] = []
    if is_own_file:
        for top_level_node in tree.body:
            if (
                isinstance(top_level_node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                and top_level_node.name == symbol
            ):
                skip_ranges.append(
                    (top_level_node.lineno, top_level_node.end_lineno or top_level_node.lineno)
                )

    def _in_own_body(lineno: int) -> bool:
        return any(start <= lineno <= end for start, end in skip_ranges)

    sites: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            matched = node.id == symbol and isinstance(node.ctx, ast.Load)
        elif isinstance(node, ast.Attribute):
            matched = node.attr == symbol and isinstance(node.ctx, ast.Load)
        else:
            continue
        if matched and not _in_own_body(node.lineno):
            sites.add(node.lineno)
    return sorted(sites)


def _exempted_names() -> frozenset[str]:
    """The set of row names carrying a recorded :class:`InertExemption`.

    :returns: Exempted row names (empty today — see the registry module).
    """
    return frozenset(row.name for row in INERT_EXEMPTIONS)


def stores_without_production_writer(
    registry: tuple[DeclaredStore, ...] = DECLARED_STORES,
) -> list[str]:
    """Rule (a): every declared store's writer method needs a production caller.

    :param registry: The rows to check (defaults to the real
        :data:`DECLARED_STORES`; injectable so tests can supply a
        deliberately-uncalled row to prove the sensor reds).
    :returns: One violation string per unwired store (empty when all are wired).
    :raises SentinelCheckError: If a scan root is missing or a file is
        unparseable (exit 2 — infrastructure failure, never a silent pass).
    """
    exempted = _exempted_names()
    violations: list[str] = []
    for row in registry:
        if row.name in exempted:
            continue
        sites: list[str] = []
        for path in _production_files():
            for lineno in store_writer_call_sites(path, row.class_name, row.writer_methods):
                sites.append(f"{path.relative_to(_REPO_ROOT).as_posix()}:{lineno}")
        if sites:
            continue
        methods = "/".join(row.writer_methods)
        violations.append(
            f"store {row.name!r} ({row.class_name} in {row.def_file}) has NO production "
            f"caller of {methods}() anywhere in {PRODUCTION_ROOTS}.\n"
            f"    what it stores: {row.what_it_stores}\n"
            f"    consequence: {row.failure_if_unwired}\n"
            "    fix: wire a real production writer, or add a reasoned InertExemption "
            "(name, owner, date, reason) -- never a silent registry removal.\n"
            f"    {_WHY_STORE}"
        )
    return sorted(violations)


def producers_without_production_caller(
    registry: tuple[DeclaredProducer, ...] = DECLARED_PRODUCERS,
) -> list[str]:
    """Rule (b): every declared producer needs a production reference.

    :param registry: The rows to check (defaults to the real
        :data:`DECLARED_PRODUCERS`; injectable so tests can supply a
        deliberately-uncalled row to prove the sensor reds).
    :returns: One violation string per unreferenced producer (empty when all
        are reachable).
    :raises SentinelCheckError: If a scan root is missing or a file is
        unparseable (exit 2 — infrastructure failure, never a silent pass).
    """
    exempted = _exempted_names()
    violations: list[str] = []
    for row in registry:
        if row.name in exempted:
            continue
        sites: list[str] = []
        for path in _production_files():
            for lineno in producer_reference_sites(path, row.symbol, row.def_file):
                sites.append(f"{path.relative_to(_REPO_ROOT).as_posix()}:{lineno}")
        if sites:
            continue
        violations.append(
            f"producer {row.name!r} ({row.symbol} in {row.def_file}) has NO production "
            f"reference anywhere in {PRODUCTION_ROOTS}.\n"
            f"    what it produces: {row.what_it_produces}\n"
            "    fix: wire a real production caller, or add a reasoned InertExemption "
            "(name, owner, date, reason) -- never a silent registry removal.\n"
            f"    {_WHY_PRODUCER}"
        )
    return sorted(violations)


def _is_frozen_model(cls: ast.ClassDef) -> bool:
    """True iff ``cls`` declares ``model_config = ConfigDict(..., frozen=True, ...)``.

    :param cls: A class definition to inspect.
    :returns: Whether the class is a frozen Pydantic model, by this
        syntactic marker.
    """
    for node in cls.body:
        if (
            isinstance(node, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "model_config" for t in node.targets)
            and isinstance(node.value, ast.Call)
        ):
            for kw in node.value.keywords:
                if (
                    kw.arg == "frozen"
                    and isinstance(kw.value, ast.Constant)
                    and kw.value.value is True
                ):
                    return True
    return False


def _self_returning_methods(cls: ast.ClassDef) -> tuple[str, ...]:
    """Method names in ``cls`` with a ``return ClassName(...)`` statement.

    :param cls: A class definition to inspect.
    :returns: Sorted, de-duplicated method names matching the
        immutable-update shape (a self-constructing return).
    """
    methods: set[str] = set()
    for node in cls.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for stmt in ast.walk(node):
            if (
                isinstance(stmt, ast.Return)
                and isinstance(stmt.value, ast.Call)
                and isinstance(stmt.value.func, ast.Name)
                and stmt.value.func.id == cls.name
            ):
                methods.add(node.name)
                break
    return tuple(sorted(methods))


#: One detected accumulator-shaped class: ``(rel_path, class_name, methods)``.
DetectedStore = tuple[str, str, tuple[str, ...]]


def detect_accumulator_classes(roots: tuple[str, ...] = PRODUCTION_ROOTS) -> list[DetectedStore]:
    """Structurally detect the "immutable accumulator/ledger" shape.

    A class matches when it is a frozen Pydantic model (see
    :func:`_is_frozen_model`) AND declares at least one method that returns a
    NEW instance of its own class (see :func:`_self_returning_methods`) — the
    exact shape of :class:`IntelLedger` and :class:`ClassDistribution`.
    Verified against the current tree (2026-07-18): exactly these two classes
    match, and nothing else in ``src``/``web`` does.

    :param roots: Repo-relative root directories to scan.
    :returns: Sorted ``(rel_path, class_name, methods)`` triples.
    :raises SentinelCheckError: If a scan root is missing or a file is
        unparseable.
    """
    hits: list[DetectedStore] = []
    for path in _production_files(roots):
        tree = _parse(path)
        rel = path.relative_to(_REPO_ROOT).as_posix()
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and _is_frozen_model(node):
                methods = _self_returning_methods(node)
                if methods:
                    hits.append((rel, node.name, methods))
    return sorted(hits)


def undeclared_accumulator_stores(
    registry: tuple[DeclaredStore, ...] = DECLARED_STORES,
) -> list[str]:
    """Rule (c) — growth: every detected accumulator class must be declared.

    :param registry: The rows to check membership against (defaults to the
        real :data:`DECLARED_STORES`).
    :returns: One violation per detected-but-undeclared class (empty when the
        registry accounts for every match).
    :raises SentinelCheckError: If a scan root is missing or a file is
        unparseable.
    """
    declared = {(row.def_file, row.class_name) for row in registry}
    violations: list[str] = []
    for rel, class_name, methods in detect_accumulator_classes():
        if (rel, class_name) in declared:
            continue
        violations.append(
            f"{rel}: class {class_name!r} matches the immutable-accumulator/ledger shape "
            f"(frozen model + self-returning method(s) {', '.join(methods)}) but has no "
            "DeclaredStore row.\n"
            "    fix: add a DeclaredStore row naming its real writer method(s) so this "
            "sentinel can verify a production caller exists.\n"
            f"    {_WHY_GROWTH}"
        )
    return sorted(violations)


#: All three rules gate: an unwired store, an unreferenced producer, or an
#: undeclared accumulator shape are each a live defect, not an observation.
_GATING_CHECKS: Final[tuple[LabelledCheck, ...]] = (
    ("store-with-no-writer", stores_without_production_writer),
    ("declared-but-uncalled-producer", producers_without_production_caller),
    ("undeclared-accumulator-store", undeclared_accumulator_stores),
)


def _summary(advisory_count: int) -> str:
    """Clean one-line summary: the counts actually enforced.

    :param advisory_count: Number of advisory findings (0 — no advisory tier).
    :returns: The summary line.
    """
    _ = advisory_count  # This sentinel declares no advisory tier.
    return (
        f"INERT clean: {len(DECLARED_STORES)} declared store(s) and "
        f"{len(DECLARED_PRODUCERS)} declared producer(s) all have a production caller; "
        "no undeclared accumulator-shaped class found."
    )


def main(argv: list[str] | None = None) -> int:
    """Run the inert-construct reachability check and return the exit code.

    :param argv: CLI args (``--check`` is accepted as the CI-mode alias; the
        behavior is always to gate).
    :returns: 0 clean, 1 gating violations found, 2 infrastructure failure.
    """
    parser = argparse.ArgumentParser(
        description="Declared-construct reachability — static gate (III.10 / III.11 / VIII.12)."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="CI-mode alias; the tool always gates (exit 1 on violations).",
    )
    parser.parse_args(argv)
    return run_sensor("INERT", _GATING_CHECKS, (), _summary)


if __name__ == "__main__":
    sys.exit(main())
