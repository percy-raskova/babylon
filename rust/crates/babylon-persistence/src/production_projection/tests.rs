use super::*;
use crate::michigan_content::MichiganContentPreset;
use crate::michigan_material::{MichiganDeliveryPreset, MichiganMaterialCatalog};
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_kernel::content_digest::sha256_of;
use babylon_practice_contract::OrderedPracticeActionBatch;
use babylon_tick::material_world::decode_material_receipts;
use babylon_tick::replay_session::ReplayCommitDisposition;

#[test]
fn projection_uses_exact_committed_state_and_refuses_future_history() {
    let preset = MichiganDeliveryPreset::Standard;
    let session = MichiganContentPreset::new_campaign(preset)
        .create_foundation(&crate::test_support::catalog())
        .unwrap()
        .into_session()
        .unwrap();
    let opening = session.material().clone();
    let initial =
        project_material_observation(&crate::test_support::catalog(), preset, &opening, None, &[])
            .unwrap();
    assert!(initial.provenance[0].starts_with("Designed finite 16-period economic circuit"));
    assert!(initial.freight.is_empty());
    assert!(initial.events.is_empty());
    assert!(initial.material_balance.is_none());
    assert_eq!(initial.labor_accounts.len(), 5);
    assert!(initial
        .labor_accounts
        .iter()
        .all(|row| { row.completed.is_none() && row.next_opening_period == 1 }));
    assert!(initial.sites.iter().all(|site| {
        site.processes
            .iter()
            .all(|process| process.produced_batches.is_none())
    }));
    let actions =
        OrderedPracticeActionBatch::empty(session.graph_session().session_identity().clone(), 1)
            .unwrap();
    let prepared = session.prepare_advance(&actions).unwrap();
    let next = prepared.material();
    let receipt = decode_material_receipts(next.receipt_bytes()).unwrap();
    let history = vec![(opening.clone(), receipt, sha256_of(next.receipt_bytes()))];
    let snapshot = project_material_observation(
        &crate::test_support::catalog(),
        preset,
        next.register(),
        Some(&opening),
        &history,
    )
    .unwrap();
    let starved = snapshot
        .sites
        .iter()
        .find(|site| site.industry_code.as_deref() == Some("332"))
        .unwrap();
    assert_eq!(starved.processes[0].planned_batches, Some(0));
    assert_eq!(starved.processes[0].produced_batches, Some(0));
    assert!(!history[0]
        .1
        .production
        .iter()
        .any(|row| digest_hex(&row.site_id.as_bytes()) == starved.id));
    assert!(!snapshot
        .events
        .iter()
        .any(|event| event.kind == "production" && event.subject_site_ids.contains(&starved.id)));
    assert_eq!(
        snapshot
            .freight
            .iter()
            .map(|lot| lot.quantity)
            .collect::<Vec<_>>(),
        next.register()
            .state()
            .freight
            .iter()
            .map(|lot| lot.quantity)
            .collect::<Vec<_>>()
    );
    assert!(snapshot.events.iter().all(|event| event.period == 1));
    assert_eq!(
        project_material_observation(
            &crate::test_support::catalog(),
            preset,
            &opening,
            None,
            &history
        ),
        Err(ProductionProjectionError::History)
    );
    assert_eq!(
        project_material_observation(
            &crate::test_support::catalog(),
            preset,
            next.register(),
            Some(&opening),
            &[]
        ),
        Err(ProductionProjectionError::History)
    );
}

#[test]
fn projection_provenance_uses_the_saved_campaign_horizon() {
    let source = include_str!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../../content/scenarios/michigan/defines.toml"
    ));
    let catalog = MichiganMaterialCatalog::from_defines_toml(&source.replace(
        "DURATION = { kind = \"continuous\" }",
        "DURATION = { kind = \"finite\", final_period = 8 }",
    ))
    .unwrap();
    let foundation = MichiganContentPreset::FourWeekStandard
        .create_foundation(&catalog)
        .unwrap();
    let capture =
        crate::economic_catalog::CapturedEconomicCatalog::from_michigan(&catalog).unwrap();
    let decoded = crate::economic_catalog::CapturedEconomicCatalog::decode(
        capture.canonical_bytes(),
        capture.digest(),
    )
    .unwrap();
    let snapshot = project_economic_current(
        decoded.view(),
        foundation.initial_register(),
        None,
        None,
        &history::OrderHistory::from_opening(foundation.initial_register().state()).unwrap(),
    )
    .unwrap();
    assert_eq!(
        snapshot.duration,
        babylon_kernel::clock::CampaignDuration::Finite { final_period: 8 }
    );
    assert!(snapshot.provenance[0].starts_with("Designed finite 8-period economic circuit"));
}

