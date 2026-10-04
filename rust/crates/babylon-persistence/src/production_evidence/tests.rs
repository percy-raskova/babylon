use std::sync::OnceLock;

use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::{hypergraph_store::HypergraphStore, stable_state::StableGraphState};
use babylon_practice_contract::OrderedPracticeActionBatch;
use babylon_tick::{
    material_replay::PreparedMaterialTick, material_staffing::StaffingComposition,
    material_world::decode_material_receipts, replay_session::ReplayCommitDisposition,
};
use serde_json::Value;

use super::*;
use crate::{
    identity::CampaignId,
    material_envelope::CommittedMaterialTickEnvelope,
    michigan_content::MichiganContentPreset,
    michigan_economy::digest_hex,
    michigan_material::MichiganDeliveryPreset,
    production_observation::ProductionSnapshot,
    production_projection::{project_material_observation, staffing::project_staffing_accounts},
    runtime::prepare_committed_tick,
};

/// Exercises the existing engine, canonical envelope, publication and projector.
/// The commit callback is an in-memory sink; this is not live-Postgres evidence.
fn published_observations() -> &'static [ObserverEconomySnapshot] {
    static OBSERVATIONS: OnceLock<Vec<ObserverEconomySnapshot>> = OnceLock::new();
    OBSERVATIONS.get_or_init(|| {
        let preset = MichiganDeliveryPreset::Standard;
        let foundation = MichiganContentPreset::new_campaign(preset)
            .create_foundation(&crate::test_support::catalog())
            .unwrap();
        let foundation_digest = foundation.digest();
        let composition = foundation.labor().clone();
        let mut session = foundation.into_session().unwrap();
        let campaign = CampaignId::from_uuid(uuid::Uuid::from_u128(293));
        let mut observation = ObserverEconomySnapshot {
            campaign_id: campaign.as_uuid().to_string(),
            resolve_tick: 0,
            foundation_digest: digest_hex(&foundation_digest),
            nominal_world_hash: None,
            tick_content_hash: None,
            envelope_digest: None,
            visibility: ObserverVisibility::FullObserver,
            counties: vec![],
            production: Some(
                project_material_observation(
                    &crate::test_support::catalog(),
                    preset,
                    session.material(),
                    None,
                    &[],
                )
                .unwrap(),
            ),
        };
        observation.production.as_mut().unwrap().staffing_accounts = project_staffing_accounts(
            &composition,
            &session.graph_session().stable_graph_state().unwrap(),
            session.material(),
            None,
            &[],
            None,
        )
        .unwrap();
        let mut result = vec![observation.clone()];
        let mut history = Vec::new();
        let mut sink = CollectingSink::default();
        for tick in 1..=3 {
            let actions = OrderedPracticeActionBatch::empty(
                session.graph_session().session_identity().clone(),
                tick,
            )
            .unwrap();
            let opening = session.material().clone();
            let opening_graph = session.graph_session().stable_graph_state().unwrap();
            let prepared = session.prepare_advance(&actions).unwrap();
            let staffing = prepared_staffing(&composition, &opening_graph, &prepared);
            let identity = *prepared.identity();
            let receipt = decode_material_receipts(prepared.material().receipt_bytes()).unwrap();
            let families = prepare_committed_tick(prepared.graph_report())
                .unwrap()
                .into_material_families(identity.tick_content_hash())
                .unwrap();
            let envelope = CommittedMaterialTickEnvelope::compose(
                campaign,
                &identity,
                families,
                prepared.material().register().canonical_bytes(),
                prepared.material().receipt_bytes(),
            )
            .unwrap();
            let (ack, _) = session
                .commit_prepared_and_publish(&mut sink, prepared, |_| {
                    Ok::<_, ()>(ReplayCommitDisposition::Committed)
                })
                .unwrap();
            history.push((opening.clone(), receipt, ack.receipt_digest()));
            observation.resolve_tick = ack.resolve_tick();
            observation.tick_content_hash = Some(digest_hex(ack.tick_content_hash().as_bytes()));
            observation.envelope_digest = Some(digest_hex(&envelope.digest()));
            observation.nominal_world_hash = Some(digest_hex(&ack.result_world_hash()));
            observation.production = Some(
                project_material_observation(
                    &crate::test_support::catalog(),
                    preset,
                    session.material(),
                    Some(&opening),
                    &history,
                )
                .unwrap(),
            );
            observation.production.as_mut().unwrap().staffing_accounts = staffing;
            result.push(observation.clone());
        }
        result
    })
}

fn prepared_staffing(
    composition: &StaffingComposition,
    opening: &StableGraphState,
    prepared: &PreparedMaterialTick<HypergraphStore>,
) -> Vec<crate::production_observation::ProductionStaffingAccount> {
    let report = prepared.graph_report();
    let events = report
        .successful_event_batch()
        .events()
        .iter()
        .map(|event| crate::stored_tick::StoredEvent {
            emitting_rule: event.emitting_rule().to_owned(),
            choice_receipt_ordinal: event
                .choice_receipt()
                .map(babylon_tick::choice_receipt::ChoiceReceiptRef::encounter_ordinal),
            event_type: event.event_type().to_owned(),
            fields: event.fields().to_vec(),
        })
        .collect::<Vec<_>>();
    project_staffing_accounts(
        composition,
        report.result_stable_graph(),
        prepared.material().register(),
        Some(opening),
        &events,
        Some(
            &babylon_tick::material_world::decode_material_receipts(
                prepared.material().receipt_bytes(),
            )
            .unwrap(),
        ),
    )
    .unwrap()
}

fn committed() -> ObserverEconomySnapshot {
    published_observations()[1].clone()
}

fn digest(snapshot: &mut ObserverEconomySnapshot) -> ProductionEvidenceDigest {
    snapshot.production_evidence_digest().unwrap().unwrap()
}

