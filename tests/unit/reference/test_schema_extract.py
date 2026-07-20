"""Task 4: canonical ``schema.sql`` extractor — golden-form, census, and CLI
contracts (parquet pipeline plan 2026-07-19).

The idempotent fixed-point test (extract -> executescript -> extract again ==
identical text) is the generic form of "verify against the Fundamental
Theorem views specifically": at cutover the SAME assertion runs against the
real reference DB, which covers all 8 real views by construction rather than
a hardcoded name list.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[3]
TOOLS_DIR = _REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import extract_reference_schema  # type: ignore[import-not-found]  # noqa: E402
from extract_reference_schema import (  # type: ignore[import-not-found]  # noqa: E402
    extract_schema_sql,
    schema_census,
)
from make_data_artifacts import (  # type: ignore[import-not-found]  # noqa: E402
    _sha256,
    _write_manifest,
)

from babylon.sentinels.coverage.checks import check_artifact_manifest  # noqa: E402


def _mini_db(tmp_path: Path, name: str = "m.sqlite") -> sqlite3.Connection:
    """Table + index + view fixture — the mini schema the brief specifies."""
    conn = sqlite3.connect(tmp_path / name)
    conn.executescript(
        "CREATE TABLE fact_a (id INTEGER PRIMARY KEY, v REAL);\n"
        "CREATE INDEX idx_fact_a_v ON fact_a (v);\n"
        "CREATE VIEW view_a AS SELECT id FROM fact_a;\n"
    )
    return conn


class TestExtractSchemaSql:
    def test_preserves_master_order_and_terminators(self, tmp_path: Path) -> None:
        conn = _mini_db(tmp_path)
        try:
            text = extract_schema_sql(conn)
        finally:
            conn.close()
        # Isolate the statement body from the header first: the header's
        # comment lines contain no ";" at all, so splitting the whole text on
        # ";\n" leaves the header glued to statement 1 in a single chunk —
        # which the naive "drop comment lines" filter would then discard
        # wholesale (losing CREATE TABLE, not just the header).
        assert text.startswith(extract_reference_schema.HEADER)
        body = text[len(extract_reference_schema.HEADER) :]
        stmts = [s for s in body.split(";\n") if s.strip()]
        assert "CREATE TABLE fact_a" in stmts[0]
        assert "CREATE INDEX idx_fact_a_v" in stmts[1]
        assert "CREATE VIEW view_a" in stmts[2]
        assert text.endswith(";\n")

    def test_idempotent_fixed_point_through_rebuild(self, tmp_path: Path) -> None:
        conn = _mini_db(tmp_path, "m.sqlite")
        try:
            text = extract_schema_sql(conn)
        finally:
            conn.close()
        conn2 = sqlite3.connect(tmp_path / "n.sqlite")
        try:
            conn2.executescript(text)
            assert extract_schema_sql(conn2) == text  # fixed point: DDL survives a round trip
        finally:
            conn2.close()

    def test_every_view_is_present(self, tmp_path: Path) -> None:
        conn = _mini_db(tmp_path)
        try:
            views = [
                row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='view'")
            ]
            text = extract_schema_sql(conn)
        finally:
            conn.close()
        assert views and all(f"CREATE VIEW {v}" in text for v in views)

    def test_excludes_sqlite_internal_objects_and_auto_indexes(self, tmp_path: Path) -> None:
        conn = sqlite3.connect(tmp_path / "auto.sqlite")
        try:
            conn.execute(
                "CREATE TABLE fact_b (id INTEGER PRIMARY KEY AUTOINCREMENT, u TEXT UNIQUE)"
            )
            conn.execute("INSERT INTO fact_b (u) VALUES ('x')")  # materializes sqlite_sequence
            conn.commit()
            text = extract_schema_sql(conn)
        finally:
            conn.close()
        assert "sqlite_sequence" not in text
        assert "sqlite_autoindex" not in text
        assert "CREATE TABLE fact_b" in text


class TestSchemaCensus:
    def test_census_correctness_on_fixture(self, tmp_path: Path) -> None:
        conn = _mini_db(tmp_path)
        try:
            counts = schema_census(conn)
        finally:
            conn.close()
        assert counts == {"tables": 1, "views": 1, "indexes": 1}

    def test_census_excludes_auto_indexes(self, tmp_path: Path) -> None:
        conn = sqlite3.connect(tmp_path / "auto2.sqlite")
        try:
            conn.execute("CREATE TABLE fact_c (id INTEGER PRIMARY KEY, u TEXT UNIQUE)")
            counts = schema_census(conn)
        finally:
            conn.close()
        assert counts == {"tables": 1, "views": 0, "indexes": 0}  # UNIQUE's auto-index excluded


class TestCliEndToEnd:
    def test_cli_writes_schema_and_updates_manifest(self, tmp_path: Path) -> None:
        db = tmp_path / "src.sqlite"
        conn = sqlite3.connect(db)
        conn.executescript(
            "CREATE TABLE fact_a (id INTEGER PRIMARY KEY, v REAL);\n"
            "CREATE INDEX idx_fact_a_v ON fact_a (v);\n"
            "CREATE VIEW view_a AS SELECT id FROM fact_a;\n"
        )
        conn.commit()
        conn.close()

        # dist-tier home: the coverage sentinel skips existence/hash checks
        # for it locally (verified at CI fetch time instead) — isolates the
        # assertion below to the schema block the extractor actually wrote.
        existing_entries = [
            {
                "name": "x",
                "format": "parquet",
                "source_table": "x",
                "generator": "tools/make_data_artifacts.py",  # _write_manifest always emits this
                "mode": "generate",
                "rows": 1,
                "sha256": "a" * 64,
                "home": "dist/data-artifacts/x.parquet",
                "material_relation": "r1",
            }
        ]
        product_block: dict[str, object] = {
            "name": "marxist-data-3NF.sqlite",
            "sha256": "b" * 64,
            "page_size": 4096,
            "application_id": 1112359244,
            "user_version": 1,
            "sqlite_version": "3.46.1",
        }
        manifest = tmp_path / "data-artifacts.yaml"
        _write_manifest(existing_entries, product_entry=product_block, path=manifest)

        out_sql = tmp_path / "schema.sql"
        rc = extract_reference_schema.main(
            [
                "--db",
                str(db),
                "--out",
                str(out_sql),
                "--manifest",
                str(manifest),
            ]
        )
        assert rc == 0
        assert out_sql.is_file()

        parsed = yaml.safe_load(manifest.read_text())
        assert parsed["schema"] == {
            "file": str(out_sql),
            "sha256": _sha256(out_sql),
            "tables": 1,
            "views": 1,
            "indexes": 1,
        }
        assert parsed["artifacts"] == existing_entries  # byte-preserved
        assert parsed["product"] == product_block  # pre-existing product block preserved

        # sentinel validates the schema block's shape+hash (an absolute
        # schema.file: pathlib's `/` operator discards the manifest-relative
        # base when the right-hand operand is already absolute, per stdlib
        # contract — so this resolves straight to out_sql and hash-matches).
        assert check_artifact_manifest(manifest) == []

    def test_cli_missing_db_is_loud(self, tmp_path: Path) -> None:
        manifest = tmp_path / "data-artifacts.yaml"
        _write_manifest([], path=manifest)
        with pytest.raises(extract_reference_schema.ArtifactError, match="database not found"):
            extract_reference_schema.main(
                [
                    "--db",
                    str(tmp_path / "nope.sqlite"),
                    "--out",
                    str(tmp_path / "schema.sql"),
                    "--manifest",
                    str(manifest),
                ]
            )

    def test_cli_missing_manifest_is_loud(self, tmp_path: Path) -> None:
        db = tmp_path / "src.sqlite"
        sqlite3.connect(db).close()
        with pytest.raises(extract_reference_schema.ArtifactError, match="manifest missing"):
            extract_reference_schema.main(
                [
                    "--db",
                    str(db),
                    "--out",
                    str(tmp_path / "schema.sql"),
                    "--manifest",
                    str(tmp_path / "nope.yaml"),
                ]
            )
