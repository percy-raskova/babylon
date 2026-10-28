use super::snapshot::{MaterialHistory, MaterialObservationRow};
use crate::economic_content::EconomicContentAdmission;
use crate::identity::CampaignId;
use crate::material_storage::OpeningRegister;
use crate::michigan_content::MichiganContentPreset;
use crate::michigan_material::MichiganMaterialCatalog;
use crate::production_projection;
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_practice_contract::OrderedPracticeActionBatch;
use babylon_tick::material_replay::PreparedMaterialTick;
use babylon_tick::material_world::MaterialWorldRegister;
use babylon_tick::replay_session::ReplayCommitDisposition;
use uuid::Uuid;

#[test]
fn admitted_opening_row_reuses_its_canonical_owner_and_refuses_altered_evidence() {
    let catalog = crate::test_support::catalog();
    let expected = MichiganContentPreset::FourWeekStandard
        .admitted(&catalog)
        .expect("the fixture admits the authored value");
    let campaign = CampaignId::from_uuid(Uuid::from_u128(339));
    let opening = MaterialObservationRow {
        row_campaign: *campaign.as_uuid(),
        row_tick: 0,
        register_storage_bytes: expected.initial_register().canonical_bytes().to_vec(),
        lookup_delta: None,
        receipts: None,
        identity: None,
        content_hash: None,
    };
    let mut history = MaterialHistory::new(&expected)
        .expect("the constructor accepts the authored fixture arguments");
    assert!(std::ptr::eq(
        history.register(&expected).state(),
        expected.initial_register().state()
    ));
    let canonical_owner = history.register(&expected).canonical_bytes().as_ptr();
    history
        .append_decoded(campaign, &expected, 0, opening.clone())
        .expect("the fixture call `append_decoded` succeeds for the authored inputs");
    // Admission of identical, already validated opening bytes must not allocate
    // a second canonical register owner at national scale.
    assert_eq!(
        history.register(&expected).canonical_bytes().as_ptr(),
        canonical_owner
    );
    assert!(std::ptr::eq(
        history.register(&expected),
        expected.initial_register()
    ));
    assert!(history.opening.is_none());
    assert!(history.receipt.is_none());
    assert!(history.prior_world.is_none());

    let mut wrong_campaign = opening.clone();
    wrong_campaign.row_campaign = Uuid::from_u128(340);
    let mut wrong_period = opening.clone();
    wrong_period.row_tick = 1;
    let mut trailing_register = opening.clone();
    trailing_register.register_storage_bytes.push(0);
    let mut changed_register = opening.clone();
    changed_register.register_storage_bytes[0] ^= 1;
    let mut different_opening = opening.clone();
    different_opening.register_storage_bytes = MichiganContentPreset::FourWeekDelayed
        .admitted(&catalog)
        .expect("the fixture admits the authored value")
        .initial_register()
        .canonical_bytes()
        .to_vec();
    let mut lookup = opening.clone();
    lookup.lookup_delta = Some(Vec::new());
    let mut receipt = opening.clone();
    receipt.receipts = Some(Vec::new());
    let mut identity = opening.clone();
    identity.identity = Some(Vec::new());
    let mut content = opening;
    content.content_hash = Some(Vec::new());
    for refused in [
        wrong_campaign,
        wrong_period,
        trailing_register,
        changed_register,
        different_opening,
        lookup,
        receipt,
        identity,
        content,
    ] {
        let mut candidate = MaterialHistory::new(&expected)
            .expect("the constructor accepts the authored fixture arguments");
        let original_owner = candidate.register(&expected).canonical_bytes().as_ptr();
        let original_chain = candidate.lookup_chain;
        assert!(candidate
            .append_decoded(campaign, &expected, 0, refused)
            .is_err());
        assert_eq!(
            candidate.register(&expected).canonical_bytes().as_ptr(),
            original_owner
        );
        assert!(std::ptr::eq(
            candidate.register(&expected),
            expected.initial_register()
        ));
        assert_eq!(candidate.lookup_chain, original_chain);
        assert!(candidate.opening.is_none());
        assert!(candidate.receipt.is_none());
        assert!(candidate.prior_world.is_none());
    }
}

