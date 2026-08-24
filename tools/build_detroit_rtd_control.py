#!/usr/bin/env python3
"""Build and verify the bounded Detroit-Windsor RTD V1 control fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
import stat as stat_module
import struct
import unicodedata
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Final, NoReturn, cast

import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]
import yaml

from babylon.config.defines import GameDefines, canonical_defines_hash
from babylon.contracts.relational_territory_dossier_v1 import (
    RTD_MAX_LOCATOR_BYTES,
    parse_draft,
    seal_draft,
)
from babylon.contracts.rtd_v1_generated import RTD_V1_METRIC_REGISTRY, RtdDossierDraftV1

ROOT: Final = Path(__file__).resolve().parents[1]
FIXTURE_DIR: Final = ROOT / "contracts" / "fixtures"
EXTRACTION_PATH: Final = FIXTURE_DIR / "detroit_windsor_rtd_v1_extraction.yaml"
WORLD_PATH: Final = FIXTURE_DIR / "detroit_windsor_rtd_v1_world_identity.json"
SCENARIO_PATH: Final = FIXTURE_DIR / "detroit_windsor_rtd_v1_admin_world.bscn"
RULE_PATH: Final = FIXTURE_DIR / "detroit_windsor_rtd_v1_admin_noop.bsl"
CONTROL_PATH: Final = FIXTURE_DIR / "detroit_windsor_rtd_v1_admin_control.json"

EXPECTED_ARTIFACTS: Final = 19
EXPECTED_GAPS: Final = 20
MAX_SELECTORS: Final = 128
MAX_SELECTED_ROWS: Final = 128
MAX_LOCATORS: Final = 32
MAX_LEDGER_BYTES: Final = 1_048_576
MAX_SOURCE_BYTES: Final = 19_056_915
MAX_SOURCE_ROWS: Final = 2_645_347
MAX_ROW_GROUPS: Final = 1
SOURCE_BATCH_SIZE: Final = 65_536
MAX_SOURCE_BATCHES: Final = 41
MAX_SOURCE_FIELDS: Final = 16
EXPECTED_METRICS: Final = 18
CSV_LINES: Final = 3_142
CSV_BYTES: Final = 103_192
MAX_CSV_LINE_BYTES: Final = 256
DEFAULT_CASE_ID: Final = "detroit-windsor-admin-control"
REFERENCE_ONLY: Final = (
    "h3_res7_population",
    "h3_res7_workplace",
    "h3_res7_land_mask",
)
ARTIFACT_IDS: Final = (
    "fact_qcew_county_rollup",
    "fact_lodes_commuter_flow",
    "fact_census_housing",
    "fact_census_rent",
    "fact_census_rent_burden",
    "fact_coercive_infrastructure",
    "dim_county",
    "dim_state",
    "dim_data_source",
    "dim_time",
    "dim_ownership",
    "dim_housing_tenure",
    "dim_race",
    "dim_rent_burden",
    "dim_coercive_type",
    "bridge_county_cz",
    "h3_res7_population",
    "h3_res7_workplace",
    "h3_res7_land_mask",
)
ARTIFACT_LAYOUT: Final = (
    ("fact_qcew_county_rollup.parquet", "PHYSICAL"),
    ("fact_lodes_commuter_flow.parquet", "PHYSICAL"),
    ("fact_census_housing.parquet", "PHYSICAL"),
    ("fact_census_rent.parquet", "PHYSICAL"),
    ("fact_census_rent_burden.parquet", "PHYSICAL"),
    ("fact_coercive_infrastructure.parquet", "PHYSICAL"),
    ("dim_county.parquet", "PHYSICAL"),
    ("dim_state.parquet", "PHYSICAL"),
    ("dim_data_source.parquet", "PHYSICAL"),
    ("dim_time.parquet", "PHYSICAL"),
    ("dim_ownership.parquet", "PHYSICAL"),
    ("dim_housing_tenure.parquet", "PHYSICAL"),
    ("dim_race.parquet", "PHYSICAL"),
    ("dim_rent_burden.parquet", "PHYSICAL"),
    ("dim_coercive_type.parquet", "PHYSICAL"),
    ("src/babylon/data/reference/bridge_county_cz.csv", "TRACKED_CSV"),
    ("h3_res7_population.parquet", "REFERENCE_DIGEST_ONLY"),
    ("h3_res7_workplace.parquet", "REFERENCE_DIGEST_ONLY"),
    ("h3_res7_land_mask.parquet", "REFERENCE_DIGEST_ONLY"),
)
ARTIFACT_METRICS: Final = (
    (
        "production/qcew-county-establishments",
        "production/qcew-county-employment",
        "production/qcew-county-total-wages-usd",
    ),
    ("circulation/lodes-county-commuter-total-jobs",),
    ("reproduction/census-housing-households",),
    ("reproduction/census-median-rent-usd",),
    ("reproduction/census-rent-burden-households",),
    ("carceral/facility-count",),
    (),
    (),
    (),
    (),
    (),
    (),
    (),
    (),
    (),
    (),
    ("reproduction/h3-population-persons",),
    ("production/h3-workplace-jobs",),
    ("ecology/h3-land-fraction",),
)
SELECTOR_FIELDS: Final[tuple[tuple[tuple[str, ...], ...], ...]] = (
    (("time_id", "ownership_id", "county_ids"),),
    (("time_id", "county_ids"),),
    (
        ("source_id", "time_id", "race_id", "county_ids", "tenure_ids"),
        ("source_id", "time_id", "race_id", "expected_rows"),
    ),
    (
        ("source_id", "time_id", "race_id", "county_ids"),
        ("source_id", "time_id", "race_id", "expected_rows"),
    ),
    (
        ("source_id", "time_id", "race_id", "burden_id", "county_ids"),
        ("source_id", "time_id", "race_id", "expected_rows"),
    ),
    (("source_id", "coercive_type_ids", "county_ids"),),
    (("county_ids",),),
    (("state_id",),),
    (("source_ids",),),
    (("time_ids",),),
    (("ownership_id",),),
    (("tenure_ids",),),
    (("race_id",),),
    (("burden_id",),),
    (("coercive_type_ids",),),
    (("county_fips",),),
    (),
    (),
    (),
)
SELECTOR_COUNTS: Final[tuple[tuple[int, ...], ...]] = (
    (3,),
    (9,),
    (9, 0),
    (3, 0),
    (3, 0),
    (5,),
    (3,),
    (1,),
    (3,),
    (3,),
    (1,),
    (3,),
    (1,),
    (1,),
    (2,),
    (3,),
    (),
    (),
    (),
)
QCEW_ROW_FIELDS: Final = (
    "county_id",
    "fips",
    "establishments",
    "establishments_bits",
    "employment",
    "employment_bits",
    "total_wages_usd",
    "total_wages_bits",
    "disclosure_code",
    "is_imputed",
)
DATA_SOURCE_ROW_FIELDS: Final = (
    "source_id",
    "source_code",
    "source_year",
    "coverage_start_year",
    "coverage_end_year",
)
SELECTED_ROW_FIELDS: Final[tuple[tuple[tuple[str, ...], ...], ...]] = (
    (QCEW_ROW_FIELDS,) * 3,
    (("home_id", "work_id", "origin", "destination", "total_jobs", "bits"),) * 9,
    (("county_id", "fips", "total", "total_bits", "owner", "owner_bits", "renter", "renter_bits"),)
    * 3,
    (("county_id", "fips", "median_rent_usd", "bits"),) * 3,
    (("county_id", "fips", "household_count", "bits"),) * 3,
    (("county_id", "fips", "coercive_type_id", "facility_count", "bits"),) * 5,
    (("county_id", "fips", "county_name", "state_id", "h3_res4"),) * 3,
    (("state_id", "state_fips", "state_name", "state_abbrev"),),
    (DATA_SOURCE_ROW_FIELDS, DATA_SOURCE_ROW_FIELDS, ("source_id", "source_code", "source_year")),
    (("time_id", "year", "month", "quarter", "is_annual"),) * 3,
    (("ownership_id", "own_code", "own_title", "is_government", "is_private"),),
    (("tenure_id", "tenure_type"),) * 3,
    (("race_id", "race_code", "race_name", "display_order"),),
    (
        (
            "burden_id",
            "bracket_code",
            "burden_min_pct",
            "is_cost_burdened",
            "is_severely_burdened",
            "bracket_order",
        ),
    ),
    (("coercive_type_id", "code", "command_chain"),) * 2,
    (("county_fips", "cz_id"),) * 3,
    (),
    (),
    (),
)
type IdentityFields = tuple[tuple[str, object], ...]

COUNTY_IDENTITY_FIELDS: Final[tuple[IdentityFields, ...]] = (
    (("county_id", 1281), ("fips", "26099")),
    (("county_id", 1294), ("fips", "26125")),
    (("county_id", 1313), ("fips", "26163")),
)
IDENTITY_EXPECTATIONS: Final[tuple[tuple[IdentityFields, ...], ...]] = (
    COUNTY_IDENTITY_FIELDS,
    (
        (("home_id", 1281), ("origin", "26099"), ("work_id", 1281), ("destination", "26099")),
        (("home_id", 1281), ("origin", "26099"), ("work_id", 1294), ("destination", "26125")),
        (("home_id", 1281), ("origin", "26099"), ("work_id", 1313), ("destination", "26163")),
        (("home_id", 1294), ("origin", "26125"), ("work_id", 1281), ("destination", "26099")),
        (("home_id", 1294), ("origin", "26125"), ("work_id", 1294), ("destination", "26125")),
        (("home_id", 1294), ("origin", "26125"), ("work_id", 1313), ("destination", "26163")),
        (("home_id", 1313), ("origin", "26163"), ("work_id", 1281), ("destination", "26099")),
        (("home_id", 1313), ("origin", "26163"), ("work_id", 1294), ("destination", "26125")),
        (("home_id", 1313), ("origin", "26163"), ("work_id", 1313), ("destination", "26163")),
    ),
    COUNTY_IDENTITY_FIELDS,
    COUNTY_IDENTITY_FIELDS,
    COUNTY_IDENTITY_FIELDS,
    (
        (("county_id", 1281), ("fips", "26099"), ("coercive_type_id", 2)),
        (("county_id", 1281), ("fips", "26099"), ("coercive_type_id", 3)),
        (("county_id", 1294), ("fips", "26125"), ("coercive_type_id", 3)),
        (("county_id", 1313), ("fips", "26163"), ("coercive_type_id", 2)),
        (("county_id", 1313), ("fips", "26163"), ("coercive_type_id", 3)),
    ),
    (
        (
            ("county_id", 1281),
            ("fips", "26099"),
            ("county_name", "Macomb County"),
            ("state_id", 23),
            ("h3_res4", None),
        ),
        (
            ("county_id", 1294),
            ("fips", "26125"),
            ("county_name", "Oakland County"),
            ("state_id", 23),
            ("h3_res4", None),
        ),
        (
            ("county_id", 1313),
            ("fips", "26163"),
            ("county_name", "Wayne County"),
            ("state_id", 23),
            ("h3_res4", None),
        ),
    ),
    ((("state_id", 23), ("state_fips", "26"), ("state_name", "Michigan"), ("state_abbrev", "MI")),),
    (
        (
            ("source_id", 2),
            ("source_code", "ACS5Y2010_API"),
            ("source_year", 2010),
            ("coverage_start_year", 2006),
            ("coverage_end_year", 2010),
        ),
        (
            ("source_id", 4),
            ("source_code", "ACS5Y2023_API"),
            ("source_year", 2023),
            ("coverage_start_year", 2019),
            ("coverage_end_year", 2023),
        ),
        (("source_id", 11), ("source_code", "HIFLD_PRISONS_2024"), ("source_year", 2024)),
    ),
    (
        (("time_id", 24), ("year", 2020), ("month", None), ("quarter", None), ("is_annual", True)),
        (("time_id", 27), ("year", 2023), ("month", None), ("quarter", None), ("is_annual", True)),
        (("time_id", 28), ("year", 2024), ("month", None), ("quarter", None), ("is_annual", True)),
    ),
    (
        (
            ("ownership_id", 1),
            ("own_code", "0"),
            ("own_title", "Ownership 0"),
            ("is_government", False),
            ("is_private", False),
        ),
    ),
    (
        (("tenure_id", 1), ("tenure_type", "total")),
        (("tenure_id", 2), ("tenure_type", "owner")),
        (("tenure_id", 3), ("tenure_type", "renter")),
    ),
    (
        (
            ("race_id", 1),
            ("race_code", "T"),
            ("race_name", "Total (all races)"),
            ("display_order", 0),
        ),
    ),
    (
        (
            ("burden_id", 9),
            ("bracket_code", "B25070_010"),
            ("burden_min_pct", "50.0"),
            ("is_cost_burdened", True),
            ("is_severely_burdened", True),
            ("bracket_order", 9),
        ),
    ),
    (
        (("coercive_type_id", 2), ("code", "prison_state"), ("command_chain", "state")),
        (("coercive_type_id", 3), ("code", "prison_local"), ("command_chain", "local")),
    ),
    (
        (("county_fips", "26099"), ("cz_id", "11600")),
        (("county_fips", "26125"), ("cz_id", "11600")),
        (("county_fips", "26163"), ("cz_id", "11600")),
    ),
    (),
    (),
    (),
)
PARQUET_COLUMNS: Final[tuple[tuple[str, ...], ...]] = (
    (
        "county_id",
        "time_id",
        "ownership_id",
        "establishments",
        "employment",
        "total_wages_usd",
        "disclosure_code",
        "is_imputed",
    ),
    ("home_county_id", "work_county_id", "time_id", "total_jobs"),
    ("county_id", "source_id", "tenure_id", "time_id", "race_id", "household_count"),
    ("county_id", "source_id", "time_id", "race_id", "median_rent_usd"),
    ("county_id", "source_id", "burden_id", "time_id", "race_id", "household_count"),
    ("county_id", "coercive_type_id", "source_id", "facility_count"),
    ("county_id", "fips", "state_id", "county_name", "h3_res4"),
    ("state_id", "state_fips", "state_name", "state_abbrev"),
    ("source_id", "source_code", "source_year", "coverage_start_year", "coverage_end_year"),
    ("time_id", "year", "month", "quarter", "is_annual"),
    ("ownership_id", "own_code", "own_title", "is_government", "is_private"),
    ("tenure_id", "tenure_type"),
    ("race_id", "race_code", "race_name", "display_order"),
    (
        "burden_id",
        "bracket_code",
        "burden_min_pct",
        "is_cost_burdened",
        "is_severely_burdened",
        "bracket_order",
    ),
    ("coercive_type_id", "code", "command_chain"),
    (),
    (),
    (),
    (),
)
COUNTY_IDS: Final = (1281, 1294, 1313)
COUNTY_FIPS: Final = ("26099", "26125", "26163")

type GapSpec = tuple[str, str, str, str, str | None, tuple[str, ...], str | None]

GAP_SPECS: Final[tuple[GapSpec, ...]] = (
    (
        "omb-msa-detroit-tri-county",
        "scale-membership/omb-msa",
        "NOT_COMPUTED",
        "MISSING_GOVERNED_OMB_DELINEATION",
        None,
        ("dim_county",),
        "reject legacy export/code 19820; require pinned governed OMB delineation",
    ),
    (
        "h3-population",
        "reproduction/h3-population-persons",
        "NOT_COMPUTED",
        "IDENTITY_CONTRACT_PENDING",
        "PER-21",
        ("h3_res7_population",),
        None,
    ),
    (
        "h3-workplace",
        "production/h3-workplace-jobs",
        "NOT_COMPUTED",
        "IDENTITY_CONTRACT_PENDING",
        "PER-21",
        ("h3_res7_workplace",),
        None,
    ),
    (
        "h3-land-fraction",
        "ecology/h3-land-fraction",
        "NOT_COMPUTED",
        "IDENTITY_CONTRACT_PENDING",
        "PER-21",
        ("h3_res7_land_mask",),
        None,
    ),
    (
        "census-housing-source-vintage-conflict",
        "reproduction/census-housing-households",
        "UNKNOWN",
        "PROVENANCE_COORDINATE_CONFLICT",
        "PER-28",
        ("fact_census_housing", "dim_data_source", "dim_time", "dim_housing_tenure", "dim_race"),
        None,
    ),
    (
        "census-rent-source-vintage-conflict",
        "reproduction/census-median-rent-usd",
        "UNKNOWN",
        "PROVENANCE_COORDINATE_CONFLICT",
        "PER-28",
        ("fact_census_rent", "dim_data_source", "dim_time", "dim_race"),
        None,
    ),
    (
        "census-rent-burden-source-vintage-conflict",
        "reproduction/census-rent-burden-households",
        "UNKNOWN",
        "PROVENANCE_COORDINATE_CONFLICT",
        "PER-28",
        ("fact_census_rent_burden", "dim_data_source", "dim_time", "dim_rent_burden", "dim_race"),
        None,
    ),
    (
        "command-administrative-centrality",
        "command/administrative-centrality",
        "NOT_COMPUTED",
        "MISSING_GOVERNED_PRODUCER",
        None,
        (),
        None,
    ),
    (
        "freight-road-corridor",
        "circulation/freight-road-corridor-intensity",
        "NOT_COMPUTED",
        "MISSING_GOVERNED_PRODUCER",
        "PER-31",
        (),
        None,
    ),
    (
        "eviction",
        "reproduction/eviction",
        "NOT_COMPUTED",
        "MISSING_GOVERNED_PRODUCER",
        None,
        (),
        None,
    ),
    (
        "foreclosure",
        "reproduction/foreclosure",
        "NOT_COMPUTED",
        "MISSING_GOVERNED_PRODUCER",
        None,
        (),
        None,
    ),
    (
        "absentee-ownership",
        "reproduction/absentee-ownership",
        "NOT_COMPUTED",
        "MISSING_GOVERNED_PRODUCER",
        None,
        (),
        None,
    ),
    (
        "agricultural-tenure-displacement",
        "extraction/agricultural-tenure-displacement",
        "NOT_COMPUTED",
        "MISSING_GOVERNED_PRODUCER",
        None,
        (),
        None,
    ),
    (
        "indigenous-jurisdiction",
        "jurisdiction/indigenous",
        "UNKNOWN",
        "REFERENCE_COVERAGE_UNAVAILABLE",
        None,
        (),
        None,
    ),
    ("care-capacity", "care/capacity", "NOT_COMPUTED", "MISSING_GOVERNED_PRODUCER", None, (), None),
    (
        "ecology-beyond-land-fraction",
        "ecology/beyond-land-fraction",
        "NOT_COMPUTED",
        "MISSING_GOVERNED_PRODUCER",
        None,
        (),
        None,
    ),
    (
        "windsor-essex-spatial-membership",
        "scale-membership/windsor-essex",
        "UNKNOWN",
        "REFERENCE_COVERAGE_UNAVAILABLE",
        None,
        (),
        None,
    ),
    ("player-fog", "player/fog", "NOT_COMPUTED", "PLAYER_BOUNDARY_UNAVAILABLE", "PER-22", (), None),
    (
        "action-eligibility",
        "player/action-eligibility",
        "NOT_COMPUTED",
        "PLAYER_BOUNDARY_UNAVAILABLE",
        "PER-27",
        (),
        None,
    ),
    (
        "organization-practice-state",
        "organization/practice-state",
        "NOT_COMPUTED",
        "PLAYER_BOUNDARY_UNAVAILABLE",
        "PER-56",
        (),
        None,
    ),
)

BOOL_FIELDS: Final = frozenset(
    {
        "is_imputed",
        "is_annual",
        "is_government",
        "is_private",
        "is_cost_burdened",
        "is_severely_burdened",
    }
)
NONE_FIELDS: Final = frozenset({"disclosure_code", "h3_res4", "month", "quarter"})
STRING_FIELDS: Final = frozenset(
    {
        "fips",
        "establishments_bits",
        "employment_bits",
        "total_wages_usd",
        "total_wages_bits",
        "origin",
        "destination",
        "bits",
        "total_bits",
        "owner_bits",
        "renter_bits",
        "median_rent_usd",
        "county_name",
        "state_fips",
        "state_name",
        "state_abbrev",
        "source_code",
        "own_code",
        "own_title",
        "tenure_type",
        "race_code",
        "race_name",
        "bracket_code",
        "burden_min_pct",
        "code",
        "command_chain",
        "county_fips",
        "cz_id",
    }
)

type Json = dict[str, object]


class DetroitControlError(ValueError):
    """A named, atomic Detroit control build refusal."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _fail(code: str) -> NoReturn:
    raise DetroitControlError(code)


