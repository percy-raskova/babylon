"""Detached codecs and pure admission checks for the T2 practice contract."""

from __future__ import annotations

import json
import math
import struct
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import IntEnum
from hashlib import sha256
from io import BytesIO
from itertools import islice
from types import MappingProxyType

from babylon.contracts.practice_contract_v1_generated import (
    MAX_EVIDENCE_DIGESTS,
    MAX_INTENT_CANONICAL_BYTES,
    MAX_INTENTS_PER_RESOLVE_TICK,
    MAX_JSON_DEPTH,
    MAX_JSONL_CASE_ID_BYTES,
    MAX_JSONL_CASES,
    MAX_JSONL_LINE_BYTES,
    MAX_JSONL_SOURCE_BYTES,
    MAX_ORG_SOLIDARITY_EDGES_PER_ORG,
    MAX_ORGANIZATIONS,
    MAX_PARAMETER_VALUE_BYTES,
    MAX_PARAMETERS,
    MAX_POLICY_AUTHORITY_PAIRS,
    ORGANIZATION_BUDGET_DELTA_V1_DOMAIN_BYTES,
    PRACTICE_INPUT_AUTHORITY_V1_DOMAIN_BYTES,
    PRACTICE_INTENT_V1_DOMAIN_BYTES,
    PRACTICE_WIRE_DOMAIN_TERMINATOR_BYTES,
    OrganizationBudgetDeltaV1,
    OrganizationPracticeTopologyV1,
    PolicyAuthorityPairV1,
    PracticeAuthorityContextV1,
    PracticeAuthorityKindV1,
    PracticeBudgetTermsV1,
    PracticeContractError,
    PracticeIdV1,
    PracticeInputAuthorityV1,
    PracticeIntentV1,
    PracticeParameterV1,
    PracticeQuoteContextV1,
    PracticeRejectionCodeV1,
    PracticeSubmissionRejectionV1,
    PracticeTargetDomainV1,
    SolidarityFootprintEdgeV1,
)

_SCHEMA_VERSION = 1
_U8_MAX = (1 << 8) - 1
_U16_MAX = (1 << 16) - 1
_U32_MAX = (1 << 32) - 1
_U64_MAX = (1 << 64) - 1
_DIGEST_BYTES = 32
_PARAMETER_DIGEST_DOMAIN = b"babylon.practice-parameter-bytes.v1"
_FIXED_TARGET_DOMAIN = b"babylon.fixed-target-selection.v1"
_KNOWN_VECTOR_KINDS = frozenset(
    {
        "manifest",
        "authority",
        "intent",
        "budget_delta",
        "rejection",
        "invalid_wire",
        "authority_validation",
        "quote_validation",
        "batch_recipe",
    }
)
_VECTOR_DATA_FIELDS = {
    "manifest": frozenset({"parameter_limit_valid_witness", "intent_truncation_offsets"}),
    "authority": frozenset(
        {
            "authority_kind",
            "actor_org_id",
            "producer_content_digest_hex",
            "canonical_hex",
            "digest_hex",
        }
    ),
    "intent": frozenset(
        {
            "practice_id",
            "actor_org_id",
            "target_node_id",
            "quoted_content_digest_hex",
            "quoted_action_budget_cost",
            "evidence_digests_hex",
            "canonical_hex",
            "digest_hex",
            "parameter_hex",
            "parameter_digest_hex",
            "target_preimage_hex",
            "target_digest_hex",
        }
    ),
    "budget_delta": frozenset({"canonical_hex", "digest_hex"}),
    "rejection": frozenset({"reason_code", "canonical_hex"}),
    "invalid_wire": frozenset({"codec", "payload_hex", "error"}),
    "authority_validation": frozenset({"recipe", "error"}),
    "quote_validation": frozenset({"recipe", "error"}),
    "batch_recipe": frozenset({"count", "recipe", "error"}),
}


