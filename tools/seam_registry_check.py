#!/usr/bin/env python3
"""Sensor 1 (Continuity) of the Seam Observatory — the static coverage gate.

Fails loudly when a player-observable quantity drifts across the engine ->
web-bridge -> frontend seam without being declared in
:data:`babylon.seams.registry.SEAM_REGISTRY`. This is Babylon's mechanical
enforcement of Constitution VIII.12 (no silent no-op / disarmed guardrail) and
III.11 (Loud Failure): the failure mode this catches is *silence* — a metric
computed, serialized, and then rendered blank while every test stays green.

**Static by contract.** This sensor never runs the engine or Django; it reads
source with :mod:`ast` and diffs sets against the imported registry (the registry
is layer-0.5 pure Python, so importing it carries no engine/web weight). Keeping
it static is what lets it live in the always-on dev fast-gate (``mise run
check`` -> ``check:seams``).

Checks come in two tiers. **Gating** checks red the fast-gate (exit 1):
``check_map_metrics`` (registry MAP-scope keys vs ``map_contract.py``'s
``MAP_METRIC_PROPERTIES``), ``check_tick_payloads_exist`` (every registered
``tick_*`` payload exists in the engine write-set), and
``check_severity_vocabulary`` (every ``_EVENT_SEVERITY`` key is a real
``EventType`` value). **Advisory** checks print loudly but do NOT gate — they
surface pre-existing drift awaiting a scoped remediation before promotion:
``check_tick_coverage`` (engine ``tick_*`` writes not yet registered),
``check_narrator_vocabulary`` (crafted-but-unreachable ``_TEMPLATES`` keys), and
``check_event_coverage`` (EventTypes dropped before the wire). Phase 3 adds
``check_bridge_serialization``.

Run: ``poetry run python tools/seam_registry_check.py --check``. Exit 0 = clean
(gating passed; advisory findings may still print), 1 = gating violations,
2 = infrastructure failure (source missing or unparseable — itself a loud
failure, never swallowed).
"""

from __future__ import annotations

import argparse
import ast
import sys
from collections.abc import Callable
from pathlib import Path

from babylon.models.enums.events import EventType
from babylon.seams.registry import SEAM_REGISTRY
from babylon.seams.types import SeamEntry, SeamScope

#: Repo root (this file is ``<root>/tools/seam_registry_check.py``).
_REPO_ROOT: Path = Path(__file__).resolve().parents[1]

#: The spec-109 A3 map contract — the single source of truth for /map/ lenses.
_MAP_CONTRACT_PATH: Path = _REPO_ROOT / "web" / "game" / "map_contract.py"
_MAP_CONTRACT_VAR: str = "MAP_METRIC_PROPERTIES"

#: The engine's per-territory ``tick_*`` write-site (``update_node`` kwargs).
_GRAPH_BRIDGE_PATH: Path = (
    _REPO_ROOT / "src" / "babylon" / "domain" / "economics" / "tick" / "graph_bridge.py"
)
#: The two capped event vocabularies that silently default when they drift.
_NARRATOR_PATH: Path = _REPO_ROOT / "web" / "game" / "narrator.py"
_ENGINE_BRIDGE_PATH: Path = _REPO_ROOT / "web" / "game" / "engine_bridge.py"
#: The bus-event -> pydantic converter (an unhandled EventType drops to None).
_SIM_ENGINE_PATH: Path = _REPO_ROOT / "src" / "babylon" / "engine" / "simulation_engine.py"


class SeamCheckError(RuntimeError):
    """A sensor could not run — source missing or unparseable (exit 2, not 1).

    Distinguishes *infrastructure* failure (the gate itself is broken) from a
    *coverage* violation (the gate works and found drift). Both are loud; only
    the latter is a registry problem to fix by editing rows.
    """


