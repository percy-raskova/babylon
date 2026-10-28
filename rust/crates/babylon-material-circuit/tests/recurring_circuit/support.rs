//! Leaf implementation for the parent module; public paths stay on the parent.

use babylon_material_circuit::{
    AttendancePlan, CapacityRow, CashAccount, CommodityDefinition, CorridorCapacity,
    EmploymentTerms, FinalDemandOrder, FinalDemandPrincipal, HouseholdCohort, HouseholdNeed,
    HouseholdPurchasePolicy, HouseholdStock, InputOutputCoefficient, LaborCapacityRow,
    LaborCoefficient, MerchantHandling, MerchantHandlingCoefficient, ProcessOutput,
    ProductionCommitment, ProductionDemandPolicy, ReplenishmentPolicy, RouteStage,
    RouteStageCapacity, SellerOffer, SiteLogisticsNode, StockCarryingValue, SupplierRoute,
};

use babylon_material_circuit::{
    AccountId, AidBook, CashTransferPurpose, CircuitAccounting, CorridorId, FinalDemandPrincipalId,
    GoodId, HistoricalCostBook, InventoryRow, LogisticsNodeId, MaterialCatalog,
    MaterialCircuitError, MaterialCircuitState, MaterialCircuitTransition, MaterialPurchase,
    MerchantRole, MonetaryBook, MonetaryCircuit, OrderId, OutboundOrderId, PriceDecision,
    PricePolicy, ProcessId, RecurringEconomy, RouteId, SiteId, StaffingPolicy, StaffingPoolBinding,
    StaffingPoolId, StaffingWorkSource, SupplierTransport, UnitId,
    MATERIAL_CIRCUIT_STATE_DOMAIN_BYTES,
};

use babylon_kernel::currency::Currency;
use babylon_material_circuit::CapacityReservations;
use babylon_material_circuit::CapacitySupply;
use babylon_material_circuit::FinancialInstitutions;
use babylon_material_circuit::HouseholdNeedBasis;
use babylon_material_circuit::HouseholdTimeAccounting;
use babylon_material_circuit::LaborCompensation;
use babylon_material_circuit::StaffingMemberId;

pub(crate) fn site(id: u8) -> SiteId {
    SiteId::from_bytes([id; 32])
}

pub(crate) fn node(id: u8) -> LogisticsNodeId {
    LogisticsNodeId::from_bytes([id; 32])
}

pub(crate) fn good(id: u8) -> GoodId {
    GoodId::from_bytes([id; 32])
}

pub(crate) fn process(id: u8) -> ProcessId {
    ProcessId::from_bytes([id; 32])
}

pub(crate) fn corridor(id: u8) -> CorridorId {
    CorridorId::from_bytes([id; 32])
}

pub(crate) fn route(id: u8) -> RouteId {
    RouteId::from_bytes([id; 32])
}

pub(crate) fn household() -> FinalDemandPrincipalId {
    FinalDemandPrincipalId::from_bytes([1; 32])
}

pub(crate) fn units() -> UnitId {
    UnitId::from_bytes([1; 32])
}

pub(crate) fn hours() -> UnitId {
    UnitId::from_bytes([2; 32])
}

pub(crate) fn money(value: i128) -> Currency {
    Currency::from_micro_units(value)
}

pub(crate) fn inventory(owner: u8, commodity: u8, quantity: u64) -> InventoryRow {
    InventoryRow {
        site_id: site(owner),
        good_id: good(commodity),
        unit_id: units(),
        quantity,
    }
}

