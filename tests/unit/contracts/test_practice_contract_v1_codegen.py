"""Behavioral contract for the closed, non-live practice schema."""

from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
import yaml
from pydantic import TypeAdapter, ValidationError
from tools.generate_practice_contract_types import (
    MAX_DEPTH,
    MAX_ENUM_MEMBERS,
    MAX_ENUMS,
    MAX_ERROR_CODES,
    MAX_FIELDS,
    MAX_RECORDS,
    MAX_SOURCE_BYTES,
    MAX_YAML_EVENTS,
    PracticeSchemaError,
    PracticeSchemaViolation,
    _read_source,
    load_practice_contract,
)

ROOT = Path(__file__).parents[3]
CONTRACT_PATH = ROOT / "contracts" / "practice_contract_v1.yaml"
ADR_PATH = ROOT / "ai" / "decisions" / "ADR227_practice_contract_groundwork.yaml"
INDEX_PATH = ROOT / "ai" / "decisions" / "index.yaml"
GENERATOR_PATH = ROOT / "tools" / "generate_practice_contract_types.py"
PYTHON_GENERATED_PATH = ROOT / "src" / "babylon" / "contracts" / "practice_contract_v1_generated.py"
RUST_GENERATED_PATH = (
    ROOT / "rust" / "crates" / "babylon-practice-contract" / "src" / "generated.rs"
)

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


def _generated_module() -> Any:
    return importlib.import_module("babylon.contracts.practice_contract_v1_generated")


def _valid_generated_records(generated: Any) -> dict[str, tuple[type[Any], dict[str, Any]]]:
    zero_digest = b"\x00" * 32
    budget_terms = generated.PracticeBudgetTermsV1(
        initial=1,
        weekly_credit_cap=1,
        storage_ceiling=4,
        organize_cost=1,
        agitate_cost=1,
        mutual_aid_cost=1,
    )
    parameter = generated.PracticeParameterV1(
        key_u8=0,
        value_kind_u8=0,
        value_length_u16=0,
        value_bytes=b"",
    )
    policy_pair = generated.PolicyAuthorityPairV1(
        producer_content_digest=zero_digest,
        actor_org_id=1,
    )
    topology_edge = generated.OrganizationPracticeTopologyEdgeV1(
        target_domain=generated.PracticeTargetDomainV1.SOCIAL_CLASS,
        target_class_node_id_u64=2,
    )
    topology_row = generated.OrganizationPracticeTopologyRowV1(
        node_id_u64=1,
        active_bool=True,
        action_budget_storage_f64_bits_u64=0,
        edges=(topology_edge,),
    )
    return {
        "MachineVerbV1": (
            generated.MachineVerbV1,
            {
                "stem": generated.VerbStemV1.MOBILIZE,
                "mode": generated.VerbModeV1.CANVASS,
            },
        ),
        "PracticeInputAuthorityV1": (
            generated.PracticeInputAuthorityV1,
            {
                "schema_version": 1,
                "authority_kind": generated.PracticeAuthorityKindV1.PLAYER_SEAT,
                "actor_org_id": 1,
                "producer_content_digest": zero_digest,
            },
        ),
        "PracticeParameterV1": (
            generated.PracticeParameterV1,
            parameter.model_dump(),
        ),
        "PracticeIntentV1": (
            generated.PracticeIntentV1,
            {
                "schema_version": 1,
                "submit_after_tick": 0,
                "resolve_tick": 1,
                "actor_org_id": 1,
                "practice_id": generated.PracticeIdV1.ORGANIZE,
                "target_domain": generated.PracticeTargetDomainV1.SOCIAL_CLASS,
                "target_node_id": 2,
                "quoted_content_digest": zero_digest,
                "quoted_action_budget_cost": 1,
                "parameters": (),
                "evidence_digests": (),
            },
        ),
        "PolicyAuthorityPairV1": (
            generated.PolicyAuthorityPairV1,
            policy_pair.model_dump(),
        ),
        "PracticeAuthorityContextV1": (
            generated.PracticeAuthorityContextV1,
            {
                "player_org_id": 1,
                "player_gateway_content_digest": zero_digest,
                "policy_authorities": (policy_pair,),
            },
        ),
        "PracticeQuoteContextV1": (
            generated.PracticeQuoteContextV1,
            {
                "last_committed_tick": 0,
                "content_digest": zero_digest,
                "budget_terms": budget_terms,
            },
        ),
        "SolidarityFootprintEdgeV1": (
            generated.SolidarityFootprintEdgeV1,
            {
                "source_org_node_id_u64": 1,
                "target_domain_u8": generated.PracticeTargetDomainV1.SOCIAL_CLASS,
                "target_class_node_id_u64": 2,
                "strength_f64_bits_u64": 0x3FF0000000000000,
            },
        ),
        "OrganizationPracticeTopologyEdgeV1": (
            generated.OrganizationPracticeTopologyEdgeV1,
            topology_edge.model_dump(),
        ),
        "OrganizationPracticeTopologyRowV1": (
            generated.OrganizationPracticeTopologyRowV1,
            topology_row.model_dump(),
        ),
        "OrganizationPracticeTopologyV1": (
            generated.OrganizationPracticeTopologyV1,
            {"organizations": (topology_row,)},
        ),
        "OrganizationBudgetDeltaV1": (
            generated.OrganizationBudgetDeltaV1,
            {
                "schema_version": 1,
                "tick": 1,
                "actor_node_id": 1,
                "pre_action_world_hash": zero_digest,
                "budget_before": 1,
                "governed_cost": 1,
                "footprint_count": 0,
                "raw_credit": 0,
                "credited_credit": 0,
                "ceiling_bound": False,
                "budget_after": 0,
            },
        ),
        "PracticeSubmissionRejectionV1": (
            generated.PracticeSubmissionRejectionV1,
            {
                "schema_version": 1,
                "submitted_bytes_digest": zero_digest,
                "reason_code": generated.PracticeRejectionCodeV1.PRACTICE_UNWIRED,
                "last_committed_tick": 0,
                "content_digest": zero_digest,
            },
        ),
        "PracticeBudgetTermsV1": (
            generated.PracticeBudgetTermsV1,
            budget_terms.model_dump(),
        ),
    }


