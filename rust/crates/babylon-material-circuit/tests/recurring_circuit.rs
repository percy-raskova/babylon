//! Executable witness for the independently worked eight-period accounting control.
use babylon_kernel::currency::Currency;
use babylon_material_circuit::*;

fn site(id: u8) -> SiteId {
    SiteId::from_bytes([id; 32])
}
fn node(id: u8) -> LogisticsNodeId {
    LogisticsNodeId::from_bytes([id; 32])
}
fn good(id: u8) -> GoodId {
    GoodId::from_bytes([id; 32])
}
fn process(id: u8) -> ProcessId {
    ProcessId::from_bytes([id; 32])
}
fn corridor(id: u8) -> CorridorId {
    CorridorId::from_bytes([id; 32])
}
fn route(id: u8) -> RouteId {
    RouteId::from_bytes([id; 32])
}
fn household() -> FinalDemandPrincipalId {
    FinalDemandPrincipalId::from_bytes([1; 32])
}
fn units() -> UnitId {
    UnitId::from_bytes([1; 32])
}
fn hours() -> UnitId {
    UnitId::from_bytes([2; 32])
}
fn money(value: i128) -> Currency {
    Currency::from_micro_units(value)
}
fn inventory(owner: u8, commodity: u8, quantity: u64) -> InventoryRow {
    InventoryRow {
        site_id: site(owner),
        good_id: good(commodity),
        unit_id: units(),
        quantity,
    }
}