#[allow(
    clippy::too_many_lines,
    reason = "a conformance scenario builds its whole fixture and asserts the full trajectory in one test"
)]
pub(crate) fn opening() -> (MaterialCatalog, MaterialCircuitState) {
    let offers = [(1, 1, 1), (2, 2, 3), (3, 2, 4)]
        .into_iter()
        .map(|(owner, commodity, price)| SellerOffer {
            site_id: site(owner),
            good_id: good(commodity),
            unit_id: units(),
            unit_price: money(price),
            pricing: PricePolicy::Fixed,
        })
        .collect();
    let recurring = RecurringEconomy {
        service_inputs: vec![],
        households: vec![HouseholdCohort {
            kind: babylon_material_circuit::HouseholdKind::Ordinary,
            principal_id: household(),
            households: 2,
            persons: 4,
        }],
        household_stocks: vec![HouseholdStock {
            principal_id: household(),
            good_id: good(2),
            unit_id: units(),
            quantity: 8,
        }],
        household_needs: vec![HouseholdNeed {
            principal_id: household(),
            good_id: good(2),
            unit_id: units(),
            basis: HouseholdNeedBasis::Persons,
            units_per_basis: 1,
        }],
        household_purchases: vec![HouseholdPurchasePolicy {
            principal_id: household(),
            retailer_site_id: site(3),
            good_id: good(2),
            unit_id: units(),
            target_closing_stock: 8,
            maximum_purchase: 4,
            enabled: true,
        }],
        offers,
        replenishment: [(2, 1, 1), (3, 2, 2)]
            .into_iter()
            .map(|(buyer, supplier, commodity)| ReplenishmentPolicy {
                buyer_site_id: site(buyer),
                supplier_site_id: site(supplier),
                good_id: good(commodity),
                unit_id: units(),
                target_stock: 4,
                maximum_purchase: 4,
                cash_floor: money(0),
            })
            .collect(),
        production: [1, 2]
            .into_iter()
            .map(|owner| ProductionDemandPolicy {
                process_id: process(owner),
                site_id: site(owner),
                output_buffer: 0,
                planned_batches: 4,
            })
            .collect(),
        attendance: [(1, 4), (2, 8), (3, 4)]
            .into_iter()
            .map(|(owner, planned_hours)| AttendancePlan {
                site_id: site(owner),
                unit_id: hours(),
                period: 1,
                planned_hours,
            })
            .collect(),
        last_household_admission_period: 0,
        last_household_consumption_period: 0,
    };
    let catalog = babylon_material_circuit::MaterialCatalogDefinition {
        capacity_policy: CapacitySupply::FiniteSchedule,
        site_logistics_nodes: [1, 2, 3]
            .into_iter()
            .map(|owner| SiteLogisticsNode {
                site_id: site(owner),
                node_id: node(owner),
            })
            .collect(),
        process_outputs: [1, 2]
            .into_iter()
            .map(|owner| ProcessOutput {
                process_id: process(owner),
                site_id: site(owner),
                good_id: good(owner),
                unit_id: units(),
                quantity_per_batch: 1,
            })
            .collect(),
        input_coefficients: [1, 2]
            .into_iter()
            .map(|owner| InputOutputCoefficient {
                process_id: process(owner),
                good_id: good(owner - 1),
                unit_id: units(),
                quantity_per_batch: 1,
            })
            .collect(),
        labor_coefficients: [(1, 1), (2, 2)]
            .into_iter()
            .map(|(owner, quantity_per_batch)| LaborCoefficient {
                process_id: process(owner),
                unit_id: hours(),
                quantity_per_batch,
            })
            .collect(),
        commodities: [0, 1, 2]
            .into_iter()
            .map(|commodity| CommodityDefinition {
                good_id: good(commodity),
                unit_id: units(),
                kind: babylon_material_circuit::CommodityKind::Storable { grams_per_unit: 1 },
            })
            .collect(),
        supplier_routes: [(1, 2, 1), (2, 3, 2)]
            .into_iter()
            .map(|(supplier, buyer, commodity)| SupplierRoute {
                buyer_site_id: site(buyer),
                supplier_site_id: site(supplier),
                good_id: good(commodity),
                unit_id: units(),
                route_id: route(supplier),
                transport_kind: SupplierTransport::Staged,
            })
            .collect(),
        route_stages: [(1, 2), (2, 3)]
            .into_iter()
            .map(|(source, destination)| RouteStage {
                route_id: route(source),
                stage_index: 0,
                from_node_id: node(source),
                to_node_id: node(destination),
                travel_periods: 1,
                loss_ppm: 0,
            })
            .collect(),
        merchants: vec![MerchantHandling {
            site_id: site(3),
            location: "county:26163"
                .parse()
                .expect("the authored literal parses as the declared type"),
            role: MerchantRole::Retail,
            capacity_id: corridor(3),
            labor_unit_id: hours(),
        }],
        handling_coefficients: vec![MerchantHandlingCoefficient {
            site_id: site(3),
            good_id: good(2),
            unit_id: units(),
            hours_per_unit: 1,
        }],
        maintenance_binding: None,
        aid_mandates: vec![],
        household_time_policy: vec![],
        service_inputs: recurring.service_inputs.clone(),
        household_needs: recurring.household_needs.clone(),
    };
    let state = MaterialCircuitState {
        period: 1,
        accounting: CircuitAccounting::Monetary(Box::new({
            let book = MonetaryBook::open(vec![
                CashAccount {
                    id: AccountId::Site(site(1)),
                    cash: money(4),
                },
                CashAccount {
                    id: AccountId::Site(site(2)),
                    cash: money(12),
                },
                CashAccount {
                    id: AccountId::Site(site(3)),
                    cash: money(8),
                },
                CashAccount {
                    id: AccountId::Household(household()),
                    cash: money(0),
                },
            ])
            .expect("the fixture opens the authored source");
            MonetaryCircuit {
                aid: AidBook::default(),

                household_time: HouseholdTimeAccounting::NotModeled,
                financial: FinancialInstitutions::empty(),
                member_labor: (1..=9)
                    .flat_map(|period| {
                        [(1, 4), (2, 8), (3, 4)]
                            .into_iter()
                            .map(move |(owner, available_hours)| {
                                babylon_material_circuit::MemberLaborCapacityRow {
                                    member_id: StaffingMemberId::from_bytes(site(owner).as_bytes()),
                                    period,
                                    available_hours,
                                }
                            })
                    })
                    .collect(),
                costs: HistoricalCostBook::open(
                    &book,
                    [
                        (AccountId::Site(site(1)), good(0), 0),
                        (AccountId::Site(site(2)), good(1), 4),
                        (AccountId::Site(site(3)), good(2), 12),
                        (AccountId::Household(household()), good(2), 32),
                    ]
                    .into_iter()
                    .map(|(owner, good_id, value)| StockCarryingValue {
                        owner,
                        good_id,
                        unit_id: units(),
                        amount: money(value),
                    })
                    .collect(),
                    vec![],
                    vec![],
                    vec![],
                )
                .expect("the fixture opens the authored source"),
                book,
                recurring: Some(Box::new(recurring)),
                employment: [1, 2, 3]
                    .into_iter()
                    .map(|owner| EmploymentTerms {
                        member_id: StaffingMemberId::from_bytes((site(owner)).as_bytes()),
                        site_id: site(owner),
                        unit_id: hours(),
                        payee: household(),
                        compensation: LaborCompensation::Wage(money(1)),
                    })
                    .collect(),
            }
        })),
        service_connections: vec![],
        service_orders: vec![],
        route_stage_capacities: [1, 2]
            .into_iter()
            .map(|id| RouteStageCapacity {
                route_id: route(id),
                stage_index: 0,
                corridor_id: corridor(id),
            })
            .collect(),
        inventory: vec![inventory(1, 0, 40), inventory(2, 1, 4), inventory(3, 2, 4)],
        orders: vec![],
        freight: vec![],
        corridor_capacities: (1..=9)
            .flat_map(|period| {
                [1, 2, 3].into_iter().map(move |id| CorridorCapacity {
                    corridor_id: corridor(id),
                    period,
                    available_grams: 4,
                })
            })
            .collect(),
        capacities: (1..=9)
            .flat_map(|period| {
                [1, 2].into_iter().map(move |owner| CapacityRow {
                    process_id: process(owner),
                    site_id: site(owner),
                    period,
                    available_batches: 4,
                })
            })
            .collect(),
        labor: (1..=9)
            .flat_map(|period| {
                [(1, 4), (2, 8), (3, 4)]
                    .into_iter()
                    .map(move |(owner, available)| LaborCapacityRow {
                        site_id: site(owner),
                        unit_id: hours(),
                        period,
                        available,
                    })
            })
            .collect(),
        production_commitments: [1, 2]
            .into_iter()
            .map(|owner| ProductionCommitment {
                process_id: process(owner),
                site_id: site(owner),
                period: 1,
                planned_batches: 4,
            })
            .collect(),
        final_demand_principals: vec![FinalDemandPrincipal {
            id: household(),
            location: "county:26163"
                .parse()
                .expect("the authored literal parses as the declared type"),
        }],
        final_demand_orders: vec![],
        maintenance_service: None,
        capacity_reservations: CapacityReservations::default(),
    };
    (
        MaterialCatalog::try_new(catalog).expect("the authored fixture catalog is valid"),
        state,
    )
}

