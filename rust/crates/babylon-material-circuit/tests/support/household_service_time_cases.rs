//! Actual utility performance changes provisioning burden through service use.
use super::*;

fn time_service_opening(input: u64) -> MaterialCircuitState {
    let mut state = opening();
    state.inventory[0].quantity = input;
    state.service_connections.push(ServiceConnection {
        provider_site_id: site(2),
        buyer: AccountId::Household(household()),
        good_id: good(2),
        unit_id: unit(2),
    });
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        unreachable!()
    };
    economy.recurring = Some(Box::new(RecurringEconomy {
        service_inputs: vec![],
        households: vec![HouseholdCohort {
            principal_id: household(),
            kind: HouseholdKind::Ordinary,
            households: 1,
            persons: 4,
        }],
        household_stocks: vec![],
        household_needs: vec![HouseholdNeed {
            principal_id: household(),
            good_id: good(2),
            unit_id: unit(2),
            basis: HouseholdNeedBasis::Households,
            units_per_basis: 1,
        }],
        household_purchases: vec![HouseholdPurchasePolicy {
            principal_id: household(),
            retailer_site_id: site(2),
            good_id: good(2),
            unit_id: unit(2),
            target_closing_stock: 0,
            maximum_purchase: 1,
            enabled: true,
        }],
        offers: (1..=3)
            .map(|n| SellerOffer {
                site_id: site(n),
                good_id: good(n),
                unit_id: unit(n),
                unit_price: money(if n == 2 { 3 } else { 2 }),
                pricing: PricePolicy::Fixed,
            })
            .collect(),
        replenishment: vec![],
        production: (1..=3)
            .map(|n| ProductionDemandPolicy {
                process_id: process(n),
                site_id: site(n),
                output_buffer: 0,
                planned_batches: if n == 1 { 2 } else { 1 },
            })
            .collect(),
        attendance: (1..=3)
            .map(|n| AttendancePlan {
                site_id: site(n),
                unit_id: unit(9),
                period: 1,
                planned_hours: if n == 1 { 2 } else { 1 },
            })
            .collect(),
        last_household_admission_period: 0,
        last_household_consumption_period: 0,
    }));
    economy.household_time = HouseholdTimeAccounting::Modeled(
        HouseholdTimeBook::new(vec![HouseholdTimePolicy {
            principal_id: household(),
            labor_unit_id: unit(9),
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
                good_id: good(2),
                unit_id: unit(2),
                hours_per_unmet_unit: 5,
            }],
        }])
        .unwrap(),
    );
    admit_material_purchase(
        &state,
        MaterialPurchase::Service(ServiceOrder {
            order_id: OrderId::from_bytes([1; 32]),
            performance_period: 1,
            provider_site_id: site(1),
            buyer: AccountId::Site(site(2)),
            good_id: good(1),
            unit_id: unit(1),
            quantity: 1,
        }),
        money(2),
    )
    .unwrap()
    .0
}

#[test]
fn household_service_performance_relaxes_only_its_actual_unmet_time_burden() {
    let supplied = advance_material_circuit(&time_service_opening(1)).unwrap();
    let interrupted = advance_material_circuit(&time_service_opening(0)).unwrap();
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
