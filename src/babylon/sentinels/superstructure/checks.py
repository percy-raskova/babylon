"""Superstructure-direction sentinel checks (I-ORD, P25 U9, ADR135).

Static AST scanner over :data:`~babylon.sentinels.superstructure.registry.
SCAN_ROOT`: every ``set_graph_attr`` call whose register argument names a
declared political-superstructure register (a string literal, or a declared
constant alias) must live in that register's declared owner file. Three
gating rules:

**(1) Ownership.** A write to a declared register from a non-owner file is a
violation — new writers enter through the registry, never silently.

**(2) Direction (I-ORD proper).** No MATERIAL_BASE-partition file may write
ANY declared register — a base-side write would be readable by later base
systems the same tick, corrupting the base→superstructure direction the
pipeline ordering otherwise guarantees.

**(3) Registry integrity.** Owner sets and the base-file list must be
disjoint, and every declared file must exist — a row naming a moved or
deleted file is the "declaration outlived its target" drift the absence/
vocabulary families already guard against.
"""

from __future__ import annotations

import argparse
import ast
import sys
from collections.abc import Callable, Iterator
from pathlib import Path

from babylon.sentinels.base import SentinelCheckError, run_sensor
from babylon.sentinels.superstructure.registry import (
    MATERIAL_BASE_SYSTEM_FILES,
    SCAN_ROOT,
    SUPERSTRUCTURE_ATTR_OWNERS,
    SUPERSTRUCTURE_CONSTANT_ALIASES,
)

#: Repo root: three levels above this package (src/babylon/sentinels/...).
_REPO_ROOT: Path = Path(__file__).resolve().parents[3].parent


def _register_of(call: ast.Call) -> str | None:
    """The declared register a ``set_graph_attr`` call writes, if any."""
    if not call.args:
        return None
    first = call.args[0]
    if isinstance(first, ast.Constant) and isinstance(first.value, str):
        return first.value if first.value in SUPERSTRUCTURE_ATTR_OWNERS else None
    if isinstance(first, ast.Name):
        return SUPERSTRUCTURE_CONSTANT_ALIASES.get(first.id)
    return None


def find_superstructure_writes(
    root: Path | None = None,
) -> Iterator[tuple[str, int, str]]:
    """Yield ``(repo_relative_path, lineno, register)`` for every write site.

    :param root: Scan root override for tests; defaults to
        ``SCAN_ROOT`` under the repo root.
    :raises SentinelCheckError: If the scan root does not exist or a source
        file fails to parse (infrastructure failure, never a silent pass).
    """
    base = root if root is not None else _REPO_ROOT / SCAN_ROOT
    if not base.is_dir():
        raise SentinelCheckError(f"scan root not found: {base}")
    anchor = root if root is not None else _REPO_ROOT
    for path in sorted(base.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError as exc:  # pragma: no cover - repo must parse
            raise SentinelCheckError(f"unparseable source {path}: {exc}") from exc
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (isinstance(func, ast.Attribute) and func.attr == "set_graph_attr"):
                continue
            register = _register_of(node)
            if register is not None:
                yield (path.relative_to(anchor).as_posix(), node.lineno, register)


def check_ownership(root: Path | None = None) -> list[str]:
    """Rule (1): every write site sits in its register's declared owner set."""
    violations: list[str] = []
    for rel_path, lineno, register in find_superstructure_writes(root):
        owners = SUPERSTRUCTURE_ATTR_OWNERS[register]
        if rel_path not in owners:
            violations.append(
                f"{rel_path}:{lineno} writes superstructure register "
                f"'{register}' but is not a declared owner "
                f"(owners: {sorted(owners)}) | REMEDY: route the write "
                "through the owning system, or add the file to "
                "SUPERSTRUCTURE_ATTR_OWNERS in sentinels/superstructure/"
                "registry.py with the ADR that licenses it."
            )
    return violations


def check_direction(root: Path | None = None) -> list[str]:
    """Rule (2), I-ORD proper: no MATERIAL_BASE file writes any register."""
    violations: list[str] = []
    for rel_path, lineno, register in find_superstructure_writes(root):
        if rel_path in MATERIAL_BASE_SYSTEM_FILES:
            violations.append(
                f"{rel_path}:{lineno} is a MATERIAL_BASE-partition file "
                f"writing superstructure register '{register}' — the base "
                "never writes the superstructure (I-ORD; a base-side write "
                "is readable by later base systems the SAME tick) | REMEDY: "
                "move the write to a CONSEQUENCE-partition system."
            )
    return violations


def check_registry_integrity() -> list[str]:
    """Rule (3): owners ∩ base files = ∅ and every declared file exists."""
    violations: list[str] = []
    for register, owners in SUPERSTRUCTURE_ATTR_OWNERS.items():
        overlap = owners & MATERIAL_BASE_SYSTEM_FILES
        if overlap:
            violations.append(
                f"register '{register}' declares MATERIAL_BASE file(s) as "
                f"owners: {sorted(overlap)} — the direction rule forbids "
                "base-partition ownership outright."
            )
        for owner in sorted(owners):
            if not (_REPO_ROOT / owner).is_file():
                violations.append(
                    f"register '{register}' declares a nonexistent owner "
                    f"file: {owner} — the declaration outlived its target."
                )
    for base_file in sorted(MATERIAL_BASE_SYSTEM_FILES):
        if not (_REPO_ROOT / base_file).is_file():
            violations.append(
                f"MATERIAL_BASE_SYSTEM_FILES names a nonexistent file: "
                f"{base_file} — re-sync with simulation_engine's partition "
                "(the citing test pins the mapping)."
            )
    return violations


_GATING_CHECKS = (
    ("register write outside its declared owner set", check_ownership),
    ("material-base file writes the superstructure (I-ORD)", check_direction),
    ("registry row drift", check_registry_integrity),
)
_ADVISORY_CHECKS: tuple[tuple[str, Callable[[], list[str]]], ...] = ()


def _summary(_advisory_count: int) -> str:
    writes = list(find_superstructure_writes())
    return (
        f"SUPERSTRUCTURE clean: {len(SUPERSTRUCTURE_ATTR_OWNERS)} declared "
        f"register(s), {len(writes)} production write site(s) — every write "
        "sits in its declared owner, no material-base file touches the "
        "superstructure (I-ORD), no registry row is stale."
    )


def main(argv: list[str] | None = None) -> int:
    """Run the superstructure-direction gate and return the exit code."""
    parser = argparse.ArgumentParser(
        description=(
            "Superstructure-direction sentinel (I-ORD): declared write "
            "ownership over the political-superstructure graph registers."
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="CI-mode alias; the tool always gates (exit 1 on violations).",
    )
    parser.parse_args(argv)
    return run_sensor("SUPERSTRUCTURE", _GATING_CHECKS, _ADVISORY_CHECKS, _summary)


if __name__ == "__main__":
    sys.exit(main())
