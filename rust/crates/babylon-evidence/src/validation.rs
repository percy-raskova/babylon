//! Bounded validators for fixture-only governed manifests and proof cones.

use std::collections::BTreeSet;

use babylon_bsl::{canonical_bytes, SExpr, SfsRuleAuditResult};
use babylon_kernel::sha256_of;
use unicode_normalization::UnicodeNormalization;

use crate::{
    record_digest, CanonicalProfileSet, CausalConeV1, ComponentKindV1, Digest32, RunIdentityV1,
    SfsClassError, SfsComponentProofProfileV1, SfsProfileRecordError, SfsProofProfileV1,
    SfsRecordError, SfsWireError, SyntheticDriverContractError, SyntheticDriverError,
};

const MAX_GOVERNED_MANIFEST_BYTES: usize = 1_048_576;
const MAX_GOVERNED_MANIFEST_LINE_BYTES: usize = 131_682;
const MAX_COMPONENTS: usize = 64;
const MAX_PROFILE_ROWS: usize = 32_768;
const MAX_BOUND_ROWS: usize = 64;
const MAX_EDGES: usize = 4_096;
const MAX_SOURCE_BYTES: usize = 65_535;
const MAX_TOTAL_ROWS: usize = 36_992;
const GOVERNED_DOMAIN: &[u8] = b"babylon.sfs-synthetic-governed-manifest.v1";
const HOST_DOMAIN: &[u8] = b"babylon.sfs-synthetic-host-component-manifest.v1";
const COMPONENT_SOURCE_DOMAIN: &[u8] = b"babylon.sfs-synthetic-component-source.v1";
const MUTATION_DOMAIN: &[u8] = b"babylon.sfs-mutation-manifest.v1";
const MEMBERSHIP_DESCRIPTOR: &[u8] =
    b"membership-reducer maps one synthetic field value to one reducer output";
const PRODUCER_DESCRIPTOR: &[u8] =
    b"post-commit-producer emits one synthetic sample after a sealed envelope";
const EXPECTED_MUTATION_DIGEST: Digest32 = Digest32::from_bytes([
    0xe4, 0x7f, 0xf6, 0xd3, 0xcc, 0x00, 0x52, 0x45, 0xe3, 0x5b, 0xf3, 0x87, 0xb6, 0x7b, 0xdc, 0x00,
    0x87, 0xa1, 0xbb, 0xfb, 0x67, 0x72, 0xbc, 0xf4, 0x22, 0xe2, 0x84, 0xb6, 0xca, 0xd5, 0x12, 0x0d,
]);

/// One sealed producer-consumer channel row.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ProducerConsumerEdgeV1 {
    producer_id: String,
    consumer_id: String,
    channel_kind: SyntheticChannelKindV1,
    channel_id: String,
}

/// One governed synthetic component and its exact source binding.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SyntheticGovernedComponentV1 {
    component_id: String,
    component_kind: ComponentKindV1,
    component_source_digest: Digest32,
    source_mode: SourceMode,
    source_payload: Vec<u8>,
    canonical_row: Vec<u8>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
struct SyntheticProfileRowV1 {
    component_id: String,
    set_name: String,
    entry: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
struct SyntheticBoundRowV1 {
    component_id: String,
    declared_fuel: u64,
    computed_bound: u64,
    cardinality_digest: Digest32,
    intrinsic_cost_digest: Digest32,
}

/// Sealed manifest whose identities and admitted rows derive only from raw bytes.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SyntheticGovernedManifestV1 {
    canonical_bytes: Vec<u8>,
    manifest_digest: Digest32,
    host_component_manifest_digest: Digest32,
    components: Vec<SyntheticGovernedComponentV1>,
    edges: Vec<ProducerConsumerEdgeV1>,
    profile_rows: Vec<SyntheticProfileRowV1>,
    bound_rows: Vec<SyntheticBoundRowV1>,
}

/// Closed synthetic channel kinds.
#[repr(u8)]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SyntheticChannelKindV1 {
    Field = 0,
    Relation = 1,
    Contribution = 2,
    LedgerRow = 3,
    Receipt = 4,
    ReducerOutput = 5,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum SourceMode {
    CanonicalBsl,
    SyntheticDescriptor,
}