/// Add the disclosure families absent from the small regional engine fixture.
/// All state/receipt projections are tested at their authenticated seams; this
/// fixture tests that the public evidence encoder binds every disclosed field.
fn full_disclosure() -> ObserverEconomySnapshot {
    use crate::production_observation::{
        CompletedProductionFinalDemand, CompletedProductionMerchantHandling,
        ProductionFinalDemandAccount, ProductionFinalDemandOrder, ProductionHandlingCoefficient,
        ProductionMerchantHandlingAccount, ProductionMerchantHandlingOrder, ProductionOutboundKind,
    };
    let mut observation = committed();
    let production = observation.production.as_mut().unwrap();
    let site = production.sites[0].id.clone();
    let stock = production.sites[0].inventory[0].clone();
    road_disclosure(production);
    production
        .merchant_handling_accounts
        .push(ProductionMerchantHandlingAccount {
            site_id: site.clone(),
            capacity_id: "handling-capacity".to_owned(),
            labor_unit_id: "labor".to_owned(),
            coefficients: vec![ProductionHandlingCoefficient {
                good_id: stock.good_id.clone(),
                unit_id: stock.unit_id.clone(),
                grams_per_unit: 10,
                hours_per_unit: 2,
            }],
            completed: Some(CompletedProductionMerchantHandling {
                period: 1,
                needed_hours: 12,
                used_hours: 6,
                handled_grams: 30,
                orders: vec![ProductionMerchantHandlingOrder {
                    order_id: "final-order".to_owned(),
                    kind: ProductionOutboundKind::LocalFinalDemand,
                    good_id: stock.good_id.clone(),
                    unit_id: stock.unit_id.clone(),
                    requested: 10,
                    feasible_quantity: 6,
                    handled_quantity: 3,
                    needed_hours: 12,
                    used_hours: 6,
                    remaining_unshipped: 7,
                }],
            }),
        });
    production
        .final_demand_accounts
        .push(ProductionFinalDemandAccount {
            total_order_count: 1,
            expired: 0,
            demand_principal_id: "county-demand".to_owned(),
            location: "county:26163".parse().unwrap(),
            good_id: stock.good_id.clone(),
            unit_id: stock.unit_id.clone(),
            good: stock.good,
            unit: stock.unit,
            ordered: 10,
            fulfilled: 3,
            outstanding: 7,
            retail_stock_on_hand: 7,
            retailer_site_ids: vec![site.clone()],
            orders: vec![ProductionFinalDemandOrder {
                expired: 0,
                order_id: "final-order".to_owned(),
                retailer_site_id: site,
                ordered: 10,
                fulfilled: 3,
                outstanding: 7,
            }],
            completed: Some(CompletedProductionFinalDemand {
                period: 1,
                opening_fulfilled: 0,
                newly_fulfilled: 3,
                closing_fulfilled: 3,
            }),
        });
    household_disclosure(production);
    support_disclosure(production);
    price_disclosure(production);
    production.staffing_accounts[0].members[0].compensation = Some(
        crate::production_observation::ProductionLaborCompensation::Wage {
            hourly_micro_units: 3,
        },
    );
    observation
}

fn road_disclosure(production: &mut ProductionSnapshot) {
    use crate::production_observation::{ProductionPhysicalEdge, ProductionRoadSource};
    production.physical_edges = vec![
        ProductionPhysicalEdge {
            id: "edge-a".to_owned(),
            shape_e7: vec![[-830_000_000, 420_000_000], [-830_001_000, 420_001_000]],
            distance_mm: 17_000,
        },
        ProductionPhysicalEdge {
            id: "edge-b".to_owned(),
            shape_e7: vec![[-830_001_000, 420_001_000], [-830_003_000, 420_003_000]],
            distance_mm: 33_000,
        },
    ];
    production.physical_routes[0].physical_edge_ids = vec![
        "edge-a".to_owned(),
        "edge-b".to_owned(),
        "edge-a".to_owned(),
    ];
    production.physical_routes[0].distance_mm = Some(67_000);
    production.road_source = Some(ProductionRoadSource {
        pbf_sha256: "pbf-sha".to_owned(),
        pbf_bytes: 100,
        pbf_url: "https://example.org/roads.pbf".to_owned(),
        replication_timestamp: "2026-09-09T00:00:00Z".to_owned(),
        footprint_sha256: "footprint-sha".to_owned(),
        buffer_degrees_e7: 200_000,
        extraction_version: "extract-v1".to_owned(),
        distance_version: "integer-v1".to_owned(),
        routing_profile_version: "michigan-freight-routing-v1".to_owned(),
        graph_sha256: "graph-sha".to_owned(),
    });
}

fn household_disclosure(production: &mut ProductionSnapshot) {
    let final_account = &production.final_demand_accounts[0];
    production
        .household_accounts
        .push(crate::ProductionHouseholdAccount {
            kind: crate::ProductionHouseholdKind::Ordinary,
            demand_principal_id: final_account.demand_principal_id.clone(),
            location: final_account.location,
            good_id: final_account.good_id.clone(),
            unit_id: final_account.unit_id.clone(),
            good: final_account.good.clone(),
            unit: final_account.unit.clone(),
            household_count: 2,
            person_count: 4,
            retailer_site_id: final_account.retailer_site_ids[0].clone(),
            stock_on_hand: 7,
            required_per_period: 4,
            completed: Some(crate::CompletedHouseholdBalance {
                period: 1,
                opening_stock: 8,
                received: 3,
                support_granted: 0,
                support_dispatched: 0,
                required: 4,
                consumed: 4,
                unmet: 0,
                closing_stock: 7,
                desired: 4,
                requested: 4,
                admitted: 4,
                fulfilled: 3,
                expired: 1,
            }),
        });
}

/// The encoder must bind gift identities and exact mass as disclosed fields.
fn support_disclosure(production: &mut ProductionSnapshot) {
    use crate::production_observation::ProductionAidCapacityOrder;
    let household = &production.household_accounts[0];
    let route = production.routes[0].physical_route_id.clone();
    let reservation = &mut production.freight_capacity_accounts[0]
        .completed
        .as_mut()
        .unwrap()
        .reservations[0];
    reservation.opening_available_grams += 42_000;
    reservation.newly_reserved_grams += 42_000;
    reservation.support_orders = (1..=2)
        .map(|quantity| ProductionAidCapacityOrder {
            commitment_id: format!("support-{quantity}"),
            mandate_id: format!("support-mandate-{quantity}"),
            donor_principal_id: household.demand_principal_id.clone(),
            recipient_principal_id: "independent-recipient".into(),
            route_id: route.clone(),
            good_id: household.good_id.clone(),
            unit_id: household.unit_id.clone(),
            dispatched: quantity,
            grams_per_unit: 14_000,
            reserved_grams: quantity * 14_000,
        })
        .collect();
}

