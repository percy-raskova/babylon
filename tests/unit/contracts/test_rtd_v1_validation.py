"""Behavioral contracts for the Python RTD V1 semantic boundary."""

from __future__ import annotations

from typing import Any

import pytest

from babylon.contracts.relational_territory_dossier_v1 import (
    RtdValidationError,
    append_bounded,
    parse_draft,
    parse_draft_json,
    validate_draft,
)
from babylon.contracts.rtd_v1_generated import (
    AudienceV1,
    CoverageV1,
    DecisionSurfaceV1,
    DimensionCoordinateV1,
    DurabilityV1,
    DyadKindV1,
    DyadV1,
    EvidenceClassV1,
    FacetFamilyV1,
    FacetV1,
    FlowKindV1,
    GapReasonV1,
    GapV1,
    HyperedgeKindV1,
    HyperedgeV1,
    MembershipKindV1,
    ProvenanceV1,
    ReferenceDigestV1,
    ReferenceFlowV1,
    RtdCollectionKindV1,
    RtdDossierDraftV1,
    ScaleMembershipV1,
    StatusV1,
    TypedIdentityV1,
    ValueKindV1,
)

ZERO_DIGEST = "0" * 64
QCEW_DIGEST = "34c2bbb935f79b3c8076a97092b004b14cca120e8272b93c35b3ac9dc2721d13"
LODES_DIGEST = "d3745f8def09cd8c7a38e1870e6ec2c1853e210b777d8e8358cfce36665bd64d"
DUPLICATE_DRAFT_COUNT = 6


def identity(local_id: str, domain: str = "entity", authority: str = "test") -> TypedIdentityV1:
    return TypedIdentityV1(domain=domain, authority=authority, local_id=local_id)


def registry_identity(domain: str, local_id: str) -> TypedIdentityV1:
    return identity(local_id, domain, "babylon.rtd.v1")


def base_draft(**updates: object) -> RtdDossierDraftV1:
    values: dict[str, object] = {
        "schema": "babylon.relational-territory-dossier",
        "schema_version": 1,
        "projection_version": 1,
        "audience": AudienceV1.ADMIN_MATERIAL,
        "durability": DurabilityV1.IN_MEMORY,
        "verified_tick": 7,
        "graph_state_hash": ZERO_DIGEST,
        "nominal_world_hash": ZERO_DIGEST,
        "reference_digests": (),
        "definitions_digest": ZERO_DIGEST,
        "template_digest": ZERO_DIGEST,
        "fog_policy_digest": None,
        "knowledge_context_digest": None,
        "actor": None,
        "focus": (),
        "scale_memberships": (),
        "facets": (),
        "dyads": (),
        "hyperedges": (),
        "flows": (),
        "gaps": (),
        "provenance": (),
        "decision_surface": DecisionSurfaceV1(
            question_id=identity("administrative-question", "question"),
            signal_refs=(),
            action_refs=(),
            receipt_refs=(),
            archive_subject_refs=(),
        ),
    }
    values.update(updates)
    return RtdDossierDraftV1.model_validate(values)


def reference(reference_id: TypedIdentityV1, digest: str) -> ReferenceDigestV1:
    return ReferenceDigestV1(
        reference_id=reference_id,
        sha256_hex=digest,
        artifact_schema_id_or_null=None,
        vintage="2023",
        evidence_class=EvidenceClassV1.Observed,
    )


def county_facet(**updates: object) -> FacetV1:
    values: dict[str, object] = {
        "facet_id": identity("facet-1", "facet"),
        "family": FacetFamilyV1.PRODUCTION_CIRCULATION,
        "subject_ref": identity("26163", "county", "census"),
        "metric_id": registry_identity("metric", "production/qcew-county-employment"),
        "unit_id": registry_identity("unit", "jobs"),
        "native_scale": registry_identity("native-scale", "county-ownership-year"),
        "coordinates": (
            DimensionCoordinateV1(
                dimension_ref=registry_identity("dimension", "county"),
                member_ref=identity("26163", "county", "census"),
            ),
            DimensionCoordinateV1(
                dimension_ref=registry_identity("dimension", "ownership"),
                member_ref=identity("0", "ownership", "bls"),
            ),
        ),
        "vintage": "2023",
        "status": StatusV1.PRESENT,
        "value_kind": ValueKindV1.UINT64_BITS,
        "value_bits_or_null": "0000000000000000",
        "coverage": CoverageV1.COMPLETE,
        "evidence_class": EvidenceClassV1.Observed,
        "provenance_refs": (),
    }
    values.update(updates)
    return FacetV1.model_validate(values)


