"""Dangling-reference checks: a dynamic string-name reference must land on something real.

DUAL of :mod:`babylon.sentinels.inert.checks` (read that module's docstring
first — this one mirrors its shape and its AST-walking discipline
deliberately, per the family's own established convention of each sentinel
package staying self-contained rather than importing a sibling package's
internals; :func:`is_test_source` here is a verbatim mirror of
:func:`babylon.sentinels.inert.checks.is_test_source`, the same relationship
:mod:`babylon.sentinels.unconsumed.checks` already has to it).

**The one rule.** For every :class:`~babylon.sentinels.dangling.registry.
WatchedReceiver` row, find every ``getattr(<receiver>, "<name>", <default>)``
call site in production code where ``<receiver>`` is statically knowable as
an instance of that receiver family (see :func:`_typed_receivers`), and check
``<name>`` against the UNION of every member declared by the row's
``member_classes`` (see :func:`_class_members`). A name absent from every
member class is a violation — the call site references a target that does
not exist anywhere reachable through that receiver's real type.

**Receiver typing** (mirrors :mod:`babylon.sentinels.inert`'s own documented
heuristic, extended by one more form): a name is "typed" as a receiver
family if it is (a) a function/method parameter whose annotation mentions
one of the family's ``annotation_names`` anywhere in it (bare, ``| None``,
``Optional[...]``), (b) a type-annotated assignment whose annotation
mentions the same, or (c) — the new form this sentinel adds — a plain
``self.<attr> = <name>`` alias assignment where ``<name>`` is already typed
by (a) or (b), closed to a fixed point (bounded by :data:`_MAX_CHAIN_PASSES`,
Constitution "no unbounded loop" discipline). Form (c) is exactly the
``self._persistence = persistence`` pattern in ``engine_bridge.py``'s
``__init__`` — without it, every ``self._persistence.foo()`` call site in
that class would be invisible to the sentinel, which is most of them.

**Scope and known limitations** (read before extending — same discipline as
:mod:`babylon.sentinels.inert`):

- Like inert's own receiver-typing, this is a best-effort static heuristic
  operating on a flat, whole-FILE name set (not truly function/class
  scoped) — a name typed in one function is (imprecisely) considered typed
  everywhere in the same file. This is the same simplification inert's own
  :func:`~babylon.sentinels.inert.checks._typed_receivers` already makes;
  documented here rather than silently assumed absent. Given the receiver
  names in the one seeded family (``persistence``, ``self._persistence``)
  are consistently and exclusively used for the persistence layer throughout
  ``engine_bridge.py``, this has zero observed false-positive/negative
  effect on the current tree.
- Only a 3-argument ``getattr(x, "literal", default)`` (or the 2-argument
  form) where the SECOND argument is a string literal is recognized — a
  computed name (``getattr(x, name_var, None)``) is invisible to this
  checker, the same "cannot resolve without value-flow analysis" limitation
  inert's rule (b) documents for ``getattr(module, "symbol_name")``.
- The registry-of-watched-classes design is the deliberate scope boundary
  (see the registry module's own docstring) — a general "flag every
  getattr in the repo" checker would drown in false positives
  (``getattr(request, ...)``, ``getattr(django_settings, ...)``, etc). Only
  receivers provably typed as a *watched* family are ever inspected.
"""

from __future__ import annotations

import argparse
import ast
import difflib
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Final

from babylon.sentinels.base import LabelledCheck, SentinelCheckError, run_sensor
from babylon.sentinels.dangling.registry import (
    DANGLING_EXEMPTIONS,
    PRODUCTION_ROOTS,
    WATCHED_CLASSES,
    WATCHED_RECEIVERS,
    WatchedClass,
    WatchedReceiver,
)
from babylon.sentinels.exemptions import is_exempt

__all__ = [
    "class_members",
    "dangling_references",
    "is_test_source",
    "main",
    "typed_getattr_sites",
]

#: Repo root (this file is ``<root>/src/babylon/sentinels/dangling/checks.py``
#: -- same nesting depth as ``inert/checks.py``, so the same parents-index
#: resolves to the identical physical path).
_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[4]

#: A fixed, statically-provable upper bound on the alias-chain fixed-point
#: (Constitution "no unbounded loop" discipline) -- mirrors
#: ``inert.checks._MAX_CHAIN_PASSES``.
_MAX_CHAIN_PASSES: Final[int] = 5

_WHY: Final[str] = (
    "WHY THIS FAILS: a getattr() naming a method that exists on NONE of the receiver's real "
    "types is structurally dead code with a heartbeat -- the guarded branch never fires, and "
    "silently falls through to whatever fallback follows (or raises later if there is none). "
    "This is not hypothetical: web/game/engine_bridge.py's _persist_action_result() reads "
    "getattr(persistence, 'persist_action_result', None) (SINGULAR) while every real backend "
    "only ever declares persist_action_results (PLURAL, batched) -- the guarded branch has been "
    "dead since it was written."
)