#[test]
fn diagnostic_field_census_reconciles_the_complete_serialized_scope() {
    let observation = full_disclosure();
    let scope = EvidenceScope {
        campaign_id: &observation.campaign_id,
        resolve_tick: observation.resolve_tick,
        foundation_digest: &observation.foundation_digest,
        tick_content_hash: observation.tick_content_hash.as_deref(),
        envelope_digest: observation.envelope_digest.as_deref(),
        nominal_world_hash: observation.nominal_world_hash.as_deref(),
        visibility: "full_observer",
        production: observation.production.as_ref().unwrap(),
    };
    let encoded = serde_json::to_vec(&scope).unwrap();
    assert_eq!(diagnostic_value_bytes(&scope).unwrap(), encoded.len());
    assert!(diagnostic_field_sizes(&scope, encoded.len()).is_ok());
    assert!(diagnostic_field_sizes(&scope, encoded.len() + 1).is_err());
}

#[test]
fn collective_resident_goods_preserve_person_needs_without_inventing_households() {
    let mut observation = full_disclosure();
    let household = &mut observation.production.as_mut().unwrap().household_accounts[0];
    household.kind = crate::ProductionHouseholdKind::CollectiveResidence;
    household.household_count = 0;
    assert!(observation.production_evidence_digest().is_ok());
}

#[test]
fn residence_kinds_bind_goods_and_services_and_refuse_lost_or_invalid_counts() {
    use crate::{
        CompletedHouseholdService, ProductionHouseholdKind as Kind,
        ProductionHouseholdServiceAccount,
    };
    let mut observation = full_disclosure();
    let production = observation.production.as_mut().unwrap();
    let household = &mut production.household_accounts[0];
    household.kind = Kind::CollectiveResidence;
    household.household_count = 0;
    production
        .household_service_accounts
        .push(ProductionHouseholdServiceAccount {
            kind: Kind::CollectiveResidence,
            demand_principal_id: household.demand_principal_id.clone(),
            location: household.location,
            good_id: "care".into(),
            unit_id: "service-hour".into(),
            good: "care".into(),
            unit: "service-hour".into(),
            household_count: 0,
            person_count: 4,
            provider_site_ids: vec!["care-provider".into()],
            required_per_period: 4,
            completed: Some(CompletedHouseholdService {
                period: 1,
                required: 4,
                requested: 4,
                admitted: 3,
                performed: 3,
                satisfied: 3,
                unmet: 1,
                unused: 0,
                expired: 0,
            }),
        });
    let collective = digest(&mut observation);
    let encoded = serde_json::to_value(&observation).unwrap();
    for family in ["household_accounts", "household_service_accounts"] {
        for (kind, persons, households) in [
            ("ordinary", 4, 0),
            ("ordinary", 1, 2),
            ("collective_residence", 0, 0),
            ("collective_residence", 4, 1),
        ] {
            let mut invalid = encoded.clone();
            let row = &mut invalid["production"][family][0];
            row["kind"] = serde_json::json!(kind);
            row["person_count"] = serde_json::json!(persons);
            row["household_count"] = serde_json::json!(households);
            let mut invalid: ObserverEconomySnapshot = serde_json::from_value(invalid).unwrap();
            assert_eq!(
                invalid.production_evidence_digest(),
                Err(ProductionEvidenceError::InvalidIdentity)
            );
        }
        let mut missing = encoded.clone();
        missing["production"][family][0]
            .as_object_mut()
            .unwrap()
            .remove("kind");
        assert!(serde_json::from_value::<ObserverEconomySnapshot>(missing).is_err());
        let mut unknown = encoded.clone();
        unknown["production"][family][0]["kind"] = serde_json::json!("invented");
        assert!(serde_json::from_value::<ObserverEconomySnapshot>(unknown).is_err());
    }
    let production = observation.production.as_mut().unwrap();
    production.household_accounts[0].kind = Kind::Ordinary;
    production.household_accounts[0].household_count = 2;
    production.household_service_accounts[0].kind = Kind::Ordinary;
    production.household_service_accounts[0].household_count = 2;
    assert_ne!(digest(&mut observation), collective);
}

#[test]
fn household_support_flows_conserve_stock_and_change_disclosed_evidence() {
    let mut before = full_disclosure();
    let mut supported = before.clone();
    let household = &mut supported.production.as_mut().unwrap().household_accounts[0];
    let done = household.completed.as_mut().unwrap();
    done.support_granted = 5;
    done.support_dispatched = 3;
    done.closing_stock = 9;
    household.stock_on_hand = 9;
    assert_ne!(digest(&mut before), digest(&mut supported));
    let mut unaccounted = supported;
    unaccounted.production.as_mut().unwrap().household_accounts[0]
        .completed
        .as_mut()
        .unwrap()
        .support_dispatched = 2;
    assert_eq!(
        unaccounted.production_evidence_digest(),
        Err(ProductionEvidenceError::InvalidIdentity)
    );
}

#[test]
fn presentation_multisets_permute_without_changing_evidence_identity() {
    let mut before = full_disclosure();
    let mut permuted = before.clone();
    let rows = permuted.production.as_mut().unwrap();
    rows.sites.reverse();
    for site in &mut rows.sites {
        site.inventory.reverse();
        site.processes.reverse();
        for process in &mut site.processes {
            process.inputs.reverse();
            process.labor.reverse();
            for input in &mut process.inputs {
                input.supplier_site_ids.reverse();
            }
        }
    }
    rows.routes.reverse();
    rows.physical_routes.reverse();
    for route in &mut rows.physical_routes {
        route.stages.reverse();
        for stage in &mut route.stages {
            stage.capacity_ids.reverse();
        }
    }
    rows.freight.reverse();
    rows.physical_edges.reverse();
    rows.labor_accounts.reverse();
    rows.staffing_accounts.reverse();
    for pool in &mut rows.staffing_accounts {
        pool.members.reverse();
    }
    rows.freight_capacity_accounts.reverse();
    for account in &mut rows.freight_capacity_accounts {
        account.route_ids.reverse();
        account.merchant_site_ids.reverse();
        if let Some(completed) = &mut account.completed {
            completed.reservations.reverse();
            for reservation in &mut completed.reservations {
                reservation.orders.reverse();
                reservation.support_orders.reverse();
            }
        }
    }
    rows.material_balance.as_mut().unwrap().rows.reverse();
    rows.provenance.reverse();
    rows.freight_order_definitions.reverse();
    assert_eq!(digest(&mut before), digest(&mut permuted));
}