pub(crate) fn economy(state: &MaterialCircuitState) -> &MonetaryCircuit {
    let CircuitAccounting::Monetary(value) = &state.accounting else {
        panic!("monetary control")
    };
    value
}

pub(crate) fn recurring_mut(state: &mut MaterialCircuitState) -> &mut RecurringEconomy {
    let CircuitAccounting::Monetary(value) = &mut state.accounting else {
        panic!("monetary control")
    };
    value
        .recurring
        .as_mut()
        .expect("the fixture set the optional field before this borrow")
}

pub(crate) fn output(transition: &MaterialCircuitTransition, owner: u8) -> u64 {
    transition
        .production
        .iter()
        .find(|row| row.site_id == site(owner))
        .map_or(0, |row| row.produced_batches)
}

#[test]
#[allow(
    clippy::too_many_lines,
    reason = "a conformance scenario builds its whole fixture and asserts the full trajectory in one test"
)]
pub(crate) fn eight_period_control_reproduces_paid_idle_withdrawal_recovery_and_conservation() {
    let (catalog, mut state) = opening();
    let mut results = Vec::new();
    let mut consumption = 0;
    let mut used = 0;
    let mut idle = 0;
    let mut unplanned = 0;
    let expected_cash = [
        [0, 0, 8, 0],
        [0, 0, 8, 0],
        [0, 0, 4, 16],
        [0, 0, 4, 20],
        [0, 0, 4, 20],
        [0, 0, 4, 8],
        [0, 0, 4, 4],
        [0, 0, 4, 4],
    ];
    let mut digests = Vec::new();
    for period in 1..=8 {
        recurring_mut(&mut state).household_purchases[0].enabled = ![3, 4].contains(&period);
        let captured = babylon_material_circuit::encode_material_circuit_state(&catalog, &state)
            .expect("the canonical material state encodes");
        let restarted =
            babylon_material_circuit::decode_material_circuit_state(&catalog, &captured)
                .expect("the canonical material bytes decode");
        let digest = babylon_material_circuit::material_circuit_state_digest(&catalog, &state)
            .expect("the authored material state has a canonical digest");
        assert_eq!(
            babylon_material_circuit::material_circuit_state_digest(&catalog, &restarted)
                .expect("the restarted material state has a canonical digest"),
            digest,
            "period {period}: a canonical restart preserves the state digest"
        );
        digests.push(digest);
        let closed = babylon_material_circuit::advance_material_circuit(&catalog, &state)
            .expect("the authored material state advances one period");
        assert_eq!(
            closed,
            babylon_material_circuit::advance_material_circuit(&catalog, &restarted)
                .expect("the authored material state advances one period")
        );
        let wages: i128 = closed
            .wage_accruals
            .iter()
            .map(|row| row.amount.micro_units())
            .sum();
        let bought: u64 = closed
            .household_demand
            .iter()
            .map(|row| row.fulfilled_quantity)
            .sum();
        results.push((bought, output(&closed, 1), output(&closed, 2), wages));
        consumption += closed
            .household_consumption
            .iter()
            .map(|row| row.consumed_quantity)
            .sum::<u64>();
        used += closed
            .labor_use
            .iter()
            .map(|row| row.used_hours)
            .sum::<u64>();
        idle += closed
            .labor_use
            .iter()
            .map(|row| row.paid_idle_hours)
            .sum::<u64>();
        unplanned += closed
            .labor_use
            .iter()
            .map(|row| row.unplanned_hours)
            .sum::<u64>();
        let accounts = &economy(&closed.state).book;
        assert_eq!(
            accounts
                .total_cash_and_reserves()
                .expect("the fixture book totals without overflow"),
            money(24)
        );
        let actual_cash = [
            AccountId::Site(site(1)),
            AccountId::Site(site(2)),
            AccountId::Site(site(3)),
            AccountId::Household(household()),
        ]
        .map(|id| {
            accounts
                .cash(id)
                .expect("the fixture book holds the payer account")
                .micro_units()
        });
        assert_eq!(
            actual_cash,
            expected_cash
                [usize::try_from(period - 1).expect("the fixture value fits the target range")],
            "period {period}"
        );
        let physical = closed
            .state
            .inventory
            .iter()
            .map(|row| row.quantity)
            .sum::<u64>()
            + closed
                .state
                .freight
                .iter()
                .map(|row| row.quantity)
                .sum::<u64>()
            + economy(&closed.state)
                .recurring
                .as_ref()
                .expect("the fixture set the optional field before this read")
                .household_stocks
                .iter()
                .map(|row| row.quantity)
                .sum::<u64>()
            + consumption;
        assert_eq!(physical, 56, "period {period}");
        assert_eq!(closed.state.final_demand_orders.len(), 0);
        assert_eq!(closed.household_consumption[0].required_quantity, 4);
        if period == 5 {
            assert_eq!(closed.household_consumption[0].unmet_quantity, 4);
        }
        state = closed.state;
    }
    assert_eq!(
        results,
        [
            (4, 4, 4, 16),
            (4, 4, 4, 16),
            (0, 4, 4, 16),
            (0, 4, 0, 4),
            (0, 0, 0, 0),
            (4, 0, 0, 4),
            (4, 0, 4, 12),
            (4, 4, 4, 16)
        ]
    );
    assert_eq!((consumption, used, idle, unplanned), (28, 80, 4, 44));
    // One canonical digest per pre-close opening. The compact v4 frame seals the
    // catalog digest, so these values intentionally differ from the pre-split
    // frame; they pin the post-split encoding as well as the quantity trajectory.
    let expected_digests = [
        "42761fc58201184fb0eaa8015e99566cfc0c44ea6eae2c7ae67a3a1952598b8f",
        "3842e4812265a774fe00352b9d09f21f7d917870768c1f8dfafb6469f5df158d",
        "bea01cb8bc108824a8c4477ba85bbd0115f53bbbf951542e643a6dc42e65ca8c",
        "85596f6e8ea75ac24dda95ceafa017b82302ffc83f0407d352312a30fb388b88",
        "989a8816fa999712139a4a4e688e13696f76430545ecfb543da8ce72d4a49230",
        "95dbfbae8ab41472c12295606d294576fcc7b50c03bacb9fccb527f9eef5022c",
        "26bb574058cf105944755de02419e2d91ff27d0f71399c9c287a42d06f0a5e8a",
        "ec2bfc11631a89b1a97ba1d48b0b6f1b8f959aa380c9169a7cd47cd6dbf808dd",
    ];
    assert_eq!(
        digests
            .iter()
            .map(|digest| {
                use std::fmt::Write;
                let mut text = String::with_capacity(digest.len().saturating_mul(2));
                for byte in digest {
                    write!(&mut text, "{byte:02x}").expect("writing to String cannot fail");
                }
                text
            })
            .collect::<Vec<_>>(),
        expected_digests
    );
    assert_eq!(
        state
            .inventory
            .iter()
            .find(|row| row.site_id == site(1) && row.good_id == good(0))
            .expect("the fixture holds the searched element")
            .quantity,
        20
    );
}

