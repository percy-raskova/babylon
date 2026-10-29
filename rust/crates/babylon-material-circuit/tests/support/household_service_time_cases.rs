//! Actual utility performance changes provisioning burden through service use.

use babylon_material_circuit::AccountId;
use babylon_material_circuit::AttendancePlan;
use babylon_material_circuit::CircuitAccounting;
use babylon_material_circuit::HouseholdCohort;
use babylon_material_circuit::HouseholdKind;
use babylon_material_circuit::HouseholdNeed;
use babylon_material_circuit::HouseholdNeedBasis;
use babylon_material_circuit::HouseholdPurchasePolicy;
use babylon_material_circuit::HouseholdTimeAccounting;
use babylon_material_circuit::HouseholdTimeBook;
use babylon_material_circuit::HouseholdTimeCommitment;
use babylon_material_circuit::HouseholdTimePolicy;
use babylon_material_circuit::HouseholdUnmetTimeBurden;
use babylon_material_circuit::MaterialCatalog;
use babylon_material_circuit::MaterialCircuitState;
use babylon_material_circuit::MaterialPurchase;
use babylon_material_circuit::OrderId;
use babylon_material_circuit::PricePolicy;
use babylon_material_circuit::ProductionDemandPolicy;
use babylon_material_circuit::RecurringEconomy;
use babylon_material_circuit::SellerOffer;
use babylon_material_circuit::ServiceConnection;
use babylon_material_circuit::ServiceOrder;

#[allow(
    clippy::too_many_lines,
    reason = "a conformance scenario builds its whole fixture and asserts the full trajectory in one test"
)]
fn time_service_opening(input: u64) -> (MaterialCatalog, MaterialCircuitState) {
    let (catalog, mut state) = crate::opening();
    state.inventory[0].quantity = input;
    state.service_connections.push(ServiceConnection {
        provider_site_id: crate::site(2),
        buyer: AccountId::Household(crate::household()),
        good_id: crate::good(2),
        unit_id: crate::unit(2),
    });
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        unreachable!()
    };
    let household_needs = vec![HouseholdNeed {
        principal_id: crate::household(),
        good_id: crate::good(2),
        unit_id: crate::unit(2),
        basis: HouseholdNeedBasis::Households,
        units_per_basis: 1,
    }];
    let recurring = RecurringEconomy {
        households: vec![HouseholdCohort {
            principal_id: crate::household(),
            kind: HouseholdKind::Ordinary,
            households: 1,
            persons: 4,
        }],
        household_stocks: vec![],
        household_purchases: vec![HouseholdPurchasePolicy {
            principal_id: crate::household(),
            retailer_site_id: crate::site(2),
            good_id: crate::good(2),
            unit_id: crate::unit(2),
            target_closing_stock: 0,
            maximum_purchase: 1,
            enabled: true,
        }],
        offers: (1..=3)
            .map(|n| SellerOffer {
                site_id: crate::site(n),
                good_id: crate::good(n),
                unit_id: crate::unit(n),
                unit_price: crate::money(if n == 2 { 3 } else { 2 }),
                pricing: PricePolicy::Fixed,
            })
            .collect(),
        replenishment: vec![],
        production: (1..=3)
            .map(|n| ProductionDemandPolicy {
                process_id: crate::process(n),
                site_id: crate::site(n),
                output_buffer: 0,
                planned_batches: if n == 1 { 2 } else { 1 },
            })
            .collect(),
        attendance: (1..=3)
            .map(|n| AttendancePlan {
                site_id: crate::site(n),
                unit_id: crate::unit(9),
                period: 1,
                planned_hours: if n == 1 { 2 } else { 1 },
            })
            .collect(),
        last_household_admission_period: 0,
        last_household_consumption_period: 0,
    };
    let needs = household_needs.clone();
    economy.recurring = Some(Box::new(recurring));
    let time_policy = HouseholdTimePolicy {
        principal_id: crate::household(),
        labor_unit_id: crate::unit(9),
        eligible_persons: 4,
        hours_per_eligible_person: 8,
        protected: HouseholdTimeCommitment {
            basis: HouseholdNeedBasis::Households,
            hours_per_basis: 2,
        },
        routine_provisioning: HouseholdTimeCommitment {
            basis: HouseholdNeedBasis::Households,
            hours_per_basis: 3,
        },
        unmet_burdens: vec![HouseholdUnmetTimeBurden {
            good_id: crate::good(2),
            unit_id: crate::unit(2),
            hours_per_unmet_unit: 5,
        }],
    };
    economy.household_time = HouseholdTimeAccounting::Modeled(HouseholdTimeBook::default());
    let mut catalog = catalog.into_definition();
    catalog.household_time_policy = vec![time_policy];
    catalog.household_needs = needs;
    catalog.service_inputs.clear();

    let catalog = MaterialCatalog::try_new(catalog).expect("the fixture catalog stays valid");
    let state = babylon_material_circuit::admit_material_purchase(
        &catalog,
        &state,
        MaterialPurchase::Service(ServiceOrder {
            order_id: OrderId::from_bytes([1; 32]),
            performance_period: 1,
            provider_site_id: crate::site(1),
            buyer: AccountId::Site(crate::site(2)),
            good_id: crate::good(1),
            unit_id: crate::unit(1),
            quantity: 1,
        }),
        crate::money(2),
    )
    .expect("the fixture admits the authored purchase")
    .0;
    (catalog, state)
}

#[test]
fn household_service_performance_relaxes_only_its_actual_unmet_time_burden() {
    let (catalog, opening) = time_service_opening(1);
    let supplied = babylon_material_circuit::advance_material_circuit(&catalog, &opening)
        .expect("the authored material state advances one period");
    let (catalog, opening) = time_service_opening(0);
    let interrupted = babylon_material_circuit::advance_material_circuit(&catalog, &opening)
        .expect("the authored material state advances one period");
    assert_eq!(supplied.household_services[0].satisfied_quantity, 1);
    assert_eq!(interrupted.household_services[0].unmet_quantity, 1);
    assert_eq!(supplied.household_time[0].attended_hours, 4);
    assert_eq!(interrupted.household_time[0].attended_hours, 4);
    assert_eq!(supplied.household_time[0].unpaid_requested_hours, 3);
    assert_eq!(interrupted.household_time[0].unpaid_requested_hours, 8);
    assert_eq!(supplied.household_time[0].contribution_available_hours, 23);
    assert_eq!(
        interrupted.household_time[0].contribution_available_hours,
        18
    );
}
