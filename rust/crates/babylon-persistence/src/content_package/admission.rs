//! Host-profile admission of one resolved external content set.
//!
//! # Scope and extension points
//!
//! `validate_profile_sources` is the profile switch. The numeric
//! `michigan-regional-v6` profile admits exactly one complete defines unit and
//! builds it through [`MichiganContentPreset::FourWeekStandard`]; native catalog
//! content continues to supply the scenario, rules and material algorithms. This
//! profile has no national foreground/background partition, so Task 10's
//! aid-derived `NationalDetailPartition` is not on this path.
//!
//! A future host profile that admits the national economic builder will consume
//! the partition already captured by `CapturedEconomicCatalog::national_detail()`.
//! `build_national_opening` derives that foreground from the Organization-payer
//! aid capture and exposes no caller-supplied selection today; the public
//! `ForegroundSelection`/`consolidate_background` seam belongs to that builder and
//! is where a future selection parameter would attach. The package resolver must
//! not grow a second selection path, and this module must not redesign the
//! national builder.
//!
//! The authored graph profile is validated here but admitted in
//! `content_package/authored_graph.rs` (Task 12). Keeping resolution, profile
//! validation and per-profile admission in separate leaves is what lets that
//! task add a profile without touching the resolver.

use std::path::Path;

use babylon_kernel::content_digest;
use uuid::Uuid;

use crate::identity::CampaignId;
use crate::material_runtime::MaterialRuntimeFoundation;
use crate::michigan_content::MichiganContentPreset;
use crate::michigan_material::MichiganMaterialCatalog;
use crate::sqlite_store::AdmittedContent;
use crate::sqlite_store::AdmittedContentEntry;
use crate::sqlite_store::AdmittedOpening;
use crate::sqlite_store::BuildIdentity;
use crate::sqlite_store::CampaignHandle;
use crate::sqlite_store::ChunkSection;
use crate::sqlite_store::ContentEntryKind;
use crate::sqlite_store::SaveError;
use crate::sqlite_store::SqliteCampaignStore;
use crate::sqlite_store::StateChunk;

use super::audit;
use super::audit::CoefficientNormalization;
use super::error::PackageError;
use super::manifest::HostProfile;
use super::manifest::SourceKind;
use super::resolver::ResolvedContentSet;

const ADMISSION_DOMAIN: &[u8] = b"babylon.michigan-regional.admission.v1\0";
const CONTRACT_DOMAIN: &[u8] = b"babylon.content-package-host.v1\0";

/// Return the deterministic host build identity under which packages are admitted.
///
/// The content store refuses to reopen a campaign under a different identity, so
/// the same binary must derive the same value. Task 13 owns a runtime build hash;
/// until then the pinned package contract version and linked `SQLite` identity name
/// this host.
#[must_use]
pub fn content_package_build_identity() -> BuildIdentity {
    let identity = format!(
        "{}|{}|{}",
        env!("CARGO_PKG_VERSION"),
        crate::sqlite_runtime_pin::PINNED_SQLITE_VERSION_TEXT,
        super::manifest::CONTENT_ABI
    );
    BuildIdentity::from_hash(content_digest::sha256_of(
        &[CONTRACT_DOMAIN, identity.as_bytes()].concat(),
    ))
}

