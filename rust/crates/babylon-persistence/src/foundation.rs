//! Database-free capture of one exact replay campaign foundation.

use std::collections::TryReserveError;

use babylon_bsl::rule_pipeline::split_content;
use babylon_bsl::rules_hash_of;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_kernel::replay::{ReplaySeed, ReplaySessionIdV1};
use babylon_kernel::sha256_of;
use babylon_kernel::tick_content_hash::RefDigestV1;
use babylon_kernel::ContentDigest;
use babylon_tick::replay_session::ReplayTickSession;

use crate::runtime::RustPersistenceRuntimeErrorV1;
use crate::semantic_codec;

/// Exact bounded mechanics and reference-manifest bytes needed to rebuild a session.
#[derive(Debug, PartialEq, Eq)]
pub struct FoundationContentBundleV1 {
    scenario_source_bytes: Vec<u8>,
    prelude_source_bytes: Option<Vec<u8>>,
    rule_source_bytes: Vec<u8>,
    defines_bytes: Vec<u8>,
    reference_bundle_manifest_bytes: Vec<u8>,
    content_digest: ContentDigest,
    reference_digest: RefDigestV1,
    canonical_bytes: Vec<u8>,
}

impl FoundationContentBundleV1 {
    /// Copy and validate one exact bounded content bundle.
    ///
    /// # Errors
    /// Returns the first UTF-8, NUL, byte-bound, integer, capacity, or
    /// allocation refusal before exposing a partial bundle.
    pub fn try_new(
        scenario_source: &str,
        prelude_source: Option<&str>,
        rule_source: &str,
        defines: &[u8],
        reference_manifest: &[u8],
    ) -> Result<Self, RustPersistenceRuntimeErrorV1> {
        let canonical_bytes = semantic_codec::encode_foundation_content(
            scenario_source,
            prelude_source,
            rule_source,
            defines,
            reference_manifest,
        )?;
        let (_, rules) =
            split_content(rule_source).map_err(|_| RustPersistenceRuntimeErrorV1::ReplaySource)?;
        let rule_forms = rules.into_iter().map(|(_, form)| form).collect::<Vec<_>>();
        let content_digest = ContentDigest {
            defines_hash: sha256_of(defines),
            rules_hash: rules_hash_of(&rule_forms)
                .map_err(|_| RustPersistenceRuntimeErrorV1::ReplaySource)?,
        };
        let reference_digest = RefDigestV1::from_bytes(sha256_of(reference_manifest));
        let scenario_source_bytes = copy_bytes(
            "foundation scenario source bytes",
            scenario_source.as_bytes(),
        )?;
        let prelude_source_bytes = prelude_source
            .map(|source| copy_bytes("foundation prelude source bytes", source.as_bytes()))
            .transpose()?;
        let rule_source_bytes = copy_bytes("foundation rule source bytes", rule_source.as_bytes())?;
        let defines_bytes = copy_bytes("foundation defines bytes", defines)?;
        let reference_bundle_manifest_bytes =
            copy_bytes("foundation reference manifest bytes", reference_manifest)?;
        Ok(Self {
            scenario_source_bytes,
            prelude_source_bytes,
            rule_source_bytes,
            defines_bytes,
            reference_bundle_manifest_bytes,
            content_digest,
            reference_digest,
            canonical_bytes,
        })
    }

    /// Borrow the exact scenario source bytes.
    #[must_use]
    pub fn scenario_source_bytes(&self) -> &[u8] {
        &self.scenario_source_bytes
    }

    /// Borrow the exact optional prelude source bytes.
    #[must_use]
    pub fn prelude_source_bytes(&self) -> Option<&[u8]> {
        self.prelude_source_bytes.as_deref()
    }

    /// Borrow the exact rule source bytes.
    #[must_use]
    pub fn rule_source_bytes(&self) -> &[u8] {
        &self.rule_source_bytes
    }

    /// Borrow the exact defines artifact bytes.
    #[must_use]
    pub fn defines_bytes(&self) -> &[u8] {
        &self.defines_bytes
    }

    /// Borrow the exact reference-bundle manifest bytes.
    #[must_use]
    pub fn reference_bundle_manifest_bytes(&self) -> &[u8] {
        &self.reference_bundle_manifest_bytes
    }

    /// Borrow the exact mechanics identity derived from the retained artifacts.
    #[must_use]
    pub const fn content_digest(&self) -> &ContentDigest {
        &self.content_digest
    }

