"""Seam bridge-serialization sweep — the autonomous whole-wire emission gate.

Sensor 3's ``provenance.py`` proves emission honesty for *one* serializer (the
map emitter) against *one* TS interface. This module generalizes that to the
**entire** engine→web-bridge→frontend surface — every dashboard, inspector, and
entity serializer — and does so with **zero hand-maintained mapping table**. The
serializer↔interface pairing is *discovered* from the code's own wiring, so the
gate's coverage is a pure function of the current codebase: add an endpoint and
it is picked up on the next run; remove one and it drops out.

Three static hops, joined on a canonical URL path:

1. **Route → view** — ``web/game/urls.py`` ``path("games/<id>/economy/", api.game_economy)``.
2. **View → serializer** — ``web/game/api.py`` ``game_economy`` body's single
   ``bridge.get_economy(...)`` call (class-based verb views: the ``get`` method).
3. **Path → interface** — the typed endpoint manifest
   ``src/frontend/src/api/endpoints.ts`` ``ep<EconomyDashboardPayload>("/api/games/:id/economy/")``.

Joining (1)+(2) gives ``canonical_path → serializer``; (3) gives
``canonical_path → interface``; the intersection yields the checkable pairs. For
each, the serializer's emitted dict keys are diffed against the interface's
declared fields — a declared-but-unemitted field is a **phantom** (a component
reads it and gets ``undefined``: a silent blank). Everything that does *not*
resolve to a checkable pair is reported as a **loud blind spot** (serializer with
no typed endpoint; endpoint with no backend route; ``Untyped`` manifest row;
list/delegated/opaque serializer return) — never silently skipped, never
hand-excluded. A blind spot IS the signal: a seam the codebase has not yet wired
through a typed contract.

Advisory, not gating: the first sweep surfaces a large pre-existing backlog, and
each phantom/blind-spot needs an owner ruling (emit it, type it, or drop it)
before it can harden into a gate. Layer-0.5 pure — ``ast`` over ``.py``, regex
over ``.ts``; no engine import, no Node.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from babylon.sentinels.base import SentinelCheckError
from babylon.sentinels.seam.provenance import _KNOWN_NORMALISATIONS, _NORMALISED_INTO

#: Repo root (this file is ``<root>/src/babylon/sentinels/seam/bridge.py``).
_REPO_ROOT: Path = Path(__file__).resolve().parents[4]

_URLS_PATH: Path = _REPO_ROOT / "web" / "game" / "urls.py"
_API_PATH: Path = _REPO_ROOT / "web" / "game" / "api.py"
_ENGINE_BRIDGE_PATH: Path = _REPO_ROOT / "web" / "game" / "engine_bridge.py"
_ENDPOINTS_TS_PATH: Path = _REPO_ROOT / "src" / "frontend" / "src" / "api" / "endpoints.ts"
_TS_TYPES_DIR: Path = _REPO_ROOT / "src" / "frontend" / "src" / "types"

#: The frontend module attribute the routes reference (``api.game_economy``).
_API_MODULE_NAME: str = "api"
#: The bridge instance the views serialize through (``bridge.get_*``).
_BRIDGE_VAR: str = "bridge"

#: Type names that carry no field-checkable shape at the fetch boundary — the
#: sweep reports them as blind spots rather than diffing. ``Untyped`` is the
#: manifest's explicit punch-list marker; the rest are generic/opaque containers.
_UNCHECKABLE_TYPES: frozenset[str] = frozenset(
    {"Untyped", "unknown", "RawEntity", "Record", "object", "any"}
)


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


def _returned_dict_keys(engine_path: Path, func_name: str) -> tuple[frozenset[str], str]:
    """Extract a serializer's emitted top-level keys and classify its return shape.

    Generalizes ``provenance._emitted_property_keys`` from a nested ``properties``
    sub-dict to **the function's own returned dict**. Unions the literal string
    keys across every ``return {...}`` in the function (over-approximating in the
    safe direction — an error-branch return only adds keys, never removes them).

    :param engine_path: The bridge source holding the serializer.
    :param func_name: The serializer method name (``"get_economy"``).
    :returns: ``(literal string keys, shape)`` where ``shape`` is one of
        ``"dict"`` (checkable), ``"opaque"`` (dict built with ``**spread`` /
        dynamic keys — uncheckable), ``"list"``, ``"delegated"`` (returns a
        call/name), ``"missing"`` (no value-returning statement), or ``"absent"``
        (no such serializer defined here — a view references it but the real
        bridge does not define it: reported as a blind spot, not a hard error,
        so one dead serializer never aborts the whole sweep).
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

    keys: set[str] = set()
    found_dict = found_list = found_delegated = dynamic = False
    for value in _own_returns(target):
        if isinstance(value, ast.Dict):
            found_dict = True
            for key in value.keys:
                if key is None:  # ``**spread`` entry
                    dynamic = True
                elif isinstance(key, ast.Constant) and isinstance(key.value, str):
                    keys.add(key.value)
                else:  # computed / non-literal key
                    dynamic = True
        elif isinstance(value, ast.List | ast.ListComp | ast.SetComp | ast.DictComp):
            found_list = True
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