def _literal_str_tuple(path: Path, var_name: str) -> tuple[str, ...]:
    """Statically extract a module-level ``tuple``/``list`` of string literals.

    Reads ``path`` with :mod:`ast` (no import, no execution) and returns the
    string constants assigned to ``var_name``. Comments and non-string elements
    are ignored so an inline-documented literal parses cleanly.

    :param path: Source file to parse.
    :param var_name: The assigned name to extract (``Assign`` or ``AnnAssign``).
    :returns: The string-literal elements, in source order.
    :raises SeamCheckError: If the file is missing, unparseable, the name is
        absent, or its value is not a tuple/list literal.
    """
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SeamCheckError(f"cannot read {path}: {exc}") from exc
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        raise SeamCheckError(f"cannot parse {path}: {exc}") from exc

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
            raise SeamCheckError(f"{path}:{var_name} is not a tuple/list literal")
        return tuple(
            elt.value
            for elt in value.elts
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
        )
    raise SeamCheckError(f"{path}: no module-level assignment to {var_name!r} found")


def _literal_dict_keys(path: Path, var_name: str) -> tuple[str, ...]:
    """Statically extract the string keys of a module-level ``dict`` literal.

    :param path: Source file to parse.
    :param var_name: The assigned name whose ``dict`` literal to read.
    :returns: The string-literal keys, in source order (non-literal keys — e.g.
        ``EventType.X.value`` — are skipped, so a computed-key map yields an
        empty tuple rather than raising).
    :raises SeamCheckError: If the file is missing/unparseable, the name is
        absent, or its value is not a dict literal.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except OSError as exc:
        raise SeamCheckError(f"cannot read {path}: {exc}") from exc
    except SyntaxError as exc:
        raise SeamCheckError(f"cannot parse {path}: {exc}") from exc

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
            raise SeamCheckError(f"{path}:{var_name} is not a dict literal")
        return tuple(
            k.value for k in value.keys if isinstance(k, ast.Constant) and isinstance(k.value, str)
        )
    raise SeamCheckError(f"{path}: no module-level assignment to {var_name!r} found")


def _tick_write_set(path: Path) -> set[str]:
    """Collect the ``tick_*`` keyword names the engine writes via ``update_node``.

    This is the engine side of the seam — the per-territory state the tick
    dynamics stamp onto graph nodes. Extracted statically (no engine run) by
    walking every ``*.update_node(...)`` call and taking its ``tick_``-prefixed
    keyword arguments.

    :param path: The ``graph_bridge.py`` source to parse.
    :returns: The set of ``tick_*`` attribute names written.
    :raises SeamCheckError: If the source is missing or unparseable.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except OSError as exc:
        raise SeamCheckError(f"cannot read {path}: {exc}") from exc
    except SyntaxError as exc:
        raise SeamCheckError(f"cannot parse {path}: {exc}") from exc

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