def draft_with_facet(facet: FacetV1 | None = None) -> RtdDossierDraftV1:
    reference_id = identity("fact_qcew_county_rollup", "reference-artifact", "babylon.data.v7")
    return base_draft(
        facets=(facet or county_facet(),),
        reference_digests=(reference(reference_id, QCEW_DIGEST),),
    )


def lodes_facet(flow_id: TypedIdentityV1, **updates: object) -> FacetV1:
    values: dict[str, object] = {
        "facet_id": identity("lodes-facet", "facet"),
        "family": FacetFamilyV1.PRODUCTION_CIRCULATION,
        "subject_ref": flow_id,
        "metric_id": registry_identity("metric", "circulation/lodes-county-commuter-total-jobs"),
        "unit_id": registry_identity("unit", "jobs"),
        "native_scale": registry_identity("native-scale", "home-county-work-county-year"),
        "coordinates": (
            DimensionCoordinateV1(
                dimension_ref=registry_identity("dimension", "home-county"),
                member_ref=identity("26163", "county", "census"),
            ),
            DimensionCoordinateV1(
                dimension_ref=registry_identity("dimension", "work-county"),
                member_ref=identity("26125", "county", "census"),
            ),
        ),
        "vintage": "2022",
        "status": StatusV1.PRESENT,
        "value_kind": ValueKindV1.UINT64_BITS,
        "value_bits_or_null": "0000000000000001",
        "coverage": CoverageV1.COMPLETE,
        "evidence_class": EvidenceClassV1.Derived,
        "provenance_refs": (),
    }
    values.update(updates)
    return FacetV1.model_validate(values)


def commuter_flow(
    flow_id: TypedIdentityV1, payload: tuple[TypedIdentityV1, ...]
) -> ReferenceFlowV1:
    return ReferenceFlowV1(
        flow_id=flow_id,
        flow_kind=FlowKindV1.COMMUTER_JOBS,
        origin_ref=identity("26163", "county", "census"),
        destination_ref=identity("26125", "county", "census"),
        payload_facets=payload,
        native_scale=registry_identity("native-scale", "home-county-work-county-year"),
        status=StatusV1.PRESENT,
        coverage=CoverageV1.COMPLETE,
        evidence_class=EvidenceClassV1.Derived,
        provenance_refs=(),
    )


def dyad(kind: DyadKindV1) -> DyadV1:
    return DyadV1(
        relation_id=identity(f"dyad-{kind.value.lower()}", "dyad"),
        relation_kind=kind,
        from_ref=identity("actor", "organization"),
        to_ref=identity("node", "county"),
        native_scale=registry_identity("native-scale", "actor-node-verified-tick"),
        status=StatusV1.PRESENT,
        coverage=CoverageV1.COMPLETE,
        payload_facets=(),
        evidence_class=EvidenceClassV1.Derived,
        provenance_refs=(),
    )


def assert_error(code: str, draft: RtdDossierDraftV1) -> None:
    with pytest.raises(RtdValidationError) as raised:
        validate_draft(draft)
    assert raised.value.code == code
    assert isinstance(raised.value.path, tuple)


def test_empty_administrative_draft_is_valid() -> None:
    assert validate_draft(base_draft()) is None


def test_mapping_and_json_shape_errors_are_stable() -> None:
    payload = base_draft().model_dump(by_alias=True, mode="json")
    payload["unexpected"] = True
    with pytest.raises(RtdValidationError) as mapping_error:
        parse_draft(payload)
    assert (mapping_error.value.code, mapping_error.value.path) == (
        "RTD_UNKNOWN_FIELD",
        ("unexpected",),
    )
    payload.pop("unexpected")
    payload["audience"] = "SECRET"
    with pytest.raises(RtdValidationError, match="RTD_ENUM"):
        parse_draft(payload)
    with pytest.raises(RtdValidationError, match="RTD_JSON"):
        parse_draft_json(b'{"schema":')
    with pytest.raises(RtdValidationError, match="RTD_JSON"):
        parse_draft_json(b"{}{}")
    with pytest.raises(RtdValidationError, match="RTD_JSON_DEPTH"):
        parse_draft_json((b"[" * 33) + (b"]" * 33))
    raw = base_draft().model_dump_json(by_alias=True)[:-1].encode()
    with pytest.raises(RtdValidationError) as json_error:
        parse_draft_json(raw + b',"unexpected":true}')
    assert json_error.value.path == ("unexpected",)


