"""Masked-arithmetic sentinel checks: no unguarded arithmetic on a masked field.

One gating rule, read statically from source (no engine import, no Django,
no DB — cheap enough for the always-on dev fast-gate):

**Unguarded arithmetic on a declared fogged field.** For every
:class:`~babylon.sentinels.masked_arithmetic.registry.DeclaredFoggedConsumer`
row, its ``function_name``'s body must contain, for its ``field``, at least
one ``is not None`` (or equivalent) guard testing that exact
``.get(field[, ...])``/``[field]`` shape — for EVERY site where that same
shape is fed directly (or via a one-level comprehension/generator unwrap)
into an arithmetic call (``float``/``int``/``round``/``abs``/``sum``).
Absent a guard anywhere in the function while an at-risk site exists is a
violation: the exact reconstruction of the founding bug
(``float(o.get("heat", 0.0))`` on an already-fogged, present-but-``None``
value — ``dict.get``'s default only fires on an ABSENT key, never a
present ``None``, so this "looks defended" but is not).

**Scope and known limitations (read before extending).**

- This is a **co-occurrence heuristic, not real control-flow analysis**: a
  guard anywhere in the function is treated as covering every at-risk site
  for that field, regardless of whether the guard's branch actually
  dominates the arithmetic use. A function with an at-risk site on one
  code path and an unrelated guard on a DIFFERENT, non-dominating path
  would false-pass. No such shape exists in the one declared row today
  (verified against the shipped fix); if a future row's real structure
  needs true dominance checking, extend this rather than silently trust a
  coincidental guard.
- **Declared-registry only, no whole-codebase growth rule** — deliberately.
  See the registry module's own docstring for why: distinguishing a
  fog-masked payload read from the engine's own raw-graph read is not
  syntactically decidable (both look like ``x.get("heat", 0.0)``), and a
  codebase-wide scan was hand-verified to produce more than twenty
  false-positive-shaped hits inside ``engine_bridge.py`` alone (pre-fog
  composer functions that build the very payload other functions later
  fog). A gate that cries wolf gets disabled; new fogged-consumer risk
  sites must be added to the registry by hand as they are discovered.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path
from typing import Final, TypeGuard

from babylon.sentinels.base import LabelledCheck, SentinelCheckError, run_sensor
from babylon.sentinels.exemptions import is_exempt
from babylon.sentinels.masked_arithmetic.registry import (
    ARITHMETIC_WRAPPERS,
    DECLARED_FOGGED_CONSUMERS,
    MASKED_ARITHMETIC_EXEMPTIONS,
    DeclaredFoggedConsumer,
)

__all__ = [
    "find_function",
    "guard_exists_for_field",
    "main",
    "unguarded_arithmetic_sites",
    "unguarded_masked_arithmetic",
]

#: Repo root (this file is
#: ``<root>/src/babylon/sentinels/masked_arithmetic/checks.py``).
_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[4]

_WHY: Final[str] = (
    "WHY THIS FAILS: dict.get(key, default)'s default only fires when key is ABSENT -- "
    "fog masks a political field to None while KEEPING the key present (apply_fog's own "
    "contract: 'present but empty, not omitted'), so float(payload.get('heat', 0.0)) does "
    "NOT fall back to 0.0 for a masked field; it raises TypeError on float(None). This is "
    "not hypothetical: _build_state_apparatus_dashboard crashed exactly this way the first "
    "time a state-apparatus org was out of the player's organizing reach."
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


def find_function(
    tree: ast.Module, function_name: str
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    """Locate a top-level function or a ``Class.method`` by dotted name.

    :param tree: A parsed module.
    :param function_name: A bare function name, or ``"Class.method"``.
    :returns: The matching function node, or ``None`` if not found.
    """
    if "." in function_name:
        class_name, method_name = function_name.split(".", 1)
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                for item in node.body:
                    if (
                        isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and item.name == method_name
                    ):
                        return item
        return None
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            return node
    return None


def _is_field_get(node: ast.expr, field: str) -> TypeGuard[ast.Call]:
    """True iff ``node`` is ``<expr>.get("field"[, default])`` (any arity)."""
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "get"
        and bool(node.args)
        and isinstance(node.args[0], ast.Constant)
        and node.args[0].value == field
    )


def _is_field_subscript(node: ast.expr, field: str) -> bool:
    """True iff ``node`` is a bare ``<expr>["field"]`` subscript (Load ctx)."""
    return (
        isinstance(node, ast.Subscript)
        and isinstance(node.ctx, ast.Load)
        and isinstance(node.slice, ast.Constant)
        and node.slice.value == field
    )


def _get_call_has_non_none_default(node: ast.Call) -> bool:
    """True iff a ``.get(field, default)`` call's default is present and not ``None``."""
    if len(node.args) < 2:
        return False
    default = node.args[1]
    return not (isinstance(default, ast.Constant) and default.value is None)


