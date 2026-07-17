"""Integration tests for the local archival lifecycle (spec-088 S2b).

Replaces the spec-037 Phase-8 stub-assertion tests (T044/T046/T047/T048
asserted ``NotImplementedError``): spec-088 implements the pipeline
local-only per the 2026-07-03 owner ruling (Parquet + zstd on disk,
DuckDB reads, no cloud code paths — ``upload_to_r2`` stays retired).

Full roundtrip under test: synthetic session rows → export → manifest →
purge (partition drop + leftovers) → DuckDB readback.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import pytest

from babylon.engine.headless_runner.runner import _apply_migrations
from babylon.persistence.archival import (
    ArchiveVerificationError,
    export_session_to_parquet,
    purge_session,
    query_archived_session,
    upload_to_r2,
)
from babylon.persistence.partitioning import ensure_session_partitions, partition_name

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def migrated_pool(pg_pool: Any) -> Any:
    _apply_migrations(pg_pool)
    return pg_pool


def _seed_session(pool: Any, session_id: uuid.UUID, *, ticks: int = 3) -> None:
    """Insert a small but multi-table synthetic session."""
    ensure_session_partitions(pool=pool, session_id=session_id)
    sid = str(session_id)
    with pool.connection() as conn:
        conn.execute(
            """
            INSERT INTO hex_spatial_map
                (session_id, h3_index, county_fips, state_fips, region_id)
            VALUES (%s, '872a91055ffffff', '26163', '26', 'midwest')
            ON CONFLICT (session_id, h3_index) DO NOTHING
            """,
            (sid,),
        )
        for tick in range(ticks):
            conn.execute(
                """
                INSERT INTO dynamic_hex_state (
                    session_id, tick, h3_index, county_fips, state_fips, region_id,
                    c, v, s, k, biocapacity_stock, energy_stock, raw_material_stock,
                    internet_access_pct, surveillance_coupling
                ) VALUES (%s, %s, '872a91055ffffff', NULL, NULL, NULL,
                          1, 2, 3, 4, 1, 1, 1, 0.5, 0.5)
                """,
                (sid, tick),
            )
            conn.execute(
                """
                INSERT INTO dynamic_demographics_state
                    (session_id, tick, county_fips, population)
                VALUES (%s, %s, '26163', 1000)
                """,
                (sid, tick),
            )


def _live_count(pool: Any, table: str, session_id: uuid.UUID) -> int:
    with pool.connection() as conn:
        row = conn.execute(
            f"SELECT count(*) FROM {table} WHERE session_id = %s",  # noqa: S608
            (str(session_id),),
        ).fetchone()
    assert row is not None
    return int(row[0])


class TestExport:
    def test_export_writes_parquet_and_manifest(self, migrated_pool: Any, tmp_path: Path) -> None:
        session = uuid.uuid4()
        _seed_session(migrated_pool, session)
        try:
            paths = export_session_to_parquet(migrated_pool, session, tmp_path)
            names = {Path(p).name for p in paths}
            assert "dynamic_hex_state.parquet" in names
            assert "dynamic_demographics_state.parquet" in names
            assert "archive_manifest.json" in names

            manifest = json.loads((tmp_path / "archive_manifest.json").read_text())
            assert manifest["session_id"] == str(session)
            assert manifest["tables"]["dynamic_hex_state"]["rows"] == 3
            assert len(manifest["tables"]["dynamic_hex_state"]["sha256"]) == 64
            # Empty families are recorded with zero rows and no file.
            assert manifest["tables"]["boundary_flow_register"]["rows"] == 0
        finally:
            purge_session(
                migrated_pool,
                session,
                manifest_path=tmp_path / "archive_manifest.json",
            )


class TestPurge:
    def test_purge_requires_verified_manifest(self, migrated_pool: Any, tmp_path: Path) -> None:
        session = uuid.uuid4()
        _seed_session(migrated_pool, session)
        export_session_to_parquet(migrated_pool, session, tmp_path)
        manifest_path = tmp_path / "archive_manifest.json"

        # Tamper: manifest claiming fewer rows than live must refuse purge.
        doctored = json.loads(manifest_path.read_text())
        doctored["tables"]["dynamic_hex_state"]["rows"] = 1
        bad_path = tmp_path / "doctored_manifest.json"
        bad_path.write_text(json.dumps(doctored))
        with pytest.raises(ArchiveVerificationError):
            purge_session(migrated_pool, session, manifest_path=bad_path)
        assert _live_count(migrated_pool, "dynamic_hex_state", session) == 3

        # Genuine manifest purges cleanly.
        purge_session(migrated_pool, session, manifest_path=manifest_path)
        assert _live_count(migrated_pool, "dynamic_hex_state", session) == 0
        assert _live_count(migrated_pool, "dynamic_demographics_state", session) == 0

    def test_purge_drops_partitions_and_spares_other_sessions(
        self, migrated_pool: Any, tmp_path: Path
    ) -> None:
        keep, drop = uuid.uuid4(), uuid.uuid4()
        _seed_session(migrated_pool, keep)
        _seed_session(migrated_pool, drop)
        try:
            export_session_to_parquet(migrated_pool, drop, tmp_path)
            purge_session(migrated_pool, drop, manifest_path=tmp_path / "archive_manifest.json")
            with migrated_pool.connection() as conn:
                part = conn.execute(
                    "SELECT to_regclass(%s)",
                    (partition_name("dynamic_hex_state", drop),),
                ).fetchone()
            assert part is not None and part[0] is None, "partition should be gone"
            assert _live_count(migrated_pool, "dynamic_hex_state", keep) == 3
        finally:
            keep_dir = tmp_path / "keep"
            export_session_to_parquet(migrated_pool, keep, keep_dir)
            purge_session(migrated_pool, keep, manifest_path=keep_dir / "archive_manifest.json")


class TestArchivedQuery:
    def test_duckdb_readback_matches_manifest(self, migrated_pool: Any, tmp_path: Path) -> None:
        session = uuid.uuid4()
        _seed_session(migrated_pool, session)
        try:
            export_session_to_parquet(migrated_pool, session, tmp_path)
            rows = query_archived_session(
                tmp_path,
                "SELECT count(*) AS n, sum(v) AS v_total FROM dynamic_hex_state",
            )
            assert rows == [{"n": 3, "v_total": 6.0}]
        finally:
            purge_session(
                migrated_pool,
                session,
                manifest_path=tmp_path / "archive_manifest.json",
            )


class TestR2Retired:
    def test_upload_to_r2_stays_retired_local_only(self) -> None:
        """Owner ruling 2026-07-03: archives are local only, period."""
        with pytest.raises(NotImplementedError, match="local-only"):
            upload_to_r2(["x.parquet"], bucket="babylon-archives")