class _StrictLoader(yaml.SafeLoader):
    """Safe YAML loader that refuses aliases and duplicate mapping keys."""

    def compose_node(self, parent: yaml.Node | None, index: int) -> yaml.Node:
        if self.check_event(yaml.AliasEvent):  # type: ignore[no-untyped-call]
            _fail("DETROIT_LEDGER_ALIAS")
        result = super().compose_node(parent, index)
        if result is None:
            _fail("DETROIT_LEDGER_YAML")
        return result


def _construct_mapping(
    loader: _StrictLoader, node: yaml.MappingNode, deep: bool = False
) -> dict[object, object]:
    result: dict[object, object] = {}
    for pair_index in range(MAX_SELECTED_ROWS):
        if pair_index == len(node.value):
            return result
        key_node, value_node = node.value[pair_index]
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str) or key in result:
            _fail("DETROIT_LEDGER_DUPLICATE_KEY")
        if key == "provenance_locators":
            result[key] = _construct_locator_sequence(value_node)
        else:
            result[key] = loader.construct_object(value_node, deep=deep)
    _fail("DETROIT_LEDGER_LIMIT")


def _construct_locator_sequence(node: yaml.Node) -> list[str]:
    if not isinstance(node, yaml.SequenceNode):
        _fail("DETROIT_LOCATOR_SHAPE")
    if len(node.value) > MAX_LOCATORS:
        _fail("DETROIT_LOCATOR_LIMIT")
    values: list[str] = []
    for locator_index in range(MAX_LOCATORS):
        if locator_index == len(node.value):
            return values
        child = node.value[locator_index]
        if not isinstance(child, yaml.ScalarNode):
            _fail("DETROIT_LOCATOR_SHAPE")
        values.append(child.value)
    _fail("DETROIT_LOCATOR_LIMIT")


_StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


def _mapping(value: object, code: str) -> Json:
    if not isinstance(value, dict) or len(value) > MAX_SELECTED_ROWS:
        _fail(code)
    keys = tuple(value)
    for key_index in range(MAX_SELECTED_ROWS):
        if key_index == len(keys):
            break
        if not isinstance(keys[key_index], str):
            _fail(code)
    return cast(Json, value)


def _sequence(value: object, maximum: int, code: str) -> list[object]:
    if not isinstance(value, list) or len(value) > maximum:
        _fail(code)
    return value


def _exact_fields(row: Json, expected: set[str], code: str) -> None:
    if set(row) != expected:
        _fail(code)


def load_extraction(path: Path = EXTRACTION_PATH) -> Json:
    """Load the closed extraction ledger without materializing unbounded input."""
    raw = path.read_bytes()
    if len(raw) > MAX_LEDGER_BYTES:
        _fail("DETROIT_LEDGER_SIZE")
    try:
        loaded = yaml.load(raw, Loader=_StrictLoader)  # noqa: S506
    except DetroitControlError:
        raise
    except yaml.YAMLError as error:
        raise DetroitControlError("DETROIT_LEDGER_YAML") from error
    ledger = _mapping(loaded, "DETROIT_LEDGER_SHAPE")
    _exact_fields(
        ledger,
        {"schema", "schema_version", "default_case_id", "question_id", "artifacts", "gaps"},
        "DETROIT_LEDGER_UNKNOWN_FIELD",
    )
    if ledger["schema"] != "babylon.detroit-windsor-rtd-v1-extraction":
        _fail("DETROIT_LEDGER_SCHEMA")
    if ledger["schema_version"] != 1 or ledger["default_case_id"] != DEFAULT_CASE_ID:
        _fail("DETROIT_LEDGER_SCHEMA")
    artifacts = _sequence(ledger["artifacts"], EXPECTED_ARTIFACTS, "DETROIT_ARTIFACT_LIMIT")
    gaps = _sequence(ledger["gaps"], EXPECTED_GAPS, "DETROIT_GAP_LIMIT")
    if len(artifacts) != EXPECTED_ARTIFACTS or len(gaps) != EXPECTED_GAPS:
        _fail("DETROIT_LEDGER_CARDINALITY")
    _validate_artifact_rows(artifacts)
    _validate_gap_rows(gaps)
    return ledger


def _validate_artifact_rows(rows: list[object]) -> None:
    expected = {
        "artifact_id",
        "relative_path",
        "verification_mode",
        "sha256",
        "bytes",
        "rows",
        "row_groups",
        "schema",
        "metric_contracts",
        "selectors",
        "selected_rows",
        "provenance_locators",
    }
    seen: set[str] = set()
    ordered_ids: list[str] = []
    reference_only: list[str] = []
    for artifact_index in range(EXPECTED_ARTIFACTS):
        row = _mapping(rows[artifact_index], "DETROIT_ARTIFACT_SHAPE")
        _exact_fields(row, expected, "DETROIT_ARTIFACT_UNKNOWN_FIELD")
        artifact_id = row["artifact_id"]
        if not isinstance(artifact_id, str) or artifact_id in seen:
            _fail("DETROIT_ARTIFACT_DUPLICATE")
        seen.add(artifact_id)
        ordered_ids.append(artifact_id)
        _validate_artifact_metadata(row, artifact_index)
        if row["verification_mode"] == "REFERENCE_DIGEST_ONLY":
            reference_only.append(artifact_id)
        selectors = _sequence(row["selectors"], MAX_SELECTORS, "DETROIT_SELECTOR_LIMIT")
        _validate_selectors(selectors, artifact_index)
        selected = _sequence(row["selected_rows"], MAX_SELECTED_ROWS, "DETROIT_SELECTED_ROW_LIMIT")
        _validate_selected_rows(selected, artifact_index)
        locators = _sequence(row["provenance_locators"], MAX_LOCATORS, "DETROIT_LOCATOR_LIMIT")
        _validate_locator_values(locators)
        contracts = _sequence(row["metric_contracts"], MAX_SELECTORS, "DETROIT_METRIC_LIMIT")
        _validate_metric_contracts(contracts, artifact_index)
    if tuple(ordered_ids) != ARTIFACT_IDS:
        _fail("DETROIT_ARTIFACT_ALIAS")
    if tuple(reference_only) != REFERENCE_ONLY:
        _fail("DETROIT_REFERENCE_ONLY_SET")