def is_test_source(path: Path) -> bool:
    """True iff ``path`` is a test file by pytest convention.

    Verbatim mirror of :func:`babylon.sentinels.inert.checks.is_test_source`
    (see that module's docstring for why each sentinel package stays
    self-contained rather than importing a sibling's internals).

    :param path: The file to classify.
    :returns: Whether the file is a test file (and must never count as a
        production call site).
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


def _mentions_any(annotation: ast.expr | None, class_names: tuple[str, ...]) -> bool:
    """True iff a type annotation mentions any of ``class_names`` anywhere in it.

    :param annotation: The annotation expression (``None`` if absent).
    :param class_names: The candidate names to look for.
    :returns: Whether the annotation mentions one of the names.
    """
    if annotation is None:
        return False
    names = set(class_names)
    return any(isinstance(node, ast.Name) and node.id in names for node in ast.walk(annotation))


def _typed_receivers(tree: ast.Module, annotation_names: tuple[str, ...]) -> set[str]:
    """Best-effort, whole-file set of dotted names typed as one of ``annotation_names``.

    Three sources: a type-annotated assignment/parameter whose annotation
    mentions one of ``annotation_names``, and a bounded fixed-point closure
    over plain ``self.<attr> = <name>`` alias assignments where ``<name>``
    is already typed — see the module docstring's "Receiver typing" section.

    :param tree: A parsed module.
    :param annotation_names: The receiver family's recognized annotation names.
    :returns: The set of dotted names known to hold an instance of the family.
    """
    typed: set[str] = set()
    assigns: list[ast.Assign] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            assigns.append(node)
        elif isinstance(node, ast.AnnAssign) and _mentions_any(node.annotation, annotation_names):
            dotted = _dotted_name(node.target)
            if dotted:
                typed.add(dotted)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            all_args = (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)
            for arg in all_args:
                if _mentions_any(arg.annotation, annotation_names):
                    typed.add(arg.arg)

    for _pass in range(_MAX_CHAIN_PASSES):
        grew = False
        for node in assigns:
            if not (isinstance(node.value, ast.Name) and node.value.id in typed):
                continue
            for target in node.targets:
                dotted = _dotted_name(target)
                if dotted and dotted not in typed:
                    typed.add(dotted)
                    grew = True
        if not grew:
            break
    return typed


def typed_getattr_sites(
    path: Path, annotation_names: tuple[str, ...]
) -> list[tuple[int, str, str]]:
    """Every ``getattr(<receiver>, "<name>", ...)`` site in ``path`` on a typed receiver.

    :param path: Source file to parse.
    :param annotation_names: The receiver family's recognized annotation names.
    :returns: Sorted ``(lineno, receiver_dotted_name, attr_name)`` triples for
        every ``getattr`` call whose receiver is statically typed as the
        family and whose 2nd argument is a string literal.
    :raises SentinelCheckError: If ``path`` is missing or unparseable.
    """
    tree = _parse(path)
    typed = _typed_receivers(tree, annotation_names)
    sites: set[tuple[int, str, str]] = set()
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "getattr"
            and len(node.args) >= 2
            and isinstance(node.args[1], ast.Constant)
            and isinstance(node.args[1].value, str)
        ):
            continue
        receiver = _dotted_name(node.args[0])
        if receiver is not None and receiver in typed:
            sites.add((node.lineno, receiver, node.args[1].value))
    return sorted(sites)


def _members_of(cls: ast.ClassDef) -> frozenset[str]:
    """Every statically-declared member name of a class.

    Three sources: every method (``FunctionDef``/``AsyncFunctionDef``,
    including private/dunder — a protocol's ``...``-bodied method counts the
    same as a concrete implementation's real one) and every
    ``Assign``/``AnnAssign`` target declared directly in the class body;
    plus every ``self.<attr> = ...`` instance attribute assigned ANYWHERE in
    the class's own methods (e.g. ``PostgresRuntime.__init__``'s
    ``self._pool = pool``) — a getattr against a plain data attribute is a
    real, valid reference, not just against a method.

    :param cls: A class definition to inspect.
    :returns: The class's full member-name set.
    """
    members: set[str] = set()
    for item in cls.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            members.add(item.name)
        elif isinstance(item, ast.Assign):
            for target in item.targets:
                if isinstance(target, ast.Name):
                    members.add(target.id)
        elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            members.add(item.target.id)
    for node in ast.walk(cls):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "self"
            ):
                members.add(target.attr)
    return frozenset(members)


def class_members(def_file: str, class_name: str) -> frozenset[str]:
    """Statically enumerate every member name ``class_name`` declares.

    :param def_file: Repo-relative ``.py`` path defining ``class_name``.
    :param class_name: The bare class name to look up.
    :returns: The class's full member-name set (see :func:`_members_of`).
    :raises SentinelCheckError: If ``def_file`` is missing/unparseable, or
        does not define a class named ``class_name``.
    """
    tree = _parse(_REPO_ROOT / def_file)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return _members_of(node)
    raise SentinelCheckError(f"class {class_name!r} not found in {def_file}")


def _member_union(receiver: WatchedReceiver, classes: tuple[WatchedClass, ...]) -> frozenset[str]:
    """The union of every member name across a receiver's declared ``member_classes``.

    :param receiver: The receiver family row.
    :param classes: The full :data:`WATCHED_CLASSES` registry to resolve
        ``member_classes`` names against.
    :returns: The union member-name set.
    :raises SentinelCheckError: If a resolved class's file is missing/unparseable.
    """
    by_name = {row.name: row for row in classes}
    union: set[str] = set()
    for member_name in receiver.member_classes:
        row = by_name[member_name]  # registry-validated at import; KeyError would be a bug
        union |= class_members(row.def_file, row.class_name)
    return frozenset(union)


def dangling_references(
    receivers: tuple[WatchedReceiver, ...] = WATCHED_RECEIVERS,
    classes: tuple[WatchedClass, ...] = WATCHED_CLASSES,
) -> list[str]:
    """The gating rule: every typed-receiver ``getattr`` must name a real member.

    :param receivers: The receiver-family rows to check (defaults to the
        real :data:`WATCHED_RECEIVERS`; injectable so tests can supply a
        deliberately-narrowed family to prove the sensor reds/greens).
    :param classes: The watched-class rows to resolve ``member_classes``
        against (defaults to the real :data:`WATCHED_CLASSES`).
    :returns: One violation string per dangling reference (empty when every
        typed-receiver getattr names a real member).
    :raises SentinelCheckError: If a scan root or a watched class's file is
        missing/unparseable (exit 2 — infrastructure failure, never a
        silent pass).
    """
    violations: list[str] = []
    for receiver in receivers:
        valid_names = _member_union(receiver, classes)
        for path in _production_files():
            rel = path.relative_to(_REPO_ROOT).as_posix()
            for lineno, dotted_receiver, attr in typed_getattr_sites(
                path, receiver.annotation_names
            ):
                if attr in valid_names:
                    continue
                key = ("dangling", receiver.name, rel, attr)
                if is_exempt(key, DANGLING_EXEMPTIONS):
                    continue
                nearest = difflib.get_close_matches(attr, sorted(valid_names), n=3)
                suggestion = f" nearest real name(s): {nearest}" if nearest else " (no close match)"
                violations.append(
                    f"{rel}:{lineno}: getattr({dotted_receiver}, {attr!r}, ...) -- {attr!r} is "
                    f"not a member of any watched class for receiver family {receiver.name!r} "
                    f"({', '.join(receiver.member_classes)}).{suggestion}\n"
                    "    fix: correct the referenced name, wire the real target, or add a "
                    "reasoned SentinelExemption (key=('dangling', receiver_name, rel_path, attr), "
                    "reason, owner, date, tracking_task) to DANGLING_EXEMPTIONS -- never a silent "
                    "rename that happens to make the string match without checking the call's "
                    "actual argument shape.\n"
                    f"    {_WHY}"
                )
    return sorted(violations)


#: The one gating rule: a dangling dynamic reference is a live defect.
_GATING_CHECKS: Final[tuple[LabelledCheck, ...]] = (("dangling-reference", dangling_references),)


def _summary(advisory_count: int) -> str:
    """Clean one-line summary: the counts actually enforced.

    :param advisory_count: Number of advisory findings (0 — no advisory tier).
    :returns: The summary line.
    """
    _ = advisory_count  # This sentinel declares no advisory tier.
    return (
        f"DANGLING clean: {len(WATCHED_RECEIVERS)} watched receiver family(ies) against "
        f"{len(WATCHED_CLASSES)} watched class(es) — every typed-receiver getattr() names a "
        "real member."
    )


def main(argv: list[str] | None = None) -> int:
    """Run the dangling-reference gate and return the exit code.

    :param argv: CLI args (``--check`` is accepted as the CI-mode alias; the
        behavior is always to gate).
    :returns: 0 clean, 1 gating violations found, 2 infrastructure failure.
    """
    parser = argparse.ArgumentParser(
        description="Dangling dynamic-reference gate (dual of the inert sentinel)."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="CI-mode alias; the tool always gates (exit 1 on violations).",
    )
    parser.parse_args(argv)
    return run_sensor("DANGLING", _GATING_CHECKS, (), _summary)


if __name__ == "__main__":
    sys.exit(main())