#[test]
pub(crate) fn prior_funded_transit_suppresses_duplicate_procurement_and_does_not_supply_current_production(
) {
    let (catalog, state) = opening();
    let mut catalog = catalog.into_definition();
    catalog.route_stages[0].travel_periods = 3;
    let catalog = MaterialCatalog::try_new(catalog).expect("the fixture catalog stays valid");
    let first = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    let second = babylon_material_circuit::advance_material_circuit(&catalog, &first.state)
        .expect("the authored material state advances one period");
    assert_eq!(output(&second, 2), 0);
    let raw = second
        .procurement
        .iter()
        .find(|row| row.buyer_site_id == site(2))
        .expect("the fixture holds the searched element");
    assert_eq!(
        (raw.on_hand, raw.outstanding_inbound, raw.admitted_quantity),
        (0, 4, 0)
    );
    assert_eq!(
        second
            .state
            .freight
            .iter()
            .filter(|row| row.destination_site_id == site(2))
            .map(|row| row.quantity)
            .sum::<u64>(),
        4
    );
}

#[test]
pub(crate) fn responsive_next_quote_does_not_reprice_existing_reserves() {
    let (catalog, mut state) = opening();
    state
        .inventory
        .iter_mut()
        .find(|row| row.site_id == site(3))
        .expect("the fixture holds the searched element")
        .quantity = 0;
    let CircuitAccounting::Monetary(accounts) = &mut state.accounting else {
        unreachable!()
    };
    let mut captured = accounts.costs.snapshot();
    captured
        .stocks
        .iter_mut()
        .find(|row| row.owner == AccountId::Site(site(3)))
        .expect("the fixture holds the searched element")
        .amount = money(0);
    // This scenario starts without the retailer's stock or its opening asset.
    accounts.costs = HistoricalCostBook::open(
        &accounts.book,
        captured.stocks,
        captured.freight,
        vec![],
        vec![],
    )
    .expect("the fixture opens the authored source");
    let offer = recurring_mut(&mut state)
        .offers
        .iter_mut()
        .find(|row| row.site_id == site(3))
        .expect("the fixture holds the searched element");
    offer.pricing = PricePolicy::Responsive {
        minimum: money(2),
        maximum: money(8),
        step: money(1),
        target_stock: 0,
    };
    let closed = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    let quote = closed
        .prices
        .iter()
        .find(|row| row.site_id == site(3))
        .expect("the fixture holds the searched element");
    assert_eq!(
        (quote.old_price, quote.next_price, quote.reason),
        (money(4), money(5), PriceDecision::UnservedDemand)
    );
    assert_eq!(closed.household_demand[0].unit_price, money(4));
    assert_eq!(closed.household_demand[0].expired_quantity, 4);
    let reserved = economy(&closed.state).book.snapshot().purchases;
    assert!(reserved
        .iter()
        .all(|row| row.unit_price == money(1) || row.unit_price == money(3)));
}