def _validate_artifact_metadata(row: Json, artifact_index: int) -> None:
    relative = row["relative_path"]
    if not isinstance(relative, str):
        _fail("DETROIT_ARTIFACT_PATH")
    relative_path = Path(relative)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        _fail("DETROIT_ARTIFACT_PATH")
    expected_path, expected_mode = ARTIFACT_LAYOUT[artifact_index]
    if relative != expected_path:
        _fail("DETROIT_ARTIFACT_LAYOUT")
    if row["verification_mode"] != expected_mode:
        _fail("DETROIT_ARTIFACT_MODE")
    digest = row["sha256"]
    if not isinstance(digest, str) or len(digest) != 64:
        _fail("DETROIT_ARTIFACT_METADATA")
    try:
        int(digest, 16)
    except ValueError as error:
        raise DetroitControlError("DETROIT_ARTIFACT_METADATA") from error
    if expected_mode == "REFERENCE_DIGEST_ONLY":
        nullable_fields = ("bytes", "rows", "row_groups", "schema")
        for field_index in range(4):
            if row[nullable_fields[field_index]] is not None:
                _fail("DETROIT_ARTIFACT_METADATA")
        return
    integer_fields = ("bytes", "rows", "row_groups")
    for field_index in range(3):
        field = integer_fields[field_index]
        value = row[field]
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            _fail("DETROIT_ARTIFACT_METADATA")
    if not isinstance(row["schema"], str):
        _fail("DETROIT_ARTIFACT_METADATA")


def _validate_selectors(selectors: list[object], artifact_index: int) -> None:
    specs = SELECTOR_FIELDS[artifact_index]
    seen: set[bytes] = set()
    for selector_index in range(MAX_SELECTORS):
        if selector_index == len(selectors):
            break
        selector = _mapping(selectors[selector_index], "DETROIT_SELECTOR_SHAPE")
        key = json.dumps(selector, sort_keys=True, separators=(",", ":")).encode()
        if key in seen:
            _fail("DETROIT_SELECTOR_DUPLICATE")
        seen.add(key)
    if len(selectors) != len(specs):
        _fail("DETROIT_SELECTOR_CARDINALITY")
    for selector_index in range(MAX_SELECTORS):
        if selector_index == len(specs):
            return
        selector = cast(Json, selectors[selector_index])
        _exact_fields(selector, set(specs[selector_index]), "DETROIT_SELECTOR_FIELDS")
        fields = specs[selector_index]
        for field_index in range(MAX_SOURCE_FIELDS):
            if field_index == len(fields):
                break
            _validate_selector_value(fields[field_index], selector[fields[field_index]])
    _fail("DETROIT_SELECTOR_LIMIT")


def _validate_selector_value(field: str, value: object) -> None:
    list_lengths = {
        "county_ids": 3,
        "source_ids": 3,
        "time_ids": 3,
        "tenure_ids": 3,
        "coercive_type_ids": 2,
        "county_fips": 3,
    }
    expected_length = list_lengths.get(field)
    if expected_length is None:
        if not isinstance(value, int) or isinstance(value, bool):
            _fail("DETROIT_SELECTOR_TYPE")
        if field == "expected_rows" and value != 0:
            _fail("DETROIT_SELECTOR_TYPE")
        return
    values = _sequence(value, expected_length, "DETROIT_SELECTOR_TYPE")
    if len(values) != expected_length:
        _fail("DETROIT_SELECTOR_TYPE")
    seen: set[object] = set()
    for value_index in range(3):
        if value_index == len(values):
            break
        item = values[value_index]
        if field == "county_fips":
            if not isinstance(item, str):
                _fail("DETROIT_SELECTOR_TYPE")
        elif not isinstance(item, int) or isinstance(item, bool):
            _fail("DETROIT_SELECTOR_TYPE")
        if item in seen:
            _fail("DETROIT_SELECTOR_TYPE")
        seen.add(item)


def _validate_selected_rows(rows: list[object], artifact_index: int) -> None:
    expected_rows = SELECTED_ROW_FIELDS[artifact_index]
    if len(rows) != len(expected_rows):
        _fail("DETROIT_SELECTED_ROW_CARDINALITY")
    for row_index in range(MAX_SELECTED_ROWS):
        if row_index == len(expected_rows):
            break
        row = _mapping(rows[row_index], "DETROIT_SELECTED_ROW_SHAPE")
        fields = expected_rows[row_index]
        _exact_fields(row, set(fields), "DETROIT_SELECTED_ROW_FIELDS")
        for field_index in range(MAX_LOCATORS):
            if field_index == len(fields):
                break
            field = fields[field_index]
            if not _selected_value_matches(field, row[field]):
                _fail("DETROIT_SELECTED_ROW_TYPE")
    _validate_selected_identities(rows, artifact_index)


def _selected_value_matches(field: str, value: object) -> bool:
    if field in BOOL_FIELDS:
        return isinstance(value, bool)
    if field in NONE_FIELDS:
        return value is None
    if field in STRING_FIELDS:
        return isinstance(value, str)
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_selected_identities(rows: list[object], artifact_index: int) -> None:
    expected_rows = IDENTITY_EXPECTATIONS[artifact_index]
    if len(rows) != len(expected_rows):
        _fail("DETROIT_SELECTED_ROW_CARDINALITY")
    for row_index in range(MAX_SELECTED_ROWS):
        if row_index == len(expected_rows):
            return
        row = cast(Json, rows[row_index])
        expected_fields = expected_rows[row_index]
        for field_index in range(MAX_SOURCE_FIELDS):
            if field_index == len(expected_fields):
                break
            field, expected = expected_fields[field_index]
            if row[field] != expected:
                _fail("DETROIT_SELECTED_ROW_IDENTITY")
    _fail("DETROIT_SELECTED_ROW_LIMIT")


def _validate_locator_values(values: list[object]) -> None:
    encoded_length = 0
    for locator_index in range(MAX_LOCATORS):
        if locator_index == len(values):
            return
        value = values[locator_index]
        if not isinstance(value, str):
            _fail("DETROIT_LOCATOR_TYPE")
        if not value or unicodedata.normalize("NFC", value) != value:
            _fail("DETROIT_LOCATOR_TEXT")
        try:
            value_bytes = value.encode("utf-8")
        except UnicodeEncodeError as error:
            raise DetroitControlError("DETROIT_LOCATOR_TEXT") from error
        if len(value_bytes) > RTD_MAX_LOCATOR_BYTES:
            _fail("DETROIT_LOCATOR_TEXT")
        encoded_length += len(value_bytes) + (1 if locator_index > 0 else 0)
        if encoded_length > RTD_MAX_LOCATOR_BYTES:
            _fail("DETROIT_LOCATOR_TEXT")


def _validate_string_sequence(values: list[object]) -> None:
    for locator_index in range(MAX_LOCATORS):
        if locator_index == len(values):
            return
        if not isinstance(values[locator_index], str):
            _fail("DETROIT_LOCATOR_TYPE")


def _validate_metric_contracts(contracts: list[object], artifact_index: int) -> None:
    if len(RTD_V1_METRIC_REGISTRY) != EXPECTED_METRICS:
        _fail("DETROIT_METRIC_REGISTRY")
    registry = {}
    for row_index in range(EXPECTED_METRICS):
        row = RTD_V1_METRIC_REGISTRY[row_index]
        registry[row.metric.local_id] = row
    expected = ARTIFACT_METRICS[artifact_index]
    seen: set[str] = set()
    actual: list[str] = []
    for contract_index in range(MAX_SELECTORS):
        if contract_index == len(contracts):
            break
        contract = _mapping(contracts[contract_index], "DETROIT_METRIC_SHAPE")
        _exact_fields(
            contract,
            {"local_id", "producer", "aggregation_rule", "reference_artifact", "digest"},
            "DETROIT_METRIC_UNKNOWN_FIELD",
        )
        local_id = contract["local_id"]
        if not isinstance(local_id, str):
            _fail("DETROIT_METRIC_REGISTRY")
        if local_id in seen:
            _fail("DETROIT_METRIC_DUPLICATE")
        if local_id not in expected:
            _fail("DETROIT_METRIC_EXTRA")
        seen.add(local_id)
        actual.append(local_id)
        registry_row = registry.get(local_id) if isinstance(local_id, str) else None
        if registry_row is None:
            _fail("DETROIT_METRIC_REGISTRY")
        reference = registry_row.reference_artifact
        expected_reference = None if reference is None else reference.local_id
        if (
            contract["producer"] != registry_row.producer.local_id
            or contract["aggregation_rule"] != registry_row.aggregation_rule.value
            or contract["reference_artifact"] != expected_reference
            or contract["digest"] != registry_row.reference_digest
        ):
            _fail("DETROIT_METRIC_REGISTRY")
    if len(actual) < len(expected):
        _fail("DETROIT_METRIC_MISSING")
    if len(actual) > len(expected):
        _fail("DETROIT_METRIC_EXTRA")
    if tuple(actual) != expected:
        _fail("DETROIT_METRIC_DECLARATION")


