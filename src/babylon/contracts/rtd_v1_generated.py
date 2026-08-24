# Generated from contracts/relational_territory_dossier_v1.yaml; sha256=5f0e271d46783bd82fb5c9336c466f4c3631a499b43c83c11b854db23ea59e40
# fmt: off
from __future__ import annotations

from enum import StrEnum
from types import MappingProxyType
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class AudienceV1(StrEnum):
    ADMIN_MATERIAL = 'ADMIN_MATERIAL'
    PLAYER_KNOWLEDGE = 'PLAYER_KNOWLEDGE'


class DurabilityV1(StrEnum):
    IN_MEMORY = 'IN_MEMORY'
    COMMITTED = 'COMMITTED'


class EvidenceClassV1(StrEnum):
    Observed = 'Observed'
    Derived = 'Derived'
    Calibrated = 'Calibrated'
    Designed = 'Designed'


class StatusV1(StrEnum):
    PRESENT = 'PRESENT'
    ABSENT = 'ABSENT'
    UNKNOWN = 'UNKNOWN'
    NOT_COMPUTED = 'NOT_COMPUTED'
    REDACTED = 'REDACTED'


class ValueKindV1(StrEnum):
    UINT64_BITS = 'UINT64_BITS'
    FLOAT64_BITS = 'FLOAT64_BITS'


class CoverageV1(StrEnum):
    COMPLETE = 'COMPLETE'
    PARTIAL = 'PARTIAL'
    NOT_APPLICABLE = 'NOT_APPLICABLE'
    UNKNOWN = 'UNKNOWN'


class MembershipKindV1(StrEnum):
    ADMINISTRATIVE = 'ADMINISTRATIVE'
    NATIONAL = 'NATIONAL'
    COMMUTING_ZONE = 'COMMUTING_ZONE'
    METROPOLITAN = 'METROPOLITAN'
    WEIGHTED_OVERLAP = 'WEIGHTED_OVERLAP'


class FacetFamilyV1(StrEnum):
    COMMAND_ADMINISTRATION = 'COMMAND_ADMINISTRATION'
    PRODUCTION_CIRCULATION = 'PRODUCTION_CIRCULATION'
    REPRODUCTION_SETTLEMENT_ACCESS = 'REPRODUCTION_SETTLEMENT_ACCESS'
    EXTRACTION_ABANDONMENT_CARCERAL = 'EXTRACTION_ABANDONMENT_CARCERAL'
    ECOLOGY_CARE = 'ECOLOGY_CARE'
    ORGANIZATION_ROOTEDNESS = 'ORGANIZATION_ROOTEDNESS'


class DyadKindV1(StrEnum):
    PRESENCE = 'PRESENCE'
    MEMBERSHIP = 'MEMBERSHIP'
    SOLIDARITY = 'SOLIDARITY'
    COMMAND = 'COMMAND'


class HyperedgeKindV1(StrEnum):
    PUBLIC_RELATION = 'PUBLIC_RELATION'


class FlowKindV1(StrEnum):
    COMMUTER_JOBS = 'COMMUTER_JOBS'
    BORDER_SYNTHESIS = 'BORDER_SYNTHESIS'


class RelationPayloadModeV1(StrEnum):
    EMPTY = 'EMPTY'
    SINGLE_METRIC_FACET = 'SINGLE_METRIC_FACET'
    IMPLICIT_RELATION = 'IMPLICIT_RELATION'


class GapReasonV1(StrEnum):
    MISSING_GOVERNED_OMB_DELINEATION = 'MISSING_GOVERNED_OMB_DELINEATION'
    IDENTITY_CONTRACT_PENDING = 'IDENTITY_CONTRACT_PENDING'
    MISSING_GOVERNED_PRODUCER = 'MISSING_GOVERNED_PRODUCER'
    REFERENCE_COVERAGE_UNAVAILABLE = 'REFERENCE_COVERAGE_UNAVAILABLE'
    PLAYER_BOUNDARY_UNAVAILABLE = 'PLAYER_BOUNDARY_UNAVAILABLE'
    PROVENANCE_COORDINATE_CONFLICT = 'PROVENANCE_COORDINATE_CONFLICT'


class MetricRepresentationV1(StrEnum):
    FACET = 'FACET'
    REFERENCE_FLOW = 'REFERENCE_FLOW'
    DYAD = 'DYAD'


class AggregationRuleV1(StrEnum):
    NONE = 'NONE'
    PUBLISHED_ROLLUP = 'PUBLISHED_ROLLUP'
    LOAD_TIME_SUM = 'LOAD_TIME_SUM'
    BLOCK_INTERNAL_POINT_ASSIGNMENT = 'BLOCK_INTERNAL_POINT_ASSIGNMENT'
    BLOCK_COORDINATE_ASSIGNMENT = 'BLOCK_COORDINATE_ASSIGNMENT'
    EQUAL_AREA_WATER_INTERSECTION = 'EQUAL_AREA_WATER_INTERSECTION'
    TYPED_RELATION_PROJECTION = 'TYPED_RELATION_PROJECTION'


class RtdCollectionKindV1(StrEnum):
    FOCUS = 'FOCUS'
    REFERENCE_DIGESTS = 'REFERENCE_DIGESTS'
    SCALE_MEMBERSHIPS = 'SCALE_MEMBERSHIPS'
    FACETS = 'FACETS'
    DYADS = 'DYADS'
    HYPEREDGES = 'HYPEREDGES'
    FLOWS = 'FLOWS'
    GAPS = 'GAPS'
    PROVENANCE = 'PROVENANCE'
    COORDINATES = 'COORDINATES'
    MEMBER_REFS = 'MEMBER_REFS'
    PAYLOAD_FACETS = 'PAYLOAD_FACETS'
    DISPLAY_REFS = 'DISPLAY_REFS'
    PROVENANCE_REFS = 'PROVENANCE_REFS'


class TypedIdentityV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    domain: str
    authority: str
    local_id: str


class ReferenceDigestV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    reference_id: TypedIdentityV1
    sha256_hex: str
    artifact_schema_id_or_null: TypedIdentityV1 | None
    vintage: str
    evidence_class: EvidenceClassV1


class DimensionCoordinateV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    dimension_ref: TypedIdentityV1
    member_ref: TypedIdentityV1