#[test]
fn physical_path_repetition_vertex_order_and_event_sequence_remain_semantic() {
    let mut before = full_disclosure();
    for mutation in [
        |rows: &mut ProductionSnapshot| {
            rows.physical_routes[0].physical_edge_ids.swap(0, 1);
        },
        |rows: &mut ProductionSnapshot| {
            rows.physical_routes[0].physical_edge_ids.pop();
        },
        |rows: &mut ProductionSnapshot| {
            rows.physical_edges[0].shape_e7.reverse();
        },
        |rows: &mut ProductionSnapshot| {
            rows.events.reverse();
        },
    ] {
        let mut changed = before.clone();
        mutation(changed.production.as_mut().unwrap());
        assert_ne!(digest(&mut before), digest(&mut changed));
    }
}

fn scalar_changes(value: &Value, pointer: &str, changes: &mut Vec<(String, Value)>) {
    match value {
        Value::Object(values) => {
            for (key, value) in values {
                scalar_changes(
                    value,
                    &format!("{pointer}/{}", key.replace('~', "~0").replace('/', "~1")),
                    changes,
                );
            }
        }
        Value::Array(values) => {
            for (index, value) in values.iter().enumerate() {
                scalar_changes(value, &format!("{pointer}/{index}"), changes);
            }
        }
        Value::String(value) => {
            let replacement = match value.as_str() {
                "Local" => "Staged".to_owned(),
                "Staged" => "Local".to_owned(),
                "Delivery" => "LocalFinalDemand".to_owned(),
                "LocalFinalDemand" => "Delivery".to_owned(),
                "Transport" => "MerchantHandling".to_owned(),
                "MerchantHandling" => "Transport".to_owned(),
                "Production" => "Retail".to_owned(),
                "Observed" => "Designed".to_owned(),
                "Designed" => "Observed".to_owned(),
                _ => format!("{value} changed"),
            };
            changes.push((pointer.to_owned(), Value::String(replacement)));
        }
        Value::Number(number) => {
            let replacement = number.as_i64().map_or_else(
                || Value::from(number.as_u64().unwrap() - 1),
                |n| Value::from(n.checked_add(1).unwrap()),
            );
            changes.push((pointer.to_owned(), replacement));
        }
        Value::Bool(value) => changes.push((pointer.to_owned(), Value::Bool(!value))),
        Value::Null => {}
    }
}

#[test]
fn every_disclosed_scalar_is_bound_or_refused_including_new_accounting_families() {
    let mut before = full_disclosure();
    let expected = digest(&mut before);
    let json = serde_json::to_value(&before).unwrap();
    let mut mutations = Vec::new();
    scalar_changes(&json["production"], "/production", &mut mutations);
    let mut checked = 0;
    for (pointer, replacement) in mutations {
        let mut changed = json.clone();
        *changed.pointer_mut(&pointer).unwrap() = replacement;
        // An unknown enum is rejected at the disclosure boundary before hashing.
        let Ok(mut changed) = serde_json::from_value::<ObserverEconomySnapshot>(changed) else {
            continue;
        };
        assert_ne!(
            changed.production_evidence_digest(),
            Ok(Some(expected)),
            "unbound scalar {pointer}"
        );
        checked += 1;
    }
    assert!(
        checked > 300,
        "the actual committed accounts and new DTO families were exercised"
    );
}

#[test]
fn scope_completed_zero_and_absent_preview_are_distinct() {
    let mut before = committed();
    for mutate in [
        |row: &mut ObserverEconomySnapshot| {
            row.campaign_id.push('x');
        },
        |row: &mut ObserverEconomySnapshot| {
            row.resolve_tick += 1;
        },
        |row: &mut ObserverEconomySnapshot| {
            row.foundation_digest.push('x');
        },
        |row: &mut ObserverEconomySnapshot| {
            row.tick_content_hash = None;
        },
        |row: &mut ObserverEconomySnapshot| {
            row.envelope_digest = None;
        },
        |row: &mut ObserverEconomySnapshot| {
            row.nominal_world_hash = None;
        },
        |row: &mut ObserverEconomySnapshot| {
            row.production.as_mut().unwrap().labor_accounts[0].completed = None;
        },
    ] {
        let mut changed = before.clone();
        mutate(&mut changed);
        assert_ne!(digest(&mut before), digest(&mut changed));
    }
    let mut opening = published_observations()[0].clone();
    assert_ne!(digest(&mut opening), digest(&mut before));
    let mut preview = before;
    preview.visibility = ObserverVisibility::KnownPreview;
    assert_eq!(
        preview.production_evidence_digest(),
        Err(ProductionEvidenceError::InvalidIdentity)
    );
    preview.production = None;
    assert_eq!(preview.production_evidence_digest(), Ok(None));
}