def _validate_gap_rows(rows: list[object]) -> None:
    seen: set[str] = set()
    fields = {"suffix", "requested", "status", "reason", "producer", "provenance_artifacts"}
    for gap_index in range(EXPECTED_GAPS):
        row = _mapping(rows[gap_index], "DETROIT_GAP_SHAPE")
        spec = GAP_SPECS[gap_index]
        expected_fields = fields | ({"note"} if spec[6] is not None else set())
        _exact_fields(row, expected_fields, "DETROIT_GAP_FIELDS")
        suffix = row["suffix"]
        if not isinstance(suffix, str) or suffix in seen:
            _fail("DETROIT_GAP_DUPLICATE")
        seen.add(suffix)
        provenance = _sequence(row["provenance_artifacts"], MAX_LOCATORS, "DETROIT_LOCATOR_LIMIT")
        _validate_string_sequence(provenance)
        actual = (
            suffix,
            row["requested"],
            row["status"],
            row["reason"],
            row["producer"],
            tuple(provenance),
            row.get("note"),
        )
        if actual != spec:
            _fail("DETROIT_GAP_SEMANTICS")


def _identity(domain: str, authority: str, local_id: str) -> Json:
    return {"domain": domain, "authority": authority, "local_id": local_id}


def _artifact_map(ledger: Json) -> dict[str, Json]:
    rows = cast(list[object], ledger["artifacts"])
    result: dict[str, Json] = {}
    for artifact_index in range(EXPECTED_ARTIFACTS):
        row = cast(Json, rows[artifact_index])
        result[cast(str, row["artifact_id"])] = row
    return result


def _reference_digests(artifacts: dict[str, Json]) -> list[Json]:
    rows: list[Json] = []
    artifact_ids = tuple(artifacts)
    if len(artifact_ids) != EXPECTED_ARTIFACTS:
        _fail("DETROIT_LEDGER_CARDINALITY")
    for artifact_index in range(EXPECTED_ARTIFACTS):
        artifact_id = artifact_ids[artifact_index]
        row = artifacts[artifact_id]
        evidence = "Derived" if artifact_id in REFERENCE_ONLY else "Observed"
        rows.append(
            {
                "reference_id": _identity("reference-artifact", "babylon.data.v7", artifact_id),
                "sha256_hex": row["sha256"],
                "artifact_schema_id_or_null": None,
                "vintage": "contract-v1",
                "evidence_class": evidence,
            }
        )
    return rows


def _provenance(artifacts: dict[str, Json]) -> list[Json]:
    rows: list[Json] = []
    artifact_ids = tuple(artifacts)
    if len(artifact_ids) != EXPECTED_ARTIFACTS:
        _fail("DETROIT_LEDGER_CARDINALITY")
    for artifact_index in range(EXPECTED_ARTIFACTS):
        artifact_id = artifact_ids[artifact_index]
        artifact = artifacts[artifact_id]
        locators = cast(list[object], artifact["provenance_locators"])
        locator_parts: list[str] = []
        for locator_index in range(MAX_LOCATORS):
            if locator_index == len(locators):
                break
            locator_parts.append(cast(str, locators[locator_index]))
        locator = ";".join(locator_parts)
        rows.append(
            {
                "provenance_id": _identity("provenance", "babylon.rtd.v1", artifact_id),
                "artifact_digest": artifact["sha256"],
                "locator": locator,
                "vintage": "contract-v1",
                "evidence_class": "Derived" if artifact_id in REFERENCE_ONLY else "Observed",
                "transformation_digest_or_null": None,
            }
        )
    return rows


def _memberships() -> list[Json]:
    rows: list[Json] = []
    for county_index in range(3):
        county = _identity("county", "census", COUNTY_FIPS[county_index])
        specs = (
            ("state", _identity("state", "census", "26"), "ADMINISTRATIVE", "Derived", "dim_state"),
            (
                "national",
                _identity("country", "iso-3166-1-alpha-2", "US"),
                "NATIONAL",
                "Designed",
                None,
            ),
            (
                "cz",
                _identity("commuting-zone", "ers", "11600"),
                "COMMUTING_ZONE",
                "Derived",
                "bridge_county_cz",
            ),
        )
        for spec_index in range(3):
            suffix, scale, kind, evidence, provenance = specs[spec_index]
            refs = (
                []
                if provenance is None
                else [_identity("provenance", "babylon.rtd.v1", provenance)]
            )
            rows.append(
                {
                    "membership_id": _identity(
                        "membership", "babylon.rtd.v1", f"{COUNTY_FIPS[county_index]}-{suffix}"
                    ),
                    "member_ref": county,
                    "scale_ref": scale,
                    "membership_kind": kind,
                    "status": "PRESENT",
                    "weight_status": "ABSENT",
                    "weight_bits_or_null": None,
                    "coverage": "COMPLETE",
                    "evidence_class": evidence,
                    "provenance_refs": refs,
                }
            )
    return rows


def _coordinate(name: str, member: Json) -> Json:
    return {
        "dimension_ref": _identity("dimension", "babylon.rtd.v1", name),
        "member_ref": member,
    }


def _facet(
    facet_id: str,
    family: str,
    subject: Json,
    metric: str,
    unit: str,
    native_scale: str,
    coordinates: list[Json],
    value_kind: str,
    bits: str,
    evidence: str,
    provenance: str,
    vintage: str,
) -> Json:
    return {
        "facet_id": _identity("facet", "babylon.rtd.v1", facet_id),
        "family": family,
        "subject_ref": subject,
        "metric_id": _identity("metric", "babylon.rtd.v1", metric),
        "unit_id": _identity("unit", "babylon.rtd.v1", unit),
        "native_scale": _identity("native-scale", "babylon.rtd.v1", native_scale),
        "coordinates": coordinates,
        "vintage": vintage,
        "status": "PRESENT",
        "value_kind": value_kind,
        "value_bits_or_null": bits,
        "coverage": "COMPLETE",
        "evidence_class": evidence,
        "provenance_refs": [_identity("provenance", "babylon.rtd.v1", provenance)],
    }


def _qcew_facets(artifact: Json) -> list[Json]:
    facets: list[Json] = []
    rows = cast(list[object], artifact["selected_rows"])
    specs = (
        (
            "establishments",
            ARTIFACT_METRICS[0][0],
            "establishments",
            "UINT64_BITS",
        ),
        ("employment", ARTIFACT_METRICS[0][1], "jobs", "UINT64_BITS"),
        ("total-wages", ARTIFACT_METRICS[0][2], "usd-current", "FLOAT64_BITS"),
    )
    for row_index in range(3):
        row = cast(Json, rows[row_index])
        county = _identity("county", "census", cast(str, row["fips"]))
        coordinates = [
            _coordinate("county", county),
            _coordinate("ownership", _identity("ownership", "qcew", "0")),
        ]
        bits_by_name = {
            "establishments": cast(str, row["establishments_bits"]),
            "employment": cast(str, row["employment_bits"]),
            "total-wages": cast(str, row["total_wages_bits"]),
        }
        for spec_index in range(3):
            suffix, metric, unit, kind = specs[spec_index]
            facets.append(
                _facet(
                    f"qcew-{row['fips']}-{suffix}",
                    "PRODUCTION_CIRCULATION",
                    county,
                    metric,
                    unit,
                    "county-ownership-year",
                    coordinates,
                    kind,
                    bits_by_name[suffix],
                    "Derived",
                    "fact_qcew_county_rollup",
                    "2024",
                )
            )
    return facets


def _lodes_facets_and_flows(artifact: Json) -> tuple[list[Json], list[Json]]:
    facets: list[Json] = []
    flows: list[Json] = []
    rows = cast(list[object], artifact["selected_rows"])
    for row_index in range(9):
        row = cast(Json, rows[row_index])
        origin = _identity("county", "census", cast(str, row["origin"]))
        destination = _identity("county", "census", cast(str, row["destination"]))
        local_id = f"lodes-{row['origin']}-{row['destination']}"
        flow_id = _identity("flow", "babylon.rtd.v1", local_id)
        facet_id = _identity("facet", "babylon.rtd.v1", local_id)
        facets.append(
            _facet(
                local_id,
                "PRODUCTION_CIRCULATION",
                flow_id,
                ARTIFACT_METRICS[1][0],
                "jobs",
                "home-county-work-county-year",
                [_coordinate("home-county", origin), _coordinate("work-county", destination)],
                "UINT64_BITS",
                cast(str, row["bits"]),
                "Derived",
                "fact_lodes_commuter_flow",
                "2020",
            )
        )
        flows.append(
            {
                "flow_id": flow_id,
                "flow_kind": "COMMUTER_JOBS",
                "origin_ref": origin,
                "destination_ref": destination,
                "payload_facets": [facet_id],
                "native_scale": _identity(
                    "native-scale", "babylon.rtd.v1", "home-county-work-county-year"
                ),
                "status": "PRESENT",
                "coverage": "COMPLETE",
                "evidence_class": "Derived",
                "provenance_refs": [
                    _identity("provenance", "babylon.rtd.v1", "fact_lodes_commuter_flow")
                ],
            }
        )
    return facets, flows


