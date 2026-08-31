//! Compile-time RED surface for the sole production Rust persistence runtime.

use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_graph::stable_state::StableGraphStateV1;
use babylon_kernel::content_digest::ContentDigest;
use babylon_kernel::replay::{ReplaySeed, ReplaySessionIdV1};
use babylon_kernel::tick_content_hash::{RefDigestV1, TickContentHashV1};
use babylon_persistence::{
    activate_rust_persistence_v1, hydrate_campaign_foundation_v1, prepare_committed_tick_v1,
    ActivationReportV1, ArchiveDirtyReceiptV1, CampaignFoundationV1, CampaignId,
    CheckpointCompletenessV1, CheckpointRowsV1, CommittedCheckpointSectionV1,
    CommittedFullCheckpointV1, CommittedResolveTickErrorV1, CommittedResolveTickV1,
    CommittedTickReceiptV1, DurableReplayRuntimeV1, FoundationContentBundleV1,
    FullCheckpointSectionTagV1, PersistenceAuthorityLedgerRowV1, PersistenceAuthorityStateV1,
    PreparedCommittedTickV1, RustPersistenceActivationErrorV1, RustPersistenceRuntimeErrorV1,
    StableGraphRowsEmptyProofV1, SuccessfulEventBatchEmptyProofV1,
};
use babylon_practice_contract::ordered_action_v1::OrderedPracticeActionBatchV1;
use babylon_tick::material_state::MaterialStateRowsV1;
use babylon_tick::replay_session::{
    IdentifiedTickReportV1, ReplayTickSession, SuccessfulEventBatchV1,
};
use postgres::Config;

fn assert_send<T: Send>() {}

fn assert_prepare_signature(
    value: fn(
        &IdentifiedTickReportV1,
    ) -> Result<PreparedCommittedTickV1, RustPersistenceRuntimeErrorV1>,
) {
    let _ = value;
}

fn assert_activation_signature(
    value: fn(&Config) -> Result<ActivationReportV1, RustPersistenceActivationErrorV1>,
) {
    let _ = value;
}

fn assert_foundation_hydration_signature(
    value: fn(&Config, CampaignId) -> Result<CampaignFoundationV1, RustPersistenceRuntimeErrorV1>,
) {
    let _ = value;
}

type ContentBundleConstructor =
    fn(
        &str,
        Option<&str>,
        &str,
        &[u8],
        &[u8],
    ) -> Result<FoundationContentBundleV1, RustPersistenceRuntimeErrorV1>;

fn assert_content_bundle_constructor(value: ContentBundleConstructor) {
    let _ = value;
}

fn assert_foundation_capture_signature(
    value: fn(
        &ReplayTickSession<HypergraphStore>,
        FoundationContentBundleV1,
    ) -> Result<CampaignFoundationV1, RustPersistenceRuntimeErrorV1>,
) {
    let _ = value;
}

type ProductionRuntime = DurableReplayRuntimeV1<HypergraphStore>;

fn assert_runtime_create_signature(
    value: fn(
        &Config,
        CampaignId,
        ReplayTickSession<HypergraphStore>,
        FoundationContentBundleV1,
    ) -> Result<ProductionRuntime, RustPersistenceRuntimeErrorV1>,
) {
    let _ = value;
}

fn assert_runtime_open_signature(
    value: fn(&Config, CampaignId) -> Result<ProductionRuntime, RustPersistenceRuntimeErrorV1>,
) {
    let _ = value;
}

fn assert_runtime_advance_signature(
    value: fn(
        &mut ProductionRuntime,
        &mut CollectingSink,
        &OrderedPracticeActionBatchV1,
    ) -> Result<CommittedTickReceiptV1, RustPersistenceRuntimeErrorV1>,
) {
    let _ = value;
}