class PracticeContractViolation(ValueError):
    """One governed practice-contract refusal."""

    __slots__ = ("_error",)
    _error: PracticeContractError

    def __init__(self, error: PracticeContractError) -> None:
        if type(error) is not PracticeContractError:
            raise TypeError("error must be PracticeContractError")
        object.__setattr__(self, "_error", error)
        super().__init__(error.name)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError(f"{name} is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError(f"{name} is immutable")

    @property
    def error(self) -> PracticeContractError:
        """Return the immutable governed error identity."""
        return self._error


class PracticeVectorCorpusError(ValueError):
    """A local malformed-corpus refusal with no wire identity."""


@dataclass(frozen=True, slots=True)
class PracticeVectorCaseV1:
    """One closed shared vector envelope."""

    case_id: str
    kind: str
    data: Mapping[str, object]


def _fail(error: PracticeContractError) -> PracticeContractViolation:
    return PracticeContractViolation(error)


def _require_exact(value: object, expected: type[object], name: str) -> None:
    if type(value) is not expected:
        raise TypeError(f"{name} must be {expected.__name__}")


def _require_u64(value: object, name: str) -> int:
    if type(value) is not int:
        raise TypeError(f"{name} must be int")
    if value < 0 or value > _U64_MAX:
        raise ValueError(f"{name} must fit u64")
    return value


def _require_u32(value: object, name: str) -> int:
    if type(value) is not int:
        raise TypeError(f"{name} must be int")
    if value < 0 or value > _U32_MAX:
        raise ValueError(f"{name} must fit u32")
    return value


def _practice_budget_terms_from_defines(
    cls: type[PracticeBudgetTermsV1], defines: object
) -> PracticeBudgetTermsV1:
    from babylon.config.defines import GameDefines

    if type(defines) is not GameDefines:
        raise TypeError("defines must be GameDefines")
    budget = defines.practice_budget
    return cls(
        initial=budget.action_budget_initial,
        weekly_credit_cap=budget.action_budget_weekly_credit_cap,
        storage_ceiling=budget.action_budget_storage_ceiling,
        organize_cost=budget.organize_action_budget_cost,
        agitate_cost=budget.agitate_action_budget_cost,
        mutual_aid_cost=budget.mutual_aid_action_budget_cost,
    )


PracticeBudgetTermsV1.from_defines = classmethod(  # type: ignore[attr-defined]
    _practice_budget_terms_from_defines
)


def read_action_budget(storage: float) -> int:
    """Convert one canonical binary64 ActionBudget storage value to ``u32``."""
    if type(storage) is not float:
        raise TypeError("storage must be float")
    if not math.isfinite(storage):
        raise _fail(PracticeContractError.PRACTICE_BUDGET_NONFINITE)
    if storage < 0.0:
        raise _fail(PracticeContractError.PRACTICE_BUDGET_NEGATIVE)
    if not storage.is_integer():
        raise _fail(PracticeContractError.PRACTICE_BUDGET_FRACTIONAL)
    if storage > float(_U32_MAX):
        raise _fail(PracticeContractError.PRACTICE_BUDGET_RANGE)
    value = int(storage)
    if struct.pack(">d", storage) != struct.pack(">d", float(value)):
        raise _fail(PracticeContractError.PRACTICE_BUDGET_ROUNDTRIP)
    return value


def write_action_budget(value: int) -> float:
    """Convert one ``u32`` ActionBudget to canonical binary64 storage."""
    return float(_require_u32(value, "value"))


def _strength_from_bits(bits: int) -> float:
    return float(struct.unpack(">d", bits.to_bytes(8, "big"))[0])


def _validate_footprint(
    actor_node_id: int,
    footprint_edges: Sequence[SolidarityFootprintEdgeV1],
) -> int:
    if len(footprint_edges) > MAX_ORG_SOLIDARITY_EDGES_PER_ORG:
        raise _fail(PracticeContractError.PRACTICE_FOOTPRINT_LIMIT)
    previous: tuple[int, int] | None = None
    for edge in islice(footprint_edges, MAX_ORG_SOLIDARITY_EDGES_PER_ORG + 1):
        _require_exact(edge, SolidarityFootprintEdgeV1, "footprint edge")
        current = (edge.source_org_node_id_u64, edge.target_class_node_id_u64)
        if current == previous:
            raise _fail(PracticeContractError.PRACTICE_FOOTPRINT_DUPLICATE)
        if previous is not None and current < previous:
            raise _fail(PracticeContractError.PRACTICE_FOOTPRINT_ORDER)
        if edge.source_org_node_id_u64 != actor_node_id:
            raise _fail(PracticeContractError.PRACTICE_FOOTPRINT_SOURCE)
        _require_exact(
            edge.target_domain_u8,
            PracticeTargetDomainV1,
            "target_domain_u8",
        )
        if edge.target_domain_u8 is not PracticeTargetDomainV1.SOCIAL_CLASS:
            raise _fail(PracticeContractError.PRACTICE_ENUM_CODE)
        strength = _strength_from_bits(edge.strength_f64_bits_u64)
        if not math.isfinite(strength):
            raise _fail(PracticeContractError.PRACTICE_FOOTPRINT_STRENGTH_NONFINITE)
        if strength <= 0.0:
            raise _fail(PracticeContractError.PRACTICE_FOOTPRINT_STRENGTH_NONPOSITIVE)
        previous = current
    return len(footprint_edges)


def _governed_cost(practice: PracticeIdV1 | None, terms: PracticeBudgetTermsV1) -> int:
    if practice is None:
        return 0
    _require_exact(practice, PracticeIdV1, "practice")
    if practice is PracticeIdV1.ORGANIZE:
        return terms.organize_cost
    if practice is PracticeIdV1.AGITATE:
        return terms.agitate_cost
    return terms.mutual_aid_cost


def compute_budget_delta(
    tick: int,
    actor_node_id: int,
    pre_action_world_hash: bytes,
    budget_before: int,
    practice: PracticeIdV1 | None,
    footprint_edges: Sequence[SolidarityFootprintEdgeV1],
    terms: PracticeBudgetTermsV1,
) -> OrganizationBudgetDeltaV1:
    """Compute one detached transition from derived practice cost and footprint."""
    checked_tick = _require_u64(tick, "tick")
    checked_actor = _require_u64(actor_node_id, "actor_node_id")
    checked_before = _require_u32(budget_before, "budget_before")
    _require_exact(pre_action_world_hash, bytes, "pre_action_world_hash")
    if len(pre_action_world_hash) != _DIGEST_BYTES:
        raise ValueError("pre_action_world_hash must contain 32 bytes")
    _require_exact(terms, PracticeBudgetTermsV1, "terms")
    footprint_count = _validate_footprint(checked_actor, footprint_edges)
    cost = _governed_cost(practice, terms)
    if checked_before < cost:
        raise _fail(PracticeContractError.PRACTICE_BUDGET_INSUFFICIENT)
    after_cost = checked_before - cost
    credited_credit = min(footprint_count, terms.weekly_credit_cap)
    before_ceiling = after_cost + credited_credit
    if before_ceiling > _U32_MAX:
        raise _fail(PracticeContractError.PRACTICE_BUDGET_ARITHMETIC)
    return OrganizationBudgetDeltaV1(
        schema_version=_SCHEMA_VERSION,
        tick=checked_tick,
        actor_node_id=checked_actor,
        pre_action_world_hash=pre_action_world_hash,
        budget_before=checked_before,
        governed_cost=cost,
        footprint_count=footprint_count,
        raw_credit=footprint_count,
        credited_credit=credited_credit,
        ceiling_bound=before_ceiling > terms.storage_ceiling,
        budget_after=min(before_ceiling, terms.storage_ceiling),
    )


class PracticeTopologyLoadCounter:
    """Bounded validation-local counts with no graph or identity authority."""

    __slots__ = ("_edge_counts", "_organizations", "_solidarity_edges")

    def __init__(self) -> None:
        self._organizations: set[int] = set()
        self._edge_counts: dict[int, int] = {}
        self._solidarity_edges: set[tuple[int, int]] = set()

    def observe_organization(
        self,
        organization_key: int,
        active: bool,
        action_budget_storage: float | None,
    ) -> None:
        """Observe one exact organization row in constant time."""
        checked_key = _require_u64(organization_key, "organization_key")
        if type(active) is not bool:
            raise TypeError("active must be bool")
        if checked_key in self._organizations:
            raise _fail(PracticeContractError.PRACTICE_TOPOLOGY_ORGANIZATION_DUPLICATE)
        if len(self._organizations) == MAX_ORGANIZATIONS:
            raise _fail(PracticeContractError.PRACTICE_TOPOLOGY_ORGANIZATION_LIMIT)
        if action_budget_storage is not None:
            read_action_budget(action_budget_storage)
        elif active:
            raise _fail(PracticeContractError.PRACTICE_TOPOLOGY_BUDGET_MISSING)
        self._organizations.add(checked_key)

    def observe_solidarity_edge(
        self,
        source_organization_key: int,
        target_domain: PracticeTargetDomainV1,
        target_key: int,
    ) -> None:
        """Observe one qualified organization-to-class solidarity edge."""
        checked_source = _require_u64(source_organization_key, "source_organization_key")
        checked_target = _require_u64(target_key, "target_key")
        _require_exact(target_domain, PracticeTargetDomainV1, "target_domain")
        if target_domain is not PracticeTargetDomainV1.SOCIAL_CLASS:
            raise _fail(PracticeContractError.PRACTICE_ENUM_CODE)
        identity = (checked_source, checked_target)
        if identity in self._solidarity_edges:
            raise _fail(PracticeContractError.PRACTICE_TOPOLOGY_EDGE_DUPLICATE)
        count = self._edge_counts.get(checked_source, 0)
        if count == MAX_ORG_SOLIDARITY_EDGES_PER_ORG:
            raise _fail(PracticeContractError.PRACTICE_FOOTPRINT_LIMIT)
        self._edge_counts[checked_source] = count + 1
        self._solidarity_edges.add(identity)

    def finish(self) -> None:
        """Complete a walk bounded to the organization maximum plus one."""
        observed = 0
        for _key in islice(self._organizations, MAX_ORGANIZATIONS + 1):
            observed += 1
        if observed > MAX_ORGANIZATIONS:
            raise _fail(PracticeContractError.PRACTICE_TOPOLOGY_ORGANIZATION_LIMIT)


def validate_topology(topology: OrganizationPracticeTopologyV1) -> None:
    """Validate one already-qualified detached topology without graph authority."""
    _require_exact(topology, OrganizationPracticeTopologyV1, "topology")
    if len(topology.organizations) > MAX_ORGANIZATIONS:
        raise _fail(PracticeContractError.PRACTICE_TOPOLOGY_ORGANIZATION_LIMIT)
    counter = PracticeTopologyLoadCounter()
    previous_organization: int | None = None
    for row in islice(topology.organizations, MAX_ORGANIZATIONS + 1):
        if row.node_id_u64 == previous_organization:
            raise _fail(PracticeContractError.PRACTICE_TOPOLOGY_ORGANIZATION_DUPLICATE)
        if previous_organization is not None and row.node_id_u64 < previous_organization:
            raise _fail(PracticeContractError.PRACTICE_TOPOLOGY_ORGANIZATION_ORDER)
        storage = (
            None
            if row.action_budget_storage_f64_bits_u64 is None
            else _strength_from_bits(row.action_budget_storage_f64_bits_u64)
        )
        counter.observe_organization(row.node_id_u64, row.active_bool, storage)
        if len(row.edges) > MAX_ORG_SOLIDARITY_EDGES_PER_ORG:
            raise _fail(PracticeContractError.PRACTICE_FOOTPRINT_LIMIT)
        previous_target: int | None = None
        for edge in islice(row.edges, MAX_ORG_SOLIDARITY_EDGES_PER_ORG + 1):
            if edge.target_class_node_id_u64 == previous_target:
                raise _fail(PracticeContractError.PRACTICE_TOPOLOGY_EDGE_DUPLICATE)
            if previous_target is not None and edge.target_class_node_id_u64 < previous_target:
                raise _fail(PracticeContractError.PRACTICE_TOPOLOGY_EDGE_ORDER)
            counter.observe_solidarity_edge(
                row.node_id_u64,
                edge.target_domain,
                edge.target_class_node_id_u64,
            )
            previous_target = edge.target_class_node_id_u64
        previous_organization = row.node_id_u64
    counter.finish()


def _domain_bytes(domain: bytes) -> bytes:
    return domain + PRACTICE_WIRE_DOMAIN_TERMINATOR_BYTES


def _check_schema_version(value: int) -> None:
    if value != _SCHEMA_VERSION:
        raise _fail(PracticeContractError.PRACTICE_SCHEMA_VERSION)


def _check_tick_pair(submit_after_tick: int, resolve_tick: int) -> None:
    if submit_after_tick == _U64_MAX:
        raise _fail(PracticeContractError.PRACTICE_TICK_OVERFLOW)
    if resolve_tick != submit_after_tick + 1:
        raise _fail(PracticeContractError.PRACTICE_TICK_MISMATCH)


def _append_u16(output: bytearray, value: int) -> None:
    output.extend(value.to_bytes(2, "big"))


def _append_u32(output: bytearray, value: int) -> None:
    output.extend(value.to_bytes(4, "big"))


def _append_u64(output: bytearray, value: int) -> None:
    output.extend(value.to_bytes(8, "big"))


def _check_evidence(evidence: Sequence[bytes]) -> None:
    if len(evidence) > MAX_EVIDENCE_DIGESTS:
        raise _fail(PracticeContractError.PRACTICE_EVIDENCE_LIMIT)
    previous: bytes | None = None
    for digest in islice(evidence, MAX_EVIDENCE_DIGESTS + 1):
        if len(digest) != _DIGEST_BYTES:
            raise TypeError("evidence digest must contain 32 bytes")
        if previous is not None and digest == previous:
            raise _fail(PracticeContractError.PRACTICE_EVIDENCE_DUPLICATE)
        if previous is not None and digest < previous:
            raise _fail(PracticeContractError.PRACTICE_EVIDENCE_ORDER)
        previous = digest


def encode_intent_parameters(value: PracticeIntentV1) -> bytes:
    """Encode the bounded parameter section, refusing V1's empty allowlist."""
    _require_exact(value, PracticeIntentV1, "value")
    parameters = value.parameters
    if len(parameters) > MAX_PARAMETERS:
        raise _fail(PracticeContractError.PRACTICE_PARAMETER_LIMIT)
    saw_parameter = False
    for parameter in islice(parameters, MAX_PARAMETERS + 1):
        saw_parameter = True
        actual_length = len(parameter.value_bytes)
        if (
            parameter.value_length_u16 > MAX_PARAMETER_VALUE_BYTES
            or actual_length > MAX_PARAMETER_VALUE_BYTES
            or actual_length != parameter.value_length_u16
        ):
            raise _fail(PracticeContractError.PRACTICE_PARAMETER_LENGTH)
    if saw_parameter:
        raise _fail(PracticeContractError.PRACTICE_PARAMETER)
    output = bytearray()
    _append_u16(output, len(parameters))
    return bytes(output)


def encode_input_authority(value: PracticeInputAuthorityV1) -> bytes:
    """Encode one fixed practice-input authority record."""
    _require_exact(value, PracticeInputAuthorityV1, "value")
    _check_schema_version(value.schema_version)
    _require_exact(value.authority_kind, PracticeAuthorityKindV1, "authority_kind")
    output = bytearray(_domain_bytes(PRACTICE_INPUT_AUTHORITY_V1_DOMAIN_BYTES))
    _append_u16(output, value.schema_version)
    output.append(value.authority_kind.value)
    _append_u64(output, value.actor_org_id)
    output.extend(value.producer_content_digest)
    return bytes(output)


def encode_intent(value: PracticeIntentV1) -> bytes:
    """Encode one bounded practice intent after complete preflight."""
    _require_exact(value, PracticeIntentV1, "value")
    _check_schema_version(value.schema_version)
    _require_exact(value.practice_id, PracticeIdV1, "practice_id")
    _require_exact(value.target_domain, PracticeTargetDomainV1, "target_domain")
    _check_tick_pair(value.submit_after_tick, value.resolve_tick)
    parameter_bytes = encode_intent_parameters(value)
    _check_evidence(value.evidence_digests)
    output = bytearray(_domain_bytes(PRACTICE_INTENT_V1_DOMAIN_BYTES))
    _append_u16(output, value.schema_version)
    _append_u64(output, value.submit_after_tick)
    _append_u64(output, value.resolve_tick)
    _append_u64(output, value.actor_org_id)
    output.append(value.practice_id.value)
    output.append(value.target_domain.value)
    _append_u64(output, value.target_node_id)
    output.extend(value.quoted_content_digest)
    _append_u32(output, value.quoted_action_budget_cost)
    output.extend(parameter_bytes)
    _append_u16(output, len(value.evidence_digests))
    for digest in islice(value.evidence_digests, MAX_EVIDENCE_DIGESTS + 1):
        output.extend(digest)
    if len(output) > MAX_INTENT_CANONICAL_BYTES:
        raise _fail(PracticeContractError.PRACTICE_LENGTH)
    return bytes(output)


def encode_budget_delta(value: OrganizationBudgetDeltaV1) -> bytes:
    """Encode one fixed organization-budget delta record."""
    _require_exact(value, OrganizationBudgetDeltaV1, "value")
    _check_schema_version(value.schema_version)
    output = bytearray(_domain_bytes(ORGANIZATION_BUDGET_DELTA_V1_DOMAIN_BYTES))
    _append_u16(output, value.schema_version)
    _append_u64(output, value.tick)
    _append_u64(output, value.actor_node_id)
    output.extend(value.pre_action_world_hash)
    for field in (
        value.budget_before,
        value.governed_cost,
        value.footprint_count,
        value.raw_credit,
        value.credited_credit,
    ):
        _append_u32(output, field)
    output.append(1 if value.ceiling_bound else 0)
    _append_u32(output, value.budget_after)
    return bytes(output)


def encode_rejection(value: PracticeSubmissionRejectionV1) -> bytes:
    """Encode one fixed context-complete submission rejection."""
    _require_exact(value, PracticeSubmissionRejectionV1, "value")
    _check_schema_version(value.schema_version)
    _require_exact(value.reason_code, PracticeRejectionCodeV1, "reason_code")
    output = bytearray()
    _append_u16(output, value.schema_version)
    output.extend(value.submitted_bytes_digest)
    _append_u16(output, value.reason_code.value)
    _append_u64(output, value.last_committed_tick)
    output.extend(value.content_digest)
    return bytes(output)


class _Cursor:
    __slots__ = ("_index", "_payload")

    def __init__(self, payload: bytes) -> None:
        self._payload = payload
        self._index = 0

    def take(self, count: int) -> bytes:
        end = self._index + count
        if end > len(self._payload):
            raise _fail(PracticeContractError.PRACTICE_TRUNCATED)
        value = self._payload[self._index : end]
        self._index = end
        return value

    def u8(self) -> int:
        return self.take(1)[0]

    def u16(self) -> int:
        return int.from_bytes(self.take(2), "big")

    def u32(self) -> int:
        return int.from_bytes(self.take(4), "big")

    def u64(self) -> int:
        return int.from_bytes(self.take(8), "big")

    def domain(self, expected: bytes) -> None:
        if self.take(len(expected)) != expected:
            raise _fail(PracticeContractError.PRACTICE_DOMAIN)

    def finish(self) -> None:
        if self._index != len(self._payload):
            raise _fail(PracticeContractError.PRACTICE_TRAILING_BYTES)


def _cursor(payload: bytes) -> _Cursor:
    _require_exact(payload, bytes, "payload")
    return _Cursor(payload)


def _decode_enum[EnumT: IntEnum](enum_type: type[EnumT], value: int) -> EnumT:
    try:
        return enum_type(value)
    except ValueError as error:
        raise _fail(PracticeContractError.PRACTICE_ENUM_CODE) from error


def decode_input_authority(payload: bytes) -> PracticeInputAuthorityV1:
    """Decode one fixed authority and require complete consumption."""
    cursor = _cursor(payload)
    cursor.domain(_domain_bytes(PRACTICE_INPUT_AUTHORITY_V1_DOMAIN_BYTES))
    schema_version = cursor.u16()
    _check_schema_version(schema_version)
    authority_kind = _decode_enum(PracticeAuthorityKindV1, cursor.u8())
    actor_org_id = cursor.u64()
    producer_content_digest = cursor.take(_DIGEST_BYTES)
    cursor.finish()
    return PracticeInputAuthorityV1(
        schema_version=schema_version,
        authority_kind=authority_kind,
        actor_org_id=actor_org_id,
        producer_content_digest=producer_content_digest,
    )


def _decode_parameters(cursor: _Cursor) -> tuple[PracticeParameterV1, ...]:
    parameter_count = cursor.u16()
    if parameter_count > MAX_PARAMETERS:
        raise _fail(PracticeContractError.PRACTICE_PARAMETER_LIMIT)
    for _index in range(MAX_PARAMETERS + 1):
        if _index == parameter_count:
            break
        key = cursor.u8()
        value_kind = cursor.u8()
        value_length = cursor.u16()
        if value_length > MAX_PARAMETER_VALUE_BYTES:
            raise _fail(PracticeContractError.PRACTICE_PARAMETER_LENGTH)
        cursor.take(value_length)
        _ = (key, value_kind)
    if parameter_count != 0:
        raise _fail(PracticeContractError.PRACTICE_PARAMETER)
    return ()


def _decode_evidence(cursor: _Cursor) -> tuple[bytes, ...]:
    evidence_count = cursor.u16()
    if evidence_count > MAX_EVIDENCE_DIGESTS:
        raise _fail(PracticeContractError.PRACTICE_EVIDENCE_LIMIT)
    output: list[bytes] = []
    previous: bytes | None = None
    for evidence_index in range(MAX_EVIDENCE_DIGESTS + 1):
        if evidence_index == evidence_count:
            break
        digest = cursor.take(_DIGEST_BYTES)
        if previous is not None and digest == previous:
            raise _fail(PracticeContractError.PRACTICE_EVIDENCE_DUPLICATE)
        if previous is not None and digest < previous:
            raise _fail(PracticeContractError.PRACTICE_EVIDENCE_ORDER)
        output.append(digest)
        previous = digest
    return tuple(output)


def decode_intent(payload: bytes) -> PracticeIntentV1:
    """Decode one bounded intent without accepting partial or trailing bytes."""
    _require_exact(payload, bytes, "payload")
    if len(payload) > MAX_INTENT_CANONICAL_BYTES:
        raise _fail(PracticeContractError.PRACTICE_LENGTH)
    cursor = _Cursor(payload)
    cursor.domain(_domain_bytes(PRACTICE_INTENT_V1_DOMAIN_BYTES))
    schema_version = cursor.u16()
    _check_schema_version(schema_version)
    submit_after_tick = cursor.u64()
    resolve_tick = cursor.u64()
    _check_tick_pair(submit_after_tick, resolve_tick)
    actor_org_id = cursor.u64()
    practice_id = _decode_enum(PracticeIdV1, cursor.u8())
    target_domain = _decode_enum(PracticeTargetDomainV1, cursor.u8())
    target_node_id = cursor.u64()
    quoted_content_digest = cursor.take(_DIGEST_BYTES)
    quoted_action_budget_cost = cursor.u32()
    parameters = _decode_parameters(cursor)
    evidence_digests = _decode_evidence(cursor)
    cursor.finish()
    return PracticeIntentV1(
        schema_version=schema_version,
        submit_after_tick=submit_after_tick,
        resolve_tick=resolve_tick,
        actor_org_id=actor_org_id,
        practice_id=practice_id,
        target_domain=target_domain,
        target_node_id=target_node_id,
        quoted_content_digest=quoted_content_digest,
        quoted_action_budget_cost=quoted_action_budget_cost,
        parameters=parameters,
        evidence_digests=evidence_digests,
    )


def decode_budget_delta(payload: bytes) -> OrganizationBudgetDeltaV1:
    """Decode one fixed organization-budget delta record."""
    cursor = _cursor(payload)
    cursor.domain(_domain_bytes(ORGANIZATION_BUDGET_DELTA_V1_DOMAIN_BYTES))
    schema_version = cursor.u16()
    _check_schema_version(schema_version)
    tick = cursor.u64()
    actor_node_id = cursor.u64()
    pre_action_world_hash = cursor.take(_DIGEST_BYTES)
    budget_before = cursor.u32()
    governed_cost = cursor.u32()
    footprint_count = cursor.u32()
    raw_credit = cursor.u32()
    credited_credit = cursor.u32()
    ceiling_code = cursor.u8()
    if ceiling_code not in (0, 1):
        raise _fail(PracticeContractError.PRACTICE_BOOLEAN)
    budget_after = cursor.u32()
    cursor.finish()
    return OrganizationBudgetDeltaV1(
        schema_version=schema_version,
        tick=tick,
        actor_node_id=actor_node_id,
        pre_action_world_hash=pre_action_world_hash,
        budget_before=budget_before,
        governed_cost=governed_cost,
        footprint_count=footprint_count,
        raw_credit=raw_credit,
        credited_credit=credited_credit,
        ceiling_bound=bool(ceiling_code),
        budget_after=budget_after,
    )


def decode_rejection(payload: bytes) -> PracticeSubmissionRejectionV1:
    """Decode one fixed context-complete submission rejection."""
    cursor = _cursor(payload)
    schema_version = cursor.u16()
    _check_schema_version(schema_version)
    submitted_bytes_digest = cursor.take(_DIGEST_BYTES)
    reason_code = _decode_enum(PracticeRejectionCodeV1, cursor.u16())
    last_committed_tick = cursor.u64()
    content_digest = cursor.take(_DIGEST_BYTES)
    cursor.finish()
    return PracticeSubmissionRejectionV1(
        schema_version=schema_version,
        submitted_bytes_digest=submitted_bytes_digest,
        reason_code=reason_code,
        last_committed_tick=last_committed_tick,
        content_digest=content_digest,
    )


def input_authority_digest(value: PracticeInputAuthorityV1) -> bytes:
    """Hash one valid canonical authority."""
    return sha256(encode_input_authority(value)).digest()


def intent_digest(value: PracticeIntentV1) -> bytes:
    """Hash one valid canonical intent."""
    return sha256(encode_intent(value)).digest()


def parameter_bytes_digest(value: PracticeIntentV1) -> bytes:
    """Hash the exact domain-separated parameter section."""
    parameter_bytes = encode_intent_parameters(value)
    return sha256(
        _PARAMETER_DIGEST_DOMAIN + PRACTICE_WIRE_DOMAIN_TERMINATOR_BYTES + parameter_bytes
    ).digest()


def target_selection_policy_digest(
    target_domain: PracticeTargetDomainV1, target_node_id: int
) -> bytes:
    """Hash one fixed-target selection using the sole framing owner."""
    _require_exact(target_domain, PracticeTargetDomainV1, "target_domain")
    checked_node_id = _require_u64(target_node_id, "target_node_id")
    preimage = bytearray(_FIXED_TARGET_DOMAIN + PRACTICE_WIRE_DOMAIN_TERMINATOR_BYTES)
    preimage.append(target_domain.value)
    _append_u64(preimage, checked_node_id)
    return sha256(preimage).digest()


def budget_delta_digest(value: OrganizationBudgetDeltaV1) -> bytes:
    """Hash one valid canonical budget delta."""
    return sha256(encode_budget_delta(value)).digest()


def submission_rejection_alias(
    error: PracticeContractError,
) -> PracticeRejectionCodeV1 | None:
    """Return only the governed metadata alias for a contract error."""
    _require_exact(error, PracticeContractError, "error")
    aliases = {
        PracticeContractError.PRACTICE_TICK_OVERFLOW: PracticeRejectionCodeV1.PRACTICE_TICK_MISMATCH,
        PracticeContractError.PRACTICE_TICK_MISMATCH: PracticeRejectionCodeV1.PRACTICE_TICK_MISMATCH,
        PracticeContractError.PRACTICE_AUTHORITY_UNREGISTERED: PracticeRejectionCodeV1.PRACTICE_AUTHORITY_UNREGISTERED,
        PracticeContractError.PRACTICE_ACTOR_MISMATCH: PracticeRejectionCodeV1.PRACTICE_ACTOR_MISMATCH,
        PracticeContractError.PRACTICE_AUTHORITY_CONTENT_MISMATCH: PracticeRejectionCodeV1.PRACTICE_AUTHORITY_UNREGISTERED,
        PracticeContractError.PRACTICE_QUOTE_CONTENT_MISMATCH: PracticeRejectionCodeV1.PRACTICE_STALE_CONTENT,
        PracticeContractError.PRACTICE_QUOTE_COST_MISMATCH: PracticeRejectionCodeV1.PRACTICE_COST_MISMATCH,
        PracticeContractError.PRACTICE_BATCH_LIMIT: PracticeRejectionCodeV1.PRACTICE_BATCH_LIMIT,
        PracticeContractError.PRACTICE_DUPLICATE_ACTOR: PracticeRejectionCodeV1.PRACTICE_DUPLICATE_ACTOR,
        PracticeContractError.PRACTICE_BUDGET_INSUFFICIENT: PracticeRejectionCodeV1.PRACTICE_BUDGET_INSUFFICIENT,
    }
    return aliases.get(error)


def rejection_for(
    *,
    submitted_bytes_digest: bytes,
    reason_code: PracticeRejectionCodeV1,
    last_committed_tick: int,
    content_digest: bytes,
) -> PracticeSubmissionRejectionV1:
    """Construct one context-complete rejection from exact typed values."""
    return PracticeSubmissionRejectionV1(
        schema_version=_SCHEMA_VERSION,
        submitted_bytes_digest=submitted_bytes_digest,
        reason_code=reason_code,
        last_committed_tick=last_committed_tick,
        content_digest=content_digest,
    )


def _validate_policy_registry(
    pairs: Sequence[PolicyAuthorityPairV1],
) -> None:
    if len(pairs) > MAX_POLICY_AUTHORITY_PAIRS:
        raise _fail(PracticeContractError.PRACTICE_AUTHORITY_REGISTRY_LIMIT)
    previous: tuple[bytes, int] | None = None
    for pair in islice(pairs, MAX_POLICY_AUTHORITY_PAIRS + 1):
        current = (pair.producer_content_digest, pair.actor_org_id)
        if previous is not None and current == previous:
            raise _fail(PracticeContractError.PRACTICE_AUTHORITY_REGISTRY_DUPLICATE)
        if previous is not None and current < previous:
            raise _fail(PracticeContractError.PRACTICE_AUTHORITY_REGISTRY_ORDER)
        previous = current


def validate_authority_pair(
    authority: PracticeInputAuthorityV1,
    intent: PracticeIntentV1,
    context: PracticeAuthorityContextV1,
) -> None:
    """Validate detached player-seat or registered-policy authority."""
    _require_exact(authority, PracticeInputAuthorityV1, "authority")
    _require_exact(intent, PracticeIntentV1, "intent")
    _require_exact(context, PracticeAuthorityContextV1, "context")
    if authority.actor_org_id != intent.actor_org_id:
        raise _fail(PracticeContractError.PRACTICE_ACTOR_MISMATCH)
    if authority.authority_kind is PracticeAuthorityKindV1.PLAYER_SEAT:
        if authority.actor_org_id != context.player_org_id:
            raise _fail(PracticeContractError.PRACTICE_ACTOR_MISMATCH)
        if authority.producer_content_digest != context.player_gateway_content_digest:
            raise _fail(PracticeContractError.PRACTICE_AUTHORITY_CONTENT_MISMATCH)
        return
    _validate_policy_registry(context.policy_authorities)
    expected = (authority.producer_content_digest, authority.actor_org_id)
    for pair in islice(context.policy_authorities, MAX_POLICY_AUTHORITY_PAIRS + 1):
        if (pair.producer_content_digest, pair.actor_org_id) == expected:
            return
    raise _fail(PracticeContractError.PRACTICE_AUTHORITY_UNREGISTERED)


def _quoted_cost(intent: PracticeIntentV1, context: PracticeQuoteContextV1) -> int:
    if intent.practice_id is PracticeIdV1.ORGANIZE:
        return context.budget_terms.organize_cost
    if intent.practice_id is PracticeIdV1.AGITATE:
        return context.budget_terms.agitate_cost
    return context.budget_terms.mutual_aid_cost


def validate_quote_context(intent: PracticeIntentV1, context: PracticeQuoteContextV1) -> None:
    """Validate a detached next-tick quote against exact immutable context."""
    _require_exact(intent, PracticeIntentV1, "intent")
    _require_exact(context, PracticeQuoteContextV1, "context")
    if intent.submit_after_tick != context.last_committed_tick:
        raise _fail(PracticeContractError.PRACTICE_TICK_MISMATCH)
    if context.last_committed_tick == _U64_MAX:
        raise _fail(PracticeContractError.PRACTICE_TICK_OVERFLOW)
    if intent.resolve_tick != context.last_committed_tick + 1:
        raise _fail(PracticeContractError.PRACTICE_TICK_MISMATCH)
    if intent.quoted_content_digest != context.content_digest:
        raise _fail(PracticeContractError.PRACTICE_QUOTE_CONTENT_MISMATCH)
    if intent.quoted_action_budget_cost != _quoted_cost(intent, context):
        raise _fail(PracticeContractError.PRACTICE_QUOTE_COST_MISMATCH)


def validate_resolve_batch(intents: Sequence[PracticeIntentV1], expected_resolve_tick: int) -> None:
    """Validate one detached bounded resolve batch without mutation."""
    _require_u64(expected_resolve_tick, "expected_resolve_tick")
    if len(intents) > MAX_INTENTS_PER_RESOLVE_TICK:
        raise _fail(PracticeContractError.PRACTICE_BATCH_LIMIT)
    seen: set[int] = set()
    for intent in islice(intents, MAX_INTENTS_PER_RESOLVE_TICK + 1):
        if type(intent) is not PracticeIntentV1:
            raise TypeError("intents must contain PracticeIntentV1")
        if intent.resolve_tick != expected_resolve_tick:
            raise _fail(PracticeContractError.PRACTICE_TICK_MISMATCH)
        if intent.actor_org_id in seen:
            raise _fail(PracticeContractError.PRACTICE_DUPLICATE_ACTOR)
        seen.add(intent.actor_org_id)


def _scan_json_depth(line: bytes) -> None:
    depth = 0
    in_string = False
    escaped = False
    for byte in islice(line, MAX_JSONL_LINE_BYTES + 1):
        if in_string:
            if escaped:
                escaped = False
            elif byte == 0x5C:
                escaped = True
            elif byte == 0x22:
                in_string = False
        elif byte == 0x22:
            in_string = True
        elif byte in (0x7B, 0x5B):
            depth += 1
            if depth > MAX_JSON_DEPTH:
                raise PracticeVectorCorpusError("JSON depth limit")
        elif byte in (0x7D, 0x5D):
            depth -= 1
            if depth < 0:
                raise PracticeVectorCorpusError("malformed JSON")


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    output: dict[str, object] = {}
    for key, value in islice(pairs, MAX_JSONL_LINE_BYTES + 1):
        if key in output:
            raise PracticeVectorCorpusError("duplicate JSON key")
        output[key] = value
    return output


def _parse_vector_line(line: bytes) -> PracticeVectorCaseV1:
    if len(line) > MAX_JSONL_LINE_BYTES:
        raise PracticeVectorCorpusError("line limit")
    stripped = line.removesuffix(b"\n").removesuffix(b"\r")
    _scan_json_depth(stripped)
    try:
        decoded = json.loads(stripped, object_pairs_hook=_unique_object)
    except PracticeVectorCorpusError:
        raise
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise PracticeVectorCorpusError("malformed JSON") from error
    if not isinstance(decoded, dict) or set(decoded) != {"case_id", "kind", "data"}:
        raise PracticeVectorCorpusError("unknown vector field")
    case_id = decoded["case_id"]
    kind = decoded["kind"]
    data = decoded["data"]
    if not isinstance(case_id, str) or not case_id:
        raise PracticeVectorCorpusError("invalid case id")
    if len(case_id.encode("utf-8")) > MAX_JSONL_CASE_ID_BYTES:
        raise PracticeVectorCorpusError("case id limit")
    if not isinstance(kind, str) or kind not in _KNOWN_VECTOR_KINDS:
        raise PracticeVectorCorpusError("unknown vector kind")
    if not isinstance(data, dict):
        raise PracticeVectorCorpusError("invalid vector data")
    if set(data) != _VECTOR_DATA_FIELDS[kind]:
        raise PracticeVectorCorpusError("unknown vector data field")
    return PracticeVectorCaseV1(case_id, kind, MappingProxyType(data))


def parse_vector_corpus(payload: bytes) -> tuple[PracticeVectorCaseV1, ...]:
    """Parse the shared JSONL corpus under fixed raw and structural bounds."""
    _require_exact(payload, bytes, "payload")
    if len(payload) > MAX_JSONL_SOURCE_BYTES:
        raise PracticeVectorCorpusError("source limit")
    output: list[PracticeVectorCaseV1] = []
    seen: set[str] = set()
    for line_index, line in enumerate(islice(BytesIO(payload), MAX_JSONL_CASES + 1)):
        if line_index == MAX_JSONL_CASES:
            raise PracticeVectorCorpusError("case limit")
        case = _parse_vector_line(line)
        if case.case_id in seen:
            raise PracticeVectorCorpusError("duplicate case id")
        seen.add(case.case_id)
        output.append(case)
    return tuple(output)


__all__ = [
    "PracticeBudgetTermsV1",
    "PracticeContractViolation",
    "PracticeTopologyLoadCounter",
    "PracticeVectorCaseV1",
    "PracticeVectorCorpusError",
    "budget_delta_digest",
    "compute_budget_delta",
    "decode_budget_delta",
    "decode_input_authority",
    "decode_intent",
    "decode_rejection",
    "encode_budget_delta",
    "encode_input_authority",
    "encode_intent",
    "encode_intent_parameters",
    "encode_rejection",
    "input_authority_digest",
    "intent_digest",
    "parameter_bytes_digest",
    "parse_vector_corpus",
    "read_action_budget",
    "rejection_for",
    "submission_rejection_alias",
    "target_selection_policy_digest",
    "validate_authority_pair",
    "validate_quote_context",
    "validate_resolve_batch",
    "validate_topology",
    "write_action_budget",
]
