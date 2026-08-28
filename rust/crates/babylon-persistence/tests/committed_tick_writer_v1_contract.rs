//! Public contract for the closed-authority committed-tick writer and read-only hydration seam.

use babylon_persistence::committed_tick_envelope::CommittedTickEnvelopeV1;
use babylon_persistence::committed_tick_storage::CampaignStorageRowV1;
use babylon_persistence::committed_tick_writer::{
    commit_committed_tick_v1, CommittedTickCommitDispositionV1, CommittedTickCommitReportV1,
    CommittedTickHydratedRowV1, CommittedTickHydrationPlanV1, CommittedTickWriteErrorV1,
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