fn opening() -> MaterialCircuitState {
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
        households: vec![HouseholdCohort {
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
            units_per_person: 1,
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
    MaterialCircuitState {
        period: 1,
        accounting: CircuitAccounting::Monetary(MonetaryCircuit {
            recurring: Some(Box::new(recurring)),
            book: MonetaryBook::open(vec![
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
            .unwrap(),
            employment: [1, 2, 3]
                .into_iter()
                .map(|owner| EmploymentTerms {
                    site_id: site(owner),
                    unit_id: hours(),
                    payee: household(),
                    hourly_rate: money(1),
                })
                .collect(),
        }),
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
        freight_mass_coefficients: [0, 1, 2]
            .into_iter()
            .map(|commodity| FreightMassCoefficient {
                good_id: good(commodity),
                unit_id: units(),
                grams_per_unit: 1,
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
        backlog: vec![],
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
        merchants: vec![MerchantHandling {
            site_id: site(3),
            county_geoid: *b"26163",
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
        final_demand_principals: vec![FinalDemandPrincipal {
            id: household(),
            county_geoid: *b"26163",
        }],
        final_demand_orders: vec![],
        maintenance_binding: None,
        maintenance_service: None,
    }
}

fn economy(state: &MaterialCircuitState) -> &MonetaryCircuit {
    let CircuitAccounting::Monetary(value) = &state.accounting else {
        panic!("monetary control")
    };
    value
}
fn recurring_mut(state: &mut MaterialCircuitState) -> &mut RecurringEconomy {
    let CircuitAccounting::Monetary(value) = &mut state.accounting else {
        panic!("monetary control")
    };
    value.recurring.as_mut().unwrap()
}
fn output(transition: &MaterialCircuitTransition, owner: u8) -> u64 {
    transition
        .production
        .iter()
        .find(|row| row.site_id == site(owner))
        .map_or(0, |row| row.produced_batches)
}

#[test]
fn eight_period_control_reproduces_paid_idle_withdrawal_recovery_and_conservation() {
    let mut state = opening();
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
    for period in 1..=8 {
        recurring_mut(&mut state).household_purchases[0].enabled = ![3, 4].contains(&period);
        let captured = encode_material_circuit_state(&state).unwrap();
        let restarted = decode_material_circuit_state(&captured).unwrap();
        let closed = advance_material_circuit(&state).unwrap();
        assert_eq!(closed, advance_material_circuit(&restarted).unwrap());
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
        assert_eq!(accounts.total_cash_and_reserves().unwrap(), money(24));
        let actual_cash = [
            AccountId::Site(site(1)),
            AccountId::Site(site(2)),
            AccountId::Site(site(3)),
            AccountId::Household(household()),
        ]
        .map(|id| accounts.cash(id).unwrap().micro_units());
        assert_eq!(
            actual_cash,
            expected_cash[usize::try_from(period - 1).unwrap()],
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
                .unwrap()
                .household_stocks
                .iter()
                .map(|row| row.quantity)
                .sum::<u64>()
            + consumption;
        assert_eq!(physical, 56, "period {period}");
        assert!(closed.state.final_demand_orders.is_empty());
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
    assert_eq!(
        state
            .inventory
            .iter()
            .find(|row| row.site_id == site(1) && row.good_id == good(0))
            .unwrap()
            .quantity,
        20
    );
}

#[test]
fn prior_funded_transit_suppresses_duplicate_procurement_and_does_not_supply_current_production() {
    let mut state = opening();
    state.route_stages[0].travel_periods = 3;
    let first = advance_material_circuit(&state).unwrap();
    let second = advance_material_circuit(&first.state).unwrap();
    assert_eq!(output(&second, 2), 0);
    let raw = second
        .procurement
        .iter()
        .find(|row| row.buyer_site_id == site(2))
        .unwrap();
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
fn responsive_next_quote_does_not_reprice_existing_reserves() {
    let mut state = opening();
    state
        .inventory
        .iter_mut()
        .find(|row| row.site_id == site(3))
        .unwrap()
        .quantity = 0;
    let offer = recurring_mut(&mut state)
        .offers
        .iter_mut()
        .find(|row| row.site_id == site(3))
        .unwrap();
    offer.pricing = PricePolicy::Responsive {
        minimum: money(2),
        maximum: money(8),
        step: money(1),
        target_stock: 0,
    };
    let closed = advance_material_circuit(&state).unwrap();
    let quote = closed
        .prices
        .iter()
        .find(|row| row.site_id == site(3))
        .unwrap();
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
fn consumption_or_procurement_failure_leaves_all_opening_accounts_unchanged() {
    let mut state = opening();
    let policy = &mut recurring_mut(&mut state).production[0];
    policy.output_buffer = u64::MAX;
    let unchanged = state.clone();
    assert_eq!(
        advance_material_circuit(&state),
        Err(MaterialCircuitError::Arithmetic)
    );
    assert_eq!(state, unchanged);
}

#[test]
fn captured_household_policies_refuse_old_bytes_bad_cursors_and_noncanonical_rows() {
    let state = opening();
    let bytes = encode_material_circuit_state(&state).unwrap();
    let mut finite = state.clone();
    let CircuitAccounting::Monetary(economy) = &mut finite.accounting else {
        unreachable!()
    };
    economy.recurring = None;
    let offset = encode_material_circuit_state(&finite).unwrap().len() - 1;
    assert_eq!(bytes[offset], 1);
    let mut old = bytes.clone();
    let version = MATERIAL_CIRCUIT_STATE_DOMAIN_BYTES.len() + 1;
    old[version..version + 2].copy_from_slice(&5_u16.to_be_bytes());
    assert_eq!(
        decode_material_circuit_state(&old),
        Err(MaterialCircuitError::WireVersion)
    );
    let mut replayed = bytes.clone();
    replayed[offset + 1..offset + 9].copy_from_slice(&1_u64.to_be_bytes());
    assert_eq!(
        decode_material_circuit_state(&replayed),
        Err(MaterialCircuitError::PeriodInvariant)
    );
    let mut excessive = bytes.clone();
    excessive[offset + 17..offset + 21].copy_from_slice(&65_537_u32.to_be_bytes());
    assert_eq!(
        decode_material_circuit_state(&excessive),
        Err(MaterialCircuitError::WireLimit)
    );
    // The captured control has one 48-byte cohort, one 104-byte stock and
    // need, one 145-byte policy, then three 113-byte fixed-price offers.
    let purchase = offset + 17 + 4 + 48 + 4 + 104 + 4 + 104 + 4;
    let mut invalid = bytes.clone();
    invalid[purchase + 144] = 2;
    assert_eq!(
        decode_material_circuit_state(&invalid),
        Err(MaterialCircuitError::WireEnum)
    );
    let offer = purchase + 145 + 4;
    let mut unordered = bytes.clone();
    unordered[offer..offer + 226].rotate_left(113);
    assert_eq!(
        decode_material_circuit_state(&unordered),
        Err(MaterialCircuitError::WireNoncanonical)
    );
}

#[test]
fn retained_finite_purchase_restores_attendance_when_recurring_purchases_are_disabled() {
    let mut state = opening();
    recurring_mut(&mut state).household_purchases[0].enabled = false;
    recurring_mut(&mut state)
        .attendance
        .iter_mut()
        .find(|row| row.site_id == site(3))
        .unwrap()
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
        .unwrap();
    let id = OrderId::from_bytes([90; 32]);
    let (state, _) = admit_material_purchase(
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
    .unwrap();
    let first = advance_material_circuit(&state).unwrap();
    assert_eq!(first.state.final_demand_orders[0].fulfilled, 0);
    assert_eq!(
        economy(&first.state)
            .recurring
            .as_ref()
            .unwrap()
            .attendance
            .iter()
            .find(|row| row.site_id == site(3))
            .unwrap()
            .planned_hours,
        1
    );
    let second = advance_material_circuit(&first.state).unwrap();
    assert_eq!(second.local_fulfillments[0].quantity, 1);
    assert_eq!(second.household_consumption[0].available_quantity, 5);
    assert!(second.state.final_demand_orders.is_empty());
    assert!(economy(&second.state)
        .book
        .purchase(OutboundOrderId::LocalFinalDemand(id))
        .is_err());
}

fn producer_retail_opening() -> MaterialCircuitState {
    let mut state = opening();
    state.merchants.push(MerchantHandling {
        site_id: site(1),
        county_geoid: *b"26163",
        role: MerchantRole::Retail,
        capacity_id: corridor(4),
        labor_unit_id: hours(),
    });
    state
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
    rows.household_needs.push(HouseholdNeed {
        principal_id: household(),
        good_id: good(1),
        unit_id: units(),
        units_per_person: 1,
    });
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
    state
}

#[test]
fn a_shared_production_and_retail_pool_requests_each_kind_of_work_once() {
    let mut state = producer_retail_opening();
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
            StaffingPolicy::one_period(4).unwrap(),
            sources,
        )
        .unwrap()
    })
    .collect::<Vec<_>>();
    let closed = close_material_period(&state).unwrap();
    let requests = closed.staffing_requests(&bindings).unwrap();
    let source = requests
        .iter()
        .filter(|row| row.site_id() == site(1))
        .collect::<Vec<_>>();
    assert_eq!(source.len(), 2);
    assert_eq!(
        source
            .iter()
            .find(|row| row.work_source() == StaffingWorkSource::Production(process(1)))
            .unwrap()
            .hours(),
        4
    );
    assert_eq!(
        source
            .iter()
            .find(|row| row.work_source() == StaffingWorkSource::MerchantHandling(site(1)))
            .unwrap()
            .hours(),
        5
    );
}

#[test]
fn cash_backed_unfilled_retail_demand_can_restart_a_producer_with_no_opening_sales() {
    let mut state = producer_retail_opening();
    state
        .production_commitments
        .retain(|row| row.site_id != site(1));
    let rows = recurring_mut(&mut state);
    rows.production[0].planned_batches = 0;
    rows.attendance
        .iter_mut()
        .find(|row| row.site_id == site(1))
        .unwrap()
        .planned_hours = 0;
    rows.replenishment.clear();
    let closed = advance_material_circuit(&state).unwrap();
    let demand = closed
        .household_demand
        .iter()
        .find(|row| row.good_id == good(1))
        .unwrap();
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
        .unwrap();
    assert_eq!(plan.planned_batches, 1);
    assert!(closed
        .state
        .production_commitments
        .iter()
        .any(|row| row.site_id == site(1) && row.planned_batches == 1));
}

#[test]
fn a_household_purchase_without_a_recipient_stock_is_refused_before_reserving_cash() {
    let mut state = producer_retail_opening();
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
        .unwrap();
    let original = state.clone();
    assert_eq!(
        admit_material_purchase(
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