class ScaleMembershipV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    membership_id: TypedIdentityV1
    member_ref: TypedIdentityV1
    scale_ref: TypedIdentityV1
    membership_kind: MembershipKindV1
    status: StatusV1
    weight_status: StatusV1
    weight_bits_or_null: str | None
    coverage: CoverageV1
    evidence_class: EvidenceClassV1
    provenance_refs: tuple[TypedIdentityV1, ...]


class FacetV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    facet_id: TypedIdentityV1
    family: FacetFamilyV1
    subject_ref: TypedIdentityV1
    metric_id: TypedIdentityV1
    unit_id: TypedIdentityV1
    native_scale: TypedIdentityV1
    coordinates: tuple[DimensionCoordinateV1, ...]
    vintage: str
    status: StatusV1
    value_kind: ValueKindV1
    value_bits_or_null: str | None
    coverage: CoverageV1
    evidence_class: EvidenceClassV1
    provenance_refs: tuple[TypedIdentityV1, ...]


class DyadV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    relation_id: TypedIdentityV1
    relation_kind: DyadKindV1
    from_ref: TypedIdentityV1
    to_ref: TypedIdentityV1
    native_scale: TypedIdentityV1
    status: StatusV1
    coverage: CoverageV1
    payload_facets: tuple[TypedIdentityV1, ...]
    evidence_class: EvidenceClassV1
    provenance_refs: tuple[TypedIdentityV1, ...]


class HyperedgeV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    hyperedge_id: TypedIdentityV1
    hyperedge_kind: HyperedgeKindV1
    member_refs: tuple[TypedIdentityV1, ...]
    native_scale: TypedIdentityV1
    status: StatusV1
    coverage: CoverageV1
    payload_facets: tuple[TypedIdentityV1, ...]
    evidence_class: EvidenceClassV1
    provenance_refs: tuple[TypedIdentityV1, ...]


class ReferenceFlowV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    flow_id: TypedIdentityV1
    flow_kind: FlowKindV1
    origin_ref: TypedIdentityV1
    destination_ref: TypedIdentityV1
    payload_facets: tuple[TypedIdentityV1, ...]
    native_scale: TypedIdentityV1
    status: StatusV1
    coverage: CoverageV1
    evidence_class: EvidenceClassV1
    provenance_refs: tuple[TypedIdentityV1, ...]


class GapV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    gap_id: TypedIdentityV1
    requested_metric_or_relation: TypedIdentityV1
    status: StatusV1
    reason_code: GapReasonV1
    required_producer_or_null: str | None
    provenance_refs: tuple[TypedIdentityV1, ...]


class ProvenanceV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    provenance_id: TypedIdentityV1
    artifact_digest: str
    locator: str
    vintage: str
    evidence_class: EvidenceClassV1
    transformation_digest_or_null: str | None


class DecisionSurfaceV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    question_id: TypedIdentityV1
    signal_refs: tuple[TypedIdentityV1, ...]
    action_refs: tuple[TypedIdentityV1, ...]
    receipt_refs: tuple[TypedIdentityV1, ...]
    archive_subject_refs: tuple[TypedIdentityV1, ...]


class RtdDossierDraftV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_: str = Field(alias="schema", serialization_alias="schema")
    schema_version: Annotated[int, Field(strict=True, ge=0, le=65_535)]
    projection_version: Annotated[int, Field(strict=True, ge=0, le=65_535)]
    audience: AudienceV1
    durability: DurabilityV1
    verified_tick: Annotated[int, Field(strict=True, ge=0, le=18_446_744_073_709_551_615)]
    graph_state_hash: str
    nominal_world_hash: str
    reference_digests: tuple[ReferenceDigestV1, ...]
    definitions_digest: str
    template_digest: str
    fog_policy_digest: str | None
    knowledge_context_digest: str | None
    actor: TypedIdentityV1 | None
    focus: tuple[TypedIdentityV1, ...]
    scale_memberships: tuple[ScaleMembershipV1, ...]
    facets: tuple[FacetV1, ...]
    dyads: tuple[DyadV1, ...]
    hyperedges: tuple[HyperedgeV1, ...]
    flows: tuple[ReferenceFlowV1, ...]
    gaps: tuple[GapV1, ...]
    provenance: tuple[ProvenanceV1, ...]
    decision_surface: DecisionSurfaceV1


class RelationalTerritoryDossierV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_: str = Field(alias="schema", serialization_alias="schema")
    schema_version: Annotated[int, Field(strict=True, ge=0, le=65_535)]
    projection_version: Annotated[int, Field(strict=True, ge=0, le=65_535)]
    audience: AudienceV1
    durability: DurabilityV1
    verified_tick: Annotated[int, Field(strict=True, ge=0, le=18_446_744_073_709_551_615)]
    graph_state_hash: str
    nominal_world_hash: str
    reference_digests: tuple[ReferenceDigestV1, ...]
    definitions_digest: str
    template_digest: str
    fog_policy_digest: str | None
    knowledge_context_digest: str | None
    actor: TypedIdentityV1 | None
    focus: tuple[TypedIdentityV1, ...]
    scale_memberships: tuple[ScaleMembershipV1, ...]
    facets: tuple[FacetV1, ...]
    dyads: tuple[DyadV1, ...]
    hyperedges: tuple[HyperedgeV1, ...]
    flows: tuple[ReferenceFlowV1, ...]
    gaps: tuple[GapV1, ...]
    provenance: tuple[ProvenanceV1, ...]
    decision_surface: DecisionSurfaceV1
    projection_hash: str


class RtdIdentityRegistryRowV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    category: str
    symbolic_name: str
    identity: TypedIdentityV1

class RtdMetricRegistryRowV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    metric: TypedIdentityV1
    representation: MetricRepresentationV1
    unit: TypedIdentityV1
    value_kind: ValueKindV1 | None
    native_scale: TypedIdentityV1
    coordinates: tuple[TypedIdentityV1, ...]
    evidence_classes: tuple[EvidenceClassV1, ...]
    aggregation_rule: AggregationRuleV1
    producer: TypedIdentityV1
    reference_artifact: TypedIdentityV1 | None
    reference_digest: str | None

class RtdRelationBindingRegistryRowV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    record_family: str
    kind: str
    metric: TypedIdentityV1 | None
    payload_mode: RelationPayloadModeV1

