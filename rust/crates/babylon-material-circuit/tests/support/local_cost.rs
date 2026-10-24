//! Two outbound passes must not blend incoming local basis into old stock sold now.
use crate::inventory;
use babylon_material_circuit::AccountId;
use babylon_material_circuit::AidBook;
use babylon_material_circuit::AttendancePlan;
use babylon_material_circuit::CashAccount;
use babylon_material_circuit::CircuitAccounting;
use babylon_material_circuit::CorridorCapacity;
use babylon_material_circuit::EmploymentTerms;
use babylon_material_circuit::FinancialInstitutions;
use babylon_material_circuit::HistoricalCostBook;
use babylon_material_circuit::HouseholdTimeAccounting;
use babylon_material_circuit::LaborCapacityRow;
use babylon_material_circuit::MaterialCircuitState;
use babylon_material_circuit::MaterialPurchase;
use babylon_material_circuit::MonetaryBook;
use babylon_material_circuit::MonetaryCircuit;
use babylon_material_circuit::OrderAccessMode;
use babylon_material_circuit::OrderId;
use babylon_material_circuit::OrderRow;
use babylon_material_circuit::PricePolicy;
use babylon_material_circuit::RecurringEconomy;
use babylon_material_circuit::ReplenishmentPolicy;
use babylon_material_circuit::SellerOffer;
use babylon_material_circuit::StaffingMemberId;
use babylon_material_circuit::StockCarryingValue;
use babylon_material_circuit::SupplierRoute;
use babylon_material_circuit::SupplierTransport;

fn local_cost_economy() -> MonetaryCircuit {
    let book = MonetaryBook::open(
        [
            (AccountId::Site(crate::site(1)), 0),
            (AccountId::Site(crate::site(2)), 10),
            (AccountId::Site(crate::site(3)), 10),
            (AccountId::Household(crate::household()), 0),
        ]
        .into_iter()
        .map(|(id, value)| CashAccount {
            id,
            cash: crate::money(value),
        })
        .collect(),
    )
    .expect("the fixture opens the authored source");
    let costs = HistoricalCostBook::open(
        &book,
        [1, 2]
            .into_iter()
            .map(|id| StockCarryingValue {
                owner: AccountId::Site(crate::site(id)),
                good_id: crate::good(2),
                unit_id: crate::units(),
                amount: crate::money(1),
            })
            .collect(),
        vec![],
        vec![],
        vec![],
    )
    .expect("the fixture opens the authored source");
    MonetaryCircuit {
        aid: AidBook::default(),

        household_time: HouseholdTimeAccounting::NotModeled,
        financial: FinancialInstitutions::empty(),
        member_labor: (1..=2)
            .map(|period| babylon_material_circuit::MemberLaborCapacityRow {
                member_id: StaffingMemberId::from_bytes(crate::site(2).as_bytes()),
                period,
                available_hours: 1,
            })
            .collect(),
        book,
        costs,
        employment: vec![EmploymentTerms {
            member_id: StaffingMemberId::from_bytes((crate::site(2)).as_bytes()),
            site_id: crate::site(2),
            unit_id: crate::hours(),
            payee: crate::household(),
            compensation: babylon_material_circuit::LaborCompensation::Wage(crate::money(1)),
        }],
        recurring: Some(Box::new(RecurringEconomy {
            service_inputs: vec![],
            households: vec![],
            household_stocks: vec![],
            household_needs: vec![],
            household_purchases: vec![],
            offers: vec![SellerOffer {
                site_id: crate::site(2),
                good_id: crate::good(2),
                unit_id: crate::units(),
                unit_price: crate::money(2),
                pricing: PricePolicy::Fixed,
            }],
            replenishment: vec![ReplenishmentPolicy {
                buyer_site_id: crate::site(3),
                supplier_site_id: crate::site(2),
                good_id: crate::good(2),
                unit_id: crate::units(),
                target_stock: 1,
                maximum_purchase: 1,
                cash_floor: crate::money(0),
            }],
            production: vec![],
            attendance: vec![AttendancePlan {
                site_id: crate::site(2),
                unit_id: crate::hours(),
                period: 1,
                planned_hours: 1,
            }],
            last_household_admission_period: 0,
            last_household_consumption_period: 0,
        })),
    }
}

fn local_cost_opening() -> MaterialCircuitState {
    let mut state = crate::opening();
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
            supplier_site_id: crate::site(supplier),
            buyer_site_id: crate::site(buyer),
            good_id: crate::good(2),
            unit_id: crate::units(),
            route_id: crate::route(supplier),
            transport_kind: SupplierTransport::Local,
        })
        .collect();
    state.merchants[0].site_id = crate::site(2);
    state.handling_coefficients[0].site_id = crate::site(2);
    state.corridor_capacities = (1..=2)
        .map(|period| CorridorCapacity {
            corridor_id: crate::corridor(3),
            period,
            available_grams: 2,
        })
        .collect();
    state.labor = (1..=2)
        .map(|period| LaborCapacityRow {
            site_id: crate::site(2),
            unit_id: crate::hours(),
            period,
            available: 1,
        })
        .collect();
    let order = OrderRow {
        order_id: OrderId::from_bytes([50; 32]),
        access_mode: OrderAccessMode::CommoditySale,
        supplier_site_id: crate::site(1),
        buyer_site_id: crate::site(2),
        good_id: crate::good(2),
        unit_id: crate::units(),
        ordered: 1,
        shipped: 0,
        lost: 0,
        delivered: 0,
        realized: 0,
    };
    babylon_material_circuit::admit_material_purchase(
        &state,
        MaterialPurchase::Delivery(order),
        crate::money(9),
    )
    .expect("the fixture admits the authored purchase")
    .0
}

#[test]
fn historical_cost_deferred_local_acquisition_does_not_reprice_second_pass_sales() {
    let closed = babylon_material_circuit::advance_material_circuit(&local_cost_opening())
        .expect("the authored material state advances one period");
    assert_eq!(closed.local_transfers.len(), 2);
    assert_eq!(closed.procurement[0].admitted_quantity, 1);
    let intermediary = closed
        .income
        .iter()
        .find(|row| row.account == AccountId::Site(crate::site(2)))
        .expect("the fixture holds the searched element");
    assert_eq!(intermediary.statement.sales, crate::money(2));
    assert_eq!(intermediary.statement.cost_of_goods_sold, crate::money(1));
    assert_eq!(intermediary.statement.handling_expense, crate::money(1));
    assert_eq!(intermediary.net_income, crate::money(0));
    let costs = crate::economy(&closed.state).costs.snapshot();
    assert_eq!(
        costs
            .stocks
            .iter()
            .find(|row| row.owner == AccountId::Site(crate::site(2)))
            .expect("the fixture holds the searched element")
            .amount,
        crate::money(9)
    );
    assert_eq!(
        costs
            .stocks
            .iter()
            .find(|row| row.owner == AccountId::Site(crate::site(3)))
            .expect("the fixture holds the searched element")
            .amount,
        crate::money(2)
    );
    assert_eq!(
        closed
            .state
            .inventory
            .iter()
            .find(|row| row.site_id == crate::site(2))
            .expect("the fixture holds the searched element")
            .quantity,
        1
    );
    assert_eq!(
        crate::economy(&closed.state)
            .book
            .total_cash_and_reserves()
            .expect("the fixture book totals without overflow"),
        crate::money(20)
    );
}
