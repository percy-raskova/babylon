"""Behavioral contract for the closed RTD V1 schema generator."""

from __future__ import annotations

import copy
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import pytest
import tools.generate_rtd_v1_types as generator
import yaml
from pydantic import ValidationError
from tools.generate_rtd_v1_types import (
    CONTRACT_LIMIT_ERROR,
    CONTRACT_SCHEMA_ERROR,
    ContractLoadError,
    ExpandedMetricSpec,
    FieldSpec,
    RecordSpec,
    RelationBindingSpec,
    TypedIdentitySpec,
    load_contract,
    main,
    render_python,
    render_rust,
)

from babylon.contracts.rtd_v1_generated import RtdDossierDraftV1

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]
CONTRACT_PATH = REPO_ROOT / "contracts" / "relational_territory_dossier_v1.yaml"
GENERATOR_PATH = REPO_ROOT / "tools" / "generate_rtd_v1_types.py"
REQUIRED_REGISTRY_COUNT = 6
EXPECTED_METRIC_COUNT = 18
EXPECTED_UNIT_COUNT = 8
EXPECTED_COORDINATE_COUNT = 13
EXPECTED_SCALE_COUNT = 9
EXPECTED_ARTIFACT_COUNT = 10
MAX_EXPECTED_METRIC_COORDINATES = 4
MAX_METRIC_COORDINATES = 32
MAX_METRIC_EVIDENCE_CLASSES = 4
MAX_EXPECTED_RECORD_FIELDS = 64
EXTRA_RECORD_DECLARATIONS = 20
EXTRA_ENUM_DECLARATIONS = 49
EXTRA_FIELD_DECLARATIONS = 62
EXTRA_ENUM_MEMBERS = 255
EXTRA_LIMIT_ROWS = 493
EXTRA_REGISTRY_ROWS = 495
REQUIRED_OPTION_RECORD_COUNT = 7
MAX_REQUIRED_OPTIONS_PER_RECORD = 3

EXPECTED_RECORDS = {
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
}

