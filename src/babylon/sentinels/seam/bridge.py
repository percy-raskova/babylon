"""Bridge serializer-introspection machinery — the Python-side half of the
retired Sensor-3 whole-wire sweep.

What survives the WO-54 cutover is the ``ast`` machinery that walks
``web/game/urls.py`` -> ``web/game/api.py`` -> ``web/game/engine_bridge.py``
and recovers each view's emitted dict keys (:func:`_returned_dict_keys`) — the
gating G4 economy-dashboard check in ``checks.py`` consumes it. The TS-anchored
sweep itself (:func:`check_bridge_serialization` and its ``endpoints.ts`` /
``types/*.ts`` readers) was excised by the cutover: ``src/frontend`` no longer
exists, so there is no Py<->TS contract left to guard. When a successor client
lands a typed contract, a new sensor guards THAT seam.
"""

from __future__ import annotations

import ast
from pathlib import Path

from babylon.sentinels.base import SentinelCheckError

#: Repo root (this file is ``<root>/src/babylon/sentinels/seam/bridge.py``).
_REPO_ROOT: Path = Path(__file__).resolve().parents[4]

_URLS_PATH: Path = _REPO_ROOT / "web" / "game" / "urls.py"
_API_PATH: Path = _REPO_ROOT / "web" / "game" / "api.py"
_ENGINE_BRIDGE_PATH: Path = _REPO_ROOT / "web" / "game" / "engine_bridge.py"

#: The frontend module attribute the routes reference (``api.game_economy``).
_API_MODULE_NAME: str = "api"
#: The bridge instance the views serialize through (``bridge.get_*``).
_BRIDGE_VAR: str = "bridge"


def _parse(path: Path) -> ast.Module:
    """Parse a Python source file, turning any failure into a loud sentinel error.

    :param path: The source file to parse.
    :returns: The parsed module AST.
    :raises SentinelCheckError: If the file is missing or unparseable — an
        infrastructure failure (exit 2), never swallowed into a false pass.
    """
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except OSError as exc:
        raise SentinelCheckError(f"cannot read {path}: {exc}") from exc
    except SyntaxError as exc:
        raise SentinelCheckError(f"cannot parse {path}: {exc}") from exc


def _canonical_path(raw: str) -> str:
    """Normalize a Django route OR a frontend URL template to a join key.

    Drops any query string, a leading ``/``/``api/`` prefix, and collapses every
    parameter segment — Django ``<str:game_id>`` / ``<int:tick>`` and manifest
    ``:id`` / ``:entityId`` alike — to a single ``*`` wildcard.
    ``games/<str:game_id>/economy/`` and ``/api/games/:id/economy/`` both map to
    ``games/*/economy``.

    :param raw: A raw route string or URL pattern.
    :returns: The canonical, parameter-agnostic path key.
    """
    without_query = raw.split("?", 1)[0].strip("/")
    if without_query.startswith("api/"):
        without_query = without_query[len("api/") :]
    segments: list[str] = []
    for segment in without_query.split("/"):
        if not segment:
            continue
        if segment.startswith(":") or (segment.startswith("<") and segment.endswith(">")):
            segments.append("*")
        else:
            segments.append(segment)
    return "/".join(segments)


def _view_name_of(arg: ast.expr) -> str | None:
    """Resolve the view identifier a ``path()`` route argument references.

    Handles ``api.game_economy`` (function view -> ``"game_economy"``) and
    ``api.EducateVerbView.as_view()`` (class view -> ``"EducateVerbView"``).

    :param arg: The second positional argument of a ``path(...)`` call.
    :returns: The view/class name, or ``None`` for a form we do not recognise
        (e.g. an inline lambda) — such routes are simply not serializer seams.
    """
    # Function view: api.game_economy
    if (
        isinstance(arg, ast.Attribute)
        and isinstance(arg.value, ast.Name)
        and arg.value.id == _API_MODULE_NAME
    ):
        return arg.attr
    # Class view: api.EducateVerbView.as_view()
    if (
        isinstance(arg, ast.Call)
        and isinstance(arg.func, ast.Attribute)
        and arg.func.attr == "as_view"
        and isinstance(arg.func.value, ast.Attribute)
        and isinstance(arg.func.value.value, ast.Name)
        and arg.func.value.value.id == _API_MODULE_NAME
    ):
        return arg.func.value.attr
    return None