def _carceral_facets(artifact: Json) -> list[Json]:
    facets: list[Json] = []
    rows = cast(list[object], artifact["selected_rows"])
    for row_index in range(5):
        row = cast(Json, rows[row_index])
        county = _identity("county", "census", cast(str, row["fips"]))
        coercive = _identity("coercive-type", "babylon.data.v7", str(row["coercive_type_id"]))
        source = _identity("source", "babylon.data.v7", "11")
        facets.append(
            _facet(
                f"carceral-{row['fips']}-{row['coercive_type_id']}",
                "EXTRACTION_ABANDONMENT_CARCERAL",
                county,
                ARTIFACT_METRICS[5][0],
                "facilities",
                "county-coercive-type-source",
                [
                    _coordinate("county", county),
                    _coordinate("coercive-type", coercive),
                    _coordinate("source", source),
                ],
                "UINT64_BITS",
                cast(str, row["bits"]),
                "Observed",
                "fact_coercive_infrastructure",
                "2024",
            )
        )
    return facets


def _gaps(ledger: Json) -> list[Json]:
    rows: list[Json] = []
    gaps = cast(list[object], ledger["gaps"])
    for gap_index in range(EXPECTED_GAPS):
        gap = cast(Json, gaps[gap_index])
        provenance = cast(list[object], gap["provenance_artifacts"])
        refs: list[Json] = []
        for locator_index in range(MAX_LOCATORS):
            if locator_index == len(provenance):
                break
            refs.append(
                _identity("provenance", "babylon.rtd.v1", cast(str, provenance[locator_index]))
            )
        rows.append(
            {
                "gap_id": _identity("gap", "babylon.rtd.v1", cast(str, gap["suffix"])),
                "requested_metric_or_relation": _identity(
                    "metric-or-relation", "babylon.rtd.v1", cast(str, gap["requested"])
                ),
                "status": gap["status"],
                "reason_code": gap["reason"],
                "required_producer_or_null": gap["producer"],
                "provenance_refs": refs,
            }
        )
    return rows


def _world_identity() -> Json:
    try:
        loaded = json.loads(WORLD_PATH.read_bytes())
    except (OSError, json.JSONDecodeError) as error:
        raise DetroitControlError("DETROIT_WORLD_IDENTITY") from error
    world = _mapping(loaded, "DETROIT_WORLD_IDENTITY")
    expected = {
        "verified_tick",
        "graph_state_hash",
        "nominal_world_hash",
        "scenario_digest",
        "rule_digest",
        "definitions_digest",
        "template_digest",
    }
    _exact_fields(world, expected, "DETROIT_WORLD_IDENTITY")
    checks = (
        ("scenario_digest", SCENARIO_PATH.read_bytes()),
        ("rule_digest", RULE_PATH.read_bytes()),
        ("template_digest", EXTRACTION_PATH.read_bytes()),
    )
    for check_index in range(3):
        field, payload = checks[check_index]
        if world[field] != hashlib.sha256(payload).hexdigest():
            _fail("DETROIT_WORLD_DIGEST")
    if world["definitions_digest"] != canonical_defines_hash(GameDefines.load_default()):
        _fail("DETROIT_DEFINES_DIGEST")
    graph_hash = world["graph_state_hash"]
    world_hash = world["nominal_world_hash"]
    if (
        world["verified_tick"] != 1
        or graph_hash == "0" * 64
        or world_hash == "0" * 64
        or graph_hash == world_hash
    ):
        _fail("DETROIT_WORLD_IDENTITY")
    return world


def build_draft(case_id: str = DEFAULT_CASE_ID) -> Json:
    """Build only the one closed administrative default case."""
    if case_id != DEFAULT_CASE_ID:
        _fail("DETROIT_DEFAULT_CASE")
    ledger = load_extraction()
    artifacts = _artifact_map(ledger)
    world = _world_identity()
    lodes_facets, flows = _lodes_facets_and_flows(artifacts["fact_lodes_commuter_flow"])
    facets = _qcew_facets(artifacts["fact_qcew_county_rollup"])
    facets.extend(lodes_facets)
    facets.extend(_carceral_facets(artifacts["fact_coercive_infrastructure"]))
    focus: list[Json] = []
    focus_ids = ("26163", "26125", "26099")
    for focus_index in range(3):
        focus.append(_identity("county", "census", focus_ids[focus_index]))
    return {
        "schema": "babylon.relational-territory-dossier",
        "schema_version": 1,
        "projection_version": 1,
        "audience": "ADMIN_MATERIAL",
        "durability": "IN_MEMORY",
        "verified_tick": world["verified_tick"],
        "graph_state_hash": world["graph_state_hash"],
        "nominal_world_hash": world["nominal_world_hash"],
        "reference_digests": _reference_digests(artifacts),
        "definitions_digest": world["definitions_digest"],
        "template_digest": world["template_digest"],
        "fog_policy_digest": None,
        "knowledge_context_digest": None,
        "actor": None,
        "focus": focus,
        "scale_memberships": _memberships(),
        "facets": facets,
        "dyads": [],
        "hyperedges": [],
        "flows": flows,
        "gaps": _gaps(ledger),
        "provenance": _provenance(artifacts),
        "decision_surface": {
            "question_id": _identity(
                "question", "babylon.rtd.v1", cast(str, ledger["question_id"])
            ),
            "signal_refs": focus,
            "action_refs": [],
            "receipt_refs": [],
            "archive_subject_refs": [],
        },
    }


def control_bytes() -> bytes:
    draft = validate_control_draft(build_draft())
    sealed = seal_draft(draft)
    payload = sealed.model_dump(mode="json", by_alias=True)
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        + b"\n"
    )


def validate_control_draft(payload: Mapping[str, object]) -> RtdDossierDraftV1:
    """Validate the generic RTD contract plus the closed T1 fixture boundary."""
    gaps_value = payload.get("gaps")
    if not isinstance(gaps_value, list):
        _fail("DETROIT_REQUIRED_GAP")
    if len(gaps_value) < EXPECTED_GAPS:
        _fail("DETROIT_REQUIRED_GAP")
    if len(gaps_value) > EXPECTED_GAPS:
        _fail("DETROIT_UNREGISTERED_GAP")
    ledger = load_extraction()
    expected_rows = cast(list[object], ledger["gaps"])
    expected_parts: list[object] = []
    for expected_index in range(EXPECTED_GAPS):
        expected_parts.append(cast(Json, expected_rows[expected_index])["suffix"])
    expected = tuple(expected_parts)
    actual: list[object] = []
    for gap_index in range(EXPECTED_GAPS):
        gap = _mapping(gaps_value[gap_index], "DETROIT_GAP_SHAPE")
        gap_id = _mapping(gap.get("gap_id"), "DETROIT_GAP_SHAPE")
        actual.append(gap_id.get("local_id"))
    if tuple(actual) != expected:
        _fail("DETROIT_REQUIRED_GAP")
    draft = parse_draft(payload)
    actual_focus: list[str] = []
    for focus_index in range(3):
        if focus_index == len(draft.focus):
            _fail("DETROIT_FOCUS")
        actual_focus.append(draft.focus[focus_index].local_id)
    if len(draft.focus) != 3 or tuple(actual_focus) != ("26163", "26125", "26099"):
        _fail("DETROIT_FOCUS")
    if len(draft.scale_memberships) != 9:
        _fail("DETROIT_MEMBERSHIP")
    forbidden = {
        "reproduction/census-housing-households",
        "reproduction/census-median-rent-usd",
        "reproduction/census-rent-burden-households",
    }
    for facet_index in range(MAX_SELECTED_ROWS):
        if facet_index == len(draft.facets):
            break
        if draft.facets[facet_index].metric_id.local_id in forbidden:
            _fail("DETROIT_CENSUS_FACET")
    return draft


def border_synthesis_draft() -> Json:
    """Return the separate opt-in Canadian synthesis vector draft."""
    draft = build_draft()
    provenance_id = _identity("provenance", "babylon.rtd.v1", "border-synthesis-opt-in")
    provenance = cast(list[object], draft["provenance"])
    provenance.append(
        {
            "provenance_id": provenance_id,
            "artifact_digest": hashlib.sha256(b"border-synthesis-opt-in").hexdigest(),
            "locator": "policy-disabled opt-in synthetic relation",
            "vintage": "contract-v1",
            "evidence_class": "Derived",
            "transformation_digest_or_null": None,
        }
    )
    flows = cast(list[object], draft["flows"])
    flows.append(
        {
            "flow_id": _identity("flow", "babylon.rtd.v1", "border-synthesis-opt-in"),
            "flow_kind": "BORDER_SYNTHESIS",
            "origin_ref": _identity("place", "census", "2622000"),
            "destination_ref": _identity("external", "babylon.rtd.v1", "canada"),
            "payload_facets": [],
            "native_scale": _identity(
                "native-scale", "babylon.rtd.v1", "policy-opt-in-border-synthesis"
            ),
            "status": "PRESENT",
            "coverage": "UNKNOWN",
            "evidence_class": "Derived",
            "provenance_refs": [provenance_id],
        }
    )
    return draft