#[test]
fn duplicate_principals_and_row_bounds_refuse_instead_of_acquiring_a_digest() {
    let before = full_disclosure();
    for mutate in [
        |rows: &mut ProductionSnapshot| {
            rows.sites.push(rows.sites[0].clone());
        },
        |rows: &mut ProductionSnapshot| {
            let member = rows.staffing_accounts[0].members[0].clone();
            rows.staffing_accounts[0].members.push(member);
        },
        |rows: &mut ProductionSnapshot| {
            rows.physical_edges.push(rows.physical_edges[0].clone());
        },
        |rows: &mut ProductionSnapshot| {
            rows.freight_capacity_accounts
                .push(rows.freight_capacity_accounts[0].clone());
        },
        |rows: &mut ProductionSnapshot| {
            let support = &mut rows.freight_capacity_accounts[0]
                .completed
                .as_mut()
                .unwrap()
                .reservations[0]
                .support_orders;
            support.push(support[0].clone());
        },
        |rows: &mut ProductionSnapshot| {
            rows.merchant_handling_accounts
                .push(rows.merchant_handling_accounts[0].clone());
        },
        |rows: &mut ProductionSnapshot| {
            rows.final_demand_accounts
                .push(rows.final_demand_accounts[0].clone());
        },
    ] {
        let mut changed = before.clone();
        mutate(changed.production.as_mut().unwrap());
        assert_eq!(
            changed.production_evidence_digest(),
            Err(ProductionEvidenceError::InvalidIdentity)
        );
    }
    let mut bounded = before;
    bounded.production.as_mut().unwrap().routes =
        vec![
            bounded.production.as_ref().unwrap().routes[0].clone();
            babylon_material_circuit::MAX_SUPPLIER_ROUTES + 1
        ];
    assert_eq!(
        bounded.production_evidence_digest(),
        Err(ProductionEvidenceError::Bound)
    );
}

#[test]
fn native_requests_larger_than_u64_grams_are_hashed_without_narrowing() {
    let mut observation = committed();
    let expected = digest(&mut observation);
    let production = observation.production.as_mut().unwrap();
    let definition = &mut production.freight_order_definitions[0];
    let prior = definition.id.clone();
    definition.order.requested = u64::MAX;
    definition.order.grams_per_unit = u64::MAX;
    definition.order.dispatched = 0;
    definition.order.remaining_unshipped = u64::MAX;
    definition.order.reserved_grams = 0;
    definition.order.requested_grams = u128::from(u64::MAX) * u128::from(u64::MAX);
    definition.id =
        crate::production_observation::freight_order_identity(&definition.order).unwrap();
    for account in &mut production.freight_capacity_accounts {
        if let Some(completed) = &mut account.completed {
            for reservation in &mut completed.reservations {
                for reference in &mut reservation.orders {
                    if *reference == prior {
                        *reference = definition.id.clone();
                    }
                }
            }
        }
    }
    assert_ne!(digest(&mut observation), expected);
}

#[test]
fn buffered_evidence_preserves_every_byte_across_chunks_and_exact_u128() {
    let value = ("\"\nλ".repeat(24_000), u128::MAX, Some("tail"));
    let body = serde_json::to_vec(&value).unwrap();
    let mut framed = DOMAIN.to_vec();
    framed.extend_from_slice(&VERSION.to_be_bytes());
    framed.extend_from_slice(&body);
    let mut output = EvidenceWriter {
        hash: Sha256::new(),
        remaining: body.len(),
        bound: false,
    };
    output.hash.update(DOMAIN);
    output.hash.update(VERSION.to_be_bytes());
    encode_evidence(&mut output, &value).unwrap();
    assert_eq!(output.remaining, 0);
    assert!(!output.bound);
    let actual: [u8; 32] = output.hash.finalize().into();
    assert_eq!(actual, babylon_kernel::content_digest::sha256_of(&framed));
}

#[test]
fn buffered_evidence_refuses_a_byte_limit_crossed_only_by_the_final_flush() {
    let mut output = EvidenceWriter {
        hash: Sha256::new(),
        remaining: 2,
        bound: false,
    };
    assert!(encode_evidence(&mut output, &"x").is_err());
    assert!(output.bound);
    assert_eq!(output.remaining, 2);
}

#[test]
fn production_evidence_stream_enforces_national_ceiling_without_partial_writes() {
    assert_eq!(MAX_EVIDENCE_BYTES, 1_000_000_000);
    let mut rejected = EvidenceWriter {
        hash: Sha256::new(),
        remaining: 2,
        bound: false,
    };
    assert!(rejected.write_all(b"abc").is_err());
    assert!(rejected.bound);
    assert_eq!(rejected.remaining, 2);
    assert_eq!(rejected.hash.finalize(), Sha256::digest(b""));
    // Exercise the final two bytes of the budget without allocating a gigabyte.
    let mut writer = EvidenceWriter {
        hash: Sha256::new(),
        remaining: 2,
        bound: false,
    };
    writer.write_all(b"ab").unwrap();
    writer.write_all(b"").unwrap();
    assert_eq!(writer.remaining, 0);
    assert!(!writer.bound);
    let accepted = writer.hash.clone().finalize();
    assert_eq!(accepted, Sha256::digest(b"ab"));
    let error = writer.write_all(b"c").unwrap_err();
    assert_eq!(error.kind(), io::ErrorKind::InvalidData);
    assert_eq!(writer.remaining, 0);
    assert!(writer.bound);
    assert_eq!(writer.hash.finalize(), accepted);
}

fn maintenance_value(mut value: Value, period: u64, jobs: Option<u64>) -> Value {
    let process = value["sites"][0]["processes"][0].clone();
    let consumer = value["sites"][0]["id"].clone();
    let provider = "9".repeat(64);
    value["sites"]
        .as_array_mut()
        .unwrap()
        .push(serde_json::json!({
            "id": provider, "location": "county:26163", "name": "Wayne maintenance",
            "industry_code": "811310", "observed_employment": null, "roles": ["Maintenance"], "function": "household_services",
            "sector_code": "81", "processes": [], "inventory": []
        }));
    value["labor_accounts"]
        .as_array_mut()
        .unwrap()
        .push(serde_json::json!({
            "site_id": provider, "unit_id": "8".repeat(64), "unit": "labor-hours",
            "next_opening_period": period + 1, "next_opening_available": 40,
            "completed": jobs.map(|n| serde_json::json!({
                "period": period, "opening": n * 10, "planned": 0, "used": n * 10,
                "unused": 0, "handling_needed": 0, "handling_used": 0,
                "maintenance_needed": 40, "maintenance_used": n * 10,
                "installation_needed": 0, "installation_used": 0
            }))
        }));
    value["maintenance_account"] = serde_json::json!({
        "provider_site_id": provider, "consumer_site_id": consumer,
        "consumer_process_id": process["id"], "spare_good_id": process["output_good_id"],
        "spare_unit_id": process["output_unit_id"], "spare_good": process["output_good"],
        "spare_unit": process["output_unit"], "labor_unit_id": "8".repeat(64), "labor_unit": "labor-hours",
        "output_good_id": process["output_good_id"], "output_unit_id": process["output_unit_id"],
        "output_good": process["output_good"], "output_unit": process["output_unit"],
        "output_per_batch": process["output_per_batch"], "spare_units_per_job": 2,
        "labor_units_per_job": 10, "enabled_batches_per_job": 2, "maximum_jobs_per_period": 4,
        "next_service_period": period + 1, "next_service_batches": jobs.map_or(4, |n| n * 2),
        "completed": jobs.map(|n| serde_json::json!({
            "period": period, "opening_service_batches": 6, "consumed_service_batches": 4,
            "expired_service_batches": 2, "prospective_batches": 8, "requested_jobs": 4,
            "opening_spare_parts": 8, "arrived_spare_parts": 0, "available_spare_parts": 8,
            "available_labor_hours": n * 10, "completed_jobs": n, "consumed_spare_parts": n * 2,
            "consumed_labor_hours": n * 10
        }))
    });
    value
}

