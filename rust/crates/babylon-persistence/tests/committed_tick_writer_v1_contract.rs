//! Public contract for the closed-authority committed-tick writer and read-only hydration seam.

use babylon_persistence::committed_tick_envelope::CommittedTickEnvelopeV1;
use babylon_persistence::committed_tick_storage::CampaignStorageRowV1;
use babylon_persistence::committed_tick_writer::{
    commit_committed_tick_v1, CommittedTickCommitDispositionV1, CommittedTickCommitReportV1,
    CommittedTickHydratedMarkerV1, CommittedTickHydratedRowV1, CommittedTickHydrationPlanV1,
    CommittedTickHydrationV1, CommittedTickWriteErrorV1,
};
use babylon_persistence::writer_gate::RustWriterAuthority;
use postgres::Config;

fn assert_error<T: std::error::Error + Send + Sync>() {}

fn assert_closed_writer_signature(
    _writer: for<'campaign, 'envelope> fn(
        &Config,
        &RustWriterAuthority,
        CampaignStorageRowV1<'campaign>,
        &'envelope CommittedTickEnvelopeV1,
    ) -> Result<
        CommittedTickCommitReportV1,
        CommittedTickWriteErrorV1,
    >,
) {
}

fn assert_checkpoint_identity_signature(
    _identity: for<'hydration> fn(
        &'hydration CommittedTickHydrationV1,
    ) -> Option<CommittedTickHydratedMarkerV1>,
) {
}

#[test]
fn writer_requires_the_closed_authority_capability_and_a_thread_safe_error() {
    assert_closed_writer_signature(commit_committed_tick_v1);
    assert_error::<CommittedTickWriteErrorV1>();
}

#[test]
fn commit_acknowledgements_have_closed_direct_idempotent_and_reconciled_dispositions() {
    let dispositions = [
        CommittedTickCommitDispositionV1::Committed,
        CommittedTickCommitDispositionV1::AlreadyCommitted,
        CommittedTickCommitDispositionV1::ReconciledAfterAmbiguousCommit,
    ];

    assert_eq!(dispositions.len(), 3);
    assert_ne!(dispositions[0], dispositions[1]);
    assert_ne!(dispositions[1], dispositions[2]);
}

#[test]
fn commit_acknowledgement_requires_synchronous_wal_flush() {
    let source = include_str!("../src/committed_tick_writer.rs");

    assert!(source.contains("SET LOCAL synchronous_commit TO on"));
    assert!(source.contains("(\"synchronous_commit\", \"on\")"));
    assert!(!source.contains("SET LOCAL synchronous_commit TO off"));
}

#[test]
fn acknowledged_commit_returns_without_a_followup_database_operation() {
    let source = include_str!("../src/committed_tick_writer.rs");
    let attempt_start = source
        .find("fn attempt_commit_using<Probe>(")
        .expect("commit attempt function");
    let attempt_end = source[attempt_start..]
        .find("\nfn write_transaction_using<Probe>(")
        .map(|offset| attempt_start + offset)
        .expect("write transaction boundary");
    let attempt = &source[attempt_start..attempt_end];
    let acknowledged_start = attempt
        .find("                Ok(()) => {")
        .expect("successful commit response");
    let acknowledged_end = attempt[acknowledged_start..]
        .find("\n                Err(error)")
        .map(|offset| acknowledged_start + offset)
        .expect("failed commit response boundary");
    let acknowledged = &attempt[acknowledged_start..acknowledged_end];

    assert!(acknowledged.contains("CommitTransactionBoundaryV1::after(commit_step)"));
    assert!(acknowledged.contains("Ok(CommitAttempt::Committed)"));
    assert!(!acknowledged.contains("client."));
    assert!(!acknowledged.contains("simple_query"));
}

#[test]
fn hydration_plan_owns_exact_ordered_checkpoint_rows_and_bounded_tail() {
    let plan = CommittedTickHydrationPlanV1::compose(
        12,
        Some(10),
        vec![
            CommittedTickHydratedRowV1::new(vec![0x01], vec![0xa1]).unwrap(),
            CommittedTickHydratedRowV1::new(vec![0x02], vec![0xa2]).unwrap(),
        ],
        vec![11, 12],
    )
    .expect("ordered bounded hydration plan");

    assert_eq!(plan.last_committed_tick(), 12);
    assert_eq!(plan.checkpoint_tick(), Some(10));
    assert_eq!(plan.checkpoint_rows()[0].key(), &[0x01]);
    assert_eq!(plan.checkpoint_rows()[1].payload(), &[0xa2]);
    assert_eq!(plan.replay_tail(), &[11, 12]);
}

#[test]
fn hydration_exposes_the_checkpoint_commit_identity_even_when_no_tail_exists() {
    assert_checkpoint_identity_signature(CommittedTickHydrationV1::checkpoint_marker);
}

#[test]
fn opaque_checkpoint_hydration_uses_only_the_tick_zero_foundation() {
    let source = include_str!("../src/committed_tick_writer.rs");
    let start = source
        .find("const READ_FOUNDATION_CHECKPOINT_SQL")
        .expect("foundation checkpoint query");
    let end = source[start..]
        .find("const READ_REPLAY_TAIL_SQL")
        .map(|offset| start + offset)
        .expect("replay-tail query boundary");
    let query = &source[start..end];

    assert!(query.contains("marker.resolve_tick = 0"));
    assert!(!query.contains("ORDER BY marker.resolve_tick DESC"));
}

#[test]
fn family_insertion_uses_one_binary_copy_protocol_not_one_command_per_row() {
    let source = include_str!("../src/committed_tick_writer.rs");
    let start = source
        .find("fn insert_batch(")
        .expect("insert batch function");
    let end = source[start..]
        .find("\nfn insert_marker(")
        .map(|offset| start + offset)
        .expect("insert marker boundary");
    let insert_batch = &source[start..end];

    assert!(insert_batch.contains("BinaryCopyInWriter::new"));
    assert!(insert_batch.contains("FROM STDIN BINARY"));
    assert!(insert_batch.contains(".copy_in("));
    assert!(insert_batch.contains(".finish()"));
    assert!(!insert_batch.contains("transaction.execute"));
}