def _schema_string(schema: pa.Schema) -> str:
    if len(schema) > MAX_SOURCE_FIELDS:
        _fail("DETROIT_SOURCE_SCHEMA")
    fields: list[str] = []
    for field_index in range(MAX_SOURCE_FIELDS):
        if field_index == len(schema):
            break
        field = schema[field_index]
        fields.append(f"{field.name}:{field.type}")
    return ",".join(fields)


def _source_path(root: Path, artifact: Json, artifact_index: int) -> Path:
    relative = cast(str, artifact["relative_path"])
    base = ROOT if artifact["verification_mode"] == "TRACKED_CSV" else root
    resolved_base = base.resolve()
    candidate = base / relative
    resolved = candidate.resolve()
    if not resolved.is_relative_to(resolved_base):
        _fail("DETROIT_ARTIFACT_PATH")
    expected_path, _ = ARTIFACT_LAYOUT[artifact_index]
    if relative != expected_path:
        _fail("DETROIT_ARTIFACT_LAYOUT")
    return candidate


def _verify_metadata(path: Path, artifact: Json) -> pq.ParquetFile:
    try:
        stat = path.stat()
    except OSError as error:
        raise DetroitControlError("DETROIT_SOURCE_MISSING") from error
    if stat.st_size != artifact["bytes"] or stat.st_size > MAX_SOURCE_BYTES:
        _fail("DETROIT_SOURCE_METADATA")
    if hashlib.sha256(path.read_bytes()).hexdigest() != artifact["sha256"]:
        _fail("DETROIT_SOURCE_DIGEST")
    parquet = pq.ParquetFile(path)
    metadata = parquet.metadata
    if metadata.num_rows != artifact["rows"] or metadata.num_rows > MAX_SOURCE_ROWS:
        _fail("DETROIT_SOURCE_METADATA")
    if (
        metadata.num_row_groups != artifact["row_groups"]
        or metadata.num_row_groups != MAX_ROW_GROUPS
    ):
        _fail("DETROIT_SOURCE_METADATA")
    if _schema_string(parquet.schema_arrow) != artifact["schema"]:
        _fail("DETROIT_SOURCE_SCHEMA")
    return parquet


def _selector_matches(artifact_index: int, row: Json, selector: Json) -> bool:
    fields = tuple(selector)
    for field_index in range(MAX_SOURCE_FIELDS):
        if field_index == len(fields):
            return True
        field = fields[field_index]
        expected = selector[field]
        if field == "expected_rows":
            continue
        if artifact_index == 1 and field == "county_ids":
            if row.get("home_county_id") not in cast(list[object], expected):
                return False
            if row.get("work_county_id") not in cast(list[object], expected):
                return False
            continue
        column = "county_fips" if field == "county_fips" else field.removesuffix("s")
        if isinstance(expected, list):
            if row.get(column) not in expected:
                return False
        elif row.get(column) != expected:
            return False
    _fail("DETROIT_SELECTOR_FIELDS")


def _finish_scan(selected: list[Json], match_counts: list[int], artifact_index: int) -> list[Json]:
    expected = SELECTOR_COUNTS[artifact_index]
    for selector_index in range(MAX_SELECTORS):
        if selector_index == len(expected):
            return selected
        if match_counts[selector_index] != expected[selector_index]:
            _fail("DETROIT_SOURCE_CARDINALITY")
    _fail("DETROIT_SELECTOR_LIMIT")


def _scan_selected(parquet: pq.ParquetFile, artifact: Json, artifact_index: int) -> list[Json]:
    selected: list[Json] = []
    selectors = cast(list[object], artifact["selectors"])
    match_counts = [0] * len(selectors)
    columns = list(PARQUET_COLUMNS[artifact_index])
    batches = parquet.iter_batches(row_groups=[0], batch_size=SOURCE_BATCH_SIZE, columns=columns)
    for _batch_index in range(MAX_SOURCE_BATCHES):
        try:
            batch = next(batches)
        except StopIteration:
            return _finish_scan(selected, match_counts, artifact_index)
        rows = batch.to_pylist()
        for row_index in range(SOURCE_BATCH_SIZE):
            if row_index == len(rows):
                break
            row = cast(Json, rows[row_index])
            matched = False
            for selector_index in range(MAX_SELECTORS):
                if selector_index == len(selectors):
                    break
                selector = cast(Json, selectors[selector_index])
                if _selector_matches(artifact_index, row, selector):
                    if matched:
                        _fail("DETROIT_SELECTOR_OVERLAP")
                    matched = True
                    match_counts[selector_index] += 1
            if not matched:
                continue
            if len(selected) == MAX_SELECTED_ROWS:
                _fail("DETROIT_SELECTED_ROW_LIMIT")
            selected.append(row)
    try:
        next(batches)
    except StopIteration:
        return _finish_scan(selected, match_counts, artifact_index)
    _fail("DETROIT_SOURCE_BATCH_LIMIT")


def _uint_bits(value: object) -> str:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        _fail("DETROIT_SOURCE_VALUE")
    return f"{value:016x}"


def _float_bits(value: object) -> str:
    if not isinstance(value, float):
        _fail("DETROIT_SOURCE_VALUE")
    return struct.pack(">d", value).hex()


def _verify_fact_rows(artifact: Json, selected: list[Json]) -> None:
    artifact_id = cast(str, artifact["artifact_id"])
    expected = cast(list[object], artifact["selected_rows"])
    source2: list[Json] = []
    source4: list[Json] = []
    for row_index in range(MAX_SELECTED_ROWS):
        if row_index == len(selected):
            break
        row = selected[row_index]
        if row.get("source_id") == 2:
            source2.append(row)
        elif row.get("source_id") == 4:
            source4.append(row)
    if artifact_id.startswith("fact_census_") and source4:
        _fail("DETROIT_CENSUS_SOURCE_CONFLICT")
    rows = source2 if artifact_id.startswith("fact_census_") else selected
    if artifact_id == "fact_census_housing":
        _compare_housing(rows, expected)
    elif artifact_id == "fact_census_rent":
        _compare_simple(rows, expected, "median_rent_usd", _float_bits)
    elif artifact_id == "fact_census_rent_burden":
        _compare_simple(rows, expected, "household_count", _uint_bits)
    elif artifact_id == "fact_qcew_county_rollup":
        _compare_qcew(rows, expected)
    elif artifact_id == "fact_lodes_commuter_flow":
        _compare_lodes(rows, expected)
    elif artifact_id == "fact_coercive_infrastructure":
        _compare_carceral(rows, expected)


def _expected_by(expected: list[object], key: str) -> dict[object, Json]:
    result: dict[object, Json] = {}
    for row_index in range(MAX_SELECTED_ROWS):
        if row_index == len(expected):
            return result
        row = cast(Json, expected[row_index])
        result[row[key]] = row
    return result


def _compare_simple(
    rows: list[Json],
    expected: list[object],
    field: str,
    bit_fn: Callable[[object], str],
) -> None:
    wanted = _expected_by(expected, "county_id")
    if len(rows) != len(wanted):
        _fail("DETROIT_SOURCE_CARDINALITY")
    for row_index in range(MAX_SELECTED_ROWS):
        if row_index == len(rows):
            return
        row = rows[row_index]
        target = wanted.get(row["county_id"])
        if target is None:
            _fail("DETROIT_SOURCE_VALUE")
        expected_value = target[field]
        value_matches = (
            str(row[field]) == expected_value
            if isinstance(expected_value, str)
            else row[field] == expected_value
        )
        if not value_matches:
            _fail("DETROIT_SOURCE_VALUE")
        computed = bit_fn(row[field])
        if computed != target["bits"]:
            _fail("DETROIT_SOURCE_BITS")


def _compare_housing(rows: list[Json], expected: list[object]) -> None:
    wanted = _expected_by(expected, "county_id")
    if len(rows) != 9:
        _fail("DETROIT_SOURCE_CARDINALITY")
    fields = {1: ("total", "total_bits"), 2: ("owner", "owner_bits"), 3: ("renter", "renter_bits")}
    for row_index in range(9):
        row = rows[row_index]
        target = wanted.get(row["county_id"])
        names = fields.get(cast(int, row["tenure_id"]))
        if (
            target is None
            or names is None
            or row["household_count"] != target[names[0]]
            or _uint_bits(row["household_count"]) != target[names[1]]
        ):
            _fail("DETROIT_SOURCE_VALUE")


