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

Phase 1 ships one check — ``check_map_metrics`` — reconciling the registry's
``MAP``-scope wire keys against ``web/game/map_contract.py``'s
``MAP_METRIC_PROPERTIES`` (the spec-109 A3 single source of truth). Later phases
add ``check_tick_attrs`` / ``check_event_tables`` / ``check_bridge_serialization``.

Run: ``poetry run python tools/seam_registry_check.py --check``. Exit 0 = clean,
1 = violations (printed to stderr), 2 = infrastructure failure (source missing
or unparseable — itself a loud failure, never swallowed).
"""

from __future__ import annotations

import argparse
import ast
import sys
from collections.abc import Callable
from pathlib import Path

from babylon.seams.registry import SEAM_REGISTRY
from babylon.seams.types import SeamEntry, SeamScope

#: Repo root (this file is ``<root>/tools/seam_registry_check.py``).
_REPO_ROOT: Path = Path(__file__).resolve().parents[1]

#: The spec-109 A3 map contract — the single source of truth for /map/ lenses.
_MAP_CONTRACT_PATH: Path = _REPO_ROOT / "web" / "game" / "map_contract.py"
_MAP_CONTRACT_VAR: str = "MAP_METRIC_PROPERTIES"


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


#: Every Sensor-1 check: ``(human label, zero-arg callable -> violations)``.
_CHECKS: tuple[tuple[str, Callable[[], list[str]]], ...] = (
    ("map metric not reconciled with MAP_METRIC_PROPERTIES", check_map_metrics),
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
    for label, check in _CHECKS:
        try:
            violations = check()
        except SeamCheckError as exc:
            print(f"SEAM SENSOR-1 ERROR: {exc}", file=sys.stderr)
            return 2
        for violation in violations:
            print(f"SEAM VIOLATION [{label}]: {violation}", file=sys.stderr)
            exit_code = 1

    if exit_code == 0:
        print(f"Seam continuity (Sensor 1): clean — {len(SEAM_REGISTRY)} registered observables.")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
