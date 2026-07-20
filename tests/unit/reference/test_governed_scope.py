"""Governed-estate boundary — one source of truth across the parquet pipeline.

Error class (discovered at cutover Step 2, 2026-07-20): three modules defined
the governed sweep surface divergently — the catalog sentinel scoped to
``fact_/dim_/bridge_/view_`` prefixes while the exporter, roundtrip verifier
and schema extractor swept every non-``sqlite_%`` object — so the first
full-coverage export against the real DB demanded a catalog row for
``ingest_checkpoint``, utility bookkeeping the governance model deliberately
leaves uncatalogued (see ``db_probe`` scope note and the subset generator's
``find_unknown_tables``). These tests pin the boundary to ONE shared constant
(``babylon.sentinels.coverage.catalog.GOVERNED_PREFIXES``) and the
utility-table exclusion at every sweep surface.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
TOOLS_DIR = _REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import make_data_artifacts  # type: ignore[import-not-found]  # noqa: E402
from extract_reference_schema import (  # type: ignore[import-not-found]  # noqa: E402
    extract_schema_sql,
    schema_census,
)
from make_data_artifacts import (  # type: ignore[import-not-found]  # noqa: E402
    governed_db_tables,
)
from make_reference_subset import (  # type: ignore[import-not-found]  # noqa: E402
    find_unknown_tables,
)
from verify_reference_roundtrip import (  # type: ignore[import-not-found]  # noqa: E402
    compare_databases,
)

from babylon.sentinels.coverage import db_probe  # noqa: E402
from babylon.sentinels.coverage.catalog import GOVERNED_PREFIXES  # noqa: E402


def _estate_db(path: Path, with_utility: bool = True) -> sqlite3.Connection:
    """Governed mini-estate plus (optionally) a utility bookkeeping table.

    Mirrors the real failure: ``ingest_checkpoint`` exists in the live DB
    with rows and an index, but is outside the governed estate.
    """
    conn = sqlite3.connect(path)
    conn.executescript(
        "CREATE TABLE fact_a (id INTEGER PRIMARY KEY, v REAL);\n"
        "CREATE INDEX idx_fact_a_v ON fact_a (v);\n"
        "CREATE TABLE dim_b (id INTEGER PRIMARY KEY, label TEXT);\n"
        "CREATE VIEW view_a AS SELECT id FROM fact_a;\n"
    )
    conn.execute("INSERT INTO fact_a VALUES (1, 2.0)")
    conn.execute("INSERT INTO dim_b VALUES (1, 'x')")
    if with_utility:
        conn.executescript(
            "CREATE TABLE ingest_checkpoint ("
            "checkpoint_id INTEGER PRIMARY KEY, source_code TEXT NOT NULL);\n"
            "CREATE INDEX idx_ingest_checkpoint_src "
            "ON ingest_checkpoint (source_code);\n"
        )
        conn.execute("INSERT INTO ingest_checkpoint VALUES (1, 'census')")
    conn.commit()
    return conn


class TestGovernedTableSweep:
    def test_governed_db_tables_excludes_utility_tables(self, tmp_path: Path) -> None:
        conn = _estate_db(tmp_path / "e.sqlite")
        assert governed_db_tables(conn) == ["dim_b", "fact_a"]

    def test_full_coverage_enumeration_skips_utility_tables(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The exact production failure of 2026-07-20: before the boundary fix
        # this raised KeyError("ingest_checkpoint: DB table has no
        # data-catalog.yaml row") despite the catalog being complete.
        conn = _estate_db(tmp_path / "e.sqlite")
        rows = {
            name: SimpleNamespace(material_relation=f"test relation for {name}")
            for name in ("fact_a", "dim_b")
        }
        monkeypatch.setattr(make_data_artifacts, "_catalog_by_name", lambda: rows)
        specs = make_data_artifacts.enumerate_full_coverage_specs(conn)
        assert {s.name for s in specs} == {"fact_a", "dim_b"}


class TestSchemaExtractionScope:
    def test_extract_schema_sql_excludes_utility_ddl(self, tmp_path: Path) -> None:
        conn = _estate_db(tmp_path / "e.sqlite")
        text = extract_schema_sql(conn)
        assert "CREATE TABLE fact_a" in text
        assert "idx_fact_a_v" in text
        assert "CREATE VIEW view_a" in text
        assert "ingest_checkpoint" not in text  # neither the table nor its index

    def test_schema_census_counts_governed_objects_only(self, tmp_path: Path) -> None:
        conn = _estate_db(tmp_path / "e.sqlite")
        assert schema_census(conn) == {"tables": 2, "views": 1, "indexes": 1}


class TestRoundtripScope:
    def test_roundtrip_ok_when_only_live_has_utility_table(self, tmp_path: Path) -> None:
        # Live carries the bookkeeping table; the rebuilt product (governed
        # estate only) must still verify clean — and the report must not
        # mention the utility table at all.
        live = tmp_path / "live.sqlite"
        rebuilt = tmp_path / "rebuilt.sqlite"
        _estate_db(live, with_utility=True).close()
        _estate_db(rebuilt, with_utility=False).close()
        report = compare_databases(live, rebuilt)
        assert report.ok
        assert "ingest_checkpoint" not in report.tables


class TestSingleSourceOfTruth:
    def test_prefix_constant_value_is_pinned(self) -> None:
        assert GOVERNED_PREFIXES == ("fact_", "dim_", "bridge_", "view_")

    def test_db_probe_uses_the_shared_constant(self) -> None:
        assert db_probe._GOVERNED_PREFIXES is GOVERNED_PREFIXES

    def test_subset_policy_review_matches_table_prefixes(self) -> None:
        # find_unknown_tables reviews exactly the table-side governed
        # prefixes: each governed table prefix is flagged when unclassified,
        # utility names never are.
        unknown = [f"{p}zzz" for p in GOVERNED_PREFIXES if p != "view_"]
        names = [*unknown, "ingest_checkpoint", "staging_arcgis_feature"]
        assert find_unknown_tables(names, {}) == sorted(unknown)
