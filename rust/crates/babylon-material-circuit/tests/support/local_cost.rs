//! Two outbound passes must not blend incoming local basis into old stock sold now.
use super::*;

fn local_cost_economy() -> MonetaryCircuit {
    let book = MonetaryBook::open(
        [
            (AccountId::Site(site(1)), 0),
            (AccountId::Site(site(2)), 10),
            (AccountId::Site(site(3)), 10),
            (AccountId::Household(household()), 0),
        ]
        .into_iter()
        .map(|(id, value)| CashAccount {
            id,
            cash: money(value),
        })
        .collect(),
    )
    .unwrap();
    let costs = HistoricalCostBook::open(
        &book,
        [1, 2]
            .into_iter()
            .map(|id| StockCarryingValue {
                owner: AccountId::Site(site(id)),
                good_id: good(2),
                unit_id: units(),
                amount: money(1),
            })
            .collect(),
        vec![],
        vec![],
        vec![],
    )
    .unwrap();
    MonetaryCircuit {
        aid: AidBook::default(),

        household_time: babylon_material_circuit::HouseholdTimeAccounting::NotModeled,
        financial: babylon_material_circuit::FinancialInstitutions::empty(),
        member_labor: (1..=2)
            .map(|period| babylon_material_circuit::MemberLaborCapacityRow {
                member_id: babylon_material_circuit::StaffingMemberId::from_bytes(
                    site(2).as_bytes(),
                ),
                period,
                available_hours: 1,
            })
            .collect(),
        book,
        costs,
        employment: vec![EmploymentTerms {
            member_id: babylon_material_circuit::StaffingMemberId::from_bytes((site(2)).as_bytes()),
            site_id: site(2),
            unit_id: hours(),
            payee: household(),
            compensation: babylon_material_circuit::LaborCompensation::Wage(money(1)),
        }],
        recurring: Some(Box::new(RecurringEconomy {
            service_inputs: vec![],
            households: vec![],
            household_stocks: vec![],
            household_needs: vec![],
            household_purchases: vec![],
            offers: vec![SellerOffer {
                site_id: site(2),
                good_id: good(2),
                unit_id: units(),
                unit_price: money(2),
                pricing: PricePolicy::Fixed,
            }],
            replenishment: vec![ReplenishmentPolicy {
                buyer_site_id: site(3),
                supplier_site_id: site(2),
                good_id: good(2),
                unit_id: units(),
                target_stock: 1,
                maximum_purchase: 1,
                cash_floor: money(0),
            }],
            production: vec![],
            attendance: vec![AttendancePlan {
                site_id: site(2),
                unit_id: hours(),
                period: 1,
                planned_hours: 1,
            }],
            last_household_admission_period: 0,
            last_household_consumption_period: 0,
        })),
    }
}

fn local_cost_opening() -> MaterialCircuitState {
    let mut state = opening();
    state.accounting = CircuitAccounting::Monetary(Box::new(local_cost_economy()));
    state.inventory = vec![inventory(1, 2, 1), inventory(2, 2, 1)];
    state.process_outputs.clear();
    state.input_coefficients.clear();
    state.labor_coefficients.clear();
    state.capacities.clear();
    state.production_commitments.clear();
    state.route_stages.clear();
    state.route_stage_capacities.clear();
    state.supplier_routes = [(1, 2), (2, 3)]
        .into_iter()
        .map(|(supplier, buyer)| SupplierRoute {
            supplier_site_id: site(supplier),
            buyer_site_id: site(buyer),
            good_id: good(2),
            unit_id: units(),
            route_id: route(supplier),
            transport_kind: SupplierTransport::Local,
        })
        .collect();
    state.merchants[0].site_id = site(2);
    state.handling_coefficients[0].site_id = site(2);
    state.corridor_capacities = (1..=2)
        .map(|period| CorridorCapacity {
            corridor_id: corridor(3),
            period,
            available_grams: 2,
        })
        .collect();
    state.labor = (1..=2)
        .map(|period| LaborCapacityRow {
            site_id: site(2),
            unit_id: hours(),
            period,
            available: 1,
        })
        .collect();
    let order = OrderRow {
        order_id: OrderId::from_bytes([50; 32]),
        access_mode: OrderAccessMode::CommoditySale,
        supplier_site_id: site(1),
        buyer_site_id: site(2),
        good_id: good(2),
        unit_id: units(),
        ordered: 1,
        shipped: 0,
        lost: 0,
        delivered: 0,
        realized: 0,
    };
    admit_material_purchase(&state, MaterialPurchase::Delivery(order), money(9))
        .unwrap()
        .0
}

#[test]
fn historical_cost_deferred_local_acquisition_does_not_reprice_second_pass_sales() {
    let closed = advance_material_circuit(&local_cost_opening()).unwrap();
    assert_eq!(closed.local_transfers.len(), 2);
    assert_eq!(closed.procurement[0].admitted_quantity, 1);
    let intermediary = closed
        .income
        .iter()
        .find(|row| row.account == AccountId::Site(site(2)))
        .unwrap();
    assert_eq!(intermediary.statement.sales, money(2));
    assert_eq!(intermediary.statement.cost_of_goods_sold, money(1));
    assert_eq!(intermediary.statement.handling_expense, money(1));
    assert_eq!(intermediary.net_income, money(0));
    let costs = economy(&closed.state).costs.snapshot();
    assert_eq!(
        costs
            .stocks
            .iter()
            .find(|row| row.owner == AccountId::Site(site(2)))
            .unwrap()
            .amount,
        money(9)
    );
    assert_eq!(
        costs
            .stocks
            .iter()
            .find(|row| row.owner == AccountId::Site(site(3)))
            .unwrap()
            .amount,
        money(2)
    );
    assert_eq!(
        closed
            .state
            .inventory
            .iter()
            .find(|row| row.site_id == site(2))
            .unwrap()
            .quantity,
        1
    );
    assert_eq!(
        economy(&closed.state)
            .book
            .total_cash_and_reserves()
            .unwrap(),
        money(20)
    );
}