fn period_three(preset: MichiganDeliveryPreset) -> ProductionSnapshot {
    let mut session = MichiganContentPreset::new_campaign(preset)
        .create_foundation(&crate::test_support::catalog())
        .unwrap()
        .into_session()
        .unwrap();
    let mut history = Vec::new();
    let mut opening = None;
    for tick in 1..=3 {
        let actions = OrderedPracticeActionBatch::empty(
            session.graph_session().session_identity().clone(),
            tick,
        )
        .unwrap();
        let next = session.prepare_advance(&actions).unwrap();
        history.push((
            session.material().clone(),
            decode_material_receipts(next.material().receipt_bytes()).unwrap(),
            sha256_of(next.material().receipt_bytes()),
        ));
        opening = Some(session.material().clone());
        session
            .commit_prepared_and_publish(&mut CollectingSink::default(), next, |_| {
                Ok::<_, ()>(ReplayCommitDisposition::Committed)
            })
            .unwrap();
    }
    project_material_observation(
        &crate::test_support::catalog().with_preset(preset).unwrap(),
        preset,
        session.material(),
        opening.as_ref(),
        &history,
    )
    .unwrap()
}

#[test]
fn physical_projection_preserves_good_identity_and_delivery_delay_causality() {
    let standard = period_three(MichiganDeliveryPreset::Standard);
    let delayed = period_three(MichiganDeliveryPreset::Delayed);
    let macomb = |snapshot: &ProductionSnapshot| {
        snapshot
            .sites
            .iter()
            .find(|site| site.is_in_county("26099"))
            .unwrap()
            .processes[0]
            .produced_batches
    };
    // The first 32 rolling batches consume 320 of the 600 billet units.
    // Standard freight delivers those 320 sheets in period 2: 32 panel
    // batches at 10 sheets each fill the 8-per-week × 4-week capacity.
    // The three-period delayed route has not arrived by period 3.
    assert_eq!(macomb(&standard), Some(32));
    assert_eq!(macomb(&delayed), Some(0));
    for site in standard
        .sites
        .iter()
        .filter(|site| site.industry_code.as_deref() == Some("311"))
    {
        assert_eq!(
            site,
            delayed
                .sites
                .iter()
                .find(|other| other.id == site.id)
                .unwrap()
        );
    }
    for route in &standard.routes {
        let supplier = standard
            .sites
            .iter()
            .find(|site| site.id == route.supplier_site_id)
            .unwrap();
        let buyer = standard
            .sites
            .iter()
            .find(|site| site.id == route.buyer_site_id)
            .unwrap();
        assert!(supplier
            .processes
            .iter()
            .any(|process| process.output_good_id == route.good_id
                && process.output_unit_id == route.unit_id));
        assert!(buyer
            .processes
            .iter()
            .flat_map(|process| &process.inputs)
            .any(|input| input.good_id == route.good_id && input.unit_id == route.unit_id));
        assert!(standard
            .freight
            .iter()
            .filter(|lot| lot.route_id == route.physical_route_id)
            .all(|lot| lot.good_id == route.good_id && lot.unit_id == route.unit_id));
    }
}

#[test]
fn delivery_delay_changes_staffed_time_budgets_and_preserves_unaffected_food() {
    let standard = period_three(MichiganDeliveryPreset::Standard);
    let delayed = period_three(MichiganDeliveryPreset::Delayed);
    for account in &standard.labor_accounts {
        let twin = delayed
            .labor_accounts
            .iter()
            .find(|row| row.site_id == account.site_id && row.unit_id == account.unit_id)
            .unwrap();
        let a = account.completed.as_ref().unwrap();
        let b = twin.completed.as_ref().unwrap();
        assert_eq!(a.period, 3);
        assert_eq!(a.used.checked_add(a.unused), Some(a.opening));
        assert_eq!(b.used.checked_add(b.unused), Some(b.opening));
        let site = standard
            .sites
            .iter()
            .find(|site| site.id == account.site_id)
            .unwrap();
        if site.industry_code.as_deref() == Some("332") {
            // Four workers × 40 hours × four weeks supply 640 hours;
            // the 32 panel batches each consume 20 hours in period 3.
            assert_eq!(a.used, 640);
            assert!(a.used > b.used);
            assert_eq!(b.used, 0);
            assert_eq!((a.opening, b.opening), (640, 0));
            assert_eq!((a.unused, b.unused), (0, 0));
        } else if site.industry_code.as_deref() == Some("311") {
            assert_eq!(account, twin);
        }
    }
}