def _route_view_pairs(urls_path: Path = _URLS_PATH) -> dict[str, str]:
    """Discover ``canonical_path -> view`` from every ``path()`` in ``urls.py``.

    :param urls_path: The URL configuration to parse (injectable for tests).
    :returns: Mapping from canonical path to the view/class name serving it.
    :raises SentinelCheckError: If ``urls.py`` is missing or unparseable.
    """
    tree = _parse(urls_path)
    pairs: dict[str, str] = {}
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "path"
            and len(node.args) >= 2
        ):
            continue
        route_arg, view_arg = node.args[0], node.args[1]
        if not (isinstance(route_arg, ast.Constant) and isinstance(route_arg.value, str)):
            continue
        view = _view_name_of(view_arg)
        if view is not None:
            pairs[_canonical_path(route_arg.value)] = view
    return pairs


def _first_bridge_serializer(node: ast.AST) -> str | None:
    """Return the bridge method whose return is this view's wire payload.

    Prefers the first ``bridge.get_*`` call (the read-serializer convention).
    When a view calls the bridge but never through ``get_*`` — the
    ``actions/preview`` shape, whose only call is ``bridge.preview_action(...)``
    — the first bridge call of any name is used instead: its return IS the wire
    payload, and skipping it would silently hide a routed, typed endpoint from
    the sweep (the exact silence this gate exists to forbid).

    :param node: A function or class AST node to scan.
    :returns: The serializer method name (``"get_economy"``) or ``None`` if the
        view never calls the bridge at all (a pure POST submit / DB-only listing).
    """
    fallback: str | None = None
    for sub in ast.walk(node):
        if (
            isinstance(sub, ast.Call)
            and isinstance(sub.func, ast.Attribute)
            and isinstance(sub.func.value, ast.Name)
            and sub.func.value.id == _BRIDGE_VAR
        ):
            if sub.func.attr.startswith("get_"):
                return sub.func.attr
            if fallback is None:
                fallback = sub.func.attr
    return fallback


def _view_serializer_map(api_path: Path = _API_PATH) -> dict[str, str]:
    """Discover ``view -> serializer`` from ``api.py``.

    Every function view and every class-based view method is scanned for its
    serializing bridge call (``get_*`` preferred, any bridge call as fallback —
    see :func:`_first_bridge_serializer`). A view that never calls the bridge is
    omitted here; the sweep still reports it as a blind spot when the manifest
    declares a typed contract for its route.

    :param api_path: The API views module to parse (injectable for tests).
    :returns: Mapping from view/class name to the bridge serializer it calls.
    :raises SentinelCheckError: If ``api.py`` is missing or unparseable.
    """
    tree = _parse(api_path)
    mapping: dict[str, str] = {}
    for node in tree.body:
        # Module-level views: function views AND class-based views (whose `get`
        # method holds the serializer) — both keyed by their top-level name,
        # matching how ``urls.py`` references them (`api.game_economy` /
        # `api.EducateVerbView`).
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            serializer = _first_bridge_serializer(node)
            if serializer is not None:
                mapping[node.name] = serializer
    return mapping


def _own_returns(func: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.expr | None]:
    """Collect the values of ``return`` statements belonging to ``func`` itself.

    Descends through control flow but NOT into nested ``def``/``lambda`` — a
    helper closure's return is not this serializer's wire shape.

    :param func: The serializer function node.
    :returns: One entry per ``return`` (the returned value, or ``None`` for a
        bare ``return``).
    """
    values: list[ast.expr | None] = []

    def visit(node: ast.AST) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda):
                continue
            if isinstance(child, ast.Return):
                values.append(child.value)
            visit(child)

    visit(func)
    return values


