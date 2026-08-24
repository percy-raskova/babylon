# Generated from contracts/practice_contract_v1.yaml; sha256=e9ed6dbaf01f89f1294f2e6d28946e73b05d9a4d75472d5b2dd352350d332f79
from __future__ import annotations

from enum import IntEnum
from itertools import islice
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

U8 = Annotated[int, Field(strict=True, ge=0, le=255)]
U16 = Annotated[int, Field(strict=True, ge=0, le=65_535)]
U32 = Annotated[int, Field(strict=True, ge=0, le=4_294_967_295)]
U64 = Annotated[int, Field(strict=True, ge=0, le=18_446_744_073_709_551_615)]
Digest32 = Annotated[bytes, Field(strict=True, min_length=32, max_length=32)]
PRACTICE_INPUT_AUTHORITY_V1_DOMAIN_BYTES = b"babylon.practice-input-authority.v1"
PRACTICE_INTENT_V1_DOMAIN_BYTES = b"babylon.practice-intent.v1"
ORGANIZATION_BUDGET_DELTA_V1_DOMAIN_BYTES = b"babylon.organization-budget-delta.v1"
PRACTICE_WIRE_DOMAIN_TERMINATOR_BYTES = b"\x00"


class PracticeIdV1(IntEnum):
    ORGANIZE = 1
    AGITATE = 2
    MUTUAL_AID = 3


class VerbStemV1(IntEnum):
    MOBILIZE = 1
    AID = 2


class VerbModeV1(IntEnum):
    CANVASS = 1
    AGITATE = 2


class PracticeAuthorityKindV1(IntEnum):
    PLAYER_SEAT = 1
    DETERMINISTIC_POLICY = 2


class PracticeTargetDomainV1(IntEnum):
    SOCIAL_CLASS = 1


class PracticeRejectionCodeV1(IntEnum):
    PRACTICE_UNWIRED = 1
    PRACTICE_STALE_CONTENT = 2
    PRACTICE_COST_MISMATCH = 3
    PRACTICE_AUTHORITY_UNREGISTERED = 4
    PRACTICE_ACTOR_MISMATCH = 5
    PRACTICE_DUPLICATE_ACTOR = 6
    PRACTICE_BATCH_LIMIT = 7
    PRACTICE_TICK_MISMATCH = 8
    PRACTICE_BUDGET_INSUFFICIENT = 9
    PRACTICE_TARGET_INELIGIBLE = 10
    PRACTICE_PENDING_DUPLICATE = 11


class PracticeActivationBlockerV1(IntEnum):
    GATE3_COMMITTED_ENVELOPE = 1
    GATE5_PENDING_INPUT = 2
    PER30_ORDERS_INVENTORY = 3
    PER31_FREIGHT_REALIZATION = 4


class PracticeContractError(IntEnum):
    PRACTICE_DOMAIN = 1
    PRACTICE_SCHEMA_VERSION = 2
    PRACTICE_ENUM_CODE = 3
    PRACTICE_LENGTH = 5
    PRACTICE_TRUNCATED = 6
    PRACTICE_TRAILING_BYTES = 7
    PRACTICE_BOOLEAN = 9
    PRACTICE_PARAMETER = 10
    PRACTICE_PARAMETER_LIMIT = 11
    PRACTICE_PARAMETER_LENGTH = 12
    PRACTICE_EVIDENCE_LIMIT = 13
    PRACTICE_EVIDENCE_ORDER = 14
    PRACTICE_EVIDENCE_DUPLICATE = 15
    PRACTICE_TICK_OVERFLOW = 16
    PRACTICE_TICK_MISMATCH = 17
    PRACTICE_AUTHORITY_REGISTRY_LIMIT = 18
    PRACTICE_AUTHORITY_REGISTRY_ORDER = 19
    PRACTICE_AUTHORITY_REGISTRY_DUPLICATE = 20
    PRACTICE_AUTHORITY_UNREGISTERED = 21
    PRACTICE_ACTOR_MISMATCH = 22
    PRACTICE_AUTHORITY_CONTENT_MISMATCH = 23
    PRACTICE_QUOTE_CONTENT_MISMATCH = 24
    PRACTICE_QUOTE_COST_MISMATCH = 25
    PRACTICE_BATCH_LIMIT = 26
    PRACTICE_DUPLICATE_ACTOR = 27
    PRACTICE_BUDGET_NONFINITE = 28
    PRACTICE_BUDGET_NEGATIVE = 29
    PRACTICE_BUDGET_FRACTIONAL = 30
    PRACTICE_BUDGET_RANGE = 31
    PRACTICE_BUDGET_ROUNDTRIP = 32
    PRACTICE_BUDGET_INSUFFICIENT = 33
    PRACTICE_BUDGET_ARITHMETIC = 34
    PRACTICE_FOOTPRINT_LIMIT = 35
    PRACTICE_FOOTPRINT_ORDER = 36
    PRACTICE_FOOTPRINT_DUPLICATE = 37
    PRACTICE_FOOTPRINT_SOURCE = 38
    PRACTICE_FOOTPRINT_STRENGTH_NONFINITE = 39
    PRACTICE_FOOTPRINT_STRENGTH_NONPOSITIVE = 40
    PRACTICE_TOPOLOGY_ORGANIZATION_LIMIT = 41
    PRACTICE_TOPOLOGY_ORGANIZATION_ORDER = 42
    PRACTICE_TOPOLOGY_ORGANIZATION_DUPLICATE = 43
    PRACTICE_TOPOLOGY_BUDGET_MISSING = 44
    PRACTICE_TOPOLOGY_EDGE_ORDER = 45
    PRACTICE_TOPOLOGY_EDGE_DUPLICATE = 46


