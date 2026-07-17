"""Data-coverage coherence (static gate).

Proves, without reading the reference database or running the engine, that every
declared reference-data requirement in
:data:`babylon.sentinels.coverage.registry.DATA_REQUIREMENTS` is **coherent**:
its named adapter class still exists at its declared module path. This is
Babylon's mechanical guard against a declared dependency silently rotting — an
adapter renamed, moved, or deleted while the registry keeps citing the old name
would orphan the dependency and let the tick fall back to a
:class:`~babylon.domain.economics.tensor.NoDataSentinel` placeholder with nothing
watching (Constitution III.11 Loud Failure, VIII.12 no disarmed guardrail).

**Static by contract.** The check reads the source file with :mod:`ast` (no
import, no execution) — the source adapters pull in ``domain``/``persistence``,
which layer-0.5 :mod:`babylon.sentinels` may not import, so existence is proven
against the *file*, mirroring the seam Sensor-1 pattern.

**Out of scope (nightly).** Whether the reference DB actually holds the rows each
requirement needs is a *coverage probe*, shipped later against a Parquet subset.
This module never touches the DB and never asserts the declared table names.

Run via the family runner; exit 0 = clean, 1 = incoherent requirement, 2 =
infrastructure failure (source file missing/unparseable — itself a loud failure).
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

from babylon.sentinels.base import LabelledCheck, SentinelCheckError, run_sensor
from babylon.sentinels.coverage.catalog import (
    CatalogTable,
    load_catalog_tables,
    subset_policy_map,
)
from babylon.sentinels.coverage.registry import DATA_REQUIREMENTS, DataRequirement

#: Repo root (this file is ``<root>/src/babylon/sentinels/coverage/checks.py``).
_REPO_ROOT: Path = Path(__file__).resolve().parents[4]


def module_class_names(path: Path) -> set[str]:
    """Statically collect the module-level class names defined in ``path``.

    Reads ``path`` with :mod:`ast` (no import, no execution) and returns the
    names of every top-level ``class`` statement. Classes nested inside
    functions or other classes are intentionally excluded — a declared adapter
    must be importable at module scope.

    :param path: Source file to parse.
    :returns: The set of top-level class names.
    :raises SentinelCheckError: If the file is missing or unparseable (an
        infrastructure failure, never swallowed into a false pass).
    """
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SentinelCheckError(f"cannot read {path}: {exc}") from exc
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        raise SentinelCheckError(f"cannot parse {path}: {exc}") from exc
    return {node.name for node in tree.body if isinstance(node, ast.ClassDef)}


def check_source_classes_exist(
    registry: tuple[DataRequirement, ...] = DATA_REQUIREMENTS,
) -> list[str]:
    """Every declared requirement's source class must exist at its module path.

    For each row, resolve ``source_file`` against the repo root, parse it, and
    assert ``source_class`` is defined at module level. A row citing a class the
    file no longer defines is an incoherent requirement — the dependency it
    guards is orphaned — and reds the gate.

    :param registry: The requirements to check (defaults to the real
        :data:`DATA_REQUIREMENTS`; injectable so tests can supply a deliberately
        broken row to prove the sensor reds).
    :returns: Sorted violation strings (empty when every source class exists).
    :raises SentinelCheckError: If any declared ``source_file`` is missing or
        unparseable (an infrastructure failure, distinct from a coverage miss).
    """
    violations: list[str] = []
    for req in registry:
        path = _REPO_ROOT / req.source_file
        classes = module_class_names(path)
        if req.source_class not in classes:
            violations.append(
                f"requirement {req.name!r} names source class {req.source_class!r} "
                f"but {req.source_file} defines no such module-level class "
                f"(renamed/moved/deleted? dependency orphaned)"
            )
    return sorted(violations)


def check_catalog_paths_exist(
    catalog: tuple[CatalogTable, ...] | None = None,
) -> list[str]:
    """Every catalog row's declared consumer/test path must exist in the repo.

    A ``consumers`` or ``tests`` entry pointing at a file the repo no longer
    contains is a rotted lineage claim — the object it guards is either
    orphaned or its consumer moved without the catalog following (the exact
    drift Program 21 exists to make loud).

    :param catalog: Rows to check (defaults to the real ``data-catalog.yaml``;
        injectable so tests can supply a deliberately broken row).
    :returns: Sorted violation strings (empty when every path exists).
    :raises SentinelCheckError: If the catalog itself cannot be loaded.
    """
    rows = load_catalog_tables() if catalog is None else catalog
    violations: list[str] = []
    for row in rows:
        for field_name, paths in (("consumers", row.consumers), ("tests", row.tests)):
            for entry in paths:
                if not (_REPO_ROOT / entry).is_file():
                    violations.append(
                        f"catalog row {row.name!r} declares {field_name} path {entry!r} "
                        "which does not exist (moved/renamed/deleted? lineage rotted)"
                    )
    return sorted(violations)


def check_subset_policy_parity(
    catalog: tuple[CatalogTable, ...] | None = None,
) -> list[str]:
    """Every base table's ``subset_policy`` must equal the generator's scope.

    ``data-catalog.yaml`` and ``tools/make_reference_subset.py``'s ``TABLE``
    dict are two sources of truth for the same fact (which rows ship in the
    ci-data subset); this check pins them together so neither can drift
    silently. Views are exempt — the generator copies ``type='table'`` only,
    and the model already forces views to declare ``skip``.

    :param catalog: Rows to check (defaults to the real catalog; injectable).
    :returns: Sorted violation strings (empty when the two SoTs agree).
    :raises SentinelCheckError: If either source of truth cannot be parsed.
    """
    rows = load_catalog_tables() if catalog is None else catalog
    policies = subset_policy_map()
    violations: list[str] = []
    for row in rows:
        if row.kind != "table":
            continue
        scope = policies.get(row.name)
        if scope is None:
            violations.append(
                f"catalog row {row.name!r} has no TablePolicy entry in "
                "tools/make_reference_subset.py TABLE (new table without a "
                "reviewed subset policy?)"
            )
        elif scope != row.subset_policy:
            violations.append(
                f"catalog row {row.name!r} declares subset_policy "
                f"{row.subset_policy!r} but the generator's TABLE dict says "
                f"{scope!r} — the two SoTs have drifted"
            )
    return sorted(violations)


#: Gating checks: a violation reds the dev fast-gate (exit 1).
_GATING_CHECKS: tuple[LabelledCheck, ...] = (
    ("declared reference-data source class does not exist", check_source_classes_exist),
    ("catalog consumer/test path does not exist", check_catalog_paths_exist),
    ("catalog subset_policy drifted from make_reference_subset.TABLE", check_subset_policy_parity),
)

#: No advisory tier yet — the reference-DB coverage probe is a nightly concern.
_ADVISORY_CHECKS: tuple[LabelledCheck, ...] = ()


def _summary(advisory_count: int) -> str:
    """Build the clean one-line summary printed when no gating violation occurred.

    :param advisory_count: Number of advisory findings (0 — this sentinel has no
        advisory tier yet; the reference-DB probe is nightly).
    :returns: The summary line naming the count of coherent requirements.
    """
    summary = (
        f"Data coverage (static): clean — {len(DATA_REQUIREMENTS)} reference-data "
        f"requirements coherent (source classes exist); "
        f"{len(load_catalog_tables())} catalog rows coherent (paths exist, "
        "subset policies in parity)."
    )
    if advisory_count:
        summary += f" ({advisory_count} advisory findings above.)"
    return summary


def main(argv: list[str] | None = None) -> int:
    """Run the data-coverage coherence check and return the process exit code.

    :param argv: CLI args (``--check`` is accepted as the CI-mode alias; the
        behavior is always to gate).
    :returns: 0 clean, 1 incoherent requirement, 2 infrastructure failure.
    """
    parser = argparse.ArgumentParser(description="Data coverage — static coherence (III.11 gate).")
    parser.add_argument(
        "--check",
        action="store_true",
        help="CI-mode alias; the tool always gates (exit 1 on violations).",
    )
    parser.parse_args(argv)
    return run_sensor("COVERAGE", _GATING_CHECKS, _ADVISORY_CHECKS, _summary)


if __name__ == "__main__":
    sys.exit(main())
