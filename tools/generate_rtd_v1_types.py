#!/usr/bin/env python3
"""Generate closed Python and Rust structural types for the RTD V1 contract."""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

import yaml
from yaml.events import (
    AliasEvent,
    MappingEndEvent,
    MappingStartEvent,
    SequenceEndEvent,
    SequenceStartEvent,
)

REPO_ROOT: Final = Path(__file__).resolve().parent.parent
DEFAULT_CONTRACT: Final = REPO_ROOT / "contracts" / "relational_territory_dossier_v1.yaml"
DEFAULT_PYTHON_OUT: Final = REPO_ROOT / "src" / "babylon" / "contracts" / "rtd_v1_generated.py"
DEFAULT_RUST_OUT: Final = REPO_ROOT / "rust" / "crates" / "babylon-rtd" / "src" / "generated.rs"

RTD_MAX_CONTRACT_BYTES: Final = 262_144
RTD_MAX_YAML_EVENTS: Final = 65_536
RTD_MAX_YAML_DEPTH: Final = 16
RTD_MAX_RECORD_DECLARATIONS: Final = 32
RTD_MAX_ENUM_DECLARATIONS: Final = 64
RTD_MAX_FIELDS_PER_RECORD: Final = 64
RTD_MAX_MEMBERS_PER_ENUM: Final = 256
RTD_MAX_REGISTRY_ROWS: Final = 512
RTD_IDENTITY_CATEGORY_COUNT: Final = 6
RTD_MAX_ENUM_MEMBER_PARTS: Final = 16

CONTRACT_SCHEMA_ERROR: Final = "RTD_CONTRACT_SCHEMA"
CONTRACT_LIMIT_ERROR: Final = "RTD_CONTRACT_LIMIT"

TOP_LEVEL_KEYS: Final = frozenset(
    {
        "schema",
        "schema_version",
        "hash_domain_separator",
        "draft_record",
        "sealed_record",
        "scalar_types",
        "limits",
        "enums",
        "records",
        "canonical_sets",
        "identity_registry",
        "metric_registry",
        "relation_binding_registry",
        "error_registry",
    }
)
IDENTITY_CATEGORIES: Final = (
    "metrics",
    "units",
    "coordinates",
    "native_scales",
    "producers",
    "references",
)

EXPECTED_SCALAR_TYPES: Final = {
    "string": {"json_type": "string", "nfc": True},
    "u16": {"json_type": "unsigned_integer", "minimum": 0, "maximum": 65_535},
    "u64": {
        "json_type": "unsigned_integer",
        "minimum": 0,
        "maximum": 18_446_744_073_709_551_615,
    },
    "digest_hex": {
        "json_type": "string",
        "nfc": True,
        "utf8_bytes": 64,
        "pattern": "^[0-9a-f]{64}$",
    },
    "bits64_hex": {
        "json_type": "string",
        "nfc": True,
        "utf8_bytes": 16,
        "pattern": "^[0-9a-f]{16}$",
        "uint64_encoding": "big_endian_bits",
        "float64_encoding": "finite_ieee754_binary64_bits",
        "normalize_negative_zero": True,
    },
    "vintage": {
        "json_type": "string",
        "nfc": True,
        "minimum_utf8_bytes": 1,
        "maximum_utf8_bytes_limit": "max_vintage_bytes",
    },
    "producer_issue": {
        "json_type": "string",
        "nfc": True,
        "minimum_utf8_bytes": 1,
        "maximum_utf8_bytes_limit": "max_required_producer_bytes",
        "pattern": "^PER-[1-9][0-9]*$",
    },
}

EXPECTED_ENUMS: Final = {
    "AudienceV1": ("ADMIN_MATERIAL", "PLAYER_KNOWLEDGE"),
    "DurabilityV1": ("IN_MEMORY", "COMMITTED"),
    "EvidenceClassV1": ("Observed", "Derived", "Calibrated", "Designed"),
    "StatusV1": ("PRESENT", "ABSENT", "UNKNOWN", "NOT_COMPUTED", "REDACTED"),
    "ValueKindV1": ("UINT64_BITS", "FLOAT64_BITS"),
    "CoverageV1": ("COMPLETE", "PARTIAL", "NOT_APPLICABLE", "UNKNOWN"),
    "MembershipKindV1": (
        "ADMINISTRATIVE",
        "NATIONAL",
        "COMMUTING_ZONE",
        "METROPOLITAN",
        "WEIGHTED_OVERLAP",
    ),
    "FacetFamilyV1": (
        "COMMAND_ADMINISTRATION",
        "PRODUCTION_CIRCULATION",
        "REPRODUCTION_SETTLEMENT_ACCESS",
        "EXTRACTION_ABANDONMENT_CARCERAL",
        "ECOLOGY_CARE",
        "ORGANIZATION_ROOTEDNESS",
    ),
    "DyadKindV1": ("PRESENCE", "MEMBERSHIP", "SOLIDARITY", "COMMAND"),
    "HyperedgeKindV1": ("PUBLIC_RELATION",),
    "FlowKindV1": ("COMMUTER_JOBS", "BORDER_SYNTHESIS"),
    "RelationPayloadModeV1": ("EMPTY", "SINGLE_METRIC_FACET", "IMPLICIT_RELATION"),
    "GapReasonV1": (
        "MISSING_GOVERNED_OMB_DELINEATION",
        "IDENTITY_CONTRACT_PENDING",
        "MISSING_GOVERNED_PRODUCER",
        "REFERENCE_COVERAGE_UNAVAILABLE",
        "PLAYER_BOUNDARY_UNAVAILABLE",
        "PROVENANCE_COORDINATE_CONFLICT",
    ),
    "MetricRepresentationV1": ("FACET", "REFERENCE_FLOW", "DYAD"),
    "AggregationRuleV1": (
        "NONE",
        "PUBLISHED_ROLLUP",
        "LOAD_TIME_SUM",
        "BLOCK_INTERNAL_POINT_ASSIGNMENT",
        "BLOCK_COORDINATE_ASSIGNMENT",
        "EQUAL_AREA_WATER_INTERSECTION",
        "TYPED_RELATION_PROJECTION",
    ),
    "RtdCollectionKindV1": (
        "FOCUS",
        "REFERENCE_DIGESTS",
        "SCALE_MEMBERSHIPS",
        "FACETS",
        "DYADS",
        "HYPEREDGES",
        "FLOWS",
        "GAPS",
        "PROVENANCE",
        "COORDINATES",
        "MEMBER_REFS",
        "PAYLOAD_FACETS",
        "DISPLAY_REFS",
        "PROVENANCE_REFS",
    ),
}

EXPECTED_LIMITS: Final = {
    "max_collection_items": 65_535,
    "max_focus": 64,
    "max_reference_digests": 4_096,
    "max_scale_memberships": 65_535,
    "max_facets": 65_535,
    "max_dyads": 65_535,
    "max_hyperedges": 65_535,
    "max_flows": 65_535,
    "max_gaps": 65_535,
    "max_provenance": 65_535,
    "max_coordinates": 32,
    "max_hyperedge_members": 1_024,
    "max_payload_facets": 256,
    "max_decision_surface_refs": 256,
    "max_provenance_refs": 8_192,
    "max_identity_component_bytes": 256,
    "max_vintage_bytes": 256,
    "max_provenance_locator_bytes": 1_024,
    "max_required_producer_bytes": 64,
    "max_canonical_bytes": 67_108_864,
}

EXPECTED_ERRORS: Final = (
    "RTD_JSON",
    "RTD_JSON_DEPTH",
    "RTD_SCHEMA_VERSION",
    "RTD_UNKNOWN_FIELD",
    "RTD_ENUM",
    "RTD_IDENTITY",
    "RTD_DIGEST",
    "RTD_NON_NFC",
    "RTD_LIMIT_EXCEEDED",
    "RTD_DUPLICATE_KEY",
    "RTD_DANGLING_REF",
    "RTD_STATUS_VALUE",
    "RTD_NATIVE_GRAIN",
    "RTD_UNSUPPORTED_DOWNSCALE",
    "RTD_H3_BEFORE_PER21",
    "RTD_MSA_EVIDENCE",
    "RTD_CANADA_CONTROL",
    "RTD_FORBIDDEN_REDUCTION",
    "RTD_VECTOR_LIMIT",
    "RTD_CANONICAL_SIZE",
)

EXPECTED_RECORD_NAMES: Final = (
    "TypedIdentityV1",
    "ReferenceDigestV1",
    "DimensionCoordinateV1",
    "ScaleMembershipV1",
    "FacetV1",
    "DyadV1",
    "HyperedgeV1",
    "ReferenceFlowV1",
    "GapV1",
    "ProvenanceV1",
    "DecisionSurfaceV1",
    "RtdDossierDraftV1",
    "RelationalTerritoryDossierV1",
)