#[test]
pub(crate) fn consumption_or_procurement_failure_leaves_all_opening_accounts_unchanged() {
    let (catalog, mut state) = opening();
    let policy = &mut recurring_mut(&mut state).production[0];
    policy.output_buffer = u64::MAX;
    let unchanged = state.clone();
    assert_eq!(
        babylon_material_circuit::advance_material_circuit(&catalog, &state),
        Err(MaterialCircuitError::Arithmetic)
    );
    assert_eq!(state, unchanged);
}

#[test]
pub(crate) fn captured_household_policies_refuse_old_bytes_bad_cursors_and_noncanonical_rows() {
    let (catalog, state) = opening();
    let bytes = babylon_material_circuit::encode_material_circuit_state(&catalog, &state)
        .expect("the canonical material state encodes");
    assert_eq!(
        babylon_material_circuit::decode_material_circuit_state(&catalog, &bytes)
            .expect("the canonical material bytes decode"),
        state
    );
    let mut previous = bytes.clone();
    let version = MATERIAL_CIRCUIT_STATE_DOMAIN_BYTES.len() + 1;
    previous[version..version + 2].copy_from_slice(&5_u16.to_be_bytes());
    assert_eq!(
        babylon_material_circuit::decode_material_circuit_state(&catalog, &previous),
        Err(MaterialCircuitError::WireVersion)
    );
    for length in 0..bytes.len() {
        assert!(babylon_material_circuit::decode_material_circuit_state(
            &catalog,
            &bytes[..length]
        )
        .is_err());
    }
    let mut trailing = bytes;
    trailing.push(0);
    assert_eq!(
        babylon_material_circuit::decode_material_circuit_state(&catalog, &trailing),
        Err(MaterialCircuitError::WireTrailing)
    );
}