#[test]
fn maintenance_evidence_covers_every_account_field_and_refuses_fog_or_wrong_endpoint() {
    let mut observation = committed();
    observation.production = Some(
        serde_json::from_value(maintenance_value(
            serde_json::to_value(observation.production.as_ref().unwrap()).unwrap(),
            1,
            Some(2),
        ))
        .unwrap(),
    );
    let original = observation.production_evidence_digest().unwrap();
    let encoded = serde_json::to_value(&observation).unwrap();
    for path in [
        "provider_site_id",
        "consumer_site_id",
        "consumer_process_id",
        "spare_good_id",
        "spare_unit_id",
        "labor_unit_id",
        "output_good_id",
        "output_unit_id",
        "output_per_batch",
        "spare_units_per_job",
        "labor_units_per_job",
        "enabled_batches_per_job",
        "maximum_jobs_per_period",
        "next_service_period",
        "next_service_batches",
    ] {
        let mut changed = encoded.clone();
        let field = &mut changed["production"]["maintenance_account"][path];
        *field = if let Some(n) = field.as_u64() {
            serde_json::json!(n + 1)
        } else {
            serde_json::json!("mismatched")
        };
        let mut changed: ObserverEconomySnapshot = serde_json::from_value(changed).unwrap();
        assert_ne!(
            changed.production_evidence_digest(),
            Ok(original),
            "uncovered {path}"
        );
    }
    for field in encoded["production"]["maintenance_account"]["completed"]
        .as_object()
        .unwrap()
        .keys()
    {
        let mut changed = encoded.clone();
        let number = changed["production"]["maintenance_account"]["completed"][field]
            .as_u64()
            .unwrap();
        changed["production"]["maintenance_account"]["completed"][field] =
            serde_json::json!(number + 1);
        let mut changed: ObserverEconomySnapshot = serde_json::from_value(changed).unwrap();
        assert_ne!(
            changed.production_evidence_digest(),
            Ok(original),
            "uncovered {field}"
        );
    }
    for field in [
        "provider_site_id",
        "consumer_site_id",
        "consumer_process_id",
        "spare_unit_id",
        "labor_unit_id",
    ] {
        let mut invalid = encoded.clone();
        invalid["production"]["maintenance_account"][field] = serde_json::json!("unbound-identity");
        let mut invalid: ObserverEconomySnapshot = serde_json::from_value(invalid).unwrap();
        assert_eq!(
            invalid.production_evidence_digest(),
            Err(ProductionEvidenceError::InvalidIdentity),
            "{field}"
        );
    }
    observation.visibility = ObserverVisibility::KnownPreview;
    assert_eq!(
        observation.production_evidence_digest(),
        Err(ProductionEvidenceError::InvalidIdentity)
    );
    observation.production = None;
    assert_eq!(observation.production_evidence_digest(), Ok(None));
}

fn price_disclosure(production: &mut ProductionSnapshot) {
    let site = &production.sites[0];
    let stock = &site.inventory[0];
    production
        .goods_price_accounts
        .push(crate::ProductionGoodsPriceAccount {
            site_id: site.id.clone(),
            good_id: stock.good_id.clone(),
            unit_id: stock.unit_id.clone(),
            good: stock.good.clone(),
            unit: stock.unit.clone(),
            current_price_micro: 4,
            completed: Some(crate::CompletedGoodsPrice {
                period: 1,
                old_price_micro: 3,
                next_price_micro: 4,
                unserved_quantity: 0,
                closing_stock: 0,
                reason: crate::GoodsPriceReason::CostPressure,
                cost_basis: crate::GoodsPriceBasis::Released,
                basis_quantity: 2,
                carrying_cost_micro: 7,
                handling_wages_micro: 1,
                unit_cost_micro: Some(4),
            }),
        });
}

#[test]
fn supplier_route_disclosure_exceeds_generic_rows_without_truncation() {
    let mut observation = committed();
    let rows = observation.production.as_mut().unwrap();
    let template = rows.routes[0].clone();
    rows.routes = (0..=MAX_ROWS)
        .map(|index| {
            let mut route = template.clone();
            route.id = format!("supplier-route-{index:06}");
            route
        })
        .collect();
    let expected = digest(&mut observation);
    observation.production.as_mut().unwrap().routes.reverse();
    assert_eq!(digest(&mut observation), expected);
    assert_eq!(
        observation.production.as_ref().unwrap().routes.len(),
        MAX_ROWS + 1
    );
    let tail = observation
        .production
        .as_mut()
        .unwrap()
        .routes
        .last_mut()
        .unwrap();
    assert_eq!(tail.id, "supplier-route-065536");
    tail.backlog = tail.backlog.checked_add(1).unwrap();
    assert_ne!(digest(&mut observation), expected);
    let duplicate = observation.production.as_ref().unwrap().routes[0].clone();
    observation
        .production
        .as_mut()
        .unwrap()
        .routes
        .push(duplicate);
    assert_eq!(
        observation.production_evidence_digest(),
        Err(ProductionEvidenceError::InvalidIdentity)
    );
}

