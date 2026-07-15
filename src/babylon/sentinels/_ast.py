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


def eventtype_names_in_func(path: Path, func_name: str) -> set[str]:
    """Collect the ``EventType.<NAME>`` members referenced inside a function.

    Used to measure how many ``EventType`` members a dispatcher (e.g.
    ``_convert_bus_event_to_pydantic``) actually handles — the rest fall through
    to a silent default.

    :param path: The source file to parse.
    :param func_name: The function whose body to scan.
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
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            for sub in ast.walk(node):
                if (
                    isinstance(sub, ast.Attribute)
                    and isinstance(sub.value, ast.Name)
                    and sub.value.id == "EventType"
                ):
                    names.add(sub.attr)
    return names
