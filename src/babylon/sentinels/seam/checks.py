"""Seam continuity (Sensor 1) — the static coverage gate.

Fails loudly when a player-observable quantity drifts across the engine ->
web-bridge -> frontend seam without being declared in
:data:`babylon.sentinels.seam.registry.SEAM_REGISTRY`. This is Babylon's
mechanical enforcement of Constitution VIII.12 (no silent no-op / disarmed
guardrail) and III.11 (Loud Failure): the failure mode this catches is
*silence* — a metric computed, serialized, and then rendered blank while every
test stays green.

**Static by contract.** These checks never run the engine or Django; they read
source with :mod:`ast` (via :mod:`babylon.sentinels._ast`) and diff sets against
the imported registry (layer-0.5 pure Python, so importing it carries no
engine/web weight). Staying static is what lets the gate live in the always-on
dev fast-gate (``mise run check`` -> ``check:seams``).

Checks come in two tiers. **Gating** checks red the fast-gate (exit 1):
``check_map_metrics`` (registry MAP-scope keys vs ``map_contract.py``'s
``MAP_METRIC_PROPERTIES``), ``check_tick_payloads_exist`` (every registered
``tick_*`` payload exists in the engine write-set),
``check_severity_vocabulary`` (T1.1 U2: no local ``_EVENT_SEVERITY`` literal
has reappeared — severity is single-sourced via
``babylon.models.event_severity.resolve_severity``), and ``check_fog_field_mirror``
(Sensor 4: the fog political
field vocabulary — ``filter.py``'s ``POLITICAL_FIELDS``/``ORG_INTERNAL_STATE_FIELDS``
vs ``fogFields.ts``'s ``FOG_FIELD_LABELS`` — agrees exactly, both directions).
**Advisory** checks print loudly but do NOT gate — they
surface pre-existing drift awaiting a scoped remediation before promotion:
``check_tick_coverage``, ``check_narrator_vocabulary``, ``check_event_coverage``.

Run via the family CLI: ``poetry run python tools/sentinel_check.py seam --check``.
Exit 0 = clean (gating passed; advisory findings may still print), 1 = gating
violations, 2 = infrastructure failure (source missing or unparseable — itself a
loud failure, never swallowed).
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

from babylon.models.enums.events import EventType
from babylon.sentinels._ast import (
    eventtype_names_in_module,
    literal_dict_keys,
    literal_str_tuple,
    parse_module,
    tick_write_set,
)
from babylon.sentinels.base import LabelledCheck, SentinelCheckError, run_sensor
from babylon.sentinels.seam.bridge import _returned_dict_keys, check_bridge_serialization
from babylon.sentinels.seam.fog_provenance import check_fog_field_mirror
from babylon.sentinels.seam.provenance import check_admin_feature_emission
from babylon.sentinels.seam.registry import SEAM_REGISTRY
from babylon.sentinels.seam.types import SeamEntry, SeamScope

#: Repo root (this file is ``<root>/src/babylon/sentinels/seam/checks.py``).
_REPO_ROOT: Path = Path(__file__).resolve().parents[4]

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
#: The bus->pydantic builder registry (Phase 2 extracted the converter's
#: if/elif chain here); a missing EventType key drops that event to None.
_EVENT_BUILDERS_PATH: Path = _REPO_ROOT / "src" / "babylon" / "engine" / "event_builders.py"


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
    :raises SentinelCheckError: If ``map_contract.py`` cannot be parsed.
    """
    contract = set(literal_str_tuple(_MAP_CONTRACT_PATH, _MAP_CONTRACT_VAR))
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


def _economy_dashboard_registry_keys(registry: tuple[SeamEntry, ...]) -> set[str]:
    """Registry ``ECONOMY``-scope wire keys whose ``read_paths`` cite
    ``get_economy_dashboard`` specifically.

    ``SeamScope.ECONOMY`` is shared by TWO distinct emitters —
    ``get_economy_dashboard`` (this check's concern) and
    ``get_game_timeseries`` (a completely different payload, e.g.
    ``crisis_pop_share``/``price_index`` — see the ``_ECONOMY_SERIES_
    METRICS``/``_ECONOMY_TIMESERIES_SCISSORS_METRICS`` registry blocks). A
    bare ``scope is SeamScope.ECONOMY`` filter would conflate the two and
    report every ``get_game_timeseries``-only row as a phantom. Filtering on
    ``read_paths`` (every row cites its real emitter there) keeps the two
    apart the same way the registry's own docstrings already do.

    :param registry: The registry to filter.
    :returns: The union of ``wire_keys`` across matching rows.
    """
    keys: set[str] = set()
    for entry in registry:
        if entry.scope is SeamScope.ECONOMY and any(
            "get_economy_dashboard" in path for path in entry.read_paths
        ):
            keys.update(entry.wire_keys)
    return keys


