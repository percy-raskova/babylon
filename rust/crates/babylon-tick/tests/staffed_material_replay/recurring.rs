//! Recurring residents cross the same graph/material commit and restart boundary.

use crate::process;
use crate::resident_member;
use crate::subject;
use crate::CollectingSink;
use crate::CorridorCapacity;
use crate::CorridorId;
use crate::MaterialCommitError;
use crate::MaterialWorldRegister;
use crate::Materials;
use crate::ReplayCommitDisposition;
use crate::Session;
use crate::StaffingComposition;
use crate::StaffingNodeBinding;
use crate::StaffingPolicy;
use crate::StaffingPoolBinding;
use crate::StaffingPoolId;
use crate::StaffingWorkSource;
use crate::MATERIAL_CYCLE;
use babylon_kernel::currency::Currency;
use babylon_material_circuit::HistoricalCostBook;
use babylon_material_circuit::MonetaryCircuit;
use babylon_material_circuit::{
    AccountId, AttendancePlan, CircuitAccounting, HouseholdCohort, HouseholdNeed,
    HouseholdPurchasePolicy, HouseholdStock, MerchantHandling, MerchantHandlingCoefficient,
    MerchantRole, PricePolicy, ProductionDemandPolicy, RecurringEconomy, SellerOffer,
};

fn capture_empty_pantry_cost(economy: &mut MonetaryCircuit) {
    let pantry = &economy
        .recurring
        .as_ref()
        .expect("the fixture set the optional field before this read")
        .household_stocks[0];
    let mut costs = economy.costs.snapshot();
    costs
        .stocks
        .push(babylon_material_circuit::StockCarryingValue {
            owner: AccountId::Household(pantry.principal_id),
            good_id: pantry.good_id,
            unit_id: pantry.unit_id,
            amount: Currency::from_micro_units(0),
        });
    economy.costs =
        HistoricalCostBook::from_snapshot(costs).expect("the snapshot admits the derived value");
}

fn opening() -> Materials {
    let Materials {
        mut catalog,
        mut state,
    } = crate::paid_material();
    let material = &mut state;
    let household = material.final_demand_principals[0].id;
    let handling = CorridorId::from_bytes([2; 32]);
    catalog.merchants.push(MerchantHandling {
        site_id: crate::site(1),
        location: "county:26163"
            .parse()
            .expect("the authored literal parses as the declared type"),
        role: MerchantRole::Retail,
        capacity_id: handling,
        labor_unit_id: crate::unit(1),
    });
    catalog
        .handling_coefficients
        .push(MerchantHandlingCoefficient {
            site_id: crate::site(1),
            good_id: crate::good(2),
            unit_id: crate::unit(2),
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
        service_inputs: vec![],
        households: vec![HouseholdCohort {
            kind: babylon_material_circuit::HouseholdKind::Ordinary,
            principal_id: household,
            households: 1,
            persons: 1,
        }],
        household_stocks: vec![HouseholdStock {
            principal_id: household,
            good_id: crate::good(2),
            unit_id: crate::unit(2),
            quantity: 0,
        }],
        household_needs: vec![HouseholdNeed {
            principal_id: household,
            good_id: crate::good(2),
            unit_id: crate::unit(2),
            basis: babylon_material_circuit::HouseholdNeedBasis::Persons,
            units_per_basis: 1,
        }],
        household_purchases: vec![HouseholdPurchasePolicy {
            principal_id: household,
            retailer_site_id: crate::site(1),
            good_id: crate::good(2),
            unit_id: crate::unit(2),
            target_closing_stock: 0,
            maximum_purchase: 1,
            enabled: true,
        }],
        offers: vec![SellerOffer {
            site_id: crate::site(1),
            good_id: crate::good(2),
            unit_id: crate::unit(2),
            unit_price: Currency::from_micro_units(2),
            pricing: PricePolicy::Fixed,
        }],
        replenishment: Vec::new(),
        production: vec![ProductionDemandPolicy {
            process_id: process(),
            site_id: crate::site(1),
            output_buffer: 0,
            planned_batches: 0,
        }],
        attendance: vec![AttendancePlan {
            site_id: crate::site(1),
            unit_id: crate::unit(1),
            period: 1,
            planned_hours: 160,
        }],
        last_household_admission_period: 0,
        last_household_consumption_period: 0,
    }));
    capture_empty_pantry_cost(economy);
    catalog.household_needs.clone_from(
        &economy
            .recurring
            .as_ref()
            .expect("the fixture set the optional field before this read")
            .household_needs,
    );
    Materials { catalog, state }
}

fn session() -> Session {
    session_with_material(opening())
}

