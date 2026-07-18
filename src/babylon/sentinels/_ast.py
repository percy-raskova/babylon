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

from babylon.models.enums.topology import NodeType
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


#: One node-type string literal found in source: ``(lineno, value, role)``
#: where role is ``"stamp"`` (the literal is written onto a node) or
#: ``"query"`` (the literal is compared against a node's ``_node_type``).
NodeTypeUse = tuple[int, str, str]

#: The attribute key every graph node's type marker lives under.
_TYPE_KEY = "_node_type"


def _leaf_value(node: ast.expr) -> str | None:
    """Resolve one expression leaf to its node-type string, if it is one.

    Two forms count: a bare string literal, and a ``NodeType.MEMBER``
    attribute reference (resolved to the member's *value*). Resolving the enum
    form is load-bearing — once code adopts ``NodeType.TERRITORY`` a
    literal-only scanner goes blind to exactly the sites it must police, and
    the sentinel would silently report an empty stamp set.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "NodeType"
    ):
        member = NodeType.__members__.get(node.attr)
        return None if member is None else member.value
    return None


def _string_constants(node: ast.expr) -> list[str]:
    """Flatten an expression into its node-type leaves.

    Handles the bare leaf plus the container forms a membership test uses
    (``in ("a", "b")``, ``in {"a"}``, ``in ["a"]``). Unresolvable elements are
    skipped, so a computed comparand contributes nothing rather than raising.
    """
    single = _leaf_value(node)
    if single is not None:
        return [single]
    if isinstance(node, (ast.Tuple, ast.Set, ast.List)):
        return [v for elt in node.elts if (v := _leaf_value(elt)) is not None]
    return []


def _is_type_key_read(node: ast.expr) -> bool:
    """True iff ``node`` reads the ``_node_type`` key off a mapping.

    Matches both the ``data.get("_node_type")`` / ``data.pop("_node_type")``
    call form and the ``data["_node_type"]`` subscript form.
    """
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in ("get", "pop")
        and node.args
    ):
        first = node.args[0]
        return isinstance(first, ast.Constant) and first.value == _TYPE_KEY
    if isinstance(node, ast.Subscript):
        sub = node.slice
        return isinstance(sub, ast.Constant) and sub.value == _TYPE_KEY
    return False


def _uses_from_call(node: ast.Call) -> list[NodeTypeUse]:
    """Node-type literals in an ``add_node`` / ``query_nodes`` style call."""
    if not isinstance(node.func, ast.Attribute):
        return []
    uses: list[NodeTypeUse] = []
    name = node.func.attr
    if name == "add_node":
        if len(node.args) >= 2:
            uses += [(node.lineno, v, "stamp") for v in _string_constants(node.args[1])]
        for kw in node.keywords:
            if kw.arg == _TYPE_KEY:
                uses += [(node.lineno, v, "stamp") for v in _string_constants(kw.value)]
    elif name in ("query_nodes", "count_nodes"):
        for kw in node.keywords:
            if kw.arg == "node_type":
                uses += [(node.lineno, v, "query") for v in _string_constants(kw.value)]
    elif name == "with_node_types":
        for arg in node.args:
            uses += [(node.lineno, v, "query") for v in _string_constants(arg)]
    return uses


def _uses_from_write(node: ast.Assign | ast.Dict) -> list[NodeTypeUse]:
    """Node-type literals written via assignment or a dict-literal payload."""
    if isinstance(node, ast.Assign):
        if any(_is_type_key_read(t) for t in node.targets):
            return [(node.lineno, v, "stamp") for v in _string_constants(node.value)]
        return []
    uses: list[NodeTypeUse] = []
    for key, value_node in zip(node.keys, node.values, strict=True):
        if isinstance(key, ast.Constant) and key.value == _TYPE_KEY:
            uses += [(node.lineno, v, "stamp") for v in _string_constants(value_node)]
    return uses


def _uses_from_compare(node: ast.Compare) -> list[NodeTypeUse]:
    """Node-type literals compared against a ``_node_type`` read."""
    operands = [node.left, *node.comparators]
    if not any(_is_type_key_read(operand) for operand in operands):
        return []
    return [(node.lineno, v, "query") for operand in operands for v in _string_constants(operand)]


def node_type_uses(path: Path) -> list[NodeTypeUse]:
    """Extract every node-type string literal a module stamps or queries.

    This is the vocabulary sentinel's eye. It reads source with :mod:`ast`, so
    a ``_node_type`` mentioned only inside a docstring or comment is invisible
    — only real code counts. Six syntactic forms are recognised:

    *Stamps* (the literal is written onto a node)
      - ``add_node(id, "social_class", ...)`` — protocol form, 2nd positional
      - ``add_node(id, ..., _node_type="social_class")`` — authoring form
      - ``node["_node_type"] = "social_class"`` — direct assignment
      - ``{"_node_type": "social_class", ...}`` — dict-literal payload

    *Queries* (the literal is matched against a node's type)
      - ``query_nodes(node_type="social_class")`` and
        ``with_node_types({"social_class"})``
      - ``data.get("_node_type") == "social_class"`` (any comparison or
        ``in``-membership against a ``_node_type`` read)

    :param path: Source file to parse.
    :returns: ``(lineno, literal, role)`` triples sorted by line then literal,
        so callers get a deterministic order (Constitution III.7).
    :raises SentinelCheckError: If the file is missing or unparseable.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except OSError as exc:
        raise SentinelCheckError(f"cannot read {path}: {exc}") from exc
    except SyntaxError as exc:
        raise SentinelCheckError(f"cannot parse {path}: {exc}") from exc

    uses: list[NodeTypeUse] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            uses += _uses_from_call(node)
        elif isinstance(node, (ast.Assign, ast.Dict)):
            uses += _uses_from_write(node)
        elif isinstance(node, ast.Compare):
            uses += _uses_from_compare(node)

    return sorted(set(uses))