def check_economy_dashboard_keys(
    registry: tuple[SeamEntry, ...] = SEAM_REGISTRY,
    engine_path: Path = _ENGINE_BRIDGE_PATH,
) -> list[str]:
    """GATING: reconcile registry economy_dashboard.* keys against
    ``get_economy_dashboard``'s REAL emitted keys (G4 Task C).

    Analogous to :func:`check_map_metrics` (registry vs. a source-of-truth,
    both directions red the gate), but for the ECONOMY scope's
    ``get_economy_dashboard`` payload — the "standing owner rule: sentinel
    every error class" response to the delegation-blindness the audit found:
    ``get_economy`` delegates its no-``territory_id`` path entirely to
    ``get_economy_dashboard`` (``return self.get_economy_dashboard(...)``),
    which used to make :func:`~babylon.sentinels.seam.bridge.
    check_bridge_serialization`'s advisory sweep report the WHOLE surface as
    an unverifiable "delegated" blind spot — silently skipping exactly the
    kind of missing-registration defect (``tick``/``has_data``/
    ``rent_extracted``/``exploitation_rate`` all went unregistered) this
    check now GATES on directly. Harvests through
    :func:`~babylon.sentinels.seam.bridge._returned_dict_keys`, the same
    delegation-aware (single-hop ``self.<method>()`` + local-dict-variable)
    harvester Task C(i) fixed generically — not special-cased to
    ``get_economy_dashboard`` by name, so any future serializer with the
    same shape benefits identically.

    :param registry: The registry to check (injectable for tests).
    :param engine_path: The bridge source to harvest keys from (injectable).
    :returns: Sorted violation strings (empty when the two sets match).
    :raises SentinelCheckError: If ``get_economy_dashboard`` cannot be found/
        parsed, OR resolves to a non-``dict`` shape — an economy-scope
        regression this check exists to gate can never silently pass as
        "nothing to check" (Constitution III.11: loud, not silent).
    """
    emitted, shape = _returned_dict_keys(engine_path, "get_economy_dashboard")
    if shape != "dict":
        raise SentinelCheckError(
            f"get_economy_dashboard returns a {shape!r} shape — cannot verify the ECONOMY "
            f"scope's registry coverage against it (fix the harvester or the serializer; "
            f"this scope may never silently go unverifiable)"
        )
    registered = _economy_dashboard_registry_keys(registry)

    violations: list[str] = []
    for missing in sorted(emitted - registered):
        violations.append(
            f"get_economy_dashboard emits {missing!r} but it is not registered in "
            f"SEAM_REGISTRY (scope=ECONOMY)"
        )
    for phantom in sorted(registered - emitted):
        violations.append(
            f"economy wire key {phantom!r} is registered (scope=ECONOMY, "
            f"get_economy_dashboard) but the serializer never emits it — a phantom a "
            f"component reading it would get undefined from"
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
    :raises SentinelCheckError: If ``graph_bridge.py`` cannot be parsed.
    """
    write_set = tick_write_set(_GRAPH_BRIDGE_PATH)
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
    :raises SentinelCheckError: If ``graph_bridge.py`` cannot be parsed.
    """
    write_set = tick_write_set(_GRAPH_BRIDGE_PATH)
    registered_payloads = {entry.payload for entry in SEAM_REGISTRY}
    return [
        f"engine writes tick attr {attr!r}, not registered as an observable "
        f"(Phase 3 decides whether it crosses the seam)"
        for attr in sorted(write_set - registered_payloads)
    ]


def check_severity_vocabulary(path: Path = _ENGINE_BRIDGE_PATH) -> list[str]:
    """GATING: no local ``_EVENT_SEVERITY`` literal may reappear in the bridge.

    T1.1 U2 (``ai/_inbox/t11-seam-severity-design.md``) single-sourced event
    severity: both the web bridge and the Archive Chronicle now resolve through
    :func:`babylon.models.event_severity.resolve_severity` (the generated table
    derived from kind x terminal_proximity), replacing the hand-copied 47-entry
    ``_EVENT_SEVERITY``/``EVENT_SEVERITY`` dict literals this check used to
    validate — a severity key keyed on a non-``EventType`` string is now
    structurally impossible (``EventKindRow.event_type: EventType`` is a typed
    Pydantic field, checked at import). This check's narrower day-one job is
    the inverse: catch a hand-copied literal reappearing here at all, which
    would be exactly the silent-drift failure mode single-sourcing eliminates.
    U6 (the ``seam_algebra`` family) generalizes this into the full three-way
    (web / Archive / generated) parity gate this check is a placeholder for.

    :param path: The source file that must carry no ``_EVENT_SEVERITY``
        module-level assignment (injectable so tests can supply a
        deliberately-regressed fixture to prove the gate reds).
    :returns: A single violation string if a local ``_EVENT_SEVERITY``
        assignment exists, else an empty list.
    :raises SentinelCheckError: If ``path`` cannot be parsed.
    """
    tree = parse_module(path)
    for node in tree.body:
        targets: list[ast.expr]
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        if any(isinstance(t, ast.Name) and t.id == "_EVENT_SEVERITY" for t in targets):
            return [
                f"{path}: a local _EVENT_SEVERITY literal has reappeared — severity must "
                "resolve through babylon.models.event_severity.resolve_severity (T1.1 U2 "
                "single-source), never a hand-copied dict"
            ]
    return []


def check_narrator_vocabulary() -> list[str]:
    """ADVISORY: ``narrator._TEMPLATES`` keys that are not ``EventType`` values.

    A template keyed on a non-``EventType`` string renders no bespoke story (the
    event falls to the generic template). The remaining drift here is *crafted*
    endgame/mechanic narrative content whose correct fix is a product decision
    (activate via outcome-aware narration vs remove) — a separate remediation, so
    this stays advisory until that scope is ruled.

    :returns: Advisory strings, one per non-EventType template key.
    :raises SentinelCheckError: If ``narrator.py`` cannot be parsed.
    """
    event_values = {e.value for e in EventType}
    templates = set(literal_dict_keys(_NARRATOR_PATH, "_TEMPLATES"))
    return [
        f"narrator._TEMPLATES key {key!r} is not an EventType value — crafted-but-unreachable "
        f"template (endgame-outcome or eventless mechanic)"
        for key in sorted(templates - event_values)
    ]


def check_event_coverage() -> list[str]:
    """ADVISORY: ``EventType`` members dropped before they reach the wire.

    An ``EventType`` absent from ``event_builders.EVENT_BUILDERS`` gets no
    builder, so the ``_convert_bus_event_to_pydantic`` dispatcher returns
    ``None`` for it at the bus->pydantic boundary and it never reaches the
    player. Advisory because many unhandled members are intentionally
    non-narrative (calibration / internal) events; owner triages which deserve
    conversion. ``EVENT_CLASS_MAP`` is excluded — its keys are computed
    (``EventType.X.value``), not static literals, with a safe class fallback.

    :returns: One advisory summary line naming the unhandled members (or empty).
    :raises SentinelCheckError: If ``event_builders.py`` cannot be parsed.
    """
    event_names = {e.name for e in EventType}
    handled = eventtype_names_in_module(_EVENT_BUILDERS_PATH)
    unhandled = sorted(event_names - handled)
    if not unhandled:
        return []
    return [
        f"EVENT_BUILDERS handles {len(handled)}/{len(event_names)} EventTypes; "
        f"{len(unhandled)} drop to None at the bus->pydantic boundary (never reach the wire): "
        f"{', '.join(unhandled)}"
    ]


#: Gating Sensor-1 checks: a violation reds the dev fast-gate (exit 1).
_GATING_CHECKS: tuple[LabelledCheck, ...] = (
    ("map metric not reconciled with MAP_METRIC_PROPERTIES", check_map_metrics),
    ("registered tick_* payload missing from the engine write-set", check_tick_payloads_exist),
    ("a local _EVENT_SEVERITY literal has reappeared in the bridge", check_severity_vocabulary),
    (
        "economy_dashboard key not reconciled with get_economy_dashboard (G4 Task C)",
        check_economy_dashboard_keys,
    ),
    (
        "fog political field-list drift between filter.py and fogFields.ts (Sensor 4)",
        check_fog_field_mirror,
    ),
)

#: Advisory Sensor-1 checks: findings are printed loudly but do NOT gate — the
#: surfaced drift is pre-existing and awaits a scoped remediation before any is
#: promoted into ``_GATING_CHECKS``.
_ADVISORY_CHECKS: tuple[LabelledCheck, ...] = (
    ("engine tick_* write not registered as an observable", check_tick_coverage),
    ("narrator._TEMPLATES keyed on a non-EventType string", check_narrator_vocabulary),
    ("EventType dropped before the wire (converter coverage)", check_event_coverage),
    (
        "AdminFeatureProperties field the map emitter never sends (Sensor 3)",
        check_admin_feature_emission,
    ),
    (
        "bridge serializer/TS emission drift + unrouted seams (Sensor 3 sweep)",
        check_bridge_serialization,
    ),
)


def _summary(advisory_count: int) -> str:
    """Build the clean one-line summary printed when no gating violation occurred."""
    summary = f"Seam continuity (Sensor 1): clean — {len(SEAM_REGISTRY)} registered observables."
    if advisory_count:
        summary += f" ({advisory_count} advisory findings above — pre-existing, non-gating.)"
    return summary


def main(argv: list[str] | None = None) -> int:
    """Run every seam Sensor-1 check; print violations; return the exit code.

    :param argv: CLI args (``--check`` is accepted as the CI-mode alias; the
        behavior is always to gate).
    :returns: 0 clean, 1 violations found, 2 infrastructure failure.
    """
    parser = argparse.ArgumentParser(description="Seam continuity — Sensor 1 (VIII.12 gate).")
    parser.add_argument(
        "--check",
        action="store_true",
        help="CI-mode alias; the tool always gates (exit 1 on violations).",
    )
    parser.parse_args(argv)
    return run_sensor("SEAM", _GATING_CHECKS, _ADVISORY_CHECKS, _summary)


if __name__ == "__main__":
    sys.exit(main())