fn session_with_material(material: Materials) -> Session {
    let pool = StaffingPoolBinding::try_new(
        StaffingPoolId::from_bytes([1; 32]),
        crate::site(1),
        crate::unit(1),
        1,
        StaffingPolicy::one_period(160).expect("the one-period fixture advances"),
        vec![
            StaffingWorkSource::Production(process()),
            StaffingWorkSource::MerchantHandling(crate::site(1)),
        ],
    )
    .expect("the authored fixture satisfies the constructor invariants");
    let staffing = StaffingComposition::try_new(vec![StaffingNodeBinding::try_new(
        subject(),
        pool.clone(),
        vec![resident_member(&pool)],
    )
    .expect("the authored fixture satisfies the constructor invariants")])
    .expect("the authored fixture satisfies the constructor invariants");
    crate::try_session_with_material(MATERIAL_CYCLE, staffing, material)
        .expect("the fixture opens a session with material")
}

fn household_time_session() -> Session {
    use babylon_material_circuit::{
        HouseholdNeedBasis, HouseholdTimeAccounting, HouseholdTimeBook, HouseholdTimeCommitment,
        HouseholdTimePolicy, HouseholdUnmetTimeBurden,
    };
    let Materials {
        mut catalog,
        mut state,
    } = opening();
    let material = &mut state;
    let CircuitAccounting::Monetary(economy) = &mut material.accounting else {
        panic!("paid household opening");
    };
    let household = economy
        .recurring
        .as_ref()
        .expect("the fixture set the optional field before this read")
        .households[0]
        .principal_id;
    economy.household_time = HouseholdTimeAccounting::Modeled(
        HouseholdTimeBook::new(vec![HouseholdTimePolicy {
            principal_id: household,
            labor_unit_id: crate::unit(1),
            eligible_persons: 1,
            hours_per_eligible_person: 224,
            protected: HouseholdTimeCommitment {
                basis: HouseholdNeedBasis::Households,
                hours_per_basis: 32,
            },
            routine_provisioning: HouseholdTimeCommitment {
                basis: HouseholdNeedBasis::Households,
                hours_per_basis: 16,
            },
            unmet_burdens: vec![HouseholdUnmetTimeBurden {
                good_id: crate::good(2),
                unit_id: crate::unit(2),
                hours_per_unmet_unit: 4,
            }],
        }])
        .expect("the constructor accepts the authored fixture arguments"),
    );
    if let HouseholdTimeAccounting::Modeled(time) = &economy.household_time {
        catalog.household_time_policy.clone_from(&time.policies);
    }
    session_with_material(Materials { catalog, state })
}

#[test]
fn household_time_receipts_publish_atomically_and_replay_after_restart() {
    use babylon_material_circuit::HouseholdTimeAccounting;
    let mut session = household_time_session();
    let mut sink = CollectingSink::default();
    let before = crate::live(&session, &sink);
    let candidate = crate::prepare(&session);
    let receipts = crate::decode_material_receipts(candidate.material().receipt_bytes())
        .expect("the canonical bytes decode into the declared type");
    let time = &receipts.household_time[0];
    assert_eq!(receipts.household_time.len(), 1);
    assert_eq!((time.period, time.attended_hours), (1, 160));
    assert_eq!(receipts.household_consumption[0].unmet_quantity, 1);
    assert_eq!(time.unpaid_requested_hours, 20);
    assert_eq!(time.contribution_available_hours, 12);
    let identity = *candidate.identity();
    let refused = session.commit_prepared_and_publish(&mut sink, candidate, |_, _| {
        Err::<ReplayCommitDisposition, _>("household time commit refused")
    });
    assert!(matches!(
        refused,
        Err(MaterialCommitError::Commit("household time commit refused"))
    ));
    assert_eq!(crate::live(&session, &sink), before);
    let retry = crate::prepare(&session);
    assert_eq!(*retry.identity(), identity);
    let graph = retry.graph_report().result_stable_graph().clone();
    let graph_material = crate::owned_checkpoint_rows(retry.graph_report().material_state_rows());
    let registers = retry
        .graph_report()
        .result_registers()
        .canonical_bytes()
        .to_vec();
    let material = retry.material().register().canonical_bytes().to_vec();
    let CircuitAccounting::Monetary(economy) = &retry.material().register().state().accounting
    else {
        panic!("paid household candidate");
    };
    let HouseholdTimeAccounting::Modeled(book) = &economy.household_time else {
        panic!("captured household time policy");
    };
    assert_eq!(book.receipts, receipts.household_time);
    crate::commit(&mut session, &mut sink, retry);
    let mut restored = household_time_session();
    restored
        .restore_full_checkpoint(
            &graph,
            &graph_material,
            &registers,
            MaterialWorldRegister::decode_external(session.catalog(), material.clone())
                .expect("the committed canonical bytes decode"),
        )
        .expect("the committed checkpoint restores");
    assert_eq!(restored.material(), session.material());
    let mut restored_sink = CollectingSink::default();
    for period in 2..=5 {
        let next = crate::prepare(&session);
        let replay = crate::prepare(&restored);
        assert_eq!(replay.identity(), next.identity());
        assert_eq!(
            replay.material().receipt_bytes(),
            next.material().receipt_bytes()
        );
        let current = crate::decode_material_receipts(next.material().receipt_bytes())
            .expect("the canonical bytes decode into the declared type");
        assert_eq!(current.household_time[0].period, period);
        assert_eq!(
            current.household_time[0].attended_hours,
            current
                .member_labor_use
                .iter()
                .map(|row| row.attended_hours)
                .sum::<u64>()
        );
        assert_eq!(
            current.household_time[0].unpaid_requested_hours,
            16 + 4 * current.household_consumption[0].unmet_quantity
        );
        crate::commit(&mut session, &mut sink, next);
        crate::commit(&mut restored, &mut restored_sink, replay);
    }
    assert_eq!(restored.material(), session.material());
}