def _compare_qcew(rows: list[Json], expected: list[object]) -> None:
    wanted = _expected_by(expected, "county_id")
    if len(rows) != 3:
        _fail("DETROIT_SOURCE_CARDINALITY")
    for row_index in range(3):
        row = rows[row_index]
        target = wanted.get(row["county_id"])
        if target is None or row["disclosure_code"] is not None or row["is_imputed"] is not False:
            _fail("DETROIT_SOURCE_VALUE")
        checks = (
            ("establishments", "establishments_bits", _uint_bits),
            ("employment", "employment_bits", _uint_bits),
            ("total_wages_usd", "total_wages_bits", _float_bits),
        )
        for check_index in range(3):
            field, bits_field, bit_fn = checks[check_index]
            expected_value = target[field]
            value_matches = (
                str(row[field]) == expected_value
                if isinstance(expected_value, str)
                else row[field] == expected_value
            )
            if not value_matches or bit_fn(row[field]) != target[bits_field]:
                _fail("DETROIT_SOURCE_VALUE")


def _compare_lodes(rows: list[Json], expected: list[object]) -> None:
    wanted: dict[tuple[object, object], Json] = {}
    for expected_index in range(MAX_SELECTED_ROWS):
        if expected_index == len(expected):
            break
        row = cast(Json, expected[expected_index])
        wanted[(row["home_id"], row["work_id"])] = row
    if len(rows) != 9:
        _fail("DETROIT_SOURCE_CARDINALITY")
    for row_index in range(9):
        row = rows[row_index]
        target = wanted.get((row["home_county_id"], row["work_county_id"]))
        if (
            target is None
            or row["total_jobs"] != target["total_jobs"]
            or _uint_bits(row["total_jobs"]) != target["bits"]
        ):
            _fail("DETROIT_SOURCE_VALUE")


def _compare_carceral(rows: list[Json], expected: list[object]) -> None:
    wanted: dict[tuple[object, object], Json] = {}
    for expected_index in range(MAX_SELECTED_ROWS):
        if expected_index == len(expected):
            break
        row = cast(Json, expected[expected_index])
        wanted[(row["county_id"], row["coercive_type_id"])] = row
    if len(rows) != 5:
        _fail("DETROIT_SOURCE_CARDINALITY")
    for row_index in range(5):
        row = rows[row_index]
        target = wanted.get((row["county_id"], row["coercive_type_id"]))
        if (
            target is None
            or row["facility_count"] != target["facility_count"]
            or _uint_bits(row["facility_count"]) != target["bits"]
        ):
            _fail("DETROIT_SOURCE_VALUE")


def _verify_dimension_rows(artifact: Json, selected: list[Json]) -> None:
    expected = cast(list[object], artifact["selected_rows"])
    if len(selected) != len(expected):
        _fail("DETROIT_SOURCE_CARDINALITY")
    id_fields = {
        "dim_county": "county_id",
        "dim_state": "state_id",
        "dim_data_source": "source_id",
        "dim_time": "time_id",
        "dim_ownership": "ownership_id",
        "dim_housing_tenure": "tenure_id",
        "dim_race": "race_id",
        "dim_rent_burden": "burden_id",
        "dim_coercive_type": "coercive_type_id",
    }
    key = id_fields[cast(str, artifact["artifact_id"])]
    wanted = _expected_by(expected, key)
    for row_index in range(MAX_SELECTED_ROWS):
        if row_index == len(selected):
            return
        row = selected[row_index]
        target = wanted.get(row[key])
        if target is None:
            _fail("DETROIT_SOURCE_VALUE")
        for field_index in range(MAX_LOCATORS):
            fields = tuple(target)
            if field_index == len(fields):
                break
            field = fields[field_index]
            if str(row[field]) != target[field] and row[field] != target[field]:
                _fail("DETROIT_SOURCE_VALUE")


def _verify_csv_metadata(path: Path, artifact: Json) -> None:
    if (
        artifact["bytes"] != CSV_BYTES
        or artifact["rows"] != CSV_LINES - 1
        or artifact["row_groups"] != 0
        or artifact["schema"] != "county_fips,cz_id,cz_name"
    ):
        _fail("DETROIT_CZ_METADATA")
    try:
        link_stat = path.lstat()
        file_stat = path.stat()
    except OSError as error:
        raise DetroitControlError("DETROIT_SOURCE_MISSING") from error
    if (
        not stat_module.S_ISREG(link_stat.st_mode)
        or not stat_module.S_ISREG(file_stat.st_mode)
        or link_stat.st_size != CSV_BYTES
        or file_stat.st_size != CSV_BYTES
    ):
        _fail("DETROIT_CZ_METADATA")


def _verify_csv(path: Path, artifact: Json, artifact_index: int) -> None:
    _verify_csv_metadata(path, artifact)
    expected = cast(list[object], artifact["selected_rows"])
    selectors = cast(list[object], artifact["selectors"])
    selector = cast(Json, selectors[0])
    wanted: dict[object, object] = {}
    for expected_index in range(MAX_SELECTED_ROWS):
        if expected_index == len(expected):
            break
        row = cast(Json, expected[expected_index])
        wanted[row["county_fips"]] = row["cz_id"]
    found: dict[str, str] = {}
    matched = 0
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for line_index in range(CSV_LINES):
                line = stream.readline(MAX_CSV_LINE_BYTES + 1)
                if (
                    not line
                    or len(line) > MAX_CSV_LINE_BYTES
                    or not line.endswith(b"\n")
                    or b"\r" in line
                ):
                    _fail("DETROIT_CZ_FORMAT")
                digest.update(line)
                if line_index == 0:
                    if line != b"county_fips,cz_id,cz_name\n":
                        _fail("DETROIT_CZ_FORMAT")
                    continue
                matched += _record_csv_match(line, selector, artifact_index, found)
            if stream.readline(1):
                _fail("DETROIT_CZ_FORMAT")
    except UnicodeDecodeError as error:
        raise DetroitControlError("DETROIT_CZ_FORMAT") from error
    except OSError as error:
        raise DetroitControlError("DETROIT_SOURCE_MISSING") from error
    if digest.hexdigest() != artifact["sha256"]:
        _fail("DETROIT_CZ_DIGEST")
    if matched != SELECTOR_COUNTS[artifact_index][0]:
        _fail("DETROIT_SOURCE_CARDINALITY")
    if found != wanted:
        _fail("DETROIT_CZ_MAPPING")


def _record_csv_match(
    line: bytes, selector: Json, artifact_index: int, found: dict[str, str]
) -> int:
    fields = line.decode("utf-8").rstrip("\n").split(",", 2)
    if len(fields) != 3:
        _fail("DETROIT_CZ_FORMAT")
    csv_row: Json = {"county_fips": fields[0], "cz_id": fields[1], "cz_name": fields[2]}
    if not _selector_matches(artifact_index, csv_row, selector):
        return 0
    found[fields[0]] = fields[1]
    return 1


def verify_source_root(root: Path, ledger: Json | None = None) -> tuple[str, ...]:
    """Verify only the closed physical source paths and selected coordinates."""
    checked = load_extraction() if ledger is None else ledger
    artifacts = cast(list[object], checked["artifacts"])
    gaps = cast(list[object], checked["gaps"])
    if len(artifacts) != EXPECTED_ARTIFACTS or len(gaps) != EXPECTED_GAPS:
        _fail("DETROIT_LEDGER_CARDINALITY")
    _validate_artifact_rows(artifacts)
    _validate_gap_rows(gaps)
    reference_only: list[str] = []
    for artifact_index in range(EXPECTED_ARTIFACTS):
        artifact = cast(Json, artifacts[artifact_index])
        mode = artifact["verification_mode"]
        if mode == "REFERENCE_DIGEST_ONLY":
            reference_only.append(cast(str, artifact["artifact_id"]))
            continue
        path = _source_path(root, artifact, artifact_index)
        if mode == "TRACKED_CSV":
            _verify_csv(path, artifact, artifact_index)
            continue
        parquet = _verify_metadata(path, artifact)
        selected = _scan_selected(parquet, artifact, artifact_index)
        if cast(str, artifact["artifact_id"]).startswith("fact_"):
            _verify_fact_rows(artifact, selected)
        else:
            _verify_dimension_rows(artifact, selected)
    if tuple(reference_only) != REFERENCE_ONLY:
        _fail("DETROIT_REFERENCE_ONLY_SET")
    return tuple(reference_only)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--verify-source-root", type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    expected = control_bytes()
    if args.verify_source_root is not None:
        verify_source_root(args.verify_source_root)
    if args.check:
        try:
            actual = CONTROL_PATH.read_bytes()
        except OSError as error:
            raise DetroitControlError("DETROIT_CONTROL_MISSING") from error
        if actual != expected:
            _fail("DETROIT_CONTROL_STALE")
        return 0
    staged = CONTROL_PATH.with_suffix(".json.tmp")
    try:
        staged.write_bytes(expected)
        staged.replace(CONTROL_PATH)
    except OSError as error:
        staged.unlink(missing_ok=True)
        raise DetroitControlError("DETROIT_CONTROL_WRITE") from error
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except DetroitControlError as error:
        raise SystemExit(error.code) from error