RTD_V1_SCHEMA_ID = 'babylon.relational-territory-dossier'
RTD_V1_LIMITS = MappingProxyType({
    'max_collection_items': 65535,
    'max_focus': 64,
    'max_reference_digests': 4096,
    'max_scale_memberships': 65535,
    'max_facets': 65535,
    'max_dyads': 65535,
    'max_hyperedges': 65535,
    'max_flows': 65535,
    'max_gaps': 65535,
    'max_provenance': 65535,
    'max_coordinates': 32,
    'max_hyperedge_members': 1024,
    'max_payload_facets': 256,
    'max_decision_surface_refs': 256,
    'max_provenance_refs': 8192,
    'max_identity_component_bytes': 256,
    'max_vintage_bytes': 256,
    'max_provenance_locator_bytes': 1024,
    'max_required_producer_bytes': 64,
    'max_canonical_bytes': 67108864,
})
RTD_V1_ERROR_REGISTRY = ('RTD_JSON', 'RTD_JSON_DEPTH', 'RTD_SCHEMA_VERSION', 'RTD_UNKNOWN_FIELD', 'RTD_ENUM', 'RTD_IDENTITY', 'RTD_DIGEST', 'RTD_NON_NFC', 'RTD_LIMIT_EXCEEDED', 'RTD_DUPLICATE_KEY', 'RTD_DANGLING_REF', 'RTD_STATUS_VALUE', 'RTD_NATIVE_GRAIN', 'RTD_UNSUPPORTED_DOWNSCALE', 'RTD_H3_BEFORE_PER21', 'RTD_MSA_EVIDENCE', 'RTD_CANADA_CONTROL', 'RTD_FORBIDDEN_REDUCTION', 'RTD_VECTOR_LIMIT', 'RTD_CANONICAL_SIZE')