#[test]
pub(crate) fn retained_finite_purchase_restores_attendance_when_recurring_purchases_are_disabled() {
    let (catalog, mut state) = opening();
    recurring_mut(&mut state).household_purchases[0].enabled = false;
    recurring_mut(&mut state)
        .attendance
        .iter_mut()
        .find(|row| row.site_id == site(3))
        .expect("the fixture holds the searched element")
        .planned_hours = 0;
    let CircuitAccounting::Monetary(accounts) = &mut state.accounting else {
        unreachable!()
    };
    accounts
        .book
        .transfer_cash(
            AccountId::Site(site(3)),
            AccountId::Household(household()),
            money(4),
            CashTransferPurpose::HouseholdTransfer,
        )
        .expect("the fixture transfer stays funded");
    let captured = accounts.costs.snapshot();
    // This control opens after its deliberate endowment transfer.
    accounts.costs = HistoricalCostBook::open(
        &accounts.book,
        captured.stocks,
        captured.freight,
        vec![],
        vec![],
    )
    .expect("the fixture opens the authored source");
    let id = OrderId::from_bytes([90; 32]);
    let (state, _) = babylon_material_circuit::admit_material_purchase(
        &catalog,
        &state,
        MaterialPurchase::LocalFinalDemand(FinalDemandOrder {
            order_id: id,
            retailer_site_id: site(3),
            demand_principal_id: household(),
            good_id: good(2),
            unit_id: units(),
            ordered: 1,
            fulfilled: 0,
        }),
        money(4),
    )
    .expect("the fixture admits the authored purchase");
    let first = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    assert_eq!(first.state.final_demand_orders[0].fulfilled, 0);
    assert_eq!(
        economy(&first.state)
            .recurring
            .as_ref()
            .expect("the fixture set the optional field before this read")
            .attendance
            .iter()
            .find(|row| row.site_id == site(3))
            .expect("the fixture holds the searched element")
            .planned_hours,
        1
    );
    let second = babylon_material_circuit::advance_material_circuit(&catalog, &first.state)
        .expect("the authored material state advances one period");
    assert_eq!(second.local_fulfillments[0].quantity, 1);
    assert_eq!(second.household_consumption[0].available_quantity, 5);
    assert_eq!(second.state.final_demand_orders.len(), 0);
    assert!(economy(&second.state)
        .book
        .purchase(OutboundOrderId::LocalFinalDemand(id))
        .is_err());
}

