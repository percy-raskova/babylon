"""Tests for the data-coverage coherence sentinel.

Two tiers, per the sentinel contract:

- **Invariant** — :func:`check_source_classes_exist` passes on the *real*
  :data:`DATA_REQUIREMENTS`: every declared reference-data adapter class is
  still defined at its declared module path.
- **Efficacy** — the sensor REDS on an injected defect: a requirement naming a
  class the file does not define, and an infrastructure failure (missing source
  file) raised loudly rather than swallowed.

This sentinel is **purely static** — it reads source files with :mod:`ast` and
never runs the engine, so it does not consume the ``shared_tick`` dynamic
fixture. The reference-DB *coverage probe* (do the rows exist) is a nightly
concern and is deliberately not exercised here.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from babylon.sentinels.base import SentinelCheckError
from babylon.sentinels.coverage.checks import (
    _REPO_ROOT,
    check_artifact_manifest,
    check_lattice_rung_concordance,
    check_source_classes_exist,
    module_class_names,
    module_level_names,
)
from babylon.sentinels.coverage.registry import (
    DATA_REQUIREMENTS,
    LATTICE_RUNG_REQUIREMENTS,
    DataRequirement,
    LatticeRungRequirement,
)

pytestmark = pytest.mark.unit


def test_registry_is_non_empty() -> None:
    """The registry declares at least the four known reference-data requirements."""
    names = {req.name for req in DATA_REQUIREMENTS}
    assert {
        "qcew_county_naics",
        "qcew_national_employment",
        "lodes_commuter_flow",
        "bea_import_use",
    } <= names


def test_real_requirements_are_coherent() -> None:
    """INVARIANT: every declared source class exists at its declared module path."""
    assert check_source_classes_exist() == []


def test_module_class_names_finds_a_known_class() -> None:
    """The AST helper resolves a real module-level adapter class."""
    path = _REPO_ROOT / "src/babylon/domain/economics/throughput/adapters.py"
    assert "SQLiteQCEWCountyNAICSSource" in module_class_names(path)


def test_efficacy_reds_on_nonexistent_source_class() -> None:
    """EFFICACY: a requirement naming a class the file lacks reds the gate.

    The source file exists and parses, but declares no such class — this is the
    exact orphaned-dependency drift the sentinel guards against.
    """
    broken = DataRequirement(
        name="phantom_dependency",
        source_class="SQLiteThisClassDoesNotExist",
        source_file="src/babylon/domain/economics/throughput/adapters.py",
        tables=("fact_qcew_annual",),
        material_relation="synthetic defect for the efficacy proof",
    )
    violations = check_source_classes_exist((broken,))
    assert len(violations) == 1
    assert "phantom_dependency" in violations[0]
    assert "SQLiteThisClassDoesNotExist" in violations[0]


def test_efficacy_missing_source_file_is_loud() -> None:
    """EFFICACY: a missing source file raises SentinelCheckError (exit-2, not a pass).

    Infrastructure failure must be loud (III.11), never swallowed into an empty
    (falsely-clean) violation list.
    """
    broken = DataRequirement(
        name="gone_module",
        source_class="Whatever",
        source_file="src/babylon/domain/economics/does_not_exist.py",
        tables=("t",),
        material_relation="synthetic missing-file defect",
    )
    with pytest.raises(SentinelCheckError):
        check_source_classes_exist((broken,))


def test_registry_rejects_blank_source_class() -> None:
    """A malformed row (blank source_class) fails loudly at construction (III.11)."""
    with pytest.raises(ValueError, match="source_class"):
        DataRequirement(
            name="bad",
            source_class="  ",
            source_file="src/babylon/x.py",
            tables=(),
            material_relation="r",
        )


def test_registry_rejects_non_py_source_file() -> None:
    """A source_file that is not a .py path fails loudly at construction."""
    with pytest.raises(ValueError, match="source_file"):
        DataRequirement(
            name="bad",
            source_class="X",
            source_file="src/babylon/x.sqlite",
            tables=(),
            material_relation="r",
        )


class TestArtifactManifestSentinel:
    """``check_artifact_manifest`` — supports both manifest versions (parquet
    pipeline Task 3): v1 (flat ``artifacts:`` only) and v2 (optional
    ``schema``/``product`` blocks alongside it).
    """

    def test_real_committed_manifest_is_clean(self) -> None:
        """INVARIANT: the actual committed v1 data-artifacts.yaml passes,
        untouched by this task (the manifest itself is not regenerated)."""
        assert check_artifact_manifest() == []

    def test_v2_fixture_with_absent_dist_schema_file_passes(self, tmp_path: Path) -> None:
        manifest_path = tmp_path / "data-artifacts.yaml"
        manifest_path.write_text(
            yaml.safe_dump(
                {
                    "version": "2.0.0",
                    "schema": {
                        "file": "dist/data-artifacts/schema.sql",
                        "sha256": "a" * 64,
                        "tables": 76,
                        "views": 8,
                        "indexes": 100,
                    },
                    "artifacts": [],
                }
            )
        )
        assert check_artifact_manifest(manifest_path) == []

    def test_v2_fixture_with_valid_schema_and_product_passes(self, tmp_path: Path) -> None:
        schema_file = tmp_path / "schema.sql"
        schema_file.write_text("CREATE TABLE t (id INTEGER);\n")
        import hashlib

        digest = hashlib.sha256(schema_file.read_bytes()).hexdigest()
        manifest_path = tmp_path / "data-artifacts.yaml"
        manifest_path.write_text(
            yaml.safe_dump(
                {
                    "version": "2.0.0",
                    "schema": {
                        "file": "schema.sql",
                        "sha256": digest,
                        "tables": 1,
                        "views": 0,
                        "indexes": 0,
                    },
                    "product": {
                        "name": "marxist-data-3NF.sqlite",
                        "sha256": "b" * 64,
                        "page_size": 4096,
                        "application_id": 1112359244,
                        "user_version": 1,
                        "sqlite_version": "3.46.1",
                    },
                    "artifacts": [],
                }
            )
        )
        assert check_artifact_manifest(manifest_path) == []

    def test_v2_in_repo_schema_file_hash_mismatch_fails(self, tmp_path: Path) -> None:
        schema_file = tmp_path / "schema.sql"
        schema_file.write_text("CREATE TABLE t (id INTEGER);\n")
        manifest_path = tmp_path / "data-artifacts.yaml"
        manifest_path.write_text(
            yaml.safe_dump(
                {
                    "version": "2.0.0",
                    "schema": {
                        "file": "schema.sql",
                        "sha256": "0" * 64,  # deliberately wrong
                        "tables": 1,
                        "views": 0,
                        "indexes": 0,
                    },
                    "artifacts": [],
                }
            )
        )
        violations = check_artifact_manifest(manifest_path)
        assert len(violations) == 1
        assert "schema.file drifted" in violations[0]

    def test_v2_malformed_product_bad_sha_length_fails(self, tmp_path: Path) -> None:
        manifest_path = tmp_path / "data-artifacts.yaml"
        manifest_path.write_text(
            yaml.safe_dump(
                {
                    "version": "2.0.0",
                    "product": {
                        "name": "marxist-data-3NF.sqlite",
                        "sha256": "abc123",  # too short, not 64 hex chars
                        "page_size": 4096,
                        "application_id": 1112359244,
                        "user_version": 1,
                        "sqlite_version": "3.46.1",
                    },
                    "artifacts": [],
                }
            )
        )
        violations = check_artifact_manifest(manifest_path)
        assert len(violations) == 1
        assert "product.sha256" in violations[0]

    def test_unknown_top_level_key_fails(self, tmp_path: Path) -> None:
        manifest_path = tmp_path / "data-artifacts.yaml"
        manifest_path.write_text(
            yaml.safe_dump(
                {
                    "version": "2.0.0",
                    "schemas": {},  # typo for "schema"
                    "artifacts": [],
                }
            )
        )
        violations = check_artifact_manifest(manifest_path)
        assert len(violations) == 1
        assert "schemas" in violations[0]


# ---------------------------------------------------------------------------
# Lattice-rung concordance sentinel (#39 T8) — Amendment U's 5 rungs
# (hex_to_county, county_to_cz, county_to_msa, county_to_state,
# state_to_nation), each naming a backing concordance (a reference-DB-backed
# class, a committed CSV, or a derivation function/constant). A rung whose
# concordance goes missing/empty must fail LOUD naming the rung (the
# CZ-silent-fallback class).
# ---------------------------------------------------------------------------


class TestLatticeRungConcordanceSentinel:
    def test_registry_declares_all_five_amendment_u_rungs(self) -> None:
        rungs = {req.rung for req in LATTICE_RUNG_REQUIREMENTS}
        assert rungs == {
            "hex_to_county",
            "county_to_cz",
            "county_to_msa",
            "county_to_state",
            "state_to_nation",
        }

    def test_real_lattice_rungs_are_coherent(self) -> None:
        """INVARIANT: every declared rung's real concordance is alive today
        (the two reference-DB-backed classes exist, the two derivation
        symbols exist, and the committed CZ CSV parses and covers its floor
        -- 3141+ counties, 741 CZs)."""
        assert check_lattice_rung_concordance() == []

    def test_module_level_names_finds_a_known_function_and_constant(self) -> None:
        """The AST helper resolves BOTH a module-level function and a
        module-level constant (the two ``"derivation"``-kind concordances)."""
        path = _REPO_ROOT / "src/babylon/domain/dialectics/instances/levels.py"
        names = module_level_names(path)
        assert "_state_parent_map" in names
        assert "_NATION_ID" in names

    # -- reference_table kind: mirrors check_source_classes_exist's own tests --

    def test_efficacy_reds_on_nonexistent_reference_table_class(self) -> None:
        broken = LatticeRungRequirement(
            rung="hex_to_county",
            concordance_name="bridge_county_h3",
            kind="reference_table",
            source_file="src/babylon/reference/schema.py",
            source_symbol="ThisClassDoesNotExist",
            material_relation="synthetic defect for the efficacy proof",
        )
        violations = check_lattice_rung_concordance((broken,))
        assert len(violations) == 1
        assert "hex_to_county" in violations[0]
        assert "ThisClassDoesNotExist" in violations[0]

    def test_efficacy_reference_table_missing_source_file_is_loud(self) -> None:
        broken = LatticeRungRequirement(
            rung="hex_to_county",
            concordance_name="bridge_county_h3",
            kind="reference_table",
            source_file="src/babylon/reference/does_not_exist.py",
            source_symbol="Whatever",
            material_relation="synthetic missing-file defect",
        )
        with pytest.raises(SentinelCheckError):
            check_lattice_rung_concordance((broken,))

    # -- derivation kind ---------------------------------------------------

    def test_efficacy_reds_on_nonexistent_derivation_symbol(self) -> None:
        broken = LatticeRungRequirement(
            rung="state_to_nation",
            concordance_name="constant nation id",
            kind="derivation",
            source_file="src/babylon/domain/dialectics/instances/levels.py",
            source_symbol="_THIS_CONSTANT_DOES_NOT_EXIST",
            material_relation="synthetic defect for the efficacy proof",
        )
        violations = check_lattice_rung_concordance((broken,))
        assert len(violations) == 1
        assert "state_to_nation" in violations[0]
        assert "_THIS_CONSTANT_DOES_NOT_EXIST" in violations[0]

    def test_efficacy_derivation_missing_source_file_is_loud(self) -> None:
        broken = LatticeRungRequirement(
            rung="state_to_nation",
            concordance_name="constant nation id",
            kind="derivation",
            source_file="src/babylon/domain/dialectics/instances/does_not_exist.py",
            source_symbol="Whatever",
            material_relation="synthetic missing-file defect",
        )
        with pytest.raises(SentinelCheckError):
            check_lattice_rung_concordance((broken,))

    # -- committed_csv kind: the CZ-silent-fallback mutation validation -----

    def _cz_style_row(self, source_file: str, **overrides: object) -> LatticeRungRequirement:
        defaults: dict[str, object] = {
            "rung": "county_to_cz",
            "concordance_name": "bridge_county_cz.csv",
            "kind": "committed_csv",
            "source_file": source_file,
            "material_relation": "synthetic defect for the efficacy proof",
            "key_column": "county_fips",
            "value_column": "cz_id",
            "min_keys": 3000,
            "min_values": 741,
        }
        defaults.update(overrides)
        return LatticeRungRequirement(**defaults)  # type: ignore[arg-type]

    def test_mutation_nonexistent_csv_path_fails_loud_naming_the_rung(self, tmp_path: Path) -> None:
        """MUTATION 1 (brief): point the CZ row at a nonexistent path."""
        broken = self._cz_style_row(str(tmp_path / "does_not_exist.csv"))
        violations = check_lattice_rung_concordance((broken,))
        assert len(violations) == 1
        assert "county_to_cz" in violations[0]
        assert "MISSING" in violations[0]

    def test_mutation_empty_csv_file_fails_loud_naming_the_rung(self, tmp_path: Path) -> None:
        """MUTATION 2 (brief, "empty-file variant"): a genuinely empty
        (0-byte) committed file -- no header, no rows."""
        empty = tmp_path / "bridge_county_cz.csv"
        empty.write_text("", encoding="utf-8")
        broken = self._cz_style_row(str(empty))
        violations = check_lattice_rung_concordance((broken,))
        assert len(violations) == 1
        assert "county_to_cz" in violations[0]
        assert "MALFORMED" in violations[0]

    def test_header_only_csv_below_floor_names_both_shortfalls(self, tmp_path: Path) -> None:
        """A CSV with the right header but zero data rows is coverage-empty
        -- both floors are violated, each named."""
        header_only = tmp_path / "bridge_county_cz.csv"
        header_only.write_text("county_fips,cz_id,cz_name\n", encoding="utf-8")
        broken = self._cz_style_row(str(header_only))
        violations = check_lattice_rung_concordance((broken,))
        assert len(violations) == 2
        assert any("county_fips" in v and "0" in v for v in violations)
        assert any("cz_id" in v and "0" in v for v in violations)

    def test_truncated_csv_below_floor_names_the_shortfall(self, tmp_path: Path) -> None:
        """A CSV with real rows, but far fewer than the declared floor --
        the truncated-artifact shape (not literally empty, still dark)."""
        truncated = tmp_path / "bridge_county_cz.csv"
        truncated.write_text(
            "county_fips,cz_id,cz_name\n01001,11101,Montgomery\n01003,11001,Mobile\n",
            encoding="utf-8",
        )
        broken = self._cz_style_row(str(truncated))
        violations = check_lattice_rung_concordance((broken,))
        assert len(violations) == 2
        assert any("only 2 distinct 'county_fips'" in v for v in violations)
        assert any("only 2 distinct 'cz_id'" in v for v in violations)

    def test_malformed_header_missing_declared_column_fails_loud(self, tmp_path: Path) -> None:
        malformed = tmp_path / "bridge_county_cz.csv"
        malformed.write_text("county_fips,commuting_zone\n01001,11101\n", encoding="utf-8")
        broken = self._cz_style_row(str(malformed))
        violations = check_lattice_rung_concordance((broken,))
        assert len(violations) == 1
        assert "MALFORMED" in violations[0]
        assert "cz_id" in violations[0]

    def test_well_formed_csv_meeting_floor_is_clean(self, tmp_path: Path) -> None:
        """Green->red->green round-trip sanity: a real, well-formed CSV
        meeting a LOWERED floor passes cleanly."""
        well_formed = tmp_path / "bridge_county_cz.csv"
        well_formed.write_text(
            "county_fips,cz_id,cz_name\n01001,11101,Montgomery\n01003,11001,Mobile\n",
            encoding="utf-8",
        )
        row = self._cz_style_row(str(well_formed), min_keys=2, min_values=2)
        assert check_lattice_rung_concordance((row,)) == []

    # -- registry model validation (mirrors DataRequirement's own tests) ----

    def test_registry_rejects_blank_rung(self) -> None:
        with pytest.raises(ValueError, match="rung"):
            LatticeRungRequirement(
                rung="  ",
                concordance_name="x",
                kind="derivation",
                source_file="src/babylon/x.py",
                source_symbol="x",
                material_relation="r",
            )

    def test_registry_rejects_reference_table_missing_source_symbol(self) -> None:
        with pytest.raises(ValueError, match="source_symbol"):
            LatticeRungRequirement(
                rung="hex_to_county",
                concordance_name="x",
                kind="reference_table",
                source_file="src/babylon/x.py",
                material_relation="r",
            )

    def test_registry_rejects_reference_table_non_py_source_file(self) -> None:
        with pytest.raises(ValueError, match="reference_table kind requires a .py"):
            LatticeRungRequirement(
                rung="hex_to_county",
                concordance_name="x",
                kind="reference_table",
                source_file="src/babylon/x.csv",
                source_symbol="X",
                material_relation="r",
            )

    def test_registry_rejects_committed_csv_non_csv_source_file(self) -> None:
        with pytest.raises(ValueError, match="committed_csv kind requires a .csv"):
            LatticeRungRequirement(
                rung="county_to_cz",
                concordance_name="x",
                kind="committed_csv",
                source_file="src/babylon/x.py",
                key_column="a",
                value_column="b",
                min_keys=1,
                min_values=1,
                material_relation="r",
            )

    def test_registry_rejects_committed_csv_missing_columns(self) -> None:
        with pytest.raises(ValueError, match="key_column and value_column"):
            LatticeRungRequirement(
                rung="county_to_cz",
                concordance_name="x",
                kind="committed_csv",
                source_file="src/babylon/x.csv",
                min_keys=1,
                min_values=1,
                material_relation="r",
            )

    def test_registry_rejects_committed_csv_non_positive_floors(self) -> None:
        with pytest.raises(ValueError, match="positive min_keys/min_values"):
            LatticeRungRequirement(
                rung="county_to_cz",
                concordance_name="x",
                kind="committed_csv",
                source_file="src/babylon/x.csv",
                key_column="a",
                value_column="b",
                material_relation="r",
            )