#[test]
#[allow(
    clippy::too_many_lines,
    reason = "`continuous_cursor_replays_beyond_sixteen_and_refuses_a_broken_tail` keeps one authored boundary's fixture and assertions together"
)]
fn continuous_cursor_replays_beyond_sixteen_and_refuses_a_broken_tail() {
    let catalog = MichiganMaterialCatalog::from_defines_toml(include_str!(
        "../../../../../content/scenarios/michigan/defines.toml"
    ))
    .expect("the authored input admits the derived value");
    let preset = MichiganContentPreset::FourWeekStandard;
    let expected = preset
        .admitted(&catalog)
        .expect("the fixture admits the authored value");
    let mut session = preset
        .create_foundation(&catalog)
        .expect("the authored catalog builds the foundation")
        .into_session()
        .expect("the fixture opens a session");
    let campaign = CampaignId::from_uuid(Uuid::from_u128(338));
    let mut history = MaterialHistory::new(&expected)
        .expect("the constructor accepts the authored fixture arguments");
    let expected_lookup = OpeningRegister::from_opening(expected.initial_register())
        .expect("the opening register admits its sections");
    let foundation = MaterialObservationRow {
        row_campaign: *campaign.as_uuid(),
        row_tick: 0,
        register_storage_bytes: expected.initial_register().canonical_bytes().to_vec(),
        lookup_delta: None,
        receipts: None,
        identity: None,
        content_hash: None,
    };
    history
        .append_decoded(campaign, &expected, 0, foundation.clone())
        .expect("the fixture call `append_decoded` succeeds for the authored inputs");
    let mut rows = vec![foundation];
    for period in 1..=20 {
        let actions = OrderedPracticeActionBatch::empty(
            session.graph_session().session_identity().clone(),
            period,
        )
        .expect("the empty authored batch constructs");
        let next = session
            .prepare_advance(&actions)
            .expect("the session prepares the authored advance");
        if period == 17 {
            verify_restart(&catalog, preset, &next);
        }
        let encoded = crate::material_storage::encode(
            next.material().register(),
            next.material().receipt_bytes(),
            &history.lookup,
            history.lookup_chain,
        )
        .expect("the fixture value encodes canonically");
        let row = MaterialObservationRow {
            row_campaign: *campaign.as_uuid(),
            row_tick: i64::try_from(period).expect("the fixture value fits the target range"),
            register_storage_bytes: encoded.register_storage_bytes,
            lookup_delta: Some(encoded.lookup_delta_bytes),
            receipts: Some(encoded.receipt_storage_bytes),
            identity: Some(next.identity().canonical_bytes().to_vec()),
            content_hash: Some(next.identity().tick_content_hash().as_bytes().to_vec()),
        };
        verify_refusals(campaign, &expected, &row, &history);
        assert_eq!(history.register.completed_tick(), period - 1);
        history
            .append_decoded(campaign, &expected, period, row.clone())
            .expect("the fixture call `append_decoded` succeeds for the authored inputs");
        if period == 1 {
            assert!(std::ptr::eq(
                history
                    .opening(&expected)
                    .expect("the fixture call `opening` succeeds for the authored inputs"),
                expected.initial_register()
            ));
        }
        rows.push(row);
        verify_published_period(&history, &expected, &expected_lookup, period);
        session
            .commit_prepared_and_publish(&mut CollectingSink::default(), next, |_, _| {
                Ok::<_, ()>(ReplayCommitDisposition::Committed)
            })
            .expect("the prepared period commits");
    }
    let mut cold = MaterialHistory::new(&expected)
        .expect("the constructor accepts the authored fixture arguments");
    for (period, row) in rows.into_iter().enumerate() {
        cold.append_decoded(
            campaign,
            &expected,
            u64::try_from(period).expect("the fixture value fits the target range"),
            row,
        )
        .expect("the fixture call `append_decoded` succeeds for the authored inputs");
    }
    assert_eq!(cold.register, history.register);
    assert_eq!(cold.receipt, history.receipt);
    let project = |value: &MaterialHistory| {
        production_projection::project_economic_current(
            expected.view(),
            expected.material_catalog(),
            value.register(&expected),
            value.opening(&expected),
            value.receipt(),
            &value.orders,
        )
        .expect("the fixture projection accepts the authored input")
    };
    assert_eq!(project(&cold), project(&history));
    assert!(project(&history)
        .events
        .iter()
        .all(|event| event.period == 20));
}

