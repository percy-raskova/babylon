"""Behavioral contract for the closed, non-live practice schema."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from itertools import islice
from pathlib import Path
from typing import Any, Never
from unittest.mock import MagicMock

import pytest
import yaml
from yaml.events import AliasEvent, CollectionEndEvent, CollectionStartEvent

ROOT = Path(__file__).parents[3]
CONTRACT_PATH = ROOT / "contracts" / "practice_contract_v1.yaml"
ADR_PATH = ROOT / "ai" / "decisions" / "ADR227_practice_contract_groundwork.yaml"
INDEX_PATH = ROOT / "ai" / "decisions" / "index.yaml"

MAX_SOURCE_BYTES = 262_144
MAX_YAML_EVENTS = 65_536
MAX_DEPTH = 16
MAX_RECORDS = 64
MAX_ENUMS = 64
MAX_FIELDS = 64
MAX_ENUM_MEMBERS = 256
MAX_ERROR_CODES = 256

PRACTICE_IDS = {"ORGANIZE": 1, "AGITATE": 2, "MUTUAL_AID": 3}
VERB_STEMS = {"MOBILIZE": 1, "AID": 2}
VERB_MODES = {"CANVASS": 1, "AGITATE": 2}
AUTHORITY_KINDS = {"PLAYER_SEAT": 1, "DETERMINISTIC_POLICY": 2}
TARGET_DOMAINS = {"SOCIAL_CLASS": 1}
REJECTION_CODES = {
    "PRACTICE_UNWIRED": 1,
    "PRACTICE_STALE_CONTENT": 2,
    "PRACTICE_COST_MISMATCH": 3,
    "PRACTICE_AUTHORITY_UNREGISTERED": 4,
    "PRACTICE_ACTOR_MISMATCH": 5,
    "PRACTICE_DUPLICATE_ACTOR": 6,
    "PRACTICE_BATCH_LIMIT": 7,
    "PRACTICE_TICK_MISMATCH": 8,
    "PRACTICE_BUDGET_INSUFFICIENT": 9,
    "PRACTICE_TARGET_INELIGIBLE": 10,
    "PRACTICE_PENDING_DUPLICATE": 11,
}
ACTIVATION_BLOCKERS = {
    "GATE3_COMMITTED_ENVELOPE": 1,
    "GATE5_PENDING_INPUT": 2,
    "PER30_ORDERS_INVENTORY": 3,
    "PER31_FREIGHT_REALIZATION": 4,
}
CONTRACT_ERRORS = {
    "PRACTICE_DOMAIN": 1,
    "PRACTICE_SCHEMA_VERSION": 2,
    "PRACTICE_ENUM_CODE": 3,
    "PRACTICE_LENGTH": 5,
    "PRACTICE_TRUNCATED": 6,
    "PRACTICE_TRAILING_BYTES": 7,
    "PRACTICE_BOOLEAN": 9,
    "PRACTICE_PARAMETER": 10,
    "PRACTICE_PARAMETER_LIMIT": 11,
    "PRACTICE_PARAMETER_LENGTH": 12,
    "PRACTICE_EVIDENCE_LIMIT": 13,
    "PRACTICE_EVIDENCE_ORDER": 14,
    "PRACTICE_EVIDENCE_DUPLICATE": 15,
    "PRACTICE_TICK_OVERFLOW": 16,
    "PRACTICE_TICK_MISMATCH": 17,
    "PRACTICE_AUTHORITY_REGISTRY_LIMIT": 18,
    "PRACTICE_AUTHORITY_REGISTRY_ORDER": 19,
    "PRACTICE_AUTHORITY_REGISTRY_DUPLICATE": 20,
    "PRACTICE_AUTHORITY_UNREGISTERED": 21,
    "PRACTICE_ACTOR_MISMATCH": 22,
    "PRACTICE_AUTHORITY_CONTENT_MISMATCH": 23,
    "PRACTICE_QUOTE_CONTENT_MISMATCH": 24,
    "PRACTICE_QUOTE_COST_MISMATCH": 25,
    "PRACTICE_BATCH_LIMIT": 26,
    "PRACTICE_DUPLICATE_ACTOR": 27,
    "PRACTICE_BUDGET_NONFINITE": 28,
    "PRACTICE_BUDGET_NEGATIVE": 29,
    "PRACTICE_BUDGET_FRACTIONAL": 30,
    "PRACTICE_BUDGET_RANGE": 31,
    "PRACTICE_BUDGET_ROUNDTRIP": 32,
    "PRACTICE_BUDGET_INSUFFICIENT": 33,
    "PRACTICE_BUDGET_ARITHMETIC": 34,
    "PRACTICE_FOOTPRINT_LIMIT": 35,
    "PRACTICE_FOOTPRINT_ORDER": 36,
    "PRACTICE_FOOTPRINT_DUPLICATE": 37,
    "PRACTICE_FOOTPRINT_SOURCE": 38,
    "PRACTICE_FOOTPRINT_STRENGTH_NONFINITE": 39,
    "PRACTICE_FOOTPRINT_STRENGTH_NONPOSITIVE": 40,
    "PRACTICE_TOPOLOGY_ORGANIZATION_LIMIT": 41,
    "PRACTICE_TOPOLOGY_ORGANIZATION_ORDER": 42,
    "PRACTICE_TOPOLOGY_ORGANIZATION_DUPLICATE": 43,
    "PRACTICE_TOPOLOGY_BUDGET_MISSING": 44,
    "PRACTICE_TOPOLOGY_EDGE_ORDER": 45,
    "PRACTICE_TOPOLOGY_EDGE_DUPLICATE": 46,
}
REJECTION_ALIASES = {
    16: "PRACTICE_TICK_MISMATCH",
    17: "PRACTICE_TICK_MISMATCH",
    21: "PRACTICE_AUTHORITY_UNREGISTERED",
    22: "PRACTICE_ACTOR_MISMATCH",
    23: "PRACTICE_AUTHORITY_UNREGISTERED",
    24: "PRACTICE_STALE_CONTENT",
    25: "PRACTICE_COST_MISMATCH",
    26: "PRACTICE_BATCH_LIMIT",
    27: "PRACTICE_DUPLICATE_ACTOR",
    33: "PRACTICE_BUDGET_INSUFFICIENT",
}


class PracticeSchemaError(StrEnum):
    SourceBytes = "SourceBytes"
    EventLimit = "EventLimit"
    Alias = "Alias"
    DuplicateKey = "DuplicateKey"
    Depth = "Depth"
    UnknownKey = "UnknownKey"
    MissingKey = "MissingKey"
    DuplicateCode = "DuplicateCode"
    MissingCode = "MissingCode"
    InvalidLimit = "InvalidLimit"
    CollectionLimit = "CollectionLimit"
    FieldOrder = "FieldOrder"
    MappingMismatch = "MappingMismatch"


class PracticeSchemaViolation(ValueError):
    def __init__(self, error: PracticeSchemaError) -> None:
        self.error = error
        super().__init__(error.value)


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(
    loader: _UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False
) -> dict[object, object]:
    result: dict[object, object] = {}
    for key_node, value_node in islice(node.value, MAX_YAML_EVENTS + 1):
        if not isinstance(key_node, yaml.ScalarNode) or key_node.tag not in {
            "tag:yaml.org,2002:int",
            "tag:yaml.org,2002:str",
        }:
            _refuse(PracticeSchemaError.MappingMismatch)
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise PracticeSchemaViolation(PracticeSchemaError.DuplicateKey)
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def _refuse(error: PracticeSchemaError) -> Never:
    raise PracticeSchemaViolation(error)


def _bounded_items(value: dict[str, Any], limit: int) -> list[tuple[str, Any]]:
    items = list(islice(value.items(), limit + 1))
    if len(items) > limit:
        _refuse(PracticeSchemaError.CollectionLimit)
    return items


def _bounded_list(value: list[Any], limit: int) -> list[Any]:
    items = list(islice(value, limit + 1))
    if len(items) > limit:
        _refuse(PracticeSchemaError.CollectionLimit)
    return items


def _mapping(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        _refuse(PracticeSchemaError.MappingMismatch)
    for key, _ in _bounded_items(value, MAX_YAML_EVENTS):
        if not isinstance(key, str):
            _refuse(PracticeSchemaError.MappingMismatch)
    return value


def _keys(value: dict[str, Any], expected: set[str]) -> None:
    if value.keys() - expected:
        _refuse(PracticeSchemaError.UnknownKey)
    if expected - value.keys():
        _refuse(PracticeSchemaError.MissingKey)


def _scan_yaml(source: bytes) -> None:
    if len(source) > MAX_SOURCE_BYTES:
        _refuse(PracticeSchemaError.SourceBytes)
    depth = 0
    try:
        for event_count, event in enumerate(
            islice(yaml.parse(source), MAX_YAML_EVENTS + 1), start=1
        ):
            if event_count > MAX_YAML_EVENTS:
                _refuse(PracticeSchemaError.EventLimit)
            if isinstance(event, AliasEvent):
                _refuse(PracticeSchemaError.Alias)
            if isinstance(event, CollectionStartEvent):
                depth += 1
                if depth > MAX_DEPTH:
                    _refuse(PracticeSchemaError.Depth)
            elif isinstance(event, CollectionEndEvent):
                depth -= 1
    except yaml.YAMLError:
        _refuse(PracticeSchemaError.MappingMismatch)


def _validate_code_table(value: object, expected: dict[str, int], *, limit: int) -> dict[str, int]:
    table = _mapping(value)
    items = _bounded_items(table, limit)
    if not all(type(code) is int and 0 < code <= 65_535 for _, code in items):
        _refuse(PracticeSchemaError.MappingMismatch)
    codes = [code for _, code in items]
    if len(codes) != len(set(codes)):
        _refuse(PracticeSchemaError.DuplicateCode)
    missing = set(expected.values()) - set(codes)
    if missing:
        _refuse(PracticeSchemaError.MissingCode)
    if dict(items) != expected:
        _refuse(PracticeSchemaError.MappingMismatch)
    return dict(items)


EXPECTED_ENUMS = {
    "PracticeIdV1": ("u8", PRACTICE_IDS),
    "VerbStemV1": ("u8", VERB_STEMS),
    "VerbModeV1": ("u8", VERB_MODES),
    "PracticeAuthorityKindV1": ("u8", AUTHORITY_KINDS),
    "PracticeTargetDomainV1": ("u8", TARGET_DOMAINS),
    "PracticeRejectionCodeV1": ("u16", REJECTION_CODES),
    "PracticeActivationBlockerV1": ("u8", ACTIVATION_BLOCKERS),
}

EXPECTED_SCALAR_TYPES = {
    "u8": {"width_bits": 8, "unsigned": True},
    "u16": {"width_bits": 16, "unsigned": True},
    "u32": {"width_bits": 32, "unsigned": True},
    "u64": {"width_bits": 64, "unsigned": True},
    "digest32": {"width_bytes": 32, "encoding": "raw_bytes"},
    "bool": {"width_bits": 8, "valid_values": [0, 1]},
    "f64_bits_u64": {"width_bits": 64, "encoding": "ieee754_binary64_bits"},
    "bytes": {"encoding": "raw_bytes"},
}
EXPECTED_PARSER_BOUNDS = {
    "max_source_bytes": MAX_SOURCE_BYTES,
    "max_yaml_events": MAX_YAML_EVENTS,
    "max_depth": MAX_DEPTH,
    "max_record_declarations": MAX_RECORDS,
    "max_enum_declarations": MAX_ENUMS,
    "max_fields_per_record": MAX_FIELDS,
    "max_members_per_enum": MAX_ENUM_MEMBERS,
    "max_error_codes": MAX_ERROR_CODES,
}
EXPECTED_LIMITS = {
    "max_parameters": 16,
    "max_parameter_value_bytes": 256,
    "max_parameter_bytes": 256,
    "max_evidence_digests": 64,
    "max_intent_canonical_bytes": 16_384,
    "max_policy_authority_pairs": 4_096,
    "max_intents_per_resolve_tick": 4_096,
    "max_organizations": 4_096,
    "max_org_solidarity_edges_per_org": 256,
    "max_jsonl_source_bytes": 2_097_152,
    "max_jsonl_cases": 512,
    "max_jsonl_line_bytes": 65_536,
    "max_jsonl_case_id_bytes": 128,
    "max_json_depth": 32,
}
EXPECTED_WIRE_LAYOUTS = {
    "PracticeInputAuthorityV1": [
        "ascii_domain",
        "zero_u8",
        "schema_version_u16_be",
        "authority_kind_u8",
        "actor_org_id_u64_be",
        "producer_content_digest_32",
    ],
    "PracticeIntentV1": [
        "ascii_domain",
        "zero_u8",
        "schema_version_u16_be",
        "submit_after_tick_u64_be",
        "resolve_tick_u64_be",
        "actor_org_id_u64_be",
        "practice_id_u8",
        "target_domain_u8",
        "target_node_id_u64_be",
        "quoted_content_digest_32",
        "quoted_action_budget_cost_u32_be",
        "parameters_count_u16_be",
        "length_framed_parameters",
        "evidence_count_u16_be",
        "evidence_digests_lexicographic",
    ],
    "OrganizationBudgetDeltaV1": [
        "ascii_domain",
        "zero_u8",
        "schema_version_u16_be",
        "tick_u64_be",
        "actor_node_id_u64_be",
        "pre_action_world_hash_32",
        "budget_before_u32_be",
        "governed_cost_u32_be",
        "footprint_count_u32_be",
        "raw_credit_u32_be",
        "credited_credit_u32_be",
        "ceiling_bound_u8",
        "budget_after_u32_be",
    ],
    "PracticeSubmissionRejectionV1": [
        "schema_version_u16_be",
        "submitted_bytes_digest_32",
        "reason_code_u16_be",
        "last_committed_tick_u64_be",
        "content_digest_32",
    ],
    "PracticeParameterV1": [
        "key_u8",
        "value_kind_u8",
        "value_length_u16_be",
        "value_bytes",
    ],
}


EXPECTED_RECORD_FIELDS = {
    "PracticeInputAuthorityV1": [
        "schema_version",
        "authority_kind",
        "actor_org_id",
        "producer_content_digest",
    ],
    "PracticeParameterV1": ["key_u8", "value_kind_u8", "value_length_u16", "value_bytes"],
    "PracticeIntentV1": [
        "schema_version",
        "submit_after_tick",
        "resolve_tick",
        "actor_org_id",
        "practice_id",
        "target_domain",
        "target_node_id",
        "quoted_content_digest",
        "quoted_action_budget_cost",
        "parameters",
        "evidence_digests",
    ],
    "PolicyAuthorityPairV1": ["producer_content_digest", "actor_org_id"],
    "PracticeAuthorityContextV1": [
        "player_org_id",
        "player_gateway_content_digest",
        "policy_authorities",
    ],
    "PracticeQuoteContextV1": ["last_committed_tick", "content_digest", "budget_terms"],
    "SolidarityFootprintEdgeV1": [
        "source_org_node_id_u64",
        "target_domain_u8",
        "target_class_node_id_u64",
        "strength_f64_bits_u64",
    ],
    "OrganizationPracticeTopologyEdgeV1": [
        "target_domain",
        "target_class_node_id_u64",
    ],
    "OrganizationPracticeTopologyRowV1": [
        "node_id_u64",
        "active_bool",
        "action_budget_storage_f64_bits_u64",
        "edges",
    ],
    "OrganizationPracticeTopologyV1": ["organizations"],
    "OrganizationBudgetDeltaV1": [
        "schema_version",
        "tick",
        "actor_node_id",
        "pre_action_world_hash",
        "budget_before",
        "governed_cost",
        "footprint_count",
        "raw_credit",
        "credited_credit",
        "ceiling_bound",
        "budget_after",
    ],
    "PracticeSubmissionRejectionV1": [
        "schema_version",
        "submitted_bytes_digest",
        "reason_code",
        "last_committed_tick",
        "content_digest",
    ],
    "PracticeBudgetTermsV1": [
        "initial",
        "weekly_credit_cap",
        "storage_ceiling",
        "organize_cost",
        "agitate_cost",
        "mutual_aid_cost",
    ],
}

EXPECTED_RECORD_TYPES = {
    "PracticeInputAuthorityV1": [
        "u16",
        "PracticeAuthorityKindV1",
        "u64",
        "digest32",
    ],
    "PracticeParameterV1": ["u8", "u8", "u16", "bytes"],
    "PracticeIntentV1": [
        "u16",
        "u64",
        "u64",
        "u64",
        "PracticeIdV1",
        "PracticeTargetDomainV1",
        "u64",
        "digest32",
        "u32",
        "sequence[PracticeParameterV1]",
        "sequence[digest32]",
    ],
    "PolicyAuthorityPairV1": ["digest32", "u64"],
    "PracticeAuthorityContextV1": [
        "u64",
        "digest32",
        "sequence[PolicyAuthorityPairV1]",
    ],
    "PracticeQuoteContextV1": ["u64", "digest32", "PracticeBudgetTermsV1"],
    "SolidarityFootprintEdgeV1": [
        "u64",
        "PracticeTargetDomainV1",
        "u64",
        "f64_bits_u64",
    ],
    "OrganizationPracticeTopologyEdgeV1": ["PracticeTargetDomainV1", "u64"],
    "OrganizationPracticeTopologyRowV1": [
        "u64",
        "bool",
        "optional[f64_bits_u64]",
        "sequence[OrganizationPracticeTopologyEdgeV1]",
    ],
    "OrganizationPracticeTopologyV1": ["sequence[OrganizationPracticeTopologyRowV1]"],
    "OrganizationBudgetDeltaV1": [
        "u16",
        "u64",
        "u64",
        "digest32",
        "u32",
        "u32",
        "u32",
        "u32",
        "u32",
        "bool",
        "u32",
    ],
    "PracticeSubmissionRejectionV1": [
        "u16",
        "digest32",
        "PracticeRejectionCodeV1",
        "u64",
        "digest32",
    ],
    "PracticeBudgetTermsV1": ["u32", "u32", "u32", "u32", "u32", "u32"],
}

EXPECTED_RECORD_BYTE_ORDERS = {
    "PracticeInputAuthorityV1": [
        "big_endian",
        "single_byte",
        "big_endian",
        "raw_bytes",
    ],
    "PracticeParameterV1": ["single_byte", "single_byte", "big_endian", "raw_bytes"],
    "PracticeIntentV1": [
        "big_endian",
        "big_endian",
        "big_endian",
        "big_endian",
        "single_byte",
        "single_byte",
        "big_endian",
        "raw_bytes",
        "big_endian",
        "length_framed_big_endian",
        "length_framed_big_endian",
    ],
    "PolicyAuthorityPairV1": ["raw_bytes", "big_endian"],
    "PracticeAuthorityContextV1": ["big_endian", "raw_bytes", "sorted_unique"],
    "PracticeQuoteContextV1": [
        "big_endian",
        "raw_bytes",
        "declared_record_order",
    ],
    "SolidarityFootprintEdgeV1": [
        "big_endian",
        "single_byte",
        "big_endian",
        "big_endian",
    ],
    "OrganizationPracticeTopologyEdgeV1": ["single_byte", "big_endian"],
    "OrganizationPracticeTopologyRowV1": [
        "big_endian",
        "single_byte",
        "optional_tag_then_big_endian",
        "sorted_unique",
    ],
    "OrganizationPracticeTopologyV1": ["sorted_unique"],
    "OrganizationBudgetDeltaV1": [
        "big_endian",
        "big_endian",
        "big_endian",
        "raw_bytes",
        "big_endian",
        "big_endian",
        "big_endian",
        "big_endian",
        "big_endian",
        "single_byte",
        "big_endian",
    ],
    "PracticeSubmissionRejectionV1": [
        "big_endian",
        "raw_bytes",
        "big_endian",
        "big_endian",
        "raw_bytes",
    ],
    "PracticeBudgetTermsV1": [
        "big_endian",
        "big_endian",
        "big_endian",
        "big_endian",
        "big_endian",
        "big_endian",
    ],
}


@dataclass(frozen=True)
class PracticeContractSpec:
    raw: dict[str, Any]
    practice_ids: dict[str, int]

    def display_label(self, practice: str) -> str:
        return self._mapping_row(practice)["display_label"]

    def machine_mapping(self, practice: str) -> tuple[str, str | None]:
        row = self._mapping_row(practice)
        return row["machine_stem"], row["machine_mode"]

    def _mapping_row(self, practice: str) -> dict[str, Any]:
        for row in _bounded_list(self.raw["practice_mappings"], 3):
            if row["practice"] == practice:
                return row
        raise KeyError(practice)


def _load_unique_yaml(source: bytes) -> dict[str, Any]:
    loader = _UniqueKeyLoader(source)
    try:
        try:
            loaded = loader.get_single_data()
        except yaml.YAMLError:
            _refuse(PracticeSchemaError.MappingMismatch)
    finally:
        loader.dispose()
    return _mapping(loaded)


def _read_source(path: Path) -> bytes:
    with path.open("rb") as source_file:
        source = source_file.read(MAX_SOURCE_BYTES + 1)
    if len(source) > MAX_SOURCE_BYTES:
        _refuse(PracticeSchemaError.SourceBytes)
    return source


def _validate_header(root: dict[str, Any]) -> None:
    expected_keys = {
        "schema",
        "schema_version",
        "evidence_class",
        "purpose",
        "domain_terminator_hex",
        "wire_layouts",
        "scalar_types",
        "parser_bounds",
        "limits",
        "enums",
        "contract_errors",
        "submission_rejection_aliases",
        "practice_mappings",
        "activation_blockers",
        "validation_laws",
        "records",
        "budget_terms",
        "topology",
    }
    _bounded_items(root, MAX_FIELDS)
    _keys(root, expected_keys)
    if (
        root["schema"] != "babylon.practice-contract"
        or root["schema_version"] != 1
        or root["evidence_class"] != "Designed"
        or not isinstance(root["purpose"], str)
        or not root["purpose"]
        or root["domain_terminator_hex"] != "00"
    ):
        _refuse(PracticeSchemaError.MappingMismatch)


def _validate_limits(root: dict[str, Any]) -> None:
    wire_layouts = _mapping(root["wire_layouts"])
    _bounded_items(wire_layouts, MAX_FIELDS)
    if wire_layouts != EXPECTED_WIRE_LAYOUTS:
        _refuse(PracticeSchemaError.FieldOrder)
    scalar_types = _mapping(root["scalar_types"])
    _bounded_items(scalar_types, MAX_FIELDS)
    if scalar_types != EXPECTED_SCALAR_TYPES:
        _refuse(PracticeSchemaError.MappingMismatch)
    parser_bounds = _mapping(root["parser_bounds"])
    _bounded_items(parser_bounds, len(EXPECTED_PARSER_BOUNDS))
    if parser_bounds != EXPECTED_PARSER_BOUNDS:
        _refuse(PracticeSchemaError.InvalidLimit)
    limits = _mapping(root["limits"])
    limit_items = _bounded_items(limits, MAX_FIELDS)
    if {name for name, _ in limit_items} != set(EXPECTED_LIMITS):
        _refuse(PracticeSchemaError.MissingKey)
    for name, row_value in limit_items:
        row = _mapping(row_value)
        _keys(row, {"value", "evidence_class", "play_purpose"})
        if row["value"] != EXPECTED_LIMITS[name]:
            _refuse(PracticeSchemaError.InvalidLimit)
        if row["evidence_class"] != "Designed" or not row["play_purpose"]:
            _refuse(PracticeSchemaError.MappingMismatch)


def _validate_enums(root: dict[str, Any]) -> None:
    enums = _mapping(root["enums"])
    enum_items = _bounded_items(enums, MAX_ENUMS)
    if {name for name, _ in enum_items} != set(EXPECTED_ENUMS):
        _refuse(PracticeSchemaError.MissingKey)
    for enum_name, enum_value in enum_items:
        enum_row = _mapping(enum_value)
        _keys(enum_row, {"width", "members", "evidence_class", "play_purpose"})
        expected_width, expected_members = EXPECTED_ENUMS[enum_name]
        if (
            enum_row["width"] != expected_width
            or enum_row["evidence_class"] != "Designed"
            or not enum_row["play_purpose"]
        ):
            _refuse(PracticeSchemaError.MappingMismatch)
        _validate_code_table(enum_row["members"], expected_members, limit=MAX_ENUM_MEMBERS)


def _validate_errors_and_aliases(root: dict[str, Any]) -> None:
    errors = _mapping(root["contract_errors"])
    _keys(errors, {"width", "members", "evidence_class", "play_purpose"})
    if (
        errors["width"] != "u16"
        or errors["evidence_class"] != "Designed"
        or not errors["play_purpose"]
    ):
        _refuse(PracticeSchemaError.MappingMismatch)
    _validate_code_table(errors["members"], CONTRACT_ERRORS, limit=MAX_ERROR_CODES)
    aliases_value = root["submission_rejection_aliases"]
    if not isinstance(aliases_value, dict):
        _refuse(PracticeSchemaError.MappingMismatch)
    alias_items = list(islice(aliases_value.items(), MAX_ERROR_CODES + 1))
    if len(alias_items) > MAX_ERROR_CODES:
        _refuse(PracticeSchemaError.CollectionLimit)
    for key, value in alias_items:
        if type(key) is not int or not isinstance(value, str):
            _refuse(PracticeSchemaError.MappingMismatch)
    if dict(alias_items) != REJECTION_ALIASES:
        _refuse(PracticeSchemaError.MappingMismatch)


def _validate_practice_mappings(root: dict[str, Any]) -> None:
    mappings = root["practice_mappings"]
    if not isinstance(mappings, list):
        _refuse(PracticeSchemaError.MappingMismatch)
    mapping_rows = _bounded_list(mappings, 3)
    expected_mappings = [
        {
            "practice": "ORGANIZE",
            "display_label": "ORGANIZE",
            "machine_stem": "mobilize",
            "machine_mode": "CANVASS",
            "parameter_allowlist": [],
        },
        {
            "practice": "AGITATE",
            "display_label": "AGITATE",
            "machine_stem": "mobilize",
            "machine_mode": "AGITATE",
            "parameter_allowlist": [],
        },
        {
            "practice": "MUTUAL_AID",
            "display_label": "MUTUAL-AID",
            "machine_stem": "aid",
            "machine_mode": None,
            "parameter_allowlist": [],
        },
    ]
    if mapping_rows != expected_mappings:
        _refuse(PracticeSchemaError.MappingMismatch)
    blockers = _mapping(root["activation_blockers"])
    _bounded_items(blockers, 3)
    expected_blockers = {
        "ORGANIZE": ["GATE3_COMMITTED_ENVELOPE", "GATE5_PENDING_INPUT"],
        "AGITATE": ["GATE3_COMMITTED_ENVELOPE", "GATE5_PENDING_INPUT"],
        "MUTUAL_AID": [
            "GATE3_COMMITTED_ENVELOPE",
            "GATE5_PENDING_INPUT",
            "PER30_ORDERS_INVENTORY",
            "PER31_FREIGHT_REALIZATION",
        ],
    }
    if blockers != expected_blockers:
        _refuse(PracticeSchemaError.MappingMismatch)
    expected_laws = {
        "resolve_tick": "checked_submit_after_tick_plus_one",
        "parameters_v1": "empty_allowlist_for_every_practice",
        "parameter_sequence_bound": "max_parameters",
        "parameter_value_bound": "max_parameter_value_bytes",
        "parameter_total_bound": "max_parameter_bytes",
        "evidence_digests": "sorted_unique_lexicographic",
        "evidence_digest_bound": "max_evidence_digests",
        "intent_canonical_bound": "max_intent_canonical_bytes",
        "policy_authorities": "sorted_unique_by_producer_digest_then_actor",
        "policy_authority_bound": "max_policy_authority_pairs",
        "resolve_batch": "shared_tick_unique_actor",
        "resolve_batch_bound": "max_intents_per_resolve_tick",
        "budget_storage": "finite_nonnegative_integral_binary64_exact_u32",
        "budget_storage_canonical_bits": "checked_u32_to_f64_bits",
        "budget_storage_noncanonical_witness": "negative_zero",
        "budget_arithmetic": "checked_u32_before_f64_storage",
        "solidarity_footprint_order": "ascending_source_then_target",
        "solidarity_footprint_identity": "source_target_EdgeType_SOLIDARITY",
        "solidarity_strength": "finite_strictly_positive",
        "topology_organizations": "ascending_unique_node_id",
        "topology_organization_bound": "max_organizations",
        "topology_edges": "ascending_unique_target_class_node_id",
        "topology_edge_bound": "max_org_solidarity_edges_per_org",
        "topology_active_budget": "required_when_active_optional_when_inactive",
        "topology_supplied_budget": "always_validate_binary64_exact_u32",
        "rejection_only_deferred": [
            "PRACTICE_UNWIRED",
            "PRACTICE_TARGET_INELIGIBLE",
            "PRACTICE_PENDING_DUPLICATE",
        ],
    }
    laws = _mapping(root["validation_laws"])
    _bounded_items(laws, MAX_FIELDS)
    if laws != expected_laws:
        _refuse(PracticeSchemaError.MappingMismatch)


def _validate_records(root: dict[str, Any]) -> None:
    records = _mapping(root["records"])
    record_items = _bounded_items(records, MAX_RECORDS)
    if {name for name, _ in record_items} != set(EXPECTED_RECORD_FIELDS):
        _refuse(PracticeSchemaError.MissingKey)
    for record_name, record_value in record_items:
        record = _mapping(record_value)
        _keys(record, {"wire_domain", "evidence_class", "play_purpose", "fields"})
        if record["evidence_class"] != "Designed" or not record["play_purpose"]:
            _refuse(PracticeSchemaError.MappingMismatch)
        fields = record["fields"]
        if not isinstance(fields, list):
            _refuse(PracticeSchemaError.MappingMismatch)
        field_rows = _bounded_list(fields, MAX_FIELDS)
        names: list[str] = []
        types: list[str] = []
        byte_orders: list[str] = []
        for field_value in field_rows:
            field = _mapping(field_value)
            _keys(field, {"name", "type", "byte_order"})
            if not field["byte_order"]:
                _refuse(PracticeSchemaError.FieldOrder)
            names.append(field["name"])
            types.append(field["type"])
            byte_orders.append(field["byte_order"])
        if (
            names != EXPECTED_RECORD_FIELDS[record_name]
            or types != EXPECTED_RECORD_TYPES[record_name]
            or byte_orders != EXPECTED_RECORD_BYTE_ORDERS[record_name]
        ):
            _refuse(PracticeSchemaError.FieldOrder)
    domains: dict[str, str] = {}
    for name, value in islice(record_items, MAX_RECORDS + 1):
        if value["wire_domain"]:
            domains[name] = value["wire_domain"]
    if domains != {
        "PracticeInputAuthorityV1": "babylon.practice-input-authority.v1",
        "PracticeIntentV1": "babylon.practice-intent.v1",
        "OrganizationBudgetDeltaV1": "babylon.organization-budget-delta.v1",
    }:
        _refuse(PracticeSchemaError.MappingMismatch)


def _validate_budget_and_topology(root: dict[str, Any]) -> None:
    budget_terms = _mapping(root["budget_terms"])
    expected_budget = {
        "initial": 1,
        "weekly_credit_cap": 1,
        "storage_ceiling": 4,
        "organize_cost": 1,
        "agitate_cost": 1,
        "mutual_aid_cost": 1,
    }
    budget_items = _bounded_items(budget_terms, 6)
    actual_budget: dict[str, int] = {}
    for name, term_value in budget_items:
        term = _mapping(term_value)
        _keys(term, {"value", "evidence_class", "play_purpose"})
        if term["evidence_class"] != "Designed" or not term["play_purpose"]:
            _refuse(PracticeSchemaError.MappingMismatch)
        actual_budget[name] = term["value"]
    if actual_budget != expected_budget:
        _refuse(PracticeSchemaError.MappingMismatch)
    topology = _mapping(root["topology"])
    _keys(
        topology,
        {
            "organization_node_type",
            "solidarity_edge_type",
            "target_node_type",
            "graph_identity",
            "target_domain_enters_graph_identity",
            "dynamic_organization_creation",
        },
    )
    if topology != {
        "organization_node_type": "NodeType/ORGANIZATION",
        "solidarity_edge_type": "EdgeType/SOLIDARITY",
        "target_node_type": "NodeType/SOCIAL_CLASS",
        "graph_identity": ["source", "target", "type"],
        "target_domain_enters_graph_identity": False,
        "dynamic_organization_creation": "unavailable_v1",
    }:
        _refuse(PracticeSchemaError.MappingMismatch)


def load_practice_contract(path: Path) -> PracticeContractSpec:
    source = _read_source(path)
    _scan_yaml(source)
    root = _load_unique_yaml(source)
    _validate_header(root)
    _validate_limits(root)
    _validate_enums(root)
    _validate_errors_and_aliases(root)
    _validate_practice_mappings(root)
    _validate_records(root)
    _validate_budget_and_topology(root)
    return PracticeContractSpec(raw=root, practice_ids=PRACTICE_IDS.copy())


def _dump_mutation(tmp_path: Path, document: dict[str, Any]) -> Path:
    path = tmp_path / "practice-contract-invalid.yaml"
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    return path


def _loaded_document() -> dict[str, Any]:
    return yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_adr227_and_index_record_a_pure_non_live_boundary() -> None:
    adr_document = yaml.safe_load(ADR_PATH.read_text(encoding="utf-8"))
    adr = adr_document["ADR227_practice_contract_groundwork"]
    assert adr["status"] == "accepted"
    assert adr["date"] == "2026-08-24"
    assert adr["crate"] == "babylon-practice-contract"
    assert adr["production_dependencies"] == ["babylon-kernel"]
    assert adr["forbidden_dependencies"] == [
        "babylon-graph",
        "babylon-bsl",
        "babylon-tick",
        "babylon-persistence",
        "babylon-client",
    ]
    assert adr["activation_blockers"] == ["PER-20", "PER-22", "PER-26", "PER-27"]
    assert adr["live_activation"] is False
    decision = " ".join(adr["decision"].split())
    for boundary in (
        "pending input ledger",
        "advance_with_inputs",
        "player gateway",
        "practice resolver",
        "durable envelope",
    ):
        assert boundary in decision
    index = yaml.safe_load(INDEX_PATH.read_text(encoding="utf-8"))["decisions"]
    assert index["ADR227_practice_contract_groundwork"] == {
        "title": adr["title"],
        "status": "accepted",
        "date": "2026-08-24",
        "file": "ADR227_practice_contract_groundwork.yaml",
    }


def test_closed_code_tables_and_machine_mappings() -> None:
    contract = load_practice_contract(CONTRACT_PATH)
    assert contract.practice_ids == PRACTICE_IDS
    assert contract.display_label("ORGANIZE") == "ORGANIZE"
    assert contract.display_label("AGITATE") == "AGITATE"
    assert contract.display_label("MUTUAL_AID") == "MUTUAL-AID"
    assert contract.machine_mapping("ORGANIZE") == ("mobilize", "CANVASS")
    assert contract.machine_mapping("AGITATE") == ("mobilize", "AGITATE")
    assert contract.machine_mapping("MUTUAL_AID") == ("aid", None)
    assert contract.raw["enums"]["PracticeAuthorityKindV1"]["members"] == AUTHORITY_KINDS
    assert contract.raw["enums"]["PracticeTargetDomainV1"]["members"] == TARGET_DOMAINS
    assert contract.raw["enums"]["PracticeRejectionCodeV1"]["members"] == REJECTION_CODES


def test_contract_error_table_aliases_and_intentional_holes() -> None:
    contract = load_practice_contract(CONTRACT_PATH)
    assert contract.raw["contract_errors"]["members"] == CONTRACT_ERRORS
    assert contract.raw["submission_rejection_aliases"] == REJECTION_ALIASES
    assert set(CONTRACT_ERRORS.values()).isdisjoint({0, 4, 8, 47})
    assert set(REJECTION_CODES.values()) == set(range(1, 12))
    assert CONTRACT_ERRORS["PRACTICE_BUDGET_ROUNDTRIP"] == 32
    assert contract.raw["limits"]["max_intents_per_resolve_tick"]["value"] == 4_096


def test_records_limits_budget_and_topology_are_exact() -> None:
    contract = load_practice_contract(CONTRACT_PATH)
    assert contract.raw["wire_layouts"] == EXPECTED_WIRE_LAYOUTS
    records = contract.raw["records"]
    assert set(records) == set(EXPECTED_RECORD_FIELDS)
    for name, expected_fields in EXPECTED_RECORD_FIELDS.items():
        assert [field["name"] for field in records[name]["fields"]] == expected_fields
        assert [field["type"] for field in records[name]["fields"]] == EXPECTED_RECORD_TYPES[name]
        assert [field["byte_order"] for field in records[name]["fields"]] == (
            EXPECTED_RECORD_BYTE_ORDERS[name]
        )
    assert contract.raw["budget_terms"] == {
        name: {
            "value": value,
            "evidence_class": "Designed",
            "play_purpose": contract.raw["budget_terms"][name]["play_purpose"],
        }
        for name, value in {
            "initial": 1,
            "weekly_credit_cap": 1,
            "storage_ceiling": 4,
            "organize_cost": 1,
            "agitate_cost": 1,
            "mutual_aid_cost": 1,
        }.items()
    }
    assert contract.raw["limits"]["max_organizations"]["value"] == 4_096
    assert contract.raw["limits"]["max_org_solidarity_edges_per_org"]["value"] == 256
    assert contract.raw["validation_laws"]["resolve_tick"] == ("checked_submit_after_tick_plus_one")
    assert contract.raw["validation_laws"]["budget_storage_noncanonical_witness"] == (
        "negative_zero"
    )
    assert contract.raw["validation_laws"]["topology_active_budget"] == (
        "required_when_active_optional_when_inactive"
    )
    assert contract.raw["practice_mappings"][0]["parameter_allowlist"] == []
    assert contract.raw["practice_mappings"][1]["parameter_allowlist"] == []
    assert contract.raw["practice_mappings"][2]["parameter_allowlist"] == []


@pytest.mark.parametrize(
    ("enum_name", "members"),
    [
        ("PracticeIdV1", {"ORGANIZE": 0, "AGITATE": 2, "MUTUAL_AID": 3}),
        ("PracticeIdV1", {"ORGANIZE": 1, "AGITATE": 2, "MUTUAL_AID": 4}),
        ("PracticeAuthorityKindV1", {"PLAYER_SEAT": 0, "DETERMINISTIC_POLICY": 2}),
        ("PracticeAuthorityKindV1", {"PLAYER_SEAT": 1, "DETERMINISTIC_POLICY": 3}),
        ("PracticeTargetDomainV1", {"SOCIAL_CLASS": 0}),
        ("PracticeTargetDomainV1", {"SOCIAL_CLASS": 2}),
        ("VerbModeV1", {"CANVASS": 0, "AGITATE": 2}),
        ("VerbModeV1", {"CANVASS": 1, "AGITATE": 3}),
    ],
)
def test_unknown_or_zero_enum_codes_refuse(
    tmp_path: Path, enum_name: str, members: dict[str, int]
) -> None:
    document = _loaded_document()
    document["enums"][enum_name]["members"] = members
    with pytest.raises(PracticeSchemaViolation):
        load_practice_contract(_dump_mutation(tmp_path, document))


@pytest.mark.parametrize(
    "mutation",
    [
        {"machine_stem": "aid", "machine_mode": "CANVASS"},
        {"machine_stem": "mobilize", "machine_mode": None},
    ],
)
def test_invalid_machine_mapping_refuses(tmp_path: Path, mutation: dict[str, object]) -> None:
    document = _loaded_document()
    document["practice_mappings"][0].update(mutation)
    with pytest.raises(PracticeSchemaViolation) as raised:
        load_practice_contract(_dump_mutation(tmp_path, document))
    assert raised.value.error is PracticeSchemaError.MappingMismatch


def test_missing_domain_separator_refuses(tmp_path: Path) -> None:
    document = _loaded_document()
    del document["domain_terminator_hex"]
    with pytest.raises(PracticeSchemaViolation) as raised:
        load_practice_contract(_dump_mutation(tmp_path, document))
    assert raised.value.error is PracticeSchemaError.MissingKey


def test_wire_field_without_byte_order_refuses(tmp_path: Path) -> None:
    document = _loaded_document()
    del document["records"]["PracticeIntentV1"]["fields"][0]["byte_order"]
    with pytest.raises(PracticeSchemaViolation) as raised:
        load_practice_contract(_dump_mutation(tmp_path, document))
    assert raised.value.error is PracticeSchemaError.MissingKey


def test_source_read_is_bounded_before_parse(monkeypatch: pytest.MonkeyPatch) -> None:
    source = _read_source(CONTRACT_PATH)
    reader = MagicMock()
    reader.__enter__.return_value = reader
    reader.read.return_value = source
    opener = MagicMock(return_value=reader)
    monkeypatch.setattr(Path, "open", opener)

    load_practice_contract(CONTRACT_PATH)

    opener.assert_called_once_with("rb")
    reader.read.assert_called_once_with(MAX_SOURCE_BYTES + 1)


@pytest.mark.parametrize(
    "source",
    [
        b"schema: [\n",
        b"true: value\n",
        b"? [sequence, key]\n: value\n",
        b"? {mapping: key}\n: value\n",
    ],
)
def test_malformed_or_complex_yaml_keys_return_typed_schema_error(
    tmp_path: Path, source: bytes
) -> None:
    path = tmp_path / "malformed-practice-contract.yaml"
    path.write_bytes(source)

    with pytest.raises(PracticeSchemaViolation) as raised:
        load_practice_contract(path)

    assert raised.value.error is PracticeSchemaError.MappingMismatch


def test_source_event_alias_duplicate_depth_and_key_refusals(tmp_path: Path) -> None:
    oversized = tmp_path / "oversized.yaml"
    oversized.write_bytes(b"x" * (MAX_SOURCE_BYTES + 1))
    with pytest.raises(PracticeSchemaViolation) as raised:
        load_practice_contract(oversized)
    assert raised.value.error is PracticeSchemaError.SourceBytes

    event_bomb = tmp_path / "events.yaml"
    event_bomb.write_text("x: [" + ",".join("0" for _ in range(MAX_YAML_EVENTS)) + "]")
    with pytest.raises(PracticeSchemaViolation) as raised:
        load_practice_contract(event_bomb)
    assert raised.value.error is PracticeSchemaError.EventLimit

    alias = tmp_path / "alias.yaml"
    alias.write_text("a: &shared 1\nb: *shared\n", encoding="utf-8")
    with pytest.raises(PracticeSchemaViolation) as raised:
        load_practice_contract(alias)
    assert raised.value.error is PracticeSchemaError.Alias

    duplicate = tmp_path / "duplicate.yaml"
    duplicate.write_text("schema: one\nschema: two\n", encoding="utf-8")
    with pytest.raises(PracticeSchemaViolation) as raised:
        load_practice_contract(duplicate)
    assert raised.value.error is PracticeSchemaError.DuplicateKey

    depth = tmp_path / "depth.yaml"
    depth.write_text("x: " + "[" * MAX_DEPTH + "0" + "]" * MAX_DEPTH, encoding="utf-8")
    with pytest.raises(PracticeSchemaViolation) as raised:
        load_practice_contract(depth)
    assert raised.value.error is PracticeSchemaError.Depth

    document = _loaded_document()
    document["undeclared"] = True
    with pytest.raises(PracticeSchemaViolation) as raised:
        load_practice_contract(_dump_mutation(tmp_path, document))
    assert raised.value.error is PracticeSchemaError.UnknownKey


def test_code_limit_order_and_mapping_refusals(tmp_path: Path) -> None:
    document = _loaded_document()
    document["enums"]["VerbModeV1"]["members"]["AGITATE"] = 1
    with pytest.raises(PracticeSchemaViolation) as raised:
        load_practice_contract(_dump_mutation(tmp_path, document))
    assert raised.value.error is PracticeSchemaError.DuplicateCode

    document = _loaded_document()
    del document["contract_errors"]["members"]["PRACTICE_DOMAIN"]
    with pytest.raises(PracticeSchemaViolation) as raised:
        load_practice_contract(_dump_mutation(tmp_path, document))
    assert raised.value.error is PracticeSchemaError.MissingCode

    document = _loaded_document()
    document["limits"]["max_parameters"]["value"] = 0
    with pytest.raises(PracticeSchemaViolation) as raised:
        load_practice_contract(_dump_mutation(tmp_path, document))
    assert raised.value.error is PracticeSchemaError.InvalidLimit

    document = _loaded_document()
    document["records"]["PracticeIntentV1"]["fields"].reverse()
    with pytest.raises(PracticeSchemaViolation) as raised:
        load_practice_contract(_dump_mutation(tmp_path, document))
    assert raised.value.error is PracticeSchemaError.FieldOrder

    document = _loaded_document()
    document["submission_rejection_aliases"][16] = "PRACTICE_UNWIRED"
    with pytest.raises(PracticeSchemaViolation) as raised:
        load_practice_contract(_dump_mutation(tmp_path, document))
    assert raised.value.error is PracticeSchemaError.MappingMismatch


@pytest.mark.parametrize("collection", ["fields", "records", "enums", "members", "errors"])
def test_meta_model_collection_plus_one_refuses(tmp_path: Path, collection: str) -> None:
    document = _loaded_document()
    if collection == "fields":
        document["records"]["PracticeIntentV1"]["fields"] = [
            {"name": f"field_{index}", "type": "u8", "byte_order": "single_byte"}
            for index in range(MAX_FIELDS + 1)
        ]
    elif collection == "records":
        document["records"] = {f"Record{index}": {} for index in range(MAX_RECORDS + 1)}
    elif collection == "enums":
        document["enums"] = {f"Enum{index}": {} for index in range(MAX_ENUMS + 1)}
    elif collection == "members":
        document["enums"]["PracticeIdV1"]["members"] = {
            f"MEMBER_{index}": index + 1 for index in range(MAX_ENUM_MEMBERS + 1)
        }
    else:
        document["contract_errors"]["members"] = {
            f"ERROR_{index}": index + 1 for index in range(MAX_ERROR_CODES + 1)
        }
    with pytest.raises(PracticeSchemaViolation) as raised:
        load_practice_contract(_dump_mutation(tmp_path, document))
    assert raised.value.error is PracticeSchemaError.CollectionLimit


def test_schema_error_registry_is_exact() -> None:
    assert [member.value for member in PracticeSchemaError] == [
        "SourceBytes",
        "EventLimit",
        "Alias",
        "DuplicateKey",
        "Depth",
        "UnknownKey",
        "MissingKey",
        "DuplicateCode",
        "MissingCode",
        "InvalidLimit",
        "CollectionLimit",
        "FieldOrder",
        "MappingMismatch",
    ]