#[test]
fn native_route_projection_keeps_every_relation_and_shares_exact_stage_definitions() {
    let snapshot = period_three(MichiganDeliveryPreset::Standard);
    let index = crate::production_observation::PhysicalRouteIndex::try_new(&snapshot).unwrap();
    let unique: std::collections::BTreeSet<_> = snapshot
        .routes
        .iter()
        .map(|row| &row.physical_route_id)
        .collect();
    assert_eq!(snapshot.physical_routes.len(), unique.len());
    assert!(!snapshot.routes.is_empty());
    for relation in &snapshot.routes {
        let definition = index.get(relation).unwrap();
        assert_eq!(definition.id, relation.physical_route_id);
        assert_eq!(
            definition.travel_periods,
            definition
                .stages
                .iter()
                .map(|stage| stage.travel_periods)
                .sum::<u64>()
        );
        assert_eq!(
            relation.backlog,
            relation.ordered.checked_sub(relation.shipped).unwrap()
        );
        for other in snapshot
            .routes
            .iter()
            .filter(|row| row.physical_route_id == relation.physical_route_id)
        {
            assert!(std::ptr::eq(definition, index.get(other).unwrap()));
        }
    }
}

#[test]
fn shared_physical_definitions_equal_actual_closed_material_route_rows() {
    let preset = MichiganDeliveryPreset::Standard;
    let session = MichiganContentPreset::new_campaign(preset)
        .create_foundation(&crate::test_support::catalog())
        .unwrap()
        .into_session()
        .unwrap();
    let actions =
        OrderedPracticeActionBatch::empty(session.graph_session().session_identity().clone(), 1)
            .unwrap();
    let opening = session.material().clone();
    let next = session.prepare_advance(&actions).unwrap();
    let receipts = decode_material_receipts(next.material().receipt_bytes()).unwrap();
    let history = vec![(
        opening.clone(),
        receipts,
        sha256_of(next.material().receipt_bytes()),
    )];
    let snapshot = project_material_observation(
        &crate::test_support::catalog(),
        preset,
        next.material().register(),
        Some(&opening),
        &history,
    )
    .unwrap();
    let index = crate::production_observation::PhysicalRouteIndex::try_new(&snapshot).unwrap();
    let actual = next.material().register().state();
    assert_eq!(snapshot.routes.len(), actual.supplier_routes.len());
    for supplier in &actual.supplier_routes {
        let relation = snapshot
            .routes
            .iter()
            .find(|row| {
                row.id
                    == super::routes::relation_id((
                        supplier.buyer_site_id,
                        supplier.supplier_site_id,
                        supplier.good_id,
                        supplier.unit_id,
                    ))
            })
            .unwrap();
        let definition = index.get(relation).unwrap();
        let expected: Vec<_> = actual
            .route_stages
            .iter()
            .filter(|row| row.route_id == supplier.route_id)
            .collect();
        assert_eq!(definition.stages.len(), expected.len());
        for stage in expected {
            let projected = definition
                .stages
                .iter()
                .find(|row| row.stage_index == stage.stage_index)
                .unwrap();
            assert_eq!(projected.travel_periods, u64::from(stage.travel_periods));
            let mut capacities: Vec<_> = actual
                .route_stage_capacities
                .iter()
                .filter(|row| {
                    row.route_id == supplier.route_id && row.stage_index == stage.stage_index
                })
                .map(|row| crate::michigan_economy::digest_hex(&row.corridor_id.as_bytes()))
                .collect();
            capacities.sort_unstable();
            assert_eq!(projected.capacity_ids, capacities);
        }
    }
}