def _eventtype_names_in_func(path: Path, func_name: str) -> set[str]:
    """Collect the ``EventType.<NAME>`` members referenced inside a function.

    Used to measure how many ``EventType`` members a dispatcher (e.g.
    ``_convert_bus_event_to_pydantic``) actually handles — the rest fall through
    to a silent default.

    :param path: The source file to parse.
    :param func_name: The function whose body to scan.
    :returns: The set of referenced ``EventType`` member names.
    :raises SeamCheckError: If the source is missing or unparseable.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except OSError as exc:
        raise SeamCheckError(f"cannot read {path}: {exc}") from exc
    except SyntaxError as exc:
        raise SeamCheckError(f"cannot parse {path}: {exc}") from exc

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


def _registry_wire_keys(scope: SeamScope, registry: tuple[SeamEntry, ...]) -> set[str]:
    """Collect every wire key registered under ``scope``.

    :param scope: The observable surface to filter by.
    :param registry: The registry to read (injected so tests can supply a
        deliberately-broken one to prove the sensor reds).
    :returns: The union of ``wire_keys`` across matching registry rows.
    """
    keys: set[str] = set()
    for entry in registry:
        if entry.scope is scope:
            keys.update(entry.wire_keys)
    return keys


def check_map_metrics(registry: tuple[SeamEntry, ...] = SEAM_REGISTRY) -> list[str]:
    """Reconcile registry ``MAP``-scope wire keys against ``MAP_METRIC_PROPERTIES``.

    The map contract (``web/game/map_contract.py``) is the SoT; the registry must
    mirror it exactly. A metric emitted on ``/map/`` features but absent from the
    registry is undeclared drift; a registry map metric the contract never
    advertises is a phantom. Both red the gate.

    :param registry: The registry to check (defaults to the real
        :data:`SEAM_REGISTRY`; injectable for tests).
    :returns: Sorted violation strings (empty when the two sets are equal).
    :raises SeamCheckError: If ``map_contract.py`` cannot be parsed.
    """
    contract = set(_literal_str_tuple(_MAP_CONTRACT_PATH, _MAP_CONTRACT_VAR))
    registered = _registry_wire_keys(SeamScope.MAP, registry)

    violations: list[str] = []
    for missing in sorted(contract - registered):
        violations.append(
            f"map metric {missing!r} is emitted (MAP_METRIC_PROPERTIES) but not "
            f"registered in SEAM_REGISTRY (scope=MAP)"
        )
    for phantom in sorted(registered - contract):
        violations.append(
            f"map metric {phantom!r} is registered (scope=MAP) but not in "
            f"MAP_METRIC_PROPERTIES — a phantom lens the backend never emits"
        )
    return violations


def check_tick_payloads_exist(registry: tuple[SeamEntry, ...] = SEAM_REGISTRY) -> list[str]:
    """Every registered ``tick_*`` payload must exist in the engine write-set.

    The engine side of the seam: a registry row may declare its payload is the
    graph attribute ``tick_phi_hour``; this asserts the engine actually writes
    that attribute (via ``graph_bridge.py``'s ``update_node``). Catches a row
    citing a renamed or removed engine attribute — a dead payload that would
    read null forever.

    :param registry: The registry to check (injectable for tests).
    :returns: Sorted violation strings (empty when every tick_* payload exists).
    :raises SeamCheckError: If ``graph_bridge.py`` cannot be parsed.
    """
    write_set = _tick_write_set(_GRAPH_BRIDGE_PATH)
    violations: list[str] = []
    for entry in registry:
        if entry.payload.startswith("tick_") and entry.payload not in write_set:
            violations.append(
                f"registry {entry.key!r} declares payload {entry.payload!r} but the engine "
                f"tick write-set has no such attr (renamed/removed in graph_bridge.py?)"
            )
    return sorted(violations)


def check_tick_coverage() -> list[str]:
    """ADVISORY: engine ``tick_*`` writes not registered as observables.

    Surfaces the "neglected seam" gap — quantities the engine computes and
    stamps onto the graph that no registry row claims. Advisory because whether
    each actually crosses the seam to the player is decided by the Phase-3
    bridge-serialization sweep; this makes the candidate surface *visible* now.

    :returns: One advisory string per unregistered ``tick_*`` write.
    :raises SeamCheckError: If ``graph_bridge.py`` cannot be parsed.
    """
    write_set = _tick_write_set(_GRAPH_BRIDGE_PATH)
    registered_payloads = {entry.payload for entry in SEAM_REGISTRY}
    return [
        f"engine writes tick attr {attr!r}, not registered as an observable "
        f"(Phase 3 decides whether it crosses the seam)"
        for attr in sorted(write_set - registered_payloads)
    ]


def check_severity_vocabulary(path: Path = _ENGINE_BRIDGE_PATH) -> list[str]:
    """GATING: every ``_EVENT_SEVERITY`` key must be a real ``EventType`` value.

    A severity key that matches no ``EventType`` value can never classify a real
    event, so that event silently defaults to ``"informational"``. The bridge's
    ``_EVENT_SEVERITY`` was repaired (dead keys removed, aliases fixed to their
    real events) so this gate now passes clean and blocks any regression.

    :param path: The source file holding ``_EVENT_SEVERITY`` (injectable so tests
        can supply a deliberately-broken fixture to prove the gate reds).
    :returns: Sorted violation strings (empty when all keys are EventType values).
    :raises SeamCheckError: If ``path`` cannot be parsed.
    """
    event_values = {e.value for e in EventType}
    severity = set(_literal_dict_keys(path, "_EVENT_SEVERITY"))
    return [
        f"_EVENT_SEVERITY key {key!r} is not an EventType value — matching events "
        f"silently default to 'informational'"
        for key in sorted(severity - event_values)
    ]


def check_narrator_vocabulary() -> list[str]:
    """ADVISORY: ``narrator._TEMPLATES`` keys that are not ``EventType`` values.

    A template keyed on a non-``EventType`` string renders no bespoke story (the
    event falls to the generic template). The remaining drift here is *crafted*
    endgame/mechanic narrative content whose correct fix is a product decision
    (activate via outcome-aware narration vs remove) — a separate remediation, so
    this stays advisory until that scope is ruled.

    :returns: Advisory strings, one per non-EventType template key.
    :raises SeamCheckError: If ``narrator.py`` cannot be parsed.
    """
    event_values = {e.value for e in EventType}
    templates = set(_literal_dict_keys(_NARRATOR_PATH, "_TEMPLATES"))
    return [
        f"narrator._TEMPLATES key {key!r} is not an EventType value — crafted-but-unreachable "
        f"template (endgame-outcome or eventless mechanic)"
        for key in sorted(templates - event_values)
    ]


def check_event_coverage() -> list[str]:
    """ADVISORY: ``EventType`` members dropped before they reach the wire.

    ``_convert_bus_event_to_pydantic`` not handling an ``EventType`` returns
    ``None`` for that event at the bus->pydantic boundary, so it never reaches
    the player. Advisory because many unhandled members are intentionally
    non-narrative (calibration / internal) events; owner triages which deserve
    conversion. ``EVENT_CLASS_MAP`` is excluded — its keys are computed
    (``EventType.X.value``), not static literals, with a safe class fallback.

    :returns: One advisory summary line naming the unhandled members (or empty).
    :raises SeamCheckError: If ``simulation_engine.py`` cannot be parsed.
    """
    event_names = {e.name for e in EventType}
    handled = _eventtype_names_in_func(_SIM_ENGINE_PATH, "_convert_bus_event_to_pydantic")
    unhandled = sorted(event_names - handled)
    if not unhandled:
        return []
    return [
        f"_convert_bus_event_to_pydantic handles {len(handled)}/{len(event_names)} EventTypes; "
        f"{len(unhandled)} drop to None at the bus->pydantic boundary (never reach the wire): "
        f"{', '.join(unhandled)}"
    ]


#: Gating Sensor-1 checks: a violation reds the dev fast-gate (exit 1).
_GATING_CHECKS: tuple[tuple[str, Callable[[], list[str]]], ...] = (
    ("map metric not reconciled with MAP_METRIC_PROPERTIES", check_map_metrics),
    ("registered tick_* payload missing from the engine write-set", check_tick_payloads_exist),
    ("_EVENT_SEVERITY keyed on a non-EventType string", check_severity_vocabulary),
)

#: Advisory Sensor-1 checks: findings are printed loudly but do NOT gate — the
#: surfaced drift is pre-existing and awaits a scoped remediation before any is
#: promoted into ``_GATING_CHECKS``.
_ADVISORY_CHECKS: tuple[tuple[str, Callable[[], list[str]]], ...] = (
    ("engine tick_* write not registered as an observable", check_tick_coverage),
    ("narrator._TEMPLATES keyed on a non-EventType string", check_narrator_vocabulary),
    ("EventType dropped before the wire (converter coverage)", check_event_coverage),
)


def main(argv: list[str] | None = None) -> int:
    """Run every Sensor-1 check; print violations; return the exit code.

    :param argv: CLI args (``--check`` is accepted as the CI-mode alias; the
        behavior is always to gate).
    :returns: 0 clean, 1 violations found, 2 infrastructure failure.
    """
    parser = argparse.ArgumentParser(description="Seam Observatory — Sensor 1 (continuity gate).")
    parser.add_argument(
        "--check",
        action="store_true",
        help="CI-mode alias; the tool always gates (exit 1 on violations).",
    )
    parser.parse_args(argv)

    exit_code = 0
    try:
        for label, check in _GATING_CHECKS:
            for violation in check():
                print(f"SEAM VIOLATION [{label}]: {violation}", file=sys.stderr)
                exit_code = 1
        advisory_count = 0
        for label, check in _ADVISORY_CHECKS:
            for finding in check():
                print(f"SEAM ADVISORY [{label}]: {finding}", file=sys.stderr)
                advisory_count += 1
    except SeamCheckError as exc:
        print(f"SEAM SENSOR-1 ERROR: {exc}", file=sys.stderr)
        return 2

    if exit_code == 0:
        summary = (
            f"Seam continuity (Sensor 1): clean — {len(SEAM_REGISTRY)} registered observables."
        )
        if advisory_count:
            summary += f" ({advisory_count} advisory findings above — pre-existing, non-gating.)"
        print(summary)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