/// Validate that the effective source kinds match the selected host profile.
///
/// # Errors
///
/// Refuses any source kind the selected profile does not accept, a missing
/// required unit, or more than one unit of a single kind.
pub fn validate_profile_sources(resolved: &ResolvedContentSet) -> Result<(), PackageError> {
    let profile = resolved.host_profile();
    match profile {
        HostProfile::MichiganRegionalV6 => {
            let defines = resolved.units_of(SourceKind::Defines).count();
            let other = resolved
                .units()
                .iter()
                .filter(|unit| unit.kind() != SourceKind::Defines)
                .count();
            if defines != 1 || other != 0 {
                return Err(PackageError::ProfileSourceKinds {
                    profile,
                    reason: format!(
                        "michigan-regional-v6 accepts exactly one defines unit; found {defines} defines and {other} other units"
                    ),
                });
            }
        }
        HostProfile::AuthoredGraphV1 => {
            let scenarios = resolved.units_of(SourceKind::Scenario).count();
            let preludes = resolved.units_of(SourceKind::Prelude).count();
            let rules = resolved.units_of(SourceKind::Rules).count();
            let defines = resolved.units_of(SourceKind::Defines).count();
            if scenarios != 1 || rules != 1 || preludes > 1 || defines != 0 {
                return Err(PackageError::ProfileSourceKinds {
                    profile,
                    reason: format!(
                        "authored-graph-v1 accepts exactly one scenario, zero or one prelude, exactly one rules unit and zero defines; found {scenarios} scenario, {preludes} prelude, {rules} rules and {defines} defines"
                    ),
                });
            }
        }
    }
    Ok(())
}

/// Admit one resolved `michigan-regional-v6` package set into a new campaign store.
///
/// The complete replacement defines unit is compiled once by the existing
/// Michigan builder. Native catalog content still supplies the scenario, rules
/// and material algorithms; this function captures the exact effective source,
/// the resolved package identity, the ordinary foundation and its opening.
///
/// # Errors
///
/// Refuses a different host profile, a source-kind mismatch, an invalid or
/// infeasible defines value, a native content audit refusal, a catalog
/// coefficient without basis or unit, or a `SQLite` store refusal.
pub fn admit_michigan_regional_package(
    resolved: &ResolvedContentSet,
    store_path: &Path,
) -> Result<CampaignHandle, SaveError> {
    if resolved.host_profile() != HostProfile::MichiganRegionalV6 {
        return Err(package_refused(format!(
            "the resolved set selects {} instead of michigan-regional-v6",
            resolved.host_profile().manifest_name()
        )));
    }
    validate_profile_sources(resolved).map_err(|error| package_refused(error.to_string()))?;
    let defines = resolved
        .units_of(SourceKind::Defines)
        .next()
        .ok_or_else(|| package_refused("the resolved set carries no defines unit".to_owned()))?;
    let defines_text = std::str::from_utf8(defines.bytes())
        .map_err(|_| package_refused("the effective defines unit is not UTF-8".to_owned()))?;
    let catalog = MichiganMaterialCatalog::from_defines_toml(defines_text)
        .map_err(|error| package_refused(error.to_string()))?;
    let foundation = MichiganContentPreset::FourWeekStandard
        .create_foundation(&catalog)
        .map_err(|error| package_refused(error.to_string()))?;
    audit::audit_rule_set(
        catalog.graph_scenario_source(),
        None,
        &[catalog.rule_source()],
    )
    .map_err(|error| package_refused(error.to_string()))?;
    let normalization = CoefficientNormalization::new(catalog.staffing().hours_per_worker_period)
        .map_err(|error| package_refused(error.to_string()))?;
    audit::audit_catalog_coefficients(foundation.material_catalog(), normalization)
        .map_err(|error| package_refused(error.to_string()))?;
    let world_hash = world_hash(&foundation)?;
    let content = admitted_content(resolved, &catalog)?;
    let opening = admitted_opening(resolved, &foundation, world_hash);
    SqliteCampaignStore::create(store_path, content, opening)
}

fn world_hash(foundation: &MaterialRuntimeFoundation) -> Result<[u8; 32], SaveError> {
    let reconstructed = foundation
        .reconstruct_captured()
        .map_err(|error| package_refused(error.to_string()))?;
    let session = reconstructed
        .into_session()
        .map_err(|error| package_refused(error.to_string()))?;
    session
        .current_world_hash()
        .map_err(|error| package_refused(error.to_string()))
}

