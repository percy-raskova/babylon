"""Shared static-analysis helpers for the ``babylon.sentinels`` family.

Every sentinel enforces its invariant by reading source with :mod:`ast` — never
by importing or running the engine/Django. That keeps the sensors cheap enough
to live in the always-on dev fast-gate. These helpers are the common primitives
(module-level literal extraction, call-site scanning) each sensor's ``checks``
module builds on; a missing or unparseable source raises
:class:`~babylon.sentinels.base.SentinelCheckError` (exit 2) rather than a silent
empty result.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from pathlib import Path

from babylon.sentinels.base import SentinelCheckError


def literal_str_tuple(path: Path, var_name: str) -> tuple[str, ...]:
    """Statically extract a module-level ``tuple``/``list`` of string literals.

    Reads ``path`` with :mod:`ast` (no import, no execution) and returns the
    string constants assigned to ``var_name``. Comments and non-string elements
    are ignored so an inline-documented literal parses cleanly.

    :param path: Source file to parse.
    :param var_name: The assigned name to extract (``Assign`` or ``AnnAssign``).
    :returns: The string-literal elements, in source order.
    :raises SentinelCheckError: If the file is missing, unparseable, the name is
        absent, or its value is not a tuple/list literal.
    """
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SentinelCheckError(f"cannot read {path}: {exc}") from exc
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        raise SentinelCheckError(f"cannot parse {path}: {exc}") from exc

    for node in tree.body:
        targets: list[ast.expr]
        value: ast.expr | None
        if isinstance(node, ast.Assign):
            targets = node.targets
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
            value = node.value
        else:
            continue
        if value is None:
            continue
        if not any(isinstance(t, ast.Name) and t.id == var_name for t in targets):
            continue
        if not isinstance(value, (ast.Tuple, ast.List)):
            raise SentinelCheckError(f"{path}:{var_name} is not a tuple/list literal")
        return tuple(
            elt.value
            for elt in value.elts
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
        )
    raise SentinelCheckError(f"{path}: no module-level assignment to {var_name!r} found")


def literal_dict_keys(path: Path, var_name: str) -> tuple[str, ...]:
    """Statically extract the string keys of a module-level ``dict`` literal.

    :param path: Source file to parse.
    :param var_name: The assigned name whose ``dict`` literal to read.
    :returns: The string-literal keys, in source order (non-literal keys — e.g.
        ``EventType.X.value`` — are skipped, so a computed-key map yields an
        empty tuple rather than raising).
    :raises SentinelCheckError: If the file is missing/unparseable, the name is
        absent, or its value is not a dict literal.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except OSError as exc:
        raise SentinelCheckError(f"cannot read {path}: {exc}") from exc
    except SyntaxError as exc:
        raise SentinelCheckError(f"cannot parse {path}: {exc}") from exc

    for node in tree.body:
        targets: list[ast.expr]
        value: ast.expr | None
        if isinstance(node, ast.Assign):
            targets = node.targets
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
            value = node.value
        else:
            continue
        if value is None or not any(isinstance(t, ast.Name) and t.id == var_name for t in targets):
            continue
        if not isinstance(value, ast.Dict):
            raise SentinelCheckError(f"{path}:{var_name} is not a dict literal")
        return tuple(
            k.value for k in value.keys if isinstance(k, ast.Constant) and isinstance(k.value, str)
        )
    raise SentinelCheckError(f"{path}: no module-level assignment to {var_name!r} found")


def tick_write_set(path: Path) -> set[str]:
    """Collect the ``tick_*`` keyword names the engine writes via ``update_node``.

    This is the engine side of the seam — the per-territory state the tick
    dynamics stamp onto graph nodes. Extracted statically (no engine run) by
    walking every ``*.update_node(...)`` call and taking its ``tick_``-prefixed
    keyword arguments.

    :param path: The ``graph_bridge.py`` source to parse.
    :returns: The set of ``tick_*`` attribute names written.
    :raises SentinelCheckError: If the source is missing or unparseable.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except OSError as exc:
        raise SentinelCheckError(f"cannot read {path}: {exc}") from exc
    except SyntaxError as exc:
        raise SentinelCheckError(f"cannot parse {path}: {exc}") from exc

    keys: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "update_node"
        ):
            for kw in node.keywords:
                if kw.arg is not None and kw.arg.startswith("tick_"):
                    keys.add(kw.arg)
    return keys


def eventtype_names_in_module(path: Path) -> set[str]:
    """Collect every ``EventType.<NAME>`` member referenced in a module.

    Used to measure builder-registry coverage: an ``EventType`` absent from
    ``event_builders.EVENT_BUILDERS`` drops that event to ``None`` at the
    bus->pydantic boundary. The registry module's only ``EventType.<NAME>``
    references are its builder keys (the builders reference event *classes*, and
    the ``EventType`` import is an ``ImportFrom``, not an ``Attribute``).

    :param path: The source file to parse.
    :returns: The set of referenced ``EventType`` member names.
    :raises SentinelCheckError: If the source is missing or unparseable.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except OSError as exc:
        raise SentinelCheckError(f"cannot read {path}: {exc}") from exc
    except SyntaxError as exc:
        raise SentinelCheckError(f"cannot parse {path}: {exc}") from exc

    names: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "EventType"
        ):
            names.add(node.attr)
    return names