def test_json_duplicate_object_key_refuses() -> None:
    raw = base_draft().model_dump_json(by_alias=True)[:-1].encode()
    with pytest.raises(RtdValidationError, match="RTD_DUPLICATE_KEY"):
        parse_draft_json(raw + b',"schema":"babylon.relational-territory-dossier"}')


@pytest.mark.parametrize(
    "kind,limit",
    (
        (RtdCollectionKindV1.FOCUS, 64),
        (RtdCollectionKindV1.REFERENCE_DIGESTS, 4096),
        (RtdCollectionKindV1.SCALE_MEMBERSHIPS, 65535),
        (RtdCollectionKindV1.FACETS, 65535),
        (RtdCollectionKindV1.DYADS, 65535),
        (RtdCollectionKindV1.HYPEREDGES, 65535),
        (RtdCollectionKindV1.FLOWS, 65535),
        (RtdCollectionKindV1.GAPS, 65535),
        (RtdCollectionKindV1.PROVENANCE, 65535),
        (RtdCollectionKindV1.COORDINATES, 32),
        (RtdCollectionKindV1.MEMBER_REFS, 1024),
        (RtdCollectionKindV1.PAYLOAD_FACETS, 256),
        (RtdCollectionKindV1.DISPLAY_REFS, 256),
        (RtdCollectionKindV1.PROVENANCE_REFS, 8192),
    ),
)
def test_every_closed_collection_refuses_limit_plus_one(
    kind: RtdCollectionKindV1, limit: int
) -> None:
    item = identity("bounded")
    original = (item,) * limit
    before = original
    with pytest.raises(RtdValidationError, match="RTD_LIMIT_EXCEEDED"):
        append_bounded(original, item, kind, kind.value.lower())
    assert original == before


def test_append_requires_tuple_input() -> None:
    with pytest.raises(RtdValidationError, match="RTD_JSON"):
        append_bounded([], identity("bad"), RtdCollectionKindV1.FOCUS, "focus")  # type: ignore[arg-type]


def test_gap_limit_refusal_preserves_original_bytes() -> None:
    gap = GapV1(
        gap_id=identity("atomic-gap", "gap"),
        requested_metric_or_relation=identity("missing", "metric"),
        status=StatusV1.UNKNOWN,
        reason_code=GapReasonV1.MISSING_GOVERNED_PRODUCER,
        required_producer_or_null="PER-28",
        provenance_refs=(),
    )
    original = (gap,) * 65535
    row_bytes = gap.model_dump_json().encode("utf-8")
    before = b"[" + row_bytes + (b"," + row_bytes) * (len(original) - 1) + b"]"
    with pytest.raises(RtdValidationError, match="RTD_LIMIT_EXCEEDED"):
        append_bounded(original, gap, RtdCollectionKindV1.GAPS, "gaps")
    after = b"[" + row_bytes + (b"," + row_bytes) * (len(original) - 1) + b"]"
    assert after == before


@pytest.mark.parametrize(
    "bad_identity,code",
    (
        (identity("", "county", "census"), "RTD_IDENTITY"),
        (identity("e\N{COMBINING ACUTE ACCENT}"), "RTD_NON_NFC"),
        (identity("x" * 257), "RTD_IDENTITY"),
    ),
)
def test_identity_and_digest_contracts(bad_identity: TypedIdentityV1, code: str) -> None:
    assert_error(code, base_draft(focus=(bad_identity,)))
    assert_error("RTD_DIGEST", base_draft(graph_state_hash="A" * 64))
    assert_error("RTD_DIGEST", base_draft(graph_state_hash="0" * 63))