fn admitted_content(
    resolved: &ResolvedContentSet,
    catalog: &MichiganMaterialCatalog,
) -> Result<AdmittedContent, SaveError> {
    let mut entries = Vec::with_capacity(resolved.units().len() + 3);
    for unit in resolved.units() {
        entries.push(AdmittedContentEntry {
            kind: ContentEntryKind::CapturedSource,
            key: unit.source_id().as_bytes().to_vec(),
            ordinal: 0,
            bytes: unit.bytes().to_vec(),
        });
    }
    entries.push(AdmittedContentEntry {
        kind: ContentEntryKind::Provenance,
        key: b"content-package".to_vec(),
        ordinal: 0,
        bytes: resolved.canonical_bytes().to_vec(),
    });
    entries.push(AdmittedContentEntry {
        kind: ContentEntryKind::CompiledDefinitions,
        key: b"michigan-defines".to_vec(),
        ordinal: 0,
        bytes: catalog
            .canonical_defines_bytes()
            .map_err(|error| package_refused(error.to_string()))?,
    });
    entries.push(AdmittedContentEntry {
        kind: ContentEntryKind::OpeningMetadata,
        key: b"michigan-regional-admission".to_vec(),
        ordinal: 0,
        bytes: admission_metadata(resolved),
    });
    Ok(AdmittedContent {
        campaign_id: CampaignId::from_uuid(campaign_uuid(resolved.digest())),
        build: content_package_build_identity(),
        entries,
    })
}

fn admitted_opening(
    resolved: &ResolvedContentSet,
    foundation: &MaterialRuntimeFoundation,
    world_hash: [u8; 32],
) -> AdmittedOpening {
    let graph = foundation.graph_foundation();
    let content_digest = graph.content_digest();
    let mut content_hash = Vec::with_capacity(64);
    content_hash.extend_from_slice(&content_digest.defines_hash);
    content_hash.extend_from_slice(&content_digest.rules_hash);
    let chunks = vec![
        chunk(
            ChunkSection::StableGraph,
            graph.stable_graph_bytes().to_vec(),
        ),
        chunk(
            ChunkSection::WorldRegisters,
            graph.world_register_bytes().to_vec(),
        ),
        chunk(
            ChunkSection::ResolverManifest,
            graph.resolver_manifest_bytes().to_vec(),
        ),
        chunk(
            ChunkSection::PreparedEnvironment,
            graph.prepared_environment_bytes().to_vec(),
        ),
        chunk(
            ChunkSection::ReplaySessionIdentity,
            graph.replay_session_identity().as_bytes().to_vec(),
        ),
        chunk(
            ChunkSection::RngSeed,
            graph.rng_seed().to_be_bytes().to_vec(),
        ),
        chunk(ChunkSection::ContentDigest, content_hash),
        chunk(
            ChunkSection::ReferenceDigest,
            graph.reference_digest().as_bytes().to_vec(),
        ),
        chunk(ChunkSection::SemanticState, admission_metadata(resolved)),
    ];
    AdmittedOpening {
        world_hash,
        state_hash: content_digest::sha256_of(foundation.initial_register().canonical_bytes()),
        chunks,
    }
}

fn chunk(section: ChunkSection, bytes: Vec<u8>) -> StateChunk {
    StateChunk {
        section,
        ordinal: 0,
        bytes,
    }
}

fn admission_metadata(resolved: &ResolvedContentSet) -> Vec<u8> {
    let mut bytes = Vec::new();
    bytes.extend_from_slice(ADMISSION_DOMAIN);
    let host = resolved.host_profile().manifest_name().as_bytes();
    bytes.extend_from_slice(
        &u32::try_from(host.len())
            .expect("host profile names are bounded")
            .to_be_bytes(),
    );
    bytes.extend_from_slice(host);
    bytes.extend_from_slice(&resolved.digest());
    bytes
}

fn campaign_uuid(digest: [u8; 32]) -> Uuid {
    let mut bytes = [0_u8; 16];
    bytes.copy_from_slice(&digest[..16]);
    Uuid::from_bytes(bytes)
}

fn package_refused(reason: String) -> SaveError {
    SaveError::ContentPackage { reason }
}
