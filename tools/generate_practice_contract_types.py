#!/usr/bin/env python3
"""Generate sealed Python and Rust practice-contract structural types."""

from __future__ import annotations

import argparse
import hashlib
from dataclasses import dataclass
from enum import StrEnum
from itertools import islice
from pathlib import Path
from typing import Any, Never, cast

import yaml
from yaml.events import AliasEvent, CollectionEndEvent, CollectionStartEvent

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = ROOT / "contracts" / "practice_contract_v1.yaml"
DEFAULT_PYTHON_OUT = ROOT / "src" / "babylon" / "contracts" / "practice_contract_v1_generated.py"
DEFAULT_RUST_OUT = ROOT / "rust" / "crates" / "babylon-practice-contract" / "src" / "generated.rs"

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
EXPECTED_ENUMS = {
    "PracticeIdV1": ("u8", PRACTICE_IDS),
    "VerbStemV1": ("u8", VERB_STEMS),
    "VerbModeV1": ("u8", VERB_MODES),
    "PracticeAuthorityKindV1": ("u8", AUTHORITY_KINDS),
    "PracticeTargetDomainV1": ("u8", TARGET_DOMAINS),
    "PracticeRejectionCodeV1": ("u16", REJECTION_CODES),
    "PracticeActivationBlockerV1": ("u8", ACTIVATION_BLOCKERS),
}
EXPECTED_ALIASES = {
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
EXPECTED_VALIDATION_LAWS = {
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
EXPECTED_BUDGET_TERMS = {
    "initial": 1,
    "weekly_credit_cap": 1,
    "storage_ceiling": 4,
    "organize_cost": 1,
    "agitate_cost": 1,
    "mutual_aid_cost": 1,
}
EXPECTED_TOPOLOGY = {
    "organization_node_type": "NodeType/ORGANIZATION",
    "solidarity_edge_type": "EdgeType/SOLIDARITY",
    "target_node_type": "NodeType/SOCIAL_CLASS",
    "graph_identity": ["source", "target", "type"],
    "target_domain_enters_graph_identity": False,
    "dynamic_organization_creation": "unavailable_v1",
}
EXPECTED_MAPPINGS = [
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
EXPECTED_BLOCKERS = {
    "ORGANIZE": ["GATE3_COMMITTED_ENVELOPE", "GATE5_PENDING_INPUT"],
    "AGITATE": ["GATE3_COMMITTED_ENVELOPE", "GATE5_PENDING_INPUT"],
    "MUTUAL_AID": [
        "GATE3_COMMITTED_ENVELOPE",
        "GATE5_PENDING_INPUT",
        "PER30_ORDERS_INVENTORY",
        "PER31_FREIGHT_REALIZATION",
    ],
}
EXPECTED_RECORD_LAYOUTS = {
    "PracticeInputAuthorityV1": (
        ("schema_version", "u16", "big_endian"),
        ("authority_kind", "PracticeAuthorityKindV1", "single_byte"),
        ("actor_org_id", "u64", "big_endian"),
        ("producer_content_digest", "digest32", "raw_bytes"),
    ),
    "PracticeParameterV1": (
        ("key_u8", "u8", "single_byte"),
        ("value_kind_u8", "u8", "single_byte"),
        ("value_length_u16", "u16", "big_endian"),
        ("value_bytes", "bytes", "raw_bytes"),
    ),
    "PracticeIntentV1": (
        ("schema_version", "u16", "big_endian"),
        ("submit_after_tick", "u64", "big_endian"),
        ("resolve_tick", "u64", "big_endian"),
        ("actor_org_id", "u64", "big_endian"),
        ("practice_id", "PracticeIdV1", "single_byte"),
        ("target_domain", "PracticeTargetDomainV1", "single_byte"),
        ("target_node_id", "u64", "big_endian"),
        ("quoted_content_digest", "digest32", "raw_bytes"),
        ("quoted_action_budget_cost", "u32", "big_endian"),
        ("parameters", "sequence[PracticeParameterV1]", "length_framed_big_endian"),
        ("evidence_digests", "sequence[digest32]", "length_framed_big_endian"),
    ),
    "PolicyAuthorityPairV1": (
        ("producer_content_digest", "digest32", "raw_bytes"),
        ("actor_org_id", "u64", "big_endian"),
    ),
    "PracticeAuthorityContextV1": (
        ("player_org_id", "u64", "big_endian"),
        ("player_gateway_content_digest", "digest32", "raw_bytes"),
        ("policy_authorities", "sequence[PolicyAuthorityPairV1]", "sorted_unique"),
    ),
    "PracticeQuoteContextV1": (
        ("last_committed_tick", "u64", "big_endian"),
        ("content_digest", "digest32", "raw_bytes"),
        ("budget_terms", "PracticeBudgetTermsV1", "declared_record_order"),
    ),
    "SolidarityFootprintEdgeV1": (
        ("source_org_node_id_u64", "u64", "big_endian"),
        ("target_domain_u8", "PracticeTargetDomainV1", "single_byte"),
        ("target_class_node_id_u64", "u64", "big_endian"),
        ("strength_f64_bits_u64", "f64_bits_u64", "big_endian"),
    ),
    "OrganizationPracticeTopologyEdgeV1": (
        ("target_domain", "PracticeTargetDomainV1", "single_byte"),
        ("target_class_node_id_u64", "u64", "big_endian"),
    ),
    "OrganizationPracticeTopologyRowV1": (
        ("node_id_u64", "u64", "big_endian"),
        ("active_bool", "bool", "single_byte"),
        (
            "action_budget_storage_f64_bits_u64",
            "optional[f64_bits_u64]",
            "optional_tag_then_big_endian",
        ),
        ("edges", "sequence[OrganizationPracticeTopologyEdgeV1]", "sorted_unique"),
    ),
    "OrganizationPracticeTopologyV1": (
        ("organizations", "sequence[OrganizationPracticeTopologyRowV1]", "sorted_unique"),
    ),
    "OrganizationBudgetDeltaV1": (
        ("schema_version", "u16", "big_endian"),
        ("tick", "u64", "big_endian"),
        ("actor_node_id", "u64", "big_endian"),
        ("pre_action_world_hash", "digest32", "raw_bytes"),
        ("budget_before", "u32", "big_endian"),
        ("governed_cost", "u32", "big_endian"),
        ("footprint_count", "u32", "big_endian"),
        ("raw_credit", "u32", "big_endian"),
        ("credited_credit", "u32", "big_endian"),
        ("ceiling_bound", "bool", "single_byte"),
        ("budget_after", "u32", "big_endian"),
    ),
    "PracticeSubmissionRejectionV1": (
        ("schema_version", "u16", "big_endian"),
        ("submitted_bytes_digest", "digest32", "raw_bytes"),
        ("reason_code", "PracticeRejectionCodeV1", "big_endian"),
        ("last_committed_tick", "u64", "big_endian"),
        ("content_digest", "digest32", "raw_bytes"),
    ),
    "PracticeBudgetTermsV1": (
        ("initial", "u32", "big_endian"),
        ("weekly_credit_cap", "u32", "big_endian"),
        ("storage_ceiling", "u32", "big_endian"),
        ("organize_cost", "u32", "big_endian"),
        ("agitate_cost", "u32", "big_endian"),
        ("mutual_aid_cost", "u32", "big_endian"),
    ),
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


def _refuse(error: PracticeSchemaError) -> Never:
    raise PracticeSchemaViolation(error)


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
            _refuse(PracticeSchemaError.DuplicateKey)
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


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


def _read_source(path: Path) -> bytes:
    with path.open("rb") as source_file:
        source = source_file.read(MAX_SOURCE_BYTES + 1)
    if len(source) > MAX_SOURCE_BYTES:
        _refuse(PracticeSchemaError.SourceBytes)
    return source


def _scan_yaml(source: bytes) -> None:
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


def _load_unique_yaml(source: bytes) -> dict[str, Any]:
    loader = _UniqueKeyLoader(source)
    try:
        try:
            loaded = loader.get_single_data()
        except yaml.YAMLError:
            _refuse(PracticeSchemaError.MappingMismatch)
    finally:
        loader.dispose()  # type: ignore[no-untyped-call]
    return _mapping(loaded)


def _validate_code_table(value: object, expected: dict[str, int]) -> None:
    table = _mapping(value)
    items = _bounded_items(table, MAX_ENUM_MEMBERS)
    codes: list[int] = []
    for _, code in islice(items, MAX_ENUM_MEMBERS + 1):
        if type(code) is not int or not 0 < code <= 65_535:
            _refuse(PracticeSchemaError.MappingMismatch)
        if code in codes:
            _refuse(PracticeSchemaError.DuplicateCode)
        codes.append(code)
    if set(expected.values()) - set(codes):
        _refuse(PracticeSchemaError.MissingCode)
    if dict(items) != expected:
        _refuse(PracticeSchemaError.MappingMismatch)


def _validate_header(root: dict[str, Any]) -> None:
    expected = {
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
    _keys(root, expected)
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
    items = _bounded_items(limits, MAX_FIELDS)
    if set(dict(items)) != set(EXPECTED_LIMITS):
        _refuse(PracticeSchemaError.MissingKey)
    for name, value in islice(items, MAX_FIELDS + 1):
        row = _mapping(value)
        _keys(row, {"value", "evidence_class", "play_purpose"})
        if row["value"] != EXPECTED_LIMITS[name]:
            _refuse(PracticeSchemaError.InvalidLimit)
        if row["evidence_class"] != "Designed" or not row["play_purpose"]:
            _refuse(PracticeSchemaError.MappingMismatch)


def _validate_enums(root: dict[str, Any]) -> None:
    enums = _mapping(root["enums"])
    items = _bounded_items(enums, MAX_ENUMS)
    if set(dict(items)) != set(EXPECTED_ENUMS):
        _refuse(PracticeSchemaError.MissingKey)
    for name, value in islice(items, MAX_ENUMS + 1):
        row = _mapping(value)
        _keys(row, {"width", "members", "evidence_class", "play_purpose"})
        width, members = EXPECTED_ENUMS[name]
        if row["width"] != width or row["evidence_class"] != "Designed":
            _refuse(PracticeSchemaError.MappingMismatch)
        _validate_code_table(row["members"], members)


def _validate_errors(root: dict[str, Any]) -> None:
    errors = _mapping(root["contract_errors"])
    _keys(errors, {"width", "members", "evidence_class", "play_purpose"})
    if errors["width"] != "u16" or errors["evidence_class"] != "Designed":
        _refuse(PracticeSchemaError.MappingMismatch)
    _validate_code_table(errors["members"], CONTRACT_ERRORS)
    aliases = root["submission_rejection_aliases"]
    if not isinstance(aliases, dict):
        _refuse(PracticeSchemaError.MappingMismatch)
    items = list(islice(aliases.items(), MAX_ERROR_CODES + 1))
    if len(items) > MAX_ERROR_CODES:
        _refuse(PracticeSchemaError.CollectionLimit)
    for key, value in islice(items, MAX_ERROR_CODES + 1):
        if type(key) is not int or not isinstance(value, str):
            _refuse(PracticeSchemaError.MappingMismatch)
    if dict(items) != EXPECTED_ALIASES:
        _refuse(PracticeSchemaError.MappingMismatch)


def _validate_mappings(root: dict[str, Any]) -> None:
    mappings = root["practice_mappings"]
    if not isinstance(mappings, list):
        _refuse(PracticeSchemaError.MappingMismatch)
    if _bounded_list(mappings, 3) != EXPECTED_MAPPINGS:
        _refuse(PracticeSchemaError.MappingMismatch)
    blockers = _mapping(root["activation_blockers"])
    if blockers != EXPECTED_BLOCKERS:
        _refuse(PracticeSchemaError.MappingMismatch)
    validation_laws = _mapping(root["validation_laws"])
    _bounded_items(validation_laws, MAX_FIELDS)
    if validation_laws != EXPECTED_VALIDATION_LAWS:
        _refuse(PracticeSchemaError.MappingMismatch)


def _validate_records(root: dict[str, Any]) -> None:
    records = _mapping(root["records"])
    items = _bounded_items(records, MAX_RECORDS)
    if set(dict(items)) != set(EXPECTED_RECORD_LAYOUTS):
        _refuse(PracticeSchemaError.MissingKey)
    for name, value in islice(items, MAX_RECORDS + 1):
        row = _mapping(value)
        _keys(row, {"wire_domain", "evidence_class", "play_purpose", "fields"})
        if row["evidence_class"] != "Designed" or not row["play_purpose"]:
            _refuse(PracticeSchemaError.MappingMismatch)
        fields = row["fields"]
        if not isinstance(fields, list):
            _refuse(PracticeSchemaError.MappingMismatch)
        field_rows = _bounded_list(fields, MAX_FIELDS)
        actual: list[tuple[str, str, str]] = []
        for field_value in islice(field_rows, MAX_FIELDS + 1):
            field = _mapping(field_value)
            _keys(field, {"name", "type", "byte_order"})
            actual.append((field["name"], field["type"], field["byte_order"]))
        if tuple(actual) != EXPECTED_RECORD_LAYOUTS[name]:
            _refuse(PracticeSchemaError.FieldOrder)
    domains: dict[str, str] = {}
    for name, value in islice(items, MAX_RECORDS + 1):
        row = _mapping(value)
        if row["wire_domain"]:
            domains[name] = cast(str, row["wire_domain"])
    if domains != {
        "PracticeInputAuthorityV1": "babylon.practice-input-authority.v1",
        "PracticeIntentV1": "babylon.practice-intent.v1",
        "OrganizationBudgetDeltaV1": "babylon.organization-budget-delta.v1",
    }:
        _refuse(PracticeSchemaError.MappingMismatch)


def _validate_budget_and_topology(root: dict[str, Any]) -> None:
    budget_terms = _mapping(root["budget_terms"])
    items = _bounded_items(budget_terms, MAX_FIELDS)
    actual: dict[str, int] = {}
    for name, value in islice(items, MAX_FIELDS + 1):
        row = _mapping(value)
        _keys(row, {"value", "evidence_class", "play_purpose"})
        if (
            type(row["value"]) is not int
            or row["evidence_class"] != "Designed"
            or not row["play_purpose"]
        ):
            _refuse(PracticeSchemaError.MappingMismatch)
        actual[name] = row["value"]
    if actual != EXPECTED_BUDGET_TERMS:
        _refuse(PracticeSchemaError.MappingMismatch)
    topology = _mapping(root["topology"])
    _bounded_items(topology, MAX_FIELDS)
    if topology != EXPECTED_TOPOLOGY:
        _refuse(PracticeSchemaError.MappingMismatch)


@dataclass(frozen=True)
class PracticeContractSpec:
    source_digest: str
    raw: dict[str, Any]

    @property
    def practice_ids(self) -> dict[str, int]:
        return dict(PRACTICE_IDS)

    def display_label(self, practice: str) -> str:
        return cast(str, self._mapping_row(practice)["display_label"])

    def machine_mapping(self, practice: str) -> tuple[str, str | None]:
        row = self._mapping_row(practice)
        return cast(str, row["machine_stem"]), cast(str | None, row["machine_mode"])

    def _mapping_row(self, practice: str) -> dict[str, Any]:
        rows_value = self.raw["practice_mappings"]
        if not isinstance(rows_value, list):
            _refuse(PracticeSchemaError.MappingMismatch)
        for row_value in islice(rows_value, 4):
            row = _mapping(row_value)
            if row["practice"] == practice:
                return row
        raise KeyError(practice)


def load_practice_contract(path: Path) -> PracticeContractSpec:
    source = _read_source(path)
    _scan_yaml(source)
    root = _load_unique_yaml(source)
    _validate_header(root)
    _validate_limits(root)
    _validate_enums(root)
    _validate_errors(root)
    _validate_mappings(root)
    _validate_records(root)
    _validate_budget_and_topology(root)
    return PracticeContractSpec(hashlib.sha256(source).hexdigest(), root)


def _rust_variant(name: str) -> str:
    parts = name.lower().split("_")
    return "".join(part.title() for part in islice(parts, MAX_FIELDS + 1))


def _rust_const(name: str) -> str:
    output: list[str] = []
    for index, character in enumerate(islice(name, MAX_SOURCE_BYTES + 1)):
        if character.isupper() and index > 0 and name[index - 1].islower():
            output.append("_")
        output.append(character.upper())
    return "".join(output)


def _python_type(type_name: str) -> str:
    scalar = {
        "u8": "U8",
        "u16": "U16",
        "u32": "U32",
        "u64": "U64",
        "f64_bits_u64": "U64",
        "digest32": "Digest32",
        "bool": "bool",
        "bytes": "bytes",
    }
    if type_name in scalar:
        return scalar[type_name]
    if type_name.startswith("sequence["):
        inner = type_name.removeprefix("sequence[").removesuffix("]")
        return f"tuple[{_python_type(inner)}, ...]"
    if type_name.startswith("optional["):
        inner = type_name.removeprefix("optional[").removesuffix("]")
        return f"{_python_type(inner)} | None"
    return type_name


def _rust_type(type_name: str) -> str:
    scalar = {
        "u8": "u8",
        "u16": "u16",
        "u32": "u32",
        "u64": "u64",
        "f64_bits_u64": "u64",
        "digest32": "[u8; 32]",
        "bool": "bool",
        "bytes": "Vec<u8>",
    }
    if type_name in scalar:
        return scalar[type_name]
    if type_name.startswith("sequence["):
        inner = type_name.removeprefix("sequence[").removesuffix("]")
        return f"Vec<{_rust_type(inner)}>"
    if type_name.startswith("optional["):
        inner = type_name.removeprefix("optional[").removesuffix("]")
        return f"Option<{_rust_type(inner)}>"
    return type_name


def _render_python_enums(spec: PracticeContractSpec) -> list[str]:
    lines: list[str] = []
    enums = spec.raw["enums"]
    for enum_name, enum_row in islice(enums.items(), MAX_ENUMS + 1):
        lines.extend([f"class {enum_name}(IntEnum):"])
        for member, code in islice(enum_row["members"].items(), MAX_ENUM_MEMBERS + 1):
            lines.append(f"    {member} = {code}")
        lines.extend(["", ""])
    lines.append("class PracticeContractError(IntEnum):")
    errors = spec.raw["contract_errors"]["members"]
    for member, code in islice(errors.items(), MAX_ERROR_CODES + 1):
        lines.append(f"    {member} = {code}")
    lines.extend(["", ""])
    return lines


def _render_python_records(spec: PracticeContractSpec) -> list[str]:
    lines = [
        "class MachineVerbV1(BaseModel):",
        '    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)',
        "",
        "    stem: VerbStemV1",
        "    mode: VerbModeV1 | None",
        "",
        "",
    ]
    records = spec.raw["records"]
    for record_name, record in islice(records.items(), MAX_RECORDS + 1):
        lines.extend(
            [
                f"class {record_name}(BaseModel):",
                '    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)',
                "",
            ]
        )
        for field in islice(record["fields"], MAX_FIELDS + 1):
            lines.append(f"    {field['name']}: {_python_type(field['type'])}")
        lines.extend(["", ""])
    return lines


def _render_python_api(spec: PracticeContractSpec) -> list[str]:
    limits = _mapping(spec.raw["limits"])
    lines: list[str] = []
    for name, row_value in islice(limits.items(), MAX_FIELDS + 1):
        row = _mapping(row_value)
        lines.append(f"{name.upper()} = {row['value']}")
    lines.extend(
        [
            "",
            "",
            "def machine_verb_for(practice: PracticeIdV1) -> MachineVerbV1:",
            "    if type(practice) is not PracticeIdV1:",
            '        raise TypeError("practice must be PracticeIdV1")',
            "    if practice is PracticeIdV1.ORGANIZE:",
            "        return MachineVerbV1(stem=VerbStemV1.MOBILIZE, mode=VerbModeV1.CANVASS)",
            "    if practice is PracticeIdV1.AGITATE:",
            "        return MachineVerbV1(stem=VerbStemV1.MOBILIZE, mode=VerbModeV1.AGITATE)",
            "    return MachineVerbV1(stem=VerbStemV1.AID, mode=None)",
            "",
            "",
            "def validate_intent_collection_bounds(",
            "    value: PracticeIntentV1,",
            ") -> PracticeContractError | None:",
            "    if len(value.parameters) > MAX_PARAMETERS:",
            "        return PracticeContractError.PRACTICE_PARAMETER_LIMIT",
            "    if len(value.evidence_digests) > MAX_EVIDENCE_DIGESTS:",
            "        return PracticeContractError.PRACTICE_EVIDENCE_LIMIT",
            "    return None",
            "",
            "",
            "def validate_authority_context_collection_bounds(",
            "    value: PracticeAuthorityContextV1,",
            ") -> PracticeContractError | None:",
            "    if len(value.policy_authorities) > MAX_POLICY_AUTHORITY_PAIRS:",
            "        return PracticeContractError.PRACTICE_AUTHORITY_REGISTRY_LIMIT",
            "    return None",
            "",
            "",
            "def validate_topology_collection_bounds(",
            "    value: OrganizationPracticeTopologyV1,",
            ") -> PracticeContractError | None:",
            "    if len(value.organizations) > MAX_ORGANIZATIONS:",
            "        return PracticeContractError.PRACTICE_TOPOLOGY_ORGANIZATION_LIMIT",
            "    for row in islice(value.organizations, MAX_ORGANIZATIONS + 1):",
            "        if len(row.edges) > MAX_ORG_SOLIDARITY_EDGES_PER_ORG:",
            "            return PracticeContractError.PRACTICE_FOOTPRINT_LIMIT",
            "    return None",
            "",
        ]
    )
    return lines


def render_python(spec: PracticeContractSpec) -> str:
    lines = [
        f"# Generated from contracts/practice_contract_v1.yaml; sha256={spec.source_digest}",
        "from __future__ import annotations",
        "",
        "from enum import IntEnum",
        "from itertools import islice",
        "from typing import Annotated",
        "",
        "from pydantic import BaseModel, ConfigDict, Field",
        "",
        "U8 = Annotated[int, Field(strict=True, ge=0, le=255)]",
        "U16 = Annotated[int, Field(strict=True, ge=0, le=65_535)]",
        "U32 = Annotated[int, Field(strict=True, ge=0, le=4_294_967_295)]",
        "U64 = Annotated[int, Field(strict=True, ge=0, le=18_446_744_073_709_551_615)]",
        "Digest32 = Annotated[bytes, Field(strict=True, min_length=32, max_length=32)]",
        "",
        "",
    ]
    lines.extend(_render_python_enums(spec))
    lines.extend(_render_python_records(spec))
    lines.extend(_render_python_api(spec))
    return "\n".join(lines)


def _render_rust_enum(name: str, width: str, members: dict[str, int]) -> list[str]:
    lines = [
        "#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]",
        f"#[repr({width})]",
        f"pub enum {name} {{",
    ]
    for member, code in islice(members.items(), MAX_ENUM_MEMBERS + 1):
        lines.append(f"    {_rust_variant(member)} = {code},")
    lines.extend(["}", "", f"impl TryFrom<{width}> for {name} {{"])
    lines.extend(
        [
            "    type Error = PracticeContractError;",
            "",
            f"    fn try_from(value: {width}) -> Result<Self, Self::Error> {{",
            "        match value {",
        ]
    )
    for member, code in islice(members.items(), MAX_ENUM_MEMBERS + 1):
        lines.append(f"            {code} => Ok(Self::{_rust_variant(member)}),")
    lines.extend(
        [
            "            _ => Err(PracticeContractError::PracticeEnumCode),",
            "        }",
            "    }",
            "}",
            "",
        ]
    )
    return lines


def _render_rust_errors(spec: PracticeContractSpec) -> list[str]:
    members = spec.raw["contract_errors"]["members"]
    lines = [
        "#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]",
        "#[repr(u16)]",
        "pub enum PracticeContractError {",
    ]
    for member, code in islice(members.items(), MAX_ERROR_CODES + 1):
        lines.append(f"    {_rust_variant(member)} = {code},")
    lines.extend(
        [
            "}",
            "",
            "#[derive(Debug, Clone, Copy, PartialEq, Eq)]",
            "pub struct UnknownPracticeContractErrorCode(pub u16);",
            "",
            "impl TryFrom<u16> for PracticeContractError {",
            "    type Error = UnknownPracticeContractErrorCode;",
            "",
            "    fn try_from(value: u16) -> Result<Self, Self::Error> {",
            "        match value {",
        ]
    )
    for member, code in islice(members.items(), MAX_ERROR_CODES + 1):
        lines.append(f"            {code} => Ok(Self::{_rust_variant(member)}),")
    lines.extend(
        [
            "            _ => Err(UnknownPracticeContractErrorCode(value)),",
            "        }",
            "    }",
            "}",
            "",
            "impl From<PracticeContractError> for u16 {",
            "    fn from(value: PracticeContractError) -> Self {",
            "        value as Self",
            "    }",
            "}",
            "",
        ]
    )
    return lines


def _render_rust_records(spec: PracticeContractSpec) -> list[str]:
    lines = [
        "#[derive(Debug, Clone, Copy, PartialEq, Eq)]",
        "pub struct MachineVerbV1 {",
        "    pub stem: VerbStemV1,",
        "    pub mode: Option<VerbModeV1>,",
        "}",
        "",
    ]
    for name, record in islice(spec.raw["records"].items(), MAX_RECORDS + 1):
        lines.extend(["#[derive(Debug, Clone, PartialEq, Eq)]", f"pub struct {name} {{"])
        field_names: list[str] = []
        for field in islice(record["fields"], MAX_FIELDS + 1):
            field_names.append(field["name"])
            lines.append(f"    pub {field['name']}: {_rust_type(field['type'])},")
        lines.extend(["}", ""])
        lines.extend(_render_rust_field_order(name, field_names))
    return lines


def _render_rust_field_order(record_name: str, field_names: list[str]) -> list[str]:
    constant = f"{_rust_const(record_name)}_FIELD_ORDER"
    declaration = f"pub const {constant}: [&str; {len(field_names)}] ="
    values = ", ".join(f'"{name}"' for name in islice(field_names, MAX_FIELDS + 1))
    inline_array = f"[{values}];"
    if len(declaration) + 1 + len(inline_array) <= 100:
        return [f"{declaration} {inline_array}", ""]
    if len(inline_array) <= 65:
        return [declaration, f"    {inline_array}", ""]
    lines = [f"{declaration} ["]
    for field_name in islice(field_names, MAX_FIELDS + 1):
        lines.append(f'    "{field_name}",')
    lines.extend(["];", ""])
    return lines


def _render_rust_api(spec: PracticeContractSpec) -> list[str]:
    lines: list[str] = []
    limits = spec.raw["limits"]
    for name, row in islice(limits.items(), MAX_FIELDS + 1):
        lines.append(f"pub const {name.upper()}: usize = {row['value']};")
    lines.extend(
        [
            "",
            "#[must_use]",
            "pub const fn practice_machine_verb(practice: PracticeIdV1) -> MachineVerbV1 {",
            "    match practice {",
            "        PracticeIdV1::Organize => MachineVerbV1 {",
            "            stem: VerbStemV1::Mobilize,",
            "            mode: Some(VerbModeV1::Canvass),",
            "        },",
            "        PracticeIdV1::Agitate => MachineVerbV1 {",
            "            stem: VerbStemV1::Mobilize,",
            "            mode: Some(VerbModeV1::Agitate),",
            "        },",
            "        PracticeIdV1::MutualAid => MachineVerbV1 {",
            "            stem: VerbStemV1::Aid,",
            "            mode: None,",
            "        },",
            "    }",
            "}",
            "",
            "/// Checks the shape-only intent collections against their contract bounds.",
            "///",
            "/// # Errors",
            "///",
            "/// Returns the assigned parameter or evidence bound error.",
            "pub fn validate_intent_collection_bounds(",
            "    value: &PracticeIntentV1,",
            ") -> Result<(), PracticeContractError> {",
            "    if value.parameters.len() > MAX_PARAMETERS {",
            "        return Err(PracticeContractError::PracticeParameterLimit);",
            "    }",
            "    if value.evidence_digests.len() > MAX_EVIDENCE_DIGESTS {",
            "        return Err(PracticeContractError::PracticeEvidenceLimit);",
            "    }",
            "    Ok(())",
            "}",
            "",
            "/// Checks the shape-only authority registry against its contract bound.",
            "///",
            "/// # Errors",
            "///",
            "/// Returns the assigned authority registry bound error.",
            "pub fn validate_authority_context_collection_bounds(",
            "    value: &PracticeAuthorityContextV1,",
            ") -> Result<(), PracticeContractError> {",
            "    if value.policy_authorities.len() > MAX_POLICY_AUTHORITY_PAIRS {",
            "        return Err(PracticeContractError::PracticeAuthorityRegistryLimit);",
            "    }",
            "    Ok(())",
            "}",
            "",
            "/// Checks shape-only topology collections against their contract bounds.",
            "///",
            "/// # Errors",
            "///",
            "/// Returns the assigned organization or footprint bound error.",
            "pub fn validate_topology_collection_bounds(",
            "    value: &OrganizationPracticeTopologyV1,",
            ") -> Result<(), PracticeContractError> {",
            "    if value.organizations.len() > MAX_ORGANIZATIONS {",
            "        return Err(PracticeContractError::PracticeTopologyOrganizationLimit);",
            "    }",
            "    for row in value.organizations.iter().take(MAX_ORGANIZATIONS + 1) {",
            "        if row.edges.len() > MAX_ORG_SOLIDARITY_EDGES_PER_ORG {",
            "            return Err(PracticeContractError::PracticeFootprintLimit);",
            "        }",
            "    }",
            "    Ok(())",
            "}",
            "",
        ]
    )
    return lines


def render_rust(spec: PracticeContractSpec) -> str:
    lines = [
        f"// Generated from contracts/practice_contract_v1.yaml; sha256={spec.source_digest}",
        "",
    ]
    lines.extend(_render_rust_errors(spec))
    for name, row in islice(spec.raw["enums"].items(), MAX_ENUMS + 1):
        lines.extend(_render_rust_enum(name, row["width"], row["members"]))
    lines.extend(_render_rust_records(spec))
    lines.extend(_render_rust_api(spec))
    return "\n".join(lines)


def _check_output(path: Path, expected: str) -> bool:
    try:
        return path.read_text(encoding="utf-8") == expected
    except FileNotFoundError:
        return False


def _write_outputs(python_path: Path, python_text: str, rust_path: Path, rust_text: str) -> None:
    python_path.parent.mkdir(parents=True, exist_ok=True)
    rust_path.parent.mkdir(parents=True, exist_ok=True)
    python_path.write_text(python_text, encoding="utf-8")
    rust_path.write_text(rust_text, encoding="utf-8")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--python-out", type=Path, default=DEFAULT_PYTHON_OUT)
    parser.add_argument("--rust-out", type=Path, default=DEFAULT_RUST_OUT)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    spec = load_practice_contract(args.contract)
    python_text = render_python(spec)
    rust_text = render_rust(spec)
    if args.check:
        return int(
            not (
                _check_output(args.python_out, python_text)
                and _check_output(args.rust_out, rust_text)
            )
        )
    _write_outputs(args.python_out, python_text, args.rust_out, rust_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