def test_duplicate_and_dangling_references_refuse() -> None:
    duplicate = identity("duplicate")
    assert_error("RTD_DUPLICATE_KEY", base_draft(focus=(duplicate, duplicate)))
    facet = county_facet(provenance_refs=(identity("missing", "provenance"),))
    assert_error("RTD_DANGLING_REF", draft_with_facet(facet))


def test_status_bits_and_negative_zero_contracts() -> None:
    assert validate_draft(draft_with_facet()) is None
    assert_error(
        "RTD_STATUS_VALUE",
        draft_with_facet(county_facet(status=StatusV1.UNKNOWN)),
    )
    assert_error("RTD_STATUS_VALUE", draft_with_facet(county_facet(value_bits_or_null=None)))
    float_facet = county_facet(
        metric_id=registry_identity("metric", "production/qcew-county-total-wages-usd"),
        unit_id=registry_identity("unit", "usd-current"),
        value_kind=ValueKindV1.FLOAT64_BITS,
        value_bits_or_null="7ff0000000000000",
    )
    assert_error("RTD_STATUS_VALUE", draft_with_facet(float_facet))
    payload = draft_with_facet(
        float_facet.model_copy(update={"value_bits_or_null": "8000000000000000"})
    ).model_dump(by_alias=True, mode="json")
    assert parse_draft(payload).facets[0].value_bits_or_null == "0000000000000000"


def test_uint64_high_bit_is_not_normalized_as_float_negative_zero() -> None:
    payload = draft_with_facet(county_facet(value_bits_or_null="8000000000000000")).model_dump(
        by_alias=True, mode="json"
    )
    parsed = parse_draft(payload)
    assert parsed.facets[0].value_kind is ValueKindV1.UINT64_BITS
    assert parsed.facets[0].value_bits_or_null == "8000000000000000"


@pytest.mark.parametrize(
    "updates",
    (
        {"metric_id": identity("unknown", "metric")},
        {"unit_id": registry_identity("unit", "persons")},
        {"native_scale": registry_identity("native-scale", "county-source-time-race")},
        {"evidence_class": EvidenceClassV1.Designed},
        {"coordinates": county_facet().coordinates[:1]},
    ),
)
def test_metric_and_native_grain_mutations_refuse(updates: dict[str, object]) -> None:
    assert_error("RTD_NATIVE_GRAIN", draft_with_facet(county_facet(**updates)))


def test_duplicate_and_extra_coordinates_refuse() -> None:
    facet = county_facet()
    duplicate = facet.model_copy(update={"coordinates": (facet.coordinates[0],) * 2})
    assert_error("RTD_DUPLICATE_KEY", draft_with_facet(duplicate))
    extra = DimensionCoordinateV1(
        dimension_ref=registry_identity("dimension", "race"),
        member_ref=identity("all", "race"),
    )
    assert_error(
        "RTD_NATIVE_GRAIN",
        draft_with_facet(facet.model_copy(update={"coordinates": facet.coordinates + (extra,)})),
    )


def test_required_reference_digest_must_exist_and_match() -> None:
    assert_error("RTD_DIGEST", base_draft(facets=(county_facet(),)))
    reference_id = identity("fact_qcew_county_rollup", "reference-artifact", "babylon.data.v7")
    assert_error(
        "RTD_DIGEST",
        base_draft(
            facets=(county_facet(),),
            reference_digests=(reference(reference_id, ZERO_DIGEST),),
        ),
    )


@pytest.mark.parametrize(
    "kind", (DyadKindV1.PRESENCE, DyadKindV1.MEMBERSHIP, DyadKindV1.SOLIDARITY)
)
def test_each_typed_dyad_binding_is_valid(kind: DyadKindV1) -> None:
    assert validate_draft(base_draft(dyads=(dyad(kind),))) is None


def test_empty_relation_bindings_and_commuter_binding_are_valid() -> None:
    command = dyad(DyadKindV1.COMMAND).model_copy(
        update={"native_scale": identity("command", "native-scale")}
    )
    border = commuter_flow(identity("border", "flow"), ()).model_copy(
        update={
            "flow_kind": FlowKindV1.BORDER_SYNTHESIS,
            "destination_ref": identity("canada", "external", "iso3166-1"),
            "native_scale": identity("border", "native-scale"),
        }
    )
    assert validate_draft(base_draft(dyads=(command,), flows=(border,))) is None
    flow_id = identity("flow-1", "flow")
    facet = lodes_facet(flow_id)
    flow = commuter_flow(flow_id, (facet.facet_id,))
    reference_id = identity("fact_lodes_commuter_flow", "reference-artifact", "babylon.data.v7")
    assert (
        validate_draft(
            base_draft(
                facets=(facet,),
                flows=(flow,),
                reference_digests=(reference(reference_id, LODES_DIGEST),),
            )
        )
        is None
    )