/// Exact synthetic validation refusals.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SfsValidationError {
    Wire(SfsWireError),
    Classifier(SfsClassError),
    Record(SfsRecordError),
    ProfileRecord(SfsProfileRecordError),
    GovernedManifestByteLimit {
        actual: usize,
    },
    GovernedManifestTotalRowLimit {
        actual: usize,
    },
    GovernedManifestLineLimit {
        row: usize,
        actual: usize,
    },
    ComponentLimit {
        actual: usize,
    },
    ProfileRowLimit {
        actual: usize,
    },
    BoundRowLimit {
        actual: usize,
    },
    EdgeLimit {
        actual: usize,
    },
    SourcePayloadLimit {
        component_id: String,
        actual: usize,
    },
    DuplicateComponentId {
        component_id: String,
    },
    DuplicateTypedEdge {
        producer_id: String,
        consumer_id: String,
        channel_id: String,
    },
    UnknownEdgeEndpoint {
        component_id: String,
    },
    UnknownConeEndpoint {
        set: &'static str,
        component_id: String,
    },
    NoRootToSinkPath,
    CausalConeDigestMismatch,
    GovernedComponentSetMismatch,
    ConeProfileMismatch,
    BoundDeclaredFuelMismatch,
    BoundComputedLimitMismatch,
    BoundCardinalityDigestMismatch,
    BoundIntrinsicCostDigestMismatch,
    EdgeProducerEffectMismatch {
        component_id: String,
        channel_id: String,
    },
    EdgeConsumerReadMismatch {
        component_id: String,
        channel_id: String,
    },
    MissingIncomingCausalEdge {
        component_id: String,
        entry: String,
    },
    MissingOutgoingCausalEdge {
        component_id: String,
        entry: String,
    },
    Driver(SyntheticDriverError),
    DriverContract(SyntheticDriverContractError),
    GovernedManifestMalformed {
        row: usize,
    },
    GovernedManifestDigestMismatch,
    HostManifestDigestMismatch,
    GovernedFootprintDigestMismatch,
    ProofProfileDigestMismatch,
    PreregistrationDigestMismatch,
    ComponentKindMismatch {
        component_id: String,
    },
    ComponentSourceDigestMismatch {
        component_id: String,
    },
    MutationManifestMalformed {
        row: usize,
    },
    MutationManifestDigestMismatch,
    MutationCoverageMismatch {
        mutation_id: String,
    },
}

impl From<SfsWireError> for SfsValidationError {
    fn from(value: SfsWireError) -> Self {
        Self::Wire(value)
    }
}

impl From<SfsProfileRecordError> for SfsValidationError {
    fn from(value: SfsProfileRecordError) -> Self {
        Self::ProfileRecord(value)
    }
}

impl ProducerConsumerEdgeV1 {
    /// Constructs one bounded NFC typed edge.
    ///
    /// # Errors
    /// Returns an exact NFC or length refusal.
    pub fn new(
        producer_id: &str,
        consumer_id: &str,
        channel_kind: SyntheticChannelKindV1,
        channel_id: &str,
    ) -> Result<Self, SfsValidationError> {
        validate_nfc(producer_id, 256, 0)?;
        validate_nfc(consumer_id, 256, 0)?;
        validate_nfc(channel_id, 96, 0)?;
        Ok(Self {
            producer_id: producer_id.to_owned(),
            consumer_id: consumer_id.to_owned(),
            channel_kind,
            channel_id: channel_id.to_owned(),
        })
    }
}

impl SyntheticGovernedComponentV1 {
    /// Constructs one digest-bound synthetic component descriptor.
    ///
    /// # Errors
    /// Returns an exact NFC or length refusal.
    pub fn new(
        component_id: &str,
        component_kind: ComponentKindV1,
        component_source_digest: Digest32,
    ) -> Result<Self, SfsValidationError> {
        validate_nfc(component_id, 256, 0)?;
        Ok(Self {
            component_id: component_id.to_owned(),
            component_kind,
            component_source_digest,
            source_mode: SourceMode::SyntheticDescriptor,
            source_payload: Vec::new(),
            canonical_row: Vec::new(),
        })
    }
}

impl SyntheticGovernedManifestV1 {
    #[must_use]
    pub const fn manifest_digest(&self) -> Digest32 {
        self.manifest_digest
    }

    #[must_use]
    pub const fn host_component_manifest_digest(&self) -> Digest32 {
        self.host_component_manifest_digest
    }
}

/// Parses, bounds, closes, and seals one exact synthetic governed manifest.
///
/// # Errors
/// Returns the first exact byte, row, source, bound, or closure refusal.
pub fn parse_synthetic_governed_manifest(
    manifest_bytes: &[u8],
    scoped_bsl_rule: &SExpr,
    scoped_bsl_audit: &SfsRuleAuditResult,
) -> Result<SyntheticGovernedManifestV1, SfsValidationError> {
    preflight_manifest(manifest_bytes)?;
    let lines = manifest_lines(manifest_bytes)?;
    let mut manifest = empty_manifest(manifest_bytes);
    for index in 0..MAX_TOTAL_ROWS {
        if index >= lines.len() {
            break;
        }
        dispatch_row(lines[index], index + 1, &mut manifest)?;
    }
    close_manifest(&mut manifest, scoped_bsl_rule, scoped_bsl_audit)?;
    Ok(manifest)
}

fn preflight_manifest(bytes: &[u8]) -> Result<(), SfsValidationError> {
    if bytes.len() > MAX_GOVERNED_MANIFEST_BYTES {
        return Err(SfsValidationError::GovernedManifestByteLimit {
            actual: bytes.len(),
        });
    }
    if bytes.contains(&b'\r') || !bytes.ends_with(b"\n") || bytes.ends_with(b"\n\n") {
        return Err(SfsValidationError::GovernedManifestMalformed { row: 0 });
    }
    Ok(())
}