pub(crate) fn producer_retail_opening() -> (MaterialCatalog, MaterialCircuitState) {
    let (catalog, mut state) = opening();
    let mut catalog = catalog.into_definition();
    catalog.merchants.push(MerchantHandling {
        site_id: site(1),
        location: "county:26163"
            .parse()
            .expect("the authored literal parses as the declared type"),
        role: MerchantRole::Retail,
        capacity_id: corridor(4),
        labor_unit_id: hours(),
    });
    catalog
        .handling_coefficients
        .push(MerchantHandlingCoefficient {
            site_id: site(1),
            good_id: good(1),
            unit_id: units(),
            hours_per_unit: 1,
        });

    state
        .corridor_capacities
        .extend((1..=9).map(|period| CorridorCapacity {
            corridor_id: corridor(4),
            period,
            available_grams: 8,
        }));
    let rows = recurring_mut(&mut state);
    rows.household_stocks.push(HouseholdStock {
        principal_id: household(),
        good_id: good(1),
        unit_id: units(),
        quantity: 0,
    });
    let need = HouseholdNeed {
        principal_id: household(),
        good_id: good(1),
        unit_id: units(),
        basis: HouseholdNeedBasis::Persons,
        units_per_basis: 1,
    };
    rows.household_needs.push(need.clone());
    catalog.household_needs.push(need);
    rows.household_purchases[0].enabled = false;
    rows.household_purchases.push(HouseholdPurchasePolicy {
        principal_id: household(),
        retailer_site_id: site(1),
        good_id: good(1),
        unit_id: units(),
        target_closing_stock: 0,
        maximum_purchase: 1,
        enabled: true,
    });
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        unreachable!()
    };
    let mut captured = economy.costs.snapshot();
    captured.stocks.push(StockCarryingValue {
        owner: AccountId::Household(household()),
        good_id: good(1),
        unit_id: units(),
        amount: money(0),
    });
    economy.costs =
        HistoricalCostBook::from_snapshot(captured).expect("the snapshot admits the derived value");
    let catalog = MaterialCatalog::try_new(catalog).expect("the fixture catalog stays valid");
    (catalog, state)
}

