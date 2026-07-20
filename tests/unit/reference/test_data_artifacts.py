"""Preservation contracts for the ADR076 data artifacts (rulings R1-R5).

Once a table's DB copy is dropped (the catalog->manifest demotion handoff),
these tests are what pins its content: row counts + known rows read from the
ARTIFACT, never the DB. The in-repo CSV tier always runs; the dist-tier
parquet contracts skip where the files are absent (they ship as ci-data
release assets, generated locally by ``tools/make_data_artifacts.py``).

The synthetic double-generation test proves the generator's byte-stability
property on every run, everywhere — the real-DB proof (two full runs,
identical manifest) was recorded 2026-07-17.
"""

from __future__ import annotations

import csv
import hashlib
import sqlite3
import sys
from pathlib import Path

import pytest
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CSV_HOME = _REPO_ROOT / "src" / "babylon" / "data" / "reference"
_DIST_HOME = _REPO_ROOT / "dist" / "data-artifacts"
_MANIFEST = _REPO_ROOT / "data-artifacts.yaml"

TOOLS_DIR = _REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS_DIR))

from make_data_artifacts import (  # type: ignore[import-not-found]  # noqa: E402
    ArtifactError,
    _arrow_type,
    _sha256,
    _table_layout,
    _write_csv,
    export_table_parquet,
    generate,
)


def _read_csv(name: str) -> list[dict[str, str]]:
    with (_CSV_HOME / name).open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class TestManifest:
    def test_manifest_hashes_match_in_repo_artifacts(self) -> None:
        manifest = yaml.safe_load(_MANIFEST.read_text())
        checked = 0
        for entry in manifest["artifacts"]:
            path = _REPO_ROOT / entry["home"]
            if not str(entry["home"]).startswith("src/"):
                continue
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            assert digest == entry["sha256"], f"{entry['name']} drifted from its manifest hash"
            checked += 1
        assert checked == 3  # the two R1 CSVs + the registered ricci CSV

    def test_manifest_carries_all_eight_artifacts(self) -> None:
        manifest = yaml.safe_load(_MANIFEST.read_text())
        names = {entry["name"] for entry in manifest["artifacts"]}
        assert names == {
            "bridge_county_bea_ea",
            "dim_bea_economic_area",
            "babylon_ricci_final",
            "fact_energy_annual",
            "dim_energy_series",
            "dim_energy_table",
            "bridge_lodes_block",
            "staging_arcgis_feature",
        }


class TestR1BeaCsvPreservation:
    def test_bridge_county_bea_ea(self) -> None:
        rows = _read_csv("bridge_county_bea_ea.csv")
        assert len(rows) == 83
        assert rows[0] == {"county_id": "1232", "bea_ea_id": "8"}

    def test_dim_bea_economic_area(self) -> None:
        rows = _read_csv("dim_bea_economic_area.csv")
        assert len(rows) == 8
        assert rows[0]["ea_code"] == "CHI"
        assert rows[0]["ea_name"] == "Chicago-Naperville (cross-border)"
        assert {r["ea_code"] for r in rows} == {
            "CHI",
            "DET",
            "GRR",
            "KAL",
            "LAN",
            "MQT",
            "SAG",
            "TVC",
        }

    def test_cross_border_ea_semantics_survive_the_demotion(self) -> None:
        # Migrated from tests/integration/test_michigan_reference_data.py's
        # TestBEAEconomicAreas when the DB copies dropped (ADR076 R1). The
        # county_id surrogates are pinned with their identities: 1242 =
        # Berrien MI (26021), 1313 = Wayne MI (26163), 1283 = Marquette MI
        # (26103) — resolved against dim_county on 2026-07-17.
        bridge = {
            row["county_id"]: row["bea_ea_id"] for row in _read_csv("bridge_county_bea_ea.csv")
        }
        code_by_ea = {
            row["bea_ea_id"]: row["ea_code"] for row in _read_csv("dim_bea_economic_area.csv")
        }
        assert code_by_ea[bridge["1242"]] == "CHI"  # Berrien belongs to cross-border Chicago
        assert code_by_ea[bridge["1313"]] == "DET"  # Wayne is the Detroit EA node
        assert code_by_ea[bridge["1283"]] == "MQT"  # Marquette anchors the Upper Peninsula EA


