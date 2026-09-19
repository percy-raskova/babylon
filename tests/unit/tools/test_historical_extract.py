"""Pinned coverage and leakage boundaries for historical observations."""

import copy
import json
from pathlib import Path

import pytest
from tools.devtools.historical_extract import (
    DEFAULT_FIXTURES,
    load_fixtures,
    starting_specs,
    validate_rows,
)


def test_committed_fixture_identity_schema_partitions_and_starting_specs() -> None:
    manifest, jobs, freight = load_fixtures(DEFAULT_FIXTURES)
    assert len(jobs) == 220
    assert len(freight) == 82
    assert len({(r["year"], r["month"]) for r in freight}) == 72
    specs = starting_specs(jobs, freight, manifest["initialization_snapshot_sha256"])
    for kind, spec in specs.items():
        assert spec == json.loads((DEFAULT_FIXTURES / f"{kind}_experiment.json").read_text())
    assert specs["freight"]["starting_snapshot"]["arrived_kg"] == 121292613
    assert specs["employment"]["starting_snapshot"]["series"] == [
        {"series_id": "26099/332", "jobs": 8143},
        {"series_id": "26125/311", "jobs": 2911},
        {"series_id": "26161/311", "jobs": 615},
        {"series_id": "26163/331", "jobs": 4464},
        {"series_id": "26163/3363", "jobs": 17378},
    ]


def test_heldout_values_never_enter_engine_inputs() -> None:
    manifest, jobs, freight = load_fixtures(DEFAULT_FIXTURES)
    before = starting_specs(jobs, freight, manifest["initialization_snapshot_sha256"])
    for row in jobs:
        if row["year"] >= 2015:
            row["employment_begin"] = 987654321
    for row in freight:
        if row["year"] >= 2020:
            row["shipwt_kg"] = 123456789
    assert starting_specs(jobs, freight, manifest["initialization_snapshot_sha256"]) == before


@pytest.mark.parametrize(
    "column,value",
    [
        ("port_code", "3802"),
        ("hs2_code", "73"),
        ("mode_code", 8),
        ("trade_type", 1),
        ("country", "2010"),
    ],
)
def test_unrelated_trade_boundaries_cannot_enter_freight(column: str, value: object) -> None:
    _, jobs, freight = load_fixtures(DEFAULT_FIXTURES)
    freight[0][column] = value
    with pytest.raises(ValueError, match="boundary"):
        validate_rows(jobs, freight)


def test_duplicates_wrong_ownership_and_missing_coverage_fail() -> None:
    _, jobs, freight = load_fixtures(DEFAULT_FIXTURES)
    duplicate = copy.deepcopy(jobs)
    duplicate[-1] = duplicate[0]
    with pytest.raises(ValueError, match="coverage or duplicate"):
        validate_rows(duplicate, freight)
    jobs[0]["own_code"] = "0"
    with pytest.raises(ValueError, match="private"):
        validate_rows(jobs, freight)
    _, jobs, freight = load_fixtures(DEFAULT_FIXTURES)
    with pytest.raises(ValueError, match="82 unique"):
        validate_rows(jobs, freight[:-1])


def test_corrupt_parquet_fails_before_scoring(tmp_path: Path) -> None:
    for source in DEFAULT_FIXTURES.iterdir():
        (tmp_path / source.name).write_bytes(source.read_bytes())
    with (tmp_path / "employment.parquet").open("ab") as stream:
        stream.write(b"corrupt")
    with pytest.raises(ValueError, match="checksum"):
        load_fixtures(tmp_path)


def test_regenerated_target_checksums_never_change_initial_spec_bytes(tmp_path: Path) -> None:
    """Re-extraction changes evaluator identity but not any engine input byte."""
    import pyarrow.parquet as pq
    from tools.devtools.historical_extract import (
        _table,
        canonical_bytes,
        digest_file,
        initialization_snapshot_digest,
        snapshot_digest,
    )

    original_manifest, jobs, freight = load_fixtures(DEFAULT_FIXTURES)
    before = starting_specs(jobs, freight, initialization_snapshot_digest(jobs, freight))
    for row in jobs:
        if row["year"] >= 2015:
            row["employment_begin"] *= 2
    for row in freight:
        if row["year"] >= 2020:
            row["shipwt_kg"] *= 2
    for source in DEFAULT_FIXTURES.iterdir():
        (tmp_path / source.name).write_bytes(source.read_bytes())
    changed_manifest = copy.deepcopy(original_manifest)
    changed_manifest["sqlite_source_sha256"] = "f" * 64
    for kind, rows in [("employment", jobs), ("freight", freight)]:
        path = tmp_path / f"{kind}.parquet"
        pq.write_table(
            _table(rows),
            path,
            compression="zstd",
            version="2.6",
            use_dictionary=False,
            write_statistics=True,
            data_page_version="2.0",
        )
        changed_manifest["datasets"][kind]["sha256"] = digest_file(path)
    changed_manifest["snapshot_sha256"] = snapshot_digest(changed_manifest)
    assert changed_manifest["snapshot_sha256"] != original_manifest["snapshot_sha256"]
    assert changed_manifest["initialization_snapshot_sha256"] == initialization_snapshot_digest(
        jobs, freight
    )
    (tmp_path / "manifest.json").write_bytes(canonical_bytes(changed_manifest))
    loaded, loaded_jobs, loaded_freight = load_fixtures(tmp_path)
    after = starting_specs(loaded_jobs, loaded_freight, loaded["initialization_snapshot_sha256"])
    assert canonical_bytes(before) == canonical_bytes(after)


def test_database_lineage_hashes_exact_bytes_and_refuses_wal(tmp_path: Path) -> None:
    import hashlib

    from tools.devtools.historical_extract import _database_fingerprint

    database = tmp_path / "reference.sqlite"
    database.write_bytes(b"fixed database bytes")
    assert _database_fingerprint(database, database.stat()) == {
        "sqlite_source_sha256": hashlib.sha256(b"fixed database bytes").hexdigest(),
        "sqlite_source_bytes": 20,
    }
    database.with_name(database.name + "-wal").write_bytes(b"")
    assert _database_fingerprint(database, database.stat())["sqlite_source_bytes"] == 20
    database.with_name(database.name + "-wal").write_bytes(b"uncheckpointed pages")
    with pytest.raises(ValueError, match="WAL"):
        _database_fingerprint(database, database.stat())


def test_database_mutation_during_fingerprint_refuses_extraction(
    tmp_path: Path, monkeypatch
) -> None:
    import tools.devtools.historical_extract as module

    database = tmp_path / "reference.sqlite"
    database.write_bytes(b"old data")
    original = module.digest_file

    def mutate(path: Path) -> str:
        result = original(path)
        path.write_bytes(b"replaced data")
        return result

    monkeypatch.setattr(module, "digest_file", mutate)
    with pytest.raises(ValueError, match="changed during extraction"):
        module._database_fingerprint(database, database.stat())