UNIT_LOCAL_IDS: Final = {
    "JOBS": "jobs",
    "ESTABLISHMENTS": "establishments",
    "USD_CURRENT": "usd-current",
    "HOUSEHOLDS": "households",
    "PERSONS": "persons",
    "FACILITIES": "facilities",
    "FRACTION": "fraction",
    "TYPED_RELATION": "typed-relation",
}
COORDINATE_LOCAL_IDS: Final = {
    "county": "county",
    "naics6": "naics6",
    "ownership": "ownership",
    "home_county": "home-county",
    "work_county": "work-county",
    "source": "source",
    "tenure": "tenure",
    "race": "race",
    "burden": "burden",
    "h3_cell": "h3-cell",
    "coercive_type": "coercive-type",
    "actor": "actor",
    "node": "node",
}
SCALE_LOCAL_IDS: Final = {
    "COUNTY_NAICS6_OWNERSHIP_YEAR": "county-naics6-ownership-year",
    "COUNTY_OWNERSHIP_YEAR": "county-ownership-year",
    "HOME_COUNTY_WORK_COUNTY_YEAR": "home-county-work-county-year",
    "COUNTY_SOURCE_TENURE_TIME_RACE": "county-source-tenure-time-race",
    "COUNTY_SOURCE_TIME_RACE": "county-source-time-race",
    "COUNTY_SOURCE_BURDEN_TIME_RACE": "county-source-burden-time-race",
    "H3_R7_VINTAGE": "h3-r7-vintage",
    "COUNTY_COERCIVE_TYPE_SOURCE": "county-coercive-type-source",
    "ACTOR_NODE_VERIFIED_TICK": "actor-node-verified-tick",
}
ARTIFACTS: Final = (
    "fact_qcew_annual",
    "fact_qcew_county_rollup",
    "fact_lodes_commuter_flow",
    "fact_census_housing",
    "fact_census_rent",
    "fact_census_rent_burden",
    "h3_res7_population",
    "h3_res7_workplace",
    "fact_coercive_infrastructure",
    "h3_res7_land_mask",
)

METRIC_KEYS: Final = (
    "production/qcew-leaf-employment",
    "production/qcew-leaf-establishments",
    "production/qcew-leaf-total-wages-usd",
    "production/qcew-leaf-average-annual-pay-usd",
    "production/qcew-county-employment",
    "production/qcew-county-establishments",
    "production/qcew-county-total-wages-usd",
    "circulation/lodes-county-commuter-total-jobs",
    "reproduction/census-housing-households",
    "reproduction/census-median-rent-usd",
    "reproduction/census-rent-burden-households",
    "reproduction/h3-population-persons",
    "production/h3-workplace-jobs",
    "carceral/facility-count",
    "ecology/h3-land-fraction",
    "rootedness/presence",
    "rootedness/solidarity",
    "rootedness/membership",
)

EXPECTED_METRIC_ROWS: Final = (
    (
        "production/qcew-leaf-employment",
        "FACET",
        "JOBS",
        "UINT64_BITS",
        "COUNTY_NAICS6_OWNERSHIP_YEAR",
        ("county", "naics6", "ownership"),
        ("Observed", "Derived"),
        "NONE",
        "fact_qcew_annual",
        "fact_qcew_annual",
        "ca3825a3d60831479313632073b7fc9a941d57dcf9b8940181c4713b6d442248",
    ),
    (
        "production/qcew-leaf-establishments",
        "FACET",
        "ESTABLISHMENTS",
        "UINT64_BITS",
        "COUNTY_NAICS6_OWNERSHIP_YEAR",
        ("county", "naics6", "ownership"),
        ("Observed", "Derived"),
        "NONE",
        "fact_qcew_annual",
        "fact_qcew_annual",
        "ca3825a3d60831479313632073b7fc9a941d57dcf9b8940181c4713b6d442248",
    ),
    (
        "production/qcew-leaf-total-wages-usd",
        "FACET",
        "USD_CURRENT",
        "FLOAT64_BITS",
        "COUNTY_NAICS6_OWNERSHIP_YEAR",
        ("county", "naics6", "ownership"),
        ("Observed", "Derived"),
        "NONE",
        "fact_qcew_annual",
        "fact_qcew_annual",
        "ca3825a3d60831479313632073b7fc9a941d57dcf9b8940181c4713b6d442248",
    ),
    (
        "production/qcew-leaf-average-annual-pay-usd",
        "FACET",
        "USD_CURRENT",
        "FLOAT64_BITS",
        "COUNTY_NAICS6_OWNERSHIP_YEAR",
        ("county", "naics6", "ownership"),
        ("Observed", "Derived"),
        "NONE",
        "fact_qcew_annual",
        "fact_qcew_annual",
        "ca3825a3d60831479313632073b7fc9a941d57dcf9b8940181c4713b6d442248",
    ),
    (
        "production/qcew-county-employment",
        "FACET",
        "JOBS",
        "UINT64_BITS",
        "COUNTY_OWNERSHIP_YEAR",
        ("county", "ownership"),
        ("Observed", "Derived"),
        "PUBLISHED_ROLLUP",
        "fact_qcew_county_rollup",
        "fact_qcew_county_rollup",
        "34c2bbb935f79b3c8076a97092b004b14cca120e8272b93c35b3ac9dc2721d13",
    ),
    (
        "production/qcew-county-establishments",
        "FACET",
        "ESTABLISHMENTS",
        "UINT64_BITS",
        "COUNTY_OWNERSHIP_YEAR",
        ("county", "ownership"),
        ("Observed", "Derived"),
        "PUBLISHED_ROLLUP",
        "fact_qcew_county_rollup",
        "fact_qcew_county_rollup",
        "34c2bbb935f79b3c8076a97092b004b14cca120e8272b93c35b3ac9dc2721d13",
    ),
    (
        "production/qcew-county-total-wages-usd",
        "FACET",
        "USD_CURRENT",
        "FLOAT64_BITS",
        "COUNTY_OWNERSHIP_YEAR",
        ("county", "ownership"),
        ("Observed", "Derived"),
        "PUBLISHED_ROLLUP",
        "fact_qcew_county_rollup",
        "fact_qcew_county_rollup",
        "34c2bbb935f79b3c8076a97092b004b14cca120e8272b93c35b3ac9dc2721d13",
    ),
    (
        "circulation/lodes-county-commuter-total-jobs",
        "REFERENCE_FLOW",
        "JOBS",
        "UINT64_BITS",
        "HOME_COUNTY_WORK_COUNTY_YEAR",
        ("home_county", "work_county"),
        ("Derived",),
        "LOAD_TIME_SUM",
        "fact_lodes_commuter_flow",
        "fact_lodes_commuter_flow",
        "d3745f8def09cd8c7a38e1870e6ec2c1853e210b777d8e8358cfce36665bd64d",
    ),
    (
        "reproduction/census-housing-households",
        "FACET",
        "HOUSEHOLDS",
        "UINT64_BITS",
        "COUNTY_SOURCE_TENURE_TIME_RACE",
        ("county", "source", "tenure", "race"),
        ("Observed",),
        "NONE",
        "fact_census_housing",
        "fact_census_housing",
        "09ff2d9666b3f5ef267b65cbc77c14e99384f0157b6a4c898ac37df2e67ca59f",
    ),
    (
        "reproduction/census-median-rent-usd",
        "FACET",
        "USD_CURRENT",
        "FLOAT64_BITS",
        "COUNTY_SOURCE_TIME_RACE",
        ("county", "source", "race"),
        ("Observed",),
        "NONE",
        "fact_census_rent",
        "fact_census_rent",
        "4c8cc134ec490ca75961d83485fc97c6bf240b32128e9d0517e00e62d578a99e",
    ),
    (
        "reproduction/census-rent-burden-households",
        "FACET",
        "HOUSEHOLDS",
        "UINT64_BITS",
        "COUNTY_SOURCE_BURDEN_TIME_RACE",
        ("county", "source", "burden", "race"),
        ("Observed",),
        "NONE",
        "fact_census_rent_burden",
        "fact_census_rent_burden",
        "8a42a51c17bf3ebee09f0b0b5145d5c8253c7e3446eec8c75714f9951b20df12",
    ),
    (
        "reproduction/h3-population-persons",
        "FACET",
        "PERSONS",
        "UINT64_BITS",
        "H3_R7_VINTAGE",
        ("h3_cell",),
        ("Derived",),
        "BLOCK_INTERNAL_POINT_ASSIGNMENT",
        "h3_res7_population",
        "h3_res7_population",
        "b096a5891284f0ca55bedae9d1a9092eb8ea9e9e32d32b6ace430a9833b53afc",
    ),
    (
        "production/h3-workplace-jobs",
        "FACET",
        "JOBS",
        "UINT64_BITS",
        "H3_R7_VINTAGE",
        ("h3_cell",),
        ("Derived",),
        "BLOCK_COORDINATE_ASSIGNMENT",
        "h3_res7_workplace",
        "h3_res7_workplace",
        "ea2ce1508f4fe51f1e879b9f4a1daf579c4b00349388b12a85f884a8f49eabb6",
    ),
    (
        "carceral/facility-count",
        "FACET",
        "FACILITIES",
        "UINT64_BITS",
        "COUNTY_COERCIVE_TYPE_SOURCE",
        ("county", "coercive_type", "source"),
        ("Observed",),
        "NONE",
        "fact_coercive_infrastructure",
        "fact_coercive_infrastructure",
        "33e6558d2b438e7aea672021f0e15f743f1ea331ab82407c0805a428b29cf808",
    ),
    (
        "ecology/h3-land-fraction",
        "FACET",
        "FRACTION",
        "FLOAT64_BITS",
        "H3_R7_VINTAGE",
        ("h3_cell",),
        ("Derived",),
        "EQUAL_AREA_WATER_INTERSECTION",
        "h3_res7_land_mask",
        "h3_res7_land_mask",
        "4e6caba297f0111a9ec93d948a83543bb9f7179361fe5dd318bb8a98a5be5194",
    ),
    (
        "rootedness/presence",
        "DYAD",
        "TYPED_RELATION",
        None,
        "ACTOR_NODE_VERIFIED_TICK",
        ("actor", "node"),
        ("Derived",),
        "TYPED_RELATION_PROJECTION",
        "committed typed graph",
        None,
        None,
    ),
    (
        "rootedness/solidarity",
        "DYAD",
        "TYPED_RELATION",
        None,
        "ACTOR_NODE_VERIFIED_TICK",
        ("actor", "node"),
        ("Derived",),
        "TYPED_RELATION_PROJECTION",
        "committed typed graph",
        None,
        None,
    ),
    (
        "rootedness/membership",
        "DYAD",
        "TYPED_RELATION",
        None,
        "ACTOR_NODE_VERIFIED_TICK",
        ("actor", "node"),
        ("Derived",),
        "TYPED_RELATION_PROJECTION",
        "committed typed graph",
        None,
        None,
    ),
)