fn verify_published_period(
    history: &MaterialHistory,
    expected: &EconomicContentAdmission,
    expected_lookup: &OpeningRegister,
    period: u64,
) {
    assert_eq!(
        history.lookup.lookup().entries(),
        expected_lookup.lookup().entries()
    );
    assert_eq!(
        history
            .opening
            .as_ref()
            .expect("the fixture set the optional field before this read")
            .completed_tick(),
        period - 1
    );
    assert_eq!(
        history
            .receipt
            .as_ref()
            .expect("the fixture set the optional field before this read")
            .0
            .resolve_tick,
        period
    );
    assert!(history
        .register(expected)
        .state()
        .capacities
        .iter()
        .all(|capacity| capacity.period == period + 1));
}

fn verify_refusals(
    campaign: CampaignId,
    expected: &EconomicContentAdmission,
    row: &MaterialObservationRow,
    history: &MaterialHistory,
) {
    let admitted_owner = history.clone();
    let period = u64::try_from(row.row_tick).expect("the fixture value fits the target range");
    let mut damaged = row.clone();
    damaged
        .lookup_delta
        .as_mut()
        .expect("the fixture set the optional field before this borrow")
        .push(0);
    let mut absent = row.clone();
    absent.lookup_delta = None;
    let mut wrong_hash = row.clone();
    wrong_hash
        .content_hash
        .as_mut()
        .expect("the fixture set the optional field before this borrow")[0] ^= 1;
    let mut missing_receipts = row.clone();
    missing_receipts.receipts = None;
    let mut wrong_period = row.clone();
    let delta = wrong_period
        .lookup_delta
        .as_mut()
        .expect("the fixture set the optional field before this borrow");
    let offset = crate::material_storage::LOOKUP_DOMAIN.len() + 2 + 32;
    delta[offset..offset + 8].copy_from_slice(&(period + 1).to_be_bytes());
    for refused in [damaged, absent, wrong_hash, missing_receipts, wrong_period] {
        let mut candidate = history.clone();
        assert!(candidate
            .append_decoded(campaign, expected, period, refused)
            .is_err());
        assert_eq!(
            candidate.lookup.lookup().entries(),
            history.lookup.lookup().entries()
        );
        assert_eq!(candidate.lookup_chain, history.lookup_chain);
        assert_eq!(
            candidate.previous_lookup_chain,
            history.previous_lookup_chain
        );
        assert_eq!(candidate.register, history.register);
        // A refused detached read can discard obsolete state, but it cannot
        // change the previously admitted owner that remains available to play.
        assert_eq!(history.opening, admitted_owner.opening);
        assert_eq!(history.receipt, admitted_owner.receipt);
        assert_eq!(candidate.prior_world, history.prior_world);
    }
}

fn verify_restart(
    catalog: &MichiganMaterialCatalog,
    preset: MichiganContentPreset,
    next: &PreparedMaterialTick<HypergraphStore>,
) {
    let mut resumed = preset
        .create_foundation(catalog)
        .expect("the authored catalog builds the foundation")
        .into_session()
        .expect("the fixture opens a session");
    resumed
        .restore_full_checkpoint(
            next.graph_report().result_stable_graph(),
            next.graph_report().material_state_rows(),
            next.graph_report().result_registers().canonical_bytes(),
            MaterialWorldRegister::decode_external(
                resumed.catalog(),
                next.material().register().canonical_bytes().to_vec(),
            )
            .expect("the committed canonical bytes decode"),
        )
        .expect("the committed checkpoint restores");
    assert_eq!(resumed.completed_tick(), 17);
    let subsequent =
        OrderedPracticeActionBatch::empty(resumed.graph_session().session_identity().clone(), 18)
            .expect("the empty authored batch constructs");
    assert!(resumed.prepare_advance(&subsequent).is_ok());
}