fn manifest_lines(bytes: &[u8]) -> Result<Vec<&[u8]>, SfsValidationError> {
    let mut lines = Vec::new();
    let mut start = 0_usize;
    for index in 0..MAX_GOVERNED_MANIFEST_BYTES {
        if index >= bytes.len() {
            break;
        }
        if bytes[index] != b'\n' {
            continue;
        }
        let actual = index - start + 1;
        if actual > MAX_GOVERNED_MANIFEST_LINE_BYTES {
            return Err(SfsValidationError::GovernedManifestLineLimit {
                row: lines.len() + 1,
                actual,
            });
        }
        if lines.len() >= MAX_TOTAL_ROWS {
            return Err(SfsValidationError::GovernedManifestTotalRowLimit {
                actual: lines.len() + 1,
            });
        }
        let line = &bytes[start..index];
        if line.is_empty() || lines.last().is_some_and(|previous| *previous >= line) {
            return Err(SfsValidationError::GovernedManifestMalformed {
                row: lines.len() + 1,
            });
        }
        lines.push(line);
        start = index + 1;
    }
    Ok(lines)
}

fn empty_manifest(bytes: &[u8]) -> SyntheticGovernedManifestV1 {
    SyntheticGovernedManifestV1 {
        canonical_bytes: bytes.to_vec(),
        manifest_digest: domain_digest(GOVERNED_DOMAIN, bytes),
        host_component_manifest_digest: Digest32::from_bytes([0; 32]),
        components: Vec::new(),
        edges: Vec::new(),
        profile_rows: Vec::new(),
        bound_rows: Vec::new(),
    }
}

fn dispatch_row(
    line: &[u8],
    row: usize,
    manifest: &mut SyntheticGovernedManifestV1,
) -> Result<(), SfsValidationError> {
    let text = std::str::from_utf8(line)
        .map_err(|_| SfsValidationError::GovernedManifestMalformed { row })?;
    let fields: Vec<&str> = text.split('|').collect();
    match fields.first().copied() {
        Some("component") => parse_component(&fields, line, row, manifest),
        Some("profile") => parse_profile(&fields, row, manifest),
        Some("bound") => parse_bound(&fields, row, manifest),
        Some("edge") => parse_edge(&fields, row, manifest),
        _ => Err(SfsValidationError::GovernedManifestMalformed { row }),
    }
}

fn parse_component(
    fields: &[&str],
    line: &[u8],
    row: usize,
    manifest: &mut SyntheticGovernedManifestV1,
) -> Result<(), SfsValidationError> {
    if fields.len() != 6 {
        return malformed(row);
    }
    if manifest.components.len() >= MAX_COMPONENTS {
        return Err(SfsValidationError::ComponentLimit {
            actual: manifest.components.len() + 1,
        });
    }
    let component_id = decode_nfc_hex(fields[1], 256, row)?;
    for index in 0..MAX_COMPONENTS {
        if index >= manifest.components.len() {
            break;
        }
        if manifest.components[index].component_id == component_id {
            return Err(SfsValidationError::DuplicateComponentId { component_id });
        }
    }
    let component_kind = parse_component_kind(fields[2], &component_id)?;
    let source_mode = match fields[3] {
        "canonical-bsl" => SourceMode::CanonicalBsl,
        "synthetic-descriptor" => SourceMode::SyntheticDescriptor,
        _ => return malformed(row),
    };
    let source_payload =
        decode_hex(fields[4], MAX_SOURCE_BYTES, row).map_err(|error| match error {
            SfsValidationError::SourcePayloadLimit { actual, .. } => {
                SfsValidationError::SourcePayloadLimit {
                    component_id: component_id.clone(),
                    actual,
                }
            }
            other => other,
        })?;
    let source_digest = digest_hex(fields[5], row)?;
    let computed = match source_mode {
        SourceMode::CanonicalBsl => Digest32::from_bytes(sha256_of(&source_payload)),
        SourceMode::SyntheticDescriptor => domain_digest(COMPONENT_SOURCE_DOMAIN, &source_payload),
    };
    if computed != source_digest {
        return Err(SfsValidationError::ComponentSourceDigestMismatch { component_id });
    }
    manifest.components.push(SyntheticGovernedComponentV1 {
        component_id,
        component_kind,
        component_source_digest: source_digest,
        source_mode,
        source_payload,
        canonical_row: line.to_vec(),
    });
    Ok(())
}

fn parse_profile(
    fields: &[&str],
    row: usize,
    manifest: &mut SyntheticGovernedManifestV1,
) -> Result<(), SfsValidationError> {
    if fields.len() != 4 {
        return malformed(row);
    }
    if manifest.profile_rows.len() >= MAX_PROFILE_ROWS {
        return Err(SfsValidationError::ProfileRowLimit {
            actual: manifest.profile_rows.len() + 1,
        });
    }
    let component_id = decode_nfc_hex(fields[1], 256, row)?;
    if !is_profile_set(fields[2]) {
        return malformed(row);
    }
    let entry = decode_nfc_hex(fields[3], 96, row)?;
    manifest.profile_rows.push(SyntheticProfileRowV1 {
        component_id,
        set_name: fields[2].to_owned(),
        entry,
    });
    Ok(())
}

