"""Static checks: the qa:regression estate declaration is complete and well-named."""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any, Final

from babylon.sentinels.base import LabelledCheck, SentinelCheckError, run_sensor

_TAG: Final[str] = "GATE-COVERAGE"
#: Repo root (this file is ``<root>/src/babylon/sentinels/gate_coverage/checks.py`` —
#: same depth as ``coverage/checks.py``, whose ``parents[4]`` idiom this mirrors).
_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[4]
_SCENARIOS_PATH: Final[Path] = _REPO_ROOT / "tools" / "regression_scenarios.py"
_ENGINE_PATH: Final[Path] = _REPO_ROOT / "src" / "babylon" / "engine" / "simulation_engine.py"
_BUNDLE_BASELINE: Final[Path] = _REPO_ROOT / "tests" / "baselines" / "detroit-tri-county-5t.json"


def _literal(path: Path, name: str) -> Any:
    """ast.literal_eval the module-level literal ``name`` in ``path``. Loud."""
    if not path.is_file():
        raise SentinelCheckError(f"source not found: {path}")
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as exc:  # pragma: no cover - repo-corruption path
        raise SentinelCheckError(f"unparseable source {path}: {exc}") from exc
    for node in ast.walk(tree):
        target = None
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target, value = node.target.id, node.value
        elif (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
        ):
            target, value = node.targets[0].id, node.value
        if target == name:
            if value is None:
                raise SentinelCheckError(f"{name} in {path} has no value")
            try:
                return ast.literal_eval(value)
            except (ValueError, TypeError) as exc:
                raise SentinelCheckError(f"{name} in {path} is not a pure literal: {exc}") from exc
    raise SentinelCheckError(f"{name} not found in {path}")