def _dict_literal_keys(node: ast.Dict) -> tuple[set[str], bool]:
    """Extract a dict literal's own string keys, flagging any dynamic ones.

    :param node: The ``ast.Dict`` node.
    :returns: ``(literal string keys, has_dynamic_key)`` — ``has_dynamic_key``
        is ``True`` on a ``**spread`` entry or a computed (non-``Constant``)
        key, meaning the dict's true key set cannot be fully known statically.
    """
    keys: set[str] = set()
    dynamic = False
    for key in node.keys:
        if key is None:  # ``**spread`` entry
            dynamic = True
        elif isinstance(key, ast.Constant) and isinstance(key.value, str):
            keys.add(key.value)
        else:  # computed / non-literal key
            dynamic = True
    return keys, dynamic


def _local_dict_var_keys(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
) -> dict[str, set[str] | None]:
    """Track local variables built up as dict literals across several statements.

    Handles the "assemble a payload, then return the variable" idiom
    (``payload = {...}``; ``payload = gate_fn(payload, tier)``;
    ``payload["veil"] = {...}``; ``return payload``) that a bare
    ``return {...}`` check misses entirely — the exact shape G4's own
    veil-gating changes gave ``get_economy_dashboard``. Over-approximates in
    the same safe direction as :func:`_returned_dict_keys` itself: every
    assignment to a name (across every branch) unions into that name's
    tracked key set, never subtracts from it.

    Three patterns recognized per assignment target:

    1. ``name = {...}`` — a dict literal; its keys union into ``name``'s set
       (or mark it dynamic-unresolvable via a ``None`` entry — see below).
    2. ``name = some_call(name, ...)`` — a same-variable "masking"
       reassignment (``gate_value_axis_fields``/``_gate_snapshot_
       territories`` both have this shape: filter/null VALUES, never add or
       remove KEYS) — ``name``'s already-tracked key set is trusted forward
       unchanged. Only trusted when ``name`` is already known; a masking-
       shaped call over an UNTRACKED name proves nothing, so it is marked
       unresolvable.
    3. ``name[<literal str>] = ...`` — one more key added to an already-
       tracked ``name`` (the ``payload["veil"] = {...}`` pattern).

    Any OTHER assignment to a tracked or untracked name (a call that is not a
    same-variable reassignment, a name, a comprehension, ...) marks that name
    unresolvable (``None``) — this function only ever CONFIRMS a stable dict
    shape, never guesses one.

    :param func: The function to scan (does not descend into nested
        ``def``/``lambda`` — same boundary :func:`_own_returns` respects).
    :returns: ``{variable_name: key_set}``; a variable mapped to ``None`` is
        proven NOT resolvable as a stable dict.
    """
    tracked: dict[str, set[str] | None] = {}

    def _is_self_reassignment(call: ast.Call, name: str) -> bool:
        return bool(call.args) and isinstance(call.args[0], ast.Name) and call.args[0].id == name

    def visit(node: ast.AST) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda):
                continue
            if isinstance(child, ast.Assign) and len(child.targets) == 1:
                target = child.targets[0]
                if isinstance(target, ast.Name):
                    name = target.id
                    if isinstance(child.value, ast.Dict):
                        literal_keys, dynamic = _dict_literal_keys(child.value)
                        existing = tracked.get(name) or set()
                        tracked[name] = None if dynamic else existing | literal_keys
                    elif (
                        isinstance(child.value, ast.Call)
                        and _is_self_reassignment(child.value, name)
                        and tracked.get(name) is not None
                    ):
                        pass  # masking reassignment — keep the tracked key set
                    else:
                        tracked[name] = None
                elif (
                    isinstance(target, ast.Subscript)
                    and isinstance(target.value, ast.Name)
                    and isinstance(target.slice, ast.Constant)
                    and isinstance(target.slice.value, str)
                ):
                    name = target.value.id
                    existing_keys = tracked.get(name)
                    if existing_keys is not None:
                        tracked[name] = existing_keys | {target.slice.value}
            visit(child)

    visit(func)
    return tracked


