use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_graph::state_hash::CanonicalState;

use babylon_persistence::michigan_content::MichiganContentPreset;
use babylon_persistence::michigan_material::MichiganDeliveryPreset;

use babylon_practice_contract::OrderedPracticeActionBatch;
use babylon_tick::material_replay::IdentifiedMaterialTick;
use babylon_tick::material_replay::{MaterialCommitError, MaterialReplaySession};
use babylon_tick::material_world;
use babylon_tick::material_world::MaterialWorldRegister;
use babylon_tick::replay_session::ReplayCommitDisposition;

fn session(preset: MichiganDeliveryPreset) -> MaterialReplaySession<HypergraphStore> {
    MichiganContentPreset::new_campaign(preset)
        .create_foundation(&crate::test_support::catalog())
        .expect("the authored catalog builds the foundation")
        .into_session()
        .expect("the fixture opens a session")
}
fn actions(session: &MaterialReplaySession<HypergraphStore>) -> OrderedPracticeActionBatch {
    OrderedPracticeActionBatch::empty(
        session.graph_session().session_identity().clone(),
        session.completed_tick() + 1,
    )
    .expect("the empty authored batch constructs")
}
#[test]
#[allow(
    clippy::too_many_lines,
    reason = "`material_commit_failure_leaves_graph_circuit_world_time_and_sink_unchanged` keeps one authored boundary's fixture and assertions together"
)]
fn material_commit_failure_leaves_graph_circuit_world_time_and_sink_unchanged() {
    for preset in [
        MichiganDeliveryPreset::Standard,
        MichiganDeliveryPreset::SharedFreightAmple,
        MichiganDeliveryPreset::SharedFreightConstrained,
    ] {
        let mut session = session(preset);
        let graph = session
            .graph_session()
            .graph()
            .state_hash()
            .expect("the fixture graph hashes its state");
        let register = session.material().canonical_bytes().to_vec();
        let world = session
            .current_world_hash()
            .expect("the committed session publishes a world hash");
        let candidate = session
            .prepare_advance(&actions(&session))
            .expect("the session prepares the authored advance");
        let prepared_receipt_bytes = candidate.material().receipt_bytes().to_vec();
        let receipts = material_world::decode_material_receipts(&prepared_receipt_bytes)
            .expect("the canonical bytes decode into the declared type");
        let catalog = crate::test_support::catalog();
        let (sheet, meal) = if preset == MichiganDeliveryPreset::SharedFreightConstrained {
            (120, 40)
        } else {
            (320, 80)
        };
        for (key, expected) in [("sheet-transfer", sheet), ("food-transfer", meal)] {
            let order_id = catalog
                .routes()
                .iter()
                .find(|route| route.key == key)
                .expect("the fixture holds the searched element")
                .order_id();
            assert_eq!(
                receipts
                    .dispatches
                    .iter()
                    .find(|row| row.order_id == order_id)
                    .expect("the fixture holds the searched element")
                    .quantity,
                expected
            );
        }
        let hash = candidate.identity().tick_content_hash();
        let mut sink = CollectingSink::default();
        let refused = session.commit_prepared_and_publish(&mut sink, candidate, |_, _| {
            Err::<ReplayCommitDisposition, _>("refused before marker")
        });
        assert!(matches!(
            refused,
            Err(MaterialCommitError::Commit("refused before marker"))
        ));
        assert_eq!(session.completed_tick(), 0);
        assert_eq!(session.material().canonical_bytes(), register);
        assert_eq!(
            session
                .graph_session()
                .graph()
                .state_hash()
                .expect("the fixture graph hashes its state"),
            graph
        );
        assert_eq!(
            session
                .current_world_hash()
                .expect("the committed session publishes a world hash"),
            world
        );
        assert!(sink.events.is_empty());
        let retry = session
            .prepare_advance(&actions(&session))
            .expect("the session prepares the authored advance");
        assert_eq!(retry.identity().tick_content_hash(), hash);
        assert_eq!(retry.material().receipt_bytes(), prepared_receipt_bytes);
        let (ack, _) = session
            .commit_prepared_and_publish(&mut sink, retry, |_, _| {
                Ok::<_, ()>(ReplayCommitDisposition::Committed)
            })
            .expect("the prepared period commits");
        assert_eq!(session.completed_tick(), 1);
        assert_eq!(session.graph_session().completed_tick(), 1);
        assert_ne!(
            session
                .graph_session()
                .graph()
                .state_hash()
                .expect("the fixture graph hashes its state"),
            graph
        );
        assert_ne!(
            session
                .current_world_hash()
                .expect("the committed session publishes a world hash"),
            world
        );
        assert_eq!(
            ack.result_world_hash(),
            session
                .current_world_hash()
                .expect("the committed session publishes a world hash")
        );
    }
}
#[test]
fn staffed_arrival_feeds_following_commitments_past_the_former_campaign_expiry() {
    let mut fast = session(MichiganDeliveryPreset::Standard);
    let mut slow = session(MichiganDeliveryPreset::Delayed);
    assert_eq!(
        fast.graph_session()
            .graph()
            .state_hash()
            .expect("the fixture graph hashes its state"),
        slow.graph_session()
            .graph()
            .state_hash()
            .expect("the fixture graph hashes its state")
    );
    let mut first_fast_delivery = None;
    let mut first_slow_delivery = None;
    for tick in 1..=18 {
        for (session, first) in [
            (&mut fast, &mut first_fast_delivery),
            (&mut slow, &mut first_slow_delivery),
        ] {
            let candidate = session
                .prepare_advance(&actions(session))
                .expect("the session prepares the authored advance");
            let receipts =
                material_world::decode_material_receipts(candidate.material().receipt_bytes())
                    .expect("the canonical bytes decode into the declared type");
            assert_eq!(receipts.resolve_tick, tick);
            let decoded = MaterialWorldRegister::decode_external(
                session.catalog(),
                candidate.material().register().canonical_bytes().to_vec(),
            )
            .expect("the committed canonical bytes decode");
            assert_eq!(&decoded, candidate.material().register());
            for produced in &receipts.production {
                let prior = session
                    .material()
                    .state()
                    .production_commitments
                    .iter()
                    .find(|row| {
                        row.period == tick
                            && row.process_id == produced.process_id
                            && row.site_id == produced.site_id
                    });
                assert_eq!(
                    prior.map_or(0, |row| row.planned_batches),
                    produced.planned_batches
                );
                assert!(produced.produced_batches <= produced.planned_batches);
            }
            if !receipts.deliveries.is_empty() {
                first.get_or_insert(tick);
            }
            session
                .commit_prepared_and_publish(&mut CollectingSink::default(), candidate, |_, _| {
                    Ok::<_, ()>(ReplayCommitDisposition::Committed)
                })
                .expect("the prepared period commits");
        }
    }
    assert!(first_fast_delivery.is_some());
    assert!(first_slow_delivery.is_some());
    assert_eq!(fast.completed_tick(), 18);
    assert_eq!(slow.completed_tick(), 18);
}

#[test]
fn committed_identity_can_publish_without_heap_allocation() {
    fn requires_copy<T: Copy>() {}
    requires_copy::<IdentifiedMaterialTick>();
    let session = session(MichiganDeliveryPreset::Standard);
    let candidate = session
        .prepare_advance(&actions(&session))
        .expect("the session prepares the authored advance");
    let identity = *candidate.identity();
    assert_eq!(
        IdentifiedMaterialTick::decode(identity.canonical_bytes())
            .expect("the committed canonical bytes decode"),
        identity
    );
}

#[path = "support/material_config.rs"]
mod test_support;