def _frontend_endpoint_pairs(endpoints_path: Path = _ENDPOINTS_TS_PATH) -> dict[str, str]:
    """Discover ``canonical_path -> declared interface`` from the endpoint manifest.

    Regex-scans ``endpoints.ts`` for ``ep<Interface>("/api/...")`` declarations.
    First declaration wins on a canonical-path collision (GET rows precede their
    POST siblings in the manifest, so the readable-shape row is kept).

    :param endpoints_path: The typed endpoint manifest (injectable for tests).
    :returns: Mapping from canonical path to the declared response type name.
    :raises SentinelCheckError: If the manifest is missing.
    """
    try:
        source = endpoints_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SentinelCheckError(f"cannot read {endpoints_path}: {exc}") from exc

    # Anchor to a real object-property declaration (``key: ep<...>("...")``) at
    # line start, so an ``ep<Interface>("/api/...")`` example inside a doc
    # comment cannot leak in as a phantom endpoint.
    declaration = re.compile(
        r"""^[ \t]*\w+\s*:\s*ep<\s*([^>]+?)\s*>\s*\(\s*["']([^"']+)["']""",
        re.MULTILINE,
    )
    pairs: dict[str, str] = {}
    for match in declaration.finditer(source):
        interface = match.group(1).strip()
        canon = _canonical_path(match.group(2))
        pairs.setdefault(canon, interface)
    return pairs


