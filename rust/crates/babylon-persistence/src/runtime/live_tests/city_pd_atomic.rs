//! Real paid-visit transaction failure and acknowledgement recovery.

use super::TestDatabase;
use crate::economic_catalog::{self, CapturedEconomicCatalog};
use crate::identity::CampaignId;
use crate::material_runtime::{
    CommitFault, DurableMaterialRuntime, MaterialRuntimeError, COMMIT_FAULT,
};
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};
use babylon_material_circuit::AgencyAttendanceOutcome;
use babylon_practice_contract::OrderedPracticeActionBatch;
use babylon_practice_contract::OrganizerAllocation;
use babylon_practice_contract::{OrganizerChoice, OrganizerCommand};
use babylon_tick::replay_session::ReplayCommitDisposition;
use postgres::{Client, NoTls};
use uuid::Uuid;

fn assert_marker_rollback(
    runtime: &mut DurableMaterialRuntime,
    owner: &mut Client,
    campaign: CampaignId,
    actions: &OrderedPracticeActionBatch,
    sink: &mut CollectingSink,
) {
    let before = runtime.session().material().canonical_bytes().to_vec();
    let before_hash = runtime.session().current_world_hash().expect("P1 hash");
    COMMIT_FAULT.with(|slot| slot.set(Some(CommitFault::MarkerTrigger)));
    assert!(matches!(
        runtime.advance_and_commit(sink, actions),
        Err(MaterialRuntimeError::Database(_))
    ));
    assert_eq!(
        COMMIT_FAULT.with(|slot| slot.replace(None)),
        None,
        "fault reached the marker"
    );
    assert_eq!(runtime.session().completed_tick(), 1);
    assert_eq!(runtime.session().material().canonical_bytes(), before);
    assert_eq!(
        runtime
            .session()
            .current_world_hash()
            .expect("unchanged hash"),
        before_hash
    );
    assert_eq!(sink.events.len(), 0);
    let counts: (i64, i64, i64, i64) = {
        let row = owner.query_one("SELECT (SELECT count(*) FROM babylon_state.tick_commit WHERE campaign_id=$1 AND resolve_tick=2), (SELECT count(*) FROM babylon_state.material_tick_v3 WHERE campaign_id=$1 AND resolve_tick=2), (SELECT count(*) FROM babylon_state.organizer_encounter_v1 WHERE campaign_id=$1), (SELECT count(*) FROM babylon_meta.archive_knowledge_grant_v1 WHERE campaign_id=$1 AND grant_key LIKE 'city-pd-%')", &[campaign.as_uuid()]).expect("rolled-back rows");
        (row.get(0), row.get(1), row.get(2), row.get(3))
    };
    assert_eq!(counts, (0, 0, 0, 0));
}

