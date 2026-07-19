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