#[test]
fn cutover_exports_one_typed_runtime_and_prepared_tick_boundary() {
    assert_send::<DurableReplayRuntimeV1<HypergraphStore>>();
    assert_send::<PreparedCommittedTickV1>();
    assert_send::<ActivationReportV1>();
    assert_send::<CampaignFoundationV1>();
    assert_send::<CommittedFullCheckpointV1>();
    assert_send::<RustPersistenceActivationErrorV1>();
    assert_send::<RustPersistenceRuntimeErrorV1>();
    assert_send::<StableGraphRowsEmptyProofV1>();
    assert_send::<SuccessfulEventBatchEmptyProofV1>();
    assert_send::<ArchiveDirtyReceiptV1>();

    assert_activation_signature(activate_rust_persistence_v1);
    assert_foundation_hydration_signature(hydrate_campaign_foundation_v1);
    assert_prepare_signature(prepare_committed_tick_v1);
    assert_content_bundle_constructor(FoundationContentBundleV1::try_new);
    assert_foundation_capture_signature(CampaignFoundationV1::capture);
    assert_runtime_create_signature(ProductionRuntime::create);
    assert_runtime_open_signature(ProductionRuntime::open);
    assert_runtime_advance_signature(ProductionRuntime::advance_and_commit);

    let checkpoint_source = include_str!("../src/checkpoint.rs");
    let export_source = include_str!("../src/lib.rs");
    assert!(!checkpoint_source.contains("CheckpointRowsEmptyProofV1"));
    assert!(!export_source.contains("CheckpointRowsEmptyProofV1"));
}

#[test]
fn activation_ledger_and_runtime_receipts_are_typed_and_observable() {
    fn assert_ledger_row(row: &PersistenceAuthorityLedgerRowV1) {
        let _: u16 = row.ordinal();
        let _: PersistenceAuthorityStateV1 = row.state();
        let _: u16 = row.schema_epoch();
        let _: [u8; 32] = row.contract_sha256();
        let _: [u8; 32] = row.reader_contract_sha256();
        let _: Option<[u8; 32]> = row.predecessor_sha256();
    }

    fn assert_activation_report(report: &ActivationReportV1) {
        let _: &PersistenceAuthorityLedgerRowV1 = report.prepared_row();
        let _: &PersistenceAuthorityLedgerRowV1 = report.rust_active_row();
    }

    fn assert_runtime(runtime: &ProductionRuntime) {
        let _: &CampaignFoundationV1 = runtime.foundation();
        let _: &PersistenceAuthorityLedgerRowV1 = runtime.activation_row();
        let _: Option<CommittedResolveTickV1> = runtime.last_committed_tick();
    }

    fn assert_receipt(receipt: &CommittedTickReceiptV1) {
        let _: CommittedResolveTickV1 = receipt.resolve_tick();
        let _: TickContentHashV1 = receipt.tick_content_hash();
    }

    let _: [PersistenceAuthorityStateV1; 2] = [
        PersistenceAuthorityStateV1::Prepared,
        PersistenceAuthorityStateV1::RustActive,
    ];
    let _ = assert_ledger_row;
    let _ = assert_activation_report;
    let _ = assert_runtime;
    let _ = assert_receipt;
}

#[test]
fn only_an_identified_replay_report_can_prepare_semantic_rows() {
    assert_prepare_signature(prepare_committed_tick_v1);

    let source = std::fs::read_to_string(
        std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("src/runtime.rs"),
    )
    .expect("sole production persistence composition module");
    assert!(source.contains("IdentifiedTickReportV1"));
    assert!(source.contains("prepare_committed_tick_v1"));
    assert!(!source.contains("prepare_rules("));
    assert!(!source.contains("run_prepared_replay_tick("));
}

#[test]
fn campaign_foundation_retains_every_exact_replay_source() {
    fn assert_foundation_accessors(foundation: &CampaignFoundationV1) {
        let content: &FoundationContentBundleV1 = foundation.content_bundle();
        let _: &[u8] = content.scenario_source_bytes();
        let _: Option<&[u8]> = content.prelude_source_bytes();
        let _: &[u8] = content.rule_source_bytes();
        let _: &[u8] = content.defines_bytes();
        let _: &[u8] = content.reference_bundle_manifest_bytes();
        let _: &[u8] = foundation.stable_graph_bytes();
        let _: &[u8] = foundation.world_register_bytes();
        let _: &[u8] = foundation.resolver_manifest_bytes();
        let _: &[u8] = foundation.prepared_environment_bytes();
        let _: &ReplaySessionIdV1 = foundation.replay_session_identity();
        let _: ReplaySeed = foundation.rng_seed();
        let _: &ContentDigest = foundation.content_digest();
        let _: RefDigestV1 = foundation.reference_digest();
    }

    let _ = assert_foundation_accessors;
}