def _unwrap_one_comprehension_level(node: ast.expr) -> ast.expr:
    """If ``node`` is a generator/list/set comprehension, return its ``elt``.

    Handles ``sum(x.get(field, 0.0) for x in xs)`` /
    ``sum([x.get(field, 0.0) for x in xs])`` — the one level of unwrapping
    needed to see the at-risk expression inside a bare ``sum(...)`` call
    (``float``/``round``/etc. wrap a single expression directly and need no
    unwrapping).

    :param node: The expression to (maybe) unwrap.
    :returns: ``node.elt`` for a comprehension, else ``node`` unchanged.
    """
    if isinstance(node, (ast.GeneratorExp, ast.ListComp, ast.SetComp)):
        return node.elt
    return node


def unguarded_arithmetic_sites(
    tree: ast.Module, function: ast.FunctionDef | ast.AsyncFunctionDef, field: str
) -> list[int]:
    """Line numbers where ``field`` is fed unguarded into arithmetic.

    An at-risk site is a call to one of
    :data:`~babylon.sentinels.masked_arithmetic.registry.ARITHMETIC_WRAPPERS`
    whose (possibly comprehension-unwrapped) argument is a
    ``.get(field, <non-None default>)`` call or a bare ``[field]``
    subscript.

    :param tree: The parsed module (unused directly, kept for a stable
        signature alongside :func:`guard_exists_for_field`).
    :param function: The function node to scan.
    :param field: The political field name at risk.
    :returns: Sorted line numbers of at-risk sites.
    """
    _ = tree
    sites: set[int] = set()
    for node in ast.walk(function):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
            continue
        if node.func.id not in ARITHMETIC_WRAPPERS:
            continue
        for arg in node.args:
            candidate = _unwrap_one_comprehension_level(arg)
            if (
                _is_field_get(candidate, field)
                and _get_call_has_non_none_default(candidate)
                or _is_field_subscript(candidate, field)
            ):
                sites.add(node.lineno)
    return sorted(sites)


def guard_exists_for_field(function: ast.FunctionDef | ast.AsyncFunctionDef, field: str) -> bool:
    """True iff an ``is not None``-shaped guard on ``field`` exists anywhere.

    Matches ``<expr>.get(field[, ...]) is not None`` / ``!= None`` and the
    bare-subscript/reversed-operand equivalents, in either comparison
    direction (``X is not None`` or ``None is not X``) — a co-occurrence
    heuristic, not real control-flow dominance (see the module docstring's
    Scope section).

    :param function: The function node to scan.
    :param field: The political field name to look for a guard on.
    :returns: Whether a qualifying guard exists anywhere in the function.
    """
    for node in ast.walk(function):
        if not isinstance(node, ast.Compare):
            continue
        operands = [node.left, *node.comparators]
        has_none = any(isinstance(o, ast.Constant) and o.value is None for o in operands)
        has_is_or_noteq = any(
            isinstance(op, (ast.Is, ast.IsNot, ast.Eq, ast.NotEq)) for op in node.ops
        )
        if not (has_none and has_is_or_noteq):
            continue
        for operand in operands:
            if _is_field_get(operand, field) or _is_field_subscript(operand, field):
                return True
    return False