#[test]
fn household_admission_consumption_and_retirement_replay_atomically() {
    let mut session = session();
    let mut sink = CollectingSink::default();
    let before = crate::live(&session, &sink);
    let candidate = crate::prepare(&session);
    let receipts = crate::decode_material_receipts(candidate.material().receipt_bytes())
        .expect("the canonical bytes decode into the declared type");
    assert_eq!(receipts.household_demand.len(), 1);
    assert_eq!(receipts.household_demand[0].admitted_quantity, 1);
    assert_eq!(receipts.household_demand[0].expired_quantity, 1);
    assert_eq!(receipts.household_consumption[0].unmet_quantity, 1);
    assert_eq!(
        candidate
            .material()
            .register()
            .state()
            .final_demand_orders
            .len(),
        0
    );
    let expected = *candidate.identity();
    let refused = session.commit_prepared_and_publish(&mut sink, candidate, |_, _| {
        Err::<ReplayCommitDisposition, _>("recurring commit refused")
    });
    assert!(matches!(
        refused,
        Err(MaterialCommitError::Commit("recurring commit refused"))
    ));
    assert_eq!(crate::live(&session, &sink), before);
    let retry = crate::prepare(&session);
    assert_eq!(*retry.identity(), expected);
    let graph = retry.graph_report().result_stable_graph().clone();
    let graph_material = crate::owned_checkpoint_rows(retry.graph_report().material_state_rows());
    let registers = retry
        .graph_report()
        .result_registers()
        .canonical_bytes()
        .to_vec();
    let material = retry.material().register().canonical_bytes().to_vec();
    assert_eq!(retry.material().register().state().freight.len(), 1);
    crate::commit(&mut session, &mut sink, retry);
    let mut restored = self::session();
    restored
        .restore_full_checkpoint(
            &graph,
            &graph_material,
            &registers,
            MaterialWorldRegister::decode_external(session.catalog(), material.clone())
                .expect("the committed canonical bytes decode"),
        )
        .expect("the committed checkpoint restores");
    let mut restored_sink = CollectingSink::default();
    let mut consumed = 0;
    for period in 2..=5 {
        let next = crate::prepare(&session);
        let replay = crate::prepare(&restored);
        assert_eq!(replay.identity(), next.identity());
        assert_eq!(
            replay.material().receipt_bytes(),
            next.material().receipt_bytes()
        );
        let receipts = crate::decode_material_receipts(next.material().receipt_bytes())
            .expect("the canonical bytes decode into the declared type");
        assert_eq!(receipts.household_consumption[0].period, period);
        consumed += receipts.household_consumption[0].consumed_quantity;
        assert_eq!(
            next.material().register().state().final_demand_orders.len(),
            0
        );
        crate::commit(&mut session, &mut sink, next);
        crate::commit(&mut restored, &mut restored_sink, replay);
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
        economy
            .book
            .cash(AccountId::Site(crate::site(2)))
            .expect("the fixture book holds the payer account"),
        Currency::from_micro_units(8)
    );
    assert_eq!(
        economy
            .book
            .total_cash_and_reserves()
            .expect("the fixture book totals without overflow"),
        Currency::from_micro_units(1000)
    );
    let recurring = economy
        .recurring
        .as_ref()
        .expect("the fixture set the optional field before this read");
    assert_eq!(recurring.last_household_admission_period, 5);
    assert_eq!(recurring.last_household_consumption_period, 5);
    assert_eq!(recurring.household_stocks[0].quantity, 0);
}
