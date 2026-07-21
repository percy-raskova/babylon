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
import re
from collections.abc import Iterator
from pathlib import Path

from babylon.models.enums.topology import EdgeType, NodeType
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


def frozenset_str_members(path: Path, var_name: str) -> tuple[str, ...]:
    """Return the string members of a module-level ``frozenset({...})`` literal.

    Reads ``VAR = frozenset({...})`` or ``VAR: frozenset[str] = frozenset({...})``
    from ``path`` by AST — no import, no execution. Non-string members are
    ignored (the sentinel compares only string symbols), but the assignment
    itself must be present and its value must be a set/list/tuple literal
    (optionally wrapped in a ``frozenset(...)`` call) — mirroring
    :func:`literal_str_tuple`'s contract so an absent or malformed baseline
    fails loud rather than reading as an empty, drift-free baseline.

    :param path: Source file to parse.
    :param var_name: The assigned name to extract (``Assign`` or ``AnnAssign``).
    :returns: The string-literal members, in source order.
    :raises SentinelCheckError: If the file is missing or unparseable, the name
        is absent, or its value is not a set/list/tuple literal.
    """
    tree = parse_module(path)
    for node in ast.walk(tree):
        target: ast.expr | None
        value: ast.expr | None
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            target = node.target
            value = node.value
        else:
            continue
        if value is None:
            continue
        if not isinstance(target, ast.Name) or target.id != var_name:
            continue
        # frozenset({...}) or frozenset([...])
        if (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Name)
            and value.func.id == "frozenset"
            and value.args
        ):
            value = value.args[0]
        if not isinstance(value, (ast.Set, ast.List, ast.Tuple)):
            raise SentinelCheckError(f"{path}:{var_name} is not a frozenset/set/list/tuple literal")
        return tuple(
            elt.value
            for elt in value.elts
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
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


#: One node-attribute stamp found in source: ``(lineno, node_type, attribute)``
#: -- a keyword (or dict-literal key) passed to a real ``add_node(id, TYPE,
#: **kwargs)`` call whose node type resolved to a single literal.
NodeAttributeStamp = tuple[int, str, str]

#: Keyword names that select the node's TYPE, not a field stamped ON it.
_NODE_TYPE_KEYS = (_TYPE_KEY, "node_type")


def _dict_literal_shape(dict_node: ast.Dict) -> tuple[str | None, list[str]]:
    """``**{"_node_type": ..., "attr": ...}`` -- split its keys into
    (node type, other attribute names)."""
    node_type: str | None = None
    attrs: list[str] = []
    for key_node, value_node in zip(dict_node.keys, dict_node.values, strict=True):
        if not (isinstance(key_node, ast.Constant) and isinstance(key_node.value, str)):
            continue
        if key_node.value in _NODE_TYPE_KEYS:
            leaf = _leaf_value(value_node)
            if leaf is not None:
                node_type = leaf
        else:
            attrs.append(key_node.value)
    return node_type, attrs


def _add_node_call_shape(call: ast.Call) -> tuple[str | None, list[str]]:
    """One ``add_node(id, TYPE, **kwargs)`` call's (node type, other attrs).

    ``node type`` is ``None`` when unresolvable (a variable, or absent) --
    callers must treat that as "contributes nothing", never a guess.
    """
    node_type: str | None = None
    if len(call.args) >= 2:
        resolved = _string_constants(call.args[1])
        node_type = resolved[0] if len(resolved) == 1 else None

    attrs: list[str] = []
    for kw in call.keywords:
        if kw.arg is None:
            if isinstance(kw.value, ast.Dict):
                dict_type, dict_attrs = _dict_literal_shape(kw.value)
                node_type = dict_type if dict_type is not None else node_type
                attrs += dict_attrs
            continue
        if kw.arg in _NODE_TYPE_KEYS:
            leaf = _leaf_value(kw.value)
            node_type = leaf if leaf is not None else node_type
            continue
        attrs.append(kw.arg)

    return node_type, attrs


#: One phantom-attribute READ found in source: ``(lineno, attribute)`` -- a
#: banned attribute name read via ``.get(...)``/``.pop(...)``/``[...]`` off a
#: raw graph-node payload dict.
AttributeRead = tuple[int, str]


def _is_node_payload_expr(expr: ast.expr, bound_names: set[str]) -> bool:
    """True iff ``expr`` is BabylonGraph's own raw node-payload accessor
    shape (``<x>.nodes.get(id, {})`` / ``<x>.nodes[id]``), directly or via a
    same-file bound ``Name`` (see :func:`_node_payload_bound_names`)."""
    if isinstance(expr, ast.Name):
        return expr.id in bound_names
    if isinstance(expr, ast.Call):
        func = expr.func
        return (
            isinstance(func, ast.Attribute)
            and func.attr == "get"
            and isinstance(func.value, ast.Attribute)
            and func.value.attr == "nodes"
        )
    if isinstance(expr, ast.Subscript):
        return isinstance(expr.value, ast.Attribute) and expr.value.attr == "nodes"
    return False


def _node_payload_bound_names(tree: ast.Module) -> set[str]:
    """Names assigned (anywhere in the file) from a raw node-payload expr
    (``member_data = graph.nodes.get(target, {})``-style bindings)."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not _is_node_payload_expr(node.value, set()):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                names.add(target.id)
    return names


def graph_node_attribute_reads(path: Path, banned: frozenset[str]) -> list[AttributeRead]:
    """Extract every banned attribute READ off a raw graph-node payload.

    The phantom-attribute-read eye (task #40): scoped deliberately narrow,
    mirroring :func:`add_node_attribute_stamps`'s own philosophy -- only a
    ``.get``/``.pop``/subscript call whose RECEIVER is (directly, or via a
    same-file bound ``Name``) BabylonGraph's own raw node-payload accessor
    shape (``<x>.nodes.get(id, {})`` / ``<x>.nodes[id]``) counts. An
    arbitrary dict reading the SAME string (a DB row, an API response
    payload, a Pydantic model's own field accessed via a duck-typed
    ``.get()`` fallback) is a different namespace entirely and is invisible
    to this rule by construction, not by omission -- it is not a graph-node
    read, so it cannot be the "no producer ever stamps this on a graph node"
    bug this rule polices.

    :param path: Source file to parse.
    :param banned: Attribute names this rule polices.
    :returns: ``(lineno, attribute)`` pairs, sorted.
    :raises SentinelCheckError: If the file is missing or unparseable.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except OSError as exc:
        raise SentinelCheckError(f"cannot read {path}: {exc}") from exc
    except SyntaxError as exc:
        raise SentinelCheckError(f"cannot parse {path}: {exc}") from exc

    bound_names = _node_payload_bound_names(tree)
    reads: list[AttributeRead] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if (
                isinstance(func, ast.Attribute)
                and func.attr in ("get", "pop")
                and node.args
                and _is_node_payload_expr(func.value, bound_names)
            ):
                first = node.args[0]
                if (
                    isinstance(first, ast.Constant)
                    and isinstance(first.value, str)
                    and first.value in banned
                ):
                    reads.append((node.lineno, first.value))
        elif isinstance(node, ast.Subscript) and _is_node_payload_expr(node.value, bound_names):
            sub = node.slice
            if isinstance(sub, ast.Constant) and isinstance(sub.value, str) and sub.value in banned:
                reads.append((node.lineno, sub.value))
    return sorted(set(reads))


def add_node_attribute_stamps(path: Path) -> list[NodeAttributeStamp]:
    """Extract every keyword attribute a real ``add_node(...)`` call stamps.

    The vocabulary sentinel's shape-closure eye (Rule c): pairs each stamped
    node type with every OTHER keyword the same call passes, so a caller can
    check the pair against the real model's declared fields.

    Scoped deliberately narrow (Constitution III.11: honest absence over a
    guess):

    * Only calls whose node type resolves to a SINGLE literal string or
      ``NodeType.MEMBER`` are considered -- a call whose node type is a
      variable (unresolvable statically) contributes nothing, rather than a
      wrong guess.
    * ``**payload`` unpacking only contributes attributes when ``payload`` is
      a dict LITERAL (mirrors :func:`node_type_uses`'s own dict-literal
      handling) -- a variable payload contributes nothing.
    * ``update_node(...)`` calls are OUT OF SCOPE entirely: they carry no
      co-located node type, and inferring one would require dataflow
      analysis this static scanner does not do (see the vocabulary
      sentinel's module docstring for the audit that established this
      boundary -- task #45).

    :param path: Source file to parse.
    :returns: ``(lineno, node_type, attribute)`` triples, sorted, one per
        keyword (or dict-literal key) the call passes alongside a resolved
        node type. ``_node_type``/``node_type`` themselves are never
        reported (they select the type, not a field on it).
    :raises SentinelCheckError: If the file is missing or unparseable.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except OSError as exc:
        raise SentinelCheckError(f"cannot read {path}: {exc}") from exc
    except SyntaxError as exc:
        raise SentinelCheckError(f"cannot parse {path}: {exc}") from exc

    stamps: list[NodeAttributeStamp] = []
    for call_node in ast.walk(tree):
        if not (
            isinstance(call_node, ast.Call)
            and isinstance(call_node.func, ast.Attribute)
            and call_node.func.attr == "add_node"
        ):
            continue
        node_type, attrs = _add_node_call_shape(call_node)
        if node_type is None:
            continue
        stamps += [(call_node.lineno, node_type, attr) for attr in attrs]

    return sorted(set(stamps))


# ─────────────────────────────────────────────────────────────────────────────
# Edge-shape closure (Rule d, ADR087): every (edge_type, SOURCE node type) a
# fixture stamps must have a production producer. Deliberately a SEPARATE,
# additive family of helpers from the node-vocabulary ones above -- narrower
# scoped (only ``add_edge``/``Relationship`` call sites whose SOURCE resolves
# to a same-file node-type binding), so it does not risk the well-tested
# node-vocabulary extractor's behavior.
# ─────────────────────────────────────────────────────────────────────────────

#: One (edge_type, source_node_type) combination a module stamps:
#: ``(lineno, edge_type_value, source_node_type_value)``.
EdgeSourceUse = tuple[int, str, str]

#: Pydantic entity-model constructor names mapped to the NodeType they mint,
#: mirroring ``vocabulary.registry.MODEL_FIELDS_BY_NODE_TYPE``'s grouping --
#: the only two SOLIDARITY producers in ``src/`` (``scenarios/_legacy.py`` +
#: ``_legacy_wayne.py``) build edges via ``Relationship(source_id=...)``
#: against nodes built via these constructors, never a raw ``add_node`` call.
_ENTITY_CTOR_NODE_TYPES: dict[str, str] = {
    "SocialClass": NodeType.SOCIAL_CLASS.value,
    "Territory": NodeType.TERRITORY.value,
    "Organization": NodeType.ORGANIZATION.value,
    "StateApparatus": NodeType.ORGANIZATION.value,
    "Business": NodeType.ORGANIZATION.value,
    "PoliticalFaction": NodeType.ORGANIZATION.value,
    "CivilSocietyOrg": NodeType.ORGANIZATION.value,
    "Institution": NodeType.INSTITUTION.value,
    "IndustryHyperedge": NodeType.INDUSTRY.value,
    "Sovereign": NodeType.SOVEREIGN.value,
    "BalkanizationFaction": NodeType.FACTION.value,
}


def _enum_member_value(node: ast.expr, enum_cls: type, enum_name: str) -> str | None:
    """Resolve ``EnumName.MEMBER`` (optionally ``.value``-suffixed) or a bare
    string literal to the member's string value.

    A deliberately separate resolver from ``node_type_uses``'s internal
    ``_leaf_value`` (never modified by this addition) — this one also
    unwraps a trailing ``.value`` (``EdgeType.SOLIDARITY.value``), a form
    that appears at several real ``add_edge(..., edge_type=X.value)`` call
    sites this rule must not go blind to.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    target = node
    if (
        isinstance(target, ast.Attribute)
        and target.attr == "value"
        and isinstance(target.value, ast.Attribute)
    ):
        target = target.value
    if (
        isinstance(target, ast.Attribute)
        and isinstance(target.value, ast.Name)
        and target.value.id == enum_name
    ):
        member = enum_cls.__members__.get(target.attr)  # type: ignore[attr-defined]
        return None if member is None else str(member.value)
    return None


def _id_key(node: ast.expr) -> str | None:
    """The binding key for an id-position expression: its literal string
    value, or the ``Name`` it references (module-level ID constants are the
    common form -- the SAME ``Name`` typically appears at both the
    node-creation site and the edge-creation site)."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return node.id
    return None


def _local_source_type_bindings(tree: ast.Module) -> dict[str, str]:
    """Map each locally-bound id key to the node type it was created with.

    Recognizes ``add_node(id_expr, TYPE, ...)`` (both the 2nd-positional and
    ``_node_type=``/``node_type=`` keyword forms) and pydantic entity
    constructors (``SocialClass(id=..., ...)`` etc, via
    :data:`_ENTITY_CTOR_NODE_TYPES`) within the SAME file -- deliberately NOT
    cross-file (a module-level ID constant shared between files still
    resolves per-file, since the constructor/add_node call and the
    edge-creation call are always co-located in every real producer today).
    """
    bindings: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Attribute) and node.func.attr == "add_node":
            if not node.args:
                continue
            type_value: str | None = None
            if len(node.args) >= 2:
                type_value = _enum_member_value(node.args[1], NodeType, "NodeType")
            for kw in node.keywords:
                if kw.arg in ("_node_type", "node_type"):
                    resolved = _enum_member_value(kw.value, NodeType, "NodeType")
                    if resolved is not None:
                        type_value = resolved
            if type_value is None:
                continue
            key = _id_key(node.args[0])
            if key is not None:
                bindings[key] = type_value
        elif isinstance(node.func, ast.Name) and node.func.id in _ENTITY_CTOR_NODE_TYPES:
            id_kw = next((kw for kw in node.keywords if kw.arg == "id"), None)
            if id_kw is None:
                continue
            key = _id_key(id_kw.value)
            if key is not None:
                bindings[key] = _ENTITY_CTOR_NODE_TYPES[node.func.id]
    return bindings


def _add_edge_call_shape(call: ast.Call) -> tuple[ast.expr | None, ast.expr | None]:
    """``add_edge(source, target, edge_type=X)``'s (source, edge_type) exprs.

    Supports both the 3rd-positional protocol form and the ``edge_type=``
    keyword authoring form (:meth:`~babylon.topology.graph.BabylonGraph.add_edge`).
    """
    source_expr = call.args[0] if len(call.args) >= 2 else None
    edge_type_expr = call.args[2] if len(call.args) >= 3 else None
    for kw in call.keywords:
        if kw.arg == "edge_type":
            edge_type_expr = kw.value
    return source_expr, edge_type_expr


def _relationship_call_shape(call: ast.Call) -> tuple[ast.expr | None, ast.expr | None]:
    """``Relationship(source_id=X, edge_type=Y, ...)``'s (source, edge_type) exprs."""
    source_expr: ast.expr | None = None
    edge_type_expr: ast.expr | None = None
    for kw in call.keywords:
        if kw.arg == "source_id":
            source_expr = kw.value
        elif kw.arg == "edge_type":
            edge_type_expr = kw.value
    return source_expr, edge_type_expr


def _edge_stamp_shape(call: ast.Call) -> tuple[ast.expr | None, ast.expr | None]:
    """Dispatch one call node to its (source, edge_type) expr pair, if any."""
    if isinstance(call.func, ast.Attribute) and call.func.attr == "add_edge":
        return _add_edge_call_shape(call)
    if isinstance(call.func, ast.Name) and call.func.id == "Relationship":
        return _relationship_call_shape(call)
    return None, None


def edge_source_type_uses(path: Path) -> list[EdgeSourceUse]:
    """Extract every (edge_type, source_node_type) combination a module stamps.

    Recognizes two syntactic forms, matched against a same-file id->type
    binding (see :func:`_local_source_type_bindings`):

    * ``add_edge(source, target, edge_type=EdgeType.X, ...)`` / the
      3rd-positional protocol form (:meth:`~babylon.topology.graph.BabylonGraph.add_edge`,
      the direct-graph-write pattern verb resolvers use) -- the source's key
      is the FIRST positional argument.
    * ``Relationship(source_id=X, target_id=Y, edge_type=EdgeType.Z, ...)``
      (:class:`~babylon.models.entities.relationship.Relationship`, the
      scenario-genesis pattern) -- the source's key is the ``source_id``
      keyword.

    Both a variable source (unresolvable against the same file's bindings)
    and an unresolvable edge type contribute nothing -- honest absence, never
    a guess (mirrors :func:`add_node_attribute_stamps`'s own philosophy).

    :param path: Source file to parse.
    :returns: ``(lineno, edge_type, source_node_type)`` triples, sorted.
    :raises SentinelCheckError: If the file is missing or unparseable.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except OSError as exc:
        raise SentinelCheckError(f"cannot read {path}: {exc}") from exc
    except SyntaxError as exc:
        raise SentinelCheckError(f"cannot parse {path}: {exc}") from exc

    bindings = _local_source_type_bindings(tree)
    uses: list[EdgeSourceUse] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        source_expr, edge_type_expr = _edge_stamp_shape(node)
        if source_expr is None or edge_type_expr is None:
            continue
        edge_value = _enum_member_value(edge_type_expr, EdgeType, "EdgeType")
        if edge_value is None:
            continue
        source_key = _id_key(source_expr)
        if source_key is None:
            continue
        source_type = bindings.get(source_key)
        if source_type is None:
            continue
        uses.append((node.lineno, edge_value, source_type))
    return sorted(set(uses))


# ─────────────────────────────────────────────────────────────────────────────
# Territory wrong-rung keying (Rule f, ADR089-adjacent, #39 T8): the res-3
# inversion class, both directions -- a bare FIPS-shaped literal passed to
# ``Territory(id=...)``, or an H3-cell-derived value passed to
# ``Territory(county_fips=...)``. A NEW, ADDITIVE family (mirrors rule (d)'s
# own precedent) so it cannot risk the well-tested node-vocabulary/edge-shape
# extractors' behavior.
# ─────────────────────────────────────────────────────────────────────────────

#: One Territory-construction wrong-rung-keying finding: ``(lineno, kind,
#: detail)`` where ``kind`` is ``"fips_literal_id"`` (a bare 5-digit string
#: literal passed to ``id=``) or ``"h3_derived_county_fips"`` (an
#: H3-cell-derived value passed to ``county_fips=``), and ``detail`` is the
#: offending literal/expression rendered for the failure message.
TerritoryKeyingUse = tuple[int, str, str]

#: A bare 5-digit FIPS string -- the ``Territory.id`` shape the model's own
#: pattern (``^(T[0-9]{3,}|[0-9a-f]{15})$``) already forbids at runtime; this
#: is the static, pre-runtime early warning for the identical mistake.
_FIPS_LITERAL_RE = re.compile(r"^\d{5}$")


def _is_h3_module_call(node: ast.AST) -> bool:
    """True iff ``node`` is a call of the form ``h3.<anything>(...)``.

    Deliberately narrow: only the ``h3.`` module-attribute call form (the
    ``h3-py`` idiom every real call site in this codebase uses --
    ``h3.polygon_to_cells``/``h3.cell_to_latlng``/etc) counts. A
    differently-named import alias is invisible here -- honest absence over
    a guess, mirroring every other extractor in this module.

    :param node: Any AST node (accepts the broad type so
        :func:`_expr_involves_h3_call` can pass every node
        :func:`ast.walk` yields without a type-narrowing dance).
    """
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "h3"
    )


def _expr_involves_h3_call(expr: ast.expr) -> bool:
    """True iff an ``h3.<call>(...)`` appears anywhere inside ``expr``.

    Anywhere, not just top-level -- ``h3.cell_to_latlng(cell)[0]`` or a
    similarly wrapped form still counts as "the source involves an h3. call".
    """
    return any(_is_h3_module_call(node) for node in ast.walk(expr))


def _h3_derived_names_in_scope(scope: ast.AST) -> set[str]:
    """Names bound, within ``scope``'s OWN lexical scope, to an H3-cell value.

    Three forms, walked in source order (a single forward pass, no full CFG):

    - ``cell = h3.polygon_to_cells(...)[0]`` / ``lat, lon = h3.cell_to_latlng(cell)``
      -- an assignment whose RHS involves an ``h3.`` call.
    - ``for cell in cells:`` where ``cells`` was ITSELF just bound to an
      h3-derived value (Wayne's real production idiom:
      ``cells = h3.polygon_to_cells(polygon, RES)`` then ``for cell in cells:``)
      -- the loop target inherits the iterable's h3-derived-ness.
    - ``x = cells`` (a bare-name RHS already known h3-derived) -- one-hop
      transitive propagation through a rename.

    Scoped to ``scope``'s own body only (:func:`_walk_own_scope` -- never
    crossing a nested ``def``/``class`` boundary), per the rule's explicit
    "within the same function scope" narrowing (a module-level H3 binding
    shared across functions is deliberately NOT traced -- this is the
    documented boundary of what a static scanner can prove without real
    dataflow analysis, mirroring :func:`add_node_attribute_stamps`'s own
    ``update_node``-out-of-scope precedent).
    """
    names: set[str] = set()
    for node in _walk_own_scope(scope):
        targets: list[ast.expr]
        value: ast.expr
        if isinstance(node, ast.Assign):
            targets = node.targets
            value = node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets = [node.target]
            value = node.value
        elif isinstance(node, ast.For):
            targets = [node.target]
            value = node.iter
        else:
            continue
        is_h3_derived = _expr_involves_h3_call(value) or (
            isinstance(value, ast.Name) and value.id in names
        )
        if not is_h3_derived:
            continue
        for target in targets:
            if isinstance(target, ast.Name):
                names.add(target.id)
            elif isinstance(target, (ast.Tuple, ast.List)):
                names.update(elt.id for elt in target.elts if isinstance(elt, ast.Name))
    return names


def territory_keying_uses(path: Path) -> list[TerritoryKeyingUse]:
    """Extract wrong-rung ``Territory(...)`` keying (vocabulary Rule f, #39 T8).

    The res-3 inversion class, both directions: USScenario's historical bug
    minted ``Territory(id=<bare FIPS>)`` (identity must live ONLY in
    ``county_fips`` -- the model's own pattern,
    ``^(T[0-9]{3,}|[0-9a-f]{15})$``, already forbids a bare FIPS in ``id`` at
    runtime; this is the STATIC, pre-runtime, agent-legible early warning for
    the identical mistake). The mirror-image mistake would stamp an
    H3-cell-derived value onto ``county_fips`` -- Wayne's hex path
    (``h3_index``-keyed, no ``county_fips``) and USScenario's county path
    (``county_fips``-keyed, ``h3_index=None``) must never cross.

    Two forms recognised, each scoped to a single ``Territory(...)`` call's
    keyword arguments:

    - ``id="26163"`` (or any 5-digit string literal) -- a bare FIPS-shaped
      literal. A variable, an f-string built from a counter
      (``f"T{i:04d}"``), or an H3-cell variable (``id=cell``) are all
      legitimate and NOT flagged -- this is a static heuristic narrowed to
      what is provable without dataflow analysis: only the literal-FIPS-
      string form is unambiguous (documented narrowing, per the rule's own
      brief).
    - ``county_fips=<expr>`` where ``<expr>`` is directly an
      ``h3.<call>(...)``, or a ``Name`` bound (within the SAME function
      scope -- see :func:`_h3_derived_names_in_scope`) from an expression
      that involves one. The bound expression's h3-derived-ness is followed
      through comprehension targets too (e.g. ``cells = [h3.cell_to_latlng(c)
      for c in raw]`` marks ``cells`` derived, so a subsequent ``for cell in
      cells:`` still inherits it), since :func:`_expr_involves_h3_call` walks
      the whole expression, comprehension bodies included.

    :param path: Source file to parse.
    :returns: ``(lineno, kind, detail)`` triples, sorted by location.
    :raises SentinelCheckError: If the file is missing or unparseable (exit 2
        — infrastructure failure, never a silent pass).
    """
    tree = parse_module(path)
    uses: list[TerritoryKeyingUse] = []

    scopes: list[ast.AST] = [tree]
    scopes.extend(
        node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )
    for scope in scopes:
        h3_names = _h3_derived_names_in_scope(scope)
        for node in _walk_own_scope(scope):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "Territory"
            ):
                continue
            for kw in node.keywords:
                if kw.arg == "id":
                    value = kw.value
                    if (
                        isinstance(value, ast.Constant)
                        and isinstance(value.value, str)
                        and _FIPS_LITERAL_RE.match(value.value)
                    ):
                        uses.append((node.lineno, "fips_literal_id", value.value))
                elif kw.arg == "county_fips":
                    value = kw.value
                    if _expr_involves_h3_call(value) or (
                        isinstance(value, ast.Name) and value.id in h3_names
                    ):
                        uses.append((node.lineno, "h3_derived_county_fips", ast.unparse(value)))
    return sorted(set(uses))


# ─────────────────────────────────────────────────────────────────────────────
# Defines-passthrough closure (task #42 fix wave 1, review MEDIUM-1): a
# production call site invoking a formulas-layer function that declares an
# OPTIONAL ``defines`` parameter must pass it, or it silently falls back to
# that function's own schema-default coefficients -- defeating the run's
# ``services.defines``/``defines.yaml`` override. A NEW, ADDITIVE family of
# helpers (mirrors rule (d)/(f)'s own precedent) -- introspects a function's
# OWN signature (never imports it) to find the ``defines`` parameter's
# positional slot, then scans call sites for either form (keyword or
# correctly-positioned positional argument).
# ─────────────────────────────────────────────────────────────────────────────


def optional_defines_param_index(path: Path, func_name: str) -> int | None:
    """Positional index of an OPTIONAL ``defines`` parameter, if any.

    Reads ``path`` with :mod:`ast` (no import, no execution) and inspects the
    module-level function named ``func_name``.

    :param path: Source file declaring ``func_name``.
    :param func_name: The module-level function to inspect.
    :returns: The parameter's 0-based positional index among ``args.args``
        if ``func_name`` declares a ``defines`` parameter WITH a default
        value (the "silently falls back to a schema default" shape this
        sentinel exists for) -- ``None`` if the function is absent from
        ``path``, declares no ``defines`` parameter at all, or declares one
        WITHOUT a default. A required parameter cannot be silently omitted
        -- Python raises ``TypeError`` at the call site -- so that shape is
        out of this sentinel's scope by construction, not by oversight.
    :raises SentinelCheckError: If the file is missing or unparseable.
    """
    tree = parse_module(path)
    for node in tree.body:
        if not (isinstance(node, ast.FunctionDef) and node.name == func_name):
            continue
        names = [a.arg for a in node.args.args]
        if "defines" not in names:
            return None
        index = names.index("defines")
        num_defaults = len(node.args.defaults)
        first_defaulted_index = len(names) - num_defaults
        if index < first_defaulted_index:
            return None  # required parameter -- out of scope
        return index
    return None


def calls_missing_keyword_or_positional_arg(
    path: Path, func_name: str, arg_name: str, positional_index: int
) -> list[int]:
    """Line numbers of calls to ``func_name`` in ``path`` that omit ``arg_name``.

    A call is considered to SATISFY the argument (and is therefore not
    reported) if ``arg_name`` is passed as a keyword, passed positionally
    (enough positional arguments reach ``positional_index``), or the call
    includes a ``**kwargs``-style unpack (an unresolvable catch-all --
    honest absence over a false positive, mirroring every other extractor in
    this module's documented "cannot resolve without value-flow analysis"
    boundary).

    :param path: Source file to scan for call sites.
    :param func_name: The bare function name to match (``f(...)`` or
        ``module.f(...)`` / ``obj.f(...)`` -- matched on the final
        attribute, like :func:`node_type_uses`'s own call-site matching).
    :param arg_name: The keyword argument name that must be supplied.
    :param positional_index: 0-based positional slot ``arg_name`` occupies
        in the callee's signature (see :func:`optional_defines_param_index`).
    :returns: Sorted, de-duplicated line numbers of offending calls.
    :raises SentinelCheckError: If the file is missing or unparseable.
    """
    tree = parse_module(path)
    misses: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        called_name: str | None = None
        if isinstance(node.func, ast.Name):
            called_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            called_name = node.func.attr
        if called_name != func_name:
            continue
        if any(kw.arg == arg_name for kw in node.keywords):
            continue
        if any(kw.arg is None for kw in node.keywords):
            continue  # **kwargs unpack -- cannot prove absence statically
        if len(node.args) > positional_index:
            continue
        misses.add(node.lineno)
    return sorted(misses)


# ─────────────────────────────────────────────────────────────────────────────
# Gate-satisfaction guard grounding (T1.1 U4, ai/_inbox/t11-seam-severity-
# design.md §3.2 point 1): three construct-entry guard SHAPES a production
# early-return can take when a required input is absent. Each helper below
# grounds ONE shape -- confirms the guard literally exists in a named source
# file -- so a :class:`~babylon.sentinels.seam_algebra.registry.GatedInput`
# row citing a guard that has since been edited away fails loud (an
# infrastructure error) rather than silently reading as still-enforced.
# ─────────────────────────────────────────────────────────────────────────────


def attribute_is_none_guard_lines(path: Path, attr_name: str) -> list[int]:
    """Line numbers where some object's ``.attr_name`` is compared to ``None``.

    Matches ``<expr>.attr_name is None`` and the reversed ``None is
    <expr>.attr_name`` anywhere in ``path`` -- the ``services.X is None``
    early-return guard shape (e.g. ``services.distribution_calculator is
    None``, ``services.melt_calculator is None``).

    :param path: Source file to scan.
    :param attr_name: The attribute name compared to ``None``.
    :returns: Sorted, de-duplicated line numbers.
    :raises SentinelCheckError: If the file is missing or unparseable.
    """
    tree = parse_module(path)
    lines: set[int] = set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Compare) and len(node.ops) == 1):
            continue
        if not isinstance(node.ops[0], ast.Is):
            continue
        for operand, other in ((node.left, node.comparators[0]), (node.comparators[0], node.left)):
            if (
                isinstance(operand, ast.Attribute)
                and operand.attr == attr_name
                and isinstance(other, ast.Constant)
                and other.value is None
            ):
                lines.add(node.lineno)
    return sorted(lines)


def dict_get_call_lines(path: Path, key: str) -> list[int]:
    """Line numbers of ``<obj>.get("<key>")`` call sites.

    The ``context.get(K)`` early-return guard shape (e.g.
    ``context.get("vol2_step")``).

    :param path: Source file to scan.
    :param key: The literal string key argument to match.
    :returns: Sorted, de-duplicated line numbers.
    :raises SentinelCheckError: If the file is missing or unparseable.
    """
    tree = parse_module(path)
    lines: set[int] = set()
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and node.args
        ):
            continue
        first = node.args[0]
        if isinstance(first, ast.Constant) and first.value == key:
            lines.add(node.lineno)
    return sorted(lines)


def hasattr_guard_lines(path: Path, attr_name: str) -> list[int]:
    """Line numbers of ``hasattr(<expr>, "<attr_name>")`` call sites.

    The optional-attribute early-return guard shape (e.g. ``context.session_id
    if hasattr(context, "session_id") else None``).

    :param path: Source file to scan.
    :param attr_name: The literal attribute-name argument to match.
    :returns: Sorted, de-duplicated line numbers.
    :raises SentinelCheckError: If the file is missing or unparseable.
    """
    tree = parse_module(path)
    lines: set[int] = set()
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "hasattr"
            and len(node.args) >= 2
        ):
            continue
        second = node.args[1]
        if isinstance(second, ast.Constant) and second.value == attr_name:
            lines.add(node.lineno)
    return sorted(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Stub-vs-calculator grounding (T1.1 U5, ai/_inbox/t11-seam-severity-design.md
# §3.2 point 2): a live production call site constructs a value type with a
# bare literal/neutral constant for one field, even though a registered
# production calculator exists elsewhere that computes exactly that value from
# real inputs. Two helpers ground the two halves of that claim -- "the literal
# is really there" (consumer side) and "the calculator really exists and
# really returns that type" (calculator side) -- so a
# :class:`~babylon.sentinels.seam_algebra.registry.StubConsumer`/
# :class:`~babylon.sentinels.seam_algebra.registry.RegisteredCalculator` row
# that has since gone stale (the stub was wired up, or the calculator renamed)
# fails loud rather than silently reading as still-live.
# ─────────────────────────────────────────────────────────────────────────────


def literal_keyword_call_lines(path: Path, symbol: str, field: str) -> list[int]:
    """Line numbers of ``symbol(..., field=<literal>, ...)`` call sites.

    Matches a call whose callee resolves to ``symbol`` (a bare ``Name`` or the
    final component of an ``Attribute`` chain -- the same call-name matching
    :func:`calls_missing_keyword_or_positional_arg` already uses) AND whose
    ``field`` keyword argument is a bare :class:`ast.Constant` (``True``/
    ``False``/a number/a string). A keyword bound to anything else -- a
    variable, a function call, an attribute read, an f-string built from real
    data -- is, by construction, NOT a literal/neutral-constant stub and is
    invisible to this rule: honest absence over a guess, mirroring every other
    extractor's documented "cannot resolve without value-flow analysis"
    boundary. This is deliberately the anti-false-positive heuristic for the
    stub-vs-calculator check (design §3.2 point 2): the rule only ever
    classifies a bare constant as a stub candidate, never a computed
    expression, so a genuinely input-derived value (however trivial-looking)
    can never be misread as one.

    :param path: Source file to scan for call sites.
    :param symbol: The bare constructor/function name to match.
    :param field: The keyword-argument name whose value must be a literal.
    :returns: Sorted, de-duplicated line numbers.
    :raises SentinelCheckError: If the file is missing or unparseable.
    """
    tree = parse_module(path)
    lines: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        called_name: str | None = None
        if isinstance(node.func, ast.Name):
            called_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            called_name = node.func.attr
        if called_name != symbol:
            continue
        for kw in node.keywords:
            if kw.arg == field and isinstance(kw.value, ast.Constant):
                lines.add(node.lineno)
    return sorted(lines)


def module_level_function_names(path: Path) -> frozenset[str]:
    """Names of every module-level ``def``/``async def`` in ``path``.

    :param path: Source file to parse.
    :returns: The function names declared directly at module scope (never a
        nested/class method -- mirrors :func:`returned_dict_keys`'s own
        module-level-only lookup).
    :raises SentinelCheckError: If the file is missing or unparseable.
    """
    tree = parse_module(path)
    return frozenset(
        node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )


def function_return_annotation_name(path: Path, func_name: str) -> str | None:
    """The bare name of ``func_name``'s ``->`` return-type annotation, if any.

    Handles the plain ``-> Name:`` form and the quoted forward-reference form
    (``-> "Name":``) -- both appear across this codebase depending on whether
    the module carries ``from __future__ import annotations``.

    :param path: Source file declaring ``func_name``.
    :param func_name: The module-level function to inspect.
    :returns: The annotation's bare name, or ``None`` if ``func_name`` is
        absent at module level, declares no return annotation, or the
        annotation is not a simple ``Name``/string-literal (a subscripted
        generic like ``tuple[int, ...]`` is out of scope -- honest absence
        over a guess).
    :raises SentinelCheckError: If the file is missing or unparseable.
    """
    tree = parse_module(path)
    for node in tree.body:
        if not (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name
        ):
            continue
        annotation = node.returns
        if isinstance(annotation, ast.Name):
            return annotation.id
        if isinstance(annotation, ast.Constant) and isinstance(annotation.value, str):
            return annotation.value
        return None
    return None
