//! Recurring residents cross the same graph/material commit and restart boundary.

use super::*;
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    AccountId, AttendancePlan, CircuitAccounting, HouseholdCohort, HouseholdNeed,
    HouseholdPurchasePolicy, HouseholdStock, MerchantHandling, MerchantHandlingCoefficient,
    MerchantRole, PricePolicy, ProductionDemandPolicy, RecurringEconomy, SellerOffer,
};

fn opening() -> MaterialCircuitState {
    let mut material = paid_material();
    let household = material.final_demand_principals[0].id;
    let handling = CorridorId::from_bytes([2; 32]);
    material.merchants.push(MerchantHandling {
        site_id: site(1),
        county_geoid: *b"26163",
        role: MerchantRole::Retail,
        capacity_id: handling,
        labor_unit_id: unit(1),
    });
    material
        .handling_coefficients
        .push(MerchantHandlingCoefficient {
            site_id: site(1),
            good_id: good(2),
            unit_id: unit(2),
            hours_per_unit: 1,
        });
    material
        .corridor_capacities
        .extend((1..=8).map(|period| CorridorCapacity {
            corridor_id: handling,
            period,
            available_grams: 10_000,
        }));
    let CircuitAccounting::Monetary(economy) = &mut material.accounting else {
        panic!("paid opening")
    };
    economy.recurring = Some(Box::new(RecurringEconomy {
        households: vec![HouseholdCohort {
            principal_id: household,
            households: 1,
            persons: 1,
        }],
        household_stocks: vec![HouseholdStock {
            principal_id: household,
            good_id: good(2),
            unit_id: unit(2),
            quantity: 0,
        }],
        household_needs: vec![HouseholdNeed {
            principal_id: household,
            good_id: good(2),
            unit_id: unit(2),
            units_per_person: 1,
        }],
        household_purchases: vec![HouseholdPurchasePolicy {
            principal_id: household,
            retailer_site_id: site(1),
            good_id: good(2),
            unit_id: unit(2),
            target_closing_stock: 0,
            maximum_purchase: 1,
            enabled: true,
        }],
        offers: vec![SellerOffer {
            site_id: site(1),
            good_id: good(2),
            unit_id: unit(2),
            unit_price: Currency::from_micro_units(2),
            pricing: PricePolicy::Fixed,
        }],
        replenishment: Vec::new(),
        production: vec![ProductionDemandPolicy {
            process_id: process(),
            site_id: site(1),
            output_buffer: 0,
            planned_batches: 0,
        }],
        attendance: vec![AttendancePlan {
            site_id: site(1),
            unit_id: unit(1),
            period: 1,
            planned_hours: 160,
        }],
        last_household_admission_period: 0,
        last_household_consumption_period: 0,
    }));
    material
}

fn session() -> Session {
    let pool = StaffingPoolBinding::try_new(
        StaffingPoolId::from_bytes([1; 32]),
        site(1),
        unit(1),
        1,
        StaffingPolicy::one_period(160).unwrap(),
        vec![
            StaffingWorkSource::Production(process()),
            StaffingWorkSource::MerchantHandling(site(1)),
        ],
    )
    .unwrap();
    let staffing =
        StaffingComposition::try_new(vec![StaffingNodeBinding::try_new(subject(), pool).unwrap()])
            .unwrap();
    try_session_with_material(MATERIAL_CYCLE, staffing, opening()).unwrap()
}

#[test]
fn household_admission_consumption_and_retirement_replay_atomically() {
    let mut session = session();
    let mut sink = CollectingSink::default();
    let before = live(&session, &sink);
    let candidate = prepare(&session);
    let receipts = decode_material_receipts(candidate.material().receipt_bytes()).unwrap();
    assert_eq!(receipts.household_demand.len(), 1);
    assert_eq!(receipts.household_demand[0].admitted_quantity, 1);
    assert_eq!(receipts.household_demand[0].expired_quantity, 1);
    assert_eq!(receipts.household_consumption[0].unmet_quantity, 1);
    assert!(candidate
        .material()
        .register()
        .state()
        .final_demand_orders
        .is_empty());
    let expected = *candidate.identity();
    let refused = session.commit_prepared_and_publish(&mut sink, candidate, |_| {
        Err::<ReplayCommitDisposition, _>("recurring commit refused")
    });
    assert!(matches!(
        refused,
        Err(MaterialCommitError::Commit("recurring commit refused"))
    ));
    assert_eq!(live(&session, &sink), before);
    let retry = prepare(&session);
    assert_eq!(*retry.identity(), expected);
    let graph = retry.graph_report().result_stable_graph().clone();
    let graph_material = owned_checkpoint_rows(retry.graph_report().material_state_rows());
    let registers = retry
        .graph_report()
        .result_registers()
        .canonical_bytes()
        .to_vec();
    let material = retry.material().register().canonical_bytes().to_vec();
    assert_eq!(retry.material().register().state().freight.len(), 1);
    commit(&mut session, &mut sink, retry);
    let mut restored = self::session();
    restored
        .restore_full_checkpoint(&graph, &graph_material, &registers, &material)
        .unwrap();
    let mut restored_sink = CollectingSink::default();
    let mut consumed = 0;
    for period in 2..=5 {
        let next = prepare(&session);
        let replay = prepare(&restored);
        assert_eq!(replay.identity(), next.identity());
        assert_eq!(
            replay.material().receipt_bytes(),
            next.material().receipt_bytes()
        );
        let receipts = decode_material_receipts(next.material().receipt_bytes()).unwrap();
        assert_eq!(receipts.household_consumption[0].period, period);
        consumed += receipts.household_consumption[0].consumed_quantity;
        assert!(next
            .material()
            .register()
            .state()
            .final_demand_orders
            .is_empty());
        commit(&mut session, &mut sink, next);
        commit(&mut restored, &mut restored_sink, replay);
    }
    assert_eq!(
        consumed, 3,
        "arriving raw inputs support consumption in periods 3–5"
    );
    assert_eq!(session.material(), restored.material());
    let CircuitAccounting::Monetary(economy) = &restored.material().state().accounting else {
        panic!("paid circuit")
    };
    assert_eq!(
        economy.book.cash(AccountId::Site(site(2))).unwrap(),
        Currency::from_micro_units(8)
    );
    assert_eq!(
        economy.book.total_cash_and_reserves().unwrap(),
        Currency::from_micro_units(1000)
    );
    let recurring = economy.recurring.as_ref().unwrap();
    assert_eq!(recurring.last_household_admission_period, 5);
    assert_eq!(recurring.last_household_consumption_period, 5);
    assert_eq!(recurring.household_stocks[0].quantity, 0);
}