#[test]
fn supplier_route_disclosure_refuses_above_admitted_source_capacity() {
    let mut observation = committed();
    let rows = observation.production.as_mut().unwrap();
    let template = rows.routes[0].clone();
    rows.routes = (0..=babylon_material_circuit::MAX_SUPPLIER_ROUTES)
        .map(|index| {
            let mut route = template.clone();
            route.id = format!("supplier-route-{index:06}");
            route
        })
        .collect();
    assert_eq!(
        observation.production_evidence_digest(),
        Err(ProductionEvidenceError::Bound)
    );
}

#[test]
fn evidence_validation_refusal_preserves_disclosure_and_sorting_is_idempotent() {
    let mut snapshot = full_disclosure();
    snapshot.production.as_mut().unwrap().sites.reverse();
    let duplicate = snapshot.production.as_ref().unwrap().sites[0].clone();
    snapshot.production.as_mut().unwrap().sites.push(duplicate);
    let unchanged = snapshot.clone();
    assert_eq!(
        snapshot.production_evidence_digest(),
        Err(ProductionEvidenceError::InvalidIdentity)
    );
    assert_eq!(snapshot, unchanged);
    snapshot.production.as_mut().unwrap().sites.pop();
    let first = snapshot.production_evidence_digest().unwrap();
    let canonical = snapshot.clone();
    assert_eq!(snapshot.production_evidence_digest().unwrap(), first);
    assert_eq!(snapshot, canonical);
}

#[test]
fn physical_definitions_share_paths_without_merging_supplier_quantities() {
    let mut observation = committed();
    let original = observation.production.as_ref().unwrap().routes[0].clone();
    let mut second = original.clone();
    second.id = "separate-supplier-relation".into();
    second.ordered = second.ordered.checked_add(1).unwrap();
    second.backlog = second.backlog.checked_add(1).unwrap();
    let rows = observation.production.as_mut().unwrap();
    let definitions = rows.physical_routes.len();
    rows.routes.push(second.clone());
    let index = crate::production_observation::PhysicalRouteIndex::try_new(rows).unwrap();
    assert!(std::ptr::eq(
        index.get(&original).unwrap(),
        index.get(&second).unwrap()
    ));
    assert_eq!(rows.physical_routes.len(), definitions);
    let expected = digest(&mut observation);
    let rows = observation.production.as_mut().unwrap();
    let tail = rows
        .routes
        .iter_mut()
        .find(|row| row.id == second.id)
        .unwrap();
    assert_eq!(tail.ordered, second.ordered);
    tail.backlog += 1;
    assert_ne!(digest(&mut observation), expected);
}

#[test]
fn physical_definition_corruption_and_missing_references_refuse_full_evidence() {
    let before = committed();
    for mutation in [
        |rows: &mut ProductionSnapshot| {
            rows.physical_routes.push(rows.physical_routes[0].clone());
        },
        |rows: &mut ProductionSnapshot| {
            rows.physical_routes[0].travel_periods += 1;
        },
        |rows: &mut ProductionSnapshot| {
            rows.routes[0].physical_route_id = "absent".into();
        },
        |rows: &mut ProductionSnapshot| {
            let mut unused = rows.physical_routes[0].clone();
            unused.id = "unused-corrupt-definition".into();
            unused.travel_periods += 1;
            rows.physical_routes.push(unused);
        },
    ] {
        let mut changed = before.clone();
        mutation(changed.production.as_mut().unwrap());
        assert_eq!(
            changed.production_evidence_digest(),
            Err(ProductionEvidenceError::InvalidIdentity)
        );
    }
}

#[test]
fn evidence_v17_census_covers_every_normalized_production_field() {
    assert_eq!(VERSION, 17);
    assert_eq!(DOMAIN, b"babylon.production-observation-evidence.v17\0");
    let mut observation = committed();
    canonicalize_production(observation.production.as_mut().unwrap());
    let scope = EvidenceScope {
        campaign_id: &observation.campaign_id,
        resolve_tick: observation.resolve_tick,
        foundation_digest: &observation.foundation_digest,
        tick_content_hash: observation.tick_content_hash.as_deref(),
        envelope_digest: observation.envelope_digest.as_deref(),
        nominal_world_hash: observation.nominal_world_hash.as_deref(),
        visibility: "full_observer",
        production: observation.production.as_ref().unwrap(),
    };
    assert_eq!(
        diagnostic_production_fields(scope.production)
            .unwrap()
            .len(),
        25
    );
    diagnostic_field_sizes(&scope, diagnostic_value_bytes(&scope).unwrap()).unwrap();
}

#[test]
fn shared_freight_definitions_refuse_forged_missing_unused_and_duplicate_facts() {
    use crate::production_observation::{FreightOrderError, FreightOrderIndex};
    let observation = committed();
    let original = observation.production.unwrap();
    assert!(!original.freight_order_definitions.is_empty());
    assert!(FreightOrderIndex::try_new(&original).is_ok());
    let mut changed = original.clone();
    changed.freight_order_definitions[0].order.requested_grams = u128::MAX;
    assert!(matches!(
        FreightOrderIndex::try_new(&changed),
        Err(FreightOrderError::Identity)
    ));
    let mut changed = original.clone();
    changed
        .freight_order_definitions
        .push(changed.freight_order_definitions[0].clone());
    assert!(matches!(
        FreightOrderIndex::try_new(&changed),
        Err(FreightOrderError::Duplicate)
    ));
    let mut changed = original.clone();
    changed.freight_order_definitions.remove(0);
    assert!(matches!(
        FreightOrderIndex::try_new(&changed),
        Err(FreightOrderError::Missing)
    ));
    let mut changed = original.clone();
    let mut unused = changed.freight_order_definitions[0].clone();
    unused.order.order_id.push_str("-unused");
    unused.id = crate::production_observation::freight_order_identity(&unused.order).unwrap();
    changed.freight_order_definitions.push(unused);
    assert!(matches!(
        FreightOrderIndex::try_new(&changed),
        Err(FreightOrderError::Unused)
    ));
    let mut changed = original;
    let reservation = &mut changed
        .freight_capacity_accounts
        .iter_mut()
        .find(|a| {
            a.completed
                .as_ref()
                .is_some_and(|c| c.reservations.iter().any(|r| !r.orders.is_empty()))
        })
        .unwrap()
        .completed
        .as_mut()
        .unwrap()
        .reservations[0];
    reservation.orders.push(reservation.orders[0].clone());
    assert!(matches!(
        FreightOrderIndex::try_new(&changed),
        Err(FreightOrderError::Duplicate)
    ));
}