RTD_V1_IDENTITY_REGISTRY = (
    RtdIdentityRegistryRowV1(category='metrics', symbolic_name='production/qcew-leaf-employment', identity=TypedIdentityV1(domain='metric', authority='babylon.rtd.v1', local_id='production/qcew-leaf-employment')),
    RtdIdentityRegistryRowV1(category='metrics', symbolic_name='production/qcew-leaf-establishments', identity=TypedIdentityV1(domain='metric', authority='babylon.rtd.v1', local_id='production/qcew-leaf-establishments')),
    RtdIdentityRegistryRowV1(category='metrics', symbolic_name='production/qcew-leaf-total-wages-usd', identity=TypedIdentityV1(domain='metric', authority='babylon.rtd.v1', local_id='production/qcew-leaf-total-wages-usd')),
    RtdIdentityRegistryRowV1(category='metrics', symbolic_name='production/qcew-leaf-average-annual-pay-usd', identity=TypedIdentityV1(domain='metric', authority='babylon.rtd.v1', local_id='production/qcew-leaf-average-annual-pay-usd')),
    RtdIdentityRegistryRowV1(category='metrics', symbolic_name='production/qcew-county-employment', identity=TypedIdentityV1(domain='metric', authority='babylon.rtd.v1', local_id='production/qcew-county-employment')),
    RtdIdentityRegistryRowV1(category='metrics', symbolic_name='production/qcew-county-establishments', identity=TypedIdentityV1(domain='metric', authority='babylon.rtd.v1', local_id='production/qcew-county-establishments')),
    RtdIdentityRegistryRowV1(category='metrics', symbolic_name='production/qcew-county-total-wages-usd', identity=TypedIdentityV1(domain='metric', authority='babylon.rtd.v1', local_id='production/qcew-county-total-wages-usd')),
    RtdIdentityRegistryRowV1(category='metrics', symbolic_name='circulation/lodes-county-commuter-total-jobs', identity=TypedIdentityV1(domain='metric', authority='babylon.rtd.v1', local_id='circulation/lodes-county-commuter-total-jobs')),
    RtdIdentityRegistryRowV1(category='metrics', symbolic_name='reproduction/census-housing-households', identity=TypedIdentityV1(domain='metric', authority='babylon.rtd.v1', local_id='reproduction/census-housing-households')),
    RtdIdentityRegistryRowV1(category='metrics', symbolic_name='reproduction/census-median-rent-usd', identity=TypedIdentityV1(domain='metric', authority='babylon.rtd.v1', local_id='reproduction/census-median-rent-usd')),
    RtdIdentityRegistryRowV1(category='metrics', symbolic_name='reproduction/census-rent-burden-households', identity=TypedIdentityV1(domain='metric', authority='babylon.rtd.v1', local_id='reproduction/census-rent-burden-households')),
    RtdIdentityRegistryRowV1(category='metrics', symbolic_name='reproduction/h3-population-persons', identity=TypedIdentityV1(domain='metric', authority='babylon.rtd.v1', local_id='reproduction/h3-population-persons')),
    RtdIdentityRegistryRowV1(category='metrics', symbolic_name='production/h3-workplace-jobs', identity=TypedIdentityV1(domain='metric', authority='babylon.rtd.v1', local_id='production/h3-workplace-jobs')),
    RtdIdentityRegistryRowV1(category='metrics', symbolic_name='carceral/facility-count', identity=TypedIdentityV1(domain='metric', authority='babylon.rtd.v1', local_id='carceral/facility-count')),
    RtdIdentityRegistryRowV1(category='metrics', symbolic_name='ecology/h3-land-fraction', identity=TypedIdentityV1(domain='metric', authority='babylon.rtd.v1', local_id='ecology/h3-land-fraction')),
    RtdIdentityRegistryRowV1(category='metrics', symbolic_name='rootedness/presence', identity=TypedIdentityV1(domain='metric', authority='babylon.rtd.v1', local_id='rootedness/presence')),
    RtdIdentityRegistryRowV1(category='metrics', symbolic_name='rootedness/solidarity', identity=TypedIdentityV1(domain='metric', authority='babylon.rtd.v1', local_id='rootedness/solidarity')),
    RtdIdentityRegistryRowV1(category='metrics', symbolic_name='rootedness/membership', identity=TypedIdentityV1(domain='metric', authority='babylon.rtd.v1', local_id='rootedness/membership')),
    RtdIdentityRegistryRowV1(category='units', symbolic_name='JOBS', identity=TypedIdentityV1(domain='unit', authority='babylon.rtd.v1', local_id='jobs')),
    RtdIdentityRegistryRowV1(category='units', symbolic_name='ESTABLISHMENTS', identity=TypedIdentityV1(domain='unit', authority='babylon.rtd.v1', local_id='establishments')),
    RtdIdentityRegistryRowV1(category='units', symbolic_name='USD_CURRENT', identity=TypedIdentityV1(domain='unit', authority='babylon.rtd.v1', local_id='usd-current')),
    RtdIdentityRegistryRowV1(category='units', symbolic_name='HOUSEHOLDS', identity=TypedIdentityV1(domain='unit', authority='babylon.rtd.v1', local_id='households')),
    RtdIdentityRegistryRowV1(category='units', symbolic_name='PERSONS', identity=TypedIdentityV1(domain='unit', authority='babylon.rtd.v1', local_id='persons')),
    RtdIdentityRegistryRowV1(category='units', symbolic_name='FACILITIES', identity=TypedIdentityV1(domain='unit', authority='babylon.rtd.v1', local_id='facilities')),
    RtdIdentityRegistryRowV1(category='units', symbolic_name='FRACTION', identity=TypedIdentityV1(domain='unit', authority='babylon.rtd.v1', local_id='fraction')),
    RtdIdentityRegistryRowV1(category='units', symbolic_name='TYPED_RELATION', identity=TypedIdentityV1(domain='unit', authority='babylon.rtd.v1', local_id='typed-relation')),
    RtdIdentityRegistryRowV1(category='coordinates', symbolic_name='county', identity=TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='county')),
    RtdIdentityRegistryRowV1(category='coordinates', symbolic_name='naics6', identity=TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='naics6')),
    RtdIdentityRegistryRowV1(category='coordinates', symbolic_name='ownership', identity=TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='ownership')),
    RtdIdentityRegistryRowV1(category='coordinates', symbolic_name='home_county', identity=TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='home-county')),
    RtdIdentityRegistryRowV1(category='coordinates', symbolic_name='work_county', identity=TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='work-county')),
    RtdIdentityRegistryRowV1(category='coordinates', symbolic_name='source', identity=TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='source')),
    RtdIdentityRegistryRowV1(category='coordinates', symbolic_name='tenure', identity=TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='tenure')),
    RtdIdentityRegistryRowV1(category='coordinates', symbolic_name='race', identity=TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='race')),
    RtdIdentityRegistryRowV1(category='coordinates', symbolic_name='burden', identity=TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='burden')),
    RtdIdentityRegistryRowV1(category='coordinates', symbolic_name='h3_cell', identity=TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='h3-cell')),
    RtdIdentityRegistryRowV1(category='coordinates', symbolic_name='coercive_type', identity=TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='coercive-type')),
    RtdIdentityRegistryRowV1(category='coordinates', symbolic_name='actor', identity=TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='actor')),
    RtdIdentityRegistryRowV1(category='coordinates', symbolic_name='node', identity=TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='node')),
    RtdIdentityRegistryRowV1(category='native_scales', symbolic_name='COUNTY_NAICS6_OWNERSHIP_YEAR', identity=TypedIdentityV1(domain='native-scale', authority='babylon.rtd.v1', local_id='county-naics6-ownership-year')),
    RtdIdentityRegistryRowV1(category='native_scales', symbolic_name='COUNTY_OWNERSHIP_YEAR', identity=TypedIdentityV1(domain='native-scale', authority='babylon.rtd.v1', local_id='county-ownership-year')),
    RtdIdentityRegistryRowV1(category='native_scales', symbolic_name='HOME_COUNTY_WORK_COUNTY_YEAR', identity=TypedIdentityV1(domain='native-scale', authority='babylon.rtd.v1', local_id='home-county-work-county-year')),
    RtdIdentityRegistryRowV1(category='native_scales', symbolic_name='COUNTY_SOURCE_TENURE_TIME_RACE', identity=TypedIdentityV1(domain='native-scale', authority='babylon.rtd.v1', local_id='county-source-tenure-time-race')),
    RtdIdentityRegistryRowV1(category='native_scales', symbolic_name='COUNTY_SOURCE_TIME_RACE', identity=TypedIdentityV1(domain='native-scale', authority='babylon.rtd.v1', local_id='county-source-time-race')),
    RtdIdentityRegistryRowV1(category='native_scales', symbolic_name='COUNTY_SOURCE_BURDEN_TIME_RACE', identity=TypedIdentityV1(domain='native-scale', authority='babylon.rtd.v1', local_id='county-source-burden-time-race')),
    RtdIdentityRegistryRowV1(category='native_scales', symbolic_name='H3_R7_VINTAGE', identity=TypedIdentityV1(domain='native-scale', authority='babylon.rtd.v1', local_id='h3-r7-vintage')),
    RtdIdentityRegistryRowV1(category='native_scales', symbolic_name='COUNTY_COERCIVE_TYPE_SOURCE', identity=TypedIdentityV1(domain='native-scale', authority='babylon.rtd.v1', local_id='county-coercive-type-source')),
    RtdIdentityRegistryRowV1(category='native_scales', symbolic_name='ACTOR_NODE_VERIFIED_TICK', identity=TypedIdentityV1(domain='native-scale', authority='babylon.rtd.v1', local_id='actor-node-verified-tick')),
    RtdIdentityRegistryRowV1(category='producers', symbolic_name='fact_qcew_annual', identity=TypedIdentityV1(domain='producer', authority='babylon.data.v7', local_id='fact_qcew_annual')),
    RtdIdentityRegistryRowV1(category='producers', symbolic_name='fact_qcew_county_rollup', identity=TypedIdentityV1(domain='producer', authority='babylon.data.v7', local_id='fact_qcew_county_rollup')),
    RtdIdentityRegistryRowV1(category='producers', symbolic_name='fact_lodes_commuter_flow', identity=TypedIdentityV1(domain='producer', authority='babylon.data.v7', local_id='fact_lodes_commuter_flow')),
    RtdIdentityRegistryRowV1(category='producers', symbolic_name='fact_census_housing', identity=TypedIdentityV1(domain='producer', authority='babylon.data.v7', local_id='fact_census_housing')),
    RtdIdentityRegistryRowV1(category='producers', symbolic_name='fact_census_rent', identity=TypedIdentityV1(domain='producer', authority='babylon.data.v7', local_id='fact_census_rent')),
    RtdIdentityRegistryRowV1(category='producers', symbolic_name='fact_census_rent_burden', identity=TypedIdentityV1(domain='producer', authority='babylon.data.v7', local_id='fact_census_rent_burden')),
    RtdIdentityRegistryRowV1(category='producers', symbolic_name='h3_res7_population', identity=TypedIdentityV1(domain='producer', authority='babylon.data.v7', local_id='h3_res7_population')),
    RtdIdentityRegistryRowV1(category='producers', symbolic_name='h3_res7_workplace', identity=TypedIdentityV1(domain='producer', authority='babylon.data.v7', local_id='h3_res7_workplace')),
    RtdIdentityRegistryRowV1(category='producers', symbolic_name='fact_coercive_infrastructure', identity=TypedIdentityV1(domain='producer', authority='babylon.data.v7', local_id='fact_coercive_infrastructure')),
    RtdIdentityRegistryRowV1(category='producers', symbolic_name='h3_res7_land_mask', identity=TypedIdentityV1(domain='producer', authority='babylon.data.v7', local_id='h3_res7_land_mask')),
    RtdIdentityRegistryRowV1(category='producers', symbolic_name='committed typed graph', identity=TypedIdentityV1(domain='producer', authority='babylon.engine', local_id='typed-graph-relations-at-verified-tick')),
    RtdIdentityRegistryRowV1(category='references', symbolic_name='fact_qcew_annual', identity=TypedIdentityV1(domain='reference-artifact', authority='babylon.data.v7', local_id='fact_qcew_annual')),
    RtdIdentityRegistryRowV1(category='references', symbolic_name='fact_qcew_county_rollup', identity=TypedIdentityV1(domain='reference-artifact', authority='babylon.data.v7', local_id='fact_qcew_county_rollup')),
    RtdIdentityRegistryRowV1(category='references', symbolic_name='fact_lodes_commuter_flow', identity=TypedIdentityV1(domain='reference-artifact', authority='babylon.data.v7', local_id='fact_lodes_commuter_flow')),
    RtdIdentityRegistryRowV1(category='references', symbolic_name='fact_census_housing', identity=TypedIdentityV1(domain='reference-artifact', authority='babylon.data.v7', local_id='fact_census_housing')),
    RtdIdentityRegistryRowV1(category='references', symbolic_name='fact_census_rent', identity=TypedIdentityV1(domain='reference-artifact', authority='babylon.data.v7', local_id='fact_census_rent')),
    RtdIdentityRegistryRowV1(category='references', symbolic_name='fact_census_rent_burden', identity=TypedIdentityV1(domain='reference-artifact', authority='babylon.data.v7', local_id='fact_census_rent_burden')),
    RtdIdentityRegistryRowV1(category='references', symbolic_name='h3_res7_population', identity=TypedIdentityV1(domain='reference-artifact', authority='babylon.data.v7', local_id='h3_res7_population')),
    RtdIdentityRegistryRowV1(category='references', symbolic_name='h3_res7_workplace', identity=TypedIdentityV1(domain='reference-artifact', authority='babylon.data.v7', local_id='h3_res7_workplace')),
    RtdIdentityRegistryRowV1(category='references', symbolic_name='fact_coercive_infrastructure', identity=TypedIdentityV1(domain='reference-artifact', authority='babylon.data.v7', local_id='fact_coercive_infrastructure')),
    RtdIdentityRegistryRowV1(category='references', symbolic_name='h3_res7_land_mask', identity=TypedIdentityV1(domain='reference-artifact', authority='babylon.data.v7', local_id='h3_res7_land_mask')),
)