def _self_call_name(value: ast.expr | None) -> str | None:
    """Return the method name if ``value`` is a ``self.<method>(...)`` call.

    :param value: A return statement's value expression (``None`` for a bare
        ``return`` — ``_own_returns`` may hand back either).
    :returns: The method name, or ``None`` if ``value`` is not a same-class
        method call (module-level function calls, e.g.
        ``gate_value_axis_fields(payload, tier)``, are NOT delegation —
        they mask/derive a value, they do not hand off "this IS the wire
        shape" the way ``self.<method>()`` does).
    """
    if (
        isinstance(value, ast.Call)
        and isinstance(value.func, ast.Attribute)
        and isinstance(value.func.value, ast.Name)
        and value.func.value.id == "self"
    ):
        return value.func.attr
    return None


def _returned_dict_keys(
    engine_path: Path, func_name: str, *, _depth: int = 0
) -> tuple[frozenset[str], str]:
    """Extract a serializer's emitted top-level keys and classify its return shape.

    Generalizes ``provenance._emitted_property_keys`` from a nested ``properties``
    sub-dict to **the function's own returned dict**. Unions the literal string
    keys across every ``return {...}`` in the function (over-approximating in the
    safe direction — an error-branch return only adds keys, never removes them).

    G4 Task C (delegation-blindness, the standing "sentinel every error class"
    rule): a return value that resolves to a stable dict shape via
    :func:`_local_dict_var_keys` (the "build up a local variable, return it"
    idiom) OR a single-hop ``self.<method>()`` call (:func:`_self_call_name` —
    the ``get_economy`` -> ``get_economy_dashboard`` pure-delegation shape)
    contributes ITS keys instead of collapsing the whole function to
    ``"delegated"``. Deliberately single-hop: ``_depth`` caps recursion at one
    level, so a delegation chain longer than one hop (or an accidental cycle)
    reports as ``"delegated"`` rather than resolving arbitrarily deep chains —
    this is a documented limit, not an oversight (see the multi-hop test).

    :param engine_path: The bridge source holding the serializer.
    :param func_name: The serializer method name (``"get_economy"``).
    :param _depth: Internal recursion guard — single-hop delegation only
        follows from ``_depth == 0``; callers never pass this explicitly.
    :returns: ``(literal string keys, shape)`` where ``shape`` is one of
        ``"dict"`` (checkable — directly or via a resolved delegation),
        ``"opaque"`` (dict built with ``**spread`` / dynamic keys —
        uncheckable), ``"list"``, ``"delegated"`` (returns an unresolved
        call/name), ``"missing"`` (no value-returning statement), or
        ``"absent"`` (no such serializer defined here — a view references it
        but the real bridge does not define it: reported as a blind spot, not
        a hard error, so one dead serializer never aborts the whole sweep).
    :raises SentinelCheckError: If the bridge source is missing or unparseable.
    """
    tree = _parse(engine_path)
    target: ast.FunctionDef | ast.AsyncFunctionDef | None = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == func_name:
            target = node
            break
    if target is None:
        return frozenset(), "absent"

    local_vars = _local_dict_var_keys(target)

    keys: set[str] = set()
    found_dict = found_list = found_delegated = dynamic = False
    for value in _own_returns(target):
        if isinstance(value, ast.Dict):
            found_dict = True
            literal_keys, is_dynamic = _dict_literal_keys(value)
            keys |= literal_keys
            dynamic = dynamic or is_dynamic
        elif isinstance(value, ast.List | ast.ListComp | ast.SetComp | ast.DictComp):
            found_list = True
        elif _depth == 0 and (delegate := _self_call_name(value)) is not None:
            delegate_keys, delegate_shape = _returned_dict_keys(
                engine_path, delegate, _depth=_depth + 1
            )
            if delegate_shape == "dict":
                found_dict = True
                keys |= delegate_keys
            else:
                found_delegated = True
        elif isinstance(value, ast.Name) and (resolved := local_vars.get(value.id)) is not None:
            found_dict = True
            keys |= resolved
        elif isinstance(value, ast.Call | ast.Name | ast.Attribute | ast.Subscript):
            found_delegated = True

    if found_dict and dynamic:
        shape = "opaque"
    elif found_dict:
        shape = "dict"
    elif found_list:
        shape = "list"
    elif found_delegated:
        shape = "delegated"
    else:
        shape = "missing"
    return frozenset(keys), shape