fn assert_paid_projection(runtime: &DurableMaterialRuntime, contact: [u8; 32]) {
    let [attempt] = runtime
        .session()
        .material()
        .city_pd()
        .expect("PD")
        .attempts
        .as_slice()
    else {
        panic!("exactly one attempted visit")
    };
    assert_eq!(attempt.funding.outcome, AgencyAttendanceOutcome::Paid);
    assert_eq!(attempt.funding.paid.micro_units(), 24_000_000);
    assert_eq!(attempt.receipt.acquired_public_fact_ids, vec![contact]);
    assert!(attempt.receipt.shift_receipt_id.is_some());
    assert!(attempt.receipt.payment_receipt_id.is_some());
    assert_eq!(
        runtime
            .organizer_snapshot()
            .expect("visible check-in")
            .city_pd_encounters
            .len(),
        1
    );
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and national source"]
fn paid_visit_marker_failure_and_ambiguous_retry_are_atomic() {
    let base = super::validated_base_config();
    let database = TestDatabase::create_from_template(
        &base,
        &super::validated_template_name(),
        "citypdatomic",
    );
    let config = database.config(&base);
    let campaign = CampaignId::from_uuid(Uuid::from_u128(0x0026_1631_7034));
    let foundation = CapturedEconomicCatalog::capture_national_campaign(
        economic_catalog::national_catalog_input(),
        campaign,
    )
    .expect("captured national source")
    .create_foundation(
        ReplaySessionId::try_from("national-city-pd-atomic").expect("session"),
        ReplaySeed::new(319),
    )
    .expect("foundation");
    let digest = foundation.digest();
    let mut runtime =
        DurableMaterialRuntime::create(&config, campaign, foundation).expect("opening");
    let snapshot = runtime.organizer_snapshot().expect("opening snapshot");
    let command = OrganizerCommand {
        allocation: OrganizerAllocation::None,
        campaign_id: *campaign.canonical_bytes(),
        actor_id: snapshot.view.actor_id,
        authority_id: snapshot.view.authority_id,
        expected_period: snapshot.view.period,
        content_digest: snapshot.view.content_digest,
        resource_digest: snapshot.view.resource_digest,
        nonce: [77; 16],
        choice: OrganizerChoice::Reinforce,
    };
    runtime
        .submit_organizer_command(&command)
        .expect("contact command");
    let mut sink = CollectingSink::default();
    let actions = runtime.next_action_batch().expect("P1 actions");
    runtime
        .advance_and_commit(&mut sink, &actions)
        .expect("P1 contact and funding");
    let contact = runtime
        .session()
        .material()
        .public_venue()
        .expect("venue")
        .records
        .iter()
        .find(|record| {
            matches!(
                record.kind,
                babylon_practice_contract::PublicVenueRecordKind::ContactCompleted { .. }
            )
        })
        .expect("actual P1 public contact")
        .source_id;
    let mut stale =
        DurableMaterialRuntime::open(&config, campaign, digest).expect("P1 retry session");
    let mut owner = config.connect(NoTls).expect("writer");
    let actions = runtime.next_action_batch().expect("P2 actions");
    let mut sink = CollectingSink::default();
    assert_marker_rollback(&mut runtime, &mut owner, campaign, &actions, &mut sink);
    COMMIT_FAULT.with(|slot| slot.set(Some(CommitFault::AfterCommit)));
    let identity = runtime
        .advance_and_commit(&mut sink, &actions)
        .expect("ambiguous commit reconciles");
    assert_eq!(
        runtime
            .diagnostic_receipt()
            .expect("diagnostic")
            .commit_disposition(),
        ReplayCommitDisposition::ReconciledAfterAmbiguousCommit
    );
    assert_paid_projection(&runtime, contact);
    let retry = stale
        .advance_and_commit(&mut CollectingSink::default(), &actions)
        .expect("stale exact retry reconciles");
    assert_eq!(retry, identity);
    assert_eq!(
        stale.session().material().canonical_bytes(),
        runtime.session().material().canonical_bytes()
    );
    let row = owner.query_one("SELECT (SELECT count(*) FROM babylon_state.organizer_encounter_v1 WHERE campaign_id=$1), (SELECT count(*) FROM babylon_meta.archive_knowledge_grant_witness_v1 WHERE campaign_id=$1 AND grant_key LIKE 'city-pd-%' AND provenance_source_id='committed-public-venue-check-in-v1')", &[campaign.as_uuid()]).expect("exact committed projection and citation");
    assert_eq!((row.get::<_, i64>(0), row.get::<_, i64>(1)), (1, 1));
    let reopened = DurableMaterialRuntime::open(&config, campaign, digest).expect("cold reopen");
    assert_eq!(reopened.tail(), Some(&identity));
    assert_eq!(
        reopened.session().material().canonical_bytes(),
        runtime.session().material().canonical_bytes()
    );
    assert_eq!(
        reopened.organizer_snapshot().expect("reopened check-in"),
        runtime.organizer_snapshot().expect("continuous check-in")
    );
}