#[test]
fn durable_tick_numbers_refuse_a_synthetic_tick_zero() {
    assert_eq!(
        CommittedResolveTickV1::try_from(0_u64),
        Err(CommittedResolveTickErrorV1::SyntheticTickZero)
    );
    assert_eq!(
        CommittedResolveTickV1::try_from(1_u64)
            .expect("the first real executed tick")
            .get(),
        1
    );
    assert_eq!(
        CommittedResolveTickV1::try_from((i64::MAX as u64) + 1),
        Err(CommittedResolveTickErrorV1::OutOfPostgresRange)
    );
}

#[test]
fn reports_and_prepared_ticks_expose_every_named_semantic_producer() {
    fn assert_report_sources(report: &IdentifiedTickReportV1) {
        let _: &StableGraphStateV1 = report.result_stable_graph();
        let _: &MaterialStateRowsV1 = report.material_state_rows();
        let _: &SuccessfulEventBatchV1 = report.successful_event_batch();
    }

    fn assert_prepared_sources(prepared: &PreparedCommittedTickV1) {
        let _: &CheckpointRowsV1 = prepared.checkpoint_rows();
        let _: &ArchiveDirtyReceiptV1 = prepared.archive_dirty_receipt();
    }

    let _ = assert_report_sources;
    let _ = assert_prepared_sources;
}

#[test]
fn restart_roots_are_explicitly_full_checkpoints() {
    fn assert_full_checkpoint(checkpoint: &CommittedFullCheckpointV1) {
        assert_eq!(checkpoint.completeness(), CheckpointCompletenessV1::Full);
        let _: &[u8] = checkpoint.manifest_bytes();
        let _: &[CommittedCheckpointSectionV1] = checkpoint.sections();
    }

    fn assert_section(section: &CommittedCheckpointSectionV1) {
        let _: FullCheckpointSectionTagV1 = section.tag();
        let _: u32 = section.row_count();
        let _: [u8; 32] = section.sha256();
    }

    let _: [FullCheckpointSectionTagV1; 9] = [
        FullCheckpointSectionTagV1::StableGraph,
        FullCheckpointSectionTagV1::WorldRegisters,
        FullCheckpointSectionTagV1::ResolverManifest,
        FullCheckpointSectionTagV1::PreparedEnvironment,
        FullCheckpointSectionTagV1::ReplaySessionIdentity,
        FullCheckpointSectionTagV1::RngSeed,
        FullCheckpointSectionTagV1::ContentDigest,
        FullCheckpointSectionTagV1::ReferenceDigest,
        FullCheckpointSectionTagV1::SemanticState,
    ];
    let _ = assert_full_checkpoint;
    let _ = assert_section;
}

#[test]
fn production_no_longer_hydrates_or_commits_a_tick_zero_marker() {
    let writer = include_str!("../src/runtime.rs");
    let old_writer =
        std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("src/committed_tick_writer.rs");
    let old_contract = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("tests/committed_tick_writer_v1_contract.rs");
    let activation = std::fs::read_to_string(
        std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("migrations/0009_rust_persistence_activation.sql"),
    )
    .expect("epoch-9 activation migration");

    assert!(writer.contains("babylon_state.campaign_foundation"));
    assert!(!writer.contains("marker.resolve_tick = 0"));
    assert!(!writer.contains("committed tick-zero"));
    assert!(!old_writer.exists());
    assert!(!old_contract.exists());
    assert!(activation.contains("CHECK (resolve_tick >= 1)"));
}

#[test]
fn the_separate_schema_epoch_binary_has_been_absorbed() {
    let old_binary =
        std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("src/bin/babylon-schema-epoch.rs");
    assert!(
        !old_binary.exists(),
        "the production runtime must own the sole migration command"
    );
}