fn parse_bound(
    fields: &[&str],
    row: usize,
    manifest: &mut SyntheticGovernedManifestV1,
) -> Result<(), SfsValidationError> {
    if fields.len() != 6 {
        return malformed(row);
    }
    if manifest.bound_rows.len() >= MAX_BOUND_ROWS {
        return Err(SfsValidationError::BoundRowLimit {
            actual: manifest.bound_rows.len() + 1,
        });
    }
    manifest.bound_rows.push(SyntheticBoundRowV1 {
        component_id: decode_nfc_hex(fields[1], 256, row)?,
        declared_fuel: fields[2]
            .parse()
            .map_err(|_| SfsValidationError::GovernedManifestMalformed { row })?,
        computed_bound: fields[3]
            .parse()
            .map_err(|_| SfsValidationError::GovernedManifestMalformed { row })?,
        cardinality_digest: digest_hex(fields[4], row)?,
        intrinsic_cost_digest: digest_hex(fields[5], row)?,
    });
    Ok(())
}

fn parse_edge(
    fields: &[&str],
    row: usize,
    manifest: &mut SyntheticGovernedManifestV1,
) -> Result<(), SfsValidationError> {
    if fields.len() != 5 {
        return malformed(row);
    }
    if manifest.edges.len() >= MAX_EDGES {
        return Err(SfsValidationError::EdgeLimit {
            actual: manifest.edges.len() + 1,
        });
    }
    let producer = decode_nfc_hex(fields[1], 256, row)?;
    let consumer = decode_nfc_hex(fields[2], 256, row)?;
    let kind = parse_channel(fields[3], row)?;
    let channel = decode_nfc_hex(fields[4], 96, row)?;
    for index in 0..MAX_EDGES {
        if index >= manifest.edges.len() {
            break;
        }
        let existing = &manifest.edges[index];
        if existing.producer_id == producer
            && existing.consumer_id == consumer
            && existing.channel_id == channel
        {
            return Err(SfsValidationError::DuplicateTypedEdge {
                producer_id: producer,
                consumer_id: consumer,
                channel_id: channel,
            });
        }
    }
    manifest.edges.push(ProducerConsumerEdgeV1::new(
        &producer, &consumer, kind, &channel,
    )?);
    Ok(())
}

fn close_manifest(
    manifest: &mut SyntheticGovernedManifestV1,
    rule: &SExpr,
    audit: &SfsRuleAuditResult,
) -> Result<(), SfsValidationError> {
    let expected = [
        ("membership-reducer", ComponentKindV1::Reducer),
        ("post-commit-producer", ComponentKindV1::PostCommitProducer),
        ("scoped-bsl-rule", ComponentKindV1::BslRule),
    ];
    if manifest.components.len() != expected.len() {
        return Err(SfsValidationError::GovernedComponentSetMismatch);
    }
    #[allow(
        clippy::needless_range_loop,
        reason = "three exact synthetic components"
    )]
    for index in 0..3 {
        if manifest.components[index].component_id != expected[index].0 {
            return Err(SfsValidationError::GovernedComponentSetMismatch);
        }
        if manifest.components[index].component_kind != expected[index].1 {
            return Err(SfsValidationError::ComponentKindMismatch {
                component_id: manifest.components[index].component_id.clone(),
            });
        }
    }
    close_sources(manifest, rule, audit)?;
    close_bound(manifest, audit)?;
    close_references(manifest)?;
    let mut host_rows = Vec::new();
    for index in 0..MAX_COMPONENTS {
        if index >= manifest.components.len() {
            break;
        }
        host_rows.extend_from_slice(&manifest.components[index].canonical_row);
        host_rows.push(b'\n');
    }
    manifest.host_component_manifest_digest = domain_digest(HOST_DOMAIN, &host_rows);
    Ok(())
}

fn close_sources(
    manifest: &SyntheticGovernedManifestV1,
    rule: &SExpr,
    audit: &SfsRuleAuditResult,
) -> Result<(), SfsValidationError> {
    let canonical = canonical_bytes(rule)
        .map_err(|_| SfsValidationError::GovernedManifestMalformed { row: 0 })?;
    let source_digest = Digest32::from_bytes(sha256_of(&canonical));
    if source_digest != Digest32::from_bytes(*audit.footprint().source_digest()) {
        return Err(SfsValidationError::ComponentSourceDigestMismatch {
            component_id: "scoped-bsl-rule".to_owned(),
        });
    }
    let bsl = &manifest.components[2];
    if bsl.source_mode != SourceMode::CanonicalBsl
        || bsl.source_payload != canonical
        || bsl.component_source_digest != source_digest
    {
        return Err(SfsValidationError::ComponentSourceDigestMismatch {
            component_id: bsl.component_id.clone(),
        });
    }
    if manifest.components[..2]
        .iter()
        .any(|component| component.source_mode != SourceMode::SyntheticDescriptor)
    {
        return Err(SfsValidationError::GovernedComponentSetMismatch);
    }
    if manifest.components[0].source_payload != MEMBERSHIP_DESCRIPTOR
        || manifest.components[1].source_payload != PRODUCER_DESCRIPTOR
    {
        return Err(SfsValidationError::ComponentSourceDigestMismatch {
            component_id: "synthetic-host-descriptor".to_owned(),
        });
    }
    Ok(())
}

