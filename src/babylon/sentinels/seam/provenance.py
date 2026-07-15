"""Seam Sensor 3 (provenance) — the emission-honesty gate.

Sensor 1 proves an observable is *wired*; Sensor 2 proves it is *alive*. Sensor 3
proves the frontend is not promised a field the backend never sends — the
"rendered but ``undefined``" failure mode, where a wire *type* declares a
property that no serializer emits, so any component reading it silently gets a
blank.

This module holds the static half: an AST diff of the keys the map emitter
(``web/game/engine_bridge.py`` ``_aggregate_hex_features``) actually writes into
``feature.properties`` versus the fields the frontend ``AdminFeatureProperties``
interface (``src/frontend/src/types/game.ts``) declares. It is **rename-aware**:
the emitter normalises every per-zoom group-identity column
(``county_fips`` / ``state_fips`` / ``msa_code`` / ``bea_ea_code`` — the
``group_key_map`` values) down to a single ``group_key`` (+ ``group_name`` /
``zoom``), so those declared-but-not-literally-emitted fields are *normalisations*
the frontend deliberately routes around (``regionFill.ts``), not phantoms. What
remains after accounting for the normalisation is a **genuine phantom** — a typed
field with no backend source at all.

Advisory, not gating: like Sensor 1's coverage advisories, a genuine phantom
needs an owner ruling (emit it from the backend, or drop it from the type) before
it can become a hard gate. The check makes the drift *visible* so it stops hiding.

Layer-0.5 pure Python (``ast`` + a regex over the ``.ts`` interface — no engine,
no Node); it lives in the always-on fast-gate via the seam CLI.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from babylon.sentinels.base import SentinelCheckError

#: Repo root (this file is ``<root>/src/babylon/sentinels/seam/provenance.py``).
_REPO_ROOT: Path = Path(__file__).resolve().parents[4]

_ENGINE_BRIDGE_PATH: Path = _REPO_ROOT / "web" / "game" / "engine_bridge.py"
_GAME_TS_PATH: Path = _REPO_ROOT / "src" / "frontend" / "src" / "types" / "game.ts"

#: The emitter whose ``feature.properties`` dict is the backend contract for /map/.
_EMITTER_FUNC: str = "_aggregate_hex_features"
#: The per-zoom group-identity map inside it; its VALUES are the columns the
#: emitter normalises into ``group_key`` (so they are declared-but-not-emitted by
#: design, not phantoms).
_GROUP_KEY_MAP_VAR: str = "group_key_map"
#: The frontend interface whose fields must each trace to an emitted key.
_ADMIN_INTERFACE: str = "AdminFeatureProperties"

#: Emitted normalisation targets the group-identity columns collapse into. Any
#: declared ``*_name`` / commuting-zone / level field is represented by one of
#: these, so it is a normalisation, not a phantom.
_NORMALISED_INTO: frozenset[str] = frozenset({"group_key", "group_name", "zoom"})
#: Declared group-identity fields the emitter represents via ``group_key`` /
#: ``group_name`` / ``zoom`` rather than emitting literally (frontend routes
#: around these — see regionFill.ts). Kept explicit so a NEW declared field that
#: is *not* one of these surfaces as a genuine phantom instead of being masked.
_KNOWN_NORMALISATIONS: frozenset[str] = frozenset(
    {
        "county_fips",
        "state_fips",
        "state_name",
        "msa_code",
        "msa_name",
        "bea_ea_code",
        "bea_ea_name",
        "cz_id",
        "cz_name",
        "group_level",
    }
)


def _emitted_property_keys(path: Path, func_name: str) -> set[str]:
    """Collect the string keys of the ``"properties"`` dict emitted in ``func_name``.

    Walks ``func_name`` for a ``dict`` literal that is the value of a
    ``"properties"`` key (the GeoJSON feature's property bag) and returns its
    literal string keys — the exact set the backend serialises to the wire.

    :param path: The ``engine_bridge.py`` source to parse.
    :param func_name: The emitter function to scan.
    :returns: The emitted ``properties`` key set.
    :raises SentinelCheckError: If the source is missing/unparseable or the
        function or its ``properties`` dict cannot be found (a moved emitter must
        fail loud, never silently report an empty — hence non-vacuous).
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except OSError as exc:
        raise SentinelCheckError(f"cannot read {path}: {exc}") from exc
    except SyntaxError as exc:
        raise SentinelCheckError(f"cannot parse {path}: {exc}") from exc

    for node in ast.walk(tree):
        if not (isinstance(node, ast.FunctionDef) and node.name == func_name):
            continue
        for sub in ast.walk(node):
            if not isinstance(sub, ast.Dict):
                continue
            for key, value in zip(sub.keys, sub.values, strict=True):
                if (
                    isinstance(key, ast.Constant)
                    and key.value == "properties"
                    and isinstance(value, ast.Dict)
                ):
                    return {
                        k.value
                        for k in value.keys
                        if isinstance(k, ast.Constant) and isinstance(k.value, str)
                    }
        raise SentinelCheckError(
            f"{path}:{func_name} has no literal 'properties' dict — emitter moved? "
            "(Sensor 3 cannot verify emission honestly against a shape it can't find)"
        )
    raise SentinelCheckError(f"{path}: function {func_name!r} not found")


def _group_key_map_values(path: Path, func_name: str, var_name: str) -> set[str]:
    """Collect the VALUES of the ``var_name`` dict literal inside ``func_name``.

    These are the group-identity columns the emitter normalises into
    ``group_key`` — declared-but-not-emitted by design.

    :param path: The ``engine_bridge.py`` source to parse.
    :param func_name: The function the map is defined in.
    :param var_name: The map variable (``group_key_map``).
    :returns: The map's string values (empty if the var is absent — the map is an
        optimisation detail, so its absence is not itself a hard failure).
    :raises SentinelCheckError: If the source is missing or unparseable.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except OSError as exc:
        raise SentinelCheckError(f"cannot read {path}: {exc}") from exc
    except SyntaxError as exc:
        raise SentinelCheckError(f"cannot parse {path}: {exc}") from exc

    for node in ast.walk(tree):
        if not (isinstance(node, ast.FunctionDef) and node.name == func_name):
            continue
        for sub in ast.walk(node):
            if (
                isinstance(sub, ast.Assign)
                and isinstance(sub.value, ast.Dict)
                and any(isinstance(t, ast.Name) and t.id == var_name for t in sub.targets)
            ):
                return {
                    v.value
                    for v in sub.value.values
                    if isinstance(v, ast.Constant) and isinstance(v.value, str)
                }
    return set()


def _declared_interface_fields(path: Path, interface: str) -> set[str]:
    """Extract the field names of a TypeScript ``interface`` by name.

    A small regex over the ``.ts`` source (no Node/TS parser at layer 0.5): take
    the ``interface <name> { ... }`` block and read each ``field?:`` / ``field:``
    identifier. Interface field names are simple identifiers, so a regex is
    sufficient and keeps the check dependency-free.

    :param path: The ``game.ts`` source.
    :param interface: The interface whose fields to read.
    :returns: The declared field names.
    :raises SentinelCheckError: If the file is missing or the interface is absent
        (a renamed/removed interface must fail loud, not silently pass).
    """
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SentinelCheckError(f"cannot read {path}: {exc}") from exc

    match = re.search(
        rf"export\s+interface\s+{re.escape(interface)}\s*\{{(.*?)\}}",
        source,
        re.DOTALL,
    )
    if match is None:
        raise SentinelCheckError(f"{path}: interface {interface!r} not found (renamed/removed?)")
    body = match.group(1)
    return set(re.findall(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\??\s*:", body, re.MULTILINE))


def check_admin_feature_emission(
    engine_path: Path = _ENGINE_BRIDGE_PATH,
    ts_path: Path = _GAME_TS_PATH,
) -> list[str]:
    """ADVISORY: ``AdminFeatureProperties`` fields the map emitter never sends.

    Diffs the frontend interface against the backend ``properties`` emission,
    subtracting the emitter's normalisation set (group-identity columns collapsed
    into ``group_key``). What remains is a **genuine phantom** — a typed field a
    component can read but the backend never produces, rendering blank. A declared
    normalisation that is NOT in the known-normalisation allowlist is *also*
    surfaced (loudly, as a candidate phantom) so the allowlist can't rot.

    :param engine_path: The bridge source holding the emitter (injectable so tests
        can supply a deliberately-broken fixture to prove the check reds).
    :param ts_path: The ``game.ts`` source holding the interface (injectable).
    :returns: One advisory string per genuine phantom (or unexpected normalisation).
    :raises SentinelCheckError: If the emitter or the interface cannot be read.
    """
    emitted = _emitted_property_keys(engine_path, _EMITTER_FUNC)
    normalised_columns = _group_key_map_values(engine_path, _EMITTER_FUNC, _GROUP_KEY_MAP_VAR)
    declared = _declared_interface_fields(ts_path, _ADMIN_INTERFACE)

    # A declared field is honest if the backend emits it literally, OR it is a
    # group-identity column the emitter normalises into group_key/group_name/zoom.
    accounted = emitted | normalised_columns | _NORMALISED_INTO | _KNOWN_NORMALISATIONS
    phantoms = declared - accounted

    return [
        f"AdminFeatureProperties declares {field!r} but the map emitter "
        f"(_aggregate_hex_features) never sends it and it is not a known group-key "
        f"normalisation — a component reading it gets undefined (silent blank)"
        for field in sorted(phantoms)
    ]