def test_parser_refuses_overlimit_before_normalization_can_truncate() -> None:
    facet = county_facet()
    payload = base_draft().model_dump(by_alias=True, mode="python")
    payload["facets"] = [facet] * 65536
    with pytest.raises(RtdValidationError, match="RTD_LIMIT_EXCEEDED"):
        parse_draft(payload)


def test_validator_requires_nested_generated_tuples() -> None:
    facet = county_facet().model_copy(update={"coordinates": list(county_facet().coordinates)})
    with pytest.raises(RtdValidationError, match="RTD_JSON"):
        validate_draft(draft_with_facet(facet))


def test_relation_binding_payload_mutations_refuse() -> None:
    flow_id = identity("flow-1", "flow")
    facet = lodes_facet(flow_id)
    reference_id = identity("fact_lodes_commuter_flow", "reference-artifact", "babylon.data.v7")
    references = (reference(reference_id, LODES_DIGEST),)
    assert_error("RTD_NATIVE_GRAIN", base_draft(flows=(commuter_flow(flow_id, ()),)))
    assert_error(
        "RTD_DUPLICATE_KEY",
        base_draft(
            facets=(facet,),
            flows=(commuter_flow(flow_id, (facet.facet_id, facet.facet_id)),),
        ),
    )
    assert_error(
        "RTD_NATIVE_GRAIN",
        base_draft(
            facets=(facet.model_copy(update={"subject_ref": identity("other", "flow")}),),
            flows=(commuter_flow(flow_id, (facet.facet_id,)),),
            reference_digests=references,
        ),
    )
    typed = dyad(DyadKindV1.PRESENCE)
    assert_error(
        "RTD_NATIVE_GRAIN",
        base_draft(
            dyads=(typed.model_copy(update={"native_scale": identity("wrong", "native-scale")}),)
        ),
    )
    assert_error(
        "RTD_DANGLING_REF",
        base_draft(
            dyads=(typed.model_copy(update={"payload_facets": (identity("missing", "facet"),)}),)
        ),
    )


def test_commuter_two_shared_wrong_metric_and_facet_representation_refuse() -> None:
    first_flow_id = identity("flow-1", "flow")
    second_flow_id = identity("flow-2", "flow")
    first = lodes_facet(first_flow_id)
    second = lodes_facet(first_flow_id, facet_id=identity("lodes-facet-2", "facet"))
    lodes_reference = identity("fact_lodes_commuter_flow", "reference-artifact", "babylon.data.v7")
    qcew_reference = identity("fact_qcew_county_rollup", "reference-artifact", "babylon.data.v7")
    assert_error(
        "RTD_NATIVE_GRAIN",
        base_draft(
            facets=(first, second),
            flows=(commuter_flow(first_flow_id, (first.facet_id, second.facet_id)),),
            reference_digests=(reference(lodes_reference, LODES_DIGEST),),
        ),
    )
    assert_error(
        "RTD_DUPLICATE_KEY",
        base_draft(
            facets=(first,),
            flows=(
                commuter_flow(first_flow_id, (first.facet_id,)),
                commuter_flow(second_flow_id, (first.facet_id,)),
            ),
            reference_digests=(reference(lodes_reference, LODES_DIGEST),),
        ),
    )
    facet_metric = county_facet(
        facet_id=identity("facet-payload", "facet"), subject_ref=first_flow_id
    )
    assert_error(
        "RTD_NATIVE_GRAIN",
        base_draft(
            facets=(facet_metric,),
            flows=(commuter_flow(first_flow_id, (facet_metric.facet_id,)),),
            reference_digests=(reference(qcew_reference, QCEW_DIGEST),),
        ),
    )


