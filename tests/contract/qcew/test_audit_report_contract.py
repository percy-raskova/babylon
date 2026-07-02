"""Spec-086 T028: emitted audit JSON validates against the contract schema (US3).

RED phase until T031/T032 land ``babylon_data.qcew.audit`` + CLI emission.
Runs the real CLI in ``--dry-run`` against a fixture DB and validates the
emitted ``qcew_impute_*.json`` with Draft 2020-12 jsonschema; the Markdown
sidecar must exist beside it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from tests.fixtures.qcew import (
    constraint_70_row,
    constraint_71_row,
    leaf_row,
    us_total_row,
    write_mini_singlefile,
)
from tests.fixtures.qcew.orm import create_qcew_engine, seed_qcew_dims

qcew_main = pytest.importorskip(
    "babylon_data.qcew.__main__", reason="babylon-data symlink not resolved (CI)"
)
jsonschema = pytest.importorskip("jsonschema", reason="jsonschema not installed")

pytestmark = [pytest.mark.contract, pytest.mark.ledger]

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[3]
    / "specs"
    / "086-qcew-loader-imputation"
    / "contracts"
    / "audit_report.schema.json"
)

ROWS = [
    constraint_70_row("26163", estabs=12, employment=1000, wages=50_000_000),
    constraint_71_row("26163", "5", estabs=12, employment=1000, wages=50_000_000),
    leaf_row("26163", "5", "336111", estabs=8, employment=700, wages=35_000_000),
    leaf_row("26163", "5", "336112", estabs=4, suppressed=True),
    us_total_row(estabs=12, employment=1000, wages=50_000_000),
]


@pytest.fixture()
def env(tmp_path: Path) -> dict[str, Path]:
    db_path = tmp_path / "ref.sqlite"
    engine = create_qcew_engine(f"sqlite:///{db_path}")
    with Session(engine) as session:
        seed_qcew_dims(session)
        session.commit()
    engine.dispose()
    source = tmp_path / "src"
    source.mkdir()
    write_mini_singlefile(source, 2010, ROWS)
    reports = tmp_path / "reports"
    return {"db": db_path, "source": source, "reports": reports}


def _emitted(reports_dir: Path, suffix: str) -> list[Path]:
    return sorted(reports_dir.glob(f"qcew_impute_*.{suffix}"))


class TestContract:
    def test_dry_run_emits_schema_valid_json_and_md(self, env: dict[str, Path]) -> None:
        code = qcew_main.main(
            [
                "--dry-run",
                "--years",
                "2010",
                "--db",
                str(env["db"]),
                "--source-dir",
                str(env["source"]),
                "--report-dir",
                str(env["reports"]),
            ]
        )
        assert code == 0
        json_files = _emitted(env["reports"], "json")
        md_files = _emitted(env["reports"], "md")
        assert len(json_files) == 1, "exactly one JSON audit artifact per run"
        assert len(md_files) == 1, "Markdown sidecar required"

        document = json.loads(json_files[0].read_text(encoding="utf-8"))
        schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
        jsonschema.validate(document, schema)  # Draft 2020-12 via $schema

        assert document["run_metadata"]["mode"] == "dry-run"
        assert document["per_year"][0]["year"] == 2010
        assert document["per_year"][0]["suppression"]["suppressed_cells"] == 1

    def test_apply_emits_report_with_table_hashes(self, env: dict[str, Path]) -> None:
        code = qcew_main.main(
            [
                "--apply",
                "--years",
                "2010",
                "--db",
                str(env["db"]),
                "--source-dir",
                str(env["source"]),
                "--report-dir",
                str(env["reports"]),
            ]
        )
        assert code == 0
        (json_file,) = _emitted(env["reports"], "json")
        document = json.loads(json_file.read_text(encoding="utf-8"))
        jsonschema.validate(document, json.loads(_SCHEMA_PATH.read_text(encoding="utf-8")))
        hashes = document["run_metadata"]["table_hashes"]
        assert set(hashes) == {"fact_qcew_annual", "fact_qcew_county_rollup"}
        assert all(len(value) == 64 for value in hashes.values())
        assert document["sc_gates"]["sc006_provenance_marker_total"] is True
