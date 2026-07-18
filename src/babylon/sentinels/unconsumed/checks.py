"""Unconsumed-sentinel checks: a declared computed value must be read.

One gating rule, read statically from source (no engine import, no Django,
no DB — cheap enough for the always-on dev fast-gate):

**Declared computed field with no reader.** Every
:class:`~babylon.sentinels.unconsumed.registry.DeclaredComputedField` row's
``dict_key`` must have >=1 read site in production code — a subscript
(``payload["reification_buffer"]``) or a ``.get()``/``.pop()`` call
(``payload.get("reification_buffer")``) naming that exact string, anywhere
in :data:`~babylon.sentinels.unconsumed.registry.PRODUCTION_ROOTS`, in a
file OTHER than a test file. This is the founding gap, reconstructed:
``compute_reification_buffer`` has a real, passing production caller (the
inert sentinel's own rule already covers that), and STILL the value it
returns is dead the moment it lands on the graph — nothing reads
``material_conditions["reification_buffer"]`` back.

**Test files never count as consumers** (excluded by :func:`is_test_source`,
mirroring :func:`babylon.sentinels.inert.checks.is_test_source` exactly — a
test-only reader satisfying this check would silently reproduce the same
"closed loop, no external referent" bug the inert sentinel guards against
for writers).

**Scope and known limitations (read before extending).**

- The reader detector is a **name-based** heuristic: it matches ANY
  subscript/``.get()``/``.pop()`` naming the declared ``dict_key`` string,
  regardless of which object it is read off. This is deliberately permissive
  (a FALSE NEGATIVE risk in the other direction is impossible here — there is
  no way to under-match a distinctive key string) but carries a FALSE
  POSITIVE risk if two UNRELATED features happen to share a dict key string
  by coincidence (e.g. a different model also has a field named
  ``"reification_buffer"``) — no such collision exists in the current tree
  (grep-verified), and a future one would make this sentinel wrongly report
  "consumed" for a genuinely-dead second field sharing the name. Given
  Constitution III.7 (determinism) makes key names load-bearing identifiers
  throughout this codebase, and given the alternative (full type-directed
  dataflow analysis to prove the SAME value flows to the read site) is far
  outside a layer-0.5 static gate's budget, this trade-off is accepted and
  documented rather than silently assumed away.
- This sentinel does **not** verify the read site actually USES the value
  for anything (a `_ = payload.get("reification_buffer")` dead-store would
  satisfy it) — it verifies REACHABILITY of a read, mirroring how the inert
  sentinel's producer rule (b) verifies a producer is REFERENCED, not that
  its return value is consumed further (see that module's own Scope note —
  this sentinel is the mirror-image gap that rule explicitly declines to
  close). Closing THAT gap would need a third, still-more-invasive sentinel
  and is out of scope here.
- Declared-registry only, no growth/detection rule (mirrors
  :func:`babylon.sentinels.inert.checks.producers_without_production_caller`'s
  own registry-only posture, rule (b) in that module) — a codebase-wide scan
  for "any computed dict key with zero readers" was investigated and
  rejected: nearly every dict key in this codebase is written once and read
  once by design (a normal data-flow, not a defect), so a generic "flag
  every write-only key" rule would drown in false positives. New rows must
  be declared by hand as new Track-1-shaped gaps are discovered.
"""

from __future__ import annotations

import argparse
import ast
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Final

from babylon.sentinels.base import LabelledCheck, SentinelCheckError, run_sensor
from babylon.sentinels.unconsumed.registry import (
    DECLARED_COMPUTED_FIELDS,
    PRODUCTION_ROOTS,
    UNCONSUMED_EXEMPTIONS,
    DeclaredComputedField,
)

__all__ = [
    "computed_fields_without_consumer",
    "is_test_source",
    "main",
    "reader_sites",
]

#: Repo root (this file is ``<root>/src/babylon/sentinels/unconsumed/checks.py``).
_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[4]

_WHY: Final[str] = (
    "WHY THIS FAILS: a value computed and stored every tick but never read back is "
    "vocabulary with a heartbeat, not a working part -- Constitution III.10 "
    "(Earn-Its-Keep) requires a construct ship with a LAW, a PREDICTION, or a "
    "COMPUTATION that something ELSE consumes. This is not hypothetical: "
    "compute_reification_buffer() has a genuine production caller (satisfies the "
    "inert sentinel's own reachability rule) and STILL nothing downstream reads "
    "material_conditions['reification_buffer'] back off the graph."
)