    /// Return the exact retained reference-manifest identity.
    #[must_use]
    pub const fn reference_digest(&self) -> RefDigestV1 {
        self.reference_digest
    }

    /// Borrow the canonical tagged content-bundle bytes.
    #[must_use]
    pub fn canonical_bytes(&self) -> &[u8] {
        &self.canonical_bytes
    }
}

/// Exact tick-zero sources from which one replay campaign can be reconstructed.
#[derive(Debug, PartialEq, Eq)]
pub struct CampaignFoundationV1 {
    stable_graph_bytes: Vec<u8>,
    world_register_bytes: Vec<u8>,
    resolver_manifest_bytes: Vec<u8>,
    prepared_environment_bytes: Vec<u8>,
    replay_session_identity: ReplaySessionIdV1,
    rng_seed: ReplaySeed,
    content_digest: ContentDigest,
    reference_digest: RefDigestV1,
    content_bundle: FoundationContentBundleV1,
    canonical_bytes: Vec<u8>,
}

impl CampaignFoundationV1 {
    /// Capture all exact reconstruction sources from one prepared tick-zero session.
    ///
    /// # Errors
    /// Refuses a session after its first executed tick or the first stable
    /// identity, byte-bound, capacity, integer, or allocation failure. This
    /// operation never parses rules or executes a tick.
    pub fn capture(
        session: &ReplayTickSession<HypergraphStore>,
        content_bundle: FoundationContentBundleV1,
    ) -> Result<Self, RustPersistenceRuntimeErrorV1> {
        if session.completed_tick() != 0 {
            return Err(RustPersistenceRuntimeErrorV1::FoundationAfterTickZero {
                actual: session.completed_tick(),
            });
        }
        let stable_graph = session
            .stable_graph_state()
            .map_err(|_| RustPersistenceRuntimeErrorV1::ReplaySource)?;
        let world_registers = session
            .world_registers()
            .map_err(|_| RustPersistenceRuntimeErrorV1::ReplaySource)?;
        let stable_graph_bytes = copy_bytes(
            "campaign foundation stable graph bytes",
            stable_graph.canonical_bytes(),
        )?;
        let world_register_bytes = copy_bytes(
            "campaign foundation world register bytes",
            world_registers.canonical_bytes(),
        )?;
        let resolver_manifest_bytes = copy_bytes(
            "campaign foundation resolver manifest bytes",
            session.resolver_manifest_bytes(),
        )?;
        let prepared_environment_bytes = copy_bytes(
            "campaign foundation prepared environment bytes",
            session.prepared_environment_bytes(),
        )?;
        let replay_session_identity =
            ReplaySessionIdV1::try_from(session.session_identity().as_bytes())
                .map_err(|_| RustPersistenceRuntimeErrorV1::ReplaySource)?;
        let rng_seed = session.rng_seed();
        let content_digest = session.content_digest().clone();
        let reference_digest = session.reference_digest();
        if content_bundle.content_digest() != &content_digest
            || content_bundle.reference_digest() != reference_digest
        {
            return Err(RustPersistenceRuntimeErrorV1::ReplaySource);
        }
        let replay_session_text = std::str::from_utf8(replay_session_identity.as_bytes())
            .map_err(|_| RustPersistenceRuntimeErrorV1::ReplaySource)?;
        let canonical_bytes = semantic_codec::encode_foundation(
            &stable_graph_bytes,
            &world_register_bytes,
            &resolver_manifest_bytes,
            &prepared_environment_bytes,
            replay_session_text,
            i64::from_be_bytes(rng_seed.to_be_bytes()),
            &content_digest.defines_hash,
            &content_digest.rules_hash,
            reference_digest.as_bytes(),
            content_bundle.canonical_bytes(),
        )?;
        Ok(Self {
            stable_graph_bytes,
            world_register_bytes,
            resolver_manifest_bytes,
            prepared_environment_bytes,
            replay_session_identity,
            rng_seed,
            content_digest,
            reference_digest,
            content_bundle,
            canonical_bytes,
        })
    }