fn close_bound(
    manifest: &SyntheticGovernedManifestV1,
    audit: &SfsRuleAuditResult,
) -> Result<(), SfsValidationError> {
    if manifest.bound_rows.len() != 1 || manifest.bound_rows[0].component_id != "scoped-bsl-rule" {
        return Err(SfsValidationError::BoundRowLimit {
            actual: manifest.bound_rows.len(),
        });
    }
    let bound = &manifest.bound_rows[0];
    if bound.declared_fuel != audit.declared_fuel() {
        return Err(SfsValidationError::BoundDeclaredFuelMismatch);
    }
    if bound.computed_bound != audit.footprint().computed_bound() {
        return Err(SfsValidationError::BoundComputedLimitMismatch);
    }
    if bound.cardinality_digest != Digest32::from_bytes(*audit.cardinality_input_digest()) {
        return Err(SfsValidationError::BoundCardinalityDigestMismatch);
    }
    if bound.intrinsic_cost_digest != Digest32::from_bytes(*audit.intrinsic_cost_input_digest()) {
        return Err(SfsValidationError::BoundIntrinsicCostDigestMismatch);
    }
    Ok(())
}

fn close_references(manifest: &SyntheticGovernedManifestV1) -> Result<(), SfsValidationError> {
    for index in 0..MAX_PROFILE_ROWS {
        if index >= manifest.profile_rows.len() {
            break;
        }
        let row = &manifest.profile_rows[index];
        if !manifest
            .components
            .iter()
            .any(|component| component.component_id == row.component_id)
        {
            return Err(SfsValidationError::GovernedComponentSetMismatch);
        }
    }
    for index in 0..MAX_EDGES {
        if index >= manifest.edges.len() {
            break;
        }
        for id in [
            &manifest.edges[index].producer_id,
            &manifest.edges[index].consumer_id,
        ] {
            if !manifest
                .components
                .iter()
                .any(|component| &component.component_id == id)
            {
                return Err(SfsValidationError::UnknownEdgeEndpoint {
                    component_id: id.clone(),
                });
            }
        }
    }
    Ok(())
}

fn validate_profile_edge_closure(
    manifest: &SyntheticGovernedManifestV1,
) -> Result<(), SfsValidationError> {
    for index in 0..MAX_PROFILE_ROWS {
        if index >= manifest.profile_rows.len() {
            break;
        }
        let row = &manifest.profile_rows[index];
        if row.component_id != "scoped-bsl-rule"
            && matches!(row.set_name.as_str(), "field_reads" | "edge_reads")
            && matching_edge_count(manifest, row, true) != 1
        {
            return Err(SfsValidationError::MissingIncomingCausalEdge {
                component_id: row.component_id.clone(),
                entry: row.entry.clone(),
            });
        }
        if row.component_id != "post-commit-producer"
            && row.set_name == "effects"
            && matching_edge_count(manifest, row, false) != 1
        {
            return Err(SfsValidationError::MissingOutgoingCausalEdge {
                component_id: row.component_id.clone(),
                entry: row.entry.clone(),
            });
        }
    }
    Ok(())
}

fn matching_edge_count(
    manifest: &SyntheticGovernedManifestV1,
    row: &SyntheticProfileRowV1,
    incoming: bool,
) -> usize {
    let mut count = 0_usize;
    for index in 0..MAX_EDGES {
        if index >= manifest.edges.len() {
            break;
        }
        let edge = &manifest.edges[index];
        let (effect, read, set_name) = edge_tokens(edge);
        let matches = if incoming {
            edge.consumer_id == row.component_id && row.set_name == set_name && row.entry == read
        } else {
            edge.producer_id == row.component_id && row.entry == effect
        };
        if matches {
            count += 1;
        }
    }
    count
}

/// Converts the sealed BSL audit to one exact proof-profile component.
///
/// # Errors
/// Returns an exact component or canonical-set refusal.
pub fn component_profile_from_bsl(
    component_id: &str,
    audit: &SfsRuleAuditResult,
) -> Result<SfsComponentProofProfileV1, SfsValidationError> {
    let footprint = audit.footprint();
    Ok(SfsComponentProofProfileV1::new(
        component_id,
        ComponentKindV1::BslRule,
        Digest32::from_bytes(*footprint.source_digest()),
        set("field_reads", footprint.field_reads())?,
        set("edge_reads", footprint.edge_reads())?,
        set("constant_reads", footprint.constant_reads())?,
        set("queries", footprint.queries())?,
        set("operators", footprint.operators())?,
        set("intrinsics", footprint.intrinsics())?,
        set(
            "comparison_clamp_contexts",
            footprint.comparison_clamp_contexts(),
        )?,
        set("effects", footprint.effects())?,
    )?)
}