EXPECTED_ENUMS = {
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

EXPECTED_LIMITS = {
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

EXPECTED_SCALAR_TYPES = {
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

EXPECTED_ERRORS = (
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


def _field_spec(
    name: str,
    type_name: str,
    *,
    nullable: bool = False,
    bound: str | None = None,
    sort_key: str | None = None,
) -> FieldSpec:
    return FieldSpec(name, type_name, nullable, bound, sort_key)


EXPECTED_RECORD_SPECS = (
    RecordSpec(
        "TypedIdentityV1",
        (
            _field_spec("domain", "string", bound="max_identity_component_bytes"),
            _field_spec("authority", "string", bound="max_identity_component_bytes"),
            _field_spec("local_id", "string", bound="max_identity_component_bytes"),
        ),
    ),
    RecordSpec(
        "ReferenceDigestV1",
        (
            _field_spec("reference_id", "identity"),
            _field_spec("sha256_hex", "digest_hex"),
            _field_spec("artifact_schema_id_or_null", "identity", nullable=True),
            _field_spec("vintage", "vintage", bound="max_vintage_bytes"),
            _field_spec("evidence_class", "EvidenceClassV1"),
        ),
    ),
    RecordSpec(
        "DimensionCoordinateV1",
        (
            _field_spec("dimension_ref", "identity"),
            _field_spec("member_ref", "identity"),
        ),
    ),
    RecordSpec(
        "ScaleMembershipV1",
        (
            _field_spec("membership_id", "identity"),
            _field_spec("member_ref", "identity"),
            _field_spec("scale_ref", "identity"),
            _field_spec("membership_kind", "MembershipKindV1"),
            _field_spec("status", "StatusV1"),
            _field_spec("weight_status", "StatusV1"),
            _field_spec("weight_bits_or_null", "bits64_hex", nullable=True),
            _field_spec("coverage", "CoverageV1"),
            _field_spec("evidence_class", "EvidenceClassV1"),
            _field_spec(
                "provenance_refs",
                "list[identity]",
                bound="max_provenance_refs",
                sort_key="identity",
            ),
        ),
    ),
    RecordSpec(
        "FacetV1",
        (
            _field_spec("facet_id", "identity"),
            _field_spec("family", "FacetFamilyV1"),
            _field_spec("subject_ref", "identity"),
            _field_spec("metric_id", "identity"),
            _field_spec("unit_id", "identity"),
            _field_spec("native_scale", "identity"),
            _field_spec(
                "coordinates",
                "list[DimensionCoordinateV1]",
                bound="max_coordinates",
                sort_key="dimension_ref",
            ),
            _field_spec("vintage", "vintage", bound="max_vintage_bytes"),
            _field_spec("status", "StatusV1"),
            _field_spec("value_kind", "ValueKindV1"),
            _field_spec("value_bits_or_null", "bits64_hex", nullable=True),
            _field_spec("coverage", "CoverageV1"),
            _field_spec("evidence_class", "EvidenceClassV1"),
            _field_spec(
                "provenance_refs",
                "list[identity]",
                bound="max_provenance_refs",
                sort_key="identity",
            ),
        ),
    ),
    RecordSpec(
        "DyadV1",
        (
            _field_spec("relation_id", "identity"),
            _field_spec("relation_kind", "DyadKindV1"),
            _field_spec("from_ref", "identity"),
            _field_spec("to_ref", "identity"),
            _field_spec("native_scale", "identity"),
            _field_spec("status", "StatusV1"),
            _field_spec("coverage", "CoverageV1"),
            _field_spec(
                "payload_facets",
                "list[identity]",
                bound="max_payload_facets",
                sort_key="identity",
            ),
            _field_spec("evidence_class", "EvidenceClassV1"),
            _field_spec(
                "provenance_refs",
                "list[identity]",
                bound="max_provenance_refs",
                sort_key="identity",
            ),
        ),
    ),
    RecordSpec(
        "HyperedgeV1",
        (
            _field_spec("hyperedge_id", "identity"),
            _field_spec("hyperedge_kind", "HyperedgeKindV1"),
            _field_spec(
                "member_refs",
                "list[identity]",
                bound="max_hyperedge_members",
                sort_key="identity",
            ),
            _field_spec("native_scale", "identity"),
            _field_spec("status", "StatusV1"),
            _field_spec("coverage", "CoverageV1"),
            _field_spec(
                "payload_facets",
                "list[identity]",
                bound="max_payload_facets",
                sort_key="identity",
            ),
            _field_spec("evidence_class", "EvidenceClassV1"),
            _field_spec(
                "provenance_refs",
                "list[identity]",
                bound="max_provenance_refs",
                sort_key="identity",
            ),
        ),
    ),
    RecordSpec(
        "ReferenceFlowV1",
        (
            _field_spec("flow_id", "identity"),
            _field_spec("flow_kind", "FlowKindV1"),
            _field_spec("origin_ref", "identity"),
            _field_spec("destination_ref", "identity"),
            _field_spec(
                "payload_facets",
                "list[identity]",
                bound="max_payload_facets",
                sort_key="identity",
            ),
            _field_spec("native_scale", "identity"),
            _field_spec("status", "StatusV1"),
            _field_spec("coverage", "CoverageV1"),
            _field_spec("evidence_class", "EvidenceClassV1"),
            _field_spec(
                "provenance_refs",
                "list[identity]",
                bound="max_provenance_refs",
                sort_key="identity",
            ),
        ),
    ),
    RecordSpec(
        "GapV1",
        (
            _field_spec("gap_id", "identity"),
            _field_spec("requested_metric_or_relation", "identity"),
            _field_spec("status", "StatusV1"),
            _field_spec("reason_code", "GapReasonV1"),
            _field_spec(
                "required_producer_or_null",
                "producer_issue",
                nullable=True,
                bound="max_required_producer_bytes",
            ),
            _field_spec(
                "provenance_refs",
                "list[identity]",
                bound="max_provenance_refs",
                sort_key="identity",
            ),
        ),
    ),
    RecordSpec(
        "ProvenanceV1",
        (
            _field_spec("provenance_id", "identity"),
            _field_spec("artifact_digest", "digest_hex"),
            _field_spec("locator", "string", bound="max_provenance_locator_bytes"),
            _field_spec("vintage", "vintage", bound="max_vintage_bytes"),
            _field_spec("evidence_class", "EvidenceClassV1"),
            _field_spec("transformation_digest_or_null", "digest_hex", nullable=True),
        ),
    ),
    RecordSpec(
        "DecisionSurfaceV1",
        (
            _field_spec("question_id", "identity"),
            _field_spec(
                "signal_refs",
                "list[identity]",
                bound="max_decision_surface_refs",
                sort_key="input_order",
            ),
            _field_spec(
                "action_refs",
                "list[identity]",
                bound="max_decision_surface_refs",
                sort_key="input_order",
            ),
            _field_spec(
                "receipt_refs",
                "list[identity]",
                bound="max_decision_surface_refs",
                sort_key="input_order",
            ),
            _field_spec(
                "archive_subject_refs",
                "list[identity]",
                bound="max_decision_surface_refs",
                sort_key="input_order",
            ),
        ),
    ),
    RecordSpec(
        "RtdDossierDraftV1",
        (
            _field_spec("schema", "string"),
            _field_spec("schema_version", "u16"),
            _field_spec("projection_version", "u16"),
            _field_spec("audience", "AudienceV1"),
            _field_spec("durability", "DurabilityV1"),
            _field_spec("verified_tick", "u64"),
            _field_spec("graph_state_hash", "digest_hex"),
            _field_spec("nominal_world_hash", "digest_hex"),
            _field_spec(
                "reference_digests",
                "list[ReferenceDigestV1]",
                bound="max_reference_digests",
                sort_key="reference_id",
            ),
            _field_spec("definitions_digest", "digest_hex"),
            _field_spec("template_digest", "digest_hex"),
            _field_spec("fog_policy_digest", "digest_hex", nullable=True),
            _field_spec("knowledge_context_digest", "digest_hex", nullable=True),
            _field_spec("actor", "identity", nullable=True),
            _field_spec("focus", "list[identity]", bound="max_focus", sort_key="identity"),
            _field_spec(
                "scale_memberships",
                "list[ScaleMembershipV1]",
                bound="max_scale_memberships",
                sort_key="membership_id",
            ),
            _field_spec("facets", "list[FacetV1]", bound="max_facets", sort_key="facet_id"),
            _field_spec("dyads", "list[DyadV1]", bound="max_dyads", sort_key="relation_id"),
            _field_spec(
                "hyperedges",
                "list[HyperedgeV1]",
                bound="max_hyperedges",
                sort_key="hyperedge_id",
            ),
            _field_spec("flows", "list[ReferenceFlowV1]", bound="max_flows", sort_key="flow_id"),
            _field_spec("gaps", "list[GapV1]", bound="max_gaps", sort_key="gap_id"),
            _field_spec(
                "provenance",
                "list[ProvenanceV1]",
                bound="max_provenance",
                sort_key="provenance_id",
            ),
            _field_spec("decision_surface", "DecisionSurfaceV1"),
        ),
    ),
    RecordSpec(
        "RelationalTerritoryDossierV1",
        (
            _field_spec("schema", "string"),
            _field_spec("schema_version", "u16"),
            _field_spec("projection_version", "u16"),
            _field_spec("audience", "AudienceV1"),
            _field_spec("durability", "DurabilityV1"),
            _field_spec("verified_tick", "u64"),
            _field_spec("graph_state_hash", "digest_hex"),
            _field_spec("nominal_world_hash", "digest_hex"),
            _field_spec(
                "reference_digests",
                "list[ReferenceDigestV1]",
                bound="max_reference_digests",
                sort_key="reference_id",
            ),
            _field_spec("definitions_digest", "digest_hex"),
            _field_spec("template_digest", "digest_hex"),
            _field_spec("fog_policy_digest", "digest_hex", nullable=True),
            _field_spec("knowledge_context_digest", "digest_hex", nullable=True),
            _field_spec("actor", "identity", nullable=True),
            _field_spec("focus", "list[identity]", bound="max_focus", sort_key="identity"),
            _field_spec(
                "scale_memberships",
                "list[ScaleMembershipV1]",
                bound="max_scale_memberships",
                sort_key="membership_id",
            ),
            _field_spec("facets", "list[FacetV1]", bound="max_facets", sort_key="facet_id"),
            _field_spec("dyads", "list[DyadV1]", bound="max_dyads", sort_key="relation_id"),
            _field_spec(
                "hyperedges",
                "list[HyperedgeV1]",
                bound="max_hyperedges",
                sort_key="hyperedge_id",
            ),
            _field_spec("flows", "list[ReferenceFlowV1]", bound="max_flows", sort_key="flow_id"),
            _field_spec("gaps", "list[GapV1]", bound="max_gaps", sort_key="gap_id"),
            _field_spec(
                "provenance",
                "list[ProvenanceV1]",
                bound="max_provenance",
                sort_key="provenance_id",
            ),
            _field_spec("decision_surface", "DecisionSurfaceV1"),
            _field_spec("projection_hash", "digest_hex"),
        ),
    ),
)

EXPECTED_CANONICAL_SET_ROWS = (
    ("ScaleMembershipV1.provenance_refs", "identity"),
    ("FacetV1.coordinates", "dimension_ref"),
    ("FacetV1.provenance_refs", "identity"),
    ("DyadV1.payload_facets", "identity"),
    ("DyadV1.provenance_refs", "identity"),
    ("HyperedgeV1.member_refs", "identity"),
    ("HyperedgeV1.payload_facets", "identity"),
    ("HyperedgeV1.provenance_refs", "identity"),
    ("ReferenceFlowV1.payload_facets", "identity"),
    ("ReferenceFlowV1.provenance_refs", "identity"),
    ("GapV1.provenance_refs", "identity"),
    ("DecisionSurfaceV1.signal_refs", "input_order"),
    ("DecisionSurfaceV1.action_refs", "input_order"),
    ("DecisionSurfaceV1.receipt_refs", "input_order"),
    ("DecisionSurfaceV1.archive_subject_refs", "input_order"),
    ("RtdDossierDraftV1.reference_digests", "reference_id"),
    ("RtdDossierDraftV1.focus", "identity"),
    ("RtdDossierDraftV1.scale_memberships", "membership_id"),
    ("RtdDossierDraftV1.facets", "facet_id"),
    ("RtdDossierDraftV1.dyads", "relation_id"),
    ("RtdDossierDraftV1.hyperedges", "hyperedge_id"),
    ("RtdDossierDraftV1.flows", "flow_id"),
    ("RtdDossierDraftV1.gaps", "gap_id"),
    ("RtdDossierDraftV1.provenance", "provenance_id"),
    ("RelationalTerritoryDossierV1.reference_digests", "reference_id"),
    ("RelationalTerritoryDossierV1.focus", "identity"),
    ("RelationalTerritoryDossierV1.scale_memberships", "membership_id"),
    ("RelationalTerritoryDossierV1.facets", "facet_id"),
    ("RelationalTerritoryDossierV1.dyads", "relation_id"),
    ("RelationalTerritoryDossierV1.hyperedges", "hyperedge_id"),
    ("RelationalTerritoryDossierV1.flows", "flow_id"),
    ("RelationalTerritoryDossierV1.gaps", "gap_id"),
    ("RelationalTerritoryDossierV1.provenance", "provenance_id"),
)

REQUIRED_OPTION_FIELDS = (
    ("ReferenceDigestV1", ("artifact_schema_id_or_null",)),
    ("ScaleMembershipV1", ("weight_bits_or_null",)),
    ("FacetV1", ("value_bits_or_null",)),
    ("GapV1", ("required_producer_or_null",)),
    ("ProvenanceV1", ("transformation_digest_or_null",)),
    (
        "RtdDossierDraftV1",
        ("fog_policy_digest", "knowledge_context_digest", "actor"),
    ),
    (
        "RelationalTerritoryDossierV1",
        ("fog_policy_digest", "knowledge_context_digest", "actor"),
    ),
)


def _identity(domain: str, authority: str, local_id: str) -> TypedIdentitySpec:
    return TypedIdentitySpec(domain=domain, authority=authority, local_id=local_id)


def _metric_identity(local_id: str) -> TypedIdentitySpec:
    return _identity("metric", "babylon.rtd.v1", local_id)


def _unit(local_id: str) -> TypedIdentitySpec:
    return _identity("unit", "babylon.rtd.v1", local_id)


def _dimension(local_id: str) -> TypedIdentitySpec:
    return _identity("dimension", "babylon.rtd.v1", local_id)


def _native_scale(local_id: str) -> TypedIdentitySpec:
    return _identity("native-scale", "babylon.rtd.v1", local_id)


def _producer(local_id: str) -> TypedIdentitySpec:
    authority = (
        "babylon.engine"
        if local_id == "typed-graph-relations-at-verified-tick"
        else "babylon.data.v7"
    )
    return _identity("producer", authority, local_id)


def _reference(local_id: str) -> TypedIdentitySpec:
    return _identity("reference-artifact", "babylon.data.v7", local_id)


UNIT_LOCAL_IDS = {
    "JOBS": "jobs",
    "ESTABLISHMENTS": "establishments",
    "USD_CURRENT": "usd-current",
    "HOUSEHOLDS": "households",
    "PERSONS": "persons",
    "FACILITIES": "facilities",
    "FRACTION": "fraction",
    "TYPED_RELATION": "typed-relation",
}

COORDINATE_LOCAL_IDS = {
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

SCALE_LOCAL_IDS = {
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

ARTIFACTS = (
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


def _metric(
    metric: str,
    representation: str,
    unit: str,
    value_kind: str | None,
    native_scale: str,
    coordinates: tuple[str, ...],
    evidence_classes: tuple[str, ...],
    aggregation_rule: str,
    producer: str,
    reference: str | None,
    digest: str | None,
) -> ExpandedMetricSpec:
    producer_identity = (
        _producer("typed-graph-relations-at-verified-tick")
        if producer == "committed typed graph"
        else _producer(producer)
    )
    expanded_coordinates: list[TypedIdentitySpec] = []
    for coordinate_index in range(MAX_EXPECTED_METRIC_COORDINATES):
        if coordinate_index >= len(coordinates):
            break
        key = coordinates[coordinate_index]
        expanded_coordinates.append(_dimension(COORDINATE_LOCAL_IDS[key]))
    return ExpandedMetricSpec(
        metric=_metric_identity(metric),
        representation=representation,
        unit=_unit(UNIT_LOCAL_IDS[unit]),
        value_kind=value_kind,
        native_scale=_native_scale(SCALE_LOCAL_IDS[native_scale]),
        coordinates=tuple(expanded_coordinates),
        evidence_classes=evidence_classes,
        aggregation_rule=aggregation_rule,
        producer=producer_identity,
        reference_artifact=None if reference is None else _reference(reference),
        reference_digest=digest,
    )


QCEW_LEAF_DIGEST = "ca3825a3d60831479313632073b7fc9a941d57dcf9b8940181c4713b6d442248"
QCEW_COUNTY_DIGEST = "34c2bbb935f79b3c8076a97092b004b14cca120e8272b93c35b3ac9dc2721d13"
LODES_DIGEST = "d3745f8def09cd8c7a38e1870e6ec2c1853e210b777d8e8358cfce36665bd64d"
CENSUS_HOUSING_DIGEST = "09ff2d9666b3f5ef267b65cbc77c14e99384f0157b6a4c898ac37df2e67ca59f"
CENSUS_RENT_DIGEST = "4c8cc134ec490ca75961d83485fc97c6bf240b32128e9d0517e00e62d578a99e"
CENSUS_BURDEN_DIGEST = "8a42a51c17bf3ebee09f0b0b5145d5c8253c7e3446eec8c75714f9951b20df12"
H3_POPULATION_DIGEST = "b096a5891284f0ca55bedae9d1a9092eb8ea9e9e32d32b6ace430a9833b53afc"
H3_WORKPLACE_DIGEST = "ea2ce1508f4fe51f1e879b9f4a1daf579c4b00349388b12a85f884a8f49eabb6"
CARCERAL_DIGEST = "33e6558d2b438e7aea672021f0e15f743f1ea331ab82407c0805a428b29cf808"
LAND_FRACTION_DIGEST = "4e6caba297f0111a9ec93d948a83543bb9f7179361fe5dd318bb8a98a5be5194"

EXPECTED_METRICS = (
    _metric(
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
        QCEW_LEAF_DIGEST,
    ),
    _metric(
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
        QCEW_LEAF_DIGEST,
    ),
    _metric(
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
        QCEW_LEAF_DIGEST,
    ),
    _metric(
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
        QCEW_LEAF_DIGEST,
    ),
    _metric(
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
        QCEW_COUNTY_DIGEST,
    ),
    _metric(
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
        QCEW_COUNTY_DIGEST,
    ),
    _metric(
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
        QCEW_COUNTY_DIGEST,
    ),
    _metric(
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
        LODES_DIGEST,
    ),
    _metric(
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
        CENSUS_HOUSING_DIGEST,
    ),
    _metric(
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
        CENSUS_RENT_DIGEST,
    ),
    _metric(
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
        CENSUS_BURDEN_DIGEST,
    ),
    _metric(
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
        H3_POPULATION_DIGEST,
    ),
    _metric(
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
        H3_WORKPLACE_DIGEST,
    ),
    _metric(
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
        CARCERAL_DIGEST,
    ),
    _metric(
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
        LAND_FRACTION_DIGEST,
    ),
    _metric(
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
    _metric(
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
    _metric(
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

EXPECTED_BINDINGS = (
    RelationBindingSpec(
        "REFERENCE_FLOW",
        "COMMUTER_JOBS",
        _metric_identity("circulation/lodes-county-commuter-total-jobs"),
        "SINGLE_METRIC_FACET",
    ),
    RelationBindingSpec("REFERENCE_FLOW", "BORDER_SYNTHESIS", None, "EMPTY"),
    RelationBindingSpec(
        "DYAD", "PRESENCE", _metric_identity("rootedness/presence"), "IMPLICIT_RELATION"
    ),
    RelationBindingSpec(
        "DYAD", "MEMBERSHIP", _metric_identity("rootedness/membership"), "IMPLICIT_RELATION"
    ),
    RelationBindingSpec(
        "DYAD", "SOLIDARITY", _metric_identity("rootedness/solidarity"), "IMPLICIT_RELATION"
    ),
    RelationBindingSpec("DYAD", "COMMAND", None, "EMPTY"),
)


def run_generator_check() -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed argv and repository path
        [sys.executable, str(GENERATOR_PATH), "--check"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_contract_declares_every_sealed_record() -> None:
    contract = load_contract(CONTRACT_PATH)
    assert contract.records == EXPECTED_RECORDS


def test_contract_freezes_schema_enums_limits_and_errors() -> None:
    contract = load_contract(CONTRACT_PATH)
    assert contract.schema == "babylon.relational-territory-dossier"
    assert contract.schema_version == 1
    assert contract.scalar_types == EXPECTED_SCALAR_TYPES
    assert contract.enums == EXPECTED_ENUMS
    assert contract.limits == EXPECTED_LIMITS
    assert contract.error_registry == EXPECTED_ERRORS


def test_contract_freezes_complete_record_layouts_and_order_policy() -> None:
    contract = load_contract(CONTRACT_PATH)
    assert contract.record_specs == EXPECTED_RECORD_SPECS
    assert tuple(contract.canonical_sets.items()) == EXPECTED_CANONICAL_SET_ROWS


def test_contract_expands_every_identity_registry_component() -> None:
    contract = load_contract(CONTRACT_PATH)
    expected = _expected_identity_registry()
    assert contract.identity_registry == expected


def _expected_identity_registry() -> dict[str, dict[str, TypedIdentitySpec]]:
    expected: dict[str, dict[str, TypedIdentitySpec]] = {
        "metrics": {},
        "units": {},
        "coordinates": {},
        "native_scales": {},
        "producers": {},
        "references": {},
    }
    for metric_index in range(EXPECTED_METRIC_COUNT):
        metric = EXPECTED_METRICS[metric_index].metric
        expected["metrics"][metric.local_id] = metric
    unit_rows = tuple(UNIT_LOCAL_IDS.items())
    for unit_index in range(EXPECTED_UNIT_COUNT):
        key, local_id = unit_rows[unit_index]
        expected["units"][key] = _unit(local_id)
    coordinate_rows = tuple(COORDINATE_LOCAL_IDS.items())
    for coordinate_index in range(EXPECTED_COORDINATE_COUNT):
        key, local_id = coordinate_rows[coordinate_index]
        expected["coordinates"][key] = _dimension(local_id)
    scale_rows = tuple(SCALE_LOCAL_IDS.items())
    for scale_index in range(EXPECTED_SCALE_COUNT):
        key, local_id = scale_rows[scale_index]
        expected["native_scales"][key] = _native_scale(local_id)
    for artifact_index in range(EXPECTED_ARTIFACT_COUNT):
        artifact = ARTIFACTS[artifact_index]
        expected["producers"][artifact] = _producer(artifact)
        expected["references"][artifact] = _reference(artifact)
    expected["producers"]["committed typed graph"] = _producer(
        "typed-graph-relations-at-verified-tick"
    )
    return expected


def test_metric_and_relation_registries_are_exact_and_fully_expanded() -> None:
    contract = load_contract(CONTRACT_PATH)
    assert contract.metric_registry == EXPECTED_METRICS
    assert contract.relation_binding_registry == EXPECTED_BINDINGS


def test_rendered_metric_rows_contain_complete_identities_not_registry_keys() -> None:
    contract = load_contract(CONTRACT_PATH)
    python_source = render_python(contract)
    rust_source = render_rust(contract)
    python_metrics = python_source.split("RTD_V1_METRIC_REGISTRY = (", 1)[1].split(
        "RTD_V1_RELATION_BINDING_REGISTRY = (", 1
    )[0]
    rust_metrics = rust_source.split(
        "pub const RTD_V1_METRIC_REGISTRY: &[RtdMetricRegistryRowV1] = &[", 1
    )[1].split("pub const RTD_V1_RELATION_BINDING_REGISTRY", 1)[0]
    assert python_metrics.count("metric=TypedIdentityV1(") == 18
    assert rust_metrics.count("metric: TypedIdentityLiteralV1 {") == 18
    assert "metric_key" not in python_source
    assert "unit_key" not in python_source
    assert "native_scale_key" not in python_source
    assert "producer_key" not in python_source
    assert "reference_key" not in python_source
    assert "metric_key" not in rust_source
    assert "unit_key" not in rust_source


def test_projection_hash_exists_only_on_the_sealed_record() -> None:
    contract = load_contract(CONTRACT_PATH)
    python_source = render_python(contract)
    rust_source = render_rust(contract)
    assert python_source.count("projection_hash:") == 1
    assert rust_source.count("projection_hash:") == 1
    assert python_source.index("projection_hash:") > python_source.index(
        "class RelationalTerritoryDossierV1"
    )
    assert rust_source.index("projection_hash:") > rust_source.index(
        "pub struct RelationalTerritoryDossierV1"
    )


def _rust_struct_body(source: str, record_name: str) -> str:
    return source.split(f"pub struct {record_name} {{", 1)[1].split("\n}", 1)[0]


def test_rust_nullable_fields_require_keys_and_accept_explicit_null() -> None:
    rust_source = render_rust(load_contract(CONTRACT_PATH))
    helper = """fn deserialize_required_option<'de, D, T>(deserializer: D) -> Result<Option<T>, D::Error>
where
    D: serde::Deserializer<'de>,
    T: Deserialize<'de>,
{
    Option::<T>::deserialize(deserializer)
}"""
    assert helper in rust_source
    assert "#[serde(default" not in rust_source
    for record_index in range(REQUIRED_OPTION_RECORD_COUNT):
        record_name, field_names = REQUIRED_OPTION_FIELDS[record_index]
        body = _rust_struct_body(rust_source, record_name)
        for field_index in range(MAX_REQUIRED_OPTIONS_PER_RECORD):
            if field_index >= len(field_names):
                break
            field_name = field_names[field_index]
            assert (
                '#[serde(deserialize_with = "deserialize_required_option")]\n'
                f"    pub {field_name}: Option<"
            ) in body


def test_both_sources_publish_every_closed_registry() -> None:
    contract = load_contract(CONTRACT_PATH)
    python_source = render_python(contract)
    rust_source = render_rust(contract)
    required_names = (
        "RTD_V1_SCHEMA_ID",
        "RTD_V1_LIMITS",
        "RTD_V1_ERROR_REGISTRY",
        "RTD_V1_IDENTITY_REGISTRY",
        "RTD_V1_METRIC_REGISTRY",
        "RTD_V1_RELATION_BINDING_REGISTRY",
    )
    for name_index in range(REQUIRED_REGISTRY_COUNT):
        name = required_names[name_index]
        assert name in python_source
        assert name in rust_source


def test_generated_files_are_current() -> None:
    result = run_generator_check()
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"


def _identity_payload(local_id: str) -> dict[str, str]:
    return {
        "domain": "test",
        "authority": "babylon.rtd.v1.tests",
        "local_id": local_id,
    }


def _minimal_draft_payload() -> dict[str, Any]:
    return {
        "schema": "babylon.relational-territory-dossier",
        "schema_version": 1,
        "projection_version": 1,
        "audience": "ADMIN_MATERIAL",
        "durability": "IN_MEMORY",
        "verified_tick": 0,
        "graph_state_hash": "0" * 64,
        "nominal_world_hash": "0" * 64,
        "reference_digests": [],
        "definitions_digest": "0" * 64,
        "template_digest": "0" * 64,
        "fog_policy_digest": None,
        "knowledge_context_digest": None,
        "actor": None,
        "focus": [_identity_payload("focus")],
        "scale_memberships": [],
        "facets": [],
        "dyads": [],
        "hyperedges": [],
        "flows": [],
        "gaps": [],
        "provenance": [],
        "decision_surface": {
            "question_id": _identity_payload("question"),
            "signal_refs": [_identity_payload("signal")],
            "action_refs": [],
            "receipt_refs": [],
            "archive_subject_refs": [],
        },
    }


def test_generated_python_collections_are_deeply_immutable_tuples() -> None:
    draft = RtdDossierDraftV1.model_validate(_minimal_draft_payload())
    assert isinstance(draft.focus, tuple)
    assert isinstance(draft.decision_surface.signal_refs, tuple)
    with pytest.raises(AttributeError):
        cast(Any, draft.focus).append(draft.focus[0])
    with pytest.raises(TypeError):
        cast(Any, draft.focus)[0] = draft.focus[0]
    with pytest.raises(AttributeError):
        cast(Any, draft.decision_surface.signal_refs).append(draft.focus[0])


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    (
        ("schema_version", "1"),
        ("schema_version", 1.0),
        ("schema_version", -1),
        ("schema_version", 65_536),
        ("projection_version", "1"),
        ("projection_version", 1.0),
        ("projection_version", -1),
        ("projection_version", 65_536),
        ("verified_tick", "1"),
        ("verified_tick", 1.0),
        ("verified_tick", -1),
        ("verified_tick", 18_446_744_073_709_551_616),
    ),
)
def test_generated_python_unsigned_fields_refuse_coercion_and_overflow(
    field_name: str, invalid_value: object
) -> None:
    payload = _minimal_draft_payload()
    payload[field_name] = invalid_value
    with pytest.raises(ValidationError):
        RtdDossierDraftV1.model_validate(payload)


def test_generated_python_unsigned_fields_accept_exact_boundaries() -> None:
    payload = _minimal_draft_payload()
    payload["schema_version"] = 0
    payload["projection_version"] = 65_535
    payload["verified_tick"] = 18_446_744_073_709_551_615
    draft = RtdDossierDraftV1.model_validate(payload)
    assert draft.schema_version == 0
    assert draft.projection_version == 65_535
    assert draft.verified_tick == 18_446_744_073_709_551_615


@pytest.mark.parametrize(
    ("python_exists", "rust_exists"),
    ((False, False), (False, True), (True, False), (True, True)),
)
def test_two_output_publication_success_replaces_both_and_cleans_private_artifacts(
    tmp_path: Path,
    python_exists: bool,
    rust_exists: bool,
) -> None:
    python_path = tmp_path / "generated.py"
    rust_path = tmp_path / "generated.rs"
    if python_exists:
        python_path.write_bytes(b"old python generation\n")
    if rust_exists:
        rust_path.write_bytes(b"old rust generation\n")

    generator._write_outputs(python_path, "new python\n", rust_path, "new rust\n")

    assert python_path.read_bytes() == b"new python\n"
    assert rust_path.read_bytes() == b"new rust\n"
    assert not tuple(tmp_path.glob(".generated.py.*"))
    assert not tuple(tmp_path.glob(".generated.rs.*"))


@pytest.mark.parametrize(
    ("python_exists", "rust_exists"),
    ((False, False), (False, True), (True, False), (True, True)),
)
@pytest.mark.parametrize("failure_index", (1, 2))
def test_two_output_publication_failure_restores_every_original_existence_combination(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    python_exists: bool,
    rust_exists: bool,
    failure_index: int,
) -> None:
    python_path = tmp_path / "generated.py"
    rust_path = tmp_path / "generated.rs"
    old_python = b"old python generation\n"
    old_rust = b"old rust generation\n"
    if python_exists:
        python_path.write_bytes(old_python)
    if rust_exists:
        rust_path.write_bytes(old_rust)

    real_publish = generator._publish_output
    publication_count = 0

    def fail_publication(state: Any) -> None:
        nonlocal publication_count
        publication_count += 1
        real_publish(state)
        if publication_count == failure_index:
            raise OSError(f"injected publication failure {failure_index}")

    monkeypatch.setattr(generator, "_publish_output", fail_publication)
    with pytest.raises(OSError, match=f"injected publication failure {failure_index}"):
        generator._write_outputs(python_path, "new python\n", rust_path, "new rust\n")

    if python_exists:
        assert python_path.read_bytes() == old_python
    else:
        assert not python_path.exists()
    if rust_exists:
        assert rust_path.read_bytes() == old_rust
    else:
        assert not rust_path.exists()
    assert not tuple(tmp_path.glob(".generated.py.*"))
    assert not tuple(tmp_path.glob(".generated.rs.*"))


@pytest.mark.parametrize(
    ("target_index", "target_label"),
    ((1, "Python"), (2, "Rust")),
)
def test_prepublication_concurrent_create_never_overwrites_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target_index: int,
    target_label: str,
) -> None:
    python_path = tmp_path / "generated.py"
    rust_path = tmp_path / "generated.rs"
    target_path = python_path if target_index == 1 else rust_path
    other_path = rust_path if target_index == 1 else python_path
    concurrent_bytes = f"concurrent {target_label.lower()} create\n".encode()
    real_publish = generator._publish_output
    publication_count = 0

    def race_before_publication(state: Any) -> None:
        nonlocal publication_count
        publication_count += 1
        if publication_count == target_index:
            target_path.write_bytes(concurrent_bytes)
        real_publish(state)

    monkeypatch.setattr(generator, "_publish_output", race_before_publication)
    with pytest.raises(
        OSError,
        match=rf"RTD_OUTPUT_CAS: {target_label} target was created after snapshot",
    ) as error:
        generator._write_outputs(python_path, "new python\n", rust_path, "new rust\n")

    assert target_path.read_bytes() == concurrent_bytes
    assert str(target_path) in str(error.value)
    assert not other_path.exists()


@pytest.mark.parametrize(
    ("target_index", "target_label"),
    ((1, "Python"), (2, "Rust")),
)
def test_existing_output_publication_no_clobber_preserves_late_create(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target_index: int,
    target_label: str,
) -> None:
    python_path = tmp_path / "generated.py"
    rust_path = tmp_path / "generated.rs"
    original_python = b"original python generation\n"
    original_rust = b"original rust generation\n"
    python_path.write_bytes(original_python)
    rust_path.write_bytes(original_rust)
    target_path = python_path if target_index == 1 else rust_path
    other_path = rust_path if target_index == 1 else python_path
    target_original = original_python if target_index == 1 else original_rust
    other_original = original_rust if target_index == 1 else original_python
    concurrent_bytes = f"late {target_label.lower()} create\n".encode()
    real_link_staged = generator._link_staged_output

    def race_after_isolation(state: Any) -> None:
        if state.label == target_label:
            target_path.write_bytes(concurrent_bytes)
        real_link_staged(state)

    monkeypatch.setattr(generator, "_link_staged_output", race_after_isolation)
    with pytest.raises(
        OSError,
        match=rf"RTD_OUTPUT_CAS: {target_label} target was created after snapshot",
    ) as error:
        generator._write_outputs(python_path, "new python\n", rust_path, "new rust\n")

    assert target_path.read_bytes() == concurrent_bytes
    assert other_path.read_bytes() == other_original
    recovery_marker = "original output recovery preserved at "
    recovery_path_text = str(error.value).split(recovery_marker, 1)[1].split(";", 1)[0]
    recovery_path = Path(recovery_path_text)
    assert recovery_path.read_bytes() == target_original


@pytest.mark.parametrize(
    ("target_index", "target_label"),
    ((1, "Python"), (2, "Rust")),
)
@pytest.mark.parametrize("replace_inode", (False, True), ids=("same-inode", "replacement-inode"))
def test_prepublication_concurrent_update_never_overwrites_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target_index: int,
    target_label: str,
    replace_inode: bool,
) -> None:
    python_path = tmp_path / "generated.py"
    rust_path = tmp_path / "generated.rs"
    original_python = b"original python generation\n"
    original_rust = b"original rust generation\n"
    python_path.write_bytes(original_python)
    rust_path.write_bytes(original_rust)
    target_path = python_path if target_index == 1 else rust_path
    other_path = rust_path if target_index == 1 else python_path
    target_original = original_python if target_index == 1 else original_rust
    other_original = original_rust if target_index == 1 else original_python
    concurrent_bytes = f"concurrent {target_label.lower()} update\n".encode()
    concurrent_path = tmp_path / f"concurrent-{target_label.lower()}"
    real_publish = generator._publish_output
    publication_count = 0

    def race_before_publication(state: Any) -> None:
        nonlocal publication_count
        publication_count += 1
        if publication_count == target_index:
            if replace_inode:
                concurrent_path.write_bytes(concurrent_bytes)
                os.replace(concurrent_path, target_path)
            else:
                target_path.write_bytes(concurrent_bytes)
        real_publish(state)

    monkeypatch.setattr(generator, "_publish_output", race_before_publication)
    with pytest.raises(
        OSError,
        match=rf"RTD_OUTPUT_CAS: {target_label} target changed after snapshot",
    ) as error:
        generator._write_outputs(python_path, "new python\n", rust_path, "new rust\n")

    assert target_path.read_bytes() == concurrent_bytes
    assert str(target_path) in str(error.value)
    assert other_path.read_bytes() == other_original
    recovery_marker = "original recovery snapshot preserved at "
    recovery_path_text = str(error.value).split(recovery_marker, 1)[1].split(";", 1)[0]
    recovery_path = Path(recovery_path_text)
    assert recovery_path.read_bytes() == target_original
    displaced_marker = "displaced output preserved at "
    displaced_path_text = str(error.value).split(displaced_marker, 1)[1].split(";", 1)[0]
    displaced_path = Path(displaced_path_text)
    assert displaced_path.read_bytes() == concurrent_bytes


@pytest.mark.parametrize("restoration_failure_index", (1, 2))
def test_rollback_preserves_failed_restoration_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    restoration_failure_index: int,
) -> None:
    python_path = tmp_path / "generated.py"
    rust_path = tmp_path / "generated.rs"
    old_python = b"old python generation\n"
    old_rust = b"old rust generation\n"
    python_path.write_bytes(old_python)
    rust_path.write_bytes(old_rust)

    real_publish = generator._publish_output
    publication_count = 0

    def fail_after_second_publication(state: Any) -> None:
        nonlocal publication_count
        publication_count += 1
        real_publish(state)
        if publication_count == 2:
            raise OSError("injected post-publication failure")

    real_restore = generator._restore_original_output
    restoration_count = 0

    def fail_restoration(state: Any) -> None:
        nonlocal restoration_count
        restoration_count += 1
        if restoration_count == restoration_failure_index:
            raise OSError(f"injected restoration failure {restoration_failure_index}")
        real_restore(state)

    monkeypatch.setattr(generator, "_publish_output", fail_after_second_publication)
    monkeypatch.setattr(generator, "_restore_original_output", fail_restoration)
    failed_label = "Python" if restoration_failure_index == 1 else "Rust"
    with pytest.raises(
        OSError,
        match=rf"RTD_OUTPUT_ROLLBACK: {failed_label} restoration failed; ",
    ) as error:
        generator._write_outputs(python_path, "new python\n", rust_path, "new rust\n")

    failed_path = python_path if restoration_failure_index == 1 else rust_path
    restored_path = rust_path if restoration_failure_index == 1 else python_path
    restored_bytes = old_rust if restoration_failure_index == 1 else old_python
    failed_bytes = old_python if restoration_failure_index == 1 else old_rust
    assert not failed_path.exists()
    assert restored_path.read_bytes() == restored_bytes
    assert not tuple(tmp_path.glob(f".{restored_path.name}.*"))
    recovery_marker = "original output recovery preserved at "
    recovery_path_text = str(error.value).split(recovery_marker, 1)[1].split(";", 1)[0]
    recovery_path = Path(recovery_path_text)
    assert recovery_path.read_bytes() == failed_bytes


@pytest.mark.parametrize(
    ("target_index", "target_label"),
    ((1, "Python"), (2, "Rust")),
)
@pytest.mark.parametrize("replace_inode", (False, True), ids=("same-inode", "replacement-inode"))
def test_absent_output_rollback_preserves_a_concurrent_replacement_for_both_targets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target_index: int,
    target_label: str,
    replace_inode: bool,
) -> None:
    python_path = tmp_path / "generated.py"
    rust_path = tmp_path / "generated.rs"
    target_path = python_path if target_index == 1 else rust_path
    other_path = rust_path if target_index == 1 else python_path
    concurrent_bytes = f"concurrent {target_label.lower()} rollback writer\n".encode()
    concurrent_path = tmp_path / f"concurrent-{target_label.lower()}"
    concurrent_path.write_bytes(concurrent_bytes)

    real_publish = generator._publish_output
    publication_count = 0

    def fail_after_second_publication(state: Any) -> None:
        nonlocal publication_count
        publication_count += 1
        real_publish(state)
        if publication_count == 2:
            raise OSError("injected post-publication failure")

    real_restore = generator._restore_published_output
    race_injected = False

    def race_before_rollback(state: Any) -> None:
        nonlocal race_injected
        if state.label == target_label and not race_injected:
            race_injected = True
            if replace_inode:
                os.replace(concurrent_path, target_path)
            else:
                target_path.write_bytes(concurrent_bytes)
        real_restore(state)

    monkeypatch.setattr(generator, "_publish_output", fail_after_second_publication)
    monkeypatch.setattr(generator, "_restore_published_output", race_before_rollback)
    with pytest.raises(
        OSError,
        match=rf"RTD_OUTPUT_ROLLBACK: {target_label} published output changed before rollback",
    ) as error:
        generator._write_outputs(python_path, "new python\n", rust_path, "new rust\n")

    assert target_path.read_bytes() == concurrent_bytes
    assert str(target_path) in str(error.value)
    assert not other_path.exists()
    displaced_marker = "displaced output preserved at "
    displaced_path_text = str(error.value).split(displaced_marker, 1)[1].split(";", 1)[0]
    displaced_path = Path(displaced_path_text)
    assert displaced_path.read_bytes() == concurrent_bytes
    if replace_inode:
        recovery_marker = "published generation preserved at "
        recovery_path_text = str(error.value).split(recovery_marker, 1)[1].split(";", 1)[0]
        recovery_path = Path(recovery_path_text)
        expected_generation = b"new python\n" if target_index == 1 else b"new rust\n"
        assert recovery_path.read_bytes() == expected_generation


def _canonical_document() -> dict[str, Any]:
    document = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


def _record_field(document: dict[str, Any], record_name: str, field_name: str) -> dict[str, Any]:
    fields = cast(list[dict[str, Any]], document["records"][record_name]["fields"])
    matches: list[dict[str, Any]] = []
    for field_index in range(MAX_EXPECTED_RECORD_FIELDS):
        if field_index >= len(fields):
            break
        field = fields[field_index]
        if field["name"] == field_name:
            matches.append(field)
    assert len(matches) == 1
    return matches[0]


def _apply_record_layout_mutation(document: dict[str, Any], mutation: str) -> None:
    if mutation == "add_field":
        document["records"]["TypedIdentityV1"]["fields"].append({"name": "extra", "type": "string"})
        return
    if mutation == "remove_field":
        document["records"]["TypedIdentityV1"]["fields"].pop()
        return
    if mutation == "type":
        _record_field(document, "TypedIdentityV1", "domain")["type"] = "vintage"
        return
    if mutation == "nullability":
        _record_field(document, "TypedIdentityV1", "domain")["nullable"] = True
        return
    if mutation == "bound":
        _record_field(document, "TypedIdentityV1", "domain")["bound"] = "max_vintage_bytes"
        return
    if mutation == "field_order":
        fields = document["records"]["TypedIdentityV1"]["fields"]
        fields[0], fields[1] = fields[1], fields[0]
        return
    if mutation in {"u16_to_u64", "u64_to_u16", "digest_constraint"}:
        field_name = {
            "u16_to_u64": "projection_version",
            "u64_to_u16": "verified_tick",
            "digest_constraint": "graph_state_hash",
        }[mutation]
        replacement = {
            "u16_to_u64": "u64",
            "u64_to_u16": "u16",
            "digest_constraint": "string",
        }[mutation]
        _record_field(document, "RtdDossierDraftV1", field_name)["type"] = replacement
        _record_field(document, "RelationalTerritoryDossierV1", field_name)["type"] = replacement
        return
    if mutation == "display_order_to_sort":
        _record_field(document, "DecisionSurfaceV1", "signal_refs")["sort_key"] = "identity"
        document["canonical_sets"]["DecisionSurfaceV1.signal_refs"] = "identity"
        return
    raise AssertionError(f"unhandled test mutation {mutation}")


@pytest.mark.parametrize(
    "mutation",
    (
        "add_field",
        "remove_field",
        "type",
        "nullability",
        "bound",
        "field_order",
        "u16_to_u64",
        "u64_to_u16",
        "digest_constraint",
        "display_order_to_sort",
    ),
)
def test_complete_record_layout_mutations_refuse_atomically(tmp_path: Path, mutation: str) -> None:
    document = _canonical_document()
    _apply_record_layout_mutation(document, mutation)
    _assert_contract_refusal(tmp_path, _dump_contract(document), CONTRACT_SCHEMA_ERROR)


def _dump_contract(document: dict[str, Any]) -> bytes:
    return yaml.safe_dump(document, sort_keys=False, allow_unicode=True).encode("utf-8")


def _assert_contract_refusal(tmp_path: Path, raw: bytes, expected_code: str) -> None:
    tmp_path.mkdir(parents=True, exist_ok=True)
    contract_path = tmp_path / "contract.yaml"
    python_output = tmp_path / "generated.py"
    rust_output = tmp_path / "generated.rs"
    python_sentinel = b"unchanged python output\n"
    rust_sentinel = b"unchanged rust output\n"
    contract_path.write_bytes(raw)
    python_output.write_bytes(python_sentinel)
    rust_output.write_bytes(rust_sentinel)

    with pytest.raises(ContractLoadError) as error:
        load_contract(contract_path)
    assert error.value.code == expected_code
    assert (
        main(
            [
                "--contract",
                str(contract_path),
                "--python-out",
                str(python_output),
                "--rust-out",
                str(rust_output),
            ]
        )
        == 2
    )
    assert python_output.read_bytes() == python_sentinel
    assert rust_output.read_bytes() == rust_sentinel


def test_missing_record_and_changed_limit_refuse_atomically(tmp_path: Path) -> None:
    missing_record = _canonical_document()
    del missing_record["records"]["GapV1"]
    _assert_contract_refusal(
        tmp_path / "missing-record", _dump_contract(missing_record), CONTRACT_SCHEMA_ERROR
    )

    changed_limit = _canonical_document()
    changed_limit["limits"]["max_focus"] = 65
    _assert_contract_refusal(
        tmp_path / "changed-limit", _dump_contract(changed_limit), CONTRACT_SCHEMA_ERROR
    )


def test_missing_and_extra_metric_rows_refuse_atomically(tmp_path: Path) -> None:
    missing = _canonical_document()
    missing["metric_registry"].pop()
    _assert_contract_refusal(tmp_path / "missing", _dump_contract(missing), CONTRACT_SCHEMA_ERROR)

    extra = _canonical_document()
    extra["metric_registry"].append(copy.deepcopy(extra["metric_registry"][0]))
    _assert_contract_refusal(tmp_path / "extra", _dump_contract(extra), CONTRACT_SCHEMA_ERROR)


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("unit", "PERSONS"),
        ("native_scale", "COUNTY_OWNERSHIP_YEAR"),
        ("coordinates", ["county", "ownership"]),
        ("evidence_classes", ["Observed"]),
        ("aggregation_rule", "PUBLISHED_ROLLUP"),
    ),
)
def test_metric_semantic_mutations_refuse_atomically(
    tmp_path: Path,
    field: str,
    replacement: Any,
) -> None:
    document = _canonical_document()
    document["metric_registry"][0][field] = replacement
    _assert_contract_refusal(tmp_path, _dump_contract(document), CONTRACT_SCHEMA_ERROR)


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("coordinates", ["county"] * (MAX_METRIC_COORDINATES + 1)),
        (
            "evidence_classes",
            ["Observed"] * (MAX_METRIC_EVIDENCE_CLASSES + 1),
        ),
    ),
)
def test_metric_nested_sequence_limit_plus_one_refuses_atomically(
    tmp_path: Path,
    field: str,
    replacement: list[str],
) -> None:
    document = _canonical_document()
    document["metric_registry"][0][field] = replacement
    _assert_contract_refusal(tmp_path, _dump_contract(document), CONTRACT_LIMIT_ERROR)


def test_missing_duplicate_and_remapped_bindings_refuse_atomically(tmp_path: Path) -> None:
    missing = _canonical_document()
    missing["relation_binding_registry"].pop()
    _assert_contract_refusal(tmp_path / "missing", _dump_contract(missing), CONTRACT_SCHEMA_ERROR)

    duplicate = _canonical_document()
    duplicate["relation_binding_registry"].append(
        copy.deepcopy(duplicate["relation_binding_registry"][0])
    )
    _assert_contract_refusal(
        tmp_path / "duplicate", _dump_contract(duplicate), CONTRACT_SCHEMA_ERROR
    )

    remapped = _canonical_document()
    remapped["relation_binding_registry"][2]["kind"] = "COMMAND"
    _assert_contract_refusal(tmp_path / "remapped", _dump_contract(remapped), CONTRACT_SCHEMA_ERROR)


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("metric", "rootedness/presence"),
        ("payload_mode", "EMPTY"),
    ),
)
def test_commuter_binding_wrong_metric_or_payload_refuses_atomically(
    tmp_path: Path,
    field: str,
    replacement: str,
) -> None:
    document = _canonical_document()
    document["relation_binding_registry"][0][field] = replacement
    _assert_contract_refusal(tmp_path, _dump_contract(document), CONTRACT_SCHEMA_ERROR)


def test_missing_and_duplicate_identity_keys_refuse_atomically(tmp_path: Path) -> None:
    missing = _canonical_document()
    del missing["identity_registry"]["units"]["JOBS"]
    _assert_contract_refusal(tmp_path / "missing", _dump_contract(missing), CONTRACT_SCHEMA_ERROR)

    canonical = CONTRACT_PATH.read_bytes()
    duplicate = canonical.replace(
        b"    JOBS: {domain: unit, authority: babylon.rtd.v1, local_id: jobs}\n",
        b"    JOBS: {domain: unit, authority: babylon.rtd.v1, local_id: jobs}\n"
        b"    JOBS: {domain: unit, authority: babylon.rtd.v1, local_id: jobs}\n",
        1,
    )
    assert duplicate != canonical
    _assert_contract_refusal(tmp_path / "duplicate", duplicate, CONTRACT_SCHEMA_ERROR)


@pytest.mark.parametrize(
    ("component", "replacement"),
    (
        ("domain", "measure"),
        ("authority", "babylon.changed"),
        ("local_id", "employment"),
    ),
)
def test_changed_identity_components_refuse_atomically(
    tmp_path: Path,
    component: str,
    replacement: str,
) -> None:
    document = _canonical_document()
    row = document["identity_registry"]["metrics"]["production/qcew-leaf-employment"]
    row[component] = replacement
    _assert_contract_refusal(tmp_path, _dump_contract(document), CONTRACT_SCHEMA_ERROR)


def test_two_registry_keys_cannot_map_to_one_identity(tmp_path: Path) -> None:
    document = _canonical_document()
    first = document["identity_registry"]["metrics"]["production/qcew-leaf-employment"]
    document["identity_registry"]["metrics"]["production/qcew-leaf-establishments"] = copy.deepcopy(
        first
    )
    _assert_contract_refusal(tmp_path, _dump_contract(document), CONTRACT_SCHEMA_ERROR)


def test_missing_and_extra_error_rows_refuse_atomically(tmp_path: Path) -> None:
    missing = _canonical_document()
    missing["error_registry"].pop()
    _assert_contract_refusal(tmp_path / "missing", _dump_contract(missing), CONTRACT_SCHEMA_ERROR)

    extra = _canonical_document()
    extra["error_registry"].append("RTD_PRIVATE_ERROR")
    _assert_contract_refusal(tmp_path / "extra", _dump_contract(extra), CONTRACT_SCHEMA_ERROR)


def test_unknown_top_level_and_record_keys_refuse_atomically(tmp_path: Path) -> None:
    unknown_top = _canonical_document()
    unknown_top["private_registry"] = []
    _assert_contract_refusal(tmp_path / "top", _dump_contract(unknown_top), CONTRACT_SCHEMA_ERROR)

    unknown_record = _canonical_document()
    unknown_record["records"]["GapV1"]["private"] = True
    _assert_contract_refusal(
        tmp_path / "record", _dump_contract(unknown_record), CONTRACT_SCHEMA_ERROR
    )


def test_duplicate_yaml_key_and_alias_refuse_atomically(tmp_path: Path) -> None:
    canonical = CONTRACT_PATH.read_bytes()
    duplicate = canonical + b"schema: babylon.relational-territory-dossier\n"
    _assert_contract_refusal(tmp_path / "duplicate", duplicate, CONTRACT_SCHEMA_ERROR)

    alias = canonical + b"alias_source: &probe []\nalias_use: *probe\n"
    _assert_contract_refusal(tmp_path / "alias", alias, CONTRACT_SCHEMA_ERROR)


@pytest.mark.parametrize(
    ("case_id", "raw"),
    (
        ("sequence-key", b"? [one, two]\n: value\n"),
        ("mapping-key", b"? {one: two}\n: value\n"),
        ("non-string-scalar-key", b"1: value\n"),
    ),
)
def test_non_string_yaml_mapping_keys_use_stable_contract_error(
    tmp_path: Path, case_id: str, raw: bytes
) -> None:
    _assert_contract_refusal(tmp_path / case_id, raw, CONTRACT_SCHEMA_ERROR)


def test_raw_size_event_count_and_depth_limits_refuse_atomically(tmp_path: Path) -> None:
    oversized = b"x" * 262_145
    _assert_contract_refusal(tmp_path / "size", oversized, CONTRACT_LIMIT_ERROR)

    too_many_events = b"events: [" + (b"x," * 65_537) + b"]\n"
    _assert_contract_refusal(tmp_path / "events", too_many_events, CONTRACT_LIMIT_ERROR)

    too_deep = b"value: " + (b"[" * 17) + b"x" + (b"]" * 17) + b"\n"
    _assert_contract_refusal(tmp_path / "depth", too_deep, CONTRACT_LIMIT_ERROR)


def test_record_enum_field_and_member_meta_model_ceilings_refuse(tmp_path: Path) -> None:
    records = _canonical_document()
    for record_index in range(EXTRA_RECORD_DECLARATIONS):
        records["records"][f"ExtraRecord{record_index}"] = {"fields": []}
    _assert_contract_refusal(tmp_path / "records", _dump_contract(records), CONTRACT_LIMIT_ERROR)

    enums = _canonical_document()
    for enum_index in range(EXTRA_ENUM_DECLARATIONS):
        enums["enums"][f"ExtraEnum{enum_index}"] = []
    _assert_contract_refusal(tmp_path / "enums", _dump_contract(enums), CONTRACT_LIMIT_ERROR)

    fields = _canonical_document()
    for field_index in range(EXTRA_FIELD_DECLARATIONS):
        fields["records"]["TypedIdentityV1"]["fields"].append(
            {"name": f"extra_{field_index}", "type": "string"}
        )
    _assert_contract_refusal(tmp_path / "fields", _dump_contract(fields), CONTRACT_LIMIT_ERROR)

    members = _canonical_document()
    for member_index in range(EXTRA_ENUM_MEMBERS):
        members["enums"]["AudienceV1"].append(f"EXTRA_{member_index}")
    _assert_contract_refusal(tmp_path / "members", _dump_contract(members), CONTRACT_LIMIT_ERROR)


def test_limit_and_registry_row_meta_model_ceilings_refuse(tmp_path: Path) -> None:
    limits = _canonical_document()
    for limit_index in range(EXTRA_LIMIT_ROWS):
        limits["limits"][f"extra_limit_{limit_index}"] = limit_index
    _assert_contract_refusal(tmp_path / "limits", _dump_contract(limits), CONTRACT_LIMIT_ERROR)

    registry = _canonical_document()
    for metric_index in range(EXTRA_REGISTRY_ROWS):
        key = f"extra/metric-{metric_index}"
        registry["identity_registry"]["metrics"][key] = {
            "domain": "metric",
            "authority": "babylon.rtd.v1",
            "local_id": key,
        }
    _assert_contract_refusal(tmp_path / "registry", _dump_contract(registry), CONTRACT_LIMIT_ERROR)