def test_nonempty_empty_bindings_and_wrong_dyad_evidence_refuse() -> None:
    facet = county_facet()
    reference_id = identity("fact_qcew_county_rollup", "reference-artifact", "babylon.data.v7")
    command = dyad(DyadKindV1.COMMAND).model_copy(update={"payload_facets": (facet.facet_id,)})
    border = commuter_flow(identity("border", "flow"), (facet.facet_id,)).model_copy(
        update={"flow_kind": FlowKindV1.BORDER_SYNTHESIS}
    )
    wrong_evidence = dyad(DyadKindV1.SOLIDARITY).model_copy(
        update={"evidence_class": EvidenceClassV1.Observed}
    )
    refs = (reference(reference_id, QCEW_DIGEST),)
    assert_error(
        "RTD_NATIVE_GRAIN",
        base_draft(facets=(facet,), dyads=(command,), reference_digests=refs),
    )
    assert_error(
        "RTD_NATIVE_GRAIN",
        base_draft(facets=(facet,), flows=(border,), reference_digests=refs),
    )
    assert_error("RTD_NATIVE_GRAIN", base_draft(dyads=(wrong_evidence,)))


def test_h3_msa_canada_downscale_and_hyperedge_boundaries() -> None:
    assert_error(
        "RTD_H3_BEFORE_PER21",
        base_draft(focus=(identity("8928308280fffff", "h3"),)),
    )
    msa = ScaleMembershipV1(
        membership_id=identity("msa", "membership"),
        member_ref=identity("26163", "county", "census"),
        scale_ref=identity("19820", "msa", "omb"),
        membership_kind=MembershipKindV1.METROPOLITAN,
        status=StatusV1.PRESENT,
        weight_status=StatusV1.ABSENT,
        weight_bits_or_null=None,
        coverage=CoverageV1.COMPLETE,
        evidence_class=EvidenceClassV1.Observed,
        provenance_refs=(),
    )
    assert_error("RTD_MSA_EVIDENCE", base_draft(scale_memberships=(msa,)))
    assert_error("RTD_MSA_EVIDENCE", base_draft(focus=(identity("19820"),)))
    assert_error(
        "RTD_CANADA_CONTROL",
        base_draft(focus=(identity("windsor", "county", "canada"),)),
    )
    overlap = msa.model_copy(
        update={
            "membership_kind": MembershipKindV1.WEIGHTED_OVERLAP,
            "scale_ref": identity("county", "scale"),
        }
    )
    assert_error("RTD_UNSUPPORTED_DOWNSCALE", base_draft(scale_memberships=(overlap,)))
    flattened = dyad(DyadKindV1.COMMAND).model_copy(
        update={"relation_id": identity("flattened", "hyperedge")}
    )
    assert_error("RTD_FORBIDDEN_REDUCTION", base_draft(dyads=(flattened,)))
    edge = HyperedgeV1(
        hyperedge_id=identity("public", "hyperedge"),
        hyperedge_kind=HyperedgeKindV1.PUBLIC_RELATION,
        member_refs=(identity("a"), identity("b"), identity("c")),
        native_scale=identity("public", "native-scale"),
        status=StatusV1.PRESENT,
        coverage=CoverageV1.COMPLETE,
        payload_facets=(),
        evidence_class=EvidenceClassV1.Derived,
        provenance_refs=(),
    )
    assert validate_draft(base_draft(hyperedges=(edge,))) is None


def test_h3_gap_requires_exact_pending_contract_state() -> None:
    metric = registry_identity("metric", "reproduction/h3-population-persons")
    gap = GapV1(
        gap_id=identity("h3-gap", "gap"),
        requested_metric_or_relation=metric,
        status=StatusV1.NOT_COMPUTED,
        reason_code=GapReasonV1.IDENTITY_CONTRACT_PENDING,
        required_producer_or_null="PER-21",
        provenance_refs=(),
    )
    assert validate_draft(base_draft(gaps=(gap,))) is None
    wrong_reason = gap.model_copy(update={"reason_code": GapReasonV1.MISSING_GOVERNED_PRODUCER})
    assert_error("RTD_H3_BEFORE_PER21", base_draft(gaps=(wrong_reason,)))