class MachineVerbV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    stem: VerbStemV1
    mode: VerbModeV1 | None


class PracticeInputAuthorityV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    schema_version: U16
    authority_kind: PracticeAuthorityKindV1
    actor_org_id: U64
    producer_content_digest: Digest32


class PracticeParameterV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    key_u8: U8
    value_kind_u8: U8
    value_length_u16: U16
    value_bytes: bytes


class PracticeIntentV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    schema_version: U16
    submit_after_tick: U64
    resolve_tick: U64
    actor_org_id: U64
    practice_id: PracticeIdV1
    target_domain: PracticeTargetDomainV1
    target_node_id: U64
    quoted_content_digest: Digest32
    quoted_action_budget_cost: U32
    parameters: tuple[PracticeParameterV1, ...]
    evidence_digests: tuple[Digest32, ...]


class PolicyAuthorityPairV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    producer_content_digest: Digest32
    actor_org_id: U64


class PracticeAuthorityContextV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    player_org_id: U64
    player_gateway_content_digest: Digest32
    policy_authorities: tuple[PolicyAuthorityPairV1, ...]


class PracticeQuoteContextV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    last_committed_tick: U64
    content_digest: Digest32
    budget_terms: PracticeBudgetTermsV1


class SolidarityFootprintEdgeV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    source_org_node_id_u64: U64
    target_domain_u8: PracticeTargetDomainV1
    target_class_node_id_u64: U64
    strength_f64_bits_u64: U64


class OrganizationPracticeTopologyEdgeV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    target_domain: PracticeTargetDomainV1
    target_class_node_id_u64: U64


class OrganizationPracticeTopologyRowV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    node_id_u64: U64
    active_bool: bool
    action_budget_storage_f64_bits_u64: U64 | None
    edges: tuple[OrganizationPracticeTopologyEdgeV1, ...]


class OrganizationPracticeTopologyV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    organizations: tuple[OrganizationPracticeTopologyRowV1, ...]


class OrganizationBudgetDeltaV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    schema_version: U16
    tick: U64
    actor_node_id: U64
    pre_action_world_hash: Digest32
    budget_before: U32
    governed_cost: U32
    footprint_count: U32
    raw_credit: U32
    credited_credit: U32
    ceiling_bound: bool
    budget_after: U32


class PracticeSubmissionRejectionV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    schema_version: U16
    submitted_bytes_digest: Digest32
    reason_code: PracticeRejectionCodeV1
    last_committed_tick: U64
    content_digest: Digest32


class PracticeBudgetTermsV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    initial: U32
    weekly_credit_cap: U32
    storage_ceiling: U32
    organize_cost: U32
    agitate_cost: U32
    mutual_aid_cost: U32


MAX_PARAMETERS = 16
MAX_PARAMETER_VALUE_BYTES = 256
MAX_PARAMETER_BYTES = 256
MAX_EVIDENCE_DIGESTS = 64
MAX_INTENT_CANONICAL_BYTES = 16384
MAX_POLICY_AUTHORITY_PAIRS = 4096
MAX_INTENTS_PER_RESOLVE_TICK = 4096
MAX_ORGANIZATIONS = 4096
MAX_ORG_SOLIDARITY_EDGES_PER_ORG = 256
MAX_JSONL_SOURCE_BYTES = 2097152
MAX_JSONL_CASES = 512
MAX_JSONL_LINE_BYTES = 65536
MAX_JSONL_CASE_ID_BYTES = 128
MAX_JSON_DEPTH = 32


def machine_verb_for(practice: PracticeIdV1) -> MachineVerbV1:
    if type(practice) is not PracticeIdV1:
        raise TypeError("practice must be PracticeIdV1")
    if practice is PracticeIdV1.ORGANIZE:
        return MachineVerbV1(stem=VerbStemV1.MOBILIZE, mode=VerbModeV1.CANVASS)
    if practice is PracticeIdV1.AGITATE:
        return MachineVerbV1(stem=VerbStemV1.MOBILIZE, mode=VerbModeV1.AGITATE)
    return MachineVerbV1(stem=VerbStemV1.AID, mode=None)


def validate_intent_collection_bounds(
    value: PracticeIntentV1,
) -> PracticeContractError | None:
    if len(value.parameters) > MAX_PARAMETERS:
        return PracticeContractError.PRACTICE_PARAMETER_LIMIT
    if len(value.evidence_digests) > MAX_EVIDENCE_DIGESTS:
        return PracticeContractError.PRACTICE_EVIDENCE_LIMIT
    return None


def validate_authority_context_collection_bounds(
    value: PracticeAuthorityContextV1,
) -> PracticeContractError | None:
    if len(value.policy_authorities) > MAX_POLICY_AUTHORITY_PAIRS:
        return PracticeContractError.PRACTICE_AUTHORITY_REGISTRY_LIMIT
    return None


def validate_topology_collection_bounds(
    value: OrganizationPracticeTopologyV1,
) -> PracticeContractError | None:
    if len(value.organizations) > MAX_ORGANIZATIONS:
        return PracticeContractError.PRACTICE_TOPOLOGY_ORGANIZATION_LIMIT
    for row in islice(value.organizations, MAX_ORGANIZATIONS + 1):
        if len(row.edges) > MAX_ORG_SOLIDARITY_EDGES_PER_ORG:
            return PracticeContractError.PRACTICE_FOOTPRINT_LIMIT
    return None
