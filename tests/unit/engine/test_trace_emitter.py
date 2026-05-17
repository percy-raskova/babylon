"""Unit tests for the TraceEmitter (T016, spec-064).

Validates that the emitted CSV header + per-row column ordering match
``contracts/trace_csv_schema.yaml`` and that None / NULL values render
as the empty string per FR-008.
"""

from __future__ import annotations

import csv
from pathlib import Path

import yaml

from babylon.engine.headless_runner.models import TraceRow
from babylon.engine.headless_runner.trace_emitter import TRACE_COLUMNS, TraceEmitter

CONTRACT_PATH = (
    Path(__file__).resolve().parents[3]
    / "specs"
    / "064-headless-sim-runner"
    / "contracts"
    / "trace_csv_schema.yaml"
)


class TestColumnContract:
    """The hard-coded TRACE_COLUMNS list matches the YAML contract."""

    def test_column_order_matches_yaml_contract(self) -> None:
        contract = yaml.safe_load(CONTRACT_PATH.read_text())
        contract_columns = tuple(c["name"] for c in contract["columns"])
        assert contract_columns == TRACE_COLUMNS
        assert contract["total_columns"] == len(TRACE_COLUMNS) == 22


class TestTraceEmitter:
    """Round-trip: write rows → read CSV → assert canonical ordering + NULL handling."""

    def test_header_row_uses_canonical_ordering(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "trace.csv"
        with TraceEmitter(csv_path):
            pass

        with csv_path.open() as fh:
            reader = csv.reader(fh)
            header = next(reader)
        assert tuple(header) == TRACE_COLUMNS

    def test_county_row_writes_full_payload(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "trace.csv"
        with TraceEmitter(csv_path) as emitter:
            emitter.write_row(
                TraceRow(
                    tick=0,
                    simulated_year=2010.0,
                    entity_id="26163",
                    entity_kind="county",
                    v=1.0,
                    c=2.0,
                    s=0.5,
                    k=10.0,
                    p_acquiescence=0.6,
                    p_revolution=0.4,
                    ideology_r=0.5,
                    ideology_l=0.3,
                    ideology_f=0.2,
                    surveillance_coupling=0.4,
                    internet_access_pct=0.85,
                    biocapacity_stock=100.0,
                    energy_stock=200.0,
                    raw_material_stock=300.0,
                    profit_rate=0.166,
                    exploitation_rate=0.5,
                    population=1750000,
                    employment_proxy=800000.0,
                ),
            )
            assert emitter.row_count == 1

        with csv_path.open() as fh:
            reader = csv.DictReader(fh)
            row = next(reader)
        assert row["entity_id"] == "26163"
        assert row["v"] == "1.0"
        assert row["population"] == "1750000"

    def test_none_rendered_as_empty_string(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "trace.csv"
        with TraceEmitter(csv_path) as emitter:
            emitter.write_row(
                TraceRow(
                    tick=0,
                    simulated_year=2010.0,
                    entity_id="canada",
                    entity_kind="external",
                    # all nullable fields default to None
                ),
            )

        # Read raw to confirm no None / "null" tokens leak in.
        contents = csv_path.read_text()
        first_data_line = contents.splitlines()[1]
        # entity_kind is the 4th field; everything after MUST be empty.
        cells = first_data_line.split(",")
        assert cells[0] == "0"
        assert cells[1] == "2010.0"
        assert cells[2] == "canada"
        assert cells[3] == "external"
        assert all(cell == "" for cell in cells[4:])

    def test_dict_row_input_also_accepted(self, tmp_path: Path) -> None:
        """The emitter should accept dict-shaped rows too (Postgres rows)."""
        csv_path = tmp_path / "trace.csv"
        row_dict = {
            "tick": 5,
            "simulated_year": 2010.0961538461538,
            "entity_id": "26099",
            "entity_kind": "county",
            "v": 100.0,
            "c": 200.0,
            "s": 50.0,
            "k": 1000.0,
            "p_acquiescence": None,
            "p_revolution": None,
            "ideology_r": None,
            "ideology_l": None,
            "ideology_f": None,
            "surveillance_coupling": 0.3,
            "internet_access_pct": 0.7,
            "biocapacity_stock": 50.0,
            "energy_stock": 100.0,
            "raw_material_stock": 150.0,
            "profit_rate": 0.166,
            "exploitation_rate": 0.5,
            "population": None,
            "employment_proxy": None,
        }
        with TraceEmitter(csv_path) as emitter:
            emitter.write_row(row_dict)
            assert emitter.row_count == 1

        with csv_path.open() as fh:
            reader = csv.DictReader(fh)
            row = next(reader)
        assert row["tick"] == "5"
        assert row["p_acquiescence"] == ""
        assert row["surveillance_coupling"] == "0.3"