#[test]
fn shared_freight_tuple_identity_covers_all_exact_fields() {
    let original = committed().production.unwrap().freight_order_definitions[0]
        .order
        .clone();
    let identity = crate::production_observation::freight_order_identity(&original).unwrap();
    for field in 0..13 {
        let mut changed = original.clone();
        match field {
            0 => changed.supplier_relation_id = Some("different".into()),
            1 => changed.order_id.push_str("different"),
            2 => changed.route_id = Some("different".into()),
            3 => {
                changed.kind = match changed.kind {
                    crate::production_observation::ProductionOutboundKind::Delivery => {
                        crate::production_observation::ProductionOutboundKind::LocalFinalDemand
                    }
                    crate::production_observation::ProductionOutboundKind::LocalFinalDemand => {
                        crate::production_observation::ProductionOutboundKind::Delivery
                    }
                }
            }
            4 => changed.supplier_site_id.push_str("different"),
            5 => changed.good_id.push_str("different"),
            6 => changed.unit_id.push_str("different"),
            7 => changed.requested ^= 1,
            8 => changed.dispatched ^= 1,
            9 => changed.remaining_unshipped ^= 1,
            10 => changed.grams_per_unit ^= 1,
            11 => changed.requested_grams = u128::MAX,
            _ => changed.reserved_grams ^= 1,
        }
        assert_ne!(
            crate::production_observation::freight_order_identity(&changed).unwrap(),
            identity
        );
    }
}

#[test]
fn freight_factoring_preserves_every_occurrence_without_expanded_owned_vectors() {
    use crate::production_observation::{FreightOrderIndex, FreightOrderRegistry};
    let mut observation = committed();
    let production = observation.production.as_mut().unwrap();
    let index = FreightOrderIndex::try_new(production).unwrap();
    let expected: Vec<_> = production
        .freight_capacity_accounts
        .iter()
        .flat_map(|a| &a.completed)
        .flat_map(|c| &c.reservations)
        .flat_map(|r| &r.orders)
        .map(|reference| index.get(reference).unwrap().clone())
        .collect();
    let mut registry = FreightOrderRegistry::default();
    let references: Vec<_> = expected
        .iter()
        .cloned()
        .map(|order| registry.intern(order).unwrap())
        .collect();
    let definitions = registry.finish();
    let expanded: Vec<_> = references
        .iter()
        .map(|reference| {
            definitions
                .iter()
                .find(|d| &d.id == reference)
                .unwrap()
                .order
                .clone()
        })
        .collect();
    assert_eq!(expanded, expected);
    let unique: std::collections::BTreeSet<_> = expected.iter().collect();
    assert_eq!(definitions.len(), unique.len());
    let before = digest(&mut observation);
    let production = observation.production.as_mut().unwrap();
    let completed = production
        .freight_capacity_accounts
        .iter_mut()
        .find_map(|a| a.completed.as_mut().filter(|c| !c.reservations.is_empty()))
        .unwrap();
    let mut occurrence = completed.reservations[0].clone();
    occurrence.reservation_period += 100;
    completed.reservations.push(occurrence);
    assert_ne!(
        digest(&mut observation),
        before,
        "reservation occurrences remain evidence, even with identical order definitions"
    );
}

#[test]
fn rekeyed_freight_tuple_with_invalid_arithmetic_refuses_admission() {
    use crate::production_observation::FreightOrderIndex;
    let original = committed();
    for fault in 0..6 {
        let mut changed = original.clone();
        let production = changed.production.as_mut().unwrap();
        let definition = &mut production.freight_order_definitions[0];
        let prior = definition.id.clone();
        match fault {
            0 => definition.order.requested_grams ^= 1,
            1 => definition.order.remaining_unshipped ^= 1,
            2 => definition.order.reserved_grams ^= 1,
            3 => definition.order.dispatched = u64::MAX,
            4 => {
                definition.order.requested = u64::MAX;
                definition.order.dispatched = u64::MAX;
                definition.order.remaining_unshipped = 0;
                definition.order.grams_per_unit = 2;
                definition.order.requested_grams = u128::from(u64::MAX) * 2;
                definition.order.reserved_grams = u64::MAX;
            }
            _ => {
                definition.order.grams_per_unit = 0;
                definition.order.requested_grams = 0;
                definition.order.reserved_grams = 0;
            }
        }
        definition.id =
            crate::production_observation::freight_order_identity(&definition.order).unwrap();
        for account in &mut production.freight_capacity_accounts {
            if let Some(completed) = &mut account.completed {
                for reservation in &mut completed.reservations {
                    for reference in &mut reservation.orders {
                        if *reference == prior {
                            *reference = definition.id.clone();
                        }
                    }
                }
            }
        }
        assert!(
            FreightOrderIndex::try_new(production).is_err(),
            "rekeyed invalid arithmetic fault {fault}"
        );
        assert_eq!(
            changed.production_evidence_digest(),
            Err(ProductionEvidenceError::InvalidIdentity)
        );
    }
}

#[test]
fn raw_freight_identity_retains_full_u128_even_when_arithmetic_admission_refuses() {
    let production = committed().production.unwrap();
    let mut tuple = production.freight_order_definitions[0].order.clone();
    let original = crate::production_observation::freight_order_identity(&tuple).unwrap();
    tuple.requested_grams = u128::MAX;
    let encoded = serde_json::to_vec(&tuple).unwrap();
    let restored: crate::production_observation::ProductionFreightCapacityOrder =
        serde_json::from_slice(&encoded).unwrap();
    assert_eq!(restored.requested_grams, u128::MAX);
    assert_eq!(restored, tuple);
    assert_ne!(
        crate::production_observation::freight_order_identity(&tuple).unwrap(),
        original
    );
}