def test_h3_gap_classification_uses_the_complete_typed_identity() -> None:
    unrelated = GapV1(
        gap_id=identity("unrelated-gap", "gap"),
        requested_metric_or_relation=identity(
            "reproduction/h3-population-persons", "unrelated-domain", "other-authority"
        ),
        status=StatusV1.UNKNOWN,
        reason_code=GapReasonV1.MISSING_GOVERNED_PRODUCER,
        required_producer_or_null="PER-28",
        provenance_refs=(),
    )
    assert validate_draft(base_draft(gaps=(unrelated,))) is None

    actual_h3 = unrelated.model_copy(
        update={
            "requested_metric_or_relation": registry_identity(
                "metric", "reproduction/h3-population-persons"
            )
        }
    )
    assert_error("RTD_H3_BEFORE_PER21", base_draft(gaps=(actual_h3,)))


def test_canadian_canonical_lodes_flow_refuses() -> None:
    flow_id = identity("canada-flow", "flow")
    flow = commuter_flow(flow_id, (identity("lodes-facet", "facet"),)).model_copy(
        update={"destination_ref": identity("canada", "external", "iso3166-1")}
    )
    assert_error("RTD_CANADA_CONTROL", base_draft(flows=(flow,)))


@pytest.mark.parametrize(
    "updates",
    (
        {"audience": AudienceV1.PLAYER_KNOWLEDGE},
        {"durability": DurabilityV1.COMMITTED},
        {"fog_policy_digest": ZERO_DIGEST},
        {"knowledge_context_digest": ZERO_DIGEST},
        {"actor": identity("player", "organization")},
    ),
)
def test_administrative_boundary_refuses_context(updates: dict[str, Any]) -> None:
    assert_error("RTD_FORBIDDEN_REDUCTION", base_draft(**updates))


@pytest.mark.parametrize("field", ("action_refs", "receipt_refs", "archive_subject_refs"))
def test_administrative_surface_refuses_gameplay_refs(field: str) -> None:
    surface = base_draft().decision_surface.model_copy(update={field: (identity("forbidden"),)})
    assert_error("RTD_FORBIDDEN_REDUCTION", base_draft(decision_surface=surface))


def test_dangling_signal_reference_refuses() -> None:
    surface = base_draft().decision_surface.model_copy(
        update={"signal_refs": (identity("missing", "facet"),)}
    )
    assert_error("RTD_DANGLING_REF", base_draft(decision_surface=surface))


def test_duplicate_keys_cover_top_level_and_nested_set_families() -> None:
    provenance = ProvenanceV1(
        provenance_id=identity("p", "provenance"),
        artifact_digest=ZERO_DIGEST,
        locator="row=1",
        vintage="2023",
        evidence_class=EvidenceClassV1.Observed,
        transformation_digest_or_null=None,
    )
    membership = ScaleMembershipV1(
        membership_id=identity("membership", "membership"),
        member_ref=identity("26163", "county", "census"),
        scale_ref=identity("26", "state", "census"),
        membership_kind=MembershipKindV1.ADMINISTRATIVE,
        status=StatusV1.PRESENT,
        weight_status=StatusV1.ABSENT,
        weight_bits_or_null=None,
        coverage=CoverageV1.COMPLETE,
        evidence_class=EvidenceClassV1.Observed,
        provenance_refs=(),
    )
    gap = GapV1(
        gap_id=identity("gap", "gap"),
        requested_metric_or_relation=identity("missing", "metric"),
        status=StatusV1.UNKNOWN,
        reason_code=GapReasonV1.MISSING_GOVERNED_PRODUCER,
        required_producer_or_null="PER-28",
        provenance_refs=(),
    )
    top_level_duplicates = (
        base_draft(reference_digests=(reference(identity("r"), ZERO_DIGEST),) * 2),
        base_draft(scale_memberships=(membership,) * 2),
        base_draft(facets=(county_facet(),) * 2),
        base_draft(dyads=(dyad(DyadKindV1.COMMAND),) * 2),
        base_draft(gaps=(gap,) * 2),
        base_draft(provenance=(provenance,) * 2),
    )
    for draft_index in range(DUPLICATE_DRAFT_COUNT):
        assert_error("RTD_DUPLICATE_KEY", top_level_duplicates[draft_index])


def test_validation_failure_returns_no_artifact() -> None:
    result: object | None = None
    with pytest.raises(RtdValidationError, match="RTD_SCHEMA_VERSION"):
        result = validate_draft(base_draft(schema_version=2))
    assert result is None
