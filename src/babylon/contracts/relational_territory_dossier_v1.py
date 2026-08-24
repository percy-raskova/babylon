"""Bounded semantic validation for administrative RTD V1 drafts.

This module is deliberately projection-only. It validates generated structural
types and never writes files, resolves fog, accepts player context, or mutates
authoritative state.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from io import BytesIO
from itertools import islice
from typing import Final

from pydantic import TypeAdapter, ValidationError

from babylon.contracts.rtd_v1_generated import (
    RTD_V1_ERROR_REGISTRY,
    RTD_V1_LIMITS,
    RTD_V1_METRIC_REGISTRY,
    RTD_V1_RELATION_BINDING_REGISTRY,
    RTD_V1_SCHEMA_ID,
    AudienceV1,
    DecisionSurfaceV1,
    DimensionCoordinateV1,
    DurabilityV1,
    DyadV1,
    FacetV1,
    FlowKindV1,
    GapV1,
    HyperedgeV1,
    MembershipKindV1,
    MetricRepresentationV1,
    ProvenanceV1,
    ReferenceDigestV1,
    ReferenceFlowV1,
    RelationalTerritoryDossierV1,
    RelationPayloadModeV1,
    RtdCollectionKindV1,
    RtdDossierDraftV1,
    RtdMetricRegistryRowV1,
    RtdRelationBindingRegistryRowV1,
    ScaleMembershipV1,
    StatusV1,
    TypedIdentityV1,
    ValueKindV1,
)

__all__ = [
    "RtdValidationError",
    "RtdVectorCaseV1",
    "append_bounded",
    "canonical_draft_bytes",
    "parse_draft",
    "parse_draft_json",
    "parse_vector_corpus",
    "projection_hash",
    "seal_draft",
    "validate_draft",
]

PathPart = str | int
RTD_MAX_COLLECTION_ITEMS: Final[int] = RTD_V1_LIMITS["max_collection_items"]
RTD_MAX_FOCUS: Final[int] = RTD_V1_LIMITS["max_focus"]
RTD_MAX_REFERENCE_DIGESTS: Final[int] = RTD_V1_LIMITS["max_reference_digests"]
RTD_MAX_SCALE_MEMBERSHIPS: Final[int] = RTD_V1_LIMITS["max_scale_memberships"]
RTD_MAX_FACETS: Final[int] = RTD_V1_LIMITS["max_facets"]
RTD_MAX_DYADS: Final[int] = RTD_V1_LIMITS["max_dyads"]
RTD_MAX_HYPEREDGES: Final[int] = RTD_V1_LIMITS["max_hyperedges"]
RTD_MAX_FLOWS: Final[int] = RTD_V1_LIMITS["max_flows"]
RTD_MAX_GAPS: Final[int] = RTD_V1_LIMITS["max_gaps"]
RTD_MAX_PROVENANCE: Final[int] = RTD_V1_LIMITS["max_provenance"]
RTD_MAX_COORDINATES: Final[int] = RTD_V1_LIMITS["max_coordinates"]
RTD_MAX_HYPEREDGE_MEMBERS: Final[int] = RTD_V1_LIMITS["max_hyperedge_members"]
RTD_MAX_PAYLOAD_FACETS: Final[int] = RTD_V1_LIMITS["max_payload_facets"]
RTD_MAX_DISPLAY_REFS: Final[int] = RTD_V1_LIMITS["max_decision_surface_refs"]
RTD_MAX_PROVENANCE_REFS: Final[int] = RTD_V1_LIMITS["max_provenance_refs"]
RTD_MAX_IDENTITY_BYTES: Final[int] = RTD_V1_LIMITS["max_identity_component_bytes"]
RTD_MAX_VINTAGE_BYTES: Final[int] = RTD_V1_LIMITS["max_vintage_bytes"]
RTD_MAX_LOCATOR_BYTES: Final[int] = RTD_V1_LIMITS["max_provenance_locator_bytes"]
RTD_MAX_PRODUCER_BYTES: Final[int] = RTD_V1_LIMITS["max_required_producer_bytes"]
RTD_MAX_JSON_INPUT_BYTES: Final[int] = RTD_V1_LIMITS["max_canonical_bytes"]
RTD_MAX_JSON_DEPTH: Final[int] = 32
RTD_METRIC_REGISTRY_ROWS: Final[int] = 18
RTD_RELATION_BINDING_ROWS: Final[int] = 6
RTD_IDENTITY_COMPONENT_COUNT: Final[int] = 3
RTD_TOP_LEVEL_COLLECTION_COUNT: Final[int] = 9
RTD_DECISION_SURFACE_LIST_COUNT: Final[int] = 4
RTD_RELATION_FAMILY_COUNT: Final[int] = 2
RTD_FACET_IDENTITY_FIELD_COUNT: Final[int] = 5
RTD_RELATION_IDENTITY_FIELD_COUNT: Final[int] = 4
RTD_TOP_LEVEL_DIGEST_COUNT: Final[int] = 4
RTD_NULLABLE_DIGEST_COUNT: Final[int] = 2
RTD_RECORD_ARRAY_COUNT: Final[int] = 7
RTD_RECORD_ID_ATTRIBUTE_COUNT: Final[int] = 7
RTD_CANADA_TOKEN_COUNT: Final[int] = 3
RTD_ADMIN_FORBIDDEN_LIST_COUNT: Final[int] = 3
RTD_MAX_VECTOR_BYTES: Final[int] = 1_048_576
RTD_MAX_VECTOR_LINES: Final[int] = 256
RTD_MAX_VECTOR_LINE_BYTES: Final[int] = 262_144
RTD_MAX_CASE_ID_BYTES: Final[int] = 128
RTD_HASH_DOMAIN: Final[bytes] = b"babylon.relational-territory-dossier.v1"

_DRAFT_ADAPTER: Final[TypeAdapter[RtdDossierDraftV1]] = TypeAdapter(RtdDossierDraftV1)
_DIGEST_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{64}$")
_BITS_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{16}$")
_PRODUCER_RE: Final[re.Pattern[str]] = re.compile(r"^PER-[1-9][0-9]*$")
_NEGATIVE_ZERO_BITS: Final[str] = "8000000000000000"
_POSITIVE_ZERO_BITS: Final[str] = "0000000000000000"
_H3_METRICS: Final[frozenset[str]] = frozenset(
    {
        "reproduction/h3-population-persons",
        "production/h3-workplace-jobs",
        "ecology/h3-land-fraction",
    }
)


class RtdValidationError(ValueError):
    """A stable RTD refusal with a generated code and structured path."""

    code: str
    path: tuple[PathPart, ...]

    def __init__(self, code: str, path: tuple[PathPart, ...]) -> None:
        if code not in RTD_V1_ERROR_REGISTRY:
            raise AssertionError(f"unregistered RTD error code: {code}")
        self.code = code
        self.path = path
        rendered_path = repr(path) if path else "<root>"
        super().__init__(f"{code} at {rendered_path}")


def _fail(code: str, *path: PathPart) -> RtdValidationError:
    return RtdValidationError(code, tuple(path))


def _collection_limit(kind: RtdCollectionKindV1) -> int:
    match kind:
        case RtdCollectionKindV1.FOCUS:
            return RTD_MAX_FOCUS
        case RtdCollectionKindV1.REFERENCE_DIGESTS:
            return RTD_MAX_REFERENCE_DIGESTS
        case RtdCollectionKindV1.SCALE_MEMBERSHIPS:
            return RTD_MAX_SCALE_MEMBERSHIPS
        case RtdCollectionKindV1.FACETS:
            return RTD_MAX_FACETS
        case RtdCollectionKindV1.DYADS:
            return RTD_MAX_DYADS
        case RtdCollectionKindV1.HYPEREDGES:
            return RTD_MAX_HYPEREDGES
        case RtdCollectionKindV1.FLOWS:
            return RTD_MAX_FLOWS
        case RtdCollectionKindV1.GAPS:
            return RTD_MAX_GAPS
        case RtdCollectionKindV1.PROVENANCE:
            return RTD_MAX_PROVENANCE
        case RtdCollectionKindV1.COORDINATES:
            return RTD_MAX_COORDINATES
        case RtdCollectionKindV1.MEMBER_REFS:
            return RTD_MAX_HYPEREDGE_MEMBERS
        case RtdCollectionKindV1.PAYLOAD_FACETS:
            return RTD_MAX_PAYLOAD_FACETS
        case RtdCollectionKindV1.DISPLAY_REFS:
            return RTD_MAX_DISPLAY_REFS
        case RtdCollectionKindV1.PROVENANCE_REFS:
            return RTD_MAX_PROVENANCE_REFS


def append_bounded[T](
    items: tuple[T, ...],
    item: T,
    kind: RtdCollectionKindV1,
    path: str,
) -> tuple[T, ...]:
    """Return one atomic bounded append selected by a closed collection kind."""
    if not isinstance(items, tuple):
        raise _fail("RTD_JSON", path)
    if len(items) >= _collection_limit(kind):
        raise _fail("RTD_LIMIT_EXCEEDED", path)
    return items + (item,)


def _scan_json_depth(payload: bytes) -> None:
    depth = 0
    in_string = False
    escaped = False
    payload_size = len(payload)
    for byte_index in range(RTD_MAX_JSON_INPUT_BYTES + 1):
        if byte_index == payload_size:
            return
        byte = payload[byte_index]
        if in_string:
            if escaped:
                escaped = False
            elif byte == 0x5C:
                escaped = True
            elif byte == 0x22:
                in_string = False
        elif byte == 0x22:
            in_string = True
        elif byte in (0x5B, 0x7B):
            depth += 1
            if depth > RTD_MAX_JSON_DEPTH:
                raise _fail("RTD_JSON_DEPTH", byte_index)
        elif byte in (0x5D, 0x7D):
            depth -= 1


def _translate_pydantic(error: ValidationError) -> RtdValidationError:
    first = error.errors(include_url=False)[0]
    path = tuple(first["loc"])
    error_type = str(first["type"])
    if error_type == "extra_forbidden":
        return RtdValidationError("RTD_UNKNOWN_FIELD", path)
    if error_type == "enum":
        return RtdValidationError("RTD_ENUM", path)
    if path and path[-1] in {"schema_version", "projection_version"}:
        return RtdValidationError("RTD_SCHEMA_VERSION", path)
    return RtdValidationError("RTD_JSON", path)


def _normalize_negative_zero(draft: RtdDossierDraftV1) -> RtdDossierDraftV1:
    facets: list[FacetV1] = []
    for facet_index in range(RTD_MAX_FACETS):
        if facet_index == len(draft.facets):
            break
        facet = draft.facets[facet_index]
        if (
            facet.value_kind is ValueKindV1.FLOAT64_BITS
            and facet.value_bits_or_null == _NEGATIVE_ZERO_BITS
        ):
            facet = facet.model_copy(update={"value_bits_or_null": _POSITIVE_ZERO_BITS})
        facets.append(facet)
    memberships: list[ScaleMembershipV1] = []
    for membership_index in range(RTD_MAX_SCALE_MEMBERSHIPS):
        if membership_index == len(draft.scale_memberships):
            break
        membership = draft.scale_memberships[membership_index]
        if membership.weight_bits_or_null == _NEGATIVE_ZERO_BITS:
            membership = membership.model_copy(update={"weight_bits_or_null": _POSITIVE_ZERO_BITS})
        memberships.append(membership)
    return draft.model_copy(
        update={"facets": tuple(facets), "scale_memberships": tuple(memberships)}
    )


def parse_draft(payload: Mapping[str, object]) -> RtdDossierDraftV1:
    """Parse a trusted mapping through the closed generated structural type."""
    try:
        draft = _DRAFT_ADAPTER.validate_python(payload)
    except ValidationError as error:
        raise _translate_pydantic(error) from error
    _preflight_limits(draft)
    _validate_nested_limits(draft)
    normalized = _normalize_negative_zero(draft)
    validate_draft(normalized)
    return normalized


def parse_draft_json(payload: bytes) -> RtdDossierDraftV1:
    """Parse an untrusted bounded JSON byte payload with full consumption."""
    if len(payload) > RTD_MAX_JSON_INPUT_BYTES:
        raise _fail("RTD_CANONICAL_SIZE")
    _scan_json_depth(payload)
    try:
        decoded = json.loads(payload, object_pairs_hook=_unique_json_object)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise _fail("RTD_JSON") from error
    if not isinstance(decoded, dict):
        raise _fail("RTD_JSON")
    return parse_draft(decoded)


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    output: dict[str, object] = {}
    for pair_index in range(RTD_MAX_JSON_INPUT_BYTES + 1):
        if pair_index == len(pairs):
            return output
        key, value = pairs[pair_index]
        if key in output:
            raise _fail("RTD_DUPLICATE_KEY", key)
        output[key] = value
    return output


def _utf8_length(value: str, path: tuple[PathPart, ...]) -> int:
    try:
        return len(value.encode("utf-8"))
    except UnicodeEncodeError as error:
        raise RtdValidationError("RTD_NON_NFC", path) from error


def _validate_nfc(value: str, path: tuple[PathPart, ...]) -> None:
    if unicodedata.normalize("NFC", value) != value:
        raise RtdValidationError("RTD_NON_NFC", path)


def _identity_key(identity: TypedIdentityV1) -> bytes:
    output = bytearray()
    components = (identity.domain, identity.authority, identity.local_id)
    for component_index in range(RTD_IDENTITY_COMPONENT_COUNT):
        encoded = components[component_index].encode("utf-8")
        output.extend(len(encoded).to_bytes(2, "big"))
        output.extend(encoded)
    return bytes(output)


def _is_h3_identity(identity: TypedIdentityV1) -> bool:
    domain = identity.domain.casefold()
    local_id = identity.local_id.casefold()
    return domain in {"h3", "h3-cell"} or (
        domain in {"dimension", "native-scale"} and local_id.startswith("h3-")
    )


def _is_canadian_geography(identity: TypedIdentityV1) -> bool:
    if identity.domain.casefold() == "external":
        return False
    text = f"{identity.authority}/{identity.local_id}".casefold()
    geographic = identity.domain.casefold() in {
        "county",
        "geography",
        "h3",
        "jurisdiction",
        "metro",
        "msa",
        "nation",
        "state",
    }
    tokens = ("canada", "windsor", "essex")
    for token_index in range(RTD_CANADA_TOKEN_COUNT):
        if tokens[token_index] in text:
            return geographic
    return False


def _validate_identity(identity: TypedIdentityV1, path: tuple[PathPart, ...]) -> None:
    components = (identity.domain, identity.authority, identity.local_id)
    for component_index in range(RTD_IDENTITY_COMPONENT_COUNT):
        component = components[component_index]
        component_path = path + (("domain", "authority", "local_id")[component_index],)
        _validate_nfc(component, component_path)
        length = _utf8_length(component, component_path)
        if length == 0 or length > RTD_MAX_IDENTITY_BYTES:
            raise RtdValidationError("RTD_IDENTITY", component_path)
    if _is_h3_identity(identity):
        raise RtdValidationError("RTD_H3_BEFORE_PER21", path)
    if identity.local_id == "19820":
        raise RtdValidationError("RTD_MSA_EVIDENCE", path)
    if _is_canadian_geography(identity):
        raise RtdValidationError("RTD_CANADA_CONTROL", path)


def _validate_digest(value: str, path: tuple[PathPart, ...]) -> None:
    _validate_nfc(value, path)
    if _DIGEST_RE.fullmatch(value) is None:
        raise RtdValidationError("RTD_DIGEST", path)


def _validate_bits(value: str, kind: ValueKindV1, path: tuple[PathPart, ...]) -> None:
    if _BITS_RE.fullmatch(value) is None:
        raise RtdValidationError("RTD_STATUS_VALUE", path)
    if kind is ValueKindV1.FLOAT64_BITS:
        raw = int(value, 16)
        if ((raw >> 52) & 0x7FF) == 0x7FF:
            raise RtdValidationError("RTD_STATUS_VALUE", path)


def _validate_status_value(
    status: StatusV1,
    value: str | None,
    kind: ValueKindV1,
    path: tuple[PathPart, ...],
) -> None:
    if status is StatusV1.PRESENT:
        if value is None:
            raise RtdValidationError("RTD_STATUS_VALUE", path)
        _validate_bits(value, kind, path)
    elif value is not None:
        raise RtdValidationError("RTD_STATUS_VALUE", path)


def _ensure_tuple(value: object, path: tuple[PathPart, ...]) -> None:
    if not isinstance(value, tuple):
        raise RtdValidationError("RTD_JSON", path)


def _preflight_limits(draft: RtdDossierDraftV1) -> None:
    top_level = (
        (draft.focus, RTD_MAX_FOCUS, "focus"),
        (draft.reference_digests, RTD_MAX_REFERENCE_DIGESTS, "reference_digests"),
        (draft.scale_memberships, RTD_MAX_SCALE_MEMBERSHIPS, "scale_memberships"),
        (draft.facets, RTD_MAX_FACETS, "facets"),
        (draft.dyads, RTD_MAX_DYADS, "dyads"),
        (draft.hyperedges, RTD_MAX_HYPEREDGES, "hyperedges"),
        (draft.flows, RTD_MAX_FLOWS, "flows"),
        (draft.gaps, RTD_MAX_GAPS, "gaps"),
        (draft.provenance, RTD_MAX_PROVENANCE, "provenance"),
    )
    for collection_index in range(RTD_TOP_LEVEL_COLLECTION_COUNT):
        items, limit, name = top_level[collection_index]
        _ensure_tuple(items, (name,))
        if len(items) > limit:
            raise _fail("RTD_LIMIT_EXCEEDED", name)
    surface = draft.decision_surface
    display_lists = (
        (surface.signal_refs, "signal_refs"),
        (surface.action_refs, "action_refs"),
        (surface.receipt_refs, "receipt_refs"),
        (surface.archive_subject_refs, "archive_subject_refs"),
    )
    for display_index in range(RTD_DECISION_SURFACE_LIST_COUNT):
        items, name = display_lists[display_index]
        _ensure_tuple(items, ("decision_surface", name))
        if len(items) > RTD_MAX_DISPLAY_REFS:
            raise _fail("RTD_LIMIT_EXCEEDED", "decision_surface", name)


def _validate_nested_limits(draft: RtdDossierDraftV1) -> None:
    for facet_index in range(RTD_MAX_FACETS):
        if facet_index == len(draft.facets):
            break
        facet = draft.facets[facet_index]
        _ensure_tuple(facet.coordinates, ("facets", facet_index, "coordinates"))
        _ensure_tuple(facet.provenance_refs, ("facets", facet_index, "provenance_refs"))
        if len(facet.coordinates) > RTD_MAX_COORDINATES:
            raise _fail("RTD_LIMIT_EXCEEDED", "facets", facet_index, "coordinates")
        if len(facet.provenance_refs) > RTD_MAX_PROVENANCE_REFS:
            raise _fail("RTD_LIMIT_EXCEEDED", "facets", facet_index, "provenance_refs")
    for edge_index in range(RTD_MAX_HYPEREDGES):
        if edge_index == len(draft.hyperedges):
            break
        edge = draft.hyperedges[edge_index]
        _ensure_tuple(edge.member_refs, ("hyperedges", edge_index, "member_refs"))
        _ensure_tuple(edge.payload_facets, ("hyperedges", edge_index, "payload_facets"))
        _ensure_tuple(edge.provenance_refs, ("hyperedges", edge_index, "provenance_refs"))
        if len(edge.member_refs) > RTD_MAX_HYPEREDGE_MEMBERS:
            raise _fail("RTD_LIMIT_EXCEEDED", "hyperedges", edge_index, "member_refs")
        if len(edge.payload_facets) > RTD_MAX_PAYLOAD_FACETS:
            raise _fail("RTD_LIMIT_EXCEEDED", "hyperedges", edge_index, "payload_facets")
        if len(edge.provenance_refs) > RTD_MAX_PROVENANCE_REFS:
            raise _fail("RTD_LIMIT_EXCEEDED", "hyperedges", edge_index, "provenance_refs")
    _validate_relation_nested_limits(draft)


def _validate_relation_nested_limits(draft: RtdDossierDraftV1) -> None:
    relations = (draft.dyads, draft.flows)
    names = ("dyads", "flows")
    for family_index in range(RTD_RELATION_FAMILY_COUNT):
        rows = relations[family_index]
        name = names[family_index]
        for row_index in range(RTD_MAX_COLLECTION_ITEMS):
            if row_index == len(rows):
                break
            row = rows[row_index]
            _ensure_tuple(row.payload_facets, (name, row_index, "payload_facets"))
            _ensure_tuple(row.provenance_refs, (name, row_index, "provenance_refs"))
            if len(row.payload_facets) > RTD_MAX_PAYLOAD_FACETS:
                raise _fail("RTD_LIMIT_EXCEEDED", name, row_index, "payload_facets")
            if len(row.provenance_refs) > RTD_MAX_PROVENANCE_REFS:
                raise _fail("RTD_LIMIT_EXCEEDED", name, row_index, "provenance_refs")
    for membership_index in range(RTD_MAX_SCALE_MEMBERSHIPS):
        if membership_index == len(draft.scale_memberships):
            break
        _ensure_tuple(
            draft.scale_memberships[membership_index].provenance_refs,
            ("scale_memberships", membership_index, "provenance_refs"),
        )
        if len(draft.scale_memberships[membership_index].provenance_refs) > RTD_MAX_PROVENANCE_REFS:
            raise _fail(
                "RTD_LIMIT_EXCEEDED", "scale_memberships", membership_index, "provenance_refs"
            )
    for gap_index in range(RTD_MAX_GAPS):
        if gap_index == len(draft.gaps):
            break
        _ensure_tuple(
            draft.gaps[gap_index].provenance_refs,
            ("gaps", gap_index, "provenance_refs"),
        )
        if len(draft.gaps[gap_index].provenance_refs) > RTD_MAX_PROVENANCE_REFS:
            raise _fail("RTD_LIMIT_EXCEEDED", "gaps", gap_index, "provenance_refs")


def _check_unique_identity_tuple(
    items: tuple[TypedIdentityV1, ...], path: tuple[PathPart, ...]
) -> None:
    seen: set[bytes] = set()
    for item_index in range(RTD_MAX_COLLECTION_ITEMS):
        if item_index == len(items):
            return
        key = _identity_key(items[item_index])
        if key in seen:
            raise RtdValidationError("RTD_DUPLICATE_KEY", path + (item_index,))
        seen.add(key)


def _validate_identity_tuple(
    items: tuple[TypedIdentityV1, ...], path: tuple[PathPart, ...]
) -> None:
    _ensure_tuple(items, path)
    for item_index in range(RTD_MAX_COLLECTION_ITEMS):
        if item_index == len(items):
            return
        _validate_identity(items[item_index], path + (item_index,))


def _validate_top_identities(draft: RtdDossierDraftV1) -> None:
    _validate_identity_tuple(draft.focus, ("focus",))
    _check_unique_identity_tuple(draft.focus, ("focus",))
    if draft.actor is not None:
        _validate_identity(draft.actor, ("actor",))
    surface = draft.decision_surface
    _validate_identity(surface.question_id, ("decision_surface", "question_id"))
    display = (
        (surface.signal_refs, "signal_refs"),
        (surface.action_refs, "action_refs"),
        (surface.receipt_refs, "receipt_refs"),
        (surface.archive_subject_refs, "archive_subject_refs"),
    )
    for display_index in range(RTD_DECISION_SURFACE_LIST_COUNT):
        items, name = display[display_index]
        _validate_identity_tuple(items, ("decision_surface", name))
    for reference_index in range(RTD_MAX_REFERENCE_DIGESTS):
        if reference_index == len(draft.reference_digests):
            break
        row = draft.reference_digests[reference_index]
        path = ("reference_digests", reference_index)
        _validate_identity(row.reference_id, path + ("reference_id",))
        if row.artifact_schema_id_or_null is not None:
            _validate_identity(
                row.artifact_schema_id_or_null,
                path + ("artifact_schema_id_or_null",),
            )


def _validate_membership_identities(draft: RtdDossierDraftV1) -> None:
    for row_index in range(RTD_MAX_SCALE_MEMBERSHIPS):
        if row_index == len(draft.scale_memberships):
            return
        row = draft.scale_memberships[row_index]
        path = ("scale_memberships", row_index)
        _validate_identity(row.membership_id, path + ("membership_id",))
        _validate_identity(row.member_ref, path + ("member_ref",))
        _validate_identity(row.scale_ref, path + ("scale_ref",))
        _validate_identity_tuple(row.provenance_refs, path + ("provenance_refs",))
        _check_unique_identity_tuple(row.provenance_refs, path + ("provenance_refs",))


def _validate_facet_identities(draft: RtdDossierDraftV1) -> None:
    for row_index in range(RTD_MAX_FACETS):
        if row_index == len(draft.facets):
            return
        row = draft.facets[row_index]
        path = ("facets", row_index)
        identities = (row.facet_id, row.subject_ref, row.metric_id, row.unit_id, row.native_scale)
        names = ("facet_id", "subject_ref", "metric_id", "unit_id", "native_scale")
        for identity_index in range(RTD_FACET_IDENTITY_FIELD_COUNT):
            _validate_identity(identities[identity_index], path + (names[identity_index],))
        seen_dimensions: set[bytes] = set()
        for coordinate_index in range(RTD_MAX_COORDINATES):
            if coordinate_index == len(row.coordinates):
                break
            coordinate = row.coordinates[coordinate_index]
            coordinate_path = path + ("coordinates", coordinate_index)
            _validate_identity(coordinate.dimension_ref, coordinate_path + ("dimension_ref",))
            _validate_identity(coordinate.member_ref, coordinate_path + ("member_ref",))
            key = _identity_key(coordinate.dimension_ref)
            if key in seen_dimensions:
                raise RtdValidationError("RTD_DUPLICATE_KEY", coordinate_path)
            seen_dimensions.add(key)
        _validate_identity_tuple(row.provenance_refs, path + ("provenance_refs",))
        _check_unique_identity_tuple(row.provenance_refs, path + ("provenance_refs",))


def _validate_relation_identities(draft: RtdDossierDraftV1) -> None:
    for row_index in range(RTD_MAX_DYADS):
        if row_index == len(draft.dyads):
            break
        dyad_row = draft.dyads[row_index]
        dyad_path = ("dyads", row_index)
        dyad_identities = (
            ("relation_id", dyad_row.relation_id),
            ("from_ref", dyad_row.from_ref),
            ("to_ref", dyad_row.to_ref),
            ("native_scale", dyad_row.native_scale),
        )
        for identity_index in range(RTD_RELATION_IDENTITY_FIELD_COUNT):
            name, value = dyad_identities[identity_index]
            _validate_identity(value, dyad_path + (name,))
        if dyad_row.relation_id.domain.casefold() == "hyperedge":
            raise RtdValidationError("RTD_FORBIDDEN_REDUCTION", dyad_path + ("relation_id",))
        _validate_relation_identity_lists(
            dyad_row.payload_facets, dyad_row.provenance_refs, dyad_path
        )
    for row_index in range(RTD_MAX_FLOWS):
        if row_index == len(draft.flows):
            break
        flow_row = draft.flows[row_index]
        flow_path = ("flows", row_index)
        flow_identities = (
            ("flow_id", flow_row.flow_id),
            ("origin_ref", flow_row.origin_ref),
            ("destination_ref", flow_row.destination_ref),
            ("native_scale", flow_row.native_scale),
        )
        for identity_index in range(RTD_RELATION_IDENTITY_FIELD_COUNT):
            name, value = flow_identities[identity_index]
            _validate_identity(value, flow_path + (name,))
        _validate_relation_identity_lists(
            flow_row.payload_facets, flow_row.provenance_refs, flow_path
        )


def _validate_relation_identity_lists(
    payload: tuple[TypedIdentityV1, ...],
    provenance: tuple[TypedIdentityV1, ...],
    path: tuple[PathPart, ...],
) -> None:
    _validate_identity_tuple(payload, path + ("payload_facets",))
    _check_unique_identity_tuple(payload, path + ("payload_facets",))
    _validate_identity_tuple(provenance, path + ("provenance_refs",))
    _check_unique_identity_tuple(provenance, path + ("provenance_refs",))


def _validate_other_identities(draft: RtdDossierDraftV1) -> None:
    for row_index in range(RTD_MAX_HYPEREDGES):
        if row_index == len(draft.hyperedges):
            break
        edge = draft.hyperedges[row_index]
        edge_path = ("hyperedges", row_index)
        _validate_identity(edge.hyperedge_id, edge_path + ("hyperedge_id",))
        _validate_identity(edge.native_scale, edge_path + ("native_scale",))
        _validate_identity_tuple(edge.member_refs, edge_path + ("member_refs",))
        _check_unique_identity_tuple(edge.member_refs, edge_path + ("member_refs",))
        _validate_relation_identity_lists(edge.payload_facets, edge.provenance_refs, edge_path)
    for row_index in range(RTD_MAX_GAPS):
        if row_index == len(draft.gaps):
            break
        gap = draft.gaps[row_index]
        gap_path = ("gaps", row_index)
        _validate_identity(gap.gap_id, gap_path + ("gap_id",))
        _validate_identity(
            gap.requested_metric_or_relation,
            gap_path + ("requested_metric_or_relation",),
        )
        _validate_identity_tuple(gap.provenance_refs, gap_path + ("provenance_refs",))
        _check_unique_identity_tuple(gap.provenance_refs, gap_path + ("provenance_refs",))
    for row_index in range(RTD_MAX_PROVENANCE):
        if row_index == len(draft.provenance):
            break
        _validate_identity(
            draft.provenance[row_index].provenance_id,
            ("provenance", row_index, "provenance_id"),
        )


def _validate_scalar_fields(draft: RtdDossierDraftV1) -> None:
    if (
        draft.schema_ != RTD_V1_SCHEMA_ID
        or draft.schema_version != 1
        or draft.projection_version != 1
    ):
        raise _fail("RTD_SCHEMA_VERSION")
    digest_fields = (
        (draft.graph_state_hash, "graph_state_hash"),
        (draft.nominal_world_hash, "nominal_world_hash"),
        (draft.definitions_digest, "definitions_digest"),
        (draft.template_digest, "template_digest"),
    )
    for digest_index in range(RTD_TOP_LEVEL_DIGEST_COUNT):
        value, name = digest_fields[digest_index]
        _validate_digest(value, (name,))
    nullable_digests = (
        ("fog_policy_digest", draft.fog_policy_digest),
        ("knowledge_context_digest", draft.knowledge_context_digest),
    )
    for digest_index in range(RTD_NULLABLE_DIGEST_COUNT):
        nullable_name, nullable_value = nullable_digests[digest_index]
        if nullable_value is not None:
            _validate_digest(nullable_value, (nullable_name,))
    _validate_reference_scalars(draft)
    _validate_record_scalars(draft)


def _validate_reference_scalars(draft: RtdDossierDraftV1) -> None:
    for row_index in range(RTD_MAX_REFERENCE_DIGESTS):
        if row_index == len(draft.reference_digests):
            return
        row = draft.reference_digests[row_index]
        path = ("reference_digests", row_index)
        _validate_digest(row.sha256_hex, path + ("sha256_hex",))
        _validate_nfc(row.vintage, path + ("vintage",))
        length = _utf8_length(row.vintage, path + ("vintage",))
        if length == 0 or length > RTD_MAX_VINTAGE_BYTES:
            raise RtdValidationError("RTD_IDENTITY", path + ("vintage",))


def _validate_record_scalars(draft: RtdDossierDraftV1) -> None:
    for row_index in range(RTD_MAX_FACETS):
        if row_index == len(draft.facets):
            break
        facet = draft.facets[row_index]
        _validate_status_value(
            facet.status,
            facet.value_bits_or_null,
            facet.value_kind,
            ("facets", row_index, "value_bits_or_null"),
        )
        _validate_bounded_text(
            facet.vintage,
            RTD_MAX_VINTAGE_BYTES,
            ("facets", row_index, "vintage"),
            False,
        )
    for row_index in range(RTD_MAX_SCALE_MEMBERSHIPS):
        if row_index == len(draft.scale_memberships):
            break
        membership = draft.scale_memberships[row_index]
        _validate_status_value(
            membership.weight_status,
            membership.weight_bits_or_null,
            ValueKindV1.FLOAT64_BITS,
            ("scale_memberships", row_index, "weight_bits_or_null"),
        )
    _validate_gap_and_provenance_scalars(draft)


def _validate_bounded_text(
    value: str, limit: int, path: tuple[PathPart, ...], allow_empty: bool
) -> None:
    _validate_nfc(value, path)
    length = _utf8_length(value, path)
    if length > limit or (not allow_empty and length == 0):
        raise RtdValidationError("RTD_IDENTITY", path)


def _validate_gap_and_provenance_scalars(draft: RtdDossierDraftV1) -> None:
    for row_index in range(RTD_MAX_GAPS):
        if row_index == len(draft.gaps):
            break
        producer = draft.gaps[row_index].required_producer_or_null
        if producer is not None:
            path = ("gaps", row_index, "required_producer_or_null")
            _validate_bounded_text(producer, RTD_MAX_PRODUCER_BYTES, path, False)
            if _PRODUCER_RE.fullmatch(producer) is None:
                raise RtdValidationError("RTD_IDENTITY", path)
    for row_index in range(RTD_MAX_PROVENANCE):
        if row_index == len(draft.provenance):
            break
        provenance = draft.provenance[row_index]
        provenance_path: tuple[PathPart, ...] = ("provenance", row_index)
        _validate_digest(provenance.artifact_digest, provenance_path + ("artifact_digest",))
        if provenance.transformation_digest_or_null is not None:
            _validate_digest(
                provenance.transformation_digest_or_null,
                provenance_path + ("transformation_digest_or_null",),
            )
        _validate_bounded_text(
            provenance.locator,
            RTD_MAX_LOCATOR_BYTES,
            provenance_path + ("locator",),
            True,
        )
        _validate_bounded_text(
            provenance.vintage,
            RTD_MAX_VINTAGE_BYTES,
            provenance_path + ("vintage",),
            False,
        )


def _record_identity_key(row: object) -> bytes:
    attributes = (
        "membership_id",
        "facet_id",
        "relation_id",
        "hyperedge_id",
        "flow_id",
        "gap_id",
        "provenance_id",
    )
    for attribute_index in range(RTD_RECORD_ID_ATTRIBUTE_COUNT):
        attribute = attributes[attribute_index]
        value = getattr(row, attribute, None)
        if isinstance(value, TypedIdentityV1):
            return _identity_key(value)
    raise AssertionError("generated RTD record lacks an identity")


def _validate_canonical_sets(draft: RtdDossierDraftV1) -> None:
    reference_seen: set[bytes] = set()
    for row_index in range(RTD_MAX_REFERENCE_DIGESTS):
        if row_index == len(draft.reference_digests):
            break
        key = _identity_key(draft.reference_digests[row_index].reference_id)
        if key in reference_seen:
            raise _fail("RTD_DUPLICATE_KEY", "reference_digests", row_index)
        reference_seen.add(key)
    global_ids: set[bytes] = set()
    arrays = (
        (draft.scale_memberships, "scale_memberships"),
        (draft.facets, "facets"),
        (draft.dyads, "dyads"),
        (draft.hyperedges, "hyperedges"),
        (draft.flows, "flows"),
        (draft.gaps, "gaps"),
        (draft.provenance, "provenance"),
    )
    for array_index in range(RTD_RECORD_ARRAY_COUNT):
        rows, name = arrays[array_index]
        for row_index in range(RTD_MAX_COLLECTION_ITEMS):
            if row_index == len(rows):
                break
            key = _record_identity_key(rows[row_index])
            if key in global_ids:
                raise _fail("RTD_DUPLICATE_KEY", name, row_index)
            global_ids.add(key)


def _provenance_keys(draft: RtdDossierDraftV1) -> set[bytes]:
    keys: set[bytes] = set()
    for row_index in range(RTD_MAX_PROVENANCE):
        if row_index == len(draft.provenance):
            return keys
        keys.add(_identity_key(draft.provenance[row_index].provenance_id))
    return keys


def _facet_map(draft: RtdDossierDraftV1) -> dict[bytes, FacetV1]:
    facets: dict[bytes, FacetV1] = {}
    for row_index in range(RTD_MAX_FACETS):
        if row_index == len(draft.facets):
            return facets
        facet = draft.facets[row_index]
        facets[_identity_key(facet.facet_id)] = facet
    return facets


def _display_subject_keys(draft: RtdDossierDraftV1) -> set[bytes]:
    keys: set[bytes] = set()
    for focus_index in range(RTD_MAX_FOCUS):
        if focus_index == len(draft.focus):
            break
        keys.add(_identity_key(draft.focus[focus_index]))
    arrays = (
        draft.scale_memberships,
        draft.facets,
        draft.dyads,
        draft.hyperedges,
        draft.flows,
        draft.gaps,
        draft.provenance,
    )
    for array_index in range(RTD_RECORD_ARRAY_COUNT):
        rows = arrays[array_index]
        for row_index in range(RTD_MAX_COLLECTION_ITEMS):
            if row_index == len(rows):
                break
            keys.add(_record_identity_key(rows[row_index]))
    return keys


def _validate_signal_closure(draft: RtdDossierDraftV1) -> None:
    declared = _display_subject_keys(draft)
    refs = draft.decision_surface.signal_refs
    for ref_index in range(RTD_MAX_DISPLAY_REFS):
        if ref_index == len(refs):
            return
        if _identity_key(refs[ref_index]) not in declared:
            raise _fail("RTD_DANGLING_REF", "decision_surface", "signal_refs", ref_index)


def _check_reference_tuple(
    refs: tuple[TypedIdentityV1, ...], declared: set[bytes], path: tuple[PathPart, ...]
) -> None:
    for ref_index in range(RTD_MAX_COLLECTION_ITEMS):
        if ref_index == len(refs):
            return
        if _identity_key(refs[ref_index]) not in declared:
            raise RtdValidationError("RTD_DANGLING_REF", path + (ref_index,))


def _validate_reference_closure(draft: RtdDossierDraftV1) -> None:
    _validate_provenance_closure(draft)
    _validate_payload_closure(draft)
    _validate_signal_closure(draft)


def _validate_provenance_closure(draft: RtdDossierDraftV1) -> None:
    provenance = _provenance_keys(draft)
    for row_index in range(RTD_MAX_SCALE_MEMBERSHIPS):
        if row_index == len(draft.scale_memberships):
            break
        _check_reference_tuple(
            draft.scale_memberships[row_index].provenance_refs,
            provenance,
            ("scale_memberships", row_index, "provenance_refs"),
        )
    for row_index in range(RTD_MAX_FACETS):
        if row_index == len(draft.facets):
            break
        _check_reference_tuple(
            draft.facets[row_index].provenance_refs,
            provenance,
            ("facets", row_index, "provenance_refs"),
        )
    for row_index in range(RTD_MAX_DYADS):
        if row_index == len(draft.dyads):
            break
        _check_reference_tuple(
            draft.dyads[row_index].provenance_refs,
            provenance,
            ("dyads", row_index, "provenance_refs"),
        )
    for row_index in range(RTD_MAX_HYPEREDGES):
        if row_index == len(draft.hyperedges):
            break
        _check_reference_tuple(
            draft.hyperedges[row_index].provenance_refs,
            provenance,
            ("hyperedges", row_index, "provenance_refs"),
        )
    for row_index in range(RTD_MAX_FLOWS):
        if row_index == len(draft.flows):
            break
        _check_reference_tuple(
            draft.flows[row_index].provenance_refs,
            provenance,
            ("flows", row_index, "provenance_refs"),
        )
    for row_index in range(RTD_MAX_GAPS):
        if row_index == len(draft.gaps):
            break
        _check_reference_tuple(
            draft.gaps[row_index].provenance_refs,
            provenance,
            ("gaps", row_index, "provenance_refs"),
        )


def _validate_payload_closure(draft: RtdDossierDraftV1) -> None:
    facets = set(_facet_map(draft))
    for row_index in range(RTD_MAX_DYADS):
        if row_index == len(draft.dyads):
            break
        _check_reference_tuple(
            draft.dyads[row_index].payload_facets,
            facets,
            ("dyads", row_index, "payload_facets"),
        )
    for row_index in range(RTD_MAX_HYPEREDGES):
        if row_index == len(draft.hyperedges):
            break
        _check_reference_tuple(
            draft.hyperedges[row_index].payload_facets,
            facets,
            ("hyperedges", row_index, "payload_facets"),
        )
    for row_index in range(RTD_MAX_FLOWS):
        if row_index == len(draft.flows):
            break
        _check_reference_tuple(
            draft.flows[row_index].payload_facets,
            facets,
            ("flows", row_index, "payload_facets"),
        )


def _metric_row(metric: TypedIdentityV1, path: tuple[PathPart, ...]) -> RtdMetricRegistryRowV1:
    key = _identity_key(metric)
    for row_index in range(RTD_METRIC_REGISTRY_ROWS):
        row = RTD_V1_METRIC_REGISTRY[row_index]
        if _identity_key(row.metric) == key:
            return row
    raise RtdValidationError("RTD_NATIVE_GRAIN", path)


def _is_registered_h3_metric(identity: TypedIdentityV1) -> bool:
    supplied_key = _identity_key(identity)
    for row_index in range(RTD_METRIC_REGISTRY_ROWS):
        row = RTD_V1_METRIC_REGISTRY[row_index]
        if row.metric.local_id in _H3_METRICS and _identity_key(row.metric) == supplied_key:
            return True
    return False


def _reference_digest_matches(
    draft: RtdDossierDraftV1,
    row: RtdMetricRegistryRowV1,
    path: tuple[PathPart, ...],
) -> None:
    if row.reference_artifact is None or row.reference_digest is None:
        return
    wanted = _identity_key(row.reference_artifact)
    for reference_index in range(RTD_MAX_REFERENCE_DIGESTS):
        if reference_index == len(draft.reference_digests):
            break
        supplied = draft.reference_digests[reference_index]
        if _identity_key(supplied.reference_id) == wanted:
            if supplied.sha256_hex != row.reference_digest:
                raise RtdValidationError("RTD_DIGEST", path)
            return
    raise RtdValidationError("RTD_DIGEST", path)


def _coordinate_keys(facet: FacetV1) -> set[bytes]:
    keys: set[bytes] = set()
    for coordinate_index in range(RTD_MAX_COORDINATES):
        if coordinate_index == len(facet.coordinates):
            return keys
        keys.add(_identity_key(facet.coordinates[coordinate_index].dimension_ref))
    return keys


def _required_coordinate_keys(row: RtdMetricRegistryRowV1) -> set[bytes]:
    keys: set[bytes] = set()
    for coordinate_index in range(RTD_MAX_COORDINATES):
        if coordinate_index == len(row.coordinates):
            return keys
        keys.add(_identity_key(row.coordinates[coordinate_index]))
    return keys


def _validate_facets(draft: RtdDossierDraftV1) -> None:
    for facet_index in range(RTD_MAX_FACETS):
        if facet_index == len(draft.facets):
            return
        facet = draft.facets[facet_index]
        path = ("facets", facet_index)
        row = _metric_row(facet.metric_id, path + ("metric_id",))
        if row.metric.local_id in _H3_METRICS:
            raise RtdValidationError("RTD_H3_BEFORE_PER21", path + ("metric_id",))
        if row.value_kind is None or facet.value_kind is not row.value_kind:
            raise RtdValidationError("RTD_NATIVE_GRAIN", path + ("value_kind",))
        if _identity_key(facet.unit_id) != _identity_key(row.unit):
            raise RtdValidationError("RTD_NATIVE_GRAIN", path + ("unit_id",))
        if _identity_key(facet.native_scale) != _identity_key(row.native_scale):
            raise RtdValidationError("RTD_NATIVE_GRAIN", path + ("native_scale",))
        if _coordinate_keys(facet) != _required_coordinate_keys(row):
            raise RtdValidationError("RTD_NATIVE_GRAIN", path + ("coordinates",))
        if facet.evidence_class not in row.evidence_classes:
            raise RtdValidationError("RTD_NATIVE_GRAIN", path + ("evidence_class",))
        _reference_digest_matches(draft, row, path + ("metric_id",))


def _binding(family: str, kind: str, path: tuple[PathPart, ...]) -> RtdRelationBindingRegistryRowV1:
    for row_index in range(RTD_RELATION_BINDING_ROWS):
        row = RTD_V1_RELATION_BINDING_REGISTRY[row_index]
        if row.record_family == family and row.kind == kind:
            return row
    raise RtdValidationError("RTD_NATIVE_GRAIN", path)


def _validate_dyad(dyad: DyadV1, index: int) -> None:
    path = ("dyads", index)
    binding = _binding("DYAD", dyad.relation_kind.value, path + ("relation_kind",))
    if (
        binding.payload_mode
        in {
            RelationPayloadModeV1.EMPTY,
            RelationPayloadModeV1.IMPLICIT_RELATION,
        }
        and dyad.payload_facets
    ):
        raise RtdValidationError("RTD_NATIVE_GRAIN", path + ("payload_facets",))
    if binding.metric is None:
        return
    metric = _metric_row(binding.metric, path + ("relation_kind",))
    if metric.representation is not MetricRepresentationV1.DYAD:
        raise RtdValidationError("RTD_NATIVE_GRAIN", path + ("relation_kind",))
    if _identity_key(dyad.native_scale) != _identity_key(metric.native_scale):
        raise RtdValidationError("RTD_NATIVE_GRAIN", path + ("native_scale",))
    if dyad.evidence_class not in metric.evidence_classes:
        raise RtdValidationError("RTD_NATIVE_GRAIN", path + ("evidence_class",))


def _is_canada_endpoint(identity: TypedIdentityV1) -> bool:
    text = f"{identity.domain}/{identity.authority}/{identity.local_id}".casefold()
    tokens = ("canada", "windsor", "essex")
    found = False
    for token_index in range(RTD_CANADA_TOKEN_COUNT):
        found = found or tokens[token_index] in text
    return found


def _coordinate_member(facet: FacetV1, dimension: TypedIdentityV1) -> TypedIdentityV1 | None:
    wanted = _identity_key(dimension)
    for coordinate_index in range(RTD_MAX_COORDINATES):
        if coordinate_index == len(facet.coordinates):
            return None
        coordinate = facet.coordinates[coordinate_index]
        if _identity_key(coordinate.dimension_ref) == wanted:
            return coordinate.member_ref
    return None


def _validate_flow_payload(
    flow: ReferenceFlowV1,
    index: int,
    binding: RtdRelationBindingRegistryRowV1,
    facets: dict[bytes, FacetV1],
    used: set[bytes],
) -> None:
    path = ("flows", index)
    if binding.payload_mode is RelationPayloadModeV1.EMPTY:
        if flow.payload_facets:
            raise RtdValidationError("RTD_NATIVE_GRAIN", path + ("payload_facets",))
        return
    if len(flow.payload_facets) != 1 or binding.metric is None:
        raise RtdValidationError("RTD_NATIVE_GRAIN", path + ("payload_facets",))
    facet_key = _identity_key(flow.payload_facets[0])
    if facet_key in used:
        raise RtdValidationError("RTD_DUPLICATE_KEY", path + ("payload_facets", 0))
    used.add(facet_key)
    facet = facets[facet_key]
    if _identity_key(facet.subject_ref) != _identity_key(flow.flow_id):
        raise RtdValidationError("RTD_NATIVE_GRAIN", path + ("payload_facets", 0))
    if _identity_key(facet.metric_id) != _identity_key(binding.metric):
        raise RtdValidationError("RTD_NATIVE_GRAIN", path + ("payload_facets", 0))
    metric = _metric_row(binding.metric, path + ("flow_kind",))
    if metric.representation is not MetricRepresentationV1.REFERENCE_FLOW:
        raise RtdValidationError("RTD_NATIVE_GRAIN", path + ("flow_kind",))
    if _identity_key(flow.native_scale) != _identity_key(metric.native_scale):
        raise RtdValidationError("RTD_NATIVE_GRAIN", path + ("native_scale",))
    if flow.evidence_class not in metric.evidence_classes:
        raise RtdValidationError("RTD_NATIVE_GRAIN", path + ("evidence_class",))
    origin = _coordinate_member(facet, metric.coordinates[0])
    destination = _coordinate_member(facet, metric.coordinates[1])
    if origin is None or _identity_key(origin) != _identity_key(flow.origin_ref):
        raise RtdValidationError("RTD_NATIVE_GRAIN", path + ("origin_ref",))
    if destination is None or _identity_key(destination) != _identity_key(flow.destination_ref):
        raise RtdValidationError("RTD_NATIVE_GRAIN", path + ("destination_ref",))


def _validate_relations(draft: RtdDossierDraftV1) -> None:
    for dyad_index in range(RTD_MAX_DYADS):
        if dyad_index == len(draft.dyads):
            break
        _validate_dyad(draft.dyads[dyad_index], dyad_index)
    facets = _facet_map(draft)
    used: set[bytes] = set()
    for flow_index in range(RTD_MAX_FLOWS):
        if flow_index == len(draft.flows):
            break
        flow = draft.flows[flow_index]
        path = ("flows", flow_index)
        if flow.flow_kind is FlowKindV1.COMMUTER_JOBS and (
            _is_canada_endpoint(flow.origin_ref) or _is_canada_endpoint(flow.destination_ref)
        ):
            raise RtdValidationError("RTD_CANADA_CONTROL", path)
        binding = _binding("REFERENCE_FLOW", flow.flow_kind.value, path + ("flow_kind",))
        _validate_flow_payload(flow, flow_index, binding, facets, used)
    for facet_index in range(RTD_MAX_FACETS):
        if facet_index == len(draft.facets):
            break
        facet = draft.facets[facet_index]
        metric = _metric_row(facet.metric_id, ("facets", facet_index, "metric_id"))
        if (
            metric.representation is MetricRepresentationV1.REFERENCE_FLOW
            and _identity_key(facet.facet_id) not in used
        ):
            raise _fail("RTD_DANGLING_REF", "facets", facet_index, "facet_id")


def _validate_canadian_flows(draft: RtdDossierDraftV1) -> None:
    for flow_index in range(RTD_MAX_FLOWS):
        if flow_index == len(draft.flows):
            return
        flow = draft.flows[flow_index]
        if flow.flow_kind is FlowKindV1.COMMUTER_JOBS and (
            _is_canada_endpoint(flow.origin_ref) or _is_canada_endpoint(flow.destination_ref)
        ):
            raise _fail("RTD_CANADA_CONTROL", "flows", flow_index)


def _validate_memberships_and_gaps(draft: RtdDossierDraftV1) -> None:
    for row_index in range(RTD_MAX_SCALE_MEMBERSHIPS):
        if row_index == len(draft.scale_memberships):
            break
        row = draft.scale_memberships[row_index]
        path = ("scale_memberships", row_index)
        if row.membership_kind is MembershipKindV1.WEIGHTED_OVERLAP:
            raise RtdValidationError("RTD_UNSUPPORTED_DOWNSCALE", path)
        if row.membership_kind is MembershipKindV1.METROPOLITAN:
            raise RtdValidationError("RTD_MSA_EVIDENCE", path)
    for row_index in range(RTD_MAX_GAPS):
        if row_index == len(draft.gaps):
            break
        _validate_gap(draft.gaps[row_index], row_index)


def _validate_gap(gap: GapV1, index: int) -> None:
    if not _is_registered_h3_metric(gap.requested_metric_or_relation):
        return
    path = ("gaps", index)
    if (
        gap.status is not StatusV1.NOT_COMPUTED
        or gap.reason_code.value != "IDENTITY_CONTRACT_PENDING"
        or gap.required_producer_or_null != "PER-21"
    ):
        raise RtdValidationError("RTD_H3_BEFORE_PER21", path)


def _validate_admin_boundary(draft: RtdDossierDraftV1) -> None:
    if draft.audience is not AudienceV1.ADMIN_MATERIAL:
        raise _fail("RTD_FORBIDDEN_REDUCTION", "audience")
    if draft.durability is not DurabilityV1.IN_MEMORY:
        raise _fail("RTD_FORBIDDEN_REDUCTION", "durability")
    if draft.fog_policy_digest is not None:
        raise _fail("RTD_FORBIDDEN_REDUCTION", "fog_policy_digest")
    if draft.knowledge_context_digest is not None:
        raise _fail("RTD_FORBIDDEN_REDUCTION", "knowledge_context_digest")
    if draft.actor is not None:
        raise _fail("RTD_FORBIDDEN_REDUCTION", "actor")
    surface = draft.decision_surface
    forbidden_lists = (
        ("action_refs", surface.action_refs),
        ("receipt_refs", surface.receipt_refs),
        ("archive_subject_refs", surface.archive_subject_refs),
    )
    for list_index in range(RTD_ADMIN_FORBIDDEN_LIST_COUNT):
        name, refs = forbidden_lists[list_index]
        if refs:
            raise _fail("RTD_FORBIDDEN_REDUCTION", "decision_surface", name)


def validate_draft(draft: RtdDossierDraftV1) -> None:
    """Validate one generated draft without publishing any derived artifact."""
    if not isinstance(draft, RtdDossierDraftV1):
        raise _fail("RTD_JSON")
    _preflight_limits(draft)
    _validate_nested_limits(draft)
    _validate_scalar_fields(draft)
    _validate_top_identities(draft)
    _validate_membership_identities(draft)
    _validate_facet_identities(draft)
    _validate_relation_identities(draft)
    _validate_other_identities(draft)
    _validate_canonical_sets(draft)
    _validate_canadian_flows(draft)
    _validate_reference_closure(draft)
    _validate_memberships_and_gaps(draft)
    _validate_admin_boundary(draft)
    _validate_facets(draft)
    _validate_relations(draft)


@dataclass(frozen=True, slots=True)
class RtdVectorCaseV1:
    """One closed shared canonical-vector envelope."""

    case_id: str
    kind: str
    draft: Mapping[str, object]
    canonical_utf8_hex: str = ""
    projection_hash: str = ""
    error: str = ""


def _validate_case_id(case_id: object) -> str:
    if not isinstance(case_id, str):
        raise _fail("RTD_VECTOR_LIMIT", "case_id")
    _validate_nfc(case_id, ("case_id",))
    length = _utf8_length(case_id, ("case_id",))
    if length == 0 or length > RTD_MAX_CASE_ID_BYTES:
        raise _fail("RTD_VECTOR_LIMIT", "case_id")
    return case_id


def _parse_valid_vector(decoded: dict[str, object], case_id: str) -> RtdVectorCaseV1:
    expected = {"case_id", "kind", "draft", "canonical_utf8_hex", "projection_hash"}
    if set(decoded) != expected:
        raise _fail("RTD_UNKNOWN_FIELD")
    draft = decoded["draft"]
    canonical_hex = decoded["canonical_utf8_hex"]
    expected_hash = decoded["projection_hash"]
    if not isinstance(draft, dict):
        raise _fail("RTD_JSON", "draft")
    if not isinstance(canonical_hex, str) or not isinstance(expected_hash, str):
        raise _fail("RTD_JSON")
    if len(canonical_hex) % 2 != 0 or re.fullmatch(r"[0-9a-f]*", canonical_hex) is None:
        raise _fail("RTD_JSON", "canonical_utf8_hex")
    if _DIGEST_RE.fullmatch(expected_hash) is None:
        raise _fail("RTD_DIGEST", "projection_hash")
    return RtdVectorCaseV1(case_id, "valid", draft, canonical_hex, expected_hash)


def _parse_invalid_vector(decoded: dict[str, object], case_id: str) -> RtdVectorCaseV1:
    expected = {"case_id", "kind", "draft", "error"}
    if set(decoded) != expected:
        raise _fail("RTD_UNKNOWN_FIELD")
    draft = decoded["draft"]
    error = decoded["error"]
    if not isinstance(draft, dict):
        raise _fail("RTD_JSON", "draft")
    if not isinstance(error, str) or error not in RTD_V1_ERROR_REGISTRY:
        raise _fail("RTD_ENUM", "error")
    return RtdVectorCaseV1(case_id, "invalid", draft, error=error)


def _parse_vector_line(line: bytes) -> RtdVectorCaseV1:
    if len(line) > RTD_MAX_VECTOR_LINE_BYTES:
        raise _fail("RTD_VECTOR_LIMIT")
    line = line.removesuffix(b"\n").removesuffix(b"\r")
    _scan_json_depth(line)
    try:
        decoded = json.loads(line, object_pairs_hook=_unique_json_object)
    except RtdValidationError:
        raise
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise _fail("RTD_JSON") from error
    if not isinstance(decoded, dict):
        raise _fail("RTD_JSON")
    case_id = _validate_case_id(decoded.get("case_id"))
    kind = decoded.get("kind")
    if kind == "valid":
        return _parse_valid_vector(decoded, case_id)
    if kind == "invalid":
        return _parse_invalid_vector(decoded, case_id)
    raise _fail("RTD_VECTOR_LIMIT", "kind")


def parse_vector_corpus(payload: bytes) -> tuple[RtdVectorCaseV1, ...]:
    """Parse the closed, bounded RTD JSONL conformance corpus."""
    if len(payload) > RTD_MAX_VECTOR_BYTES:
        raise _fail("RTD_VECTOR_LIMIT")
    output: list[RtdVectorCaseV1] = []
    seen: set[str] = set()
    line_source = BytesIO(payload)
    for line_index, line in enumerate(islice(line_source, RTD_MAX_VECTOR_LINES + 1)):
        if line_index == RTD_MAX_VECTOR_LINES:
            raise _fail("RTD_VECTOR_LIMIT")
        case = _parse_vector_line(line)
        if case.case_id in seen:
            raise _fail("RTD_DUPLICATE_KEY", "case_id")
        seen.add(case.case_id)
        output.append(case)
    return tuple(output)


class _CanonicalWriter:
    __slots__ = ("_buffer", "_count")

    def __init__(self) -> None:
        self._buffer = bytearray()
        self._count = 0

    def write(self, value: bytes) -> None:
        next_count = self._count + len(value)
        if next_count > RTD_MAX_JSON_INPUT_BYTES:
            raise _fail("RTD_CANONICAL_SIZE")
        self._buffer.extend(value)
        self._count = next_count

    def finish(self) -> bytes:
        return bytes(self._buffer)


def _write_string(writer: _CanonicalWriter, value: str) -> None:
    encoded = value.encode("utf-8")
    writer.write(b'"')
    escapes = {
        0x08: b"\\b",
        0x09: b"\\t",
        0x0A: b"\\n",
        0x0C: b"\\f",
        0x0D: b"\\r",
        0x22: b'\\"',
        0x5C: b"\\\\",
    }
    for byte_index in range(RTD_MAX_JSON_INPUT_BYTES + 1):
        if byte_index == len(encoded):
            break
        byte = encoded[byte_index]
        escaped = escapes.get(byte)
        if escaped is not None:
            writer.write(escaped)
        elif byte < 0x20:
            writer.write(f"\\u{byte:04x}".encode("ascii"))
        else:
            writer.write(bytes((byte,)))
    writer.write(b'"')


def _field(writer: _CanonicalWriter, key: str, first: bool) -> bool:
    if not first:
        writer.write(b",")
    _write_string(writer, key)
    writer.write(b":")
    return False


def _write_nullable_string(writer: _CanonicalWriter, value: str | None) -> None:
    if value is None:
        writer.write(b"null")
    else:
        _write_string(writer, value)


def _write_u64(writer: _CanonicalWriter, value: int) -> None:
    writer.write(str(value).encode("ascii"))


def _write_enum(writer: _CanonicalWriter, value: object) -> None:
    enum_value = getattr(value, "value", None)
    if not isinstance(enum_value, str):
        raise AssertionError("generated RTD enum lacks a string value")
    _write_string(writer, enum_value)


def _write_identity(writer: _CanonicalWriter, identity: TypedIdentityV1) -> None:
    writer.write(b"{")
    first = _field(writer, "authority", True)
    _write_string(writer, identity.authority)
    first = _field(writer, "domain", first)
    _write_string(writer, identity.domain)
    _field(writer, "local_id", first)
    _write_string(writer, identity.local_id)
    writer.write(b"}")


def _write_nullable_identity(writer: _CanonicalWriter, identity: TypedIdentityV1 | None) -> None:
    if identity is None:
        writer.write(b"null")
    else:
        _write_identity(writer, identity)


def _write_array[T](
    writer: _CanonicalWriter,
    items: tuple[T, ...],
    emit: Callable[[_CanonicalWriter, T], None],
    sort_key: Callable[[T], bytes] | None,
) -> None:
    ordered = items if sort_key is None else tuple(sorted(items, key=sort_key))
    writer.write(b"[")
    for item_index in range(RTD_MAX_COLLECTION_ITEMS):
        if item_index == len(ordered):
            break
        if item_index != 0:
            writer.write(b",")
        emit(writer, ordered[item_index])
    writer.write(b"]")


def _write_identity_array(
    writer: _CanonicalWriter,
    items: tuple[TypedIdentityV1, ...],
    preserve_order: bool = False,
) -> None:
    _write_array(writer, items, _write_identity, None if preserve_order else _identity_key)


def _write_reference(writer: _CanonicalWriter, row: ReferenceDigestV1) -> None:
    writer.write(b"{")
    first = _field(writer, "artifact_schema_id_or_null", True)
    _write_nullable_identity(writer, row.artifact_schema_id_or_null)
    first = _field(writer, "evidence_class", first)
    _write_enum(writer, row.evidence_class)
    first = _field(writer, "reference_id", first)
    _write_identity(writer, row.reference_id)
    first = _field(writer, "sha256_hex", first)
    _write_string(writer, row.sha256_hex)
    _field(writer, "vintage", first)
    _write_string(writer, row.vintage)
    writer.write(b"}")


def _write_coordinate(writer: _CanonicalWriter, row: DimensionCoordinateV1) -> None:
    writer.write(b"{")
    first = _field(writer, "dimension_ref", True)
    _write_identity(writer, row.dimension_ref)
    _field(writer, "member_ref", first)
    _write_identity(writer, row.member_ref)
    writer.write(b"}")


def _write_membership(writer: _CanonicalWriter, row: ScaleMembershipV1) -> None:
    writer.write(b"{")
    first = _field(writer, "coverage", True)
    _write_enum(writer, row.coverage)
    first = _field(writer, "evidence_class", first)
    _write_enum(writer, row.evidence_class)
    first = _field(writer, "member_ref", first)
    _write_identity(writer, row.member_ref)
    first = _field(writer, "membership_id", first)
    _write_identity(writer, row.membership_id)
    first = _field(writer, "membership_kind", first)
    _write_enum(writer, row.membership_kind)
    first = _field(writer, "provenance_refs", first)
    _write_identity_array(writer, row.provenance_refs)
    first = _field(writer, "scale_ref", first)
    _write_identity(writer, row.scale_ref)
    first = _field(writer, "status", first)
    _write_enum(writer, row.status)
    first = _field(writer, "weight_bits_or_null", first)
    _write_nullable_string(writer, row.weight_bits_or_null)
    _field(writer, "weight_status", first)
    _write_enum(writer, row.weight_status)
    writer.write(b"}")


def _write_facet(writer: _CanonicalWriter, row: FacetV1) -> None:
    writer.write(b"{")
    first = _field(writer, "coordinates", True)
    _write_array(
        writer, row.coordinates, _write_coordinate, lambda item: _identity_key(item.dimension_ref)
    )
    first = _field(writer, "coverage", first)
    _write_enum(writer, row.coverage)
    first = _field(writer, "evidence_class", first)
    _write_enum(writer, row.evidence_class)
    first = _field(writer, "facet_id", first)
    _write_identity(writer, row.facet_id)
    first = _field(writer, "family", first)
    _write_enum(writer, row.family)
    first = _field(writer, "metric_id", first)
    _write_identity(writer, row.metric_id)
    first = _field(writer, "native_scale", first)
    _write_identity(writer, row.native_scale)
    first = _field(writer, "provenance_refs", first)
    _write_identity_array(writer, row.provenance_refs)
    first = _field(writer, "status", first)
    _write_enum(writer, row.status)
    first = _field(writer, "subject_ref", first)
    _write_identity(writer, row.subject_ref)
    first = _field(writer, "unit_id", first)
    _write_identity(writer, row.unit_id)
    first = _field(writer, "value_bits_or_null", first)
    _write_nullable_string(writer, row.value_bits_or_null)
    first = _field(writer, "value_kind", first)
    _write_enum(writer, row.value_kind)
    _field(writer, "vintage", first)
    _write_string(writer, row.vintage)
    writer.write(b"}")


def _write_dyad(writer: _CanonicalWriter, row: DyadV1) -> None:
    writer.write(b"{")
    first = _field(writer, "coverage", True)
    _write_enum(writer, row.coverage)
    first = _field(writer, "evidence_class", first)
    _write_enum(writer, row.evidence_class)
    first = _field(writer, "from_ref", first)
    _write_identity(writer, row.from_ref)
    first = _field(writer, "native_scale", first)
    _write_identity(writer, row.native_scale)
    first = _field(writer, "payload_facets", first)
    _write_identity_array(writer, row.payload_facets)
    first = _field(writer, "provenance_refs", first)
    _write_identity_array(writer, row.provenance_refs)
    first = _field(writer, "relation_id", first)
    _write_identity(writer, row.relation_id)
    first = _field(writer, "relation_kind", first)
    _write_enum(writer, row.relation_kind)
    first = _field(writer, "status", first)
    _write_enum(writer, row.status)
    _field(writer, "to_ref", first)
    _write_identity(writer, row.to_ref)
    writer.write(b"}")


def _write_hyperedge(writer: _CanonicalWriter, row: HyperedgeV1) -> None:
    writer.write(b"{")
    first = _field(writer, "coverage", True)
    _write_enum(writer, row.coverage)
    first = _field(writer, "evidence_class", first)
    _write_enum(writer, row.evidence_class)
    first = _field(writer, "hyperedge_id", first)
    _write_identity(writer, row.hyperedge_id)
    first = _field(writer, "hyperedge_kind", first)
    _write_enum(writer, row.hyperedge_kind)
    first = _field(writer, "member_refs", first)
    _write_identity_array(writer, row.member_refs)
    first = _field(writer, "native_scale", first)
    _write_identity(writer, row.native_scale)
    first = _field(writer, "payload_facets", first)
    _write_identity_array(writer, row.payload_facets)
    first = _field(writer, "provenance_refs", first)
    _write_identity_array(writer, row.provenance_refs)
    _field(writer, "status", first)
    _write_enum(writer, row.status)
    writer.write(b"}")


def _write_flow(writer: _CanonicalWriter, row: ReferenceFlowV1) -> None:
    writer.write(b"{")
    first = _field(writer, "coverage", True)
    _write_enum(writer, row.coverage)
    first = _field(writer, "destination_ref", first)
    _write_identity(writer, row.destination_ref)
    first = _field(writer, "evidence_class", first)
    _write_enum(writer, row.evidence_class)
    first = _field(writer, "flow_id", first)
    _write_identity(writer, row.flow_id)
    first = _field(writer, "flow_kind", first)
    _write_enum(writer, row.flow_kind)
    first = _field(writer, "native_scale", first)
    _write_identity(writer, row.native_scale)
    first = _field(writer, "origin_ref", first)
    _write_identity(writer, row.origin_ref)
    first = _field(writer, "payload_facets", first)
    _write_identity_array(writer, row.payload_facets)
    first = _field(writer, "provenance_refs", first)
    _write_identity_array(writer, row.provenance_refs)
    _field(writer, "status", first)
    _write_enum(writer, row.status)
    writer.write(b"}")


def _write_gap(writer: _CanonicalWriter, row: GapV1) -> None:
    writer.write(b"{")
    first = _field(writer, "gap_id", True)
    _write_identity(writer, row.gap_id)
    first = _field(writer, "provenance_refs", first)
    _write_identity_array(writer, row.provenance_refs)
    first = _field(writer, "reason_code", first)
    _write_enum(writer, row.reason_code)
    first = _field(writer, "requested_metric_or_relation", first)
    _write_identity(writer, row.requested_metric_or_relation)
    first = _field(writer, "required_producer_or_null", first)
    _write_nullable_string(writer, row.required_producer_or_null)
    _field(writer, "status", first)
    _write_enum(writer, row.status)
    writer.write(b"}")


def _write_provenance(writer: _CanonicalWriter, row: ProvenanceV1) -> None:
    writer.write(b"{")
    first = _field(writer, "artifact_digest", True)
    _write_string(writer, row.artifact_digest)
    first = _field(writer, "evidence_class", first)
    _write_enum(writer, row.evidence_class)
    first = _field(writer, "locator", first)
    _write_string(writer, row.locator)
    first = _field(writer, "provenance_id", first)
    _write_identity(writer, row.provenance_id)
    first = _field(writer, "transformation_digest_or_null", first)
    _write_nullable_string(writer, row.transformation_digest_or_null)
    _field(writer, "vintage", first)
    _write_string(writer, row.vintage)
    writer.write(b"}")


def _write_decision_surface(writer: _CanonicalWriter, row: DecisionSurfaceV1) -> None:
    writer.write(b"{")
    first = _field(writer, "action_refs", True)
    _write_identity_array(writer, row.action_refs, True)
    first = _field(writer, "archive_subject_refs", first)
    _write_identity_array(writer, row.archive_subject_refs, True)
    first = _field(writer, "question_id", first)
    _write_identity(writer, row.question_id)
    first = _field(writer, "receipt_refs", first)
    _write_identity_array(writer, row.receipt_refs, True)
    _field(writer, "signal_refs", first)
    _write_identity_array(writer, row.signal_refs, True)
    writer.write(b"}")


def _write_draft(writer: _CanonicalWriter, draft: RtdDossierDraftV1) -> None:
    writer.write(b"{")
    first = _field(writer, "actor", True)
    _write_nullable_identity(writer, draft.actor)
    first = _field(writer, "audience", first)
    _write_enum(writer, draft.audience)
    first = _field(writer, "decision_surface", first)
    _write_decision_surface(writer, draft.decision_surface)
    first = _field(writer, "definitions_digest", first)
    _write_string(writer, draft.definitions_digest)
    first = _field(writer, "durability", first)
    _write_enum(writer, draft.durability)
    first = _field(writer, "dyads", first)
    _write_array(writer, draft.dyads, _write_dyad, lambda row: _identity_key(row.relation_id))
    first = _field(writer, "facets", first)
    _write_array(writer, draft.facets, _write_facet, lambda row: _identity_key(row.facet_id))
    first = _field(writer, "flows", first)
    _write_array(writer, draft.flows, _write_flow, lambda row: _identity_key(row.flow_id))
    first = _field(writer, "focus", first)
    _write_identity_array(writer, draft.focus)
    first = _field(writer, "fog_policy_digest", first)
    _write_nullable_string(writer, draft.fog_policy_digest)
    first = _field(writer, "gaps", first)
    _write_array(writer, draft.gaps, _write_gap, lambda row: _identity_key(row.gap_id))
    first = _field(writer, "graph_state_hash", first)
    _write_string(writer, draft.graph_state_hash)
    first = _field(writer, "hyperedges", first)
    _write_array(
        writer, draft.hyperedges, _write_hyperedge, lambda row: _identity_key(row.hyperedge_id)
    )
    first = _field(writer, "knowledge_context_digest", first)
    _write_nullable_string(writer, draft.knowledge_context_digest)
    first = _field(writer, "nominal_world_hash", first)
    _write_string(writer, draft.nominal_world_hash)
    first = _field(writer, "projection_version", first)
    _write_u64(writer, draft.projection_version)
    first = _field(writer, "provenance", first)
    _write_array(
        writer, draft.provenance, _write_provenance, lambda row: _identity_key(row.provenance_id)
    )
    first = _field(writer, "reference_digests", first)
    _write_array(
        writer,
        draft.reference_digests,
        _write_reference,
        lambda row: _identity_key(row.reference_id),
    )
    first = _field(writer, "scale_memberships", first)
    _write_array(
        writer,
        draft.scale_memberships,
        _write_membership,
        lambda row: _identity_key(row.membership_id),
    )
    first = _field(writer, "schema", first)
    _write_string(writer, draft.schema_)
    first = _field(writer, "schema_version", first)
    _write_u64(writer, draft.schema_version)
    first = _field(writer, "template_digest", first)
    _write_string(writer, draft.template_digest)
    first = _field(writer, "verified_tick", first)
    _write_u64(writer, draft.verified_tick)
    writer.write(b"}")


def canonical_draft_bytes(draft: RtdDossierDraftV1) -> bytes:
    """Return the bounded canonical JSON bytes for one validated draft."""
    normalized = _normalize_negative_zero(draft)
    validate_draft(normalized)
    writer = _CanonicalWriter()
    _write_draft(writer, normalized)
    return writer.finish()


def projection_hash(draft: RtdDossierDraftV1) -> str:
    """Return the domain-separated SHA-256 of one canonical draft."""
    canonical = canonical_draft_bytes(draft)
    return hashlib.sha256(RTD_HASH_DOMAIN + b"\x00" + canonical).hexdigest()


def seal_draft(draft: RtdDossierDraftV1) -> RelationalTerritoryDossierV1:
    """Seal a complete valid draft only after canonical hashing succeeds."""
    normalized = _normalize_negative_zero(draft)
    digest = projection_hash(normalized)
    return RelationalTerritoryDossierV1(
        schema=normalized.schema_,
        schema_version=normalized.schema_version,
        projection_version=normalized.projection_version,
        audience=normalized.audience,
        durability=normalized.durability,
        verified_tick=normalized.verified_tick,
        graph_state_hash=normalized.graph_state_hash,
        nominal_world_hash=normalized.nominal_world_hash,
        reference_digests=normalized.reference_digests,
        definitions_digest=normalized.definitions_digest,
        template_digest=normalized.template_digest,
        fog_policy_digest=normalized.fog_policy_digest,
        knowledge_context_digest=normalized.knowledge_context_digest,
        actor=normalized.actor,
        focus=normalized.focus,
        scale_memberships=normalized.scale_memberships,
        facets=normalized.facets,
        dyads=normalized.dyads,
        hyperedges=normalized.hyperedges,
        flows=normalized.flows,
        gaps=normalized.gaps,
        provenance=normalized.provenance,
        decision_surface=normalized.decision_surface,
        projection_hash=digest,
    )