/// Validates exact typed-edge closure and the complete three-component cone.
///
/// # Errors
/// Returns the first exact identity, profile, edge, or reachability refusal.
pub fn validate_synthetic_cone(
    cone: &CausalConeV1,
    profile: &SfsProofProfileV1,
    governed_manifest: &SyntheticGovernedManifestV1,
) -> Result<(), SfsValidationError> {
    if profile.governed_manifest_digest() != governed_manifest.manifest_digest {
        return Err(SfsValidationError::GovernedManifestDigestMismatch);
    }
    if Digest32::from_bytes(*record_digest(cone)?.as_bytes()) != profile.causal_cone_digest() {
        return Err(SfsValidationError::CausalConeDigestMismatch);
    }
    validate_endpoints(cone, governed_manifest)?;
    let expected_profiles = manifest_profiles(governed_manifest)?;
    if profile.components() != expected_profiles.as_slice() {
        return Err(SfsValidationError::ConeProfileMismatch);
    }
    validate_typed_edges(governed_manifest, &expected_profiles)?;
    validate_reachability(cone, governed_manifest)
}

fn manifest_profiles(
    manifest: &SyntheticGovernedManifestV1,
) -> Result<Vec<SfsComponentProofProfileV1>, SfsValidationError> {
    let mut output = Vec::with_capacity(manifest.components.len());
    for index in 0..MAX_COMPONENTS {
        if index >= manifest.components.len() {
            break;
        }
        let component = &manifest.components[index];
        let values = |name| profile_entries(manifest, &component.component_id, name);
        output.push(SfsComponentProofProfileV1::new(
            &component.component_id,
            component.component_kind,
            component.component_source_digest,
            CanonicalProfileSet::new("field_reads", values("field_reads"))?,
            CanonicalProfileSet::new("edge_reads", values("edge_reads"))?,
            CanonicalProfileSet::new("constant_reads", values("constant_reads"))?,
            CanonicalProfileSet::new("queries", values("queries"))?,
            CanonicalProfileSet::new("operators", values("operators"))?,
            CanonicalProfileSet::new("intrinsics", values("intrinsics"))?,
            CanonicalProfileSet::new(
                "comparison_clamp_contexts",
                values("comparison_clamp_contexts"),
            )?,
            CanonicalProfileSet::new("effects", values("effects"))?,
        )?);
    }
    Ok(output)
}

fn profile_entries(manifest: &SyntheticGovernedManifestV1, id: &str, name: &str) -> Vec<String> {
    manifest
        .profile_rows
        .iter()
        .filter(|row| row.component_id == id && row.set_name == name)
        .map(|row| row.entry.clone())
        .collect()
}

fn validate_endpoints(
    cone: &CausalConeV1,
    manifest: &SyntheticGovernedManifestV1,
) -> Result<(), SfsValidationError> {
    for (set_name, ids) in [("roots", cone.roots()), ("sinks", cone.sinks())] {
        for index in 0..MAX_COMPONENTS {
            if index >= ids.len() {
                break;
            }
            if !manifest
                .components
                .iter()
                .any(|component| component.component_id == ids[index])
            {
                return Err(SfsValidationError::UnknownConeEndpoint {
                    set: set_name,
                    component_id: ids[index].clone(),
                });
            }
        }
    }
    Ok(())
}

fn validate_typed_edges(
    manifest: &SyntheticGovernedManifestV1,
    profiles: &[SfsComponentProofProfileV1],
) -> Result<(), SfsValidationError> {
    for index in 0..MAX_EDGES {
        if index >= manifest.edges.len() {
            break;
        }
        let edge = &manifest.edges[index];
        let producer = profiles
            .iter()
            .find(|profile| profile.component_id() == edge.producer_id)
            .unwrap();
        let consumer = profiles
            .iter()
            .find(|profile| profile.component_id() == edge.consumer_id)
            .unwrap();
        let (effect, read, set_name) = edge_tokens(edge);
        if !profile_has(manifest, producer.component_id(), "effects", &effect) {
            return Err(SfsValidationError::EdgeProducerEffectMismatch {
                component_id: edge.producer_id.clone(),
                channel_id: edge.channel_id.clone(),
            });
        }
        if !profile_has(manifest, consumer.component_id(), set_name, &read) {
            return Err(SfsValidationError::EdgeConsumerReadMismatch {
                component_id: edge.consumer_id.clone(),
                channel_id: edge.channel_id.clone(),
            });
        }
    }
    validate_profile_edge_closure(manifest)?;
    Ok(())
}

fn edge_tokens(edge: &ProducerConsumerEdgeV1) -> (String, String, &'static str) {
    match edge.channel_kind {
        SyntheticChannelKindV1::Field => (
            format!("node:{}", edge.channel_id),
            edge.channel_id.clone(),
            "field_reads",
        ),
        SyntheticChannelKindV1::Relation => (
            format!("edge:{}", edge.channel_id),
            edge.channel_id.clone(),
            "edge_reads",
        ),
        SyntheticChannelKindV1::Contribution => prefixed("contribution", &edge.channel_id),
        SyntheticChannelKindV1::LedgerRow => prefixed("ledger-row", &edge.channel_id),
        SyntheticChannelKindV1::Receipt => prefixed("receipt", &edge.channel_id),
        SyntheticChannelKindV1::ReducerOutput => prefixed("reducer-output", &edge.channel_id),
    }
}

fn prefixed(prefix: &str, channel: &str) -> (String, String, &'static str) {
    let token = format!("{prefix}:{channel}");
    (token.clone(), token, "field_reads")
}

fn profile_has(manifest: &SyntheticGovernedManifestV1, id: &str, set: &str, entry: &str) -> bool {
    manifest
        .profile_rows
        .iter()
        .any(|row| row.component_id == id && row.set_name == set && row.entry == entry)
}