    #[allow(
        clippy::too_many_arguments,
        reason = "the durable foundation has nine exact replay sources and five content artifacts"
    )]
    pub(crate) fn from_persisted(
        stable_graph_bytes: Vec<u8>,
        world_register_bytes: Vec<u8>,
        resolver_manifest_bytes: Vec<u8>,
        prepared_environment_bytes: Vec<u8>,
        replay_session_identity: &str,
        rng_seed: i64,
        defines_hash: [u8; 32],
        rules_hash: [u8; 32],
        reference_digest: [u8; 32],
        scenario_source: &str,
        prelude_source: Option<&str>,
        rule_source: &str,
        defines_bytes: &[u8],
        reference_manifest: &[u8],
        expected_foundation_sha256: [u8; 32],
    ) -> Result<Self, RustPersistenceRuntimeErrorV1> {
        let content_bundle = FoundationContentBundleV1::try_new(
            scenario_source,
            prelude_source,
            rule_source,
            defines_bytes,
            reference_manifest,
        )?;
        let content_digest = ContentDigest {
            defines_hash,
            rules_hash,
        };
        let reference_digest = RefDigestV1::from_bytes(reference_digest);
        if content_bundle.content_digest() != &content_digest
            || content_bundle.reference_digest() != reference_digest
        {
            return Err(RustPersistenceRuntimeErrorV1::ReplaySource);
        }
        let replay_session_identity = ReplaySessionIdV1::try_from(replay_session_identity)
            .map_err(|_| RustPersistenceRuntimeErrorV1::ReplaySource)?;
        let canonical_bytes = semantic_codec::encode_foundation(
            &stable_graph_bytes,
            &world_register_bytes,
            &resolver_manifest_bytes,
            &prepared_environment_bytes,
            std::str::from_utf8(replay_session_identity.as_bytes())
                .map_err(|_| RustPersistenceRuntimeErrorV1::ReplaySource)?,
            rng_seed,
            &content_digest.defines_hash,
            &content_digest.rules_hash,
            reference_digest.as_bytes(),
            content_bundle.canonical_bytes(),
        )?;
        if sha256_of(&canonical_bytes) != expected_foundation_sha256 {
            return Err(RustPersistenceRuntimeErrorV1::ReplaySource);
        }
        Ok(Self {
            stable_graph_bytes,
            world_register_bytes,
            resolver_manifest_bytes,
            prepared_environment_bytes,
            replay_session_identity,
            rng_seed: ReplaySeed::new(rng_seed),
            content_digest,
            reference_digest,
            content_bundle,
            canonical_bytes,
        })
    }

    /// Borrow the exact stable graph bytes.
    #[must_use]
    pub fn stable_graph_bytes(&self) -> &[u8] {
        &self.stable_graph_bytes
    }

    /// Borrow the exact tick-zero world-register bytes.
    #[must_use]
    pub fn world_register_bytes(&self) -> &[u8] {
        &self.world_register_bytes
    }

    /// Borrow the exact resolver-manifest bytes.
    #[must_use]
    pub fn resolver_manifest_bytes(&self) -> &[u8] {
        &self.resolver_manifest_bytes
    }

    /// Borrow the exact prepared-environment bytes.
    #[must_use]
    pub fn prepared_environment_bytes(&self) -> &[u8] {
        &self.prepared_environment_bytes
    }

    /// Borrow the exact replay-session namespace.
    #[must_use]
    pub const fn replay_session_identity(&self) -> &ReplaySessionIdV1 {
        &self.replay_session_identity
    }

    /// Return the exact replay seed.
    #[must_use]
    pub const fn rng_seed(&self) -> ReplaySeed {
        self.rng_seed
    }

    /// Borrow the exact mechanics-content identity.
    #[must_use]
    pub const fn content_digest(&self) -> &ContentDigest {
        &self.content_digest
    }

    /// Return the exact reference-data identity.
    #[must_use]
    pub const fn reference_digest(&self) -> RefDigestV1 {
        self.reference_digest
    }

    /// Borrow the exact content bundle.
    #[must_use]
    pub const fn content_bundle(&self) -> &FoundationContentBundleV1 {
        &self.content_bundle
    }

    /// Borrow the canonical complete foundation bytes.
    #[must_use]
    pub fn canonical_bytes(&self) -> &[u8] {
        &self.canonical_bytes
    }
}

fn copy_bytes(
    field: &'static str,
    source: &[u8],
) -> Result<Vec<u8>, RustPersistenceRuntimeErrorV1> {
    let mut bytes = Vec::new();
    bytes
        .try_reserve_exact(source.len())
        .map_err(
            |_: TryReserveError| RustPersistenceRuntimeErrorV1::Allocation {
                field,
                requested: source.len(),
            },
        )?;
    bytes.extend_from_slice(source);
    Ok(bytes)
}