RTD_V1_METRIC_REGISTRY = (
    RtdMetricRegistryRowV1(
        metric=TypedIdentityV1(domain='metric', authority='babylon.rtd.v1', local_id='production/qcew-leaf-employment'),
        representation=MetricRepresentationV1.FACET,
        unit=TypedIdentityV1(domain='unit', authority='babylon.rtd.v1', local_id='jobs'),
        value_kind=ValueKindV1.UINT64_BITS,
        native_scale=TypedIdentityV1(domain='native-scale', authority='babylon.rtd.v1', local_id='county-naics6-ownership-year'),
        coordinates=(TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='county'), TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='naics6'), TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='ownership'),),
        evidence_classes=(EvidenceClassV1.Observed, EvidenceClassV1.Derived,),
        aggregation_rule=AggregationRuleV1.NONE,
        producer=TypedIdentityV1(domain='producer', authority='babylon.data.v7', local_id='fact_qcew_annual'),
        reference_artifact=TypedIdentityV1(domain='reference-artifact', authority='babylon.data.v7', local_id='fact_qcew_annual'),
        reference_digest='ca3825a3d60831479313632073b7fc9a941d57dcf9b8940181c4713b6d442248',
    ),
    RtdMetricRegistryRowV1(
        metric=TypedIdentityV1(domain='metric', authority='babylon.rtd.v1', local_id='production/qcew-leaf-establishments'),
        representation=MetricRepresentationV1.FACET,
        unit=TypedIdentityV1(domain='unit', authority='babylon.rtd.v1', local_id='establishments'),
        value_kind=ValueKindV1.UINT64_BITS,
        native_scale=TypedIdentityV1(domain='native-scale', authority='babylon.rtd.v1', local_id='county-naics6-ownership-year'),
        coordinates=(TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='county'), TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='naics6'), TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='ownership'),),
        evidence_classes=(EvidenceClassV1.Observed, EvidenceClassV1.Derived,),
        aggregation_rule=AggregationRuleV1.NONE,
        producer=TypedIdentityV1(domain='producer', authority='babylon.data.v7', local_id='fact_qcew_annual'),
        reference_artifact=TypedIdentityV1(domain='reference-artifact', authority='babylon.data.v7', local_id='fact_qcew_annual'),
        reference_digest='ca3825a3d60831479313632073b7fc9a941d57dcf9b8940181c4713b6d442248',
    ),
    RtdMetricRegistryRowV1(
        metric=TypedIdentityV1(domain='metric', authority='babylon.rtd.v1', local_id='production/qcew-leaf-total-wages-usd'),
        representation=MetricRepresentationV1.FACET,
        unit=TypedIdentityV1(domain='unit', authority='babylon.rtd.v1', local_id='usd-current'),
        value_kind=ValueKindV1.FLOAT64_BITS,
        native_scale=TypedIdentityV1(domain='native-scale', authority='babylon.rtd.v1', local_id='county-naics6-ownership-year'),
        coordinates=(TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='county'), TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='naics6'), TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='ownership'),),
        evidence_classes=(EvidenceClassV1.Observed, EvidenceClassV1.Derived,),
        aggregation_rule=AggregationRuleV1.NONE,
        producer=TypedIdentityV1(domain='producer', authority='babylon.data.v7', local_id='fact_qcew_annual'),
        reference_artifact=TypedIdentityV1(domain='reference-artifact', authority='babylon.data.v7', local_id='fact_qcew_annual'),
        reference_digest='ca3825a3d60831479313632073b7fc9a941d57dcf9b8940181c4713b6d442248',
    ),
    RtdMetricRegistryRowV1(
        metric=TypedIdentityV1(domain='metric', authority='babylon.rtd.v1', local_id='production/qcew-leaf-average-annual-pay-usd'),
        representation=MetricRepresentationV1.FACET,
        unit=TypedIdentityV1(domain='unit', authority='babylon.rtd.v1', local_id='usd-current'),
        value_kind=ValueKindV1.FLOAT64_BITS,
        native_scale=TypedIdentityV1(domain='native-scale', authority='babylon.rtd.v1', local_id='county-naics6-ownership-year'),
        coordinates=(TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='county'), TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='naics6'), TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='ownership'),),
        evidence_classes=(EvidenceClassV1.Observed, EvidenceClassV1.Derived,),
        aggregation_rule=AggregationRuleV1.NONE,
        producer=TypedIdentityV1(domain='producer', authority='babylon.data.v7', local_id='fact_qcew_annual'),
        reference_artifact=TypedIdentityV1(domain='reference-artifact', authority='babylon.data.v7', local_id='fact_qcew_annual'),
        reference_digest='ca3825a3d60831479313632073b7fc9a941d57dcf9b8940181c4713b6d442248',
    ),
    RtdMetricRegistryRowV1(
        metric=TypedIdentityV1(domain='metric', authority='babylon.rtd.v1', local_id='production/qcew-county-employment'),
        representation=MetricRepresentationV1.FACET,
        unit=TypedIdentityV1(domain='unit', authority='babylon.rtd.v1', local_id='jobs'),
        value_kind=ValueKindV1.UINT64_BITS,
        native_scale=TypedIdentityV1(domain='native-scale', authority='babylon.rtd.v1', local_id='county-ownership-year'),
        coordinates=(TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='county'), TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='ownership'),),
        evidence_classes=(EvidenceClassV1.Observed, EvidenceClassV1.Derived,),
        aggregation_rule=AggregationRuleV1.PUBLISHED_ROLLUP,
        producer=TypedIdentityV1(domain='producer', authority='babylon.data.v7', local_id='fact_qcew_county_rollup'),
        reference_artifact=TypedIdentityV1(domain='reference-artifact', authority='babylon.data.v7', local_id='fact_qcew_county_rollup'),
        reference_digest='34c2bbb935f79b3c8076a97092b004b14cca120e8272b93c35b3ac9dc2721d13',
    ),
    RtdMetricRegistryRowV1(
        metric=TypedIdentityV1(domain='metric', authority='babylon.rtd.v1', local_id='production/qcew-county-establishments'),
        representation=MetricRepresentationV1.FACET,
        unit=TypedIdentityV1(domain='unit', authority='babylon.rtd.v1', local_id='establishments'),
        value_kind=ValueKindV1.UINT64_BITS,
        native_scale=TypedIdentityV1(domain='native-scale', authority='babylon.rtd.v1', local_id='county-ownership-year'),
        coordinates=(TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='county'), TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='ownership'),),
        evidence_classes=(EvidenceClassV1.Observed, EvidenceClassV1.Derived,),
        aggregation_rule=AggregationRuleV1.PUBLISHED_ROLLUP,
        producer=TypedIdentityV1(domain='producer', authority='babylon.data.v7', local_id='fact_qcew_county_rollup'),
        reference_artifact=TypedIdentityV1(domain='reference-artifact', authority='babylon.data.v7', local_id='fact_qcew_county_rollup'),
        reference_digest='34c2bbb935f79b3c8076a97092b004b14cca120e8272b93c35b3ac9dc2721d13',
    ),
    RtdMetricRegistryRowV1(
        metric=TypedIdentityV1(domain='metric', authority='babylon.rtd.v1', local_id='production/qcew-county-total-wages-usd'),
        representation=MetricRepresentationV1.FACET,
        unit=TypedIdentityV1(domain='unit', authority='babylon.rtd.v1', local_id='usd-current'),
        value_kind=ValueKindV1.FLOAT64_BITS,
        native_scale=TypedIdentityV1(domain='native-scale', authority='babylon.rtd.v1', local_id='county-ownership-year'),
        coordinates=(TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='county'), TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='ownership'),),
        evidence_classes=(EvidenceClassV1.Observed, EvidenceClassV1.Derived,),
        aggregation_rule=AggregationRuleV1.PUBLISHED_ROLLUP,
        producer=TypedIdentityV1(domain='producer', authority='babylon.data.v7', local_id='fact_qcew_county_rollup'),
        reference_artifact=TypedIdentityV1(domain='reference-artifact', authority='babylon.data.v7', local_id='fact_qcew_county_rollup'),
        reference_digest='34c2bbb935f79b3c8076a97092b004b14cca120e8272b93c35b3ac9dc2721d13',
    ),
    RtdMetricRegistryRowV1(
        metric=TypedIdentityV1(domain='metric', authority='babylon.rtd.v1', local_id='circulation/lodes-county-commuter-total-jobs'),
        representation=MetricRepresentationV1.REFERENCE_FLOW,
        unit=TypedIdentityV1(domain='unit', authority='babylon.rtd.v1', local_id='jobs'),
        value_kind=ValueKindV1.UINT64_BITS,
        native_scale=TypedIdentityV1(domain='native-scale', authority='babylon.rtd.v1', local_id='home-county-work-county-year'),
        coordinates=(TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='home-county'), TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='work-county'),),
        evidence_classes=(EvidenceClassV1.Derived,),
        aggregation_rule=AggregationRuleV1.LOAD_TIME_SUM,
        producer=TypedIdentityV1(domain='producer', authority='babylon.data.v7', local_id='fact_lodes_commuter_flow'),
        reference_artifact=TypedIdentityV1(domain='reference-artifact', authority='babylon.data.v7', local_id='fact_lodes_commuter_flow'),
        reference_digest='d3745f8def09cd8c7a38e1870e6ec2c1853e210b777d8e8358cfce36665bd64d',
    ),
    RtdMetricRegistryRowV1(
        metric=TypedIdentityV1(domain='metric', authority='babylon.rtd.v1', local_id='reproduction/census-housing-households'),
        representation=MetricRepresentationV1.FACET,
        unit=TypedIdentityV1(domain='unit', authority='babylon.rtd.v1', local_id='households'),
        value_kind=ValueKindV1.UINT64_BITS,
        native_scale=TypedIdentityV1(domain='native-scale', authority='babylon.rtd.v1', local_id='county-source-tenure-time-race'),
        coordinates=(TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='county'), TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='source'), TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='tenure'), TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='race'),),
        evidence_classes=(EvidenceClassV1.Observed,),
        aggregation_rule=AggregationRuleV1.NONE,
        producer=TypedIdentityV1(domain='producer', authority='babylon.data.v7', local_id='fact_census_housing'),
        reference_artifact=TypedIdentityV1(domain='reference-artifact', authority='babylon.data.v7', local_id='fact_census_housing'),
        reference_digest='09ff2d9666b3f5ef267b65cbc77c14e99384f0157b6a4c898ac37df2e67ca59f',
    ),
    RtdMetricRegistryRowV1(
        metric=TypedIdentityV1(domain='metric', authority='babylon.rtd.v1', local_id='reproduction/census-median-rent-usd'),
        representation=MetricRepresentationV1.FACET,
        unit=TypedIdentityV1(domain='unit', authority='babylon.rtd.v1', local_id='usd-current'),
        value_kind=ValueKindV1.FLOAT64_BITS,
        native_scale=TypedIdentityV1(domain='native-scale', authority='babylon.rtd.v1', local_id='county-source-time-race'),
        coordinates=(TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='county'), TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='source'), TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='race'),),
        evidence_classes=(EvidenceClassV1.Observed,),
        aggregation_rule=AggregationRuleV1.NONE,
        producer=TypedIdentityV1(domain='producer', authority='babylon.data.v7', local_id='fact_census_rent'),
        reference_artifact=TypedIdentityV1(domain='reference-artifact', authority='babylon.data.v7', local_id='fact_census_rent'),
        reference_digest='4c8cc134ec490ca75961d83485fc97c6bf240b32128e9d0517e00e62d578a99e',
    ),
    RtdMetricRegistryRowV1(
        metric=TypedIdentityV1(domain='metric', authority='babylon.rtd.v1', local_id='reproduction/census-rent-burden-households'),
        representation=MetricRepresentationV1.FACET,
        unit=TypedIdentityV1(domain='unit', authority='babylon.rtd.v1', local_id='households'),
        value_kind=ValueKindV1.UINT64_BITS,
        native_scale=TypedIdentityV1(domain='native-scale', authority='babylon.rtd.v1', local_id='county-source-burden-time-race'),
        coordinates=(TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='county'), TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='source'), TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='burden'), TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='race'),),
        evidence_classes=(EvidenceClassV1.Observed,),
        aggregation_rule=AggregationRuleV1.NONE,
        producer=TypedIdentityV1(domain='producer', authority='babylon.data.v7', local_id='fact_census_rent_burden'),
        reference_artifact=TypedIdentityV1(domain='reference-artifact', authority='babylon.data.v7', local_id='fact_census_rent_burden'),
        reference_digest='8a42a51c17bf3ebee09f0b0b5145d5c8253c7e3446eec8c75714f9951b20df12',
    ),
    RtdMetricRegistryRowV1(
        metric=TypedIdentityV1(domain='metric', authority='babylon.rtd.v1', local_id='reproduction/h3-population-persons'),
        representation=MetricRepresentationV1.FACET,
        unit=TypedIdentityV1(domain='unit', authority='babylon.rtd.v1', local_id='persons'),
        value_kind=ValueKindV1.UINT64_BITS,
        native_scale=TypedIdentityV1(domain='native-scale', authority='babylon.rtd.v1', local_id='h3-r7-vintage'),
        coordinates=(TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='h3-cell'),),
        evidence_classes=(EvidenceClassV1.Derived,),
        aggregation_rule=AggregationRuleV1.BLOCK_INTERNAL_POINT_ASSIGNMENT,
        producer=TypedIdentityV1(domain='producer', authority='babylon.data.v7', local_id='h3_res7_population'),
        reference_artifact=TypedIdentityV1(domain='reference-artifact', authority='babylon.data.v7', local_id='h3_res7_population'),
        reference_digest='b096a5891284f0ca55bedae9d1a9092eb8ea9e9e32d32b6ace430a9833b53afc',
    ),
    RtdMetricRegistryRowV1(
        metric=TypedIdentityV1(domain='metric', authority='babylon.rtd.v1', local_id='production/h3-workplace-jobs'),
        representation=MetricRepresentationV1.FACET,
        unit=TypedIdentityV1(domain='unit', authority='babylon.rtd.v1', local_id='jobs'),
        value_kind=ValueKindV1.UINT64_BITS,
        native_scale=TypedIdentityV1(domain='native-scale', authority='babylon.rtd.v1', local_id='h3-r7-vintage'),
        coordinates=(TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='h3-cell'),),
        evidence_classes=(EvidenceClassV1.Derived,),
        aggregation_rule=AggregationRuleV1.BLOCK_COORDINATE_ASSIGNMENT,
        producer=TypedIdentityV1(domain='producer', authority='babylon.data.v7', local_id='h3_res7_workplace'),
        reference_artifact=TypedIdentityV1(domain='reference-artifact', authority='babylon.data.v7', local_id='h3_res7_workplace'),
        reference_digest='ea2ce1508f4fe51f1e879b9f4a1daf579c4b00349388b12a85f884a8f49eabb6',
    ),
    RtdMetricRegistryRowV1(
        metric=TypedIdentityV1(domain='metric', authority='babylon.rtd.v1', local_id='carceral/facility-count'),
        representation=MetricRepresentationV1.FACET,
        unit=TypedIdentityV1(domain='unit', authority='babylon.rtd.v1', local_id='facilities'),
        value_kind=ValueKindV1.UINT64_BITS,
        native_scale=TypedIdentityV1(domain='native-scale', authority='babylon.rtd.v1', local_id='county-coercive-type-source'),
        coordinates=(TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='county'), TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='coercive-type'), TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='source'),),
        evidence_classes=(EvidenceClassV1.Observed,),
        aggregation_rule=AggregationRuleV1.NONE,
        producer=TypedIdentityV1(domain='producer', authority='babylon.data.v7', local_id='fact_coercive_infrastructure'),
        reference_artifact=TypedIdentityV1(domain='reference-artifact', authority='babylon.data.v7', local_id='fact_coercive_infrastructure'),
        reference_digest='33e6558d2b438e7aea672021f0e15f743f1ea331ab82407c0805a428b29cf808',
    ),
    RtdMetricRegistryRowV1(
        metric=TypedIdentityV1(domain='metric', authority='babylon.rtd.v1', local_id='ecology/h3-land-fraction'),
        representation=MetricRepresentationV1.FACET,
        unit=TypedIdentityV1(domain='unit', authority='babylon.rtd.v1', local_id='fraction'),
        value_kind=ValueKindV1.FLOAT64_BITS,
        native_scale=TypedIdentityV1(domain='native-scale', authority='babylon.rtd.v1', local_id='h3-r7-vintage'),
        coordinates=(TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='h3-cell'),),
        evidence_classes=(EvidenceClassV1.Derived,),
        aggregation_rule=AggregationRuleV1.EQUAL_AREA_WATER_INTERSECTION,
        producer=TypedIdentityV1(domain='producer', authority='babylon.data.v7', local_id='h3_res7_land_mask'),
        reference_artifact=TypedIdentityV1(domain='reference-artifact', authority='babylon.data.v7', local_id='h3_res7_land_mask'),
        reference_digest='4e6caba297f0111a9ec93d948a83543bb9f7179361fe5dd318bb8a98a5be5194',
    ),
    RtdMetricRegistryRowV1(
        metric=TypedIdentityV1(domain='metric', authority='babylon.rtd.v1', local_id='rootedness/presence'),
        representation=MetricRepresentationV1.DYAD,
        unit=TypedIdentityV1(domain='unit', authority='babylon.rtd.v1', local_id='typed-relation'),
        value_kind=None,
        native_scale=TypedIdentityV1(domain='native-scale', authority='babylon.rtd.v1', local_id='actor-node-verified-tick'),
        coordinates=(TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='actor'), TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='node'),),
        evidence_classes=(EvidenceClassV1.Derived,),
        aggregation_rule=AggregationRuleV1.TYPED_RELATION_PROJECTION,
        producer=TypedIdentityV1(domain='producer', authority='babylon.engine', local_id='typed-graph-relations-at-verified-tick'),
        reference_artifact=None,
        reference_digest=None,
    ),
    RtdMetricRegistryRowV1(
        metric=TypedIdentityV1(domain='metric', authority='babylon.rtd.v1', local_id='rootedness/solidarity'),
        representation=MetricRepresentationV1.DYAD,
        unit=TypedIdentityV1(domain='unit', authority='babylon.rtd.v1', local_id='typed-relation'),
        value_kind=None,
        native_scale=TypedIdentityV1(domain='native-scale', authority='babylon.rtd.v1', local_id='actor-node-verified-tick'),
        coordinates=(TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='actor'), TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='node'),),
        evidence_classes=(EvidenceClassV1.Derived,),
        aggregation_rule=AggregationRuleV1.TYPED_RELATION_PROJECTION,
        producer=TypedIdentityV1(domain='producer', authority='babylon.engine', local_id='typed-graph-relations-at-verified-tick'),
        reference_artifact=None,
        reference_digest=None,
    ),
    RtdMetricRegistryRowV1(
        metric=TypedIdentityV1(domain='metric', authority='babylon.rtd.v1', local_id='rootedness/membership'),
        representation=MetricRepresentationV1.DYAD,
        unit=TypedIdentityV1(domain='unit', authority='babylon.rtd.v1', local_id='typed-relation'),
        value_kind=None,
        native_scale=TypedIdentityV1(domain='native-scale', authority='babylon.rtd.v1', local_id='actor-node-verified-tick'),
        coordinates=(TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='actor'), TypedIdentityV1(domain='dimension', authority='babylon.rtd.v1', local_id='node'),),
        evidence_classes=(EvidenceClassV1.Derived,),
        aggregation_rule=AggregationRuleV1.TYPED_RELATION_PROJECTION,
        producer=TypedIdentityV1(domain='producer', authority='babylon.engine', local_id='typed-graph-relations-at-verified-tick'),
        reference_artifact=None,
        reference_digest=None,
    ),
)