fn validate_reachability(
    cone: &CausalConeV1,
    manifest: &SyntheticGovernedManifestV1,
) -> Result<(), SfsValidationError> {
    let count = manifest.components.len();
    let mut adjacency = [[false; MAX_COMPONENTS]; MAX_COMPONENTS];
    for index in 0..MAX_EDGES {
        if index >= manifest.edges.len() {
            break;
        }
        let producer = component_index(manifest, &manifest.edges[index].producer_id).unwrap();
        let consumer = component_index(manifest, &manifest.edges[index].consumer_id).unwrap();
        adjacency[producer][consumer] = true;
    }
    let forward = closure(cone.roots(), manifest, &adjacency, false);
    let reverse = closure(cone.sinks(), manifest, &adjacency, true);
    let actual: Vec<String> = (0..count)
        .filter(|index| forward[*index] && reverse[*index])
        .map(|index| manifest.components[index].component_id.clone())
        .collect();
    if !forward
        .iter()
        .take(count)
        .zip(reverse.iter())
        .any(|(left, right)| *left && *right)
    {
        return Err(SfsValidationError::NoRootToSinkPath);
    }
    if actual != cone.components() {
        return Err(SfsValidationError::GovernedComponentSetMismatch);
    }
    Ok(())
}

fn closure(
    starts: &[String],
    manifest: &SyntheticGovernedManifestV1,
    adjacency: &[[bool; MAX_COMPONENTS]; MAX_COMPONENTS],
    reverse: bool,
) -> [bool; MAX_COMPONENTS] {
    let mut found = [false; MAX_COMPONENTS];
    for start in starts {
        found[component_index(manifest, start).unwrap()] = true;
    }
    for _pass in 0..MAX_COMPONENTS {
        for left in 0..MAX_COMPONENTS {
            if left >= manifest.components.len() {
                break;
            }
            for right in 0..MAX_COMPONENTS {
                if right >= manifest.components.len() {
                    break;
                }
                let edge = if reverse {
                    adjacency[right][left]
                } else {
                    adjacency[left][right]
                };
                if found[left] && edge {
                    found[right] = true;
                }
            }
        }
    }
    found
}

fn component_index(manifest: &SyntheticGovernedManifestV1, id: &str) -> Option<usize> {
    manifest
        .components
        .iter()
        .position(|component| component.component_id == id)
}

/// Validates distinct manifest/profile/preregistration identity placement.
///
/// # Errors
/// Returns the first exact manifest, profile, mutation, or preregistration mismatch.
pub fn validate_synthetic_profile_identity(
    run_identity: &RunIdentityV1,
    proof_profile: &SfsProofProfileV1,
    preregistration: &crate::SfsPreregistrationV1,
    governed_manifest: &SyntheticGovernedManifestV1,
    mutation_manifest_digest: Digest32,
) -> Result<(), SfsValidationError> {
    if run_identity.host_component_manifest_digest()
        != governed_manifest.host_component_manifest_digest
    {
        return Err(SfsValidationError::HostManifestDigestMismatch);
    }
    if run_identity.governed_footprint_manifest_digest() != governed_manifest.manifest_digest {
        return Err(SfsValidationError::GovernedFootprintDigestMismatch);
    }
    if proof_profile.governed_manifest_digest() != governed_manifest.manifest_digest {
        return Err(SfsValidationError::GovernedManifestDigestMismatch);
    }
    let profile_digest = Digest32::from_bytes(*record_digest(proof_profile)?.as_bytes());
    if run_identity.sfs_proof_profile_digest() != profile_digest
        || preregistration.sfs_proof_profile_digest() != profile_digest
    {
        return Err(SfsValidationError::ProofProfileDigestMismatch);
    }
    if preregistration.mutation_manifest_digest() != mutation_manifest_digest {
        return Err(SfsValidationError::MutationManifestDigestMismatch);
    }
    let prereg_digest = Digest32::from_bytes(*record_digest(preregistration)?.as_bytes());
    if run_identity.sfs_preregistration_digest() != prereg_digest {
        return Err(SfsValidationError::PreregistrationDigestMismatch);
    }
    Ok(())
}

