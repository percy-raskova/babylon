"""Spec-086 T023: CLI surface per contracts/cli_contract.md (US2).

RED phase until T025 implements ``babylon_data.qcew.__main__``.

Exit codes: 0 success · 1 validation failure (swap refused, canonical
untouched) · 2 pre-flight/usage failure. Modes are mutually exclusive and
exactly one is required. ``--years`` accepts ``A-B`` and comma lists.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from tests.fixtures.qcew import (
    SINGLEFILE_HEADER,
    constraint_70_row,
    constraint_71_row,
    leaf_row,
    write_mini_singlefile,
)
from tests.fixtures.qcew.orm import create_qcew_engine, seed_qcew_dims

qcew_main = pytest.importorskip(
    "babylon_data.qcew.__main__",
    reason="babylon-data symlink not resolved (CI)",
)

pytestmark = [pytest.mark.unit, pytest.mark.ledger]

KNOWN_ROWS = [
    constraint_70_row("26163", estabs=6, employment=1000, wages=50_000_000),
    constraint_71_row("26163", "5", estabs=6, employment=1000, wages=50_000_000),
    leaf_row("26163", "5", "336111", estabs=4, employment=750, wages=37_500_000),
    leaf_row("26163", "5", "336112", estabs=2, suppressed=True),
]

#: Published total wildly above the only (disclosed) leaf with nothing
#: suppressed to absorb it → reconciliation gate must fail.
IRRECONCILABLE_ROWS = [
    constraint_70_row("26163", estabs=6, employment=1000, wages=50_000_000),
    constraint_71_row("26163", "5", estabs=6, employment=1000, wages=50_000_000),
    leaf_row("26163", "5", "336111", estabs=4, employment=500, wages=25_000_000),
]


@pytest.fixture()
def ref_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "ref.sqlite"
    engine = create_qcew_engine(f"sqlite:///{db_path}")
    with Session(engine) as session:
        seed_qcew_dims(session)
        session.commit()
    engine.dispose()
    return db_path


@pytest.fixture()
def source_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "src"
    directory.mkdir()
    write_mini_singlefile(directory, 2010, KNOWN_ROWS)
    return directory


def _run(*argv: str) -> int:
    return int(qcew_main.main(list(argv)))


class TestArgumentContract:
    def test_mode_is_required(self, ref_db: Path, source_dir: Path) -> None:
        with pytest.raises(SystemExit) as excinfo:
            _run("--years", "2010", "--db", str(ref_db), "--source-dir", str(source_dir))
        assert excinfo.value.code == 2

    def test_modes_mutually_exclusive(self, ref_db: Path, source_dir: Path) -> None:
        with pytest.raises(SystemExit) as excinfo:
            _run(
                "--dry-run",
                "--apply",
                "--years",
                "2010",
                "--db",
                str(ref_db),
                "--source-dir",
                str(source_dir),
            )
        assert excinfo.value.code == 2

    def test_years_range_and_list_forms(self) -> None:
        assert qcew_main.parse_years("2010-2013") == [2010, 2011, 2012, 2013]
        assert qcew_main.parse_years("2010,2015") == [2010, 2015]
        assert qcew_main.parse_years("2024") == [2024]

    def test_years_garbage_rejected(self) -> None:
        with pytest.raises(ValueError, match="years"):
            qcew_main.parse_years("twenty-ten")


class TestPreflight:
    def test_missing_singlefile_exits_2(self, ref_db: Path, source_dir: Path) -> None:
        code = _run(
            "--dry-run",
            "--years",
            "2010,2015",  # 2015 file absent from source_dir
            "--db",
            str(ref_db),
            "--source-dir",
            str(source_dir),
        )
        assert code == 2

    def test_header_drift_exits_2(self, ref_db: Path, tmp_path: Path) -> None:
        directory = tmp_path / "bad"
        directory.mkdir()
        (directory / "2010.annual.singlefile.csv").write_text(
            SINGLEFILE_HEADER.replace("area_fips", "area_flps") + "\n", encoding="utf-8"
        )
        code = _run(
            "--dry-run", "--years", "2010", "--db", str(ref_db), "--source-dir", str(directory)
        )
        assert code == 2


class TestModes:
    def test_dry_run_writes_nothing(self, ref_db: Path, source_dir: Path) -> None:
        code = _run(
            "--dry-run", "--years", "2010", "--db", str(ref_db), "--source-dir", str(source_dir)
        )
        assert code == 0
        engine = create_qcew_engine(f"sqlite:///{ref_db}")
        with Session(engine) as session:
            count = session.execute(text("SELECT COUNT(*) FROM fact_qcew_annual")).scalar_one()
        assert count == 0

    def test_apply_populates_canonical_and_keeps_backup(
        self, ref_db: Path, source_dir: Path
    ) -> None:
        code = _run(
            "--apply", "--years", "2010", "--db", str(ref_db), "--source-dir", str(source_dir)
        )
        assert code == 0
        engine = create_qcew_engine(f"sqlite:///{ref_db}")
        with Session(engine) as session:
            total = session.execute(
                text("SELECT SUM(employment) FROM fact_qcew_annual")
            ).scalar_one()
            tables = {
                row[0]
                for row in session.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table'")
                )
            }
        assert total == 1000  # 750 disclosed + 250 imputed
        assert "fact_qcew_annual__pre_086" in tables

    def test_validation_failure_exits_1_and_leaves_canonical_untouched(
        self, ref_db: Path, tmp_path: Path
    ) -> None:
        directory = tmp_path / "bad-data"
        directory.mkdir()
        write_mini_singlefile(directory, 2010, IRRECONCILABLE_ROWS)
        code = _run(
            "--apply", "--years", "2010", "--db", str(ref_db), "--source-dir", str(directory)
        )
        assert code == 1
        engine = create_qcew_engine(f"sqlite:///{ref_db}")
        with Session(engine) as session:
            count = session.execute(text("SELECT COUNT(*) FROM fact_qcew_annual")).scalar_one()
        assert count == 0  # swap refused

    def test_restart_flag_accepted_with_apply(self, ref_db: Path, source_dir: Path) -> None:
        code = _run(
            "--apply",
            "--restart",
            "--years",
            "2010",
            "--db",
            str(ref_db),
            "--source-dir",
            str(source_dir),
        )
        assert code == 0
