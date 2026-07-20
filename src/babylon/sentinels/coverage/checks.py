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

**Amendment U lattice rungs** (#39 T8,
:data:`~babylon.sentinels.coverage.registry.LATTICE_RUNG_REQUIREMENTS`) are a
narrow exception to "never asserted": the county→CZ rung's backing concordance
is a small, COMMITTED, in-repo CSV (never the reference DB), so
:func:`check_lattice_rung_concordance` parses it directly and floors its
key/value coverage — a rung whose concordance goes missing or truncated must
fail LOUD naming the rung (the CZ-silent-fallback class: T7's web CZ framing
used to fall back to county silently). The two reference-DB-backed rungs
(hex→county, county→MSA) stay static-existence-only here, exactly like
:data:`DATA_REQUIREMENTS`; their tables' EMPTINESS is already governed nightly
by ``data-catalog.yaml``'s KEEP law (:mod:`babylon.sentinels.coverage.db_probe`).

Run via the family runner; exit 0 = clean, 1 = incoherent requirement, 2 =
infrastructure failure (source file missing/unparseable — itself a loud failure).
"""

from __future__ import annotations

import argparse
import ast
import csv
import sys
from pathlib import Path

from babylon.sentinels._ast import referenced_names, returned_dict_keys
from babylon.sentinels.base import LabelledCheck, SentinelCheckError, run_sensor
from babylon.sentinels.coverage.catalog import (
    CatalogTable,
    load_catalog_tables,
    subset_policy_map,
)
from babylon.sentinels.coverage.registry import (
    DATA_REQUIREMENTS,
    GATE_ESTATES,
    LATTICE_RUNG_REQUIREMENTS,
    DataRequirement,
    GateEstate,
    LatticeRungRequirement,
)
from babylon.sentinels.report import finding

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


def module_level_names(path: Path) -> set[str]:
    """Statically collect module-level class/function/constant names in ``path``.

    Mirrors :func:`module_class_names` but broader — a ``"derivation"``-kind
    :class:`~babylon.sentinels.coverage.registry.LatticeRungRequirement` row
    names a plain function (``_state_parent_map``) or a module-level constant
    (``_NATION_ID``) as its concordance, not a class, so this helper collects
    ``ClassDef``/``FunctionDef``/``AsyncFunctionDef`` names plus the targets of
    module-level ``Assign``/``AnnAssign`` statements.

    :param path: Source file to parse.
    :returns: The set of top-level class/function/constant names.
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

    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            names.update(target.id for target in node.targets if isinstance(target, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


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


#: One sentence explaining WHY a lattice-rung concordance going dark matters —
#: shared by every finding :func:`check_lattice_rung_concordance` emits.
_WHY_LATTICE_RUNG_DARK = (
    "a lattice rung whose concordance silently degrades stops resolving real "
    "aggregation keys and a consumer (e.g. T7's CZ web framing) falls back to "
    "the next rung down without anyone noticing -- the CZ-silent-fallback "
    "class this row family exists to prevent (Constitution III.11)."
)


def _committed_csv_violations(req: LatticeRungRequirement, path: Path) -> list[str]:
    """Coverage violations for one ``"committed_csv"`` lattice-rung row.

    Deliberately mirrors :func:`check_artifact_manifest`'s own "a missing
    committed DATA artifact is a coverage VIOLATION, not an infrastructure
    SentinelCheckError" posture — unlike a vanished *source module*
    (:func:`check_source_classes_exist`'s contract), a vanished or truncated
    committed CSV is exactly the drift this row exists to catch, so it must
    reach the gate's ordinary violation-string path, never exit 2.

    :param req: The ``committed_csv``-kind row to check.
    :param path: Resolved absolute path to ``req.source_file``.
    :returns: Violation strings (empty when the file exists, parses, declares
        both columns, and each covers at least its declared floor).
    """
    if not path.is_file():
        return [
            f"lattice rung {req.rung!r} concordance {req.concordance_name!r} is "
            f"MISSING ({req.source_file} does not exist) -- {_WHY_LATTICE_RUNG_DARK}"
        ]

    try:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            fieldnames = reader.fieldnames or ()
            if req.key_column not in fieldnames or req.value_column not in fieldnames:
                return [
                    f"lattice rung {req.rung!r} concordance {req.concordance_name!r} is "
                    f"MALFORMED: header {list(fieldnames)} is missing declared column(s) "
                    f"{req.key_column!r}/{req.value_column!r} -- {_WHY_LATTICE_RUNG_DARK}"
                ]
            keys: set[str] = set()
            values: set[str] = set()
            for row in reader:
                keys.add(row[req.key_column])
                values.add(row[req.value_column])
    except (OSError, csv.Error) as exc:
        raise SentinelCheckError(f"cannot read {path}: {exc}") from exc

    violations: list[str] = []
    if len(keys) < req.min_keys:
        violations.append(
            f"lattice rung {req.rung!r} concordance {req.concordance_name!r} covers only "
            f"{len(keys)} distinct {req.key_column!r} keys, below the declared floor of "
            f"{req.min_keys} -- {_WHY_LATTICE_RUNG_DARK}"
        )
    if len(values) < req.min_values:
        violations.append(
            f"lattice rung {req.rung!r} concordance {req.concordance_name!r} covers only "
            f"{len(values)} distinct {req.value_column!r} values, below the declared floor "
            f"of {req.min_values} -- {_WHY_LATTICE_RUNG_DARK}"
        )
    return violations


def check_lattice_rung_concordance(
    registry: tuple[LatticeRungRequirement, ...] = LATTICE_RUNG_REQUIREMENTS,
) -> list[str]:
    """Every Amendment U lattice rung's declared concordance is coherent and alive.

    Dispatches per :attr:`~babylon.sentinels.coverage.registry.LatticeRungRequirement.kind`:

    - ``"reference_table"``: the named SQLAlchemy model class must still exist
      at its declared module path (mirrors :func:`check_source_classes_exist`
      exactly; a missing/unparseable *source module* is an infrastructure
      failure, :class:`SentinelCheckError`).
    - ``"derivation"``: the named function/constant must still exist at
      module level (:func:`module_level_names`; same infra-failure contract).
    - ``"committed_csv"``: the artifact must exist, parse, declare both
      columns, and cover at least its declared key/value floors — see
      :func:`_committed_csv_violations` (a missing/truncated DATA artifact is
      a coverage VIOLATION here, never an infrastructure failure — mirrors
      :func:`check_artifact_manifest`).

    :param registry: The requirements to check (defaults to the real
        :data:`~babylon.sentinels.coverage.registry.LATTICE_RUNG_REQUIREMENTS`;
        injectable so tests can supply a deliberately broken row).
    :returns: Sorted violation strings (empty when every rung is coherent).
    :raises SentinelCheckError: If a ``reference_table``/``derivation`` row's
        source module is missing or unparseable (an infrastructure failure,
        distinct from a coverage miss).
    """
    violations: list[str] = []
    for req in registry:
        path = _REPO_ROOT / req.source_file
        if req.kind == "reference_table":
            if req.source_symbol not in module_class_names(path):
                violations.append(
                    f"lattice rung {req.rung!r} names source class {req.source_symbol!r} "
                    f"but {req.source_file} defines no such module-level class "
                    f"(renamed/moved/deleted? {_WHY_LATTICE_RUNG_DARK})"
                )
        elif req.kind == "derivation":
            if req.source_symbol not in module_level_names(path):
                violations.append(
                    f"lattice rung {req.rung!r} names derivation symbol "
                    f"{req.source_symbol!r} but {req.source_file} defines no such "
                    f"module-level name (renamed/moved/deleted? {_WHY_LATTICE_RUNG_DARK})"
                )
        else:
            violations.extend(_committed_csv_violations(req, path))
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


#: Top-level keys the manifest may declare (v1: just `version`/`artifacts`;
#: v2 adds the optional `schema`/`product` blocks). Anything else is a typo
#: (e.g. `schemas:`) that would silently disarm whichever block it was meant
#: to populate — loud, not ignored (III.11).
_MANIFEST_TOP_LEVEL_KEYS = frozenset({"version", "schema", "product", "artifacts"})


def _check_schema_block(
    schema: dict[str, object], target: Path, manifest_path: Path | None
) -> list[str]:
    """Validate an optional v2 ``schema`` block (Task 4's extractor output).

    ``file`` follows the identical in-repo/dist-tier rule as artifact
    entries: an in-repo path must exist and sha256-match; a ``dist/`` path is
    skipped when absent locally (CI verifies it at fetch time).
    ``tables``/``views``/``indexes`` are shape-checked as non-negative ints
    only — no cross-check against the real schema.
    """
    import hashlib

    violations: list[str] = []
    required = ("file", "sha256", "tables", "views", "indexes")
    missing = [key for key in required if key not in schema]
    if missing:
        violations.append(f"manifest schema block missing key(s): {missing}")
        return violations

    home = str(schema["file"])
    if not home.startswith("dist/"):
        path = (target.parent / home) if manifest_path is not None else (_REPO_ROOT / home)
        if not path.is_file():
            violations.append(f"schema.file missing: {home} (manifest promises it in-repo)")
        else:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != schema["sha256"]:
                violations.append(
                    f"schema.file drifted: sha256 {digest[:12]}... != manifest "
                    f"{str(schema['sha256'])[:12]}... ({home})"
                )

    for key in ("tables", "views", "indexes"):
        value = schema[key]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            violations.append(f"schema.{key} must be a non-negative int, got {value!r}")

    return violations


def _check_product_block(product: dict[str, object]) -> list[str]:
    """Validate an optional v2 ``product`` block (Task 5's builder output).

    SHAPE validation only (plan deviation D2): the static fast gate never
    verifies ``sha256`` against an actual on-disk database — the
    rebuild-vs-rebuild pin is verified by the builder and by CI at
    build/fetch time, never by this sensor (doing so here would require the
    multi-hundred-MB reference DB locally, which the fast gate must not
    require).
    """
    violations: list[str] = []
    required = ("name", "sha256", "page_size", "application_id", "user_version", "sqlite_version")
    missing = [key for key in required if key not in product]
    if missing:
        violations.append(f"manifest product block missing key(s): {missing}")
        return violations

    name = product["name"]
    if not isinstance(name, str) or not name.strip():
        violations.append(f"product.name must be a non-empty string, got {name!r}")

    sha256_value = product["sha256"]
    is_valid_sha = (
        isinstance(sha256_value, str)
        and len(sha256_value) == 64
        and sha256_value == sha256_value.lower()
        and all(c in "0123456789abcdef" for c in sha256_value)
    )
    if not is_valid_sha:
        violations.append(f"product.sha256 must be 64 lowercase hex chars, got {sha256_value!r}")

    for key in ("page_size", "user_version"):
        value = product[key]
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            violations.append(f"product.{key} must be a positive int, got {value!r}")

    application_id = product["application_id"]
    if isinstance(application_id, bool) or not isinstance(application_id, int):
        violations.append(f"product.application_id must be an int, got {application_id!r}")

    sqlite_version = product["sqlite_version"]
    if not isinstance(sqlite_version, str) or not sqlite_version.strip():
        violations.append(
            f"product.sqlite_version must be a non-empty string, got {sqlite_version!r}"
        )

    return violations


def check_artifact_manifest(
    manifest_path: Path | None = None,
) -> list[str]:
    """Every in-repo artifact in ``data-artifacts.yaml`` exists and hash-matches.

    Supports both manifest versions (parquet pipeline Task 3): v1
    (``version: "1.0.0"``, flat ``artifacts:`` only) and v2 (optional
    ``schema``/``product`` blocks alongside ``artifacts:``). The
    artifact-entry checks below are identical for both — this function never
    branches on the declared ``version`` string itself, only on which
    optional top-level blocks are present.

    The manifest is the successor registry for demoted reference tables
    (ADR076): once a table's DB copy is dropped, the hash-pinned artifact IS
    the data. An in-repo entry whose file is missing or whose sha256 drifted
    is silent data corruption — exactly what the demotion handoff forbids.
    Release-tier entries (``dist/``) are pin-verified at fetch time in CI,
    not here (the fast gate must not require the assets locally); the v2
    ``schema.file`` follows the identical rule (see
    :func:`_check_schema_block`). The v2 ``product`` block is validated for
    shape only, never its hash (see :func:`_check_product_block` for why —
    plan deviation D2).

    Any unknown top-level key (e.g. ``schemas:`` typoed for ``schema:``) is a
    loud violation (Constitution III.11) rather than a silently-ignored typo
    that would disarm whichever block it was meant to populate.

    :param manifest_path: Manifest to check (defaults to the real
        ``data-artifacts.yaml``; injectable for efficacy tests). A missing
        manifest is fine — the program may not have landed on this branch.
    :returns: Sorted violation strings.
    :raises SentinelCheckError: If the manifest exists but cannot be parsed.
    """
    import hashlib

    import yaml

    target = _REPO_ROOT / "data-artifacts.yaml" if manifest_path is None else manifest_path
    if not target.is_file():
        return []
    try:
        manifest = yaml.safe_load(target.read_text())
        entries = manifest["artifacts"]
    except (yaml.YAMLError, KeyError, TypeError) as error:
        msg = f"data-artifacts.yaml is unreadable/malformed: {error}"
        raise SentinelCheckError(msg) from error

    violations: list[str] = []

    unknown_keys = set(manifest) - _MANIFEST_TOP_LEVEL_KEYS
    if unknown_keys:
        violations.append(
            f"data-artifacts.yaml has unknown top-level key(s): {sorted(unknown_keys)} "
            f"(allowed: {sorted(_MANIFEST_TOP_LEVEL_KEYS)}) — typo?"
        )

    for entry in entries:
        home = str(entry["home"])
        if home.startswith("dist/"):
            continue
        artifact = (target.parent / home) if manifest_path is not None else (_REPO_ROOT / home)
        if not artifact.is_file():
            violations.append(
                f"artifact {entry['name']!r} missing: {home} (manifest promises it in-repo)"
            )
            continue
        digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
        if digest != entry["sha256"]:
            violations.append(
                f"artifact {entry['name']!r} drifted: sha256 {digest[:12]}... != "
                f"manifest {str(entry['sha256'])[:12]}... ({home})"
            )

    schema = manifest.get("schema")
    if schema is not None:
        violations.extend(_check_schema_block(schema, target, manifest_path))

    product = manifest.get("product")
    if product is not None:
        violations.extend(_check_product_block(product))

    return sorted(violations)


def check_gate_estate_coverage(
    estates: tuple[GateEstate, ...] = GATE_ESTATES,
) -> list[str]:
    """Every gate must inject every service key of the estate it claims to guard.

    Reads the factory's returned dict keys statically (the estate) and the
    harness's mentioned names (what it injects), and reports any key the harness
    never mentions. A gate that runs green while executing none of its estate is
    **gate-blind** — the state ``qa:regression`` was in for the whole economics
    estate.

    :param estates: Claims to check (defaults to the real :data:`GATE_ESTATES`;
        injectable so the efficacy test can supply a deliberately blind gate).
    :returns: Sorted agent-legible finding strings (empty when no gate is blind).
    :raises SentinelCheckError: If a harness or factory file is missing,
        unparseable, or the named factory returns no dict literal.
    """
    findings: list[str] = []
    for estate in estates:
        keys = returned_dict_keys(_REPO_ROOT / estate.factory_file, estate.factory_symbol)
        injected = referenced_names(_REPO_ROOT / estate.harness_file)
        # A harness that calls the factory itself injects the WHOLE estate;
        # requiring it to spell every key would force the harness to
        # duplicate the factory's own key list (DRY).
        if estate.factory_symbol in injected:
            continue
        missing = sorted(
            key for key in keys if key not in injected and key not in estate.exempt_keys
        )
        if not missing:
            continue
        findings.append(
            finding(
                error_class="gate-blindness",
                symbol=f"{estate.gate_name} / {estate.estate_name}",
                file=estate.harness_file,
                line=0,
                problem=(
                    f"claims to guard {estate.factory_symbol}'s estate but never "
                    f"injects {len(missing)} of its {len(keys)} service keys "
                    f"({', '.join(missing)}) — the gate can be green with that code "
                    "never executed"
                ),
                remedy=(
                    "build calculator_overrides in the harness from a committed "
                    "deterministic fixture so the estate actually runs, or narrow the "
                    "claim by declaring exempt_keys WITH an exempt_reason on the "
                    "GateEstate row"
                ),
            )
        )
    return sorted(findings)


#: Gating checks: a violation reds the dev fast-gate (exit 1).
_GATING_CHECKS: tuple[LabelledCheck, ...] = (
    ("declared reference-data source class does not exist", check_source_classes_exist),
    ("catalog consumer/test path does not exist", check_catalog_paths_exist),
    ("catalog subset_policy drifted from make_reference_subset.TABLE", check_subset_policy_parity),
    ("data-artifacts manifest entry missing or hash-drifted", check_artifact_manifest),
    ("lattice-rung concordance orphaned, missing, or truncated", check_lattice_rung_concordance),
)

#: Advisory tier: gate-blindness reports loudly but never gates, per the
#: standing owner ruling that sentinels are advisory and local/on-demand.
_ADVISORY_CHECKS: tuple[LabelledCheck, ...] = (
    ("DoD gate does not execute the estate it claims to guard", check_gate_estate_coverage),
)


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
        f"subset policies in parity); {len(LATTICE_RUNG_REQUIREMENTS)} Amendment U "
        "lattice rungs coherent (concordances exist, alive, and covering their "
        "declared floors)."
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