/// Validates the exact 41-row mutation specification and preregistered digest.
///
/// # Errors
/// Returns the first framing, schema, coverage, activation, or digest refusal.
pub fn validate_synthetic_mutation_manifest(
    bytes: &[u8],
    preregistration: &crate::SfsPreregistrationV1,
) -> Result<Digest32, SfsValidationError> {
    if bytes.contains(&b'\r') || !bytes.ends_with(b"\n") || bytes.ends_with(b"\n\n") {
        return Err(SfsValidationError::MutationManifestMalformed { row: 0 });
    }
    let rows: Vec<&[u8]> = bytes[..bytes.len() - 1]
        .split(|byte| *byte == b'\n')
        .collect();
    if rows.len() != 41 {
        return Err(SfsValidationError::MutationCoverageMismatch {
            mutation_id: "row-count".to_owned(),
        });
    }
    for index in 0..41 {
        if index > 0 && rows[index - 1] >= rows[index] {
            return Err(SfsValidationError::MutationManifestMalformed { row: index + 1 });
        }
        let text = std::str::from_utf8(rows[index])
            .map_err(|_| SfsValidationError::MutationManifestMalformed { row: index + 1 })?;
        let fields: Vec<&str> = text.split('|').collect();
        if fields.len() != 6
            || !matches!(fields[1], "STATIC" | "DRIVER" | "DYNAMIC" | "EVALUATOR")
            || !matches!(
                fields[4],
                "SYNTHETIC" | "GATE3" | "GATE5" | "G6" | "PER44" | "LIVE_T3"
            )
            || (fields[4] == "SYNTHETIC" && fields[5] == "-")
            || (fields[4] != "SYNTHETIC" && fields[5] != "-")
        {
            return Err(SfsValidationError::MutationManifestMalformed { row: index + 1 });
        }
    }
    let digest = domain_digest(MUTATION_DOMAIN, bytes);
    if digest != EXPECTED_MUTATION_DIGEST || digest != preregistration.mutation_manifest_digest() {
        return Err(SfsValidationError::MutationManifestDigestMismatch);
    }
    Ok(digest)
}

fn parse_component_kind(value: &str, id: &str) -> Result<ComponentKindV1, SfsValidationError> {
    match value {
        "0" => Ok(ComponentKindV1::BslRule),
        "1" => Ok(ComponentKindV1::RustBoundary),
        "2" => Ok(ComponentKindV1::Reducer),
        "3" => Ok(ComponentKindV1::PostCommitProducer),
        _ => Err(SfsValidationError::ComponentKindMismatch {
            component_id: id.to_owned(),
        }),
    }
}

fn parse_channel(value: &str, row: usize) -> Result<SyntheticChannelKindV1, SfsValidationError> {
    match value {
        "0" => Ok(SyntheticChannelKindV1::Field),
        "1" => Ok(SyntheticChannelKindV1::Relation),
        "2" => Ok(SyntheticChannelKindV1::Contribution),
        "3" => Ok(SyntheticChannelKindV1::LedgerRow),
        "4" => Ok(SyntheticChannelKindV1::Receipt),
        "5" => Ok(SyntheticChannelKindV1::ReducerOutput),
        _ => malformed(row),
    }
}

fn is_profile_set(value: &str) -> bool {
    matches!(
        value,
        "field_reads"
            | "edge_reads"
            | "constant_reads"
            | "queries"
            | "operators"
            | "intrinsics"
            | "comparison_clamp_contexts"
            | "effects"
    )
}

fn decode_nfc_hex(value: &str, maximum: usize, row: usize) -> Result<String, SfsValidationError> {
    let bytes = decode_hex(value, maximum, row)?;
    let text = String::from_utf8(bytes)
        .map_err(|_| SfsValidationError::GovernedManifestMalformed { row })?;
    validate_nfc(&text, maximum, row)?;
    Ok(text)
}

fn decode_hex(value: &str, maximum: usize, row: usize) -> Result<Vec<u8>, SfsValidationError> {
    if value.is_empty()
        || !value.len().is_multiple_of(2)
        || value
            .bytes()
            .any(|byte| !matches!(byte, b'0'..=b'9' | b'a'..=b'f'))
    {
        return malformed(row);
    }
    let actual = value.len() / 2;
    if actual > maximum {
        return Err(SfsValidationError::SourcePayloadLimit {
            component_id: String::new(),
            actual,
        });
    }
    let mut output = Vec::with_capacity(actual);
    for index in 0..MAX_SOURCE_BYTES {
        if index >= actual {
            break;
        }
        let byte = u8::from_str_radix(&value[index * 2..index * 2 + 2], 16)
            .map_err(|_| SfsValidationError::GovernedManifestMalformed { row })?;
        output.push(byte);
    }
    Ok(output)
}

fn digest_hex(value: &str, row: usize) -> Result<Digest32, SfsValidationError> {
    let bytes = decode_hex(value, 32, row)?;
    let array: [u8; 32] = bytes
        .try_into()
        .map_err(|_| SfsValidationError::GovernedManifestMalformed { row })?;
    Ok(Digest32::from_bytes(array))
}

fn validate_nfc(value: &str, maximum: usize, row: usize) -> Result<(), SfsValidationError> {
    if value.is_empty() || value.len() > maximum || value.nfc().ne(value.chars()) {
        return malformed(row);
    }
    Ok(())
}

fn set(
    field: &'static str,
    values: &BTreeSet<String>,
) -> Result<CanonicalProfileSet, SfsValidationError> {
    Ok(CanonicalProfileSet::new(
        field,
        values.iter().cloned().collect(),
    )?)
}

fn domain_digest(domain: &[u8], payload: &[u8]) -> Digest32 {
    let mut bytes = Vec::with_capacity(domain.len() + 1 + payload.len());
    bytes.extend_from_slice(domain);
    bytes.push(0);
    bytes.extend_from_slice(payload);
    Digest32::from_bytes(sha256_of(&bytes))
}

fn malformed<T>(row: usize) -> Result<T, SfsValidationError> {
    Err(SfsValidationError::GovernedManifestMalformed { row })
}