def parse_module(path: Path) -> ast.Module:
    """Read and parse ``path`` with :mod:`ast`, failing loudly on either error.

    The single shared entry point for the U7 sensors: a missing or unparseable
    source is an *infrastructure* failure (exit 2), never an empty result that
    would read as a clean pass (Constitution III.11).

    :param path: Source file to parse.
    :returns: The parsed module.
    :raises SentinelCheckError: If the file cannot be read or cannot be parsed.
    """
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SentinelCheckError(f"cannot read {path}: {exc}") from exc
    try:
        return ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        raise SentinelCheckError(f"cannot parse {path}: {exc}") from exc


def referenced_names(path: Path) -> set[str]:
    """Collect every symbol a module *mentions*, however it mentions it.

    A consumer can reach an output four ways: a bare name (``price_divergence``),
    an attribute (``axis.fictitious_log``), a keyword argument
    (``update_node(..., price_divergence=x)``), or a string key
    (``attrs.get("national_financial")``). All four count as a reference — the
    liveness and coupling sensors ask "does this file read that output?", and a
    string-keyed graph read is as real a reader as an imported constant.

    :param path: Source file to parse.
    :returns: The union of referenced names, attribute names, keyword-argument
        names, and string-literal constants.
    :raises SentinelCheckError: If the file is missing or unparseable.
    """
    tree = parse_module(path)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.keyword) and node.arg is not None:
            names.add(node.arg)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            names.add(node.value)
    return names


def coupling_edges(path: Path) -> tuple[tuple[str, str, str], ...]:
    """Extract the declared ``Coupling(source=, target=, kind=)`` literals.

    Reads the dialectics catalog statically — :mod:`babylon.sentinels` may not
    import ``babylon.domain`` (import-linter contract, ``pyproject.toml``) — and
    returns the declared coupling map as plain triples. A call whose endpoints
    are not string literals is skipped (a computed edge is not a *declared* one).

    :param path: The module declaring the ``Coupling(...)`` literals.
    :returns: ``(source, target, kind)`` triples, in source order.
    :raises SentinelCheckError: If the file is missing or unparseable.
    """
    tree = parse_module(path)
    edges: list[tuple[str, str, str]] = []
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "Coupling"
        ):
            continue
        parts: dict[str, str] = {}
        for kw in node.keywords:
            if (
                kw.arg in {"source", "target", "kind"}
                and isinstance(kw.value, ast.Constant)
                and isinstance(kw.value.value, str)
            ):
                parts[kw.arg] = kw.value.value
        if len(parts) == 3:
            edges.append((parts["source"], parts["target"], parts["kind"]))
    return tuple(edges)


_SCOPE_BOUNDARY: tuple[type[ast.AST], ...] = (
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.ClassDef,
)


def _walk_own_scope(node: ast.AST) -> Iterator[ast.AST]:
    """Depth-first walk of ``node``'s own lexical scope only.

    Like :func:`ast.walk`, but does not descend into a nested ``def``/``async
    def``/``class`` body — a ``return`` statement inside one of those belongs to
    that inner scope, not to ``node``.

    :param node: The function/module body to walk.
    :yields: Every descendant node reachable without crossing a scope boundary.
    """
    for child in ast.iter_child_nodes(node):
        yield child
        if not isinstance(child, _SCOPE_BOUNDARY):
            yield from _walk_own_scope(child)


def returned_dict_keys(path: Path, func_name: str) -> tuple[str, ...]:
    """Extract the string keys of the dict literal a named function returns.

    The service factories (``create_economics_services``,
    ``create_financial_services``) each end in one dict literal whose keys ARE
    the estate the DoD gate is meant to inject. Reading them statically lets the
    gate-blindness sensor compare estate against harness without importing
    ``babylon.domain``.

    Only the function's *own* scope is scanned: a ``return {...}`` nested inside
    a closure or class the function declares internally does not count, and if
    the function's own scope contains more than one ``return {...}``, only the
    LAST one in source order is read (matching what actually executes when a
    factory has a superseded early-return branch).

    :param path: Source file defining ``func_name``.
    :param func_name: The module-level function whose returned dict to read.
    :returns: The string keys of the last returned dict literal, sorted.
    :raises SentinelCheckError: If the file is missing/unparseable, the function
        is absent, or it returns no dict literal.
    """
    tree = parse_module(path)
    target: ast.FunctionDef | None = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            target = node
    if target is None:
        raise SentinelCheckError(f"{path}: no function {func_name!r} at module level")
    last_keys: tuple[str, ...] | None = None
    for sub in _walk_own_scope(target):
        if isinstance(sub, ast.Return) and isinstance(sub.value, ast.Dict):
            last_keys = tuple(
                k.value
                for k in sub.value.keys
                if isinstance(k, ast.Constant) and isinstance(k.value, str)
            )
    if last_keys is None:
        raise SentinelCheckError(f"{path}:{func_name} returns no dict literal")
    return tuple(sorted(last_keys))