#[test]
pub(crate) fn a_shared_production_and_retail_pool_requests_each_kind_of_work_once() {
    let (catalog, mut state) = producer_retail_opening();
    recurring_mut(&mut state).production[0].output_buffer = 4;
    let bindings = [
        (
            1,
            1,
            vec![
                StaffingWorkSource::Production(process(1)),
                StaffingWorkSource::MerchantHandling(site(1)),
            ],
        ),
        (2, 2, vec![StaffingWorkSource::Production(process(2))]),
        (3, 1, vec![StaffingWorkSource::MerchantHandling(site(3))]),
    ]
    .into_iter()
    .map(|(owner, persons, sources)| {
        StaffingPoolBinding::try_new(
            StaffingPoolId::from_bytes([owner; 32]),
            site(owner),
            hours(),
            persons,
            StaffingPolicy::one_period(4).expect("the one-period fixture advances"),
            sources,
        )
        .expect("the authored fixture satisfies the constructor invariants")
    })
    .collect::<Vec<_>>();
    let closed = babylon_material_circuit::close_material_period(&catalog, &state)
        .expect("the material period closes");
    let requests = closed
        .staffing_requests(&catalog, &bindings)
        .expect("the fixture staffing requests are present");
    let source = requests
        .iter()
        .filter(|row| row.site_id() == site(1))
        .collect::<Vec<_>>();
    assert_eq!(source.len(), 2);
    assert_eq!(
        source
            .iter()
            .find(|row| row.work_source() == StaffingWorkSource::Production(process(1)))
            .expect("the fixture holds the searched element")
            .hours(),
        4
    );
    assert_eq!(
        source
            .iter()
            .find(|row| row.work_source() == StaffingWorkSource::MerchantHandling(site(1)))
            .expect("the fixture holds the searched element")
            .hours(),
        5
    );
}

#[test]
pub(crate) fn cash_backed_unfilled_retail_demand_can_restart_a_producer_with_no_opening_sales() {
    let (catalog, mut state) = producer_retail_opening();
    state
        .production_commitments
        .retain(|row| row.site_id != site(1));
    let rows = recurring_mut(&mut state);
    rows.production[0].planned_batches = 0;
    rows.attendance
        .iter_mut()
        .find(|row| row.site_id == site(1))
        .expect("the fixture holds the searched element")
        .planned_hours = 0;
    rows.replenishment.clear();
    let closed = babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the authored material state advances one period");
    let demand = closed
        .household_demand
        .iter()
        .find(|row| row.good_id == good(1))
        .expect("the fixture holds the searched element");
    assert_eq!(
        (
            demand.admitted_quantity,
            demand.fulfilled_quantity,
            demand.expired_quantity
        ),
        (1, 0, 1)
    );
    let plan = closed
        .production_plans
        .iter()
        .find(|row| row.site_id == site(1))
        .expect("the fixture holds the searched element");
    assert_eq!(plan.planned_batches, 1);
    assert!(closed
        .state
        .production_commitments
        .iter()
        .any(|row| row.site_id == site(1) && row.planned_batches == 1));
}

#[test]
pub(crate) fn a_household_purchase_without_a_recipient_stock_is_refused_before_reserving_cash() {
    let (catalog, mut state) = producer_retail_opening();
    let rows = recurring_mut(&mut state);
    rows.household_stocks.retain(|row| row.good_id != good(1));
    rows.household_needs.retain(|row| row.good_id != good(1));
    rows.household_purchases
        .retain(|row| row.good_id != good(1));
    let CircuitAccounting::Monetary(accounts) = &mut state.accounting else {
        unreachable!()
    };
    accounts
        .book
        .transfer_cash(
            AccountId::Site(site(1)),
            AccountId::Household(household()),
            money(1),
            CashTransferPurpose::HouseholdTransfer,
        )
        .expect("the fixture transfer stays funded");
    let mut captured = accounts.costs.snapshot();
    captured
        .stocks
        .retain(|row| row.owner != AccountId::Household(household()) || row.good_id != good(1));
    // Capture this fixture's changed opening endowments and absent stock explicitly.
    accounts.costs = HistoricalCostBook::open(
        &accounts.book,
        captured.stocks,
        captured.freight,
        vec![],
        vec![],
    )
    .expect("the fixture opens the authored source");
    let original = state.clone();
    assert_eq!(
        babylon_material_circuit::admit_material_purchase(
            &catalog,
            &state,
            MaterialPurchase::LocalFinalDemand(FinalDemandOrder {
                order_id: OrderId::from_bytes([91; 32]),
                retailer_site_id: site(1),
                demand_principal_id: household(),
                good_id: good(1),
                unit_id: units(),
                ordered: 1,
                fulfilled: 0,
            }),
            money(1),
        ),
        Err(MaterialCircuitError::FinalDemandInvariant)
    );
    assert_eq!(state, original);
}