def is_test_source(path: Path) -> bool:
    """True iff ``path`` is a test file by pytest convention.

    Mirrors :func:`babylon.sentinels.inert.checks.is_test_source` exactly
    (duplicated rather than imported — the two sentinels' internals stay
    independently versioned, see the inert sentinel's own module docstring
    for why cross-sentinel coupling is avoided).

    :param path: The file to classify.
    :returns: Whether the file is a test file (and must never count as a
        production reader).
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


def reader_sites(path: Path, dict_key: str) -> list[int]:
    """Line numbers in ``path`` where ``dict_key`` is READ off a mapping.

    Matches a subscript (``x["dict_key"]``) in :class:`ast.Load` context, or
    a ``.get("dict_key", ...)``/``.pop("dict_key", ...)`` call — the two
    syntactic shapes this codebase uses to read a dict key back, mirroring
    :func:`babylon.sentinels._ast._is_type_key_read`'s own two-form pattern
    (duplicated rather than imported for the same independent-versioning
    reason as :func:`is_test_source`).

    :param path: Source file to parse.
    :param dict_key: The exact string key to look for.
    :returns: Sorted, de-duplicated line numbers of matching read sites.
    :raises SentinelCheckError: If ``path`` is missing or unparseable.
    """
    tree = _parse(path)
    sites: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Load):
            sl = node.slice
            if isinstance(sl, ast.Constant) and sl.value == dict_key:
                sites.add(node.lineno)
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in ("get", "pop")
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value == dict_key
        ):
            sites.add(node.lineno)
    return sorted(sites)


def _exempted_names() -> frozenset[str]:
    """The set of row names carrying a recorded :class:`UnconsumedExemption`.

    :returns: Exempted row names (empty today — see the registry module).
    """
    return frozenset(row.name for row in UNCONSUMED_EXEMPTIONS)


def computed_fields_without_consumer(
    registry: tuple[DeclaredComputedField, ...] = DECLARED_COMPUTED_FIELDS,
) -> list[str]:
    """Every declared computed field's dict key needs a production reader.

    :param registry: The rows to check (defaults to the real
        :data:`~babylon.sentinels.unconsumed.registry.DECLARED_COMPUTED_FIELDS`;
        injectable so tests can supply a deliberately-unread row to prove
        the sensor reds).
    :returns: One violation string per unread field (empty when all are
        read somewhere in production).
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
            for lineno in reader_sites(path, row.dict_key):
                sites.append(f"{path.relative_to(_REPO_ROOT).as_posix()}:{lineno}")
        if sites:
            continue
        violations.append(
            f"computed field {row.name!r} (dict_key={row.dict_key!r}, written by "
            f"{row.write_symbol} in {row.write_file}) has NO production reader "
            f"anywhere in {PRODUCTION_ROOTS}.\n"
            f"    what it computes: {row.what_it_computes}\n"
            f"    consequence: {row.consequence_if_unread}\n"
            "    fix: wire a real downstream consumer, or add a reasoned "
            "UnconsumedExemption (name, owner, date, reason) -- never a silent "
            "registry removal.\n"
            f"    {_WHY}"
        )
    return sorted(violations)


#: The one rule gates: an unread computed field is a live defect, not an
#: observation (mirrors the inert sentinel's all-gating posture).
_GATING_CHECKS: Final[tuple[LabelledCheck, ...]] = (
    ("computed-field-with-no-reader", computed_fields_without_consumer),
)


def _summary(advisory_count: int) -> str:
    """Clean one-line summary: the counts actually enforced.

    :param advisory_count: Number of advisory findings (0 — no advisory tier).
    :returns: The summary line.
    """
    _ = advisory_count  # This sentinel declares no advisory tier.
    return (
        f"UNCONSUMED clean: {len(DECLARED_COMPUTED_FIELDS)} declared computed "
        "field(s) all have a production reader."
    )


def main(argv: list[str] | None = None) -> int:
    """Run the unconsumed-value reachability check and return the exit code.

    :param argv: CLI args (``--check`` is accepted as the CI-mode alias; the
        behavior is always to gate).
    :returns: 0 clean, 1 gating violations found, 2 infrastructure failure.
    """
    parser = argparse.ArgumentParser(
        description=("Declared computed-field reader reachability — static gate (III.10 / III.11).")
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="CI-mode alias; the tool always gates (exit 1 on violations).",
    )
    parser.parse_args(argv)
    return run_sensor("UNCONSUMED", _GATING_CHECKS, (), _summary)


if __name__ == "__main__":
    sys.exit(main())