class TestR2RicciRegistration:
    def test_canonical_csv_is_untouched_and_registered(self) -> None:
        # register-mode must never rewrite the pre-existing canonical CSV —
        # its content contract lives in test_unequal_exchange_artifacts.py.
        rows = _read_csv("babylon_ricci_final.csv")
        assert len(rows) == 51
        assert rows[0]["region_name"] == "North America"


@pytest.mark.skipif(
    not (_DIST_HOME / "bridge_lodes_block.parquet").is_file(),
    reason="dist-tier parquet artifacts absent (generate locally or fetch ci-data assets)",
)
class TestParquetPreservation:
    def test_bridge_lodes_block_spike(self) -> None:
        import pyarrow.parquet as pq

        table = pq.read_table(_DIST_HOME / "bridge_lodes_block.parquet")
        assert table.num_rows == 1_150_562
        assert table.column_names[0] == "block_geoid"
        first = table.slice(0, 1).to_pylist()[0]
        assert first["block_geoid"] == "011010001001000"
        assert first["state_fips"] == "01"
        assert first["cbsa_code"] == "33860"

    def test_energy_family(self) -> None:
        import pyarrow.parquet as pq

        fact = pq.read_table(_DIST_HOME / "fact_energy_annual.parquet")
        assert fact.num_rows == 525
        first = fact.slice(0, 1).to_pylist()[0]
        assert first["series_id"] == 1
        assert first["time_id"] == 1
        assert first["value"] == pytest.approx(69869.338)
        assert pq.read_table(_DIST_HOME / "dim_energy_series.parquet").num_rows == 20
        assert pq.read_table(_DIST_HOME / "dim_energy_table.parquet").num_rows == 14

    def test_staging_arcgis_feature(self) -> None:
        import pyarrow.parquet as pq

        table = pq.read_table(_DIST_HOME / "staging_arcgis_feature.parquet")
        assert table.num_rows == 5_974


class TestGeneratorDeterminism:
    """The ADR076 byte-stability property, proven on synthetic input."""

    @pytest.fixture()
    def source_db(self, tmp_path: Path) -> Path:
        db = tmp_path / "source.sqlite"
        conn = sqlite3.connect(db)
        conn.executescript(
            """
            CREATE TABLE fact_sample (
                id INTEGER NOT NULL,
                label VARCHAR(20),
                value NUMERIC(10, 2),
                PRIMARY KEY (id)
            );
            INSERT INTO fact_sample VALUES (2, 'b', 2.5), (1, 'a', 1.25), (3, NULL, NULL);
            """
        )
        conn.commit()
        conn.close()
        return db

    def test_double_generation_is_byte_identical(self, source_db: Path, tmp_path: Path) -> None:
        # The parquet leg exercises the production writer, export_table_parquet
        # (the generate() path's only parquet-writing call) — not a second,
        # production-unused writer that the fast gate wouldn't otherwise guard.
        conn = sqlite3.connect(f"file:{source_db}?mode=ro", uri=True)
        try:
            columns, _pk, _schema = _table_layout(conn, "fact_sample")
            rows = conn.execute("SELECT id, label, value FROM fact_sample ORDER BY id").fetchall()
            hashes: dict[str, set[str]] = {"csv": set(), "parquet": set()}
            for run in (1, 2):
                csv_out = tmp_path / f"run{run}.csv"
                pq_out = tmp_path / f"run{run}.parquet"
                _write_csv(csv_out, columns, rows)
                export_table_parquet(conn, "fact_sample", pq_out)
                hashes["csv"].add(_sha256(csv_out))
                hashes["parquet"].add(_sha256(pq_out))
        finally:
            conn.close()
        assert len(hashes["csv"]) == 1
        assert len(hashes["parquet"]) == 1

    def test_unmapped_decltype_is_loud(self) -> None:
        with pytest.raises(ArtifactError, match="BLOB"):
            _arrow_type("BLOB")

    def test_missing_source_table_is_loud(self, source_db: Path) -> None:
        conn = sqlite3.connect(source_db)
        try:
            with pytest.raises(ArtifactError, match="fact_missing"):
                _table_layout(conn, "fact_missing")
        finally:
            conn.close()

    def test_generate_requires_every_spec_table(self, source_db: Path) -> None:
        # The real ARTIFACTS specs must hard-fail against a DB lacking them —
        # the loud-policy discipline inherited from make_reference_subset.
        with pytest.raises(ArtifactError):
            generate(source_db)
