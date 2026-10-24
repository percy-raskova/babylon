use super::runtime::{DurableMaterialRuntime, MaterialRuntimeFoundation};
use crate::identity::CampaignId;
use crate::michigan_content::MichiganContentPreset;
use crate::michigan_material::MichiganDeliveryPreset;
use crate::michigan_material::MichiganMaterialCatalog;
use crate::{material_storage, CommittedTickReceipt};
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_practice_contract::OrderedPracticeActionBatch;
use babylon_tick::replay_session::ReplayCommitDisposition;
use postgres::Config;
use std::convert::Infallible;
use uuid::Uuid;

fn foundation() -> MaterialRuntimeFoundation {
    let catalog = MichiganMaterialCatalog::from_defines_toml(include_str!(
        "../../../../../content/scenarios/michigan/defines.toml"
    ))
    .expect("the authored input admits the derived value");
    MichiganContentPreset::new_campaign(MichiganDeliveryPreset::Standard)
        .create_foundation(&catalog)
        .expect("the authored catalog builds the foundation")
}

fn runtime() -> DurableMaterialRuntime {
    let foundation = foundation();
    let opening_bytes = foundation.initial_register().shared_canonical_bytes();
    let lookup = material_storage::seed(opening_bytes.as_slice())
        .expect("the fixture seeds the authored rows");
    let lookup_chain = material_storage::initial_lookup_chain(&lookup)
        .expect("the opening register builds its first lookup chain");
    DurableMaterialRuntime {
        config: Config::new(),
        campaign: CampaignId::from_uuid(Uuid::nil()),
        session: foundation
            .into_session()
            .expect("the fixture opens a session"),
        lookup,
        lookup_chain,
        tail: None,
        last_receipt: None,
        last_choice_receipts: Vec::new(),
    }
}

fn publish(runtime: &mut DurableMaterialRuntime) -> CommittedTickReceipt {
    let actions = OrderedPracticeActionBatch::empty(
        runtime.session.graph_session().session_identity().clone(),
        runtime.session.completed_tick() + 1,
    )
    .expect("the empty authored batch constructs");
    let candidate = runtime
        .session
        .prepare_advance(&actions)
        .expect("the session prepares the authored advance");
    let receipt = CommittedTickReceipt::from_material_candidate(&candidate)
        .expect("the authored input admits the derived value");
    let choices = candidate.graph_report().report().choice_receipts.clone();
    assert_eq!(
        receipt.tick_content_hash(),
        candidate.identity().tick_content_hash()
    );
    assert_eq!(
        receipt.world_before(),
        candidate.identity().prior_world_hash()
    );
    assert_eq!(
        receipt.world_after(),
        candidate.identity().result_world_hash()
    );
    assert_eq!(
        receipt.considered(),
        candidate.graph_report().report().considered
    );
    assert_eq!(receipt.fired(), candidate.graph_report().report().fired);
    let (ack, _) = runtime
        .session
        .commit_prepared_and_publish(&mut CollectingSink::default(), candidate, |_| {
            Ok::<_, Infallible>(ReplayCommitDisposition::Committed)
        })
        .expect("the prepared period commits");
    runtime.tail = Some(ack);
    runtime.last_receipt = Some(receipt.clone());
    runtime.last_choice_receipts = choices;
    receipt
}

#[test]
fn diagnostics_bind_the_acknowledged_material_world_and_current_graph() {
    let mut runtime = runtime();
    assert!(runtime.diagnostic_receipt().is_none());
    let before = runtime.observe_current_stable_graph_state().expect(
        "the fixture call `observe_current_stable_graph_state` succeeds for the authored inputs",
    );
    let receipt = publish(&mut runtime);
    assert_eq!(
        before.digest().as_bytes(),
        &receipt.prior_stable_graph_digest()
    );
    let graph = runtime.observe_committed_graph_state(&receipt).expect(
        "the fixture call `observe_committed_graph_state` succeeds for the authored inputs",
    );
    assert_eq!(
        graph.digest().as_bytes(),
        &receipt.result_stable_graph_digest()
    );
    assert_eq!(
        runtime
            .session
            .current_world_hash()
            .expect("the committed session publishes a world hash"),
        receipt.world_after()
    );
    assert_eq!(runtime.diagnostic_receipt(), Some(&receipt));
    assert_eq!(
        runtime
            .observe_committed_choice_receipts(&receipt)
            .expect("the fixture call `observe_committed_choice_receipts` succeeds for the authored inputs")
            .len(),
        receipt.choice_receipt_count()
    );
}

#[test]
fn stale_and_process_absent_details_cannot_be_observed_as_current() {
    let mut runtime = runtime();
    let receipt = publish(&mut runtime);
    // Restart can authenticate the graph without inventing process-local details.
    runtime.last_receipt = None;
    runtime.last_choice_receipts.clear();
    assert!(runtime.observe_committed_graph_state(&receipt).is_ok());
    assert!(runtime.observe_committed_choice_receipts(&receipt).is_err());
    publish(&mut runtime);
    assert!(runtime.observe_committed_graph_state(&receipt).is_err());
    assert!(runtime.observe_committed_choice_receipts(&receipt).is_err());
}