def _interface_fields(ts_dir: Path, interface: str) -> set[str] | None:
    """Read the field names of a TS ``interface`` from any file under ``ts_dir``.

    Layer-0.5 regex parse (no Node/TS): finds ``export interface <name> ... {``
    (tolerating an ``extends`` clause) and reads each ``field?:`` / ``field:``
    identifier at the top of the block.

    :param ts_dir: The frontend ``types/`` directory to search.
    :param interface: The interface name to resolve.
    :returns: The declared field names, or ``None`` if no file declares the
        interface (an external/generic type such as ``FeatureCollection`` — the
        caller treats a ``None`` as an honest, reported blind spot).
    :raises SentinelCheckError: If ``ts_dir`` cannot be listed.
    """
    try:
        ts_files = sorted(ts_dir.glob("*.ts"))
    except OSError as exc:
        raise SentinelCheckError(f"cannot list {ts_dir}: {exc}") from exc

    pattern = re.compile(
        rf"export\s+interface\s+{re.escape(interface)}\b[^{{]*\{{(.*?)\}}",
        re.DOTALL,
    )
    for path in ts_files:
        match = pattern.search(path.read_text(encoding="utf-8"))
        if match is not None:
            body = match.group(1)
            return set(re.findall(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\??\s*:", body, re.MULTILINE))
    return None


def _known_normalisations(interface: str) -> frozenset[str]:
    """Fields a serializer legitimately does not emit literally, by interface.

    Only ``AdminFeatureProperties`` has such a set today (the ``group_key``
    collapse discovered in ``provenance.py``); every other interface has none, so
    an unemitted declared field is a genuine phantom.

    :param interface: The interface being checked.
    :returns: The allowlist of declared-but-normalised fields for that interface.
    """
    if interface == "AdminFeatureProperties":
        return _KNOWN_NORMALISATIONS | _NORMALISED_INTO
    return frozenset()


def _is_uncheckable(interface: str) -> bool:
    """Whether a declared type carries no field-checkable shape (blind spot).

    :param interface: The declared response type name from the manifest.
    :returns: ``True`` for the ``Untyped`` punch-list marker, a list type
        (``Foo[]``), or a generic/opaque container.
    """
    return interface.endswith("[]") or interface in _UNCHECKABLE_TYPES


def check_bridge_serialization(
    urls_path: Path = _URLS_PATH,
    api_path: Path = _API_PATH,
    engine_path: Path = _ENGINE_BRIDGE_PATH,
    endpoints_path: Path = _ENDPOINTS_TS_PATH,
    ts_dir: Path = _TS_TYPES_DIR,
) -> list[str]:
    """ADVISORY: reconcile every bridge serializer with its typed UI contract.

    For each backend route whose view calls a ``bridge.get_*`` serializer, join
    to the typed endpoint manifest and, when both sides resolve to a checkable
    interface, report every declared field the serializer never emits (a phantom
    silent-blank). Everything unresolved is reported as a loud blind spot: a
    serializer with no manifest entry, a manifest entry with no backend route, an
    ``Untyped``/list/opaque contract. Coverage is a pure function of the current
    routes + manifest — no hand table, so the check grows and contracts with the
    codebase.

    All arguments are injectable so tests can supply tiny fixtures proving the
    check reds on a planted phantom or an unrouted serializer.

    :returns: Sorted advisory strings (phantoms + blind spots); empty when the
        whole reconciled surface is honest.
    :raises SentinelCheckError: If any discovery source is missing/unparseable.
    """
    route_to_view = _route_view_pairs(urls_path)
    view_to_serializer = _view_serializer_map(api_path)
    path_to_interface = _frontend_endpoint_pairs(endpoints_path)

    findings: list[str] = []
    for canon, view in sorted(route_to_view.items()):
        serializer = view_to_serializer.get(view)
        if serializer is None:
            # No bridge call at all. Silence is only honest when nothing is
            # promised either: a typed manifest row with no serializer to check
            # it against is an unverifiable promise — a loud blind spot.
            interface = path_to_interface.get(canon)
            if interface is not None and not _is_uncheckable(interface):
                findings.append(
                    f"[{canon}] endpoints.ts declares {interface} but view {view} calls no "
                    f"bridge serializer — emission honesty unverifiable at this seam "
                    f"(serialize through the bridge or retype the manifest row)"
                )
            continue  # not a serializer seam (POST resolver / DB listing / redirect)

        interface = path_to_interface.get(canon)
        if interface is None:
            findings.append(
                f"[{canon}] serializer {serializer} reaches the wire but no endpoints.ts "
                f"entry declares this path — unrouted to a typed UI contract "
                f"(add a manifest row / confirm the endpoint is live)"
            )
            continue
        if _is_uncheckable(interface):
            findings.append(
                f"[{canon}] {serializer} -> {interface}: no field-checkable interface yet "
                f"(punch-list: give the response a typed contract)"
            )
            continue

        keys, shape = _returned_dict_keys(engine_path, serializer)
        if shape == "absent":
            findings.append(
                f"[{canon}] view calls bridge.{serializer}() but engine_bridge.py defines no "
                f"such serializer — dead/misrouted (stub-only fallback or renamed)"
            )
            continue
        if shape != "dict":
            findings.append(
                f"[{canon}] serializer {serializer} returns a {shape} shape — keys not "
                f"statically extractable; emission honesty unverifiable (blind spot)"
            )
            continue

        declared = _interface_fields(ts_dir, interface)
        if declared is None:
            findings.append(
                f"[{canon}] {serializer} -> {interface}: interface not declared under types/ "
                f"(external/generic type — emission unverifiable here)"
            )
            continue

        phantoms = declared - keys - _known_normalisations(interface)
        findings.extend(
            f"[{canon}] {interface} declares {field!r} but serializer {serializer} never "
            f"emits it — a component reading it gets undefined (silent blank)"
            for field in sorted(phantoms)
        )

    # Reverse direction: a typed endpoint the backend no longer serves.
    backend_paths = set(route_to_view)
    for canon, interface in sorted(path_to_interface.items()):
        if canon not in backend_paths:
            findings.append(
                f"[{canon}] endpoints.ts declares {interface} but no backend route serves this "
                f"path — dead or renamed endpoint (drop the manifest row or restore the route)"
            )

    return sorted(findings)