EXPECTED_BINDING_ROWS: Final = (
    (
        "REFERENCE_FLOW",
        "COMMUTER_JOBS",
        "circulation/lodes-county-commuter-total-jobs",
        "SINGLE_METRIC_FACET",
    ),
    ("REFERENCE_FLOW", "BORDER_SYNTHESIS", None, "EMPTY"),
    ("DYAD", "PRESENCE", "rootedness/presence", "IMPLICIT_RELATION"),
    ("DYAD", "MEMBERSHIP", "rootedness/membership", "IMPLICIT_RELATION"),
    ("DYAD", "SOLIDARITY", "rootedness/solidarity", "IMPLICIT_RELATION"),
    ("DYAD", "COMMAND", None, "EMPTY"),
)


class ContractLoadError(ValueError):
    """A stable refusal raised before code generation."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True, slots=True)
class TypedIdentitySpec:
    domain: str
    authority: str
    local_id: str


@dataclass(frozen=True, slots=True)
class FieldSpec:
    name: str
    type_name: str
    nullable: bool
    bound: str | None
    sort_key: str | None


@dataclass(frozen=True, slots=True)
class RecordSpec:
    name: str
    fields: tuple[FieldSpec, ...]


@dataclass(frozen=True, slots=True)
class ExpandedMetricSpec:
    metric: TypedIdentitySpec
    representation: str
    unit: TypedIdentitySpec
    value_kind: str | None
    native_scale: TypedIdentitySpec
    coordinates: tuple[TypedIdentitySpec, ...]
    evidence_classes: tuple[str, ...]
    aggregation_rule: str
    producer: TypedIdentitySpec
    reference_artifact: TypedIdentitySpec | None
    reference_digest: str | None


@dataclass(frozen=True, slots=True)
class RelationBindingSpec:
    record_family: str
    kind: str
    metric: TypedIdentitySpec | None
    payload_mode: str


@dataclass(frozen=True, slots=True)
class RtdContractSpec:
    schema: str
    schema_version: int
    hash_domain_separator: str
    draft_record: str
    sealed_record: str
    scalar_types: dict[str, dict[str, Any]]
    limits: dict[str, int]
    enums: dict[str, tuple[str, ...]]
    records: set[str]
    record_specs: tuple[RecordSpec, ...]
    canonical_sets: dict[str, str]
    identity_registry: dict[str, dict[str, TypedIdentitySpec]]
    metric_registry: tuple[ExpandedMetricSpec, ...]
    relation_binding_registry: tuple[RelationBindingSpec, ...]
    error_registry: tuple[str, ...]
    contract_path: str
    contract_sha256: str


class StrictSafeLoader(yaml.SafeLoader):
    """SafeLoader variant that refuses a duplicate mapping key."""


def _construct_unique_mapping(
    loader: StrictSafeLoader,
    node: yaml.MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    if len(node.value) > RTD_MAX_REGISTRY_ROWS:
        raise ContractLoadError(CONTRACT_LIMIT_ERROR, "mapping exceeds 512 rows")
    for pair_index in range(RTD_MAX_REGISTRY_ROWS):
        if pair_index >= len(node.value):
            break
        key_node, value_node = node.value[pair_index]
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ContractLoadError(CONTRACT_SCHEMA_ERROR, f"duplicate YAML key {key!r}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


StrictSafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def _schema_error(detail: str) -> ContractLoadError:
    return ContractLoadError(CONTRACT_SCHEMA_ERROR, detail)


def _limit_error(detail: str) -> ContractLoadError:
    return ContractLoadError(CONTRACT_LIMIT_ERROR, detail)


def _read_raw_contract(path: Path) -> bytes:
    try:
        with path.open("rb") as contract_file:
            byte_count = os.fstat(contract_file.fileno()).st_size
            if byte_count > RTD_MAX_CONTRACT_BYTES:
                raise _limit_error("raw YAML exceeds 262144 bytes")
            raw = contract_file.read(RTD_MAX_CONTRACT_BYTES + 1)
    except OSError as error:
        raise _schema_error(f"cannot read contract: {error}") from error
    if len(raw) > RTD_MAX_CONTRACT_BYTES:
        raise _limit_error("raw YAML exceeds 262144 bytes")
    return raw


def _scan_yaml_events(raw: bytes) -> None:
    depth = 0
    try:
        events = iter(yaml.parse(raw, Loader=StrictSafeLoader))
        for event_index in range(RTD_MAX_YAML_EVENTS + 1):
            event = next(events, None)
            if event is None:
                return
            if event_index == RTD_MAX_YAML_EVENTS:
                raise _limit_error("YAML exceeds 65536 events")
            if isinstance(event, AliasEvent):
                raise _schema_error("YAML aliases are forbidden")
            if isinstance(event, (MappingStartEvent, SequenceStartEvent)):
                depth += 1
                if depth > RTD_MAX_YAML_DEPTH:
                    raise _limit_error("YAML nesting depth exceeds 16")
            elif isinstance(event, (MappingEndEvent, SequenceEndEvent)):
                depth -= 1
    except ContractLoadError:
        raise
    except yaml.YAMLError as error:
        raise _schema_error(f"invalid YAML: {error}") from error


def _parse_yaml(raw: bytes) -> dict[str, Any]:
    try:
        loaded = yaml.load(
            raw,
            Loader=StrictSafeLoader,  # noqa: S506 - subclasses yaml.SafeLoader
        )
    except ContractLoadError:
        raise
    except yaml.YAMLError as error:
        raise _schema_error(f"invalid YAML: {error}") from error
    if not isinstance(loaded, dict):
        raise _schema_error("contract root must be a mapping")
    return loaded


def _mapping(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise _schema_error(f"{context} must be a mapping")
    return value


def _sequence(value: Any, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise _schema_error(f"{context} must be a sequence")
    return value


def _closed_keys(mapping: Mapping[str, Any], allowed: frozenset[str], context: str) -> None:
    unknown = set(mapping) - allowed
    missing = allowed - set(mapping)
    if unknown:
        raise _schema_error(f"{context} has unknown keys {sorted(unknown)!r}")
    if missing:
        raise _schema_error(f"{context} lacks keys {sorted(missing)!r}")


def _validate_header(document: Mapping[str, Any]) -> None:
    _closed_keys(document, TOP_LEVEL_KEYS, "contract")
    if document["schema"] != "babylon.relational-territory-dossier":
        raise _schema_error("schema identifier changed")
    if type(document["schema_version"]) is not int or document["schema_version"] != 1:
        raise _schema_error("schema_version must be unsigned integer 1")
    if document["hash_domain_separator"] != "babylon.relational-territory-dossier.v1":
        raise _schema_error("hash domain separator changed")
    if document["draft_record"] != "RtdDossierDraftV1":
        raise _schema_error("draft_record changed")
    if document["sealed_record"] != "RelationalTerritoryDossierV1":
        raise _schema_error("sealed_record changed")


def _validate_limits(raw_limits: Any) -> dict[str, int]:
    limits = _mapping(raw_limits, "limits")
    if len(limits) > RTD_MAX_REGISTRY_ROWS:
        raise _limit_error("limits exceed 512 rows")
    if set(limits) != set(EXPECTED_LIMITS):
        raise _schema_error("limit names changed")
    names = tuple(limits)
    for limit_index in range(RTD_MAX_REGISTRY_ROWS):
        if limit_index >= len(names):
            break
        name = names[limit_index]
        value = limits[name]
        if type(value) is not int or value < 0 or value > 18_446_744_073_709_551_615:
            raise _schema_error(f"limit {name} is not unsigned 64-bit")
        if value != EXPECTED_LIMITS[name]:
            raise _schema_error(f"limit {name} changed")
    return dict(limits)


def _validate_scalar_types(raw_types: Any) -> dict[str, dict[str, Any]]:
    scalar_types = _mapping(raw_types, "scalar_types")
    if len(scalar_types) > RTD_MAX_REGISTRY_ROWS:
        raise _limit_error("scalar type declarations exceed 512 rows")
    if scalar_types != EXPECTED_SCALAR_TYPES:
        raise _schema_error("scalar type declarations changed")
    result: dict[str, dict[str, Any]] = {}
    names = tuple(scalar_types)
    for scalar_index in range(RTD_MAX_REGISTRY_ROWS):
        if scalar_index >= len(names):
            break
        name = names[scalar_index]
        result[name] = dict(_mapping(scalar_types[name], f"scalar type {name}"))
    return result


def _validate_enums(raw_enums: Any) -> dict[str, tuple[str, ...]]:
    enums = _mapping(raw_enums, "enums")
    if len(enums) > RTD_MAX_ENUM_DECLARATIONS:
        raise _limit_error("enum declarations exceed 64")
    if tuple(enums) != tuple(EXPECTED_ENUMS):
        raise _schema_error("enum declarations changed or reordered")
    validated: dict[str, tuple[str, ...]] = {}
    enum_names = tuple(enums)
    for enum_index in range(RTD_MAX_ENUM_DECLARATIONS):
        if enum_index >= len(enum_names):
            break
        name = enum_names[enum_index]
        members = _sequence(enums[name], f"enum {name}")
        if len(members) > RTD_MAX_MEMBERS_PER_ENUM:
            raise _limit_error(f"enum {name} exceeds 256 members")
        if tuple(members) != EXPECTED_ENUMS[name]:
            raise _schema_error(f"enum {name} changed")
        if len(set(members)) != len(members):
            raise _schema_error(f"enum {name} duplicates a member")
        validated[name] = tuple(members)
    return validated


def _parse_field(raw_field: Any, record_name: str) -> FieldSpec:
    field = _mapping(raw_field, f"field in {record_name}")
    allowed = frozenset({"name", "type", "nullable", "bound", "sort_key"})
    unknown = set(field) - allowed
    if unknown:
        raise _schema_error(f"field in {record_name} has unknown keys {sorted(unknown)!r}")
    if "name" not in field or "type" not in field:
        raise _schema_error(f"field in {record_name} lacks name or type")
    name = field["name"]
    type_name = field["type"]
    nullable = field.get("nullable", False)
    bound = field.get("bound")
    sort_key = field.get("sort_key")
    if not isinstance(name, str) or not isinstance(type_name, str) or type(nullable) is not bool:
        raise _schema_error(f"field in {record_name} has invalid scalar metadata")
    if bound is not None and not isinstance(bound, str):
        raise _schema_error(f"field {record_name}.{name} has invalid bound")
    if sort_key is not None and not isinstance(sort_key, str):
        raise _schema_error(f"field {record_name}.{name} has invalid sort key")
    return FieldSpec(name, type_name, nullable, bound, sort_key)


def _validate_field_semantics(field: FieldSpec, known_types: frozenset[str]) -> None:
    base_type = field.type_name
    is_list = base_type.startswith("list[") and base_type.endswith("]")
    if is_list:
        base_type = base_type[5:-1]
        if field.bound is None:
            raise _schema_error(f"container {field.name} lacks a named ceiling")
    elif field.bound is not None and base_type not in {
        "string",
        "vintage",
        "producer_issue",
    }:
        raise _schema_error(f"non-container {field.name} has an invalid bound")
    if base_type not in known_types:
        raise _schema_error(f"field {field.name} has unsupported type {base_type}")
    if field.bound is not None and field.bound not in EXPECTED_LIMITS:
        raise _schema_error(f"field {field.name} names an unknown ceiling")
    if is_list and field.sort_key is None:
        raise _schema_error(f"container {field.name} lacks sort semantics")
    if not is_list and field.sort_key is not None:
        raise _schema_error(f"scalar {field.name} has sort semantics")


def _parse_records(
    raw_records: Any, enums: Mapping[str, tuple[str, ...]]
) -> tuple[RecordSpec, ...]:
    records = _mapping(raw_records, "records")
    if len(records) > RTD_MAX_RECORD_DECLARATIONS:
        raise _limit_error("record declarations exceed 32")
    if tuple(records) != EXPECTED_RECORD_NAMES:
        raise _schema_error("record declarations changed or reordered")
    known_types = (
        frozenset(EXPECTED_SCALAR_TYPES)
        | frozenset({"identity"})
        | frozenset(enums)
        | frozenset(records)
    )
    parsed: list[RecordSpec] = []
    names = tuple(records)
    for record_index in range(RTD_MAX_RECORD_DECLARATIONS):
        if record_index >= len(names):
            break
        name = names[record_index]
        declaration = _mapping(records[name], f"record {name}")
        _closed_keys(declaration, frozenset({"fields"}), f"record {name}")
        fields = _sequence(declaration["fields"], f"record {name} fields")
        if len(fields) > RTD_MAX_FIELDS_PER_RECORD:
            raise _limit_error(f"record {name} exceeds 64 fields")
        parsed_fields: list[FieldSpec] = []
        seen: set[str] = set()
        for field_index in range(RTD_MAX_FIELDS_PER_RECORD):
            if field_index >= len(fields):
                break
            parsed_field = _parse_field(fields[field_index], name)
            if parsed_field.name in seen:
                raise _schema_error(f"record {name} duplicates field {parsed_field.name}")
            seen.add(parsed_field.name)
            _validate_field_semantics(parsed_field, known_types)
            parsed_fields.append(parsed_field)
        parsed.append(RecordSpec(name, tuple(parsed_fields)))
    _validate_identity_field_rules(tuple(parsed))
    _validate_draft_and_sealed(tuple(parsed))
    return tuple(parsed)


def _validate_identity_field_rules(records: tuple[RecordSpec, ...]) -> None:
    for record_index in range(RTD_MAX_RECORD_DECLARATIONS):
        if record_index >= len(records):
            break
        record = records[record_index]
        for field_index in range(RTD_MAX_FIELDS_PER_RECORD):
            if field_index >= len(record.fields):
                break
            field = record.fields[field_index]
            base = field.type_name[5:-1] if field.type_name.startswith("list[") else field.type_name
            identity_name = (
                field.name.endswith("_ref")
                or (record.name != "TypedIdentityV1" and field.name.endswith("_id"))
                or field.name == "actor"
            )
            if identity_name and base != "identity":
                raise _schema_error(f"{record.name}.{field.name} must be a typed identity")


def _validate_draft_and_sealed(records: tuple[RecordSpec, ...]) -> None:
    draft = records[11]
    sealed = records[12]
    draft_names = _record_field_names(draft)
    sealed_names = _record_field_names(sealed)
    if "projection_hash" in draft_names:
        raise _schema_error("draft record contains projection_hash")
    if sealed_names != draft_names + ("projection_hash",):
        raise _schema_error("sealed record must add only projection_hash")


def _record_field_names(record: RecordSpec) -> tuple[str, ...]:
    names: list[str] = []
    for field_index in range(RTD_MAX_FIELDS_PER_RECORD):
        if field_index >= len(record.fields):
            break
        names.append(record.fields[field_index].name)
    return tuple(names)


def _expected_identity(category: str, key: str) -> TypedIdentitySpec:
    if category == "metrics" and key in METRIC_KEYS:
        return TypedIdentitySpec("metric", "babylon.rtd.v1", key)
    if category == "units" and key in UNIT_LOCAL_IDS:
        return TypedIdentitySpec("unit", "babylon.rtd.v1", UNIT_LOCAL_IDS[key])
    if category == "coordinates" and key in COORDINATE_LOCAL_IDS:
        return TypedIdentitySpec("dimension", "babylon.rtd.v1", COORDINATE_LOCAL_IDS[key])
    if category == "native_scales" and key in SCALE_LOCAL_IDS:
        return TypedIdentitySpec("native-scale", "babylon.rtd.v1", SCALE_LOCAL_IDS[key])
    if category == "producers" and key in ARTIFACTS:
        return TypedIdentitySpec("producer", "babylon.data.v7", key)
    if category == "producers" and key == "committed typed graph":
        return TypedIdentitySpec(
            "producer", "babylon.engine", "typed-graph-relations-at-verified-tick"
        )
    if category == "references" and key in ARTIFACTS:
        return TypedIdentitySpec("reference-artifact", "babylon.data.v7", key)
    raise _schema_error(f"identity registry has unknown {category} key {key}")


def _parse_identity(raw: Any, context: str) -> TypedIdentitySpec:
    row = _mapping(raw, context)
    _closed_keys(row, frozenset({"domain", "authority", "local_id"}), context)
    values = (row["domain"], row["authority"], row["local_id"])
    if not isinstance(values[0], str) or not values[0]:
        raise _schema_error(f"{context} has an invalid identity component")
    if not isinstance(values[1], str) or not values[1]:
        raise _schema_error(f"{context} has an invalid identity component")
    if not isinstance(values[2], str) or not values[2]:
        raise _schema_error(f"{context} has an invalid identity component")
    return TypedIdentitySpec(values[0], values[1], values[2])


def _parse_identity_registry(raw_registry: Any) -> dict[str, dict[str, TypedIdentitySpec]]:
    registry = _mapping(raw_registry, "identity_registry")
    if tuple(registry) != IDENTITY_CATEGORIES:
        raise _schema_error("identity registry categories changed or reordered")
    result: dict[str, dict[str, TypedIdentitySpec]] = {}
    seen_identities: set[TypedIdentitySpec] = set()
    for category_index in range(RTD_IDENTITY_CATEGORY_COUNT):
        category = IDENTITY_CATEGORIES[category_index]
        rows = _mapping(registry[category], f"identity_registry.{category}")
        if len(rows) > RTD_MAX_REGISTRY_ROWS:
            raise _limit_error(f"identity_registry.{category} exceeds 512 rows")
        parsed_rows: dict[str, TypedIdentitySpec] = {}
        keys = tuple(rows)
        for row_index in range(RTD_MAX_REGISTRY_ROWS):
            if row_index >= len(keys):
                break
            key = keys[row_index]
            if not isinstance(key, str) or key in parsed_rows:
                raise _schema_error(f"identity_registry.{category} duplicates a key")
            identity = _parse_identity(rows[key], f"identity_registry.{category}.{key}")
            if identity != _expected_identity(category, key):
                raise _schema_error(f"identity_registry.{category}.{key} changed")
            if identity in seen_identities:
                raise _schema_error("two registry keys map to the same typed identity")
            parsed_rows[key] = identity
            seen_identities.add(identity)
        result[category] = parsed_rows
    _validate_identity_registry_counts(result)
    return result


def _validate_identity_registry_counts(
    registry: Mapping[str, Mapping[str, TypedIdentitySpec]],
) -> None:
    expected_counts = (18, 8, 13, 9, 11, 10)
    for category_index in range(RTD_IDENTITY_CATEGORY_COUNT):
        category = IDENTITY_CATEGORIES[category_index]
        if len(registry[category]) != expected_counts[category_index]:
            raise _schema_error(f"identity_registry.{category} has missing or extra rows")


def _metric_signature(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        row.get("metric"),
        row.get("representation"),
        row.get("unit"),
        row.get("value_kind"),
        row.get("native_scale"),
        tuple(_sequence(row.get("coordinates"), "metric coordinates")),
        tuple(_sequence(row.get("evidence_classes"), "metric evidence_classes")),
        row.get("aggregation_rule"),
        row.get("producer"),
        row.get("reference"),
        row.get("reference_digest"),
    )


def _identity_lookup(
    registry: Mapping[str, Mapping[str, TypedIdentitySpec]],
    category: str,
    key: Any,
) -> TypedIdentitySpec:
    if not isinstance(key, str) or key not in registry[category]:
        raise _schema_error(f"metric refers to unknown {category} key {key!r}")
    return registry[category][key]


def _expand_metric(
    row: Mapping[str, Any],
    registry: Mapping[str, Mapping[str, TypedIdentitySpec]],
) -> ExpandedMetricSpec:
    coordinate_keys = _sequence(row["coordinates"], "metric coordinates")
    if len(coordinate_keys) > RTD_MAX_REGISTRY_ROWS:
        raise _limit_error("metric coordinates exceed 512 rows")
    coordinates: list[TypedIdentitySpec] = []
    for coordinate_index in range(RTD_MAX_REGISTRY_ROWS):
        if coordinate_index >= len(coordinate_keys):
            break
        coordinates.append(
            _identity_lookup(registry, "coordinates", coordinate_keys[coordinate_index])
        )
    reference_key = row["reference"]
    reference = (
        None if reference_key is None else _identity_lookup(registry, "references", reference_key)
    )
    return ExpandedMetricSpec(
        metric=_identity_lookup(registry, "metrics", row["metric"]),
        representation=row["representation"],
        unit=_identity_lookup(registry, "units", row["unit"]),
        value_kind=row["value_kind"],
        native_scale=_identity_lookup(registry, "native_scales", row["native_scale"]),
        coordinates=tuple(coordinates),
        evidence_classes=tuple(row["evidence_classes"]),
        aggregation_rule=row["aggregation_rule"],
        producer=_identity_lookup(registry, "producers", row["producer"]),
        reference_artifact=reference,
        reference_digest=row["reference_digest"],
    )


def _parse_metric_registry(
    raw_registry: Any,
    identity_registry: Mapping[str, Mapping[str, TypedIdentitySpec]],
) -> tuple[ExpandedMetricSpec, ...]:
    rows = _sequence(raw_registry, "metric_registry")
    if len(rows) > RTD_MAX_REGISTRY_ROWS:
        raise _limit_error("metric_registry exceeds 512 rows")
    if len(rows) != 18:
        raise _schema_error("metric_registry must contain exactly 18 rows")
    allowed = frozenset(
        {
            "metric",
            "representation",
            "unit",
            "value_kind",
            "native_scale",
            "coordinates",
            "evidence_classes",
            "aggregation_rule",
            "producer",
            "reference",
            "reference_digest",
        }
    )
    expanded: list[ExpandedMetricSpec] = []
    seen: set[str] = set()
    for row_index in range(RTD_MAX_REGISTRY_ROWS):
        if row_index >= len(rows):
            break
        row = _mapping(rows[row_index], "metric row")
        _closed_keys(row, allowed, "metric row")
        signature = _metric_signature(row)
        if signature != EXPECTED_METRIC_ROWS[row_index]:
            raise _schema_error(f"metric row {row_index} changed or is reordered")
        metric_key = row["metric"]
        if not isinstance(metric_key, str) or metric_key in seen:
            raise _schema_error("metric_registry duplicates a metric")
        seen.add(metric_key)
        expanded.append(_expand_metric(row, identity_registry))
    return tuple(expanded)


def _parse_relation_bindings(
    raw_registry: Any,
    identity_registry: Mapping[str, Mapping[str, TypedIdentitySpec]],
) -> tuple[RelationBindingSpec, ...]:
    rows = _sequence(raw_registry, "relation_binding_registry")
    if len(rows) > RTD_MAX_REGISTRY_ROWS:
        raise _limit_error("relation_binding_registry exceeds 512 rows")
    if len(rows) != 6:
        raise _schema_error("relation_binding_registry must contain exactly six rows")
    allowed = frozenset({"record_family", "kind", "metric", "payload_mode"})
    result: list[RelationBindingSpec] = []
    seen: set[tuple[str, str]] = set()
    for row_index in range(RTD_MAX_REGISTRY_ROWS):
        if row_index >= len(rows):
            break
        row = _mapping(rows[row_index], "relation binding row")
        _closed_keys(row, allowed, "relation binding row")
        signature = (row["record_family"], row["kind"], row["metric"], row["payload_mode"])
        if signature != EXPECTED_BINDING_ROWS[row_index]:
            raise _schema_error(f"relation binding row {row_index} changed or is reordered")
        binding_key = (row["record_family"], row["kind"])
        if binding_key in seen:
            raise _schema_error("relation_binding_registry duplicates a relation kind")
        seen.add(binding_key)
        metric = (
            None
            if row["metric"] is None
            else _identity_lookup(identity_registry, "metrics", row["metric"])
        )
        result.append(
            RelationBindingSpec(binding_key[0], binding_key[1], metric, row["payload_mode"])
        )
    return tuple(result)


def _parse_error_registry(raw_registry: Any) -> tuple[str, ...]:
    errors = _sequence(raw_registry, "error_registry")
    if len(errors) > RTD_MAX_REGISTRY_ROWS:
        raise _limit_error("error_registry exceeds 512 rows")
    if tuple(errors) != EXPECTED_ERRORS or len(set(errors)) != len(errors):
        raise _schema_error("error_registry changed, duplicates, or is reordered")
    return tuple(errors)


def _parse_canonical_sets(raw_sets: Any, records: tuple[RecordSpec, ...]) -> dict[str, str]:
    sets = _mapping(raw_sets, "canonical_sets")
    if len(sets) > RTD_MAX_REGISTRY_ROWS:
        raise _limit_error("canonical_sets exceeds 512 rows")
    result: dict[str, str] = {}
    keys = tuple(sets)
    for row_index in range(RTD_MAX_REGISTRY_ROWS):
        if row_index >= len(keys):
            break
        path = keys[row_index]
        sort_key = sets[path]
        if not isinstance(path, str) or not isinstance(sort_key, str):
            raise _schema_error("canonical set rows must be string mappings")
        result[path] = sort_key
    declared: dict[str, str] = {}
    for record_index in range(RTD_MAX_RECORD_DECLARATIONS):
        if record_index >= len(records):
            break
        record = records[record_index]
        for field_index in range(RTD_MAX_FIELDS_PER_RECORD):
            if field_index >= len(record.fields):
                break
            field = record.fields[field_index]
            if field.type_name.startswith("list["):
                declared[f"{record.name}.{field.name}"] = field.sort_key or ""
    if result != declared:
        raise _schema_error("canonical_sets contradict record sort declarations")
    return result


def _contract_relative_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.name


def load_contract(path: Path) -> RtdContractSpec:
    """Load and validate the bounded, closed RTD V1 generator contract."""
    raw = _read_raw_contract(path)
    _scan_yaml_events(raw)
    document = _parse_yaml(raw)
    _validate_header(document)
    scalar_types = _validate_scalar_types(document["scalar_types"])
    limits = _validate_limits(document["limits"])
    enums = _validate_enums(document["enums"])
    records = _parse_records(document["records"], enums)
    canonical_sets = _parse_canonical_sets(document["canonical_sets"], records)
    identities = _parse_identity_registry(document["identity_registry"])
    metrics = _parse_metric_registry(document["metric_registry"], identities)
    bindings = _parse_relation_bindings(document["relation_binding_registry"], identities)
    errors = _parse_error_registry(document["error_registry"])
    return RtdContractSpec(
        schema=document["schema"],
        schema_version=document["schema_version"],
        hash_domain_separator=document["hash_domain_separator"],
        draft_record=document["draft_record"],
        sealed_record=document["sealed_record"],
        scalar_types=scalar_types,
        limits=limits,
        enums=enums,
        records=set(EXPECTED_RECORD_NAMES),
        record_specs=records,
        canonical_sets=canonical_sets,
        identity_registry=identities,
        metric_registry=metrics,
        relation_binding_registry=bindings,
        error_registry=errors,
        contract_path=_contract_relative_path(path),
        contract_sha256=hashlib.sha256(raw).hexdigest(),
    )


def _pascal_case(member: str) -> str:
    parts = member.lower().split("_")
    if len(parts) > RTD_MAX_ENUM_MEMBER_PARTS:
        raise _schema_error("enum member exceeds 16 underscore-delimited parts")
    rendered: list[str] = []
    for part_index in range(RTD_MAX_ENUM_MEMBER_PARTS):
        if part_index >= len(parts):
            break
        part = parts[part_index]
        rendered.append(part[:1].upper() + part[1:])
    return "".join(rendered)


def _python_type(field: FieldSpec) -> str:
    type_name = field.type_name
    is_list = type_name.startswith("list[")
    base = type_name[5:-1] if is_list else type_name
    scalar = {
        "string": "str",
        "vintage": "str",
        "producer_issue": "str",
        "digest_hex": "str",
        "bits64_hex": "str",
        "u16": "int",
        "u64": "int",
        "identity": "TypedIdentityV1",
    }.get(base, base)
    rendered = f"list[{scalar}]" if is_list else scalar
    return f"{rendered} | None" if field.nullable else rendered


def _rust_type(field: FieldSpec) -> str:
    type_name = field.type_name
    is_list = type_name.startswith("list[")
    base = type_name[5:-1] if is_list else type_name
    scalar = {
        "string": "String",
        "vintage": "String",
        "producer_issue": "String",
        "digest_hex": "String",
        "bits64_hex": "String",
        "u16": "u16",
        "u64": "u64",
        "identity": "TypedIdentityV1",
    }.get(base, base)
    rendered = f"Vec<{scalar}>" if is_list else scalar
    return f"Option<{rendered}>" if field.nullable else rendered


def _python_identity(identity: TypedIdentitySpec) -> str:
    return f"TypedIdentityV1(domain={identity.domain!r}, authority={identity.authority!r}, local_id={identity.local_id!r})"


def _append_rust_identity(
    lines: list[str],
    prefix: str,
    identity: TypedIdentitySpec,
    suffix: str,
) -> None:
    indent = prefix[: len(prefix) - len(prefix.lstrip())]
    lines.extend(
        (
            f"{prefix}TypedIdentityLiteralV1 {{",
            f'{indent}    domain: "{identity.domain}",',
            f'{indent}    authority: "{identity.authority}",',
            f'{indent}    local_id: "{identity.local_id}",',
            f"{indent}}}{suffix}",
        )
    )


def _python_header(spec: RtdContractSpec) -> list[str]:
    return [
        f"# Generated from {spec.contract_path}; sha256={spec.contract_sha256}",
        "# fmt: off",
        "from __future__ import annotations",
        "",
        "from enum import StrEnum",
        "from types import MappingProxyType",
        "",
        "from pydantic import BaseModel, ConfigDict, Field",
        "",
        "",
    ]


def _render_python_enums(spec: RtdContractSpec, lines: list[str]) -> None:
    names = tuple(spec.enums)
    for enum_index in range(RTD_MAX_ENUM_DECLARATIONS):
        if enum_index >= len(names):
            break
        name = names[enum_index]
        lines.append(f"class {name}(StrEnum):")
        members = spec.enums[name]
        for member_index in range(RTD_MAX_MEMBERS_PER_ENUM):
            if member_index >= len(members):
                break
            member = members[member_index]
            lines.append(f"    {member} = {member!r}")
        lines.extend(("", ""))


def _render_python_records(spec: RtdContractSpec, lines: list[str]) -> None:
    for record_index in range(RTD_MAX_RECORD_DECLARATIONS):
        if record_index >= len(spec.record_specs):
            break
        record = spec.record_specs[record_index]
        lines.extend(
            (
                f"class {record.name}(BaseModel):",
                '    model_config = ConfigDict(frozen=True, extra="forbid")',
                "",
            )
        )
        for field_index in range(RTD_MAX_FIELDS_PER_RECORD):
            if field_index >= len(record.fields):
                break
            field = record.fields[field_index]
            rendered_field = f"    {field.name}: {_python_type(field)}"
            if field.name == "schema":
                rendered_field = (
                    f'    schema_: {_python_type(field)} = Field(alias="schema", '
                    'serialization_alias="schema")'
                )
            lines.append(rendered_field)
        lines.extend(("", ""))


def _render_python_registry_types(lines: list[str]) -> None:
    lines.extend(
        (
            "class RtdIdentityRegistryRowV1(BaseModel):",
            '    model_config = ConfigDict(frozen=True, extra="forbid")',
            "",
            "    category: str",
            "    symbolic_name: str",
            "    identity: TypedIdentityV1",
            "",
            "class RtdMetricRegistryRowV1(BaseModel):",
            '    model_config = ConfigDict(frozen=True, extra="forbid")',
            "",
            "    metric: TypedIdentityV1",
            "    representation: MetricRepresentationV1",
            "    unit: TypedIdentityV1",
            "    value_kind: ValueKindV1 | None",
            "    native_scale: TypedIdentityV1",
            "    coordinates: tuple[TypedIdentityV1, ...]",
            "    evidence_classes: tuple[EvidenceClassV1, ...]",
            "    aggregation_rule: AggregationRuleV1",
            "    producer: TypedIdentityV1",
            "    reference_artifact: TypedIdentityV1 | None",
            "    reference_digest: str | None",
            "",
            "class RtdRelationBindingRegistryRowV1(BaseModel):",
            '    model_config = ConfigDict(frozen=True, extra="forbid")',
            "",
            "    record_family: str",
            "    kind: str",
            "    metric: TypedIdentityV1 | None",
            "    payload_mode: RelationPayloadModeV1",
            "",
        )
    )


def _render_python_constants(spec: RtdContractSpec, lines: list[str]) -> None:
    lines.append(f"RTD_V1_SCHEMA_ID = {spec.schema!r}")
    lines.append("RTD_V1_LIMITS = MappingProxyType({")
    limit_names = tuple(spec.limits)
    for limit_index in range(RTD_MAX_REGISTRY_ROWS):
        if limit_index >= len(limit_names):
            break
        name = limit_names[limit_index]
        lines.append(f"    {name!r}: {spec.limits[name]},")
    lines.extend(("})", f"RTD_V1_ERROR_REGISTRY = {spec.error_registry!r}", ""))


def _render_python_identities(spec: RtdContractSpec, lines: list[str]) -> None:
    lines.append("RTD_V1_IDENTITY_REGISTRY = (")
    for category_index in range(RTD_IDENTITY_CATEGORY_COUNT):
        category = IDENTITY_CATEGORIES[category_index]
        rows = spec.identity_registry[category]
        keys = tuple(rows)
        for row_index in range(RTD_MAX_REGISTRY_ROWS):
            if row_index >= len(keys):
                break
            key = keys[row_index]
            lines.append(
                f"    RtdIdentityRegistryRowV1(category={category!r}, symbolic_name={key!r}, identity={_python_identity(rows[key])}),"
            )
    lines.extend((")", ""))


def _python_tuple(items: Sequence[str]) -> str:
    if not items:
        return "()"
    return "(" + ", ".join(items) + ",)"


def _python_identity_tuple(items: tuple[TypedIdentitySpec, ...]) -> str:
    rendered: list[str] = []
    for item_index in range(RTD_MAX_REGISTRY_ROWS):
        if item_index >= len(items):
            break
        rendered.append(_python_identity(items[item_index]))
    return _python_tuple(tuple(rendered))


def _python_evidence_tuple(items: tuple[str, ...]) -> str:
    rendered: list[str] = []
    for item_index in range(RTD_MAX_MEMBERS_PER_ENUM):
        if item_index >= len(items):
            break
        rendered.append(f"EvidenceClassV1.{items[item_index]}")
    return _python_tuple(tuple(rendered))


def _render_python_metrics(spec: RtdContractSpec, lines: list[str]) -> None:
    lines.append("RTD_V1_METRIC_REGISTRY = (")
    for row_index in range(RTD_MAX_REGISTRY_ROWS):
        if row_index >= len(spec.metric_registry):
            break
        row = spec.metric_registry[row_index]
        coordinates = _python_identity_tuple(row.coordinates)
        evidence = _python_evidence_tuple(row.evidence_classes)
        value_kind = "None" if row.value_kind is None else f"ValueKindV1.{row.value_kind}"
        reference = (
            "None" if row.reference_artifact is None else _python_identity(row.reference_artifact)
        )
        lines.extend(
            (
                "    RtdMetricRegistryRowV1(",
                f"        metric={_python_identity(row.metric)},",
                f"        representation=MetricRepresentationV1.{row.representation},",
                f"        unit={_python_identity(row.unit)},",
                f"        value_kind={value_kind},",
                f"        native_scale={_python_identity(row.native_scale)},",
                f"        coordinates={coordinates},",
                f"        evidence_classes={evidence},",
                f"        aggregation_rule=AggregationRuleV1.{row.aggregation_rule},",
                f"        producer={_python_identity(row.producer)},",
                f"        reference_artifact={reference},",
                f"        reference_digest={row.reference_digest!r},",
                "    ),",
            )
        )
    lines.extend((")", ""))


def _render_python_bindings(spec: RtdContractSpec, lines: list[str]) -> None:
    lines.append("RTD_V1_RELATION_BINDING_REGISTRY = (")
    for row_index in range(RTD_MAX_REGISTRY_ROWS):
        if row_index >= len(spec.relation_binding_registry):
            break
        row = spec.relation_binding_registry[row_index]
        metric = "None" if row.metric is None else _python_identity(row.metric)
        lines.append(
            f"    RtdRelationBindingRegistryRowV1(record_family={row.record_family!r}, kind={row.kind!r}, metric={metric}, payload_mode=RelationPayloadModeV1.{row.payload_mode}),"
        )
    lines.extend((")", ""))


def render_python(spec: RtdContractSpec) -> str:
    """Render the complete generated Python source deterministically."""
    lines = _python_header(spec)
    _render_python_enums(spec, lines)
    _render_python_records(spec, lines)
    _render_python_registry_types(lines)
    _render_python_constants(spec, lines)
    _render_python_identities(spec, lines)
    _render_python_metrics(spec, lines)
    _render_python_bindings(spec, lines)
    lines.extend(("# fmt: on", ""))
    return "\n".join(lines)


def _rust_header(spec: RtdContractSpec) -> list[str]:
    return [
        f"// Generated from {spec.contract_path}; sha256={spec.contract_sha256}",
        "",
        "use serde::Deserialize;",
        "",
    ]


def _render_rust_enums(spec: RtdContractSpec, lines: list[str]) -> None:
    names = tuple(spec.enums)
    for enum_index in range(RTD_MAX_ENUM_DECLARATIONS):
        if enum_index >= len(names):
            break
        name = names[enum_index]
        lines.extend(
            ("#[derive(Clone, Copy, Debug, PartialEq, Eq, Deserialize)]", f"pub enum {name} {{")
        )
        members = spec.enums[name]
        for member_index in range(RTD_MAX_MEMBERS_PER_ENUM):
            if member_index >= len(members):
                break
            member = members[member_index]
            lines.extend((f'    #[serde(rename = "{member}")]', f"    {_pascal_case(member)},"))
        lines.extend(("}", ""))


def _render_rust_records(spec: RtdContractSpec, lines: list[str]) -> None:
    for record_index in range(RTD_MAX_RECORD_DECLARATIONS):
        if record_index >= len(spec.record_specs):
            break
        record = spec.record_specs[record_index]
        lines.extend(
            (
                "#[derive(Clone, Debug, PartialEq, Eq, Deserialize)]",
                "#[serde(deny_unknown_fields)]",
                f"pub struct {record.name} {{",
            )
        )
        for field_index in range(RTD_MAX_FIELDS_PER_RECORD):
            if field_index >= len(record.fields):
                break
            field = record.fields[field_index]
            lines.append(f"    pub {field.name}: {_rust_type(field)},")
        lines.extend(("}", ""))


def _render_rust_registry_types(lines: list[str]) -> None:
    lines.extend(
        (
            "#[derive(Clone, Copy, Debug, PartialEq, Eq)]",
            "pub struct TypedIdentityLiteralV1 {",
            "    pub domain: &'static str,",
            "    pub authority: &'static str,",
            "    pub local_id: &'static str,",
            "}",
            "",
            "#[derive(Clone, Copy, Debug, PartialEq, Eq)]",
            "pub struct RtdIdentityRegistryRowV1 {",
            "    pub category: &'static str,",
            "    pub symbolic_name: &'static str,",
            "    pub identity: TypedIdentityLiteralV1,",
            "}",
            "",
            "#[derive(Clone, Copy, Debug, PartialEq, Eq)]",
            "pub struct RtdMetricRegistryRowV1 {",
            "    pub metric: TypedIdentityLiteralV1,",
            "    pub representation: MetricRepresentationV1,",
            "    pub unit: TypedIdentityLiteralV1,",
            "    pub value_kind: Option<ValueKindV1>,",
            "    pub native_scale: TypedIdentityLiteralV1,",
            "    pub coordinates: &'static [TypedIdentityLiteralV1],",
            "    pub evidence_classes: &'static [EvidenceClassV1],",
            "    pub aggregation_rule: AggregationRuleV1,",
            "    pub producer: TypedIdentityLiteralV1,",
            "    pub reference_artifact: Option<TypedIdentityLiteralV1>,",
            "    pub reference_digest: Option<&'static str>,",
            "}",
            "",
            "#[derive(Clone, Copy, Debug, PartialEq, Eq)]",
            "pub struct RtdRelationBindingRegistryRowV1 {",
            "    pub record_family: &'static str,",
            "    pub kind: &'static str,",
            "    pub metric: Option<TypedIdentityLiteralV1>,",
            "    pub payload_mode: RelationPayloadModeV1,",
            "}",
            "",
        )
    )


def _rust_constant_name(name: str) -> str:
    return "RTD_" + name.upper()


def _render_rust_constants(spec: RtdContractSpec, lines: list[str]) -> None:
    lines.append(f'pub const RTD_V1_SCHEMA_ID: &str = "{spec.schema}";')
    limit_names = tuple(spec.limits)
    for limit_index in range(RTD_MAX_REGISTRY_ROWS):
        if limit_index >= len(limit_names):
            break
        name = limit_names[limit_index]
        lines.append(f"pub const {_rust_constant_name(name)}: u64 = {spec.limits[name]};")
    lines.append("")
    lines.append("pub const RTD_V1_LIMITS: &[(&str, u64)] = &[")
    for limit_index in range(RTD_MAX_REGISTRY_ROWS):
        if limit_index >= len(limit_names):
            break
        name = limit_names[limit_index]
        limit_row = f'    ("{name}", {_rust_constant_name(name)}),'
        if len(name) < 27:
            lines.append(limit_row)
        else:
            lines.extend(
                (
                    "    (",
                    f'        "{name}",',
                    f"        {_rust_constant_name(name)},",
                    "    ),",
                )
            )
    lines.extend(("];", ""))
    lines.append("pub const RTD_V1_ERROR_REGISTRY: &[&str] = &[")
    for error_index in range(RTD_MAX_REGISTRY_ROWS):
        if error_index >= len(spec.error_registry):
            break
        lines.append(f'    "{spec.error_registry[error_index]}",')
    lines.extend(("];", ""))


def _render_rust_identities(spec: RtdContractSpec, lines: list[str]) -> None:
    lines.append("pub const RTD_V1_IDENTITY_REGISTRY: &[RtdIdentityRegistryRowV1] = &[")
    for category_index in range(RTD_IDENTITY_CATEGORY_COUNT):
        category = IDENTITY_CATEGORIES[category_index]
        rows = spec.identity_registry[category]
        keys = tuple(rows)
        for row_index in range(RTD_MAX_REGISTRY_ROWS):
            if row_index >= len(keys):
                break
            key = keys[row_index]
            lines.extend(
                (
                    "    RtdIdentityRegistryRowV1 {",
                    f'        category: "{category}",',
                    f'        symbolic_name: "{key}",',
                )
            )
            _append_rust_identity(lines, "        identity: ", rows[key], ",")
            lines.append("    },")
    lines.extend(("];", ""))


def _append_rust_identity_slice(
    lines: list[str],
    prefix: str,
    items: tuple[TypedIdentitySpec, ...],
) -> None:
    if len(items) == 1:
        identity = items[0]
        indent = prefix[: len(prefix) - len(prefix.lstrip())]
        lines.extend(
            (
                f"{prefix}&[TypedIdentityLiteralV1 {{",
                f'{indent}    domain: "{identity.domain}",',
                f'{indent}    authority: "{identity.authority}",',
                f'{indent}    local_id: "{identity.local_id}",',
                f"{indent}}}],",
            )
        )
        return
    lines.append(f"{prefix}&[")
    for item_index in range(RTD_MAX_REGISTRY_ROWS):
        if item_index >= len(items):
            break
        _append_rust_identity(lines, "            ", items[item_index], ",")
    lines.append("        ],")


def _rust_evidence_slice(items: tuple[str, ...]) -> str:
    rendered: list[str] = []
    for item_index in range(RTD_MAX_MEMBERS_PER_ENUM):
        if item_index >= len(items):
            break
        rendered.append(f"EvidenceClassV1::{_pascal_case(items[item_index])}")
    return "&[" + ", ".join(rendered) + "]"


def _render_rust_metrics(spec: RtdContractSpec, lines: list[str]) -> None:
    lines.append("pub const RTD_V1_METRIC_REGISTRY: &[RtdMetricRegistryRowV1] = &[")
    for row_index in range(RTD_MAX_REGISTRY_ROWS):
        if row_index >= len(spec.metric_registry):
            break
        row = spec.metric_registry[row_index]
        value_kind = (
            "None"
            if row.value_kind is None
            else f"Some(ValueKindV1::{_pascal_case(row.value_kind)})"
        )
        digest = "None" if row.reference_digest is None else f'Some("{row.reference_digest}")'
        lines.append("    RtdMetricRegistryRowV1 {")
        _append_rust_identity(lines, "        metric: ", row.metric, ",")
        lines.append(
            f"        representation: MetricRepresentationV1::{_pascal_case(row.representation)},"
        )
        _append_rust_identity(lines, "        unit: ", row.unit, ",")
        lines.append(f"        value_kind: {value_kind},")
        _append_rust_identity(lines, "        native_scale: ", row.native_scale, ",")
        _append_rust_identity_slice(lines, "        coordinates: ", row.coordinates)
        lines.append(f"        evidence_classes: {_rust_evidence_slice(row.evidence_classes)},")
        lines.append(
            f"        aggregation_rule: AggregationRuleV1::{_pascal_case(row.aggregation_rule)},"
        )
        _append_rust_identity(lines, "        producer: ", row.producer, ",")
        if row.reference_artifact is None:
            lines.append("        reference_artifact: None,")
        else:
            _append_rust_identity(
                lines,
                "        reference_artifact: Some(",
                row.reference_artifact,
                "),",
            )
        lines.extend((f"        reference_digest: {digest},", "    },"))
    lines.extend(("];", ""))


def _render_rust_bindings(spec: RtdContractSpec, lines: list[str]) -> None:
    lines.append(
        "pub const RTD_V1_RELATION_BINDING_REGISTRY: &[RtdRelationBindingRegistryRowV1] = &["
    )
    for row_index in range(RTD_MAX_REGISTRY_ROWS):
        if row_index >= len(spec.relation_binding_registry):
            break
        row = spec.relation_binding_registry[row_index]
        lines.extend(
            (
                "    RtdRelationBindingRegistryRowV1 {",
                f'        record_family: "{row.record_family}",',
                f'        kind: "{row.kind}",',
            )
        )
        if row.metric is None:
            lines.append("        metric: None,")
        else:
            _append_rust_identity(lines, "        metric: Some(", row.metric, "),")
        lines.extend(
            (
                f"        payload_mode: RelationPayloadModeV1::{_pascal_case(row.payload_mode)},",
                "    },",
            )
        )
    lines.extend(("];", ""))


def render_rust(spec: RtdContractSpec) -> str:
    """Render the complete generated Rust source deterministically."""
    lines = _rust_header(spec)
    _render_rust_enums(spec, lines)
    _render_rust_records(spec, lines)
    _render_rust_registry_types(lines)
    _render_rust_constants(spec, lines)
    _render_rust_identities(spec, lines)
    _render_rust_metrics(spec, lines)
    _render_rust_bindings(spec, lines)
    return "\n".join(lines)


def _check_output(path: Path, expected: str) -> bool:
    try:
        return path.read_bytes() == expected.encode("utf-8")
    except OSError:
        return False


def _stage_output(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as output_file:
            output_file.write(content.encode("utf-8"))
            output_file.flush()
            os.fsync(output_file.fileno())
    except OSError:
        temporary_path.unlink(missing_ok=True)
        raise
    return temporary_path


def _write_outputs(
    python_path: Path, python_source: str, rust_path: Path, rust_source: str
) -> None:
    staged_python = _stage_output(python_path, python_source)
    try:
        staged_rust = _stage_output(rust_path, rust_source)
    except OSError:
        staged_python.unlink(missing_ok=True)
        raise
    try:
        os.replace(staged_python, python_path)
        os.replace(staged_rust, rust_path)
    finally:
        staged_python.unlink(missing_ok=True)
        staged_rust.unlink(missing_ok=True)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--python-out", type=Path, default=DEFAULT_PYTHON_OUT)
    parser.add_argument("--rust-out", type=Path, default=DEFAULT_RUST_OUT)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Generate both outputs, or compare exact UTF-8 bytes in check mode."""
    args = _parse_args(argv)
    try:
        spec = load_contract(args.contract)
        python_source = render_python(spec)
        rust_source = render_rust(spec)
        if args.check:
            python_current = _check_output(args.python_out, python_source)
            rust_current = _check_output(args.rust_out, rust_source)
            if not python_current or not rust_current:
                print("RTD V1 generated sources are stale", file=sys.stderr)
                return 1
            print("RTD V1 generated sources are current")
            return 0
        _write_outputs(args.python_out, python_source, args.rust_out, rust_source)
    except (ContractLoadError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 2
    print(f"Wrote {args.python_out} and {args.rust_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
