#!/usr/bin/env python3
"""Build and verify the bounded Detroit-Windsor RTD V1 control fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Final, NoReturn, cast

import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]
import yaml

from babylon.config.defines import GameDefines, canonical_defines_hash
from babylon.contracts.relational_territory_dossier_v1 import parse_draft, seal_draft
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
COUNTY_IDS: Final = (1281, 1294, 1313)
COUNTY_FIPS: Final = ("26099", "26125", "26163")

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
        result[key] = loader.construct_object(value_node, deep=deep)
    _fail("DETROIT_LEDGER_LIMIT")


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
        if row["verification_mode"] == "REFERENCE_DIGEST_ONLY":
            reference_only.append(artifact_id)
        selectors = _sequence(row["selectors"], MAX_SELECTORS, "DETROIT_SELECTOR_LIMIT")
        _validate_unique_selectors(selectors)
        _sequence(row["selected_rows"], MAX_SELECTED_ROWS, "DETROIT_SELECTED_ROW_LIMIT")
        _sequence(row["provenance_locators"], MAX_LOCATORS, "DETROIT_LOCATOR_LIMIT")
        contracts = _sequence(row["metric_contracts"], MAX_SELECTORS, "DETROIT_METRIC_LIMIT")
        _validate_metric_contracts(contracts)
    if tuple(ordered_ids) != ARTIFACT_IDS:
        _fail("DETROIT_ARTIFACT_ALIAS")
    if tuple(reference_only) != REFERENCE_ONLY:
        _fail("DETROIT_REFERENCE_ONLY_SET")


def _validate_unique_selectors(selectors: list[object]) -> None:
    seen: set[bytes] = set()
    for selector_index in range(MAX_SELECTORS):
        if selector_index == len(selectors):
            return
        selector = _mapping(selectors[selector_index], "DETROIT_SELECTOR_SHAPE")
        key = json.dumps(selector, sort_keys=True, separators=(",", ":")).encode()
        if key in seen:
            _fail("DETROIT_SELECTOR_DUPLICATE")
        seen.add(key)


def _validate_metric_contracts(contracts: list[object]) -> None:
    if len(RTD_V1_METRIC_REGISTRY) != EXPECTED_METRICS:
        _fail("DETROIT_METRIC_REGISTRY")
    registry = {}
    for row_index in range(EXPECTED_METRICS):
        row = RTD_V1_METRIC_REGISTRY[row_index]
        registry[row.metric.local_id] = row
    for contract_index in range(MAX_SELECTORS):
        if contract_index == len(contracts):
            return
        contract = _mapping(contracts[contract_index], "DETROIT_METRIC_SHAPE")
        _exact_fields(
            contract,
            {"local_id", "producer", "aggregation_rule", "reference_artifact", "digest"},
            "DETROIT_METRIC_UNKNOWN_FIELD",
        )
        local_id = contract["local_id"]
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


def _validate_gap_rows(rows: list[object]) -> None:
    seen: set[str] = set()
    expected = {"suffix", "requested", "status", "reason", "producer", "provenance_artifacts"}
    optional = expected | {"note"}
    for gap_index in range(EXPECTED_GAPS):
        row = _mapping(rows[gap_index], "DETROIT_GAP_SHAPE")
        if set(row) not in (expected, optional):
            _fail("DETROIT_GAP_UNKNOWN_FIELD")
        suffix = row["suffix"]
        if not isinstance(suffix, str) or suffix in seen:
            _fail("DETROIT_GAP_DUPLICATE")
        seen.add(suffix)
        _sequence(row["provenance_artifacts"], MAX_LOCATORS, "DETROIT_LOCATOR_LIMIT")


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
            locator_parts.append(str(locators[locator_index]))
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
            "production/qcew-county-establishments",
            "establishments",
            "UINT64_BITS",
        ),
        ("employment", "production/qcew-county-employment", "jobs", "UINT64_BITS"),
        ("total-wages", "production/qcew-county-total-wages-usd", "usd-current", "FLOAT64_BITS"),
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
                "circulation/lodes-county-commuter-total-jobs",
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
                "carceral/facility-count",
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


def _source_path(root: Path, artifact: Json) -> Path:
    relative = cast(str, artifact["relative_path"])
    return ROOT / relative if artifact["verification_mode"] == "TRACKED_CSV" else root / relative


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


def _wanted_row(artifact_id: str, row: Mapping[str, object]) -> bool:
    county = row.get("county_id")
    if artifact_id == "fact_qcew_county_rollup":
        return county in COUNTY_IDS and row.get("time_id") == 28 and row.get("ownership_id") == 1
    if artifact_id == "fact_lodes_commuter_flow":
        return (
            row.get("home_county_id") in COUNTY_IDS
            and row.get("work_county_id") in COUNTY_IDS
            and row.get("time_id") == 24
        )
    if artifact_id.startswith("fact_census_"):
        base = county in COUNTY_IDS and row.get("time_id") == 27 and row.get("race_id") == 1
        if artifact_id == "fact_census_housing":
            return base and row.get("source_id") in (2, 4) and row.get("tenure_id") in (1, 2, 3)
        if artifact_id == "fact_census_rent_burden":
            return base and row.get("source_id") in (2, 4) and row.get("burden_id") == 9
        return base and row.get("source_id") in (2, 4)
    if artifact_id == "fact_coercive_infrastructure":
        return (
            county in COUNTY_IDS
            and row.get("source_id") == 11
            and row.get("coercive_type_id") in (2, 3)
        )
    selected_ids = {
        "dim_county": ("county_id", COUNTY_IDS),
        "dim_state": ("state_id", (23,)),
        "dim_data_source": ("source_id", (2, 4, 11)),
        "dim_time": ("time_id", (24, 27, 28)),
        "dim_ownership": ("ownership_id", (1,)),
        "dim_housing_tenure": ("tenure_id", (1, 2, 3)),
        "dim_race": ("race_id", (1,)),
        "dim_rent_burden": ("burden_id", (9,)),
        "dim_coercive_type": ("coercive_type_id", (2, 3)),
    }
    key, values = selected_ids[artifact_id]
    return row.get(key) in values


def _scan_selected(parquet: pq.ParquetFile, artifact_id: str) -> list[Json]:
    selected: list[Json] = []
    batches = parquet.iter_batches(row_groups=[0], batch_size=SOURCE_BATCH_SIZE)
    for _batch_index in range(MAX_SOURCE_BATCHES):
        try:
            batch = next(batches)
        except StopIteration:
            return selected
        rows = batch.to_pylist()
        for row_index in range(SOURCE_BATCH_SIZE):
            if row_index == len(rows):
                break
            row = cast(Json, rows[row_index])
            if _wanted_row(artifact_id, row):
                if len(selected) == MAX_SELECTED_ROWS:
                    _fail("DETROIT_SELECTED_ROW_LIMIT")
                selected.append(row)
    try:
        next(batches)
    except StopIteration:
        return selected
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


def _verify_csv(path: Path, artifact: Json) -> None:
    raw = path.read_bytes()
    if len(raw) != artifact["bytes"] or hashlib.sha256(raw).hexdigest() != artifact["sha256"]:
        _fail("DETROIT_CZ_DIGEST")
    lines = raw.splitlines(keepends=True)
    if len(lines) != CSV_LINES or lines[0] != b"county_fips,cz_id,cz_name\n":
        _fail("DETROIT_CZ_FORMAT")
    expected = cast(list[object], artifact["selected_rows"])
    wanted: dict[object, object] = {}
    for expected_index in range(MAX_SELECTED_ROWS):
        if expected_index == len(expected):
            break
        row = cast(Json, expected[expected_index])
        wanted[row["county_fips"]] = row["cz_id"]
    found: dict[str, str] = {}
    for line_index in range(CSV_LINES):
        if not lines[line_index].endswith(b"\n"):
            _fail("DETROIT_CZ_FORMAT")
        if line_index == 0:
            continue
        fields = lines[line_index].decode("utf-8").rstrip("\n").split(",")
        if fields[0] in wanted:
            found[fields[0]] = fields[1]
    if found != wanted:
        _fail("DETROIT_CZ_MAPPING")


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
        path = _source_path(root, artifact)
        if mode == "TRACKED_CSV":
            _verify_csv(path, artifact)
            continue
        parquet = _verify_metadata(path, artifact)
        selected = _scan_selected(parquet, cast(str, artifact["artifact_id"]))
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