RTD_V1_RELATION_BINDING_REGISTRY = (
    RtdRelationBindingRegistryRowV1(record_family='REFERENCE_FLOW', kind='COMMUTER_JOBS', metric=TypedIdentityV1(domain='metric', authority='babylon.rtd.v1', local_id='circulation/lodes-county-commuter-total-jobs'), payload_mode=RelationPayloadModeV1.SINGLE_METRIC_FACET),
    RtdRelationBindingRegistryRowV1(record_family='REFERENCE_FLOW', kind='BORDER_SYNTHESIS', metric=None, payload_mode=RelationPayloadModeV1.EMPTY),
    RtdRelationBindingRegistryRowV1(record_family='DYAD', kind='PRESENCE', metric=TypedIdentityV1(domain='metric', authority='babylon.rtd.v1', local_id='rootedness/presence'), payload_mode=RelationPayloadModeV1.IMPLICIT_RELATION),
    RtdRelationBindingRegistryRowV1(record_family='DYAD', kind='MEMBERSHIP', metric=TypedIdentityV1(domain='metric', authority='babylon.rtd.v1', local_id='rootedness/membership'), payload_mode=RelationPayloadModeV1.IMPLICIT_RELATION),
    RtdRelationBindingRegistryRowV1(record_family='DYAD', kind='SOLIDARITY', metric=TypedIdentityV1(domain='metric', authority='babylon.rtd.v1', local_id='rootedness/solidarity'), payload_mode=RelationPayloadModeV1.IMPLICIT_RELATION),
    RtdRelationBindingRegistryRowV1(record_family='DYAD', kind='COMMAND', metric=None, payload_mode=RelationPayloadModeV1.EMPTY),
)

# fmt: on