def test_generator_check_refuses_absent_outputs(tmp_path: Path) -> None:
    python_output = tmp_path / "missing.py"
    rust_output = tmp_path / "missing.rs"
    result = subprocess.run(
        [
            sys.executable,
            str(GENERATOR_PATH),
            "--check",
            "--python-out",
            str(python_output),
            "--rust-out",
            str(rust_output),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert not python_output.exists()
    assert not rust_output.exists()


@pytest.mark.parametrize(
    ("mutation", "expected_error"),
    [
        ("missing_agitate", PracticeSchemaError.MissingCode),
        ("fourth_mode", PracticeSchemaError.MappingMismatch),
    ],
)
def test_generator_invalid_contract_check_preserves_both_outputs(
    tmp_path: Path,
    mutation: str,
    expected_error: PracticeSchemaError,
) -> None:
    document = _loaded_document()
    if mutation == "missing_agitate":
        del document["enums"]["PracticeIdV1"]["members"]["AGITATE"]
    else:
        document["enums"]["VerbModeV1"]["members"]["FOURTH_MODE"] = 3
    invalid_contract = _dump_mutation(tmp_path, document)

    with pytest.raises(PracticeSchemaViolation) as raised:
        load_practice_contract(invalid_contract)
    assert raised.value.error is expected_error

    before_python = PYTHON_GENERATED_PATH.read_bytes()
    before_rust = RUST_GENERATED_PATH.read_bytes()
    result = subprocess.run(
        [
            sys.executable,
            str(GENERATOR_PATH),
            "--check",
            "--contract",
            str(invalid_contract),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert PYTHON_GENERATED_PATH.read_bytes() == before_python
    assert RUST_GENERATED_PATH.read_bytes() == before_rust


def test_generated_outputs_are_current_and_strict() -> None:
    assert GENERATOR_PATH.is_file()
    assert PYTHON_GENERATED_PATH.is_file()
    assert RUST_GENERATED_PATH.is_file()
    result = subprocess.run(
        [sys.executable, str(GENERATOR_PATH), "--check"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    generated = _generated_module()
    for model_name in (
        "MachineVerbV1",
        *EXPECTED_RECORD_FIELDS,
    ):
        config = getattr(generated, model_name).model_config
        assert config["frozen"] is True
        assert config["extra"] == "forbid"
        assert config["strict"] is True


def test_generated_wire_domain_bytes_and_terminator_are_exact() -> None:
    generated = _generated_module()
    assert generated.PRACTICE_INPUT_AUTHORITY_V1_DOMAIN_BYTES == (
        b"babylon.practice-input-authority.v1"
    )
    assert generated.PRACTICE_INTENT_V1_DOMAIN_BYTES == b"babylon.practice-intent.v1"
    assert generated.ORGANIZATION_BUDGET_DELTA_V1_DOMAIN_BYTES == (
        b"babylon.organization-budget-delta.v1"
    )
    assert generated.PRACTICE_WIRE_DOMAIN_TERMINATOR_BYTES == b"\x00"


def test_generated_python_enums_and_machine_mapping_are_closed() -> None:
    generated = _generated_module()
    expected = {
        generated.PracticeIdV1.ORGANIZE: (
            generated.VerbStemV1.MOBILIZE,
            generated.VerbModeV1.CANVASS,
        ),
        generated.PracticeIdV1.AGITATE: (
            generated.VerbStemV1.MOBILIZE,
            generated.VerbModeV1.AGITATE,
        ),
        generated.PracticeIdV1.MUTUAL_AID: (generated.VerbStemV1.AID, None),
    }
    for practice, (stem, mode) in expected.items():
        machine = generated.machine_verb_for(practice)
        assert machine.stem is stem
        assert machine.mode is mode
    for enum_type in (
        generated.PracticeIdV1,
        generated.VerbStemV1,
        generated.VerbModeV1,
        generated.PracticeAuthorityKindV1,
        generated.PracticeTargetDomainV1,
        generated.PracticeRejectionCodeV1,
        generated.PracticeActivationBlockerV1,
        generated.PracticeContractError,
    ):
        with pytest.raises(ValidationError):
            TypeAdapter(enum_type).validate_python(1, strict=True)


@pytest.mark.parametrize(
    ("model_name", "field_name", "cross_enum"),
    [
        ("MachineVerbV1", "stem", "PracticeIdV1"),
        ("MachineVerbV1", "mode", "PracticeIdV1"),
        ("PracticeInputAuthorityV1", "authority_kind", "PracticeIdV1"),
        ("PracticeIntentV1", "practice_id", "PracticeTargetDomainV1"),
        ("PracticeIntentV1", "target_domain", "PracticeIdV1"),
        ("SolidarityFootprintEdgeV1", "target_domain_u8", "PracticeIdV1"),
        ("OrganizationPracticeTopologyEdgeV1", "target_domain", "PracticeIdV1"),
        ("PracticeSubmissionRejectionV1", "reason_code", "PracticeIdV1"),
    ],
)
def test_generated_record_enum_fields_reject_raw_and_cross_enum_values(
    model_name: str,
    field_name: str,
    cross_enum: str,
) -> None:
    generated = _generated_module()
    model, values = _valid_generated_records(generated)[model_name]
    invalid_values = (1, getattr(generated, cross_enum)(1))
    for invalid in invalid_values:
        with pytest.raises(ValidationError):
            model.model_validate({**values, field_name: invalid})


def test_generated_python_rejects_non_strict_shapes() -> None:
    generated = _generated_module()
    records = _valid_generated_records(generated)
    for model_name, field_name in (
        ("OrganizationPracticeTopologyRowV1", "active_bool"),
        ("OrganizationBudgetDeltaV1", "ceiling_bound"),
    ):
        model, values = records[model_name]
        for invalid in (0, 1, "true"):
            with pytest.raises(ValidationError):
                model.model_validate({**values, field_name: invalid})
    for model_name, field_name in (
        ("PracticeIntentV1", "parameters"),
        ("PracticeIntentV1", "evidence_digests"),
        ("PracticeAuthorityContextV1", "policy_authorities"),
        ("OrganizationPracticeTopologyRowV1", "edges"),
        ("OrganizationPracticeTopologyV1", "organizations"),
    ):
        model, values = records[model_name]
        with pytest.raises(ValidationError):
            model.model_validate({**values, field_name: []})
    parameter_model, parameter_values = records["PracticeParameterV1"]
    with pytest.raises(ValidationError):
        parameter_model.model_validate({**parameter_values, "value_bytes": ""})


def test_generated_python_rejects_every_bad_digest_shape() -> None:
    generated = _generated_module()
    records = _valid_generated_records(generated)
    direct_digest_fields = (
        ("PracticeInputAuthorityV1", "producer_content_digest"),
        ("PracticeIntentV1", "quoted_content_digest"),
        ("PolicyAuthorityPairV1", "producer_content_digest"),
        ("PracticeAuthorityContextV1", "player_gateway_content_digest"),
        ("PracticeQuoteContextV1", "content_digest"),
        ("OrganizationBudgetDeltaV1", "pre_action_world_hash"),
        ("PracticeSubmissionRejectionV1", "submitted_bytes_digest"),
        ("PracticeSubmissionRejectionV1", "content_digest"),
    )
    for model_name, field_name in direct_digest_fields:
        model, values = records[model_name]
        for invalid in (b"x" * 31, b"x" * 33, "x" * 32):
            with pytest.raises(ValidationError):
                model.model_validate({**values, field_name: invalid})
    intent_model, intent_values = records["PracticeIntentV1"]
    for invalid in (b"x" * 31, b"x" * 33):
        with pytest.raises(ValidationError):
            intent_model.model_validate({**intent_values, "evidence_digests": (invalid,)})


def test_generated_python_rejects_unsigned_width_violations() -> None:
    generated = _generated_module()
    records = _valid_generated_records(generated)
    unsigned_fields = (
        ("PracticeInputAuthorityV1", "schema_version", 16),
        ("PracticeInputAuthorityV1", "actor_org_id", 64),
        ("PracticeParameterV1", "key_u8", 8),
        ("PracticeParameterV1", "value_kind_u8", 8),
        ("PracticeParameterV1", "value_length_u16", 16),
        ("PracticeIntentV1", "submit_after_tick", 64),
        ("PracticeIntentV1", "schema_version", 16),
        ("PracticeIntentV1", "resolve_tick", 64),
        ("PracticeIntentV1", "actor_org_id", 64),
        ("PracticeIntentV1", "target_node_id", 64),
        ("PracticeIntentV1", "quoted_action_budget_cost", 32),
        ("PolicyAuthorityPairV1", "actor_org_id", 64),
        ("PracticeAuthorityContextV1", "player_org_id", 64),
        ("PracticeQuoteContextV1", "last_committed_tick", 64),
        ("SolidarityFootprintEdgeV1", "source_org_node_id_u64", 64),
        ("SolidarityFootprintEdgeV1", "target_class_node_id_u64", 64),
        ("SolidarityFootprintEdgeV1", "strength_f64_bits_u64", 64),
        ("OrganizationPracticeTopologyEdgeV1", "target_class_node_id_u64", 64),
        ("OrganizationPracticeTopologyRowV1", "node_id_u64", 64),
        ("OrganizationPracticeTopologyRowV1", "action_budget_storage_f64_bits_u64", 64),
        ("OrganizationBudgetDeltaV1", "tick", 64),
        ("OrganizationBudgetDeltaV1", "schema_version", 16),
        ("OrganizationBudgetDeltaV1", "actor_node_id", 64),
        ("OrganizationBudgetDeltaV1", "budget_before", 32),
        ("OrganizationBudgetDeltaV1", "governed_cost", 32),
        ("OrganizationBudgetDeltaV1", "footprint_count", 32),
        ("OrganizationBudgetDeltaV1", "raw_credit", 32),
        ("OrganizationBudgetDeltaV1", "credited_credit", 32),
        ("OrganizationBudgetDeltaV1", "budget_after", 32),
        ("PracticeSubmissionRejectionV1", "schema_version", 16),
        ("PracticeSubmissionRejectionV1", "last_committed_tick", 64),
        ("PracticeBudgetTermsV1", "initial", 32),
        ("PracticeBudgetTermsV1", "weekly_credit_cap", 32),
        ("PracticeBudgetTermsV1", "storage_ceiling", 32),
        ("PracticeBudgetTermsV1", "organize_cost", 32),
        ("PracticeBudgetTermsV1", "agitate_cost", 32),
        ("PracticeBudgetTermsV1", "mutual_aid_cost", 32),
    )
    for model_name, field_name, width in unsigned_fields:
        model, values = records[model_name]
        for invalid in (-1, 2**width):
            with pytest.raises(ValidationError):
                model.model_validate({**values, field_name: invalid})


def test_generated_tuple_constructors_are_shape_only_but_validators_are_bounded() -> None:
    generated = _generated_module()
    records = _valid_generated_records(generated)
    parameter_model, parameter_values = records["PracticeParameterV1"]
    parameter = parameter_model.model_validate(parameter_values)
    intent_model, intent_values = records["PracticeIntentV1"]
    intent = intent_model.model_validate({**intent_values, "parameters": (parameter,) * 17})
    assert generated.validate_intent_collection_bounds(intent) is (
        generated.PracticeContractError.PRACTICE_PARAMETER_LIMIT
    )
    intent = intent_model.model_validate(
        {**intent_values, "evidence_digests": (b"\x00" * 32,) * 65}
    )
    assert generated.validate_intent_collection_bounds(intent) is (
        generated.PracticeContractError.PRACTICE_EVIDENCE_LIMIT
    )
    policy_model, policy_values = records["PolicyAuthorityPairV1"]
    policy = policy_model.model_validate(policy_values)
    authority_model, authority_values = records["PracticeAuthorityContextV1"]
    authority = authority_model.model_validate(
        {**authority_values, "policy_authorities": (policy,) * 4_097}
    )
    assert generated.validate_authority_context_collection_bounds(authority) is (
        generated.PracticeContractError.PRACTICE_AUTHORITY_REGISTRY_LIMIT
    )
    row_model, row_values = records["OrganizationPracticeTopologyRowV1"]
    row = row_model.model_validate(row_values)
    topology_model, topology_values = records["OrganizationPracticeTopologyV1"]
    topology = topology_model.model_validate({**topology_values, "organizations": (row,) * 4_097})
    assert generated.validate_topology_collection_bounds(topology) is (
        generated.PracticeContractError.PRACTICE_TOPOLOGY_ORGANIZATION_LIMIT
    )
    edge_model, edge_values = records["OrganizationPracticeTopologyEdgeV1"]
    edge = edge_model.model_validate(edge_values)
    row = row_model.model_validate({**row_values, "edges": (edge,) * 257})
    topology = topology_model.model_validate({**topology_values, "organizations": (row,)})
    assert generated.validate_topology_collection_bounds(topology) is (
        generated.PracticeContractError.PRACTICE_FOOTPRINT_LIMIT
    )
