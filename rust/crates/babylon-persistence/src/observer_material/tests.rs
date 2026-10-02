use super::*;
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_practice_contract::OrderedPracticeActionBatch;
use babylon_tick::replay_session::ReplayCommitDisposition;

#[test]
fn continuous_cursor_replays_beyond_sixteen_and_refuses_a_broken_tail() {
    let catalog = crate::michigan_material::MichiganMaterialCatalog::from_defines_toml(
        include_str!("../../../../../content/scenarios/michigan/defines.toml"),
    )
    .unwrap();
    let preset = crate::michigan_content::MichiganContentPreset::FourWeekStandard;
    let expected = preset.admitted(&catalog).unwrap();
    let mut session = preset
        .create_foundation(&catalog)
        .unwrap()
        .into_session()
        .unwrap();
    let campaign = CampaignId::from_uuid(uuid::Uuid::from_u128(338));
    let mut history = MaterialHistory::new(&expected).unwrap();
    let foundation = MaterialObservationRow {
        row_campaign: *campaign.as_uuid(),
        row_tick: 0,
        register_bytes: expected.initial_register().canonical_bytes().to_vec(),
        receipts: None,
        identity: None,
        content_hash: None,
        foundation_bytes: Some(expected.canonical_bytes().to_vec()),
    };
    history
        .append_decoded(campaign, &expected, 0, foundation.clone())
        .unwrap();
    let mut rows = vec![foundation];
    for period in 1..=20 {
        let actions = OrderedPracticeActionBatch::empty(
            session.graph_session().session_identity().clone(),
            period,
        )
        .unwrap();
        let next = session.prepare_advance(&actions).unwrap();
        if period == 17 {
            verify_restart(&catalog, preset, &next);
        }
        let row = MaterialObservationRow {
            row_campaign: *campaign.as_uuid(),
            row_tick: i64::try_from(period).unwrap(),
            register_bytes: next.material().register().canonical_bytes().to_vec(),
            receipts: Some(next.material().receipt_bytes().to_vec()),
            identity: Some(next.identity().canonical_bytes().to_vec()),
            content_hash: Some(next.identity().tick_content_hash().as_bytes().to_vec()),
            foundation_bytes: None,
        };
        let mut missing = row.clone();
        missing.receipts = None;
        assert!(history
            .clone()
            .append_decoded(campaign, &expected, period, missing)
            .is_err());
        assert_eq!(history.register.completed_tick(), period - 1);
        history
            .append_decoded(campaign, &expected, period, row.clone())
            .unwrap();
        rows.push(row);
        assert_eq!(
            history.opening.as_ref().unwrap().completed_tick(),
            period - 1
        );
        assert_eq!(history.receipt.as_ref().unwrap().0.resolve_tick, period);
        assert!(history
            .register
            .state()
            .capacities
            .iter()
            .all(|capacity| capacity.period == period + 1));
        session
            .commit_prepared_and_publish(&mut CollectingSink::default(), next, |_| {
                Ok::<_, ()>(ReplayCommitDisposition::Committed)
            })
            .unwrap();
    }
    let mut cold = MaterialHistory::new(&expected).unwrap();
    for (period, row) in rows.into_iter().enumerate() {
        cold.append_decoded(campaign, &expected, u64::try_from(period).unwrap(), row)
            .unwrap();
    }
    assert_eq!(cold.register, history.register);
    assert_eq!(cold.receipt, history.receipt);
    let project = |value: &MaterialHistory| {
        project_economic_current(
            expected.view(),
            &value.register,
            value.opening.as_ref(),
            value.receipt.as_ref(),
            &value.orders,
        )
        .unwrap()
    };
    assert_eq!(project(&cold), project(&history));
    assert!(project(&history)
        .events
        .iter()
        .all(|event| event.period == 20));
}

fn verify_restart(
    catalog: &crate::michigan_material::MichiganMaterialCatalog,
    preset: crate::michigan_content::MichiganContentPreset,
    next: &babylon_tick::material_replay::PreparedMaterialTick<
        babylon_graph::hypergraph_store::HypergraphStore,
    >,
) {
    let mut resumed = preset
        .create_foundation(catalog)
        .unwrap()
        .into_session()
        .unwrap();
    resumed
        .restore_full_checkpoint(
            next.graph_report().result_stable_graph(),
            next.graph_report().material_state_rows(),
            next.graph_report().result_registers().canonical_bytes(),
            next.material().register().canonical_bytes(),
        )
        .unwrap();
    assert_eq!(resumed.completed_tick(), 17);
    let subsequent =
        OrderedPracticeActionBatch::empty(resumed.graph_session().session_identity().clone(), 18)
            .unwrap();
    assert!(resumed.prepare_advance(&subsequent).is_ok());
}