def unguarded_masked_arithmetic(
    registry: tuple[DeclaredFoggedConsumer, ...] = DECLARED_FOGGED_CONSUMERS,
) -> list[str]:
    """Every declared fogged consumer must guard its at-risk field.

    :param registry: The rows to check (defaults to the real
        :data:`~babylon.sentinels.masked_arithmetic.registry.DECLARED_FOGGED_CONSUMERS`;
        injectable so tests can supply a deliberately-unguarded row to prove
        the sensor reds).
    :returns: One violation string per unguarded row (empty when every
        declared row's at-risk field is guarded, or has no at-risk site at
        all).
    :raises SentinelCheckError: If ``def_file`` is missing, unparseable, or
        ``function_name`` cannot be found (exit 2 — infrastructure failure,
        never a silent pass).
    """
    violations: list[str] = []
    for row in registry:
        if is_exempt(("fogged_consumer", row.name), MASKED_ARITHMETIC_EXEMPTIONS):
            continue
        path = _REPO_ROOT / row.def_file
        tree = _parse(path)
        function = find_function(tree, row.function_name)
        if function is None:
            raise SentinelCheckError(
                f"{row.name!r}: function {row.function_name!r} not found in {row.def_file} "
                "(cannot verify the guard -- the registry row is stale)"
            )
        at_risk = unguarded_arithmetic_sites(tree, function, row.field)
        if not at_risk:
            continue
        if guard_exists_for_field(function, row.field):
            continue
        lines = ", ".join(f"{row.def_file}:{ln}" for ln in at_risk)
        violations.append(
            f"{row.name!r}: {row.function_name} in {row.def_file} does arithmetic on "
            f"field {row.field!r} with NO 'is not None' guard anywhere in the function "
            f"(at-risk site(s): {lines}).\n"
            f"    payload: {row.payload_note}\n"
            f"    consequence: {row.consequence_if_regressed}\n"
            "    fix: guard the field with an explicit `is not None` check before "
            "arithmetic, or add a reasoned SentinelExemption "
            "(key=('fogged_consumer', name), reason, owner, date, tracking_task) to "
            "MASKED_ARITHMETIC_EXEMPTIONS -- never a silent registry removal.\n"
            f"    {_WHY}"
        )
    return sorted(violations)


_GATING_CHECKS: Final[tuple[LabelledCheck, ...]] = (
    ("unguarded-masked-arithmetic", unguarded_masked_arithmetic),
)


def _summary(advisory_count: int) -> str:
    """Clean one-line summary: the counts actually enforced.

    :param advisory_count: Number of advisory findings (0 — no advisory tier).
    :returns: The summary line.
    """
    _ = advisory_count  # This sentinel declares no advisory tier.
    return (
        f"MASKED_ARITHMETIC clean: {len(DECLARED_FOGGED_CONSUMERS)} declared fogged "
        "consumer(s) all guard their at-risk field before arithmetic."
    )


def main(argv: list[str] | None = None) -> int:
    """Run the masked-arithmetic regression check and return the exit code.

    :param argv: CLI args (``--check`` is accepted as the CI-mode alias; the
        behavior is always to gate).
    :returns: 0 clean, 1 gating violations found, 2 infrastructure failure.
    """
    parser = argparse.ArgumentParser(
        description=("Fog-masked field arithmetic guard — static gate (III.11, Track 1 Task 10).")
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="CI-mode alias; the tool always gates (exit 1 on violations).",
    )
    parser.parse_args(argv)
    return run_sensor("MASKED_ARITHMETIC", _GATING_CHECKS, (), _summary)


if __name__ == "__main__":
    sys.exit(main())