def engine_system_names(engine_path: Path = _ENGINE_PATH) -> tuple[str, ...]:
    """The class names in ``_SYSTEM_CLASSES``, by AST (never imported)."""
    if not engine_path.is_file():
        raise SentinelCheckError(f"engine source not found: {engine_path}")
    tree = ast.parse(engine_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        target = (
            node.target
            if isinstance(node, ast.AnnAssign)
            else node.targets[0]
            if len(node.targets) == 1
            else None
        )
        if not (isinstance(target, ast.Name) and target.id == "_SYSTEM_CLASSES"):
            continue
        value = node.value
        if isinstance(value, ast.Tuple):
            names = tuple(elt.id for elt in value.elts if isinstance(elt, ast.Name))
            if names:
                return names
    raise SentinelCheckError(f"_SYSTEM_CLASSES tuple not found in {engine_path}")


def _declared_rows(scenarios_path: Path) -> tuple[Any, Any, Any]:
    coverage = _literal(scenarios_path, "SCENARIO_COVERAGE_DATA")
    gaps = _literal(scenarios_path, "COVERAGE_GAPS_DATA")
    writers = _literal(scenarios_path, "CHANNEL_WRITERS")
    return coverage, gaps, writers


def check_union_covers_all_systems(
    scenarios_path: Path = _SCENARIOS_PATH,
    engine_path: Path = _ENGINE_PATH,
) -> list[str]:
    """Every engine System is evidenced by some scenario OR a declared gap."""
    coverage, gaps, _ = _declared_rows(scenarios_path)
    engine = set(engine_system_names(engine_path))
    evidenced = {row["system"] for entry in coverage for row in entry.get("systems", ())}
    gapped = {row["system"] for row in gaps}
    findings: list[str] = []
    for system in sorted(engine - evidenced - gapped):
        findings.append(
            f"[gate-blindness] {system}: no canonical scenario evidences it and no "
            f"CoverageGap row declares the hole. REMEDY: add SystemEvidence to a "
            f"scenario in {scenarios_path.name}, or a CoverageGap row with reason "
            f"+ remediation."
        )
    for system in sorted(evidenced & gapped):
        findings.append(
            f"[gate-blindness] {system}: both evidenced and declared a gap — "
            f"stale gap row. REMEDY: delete the CoverageGap entry."
        )
    return findings


def check_declared_names_exist(
    scenarios_path: Path = _SCENARIOS_PATH,
    engine_path: Path = _ENGINE_PATH,
) -> list[str]:
    """Every system named anywhere in the declarations is a real engine System."""
    coverage, gaps, writers = _declared_rows(scenarios_path)
    engine = set(engine_system_names(engine_path))
    named: set[str] = set()
    named.update(row["system"] for entry in coverage for row in entry.get("systems", ()))
    named.update(row["system"] for row in gaps)
    for writer_list in writers.values():
        named.update(writer_list)
    return [
        f"[gate-blindness] declared system {name!r} does not exist in "
        f"_SYSTEM_CLASSES. REMEDY: fix the name or delete the row."
        for name in sorted(named - engine)
    ]


def check_bundle_evidence(
    scenarios_path: Path = _SCENARIOS_PATH,
    bundle_path: Path = _BUNDLE_BASELINE,
) -> list[str]:
    """bundle_event/bundle_field evidence rows hold against the committed baseline."""
    coverage, _, _ = _declared_rows(scenarios_path)
    rows = [
        row
        for entry in coverage
        for row in entry.get("systems", ())
        if row.get("kind") in ("bundle_event", "bundle_field")
    ]
    if not rows:
        return []
    if not bundle_path.is_file():
        raise SentinelCheckError(f"bundle baseline not found: {bundle_path}")
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    # Each bundle event's top-level "event_type" key is always the literal
    # string "Event" (the Python class name of the emitted Event object) —
    # useless as a discriminator. The real per-entry event-type string (e.g.
    # "organizational_action", "lifecycle_transition") lives one level
    # deeper, at "details.type" (verified against the committed baseline).
    event_types = {
        details.get("type")
        for e in bundle.get("events", [])
        if isinstance(details := e.get("details"), dict)
    }
    findings: list[str] = []
    for row in rows:
        if row["kind"] == "bundle_event" and row["key"] not in event_types:
            findings.append(
                f"[gate-blindness] {row['system']}: bundle_event {row['key']!r} not "
                f"present in {bundle_path.name}. REMEDY: fix the key or the claim."
            )
        if row["kind"] == "bundle_field":
            node: Any = bundle
            for part in row["key"].split("."):
                if not isinstance(node, dict) or part not in node:
                    findings.append(
                        f"[gate-blindness] {row['system']}: bundle_field "
                        f"{row['key']!r} not present in {bundle_path.name}. "
                        f"REMEDY: fix the dotted path."
                    )
                    break
                node = node[part]
            else:
                # The dotted path fully resolved (no break) — presence alone
                # doesn't prove the claimed System ran when the field is
                # schema-static (always emitted, even 0.0 when inert). Pin
                # the VALUE the row actually relies on: if it equals a
                # declared forbidden_values entry (typically the field's
                # seeded/default value), the evidenced System appears NOT to
                # have run — a future baseline regen collapsing back to that
                # value must red, not stay silently green on presence.
                forbidden = row.get("forbidden_values", ())
                if str(node) in forbidden:
                    findings.append(
                        f"[gate-blindness] {row['system']}: bundle_field "
                        f"{row['key']!r} holds forbidden value {str(node)!r} in "
                        f"{bundle_path.name} — the evidenced system appears NOT "
                        f"to have run. REMEDY: regenerate the baseline honestly, "
                        f"or fix the claim."
                    )
    return findings


_GATING_CHECKS: Final[tuple[LabelledCheck, ...]] = (
    ("estate union covers all engine systems", check_union_covers_all_systems),
    ("declared system names exist", check_declared_names_exist),
    ("bundle evidence holds", check_bundle_evidence),
)
_ADVISORY_CHECKS: Final[tuple[LabelledCheck, ...]] = ()
# Gating like check:surface (owner ruling 2026-07-19 precedent), not advisory:
# an undeclared hole in the gate's own estate is the U9 failure mode.


def _summary(advisory_count: int) -> str:
    del advisory_count  # unused: no advisory tier for this sentinel
    return "Gate coverage: estate declaration complete and well-named."


def main(argv: list[str] | None = None) -> int:
    """CLI entry for the family dispatcher."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="CI mode (no-op alias)")
    parser.parse_args(argv)
    return run_sensor(_TAG, _GATING_CHECKS, _ADVISORY_CHECKS, _summary)


if __name__ == "__main__":
    sys.exit(main())
