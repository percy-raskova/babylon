//! Integrated counterfactual controls: market withdrawal, resident work, and finite trade.
use super::*;
use babylon_kernel::economic_location::{EconomicLocation, ForeignCounterpart};

fn rolling(mut state: MaterialCircuitState) -> MaterialCircuitState {
    state.capacities.retain(|row| row.period == state.period);
    state
        .corridor_capacities
        .retain(|row| row.period == state.period);
    state.capacity_supply = CapacitySupply::Rolling(Box::new(RollingCapacitySupply {
        processes: babylon_material_circuit::RollingProcessSupply::CapturedNameplate(
            state
                .capacities
                .iter()
                .map(|row| InstalledProcessCapacity {
                    process_id: row.process_id,
                    site_id: row.site_id,
                    batches_per_period: row.available_batches,
                })
                .collect(),
        ),
        shared: state
            .corridor_capacities
            .iter()
            .map(|row| SharedCapacitySupply {
                corridor_id: row.corridor_id,
                grams_per_period: row.available_grams,
            })
            .collect(),
        future_reservations: vec![],
    }));
    state
}

fn staffing() -> StaffingState {
    let pools = [(1, 1), (2, 2), (3, 1)]
        .into_iter()
        .map(|(owner, persons)| {
            let source = if owner == 3 {
                StaffingWorkSource::MerchantHandling(site(owner))
            } else {
                StaffingWorkSource::Production(process(owner))
            };
            let binding = StaffingPoolBinding::try_new(
                StaffingPoolId::from_bytes([owner; 32]),
                site(owner),
                hours(),
                persons,
                StaffingPolicy::one_period(4).unwrap(),
                vec![source],
            )
            .unwrap();
            StaffingPoolState::try_new(binding, persons, 0, persons * 4).unwrap()
        })
        .collect();
    StaffingState::try_new(1, pools).unwrap()
}

fn residents() -> Vec<Vec<StaffingMemberState>> {
    [(1, 1), (2, 2), (3, 1)]
        .into_iter()
        .map(|(id, persons)| {
            vec![StaffingMemberState::try_new(
                StaffingMemberBinding::try_new(
                    StaffingMemberId::from_bytes([id; 32]),
                    household(),
                    "county:26163".parse().unwrap(),
                    persons,
                )
                .unwrap(),
                persons,
                0,
            )
            .unwrap()]
        })
        .collect()
}

fn assert_conservation(
    state: &MaterialCircuitState,
    consumed: u64,
    physical_total: u64,
    cash: i128,
) {
    let physical = state.inventory.iter().map(|r| r.quantity).sum::<u64>()
        + state.freight.iter().map(|r| r.quantity).sum::<u64>()
        + economy(state)
            .recurring
            .as_ref()
            .unwrap()
            .household_stocks
            .iter()
            .map(|r| r.quantity)
            .sum::<u64>();
    assert_eq!(physical + consumed, physical_total);
    assert_eq!(
        economy(state).book.total_cash_and_reserves().unwrap(),
        money(cash)
    );
}

fn allocate_resident_work(
    receipts: &[StaffingReceipt],
    members: &mut [Vec<StaffingMemberState>],
    next_period: u64,
) -> (Vec<MemberLaborCapacityRow>, u64, u64) {
    let mut hires = 0;
    let mut separations = 0;
    let mut hours_next = Vec::new();
    for (index, receipt) in receipts.iter().enumerate() {
        let shares = distribute_staffing_members(receipt, &members[index]).unwrap();
        assert_eq!(
            shares.iter().map(|r| r.closing_employed).sum::<u64>(),
            receipt.closing_employed()
        );
        assert_eq!(
            shares.iter().map(|r| r.next_opening_hours).sum::<u64>(),
            receipt.next_opening_hours()
        );
        members[index] = shares
            .iter()
            .map(|r| {
                r.validate().unwrap();
                assert_eq!(
                    r.closing_employed + r.closing_reserve,
                    r.member.labor_force()
                );
                separations += r.separations;
                hires += r.hires;
                hours_next.push(MemberLaborCapacityRow {
                    member_id: r.member.member_id(),
                    period: next_period,
                    available_hours: r.next_opening_hours,
                });
                StaffingMemberState::try_new(
                    r.member.clone(),
                    r.closing_employed,
                    r.closing_reserve,
                )
                .unwrap()
            })
            .collect();
    }
    (hours_next, hires, separations)
}

fn circuit_activity(
    transition: &MaterialCircuitTransition,
    members: &[Vec<StaffingMemberState>],
) -> (u64, u64, u64, u64) {
    let planned = transition
        .production_plans
        .iter()
        .map(|r| r.planned_batches)
        .sum::<u64>();
    let employed = members
        .iter()
        .flatten()
        .map(StaffingMemberState::employed)
        .sum::<u64>();
    let stock = transition
        .state
        .inventory
        .iter()
        .filter(|r| r.good_id == good(2))
        .map(|r| r.quantity)
        .sum::<u64>();
    (
        output(transition, 1) + output(transition, 2),
        planned,
        employed,
        stock,
    )
}

#[test]
fn withdrawal_and_recovery_pass_through_plans_and_conserved_resident_workforce() {
    let mut state = rolling(opening());
    state.labor.retain(|row| row.period == 1);
    if let CircuitAccounting::Monetary(e) = &mut state.accounting {
        e.member_labor.retain(|row| row.period == 1);
    }
    let mut pools = staffing();
    let mut members = residents();
    let mut trajectory = Vec::new();
    let mut separations = 0;
    let mut hires = 0;
    let mut consumed = 0;
    for period in 1..=12 {
        recurring_mut(&mut state).household_purchases[0].enabled = ![3, 4].contains(&period);
        let closed = close_material_period(&state).unwrap();
        let bindings: Vec<_> = pools.pools().iter().map(|p| p.binding().clone()).collect();
        let requests = closed.staffing_requests(&bindings).unwrap();
        let staffing = advance_staffing(&pools, &requests).unwrap();
        let (hours_next, period_hires, period_separations) =
            allocate_resident_work(staffing.receipts(), &mut members, period + 1);
        hires += period_hires;
        separations += period_separations;
        let transition = closed
            .finish_with_workforce(staffing.next_labor().to_vec(), hours_next)
            .unwrap();
        trajectory.push(circuit_activity(&transition, &members));
        consumed += transition
            .household_consumption
            .iter()
            .map(|r| r.consumed_quantity)
            .sum::<u64>();
        assert_conservation(&transition.state, consumed, 56, 24);
        assert_eq!(
            members
                .iter()
                .flatten()
                .map(|r| r.employed() + r.reserve())
                .sum::<u64>(),
            4
        );
        pools = staffing.state().clone();
        state = decode_material_circuit_state(
            &encode_material_circuit_state(&transition.state).unwrap(),
        )
        .unwrap();
    }
    assert!(
        separations > 0 && hires > 0,
        "withdrawal must release work and recovery must rehire: {trajectory:?}"
    );
    assert!(
        trajectory[2..6].iter().any(|r| r.1 < 8 && r.2 < 4),
        "plans and staffing must respond: {trajectory:?}"
    );
    assert!(
        trajectory[6..]
            .iter()
            .any(|r| r.0 == 8 && r.1 == 8 && r.2 == 4),
        "restored demand must restart the circuit: {trajectory:?}"
    );
    assert!(
        trajectory[2..6].iter().any(|r| r.3 > 0),
        "withdrawal leaves unsold stock: {trajectory:?}"
    );
}

fn foreign_trade_opening() -> MaterialCircuitState {
    let mut state = opening();
    state.process_outputs.clear();
    state.input_coefficients.clear();
    state.labor_coefficients.clear();
    state.production_commitments.clear();
    state.capacities.clear();
    // Keep sixteen finite goods: four exports, four imports, and eight retail units.
    state.inventory = vec![inventory(1, 1, 4), inventory(2, 2, 4), inventory(3, 2, 8)];
    recurring_mut(&mut state).household_stocks[0].quantity = 0;
    state.merchants.extend(
        [
            (1, "county:26163".parse().unwrap()),
            (2, EconomicLocation::Foreign(ForeignCounterpart::Canada)),
        ]
        .into_iter()
        .map(|(id, location)| MerchantHandling {
            site_id: site(id),
            location,
            role: MerchantRole::Wholesale,
            capacity_id: corridor(id + 3),
            labor_unit_id: hours(),
        }),
    );
    state
        .handling_coefficients
        .extend(
            [(1, 1), (2, 2)]
                .into_iter()
                .map(|(id, g)| MerchantHandlingCoefficient {
                    site_id: site(id),
                    good_id: good(g),
                    unit_id: units(),
                    hours_per_unit: 1,
                }),
        );
    state.supplier_routes = [(1, 2, 1), (2, 1, 2)]
        .into_iter()
        .map(|(seller, buyer, g)| SupplierRoute {
            supplier_site_id: site(seller),
            buyer_site_id: site(buyer),
            good_id: good(g),
            unit_id: units(),
            route_id: route(seller),
            transport_kind: SupplierTransport::Staged,
        })
        .collect();
    state.route_stages[1].to_node_id = node(1);
    // Warehouse handling and road freight are distinct physical capacity principals.
    state.corridor_capacities.extend((1..=9).flat_map(|period| {
        [4, 5].into_iter().map(move |id| CorridorCapacity {
            corridor_id: corridor(id),
            period,
            available_grams: 4,
        })
    }));
    fund_foreign_trade(&mut state);
    configure_trade_policies(recurring_mut(&mut state));
    state
}

fn fund_foreign_trade(state: &mut MaterialCircuitState) {
    let CircuitAccounting::Monetary(e) = &mut state.accounting else {
        panic!("paid trade")
    };
    e.book = MonetaryBook::open(
        [
            // The retailer pays its first handling shift before household admission.
            (AccountId::Site(site(1)), 96),
            (AccountId::Site(site(2)), 100),
            (AccountId::Site(site(3)), 4),
            (AccountId::Household(household()), 0),
        ]
        .into_iter()
        .map(|(id, cash)| CashAccount {
            id,
            cash: money(cash),
        })
        .collect(),
    )
    .unwrap();
    e.costs = HistoricalCostBook::open(
        &e.book,
        [
            (AccountId::Site(site(1)), 1),
            (AccountId::Site(site(2)), 2),
            (AccountId::Site(site(3)), 2),
            (AccountId::Household(household()), 2),
        ]
        .into_iter()
        .map(|(owner, g)| StockCarryingValue {
            owner,
            good_id: good(g),
            unit_id: units(),
            amount: money(0),
        })
        .collect(),
        vec![],
        vec![],
        vec![],
    )
    .unwrap();
}

fn configure_trade_policies(recurring: &mut RecurringEconomy) {
    recurring.production.clear();
    recurring.offers = [(1, 1), (2, 2), (3, 2)]
        .into_iter()
        .map(|(id, g)| SellerOffer {
            site_id: site(id),
            good_id: good(g),
            unit_id: units(),
            unit_price: money(1),
            pricing: PricePolicy::Fixed,
        })
        .collect();
    recurring.replenishment = [(1, 2, 1), (2, 1, 2)]
        .into_iter()
        .map(|(seller, buyer, g)| ReplenishmentPolicy {
            buyer_site_id: site(buyer),
            supplier_site_id: site(seller),
            good_id: good(g),
            unit_id: units(),
            target_stock: 4,
            maximum_purchase: 2,
            cash_floor: money(0),
        })
        .collect();
}

fn record_trade_settlement(
    state: &MaterialCircuitState,
    transition: &MaterialCircuitTransition,
    delivered: &mut [u64; 2],
    settled: &mut [i128; 2],
) {
    for receipt in &transition.deliveries {
        let order = state
            .orders
            .iter()
            .find(|r| r.order_id == receipt.order_id)
            .unwrap();
        delivered[usize::from(order.supplier_site_id == site(2))] += receipt.quantity;
    }
    for transfer in &transition.money_transfers {
        if let MoneyTransferPurpose::DeliverySettlement(OutboundOrderId::Delivery(id)) =
            transfer.purpose
        {
            let order = state.orders.iter().find(|r| r.order_id == id).unwrap();
            assert_eq!(
                transfer.credit.location,
                MoneyLocation::Cash(AccountId::Site(order.supplier_site_id))
            );
            assert_eq!(
                transfer.debit.location,
                MoneyLocation::PurchaseReserve(OutboundOrderId::Delivery(id))
            );
            assert_eq!(
                transfer.debit.delta.micro_units(),
                -transfer.credit.delta.micro_units()
            );
            settled[usize::from(order.supplier_site_id == site(2))] +=
                transfer.credit.delta.micro_units();
        }
    }
}

#[test]
fn finite_foreign_imports_and_exports_settle_only_after_bidirectional_delivery() {
    let mut state = foreign_trade_opening();
    let mut delivered = [0_u64; 2];
    let mut settled = [0_i128; 2];
    let mut active_periods = 0;
    let mut purchase_periods = 0;
    let mut purchased = 0;
    let mut consumed = 0;
    for period in 1..=8 {
        let transition = advance_material_circuit(&state).unwrap();
        if !transition.dispatches.is_empty() {
            active_periods += 1;
        }
        if period == 1 {
            assert!(transition.deliveries.is_empty());
            assert!(transition.realizations.is_empty());
            assert!(!transition.state.freight.is_empty());
        }
        let delivered_before = delivered;
        let settled_before = settled;
        record_trade_settlement(&state, &transition, &mut delivered, &mut settled);
        for direction in 0..2 {
            assert_eq!(
                settled[direction] - settled_before[direction],
                i128::from(delivered[direction] - delivered_before[direction])
            );
        }
        let period_purchases = transition
            .household_demand
            .iter()
            .map(|r| r.fulfilled_quantity)
            .sum::<u64>();
        if period_purchases > 0 {
            purchase_periods += 1;
        }
        purchased += period_purchases;
        let retailer_work = transition
            .member_labor_use
            .iter()
            .find(|r| r.site_id == site(3))
            .unwrap();
        retailer_work.validate().unwrap();
        assert_eq!(retailer_work.handling_hours, period_purchases);
        assert_eq!(
            retailer_work.handling_wages,
            money(i128::from(period_purchases))
        );
        consumed += transition
            .household_consumption
            .iter()
            .map(|r| r.consumed_quantity)
            .sum::<u64>();
        assert_conservation(&transition.state, consumed, 16, 200);
        assert!(transition.production.is_empty());
        assert!(transition.local_transfers.is_empty());
        state = decode_material_circuit_state(
            &encode_material_circuit_state(&transition.state).unwrap(),
        )
        .unwrap();
    }
    assert!(active_periods >= 2);
    assert!(purchase_periods >= 2);
    assert_eq!(purchased, 8);
    assert_eq!(consumed, 8);
    assert_eq!(delivered, [4, 4]);
    assert_eq!(settled, [4, 4]);
    assert!(state.freight.is_empty());
    assert_eq!(
        state
            .inventory
            .iter()
            .filter(|r| r.site_id == site(1) && r.good_id == good(2))
            .map(|r| r.quantity)
            .sum::<u64>(),
        4
    );
    assert_eq!(
        state
            .inventory
            .iter()
            .filter(|r| r.site_id == site(2) && r.good_id == good(1))
            .map(|r| r.quantity)
            .sum::<u64>(),
        4
    );
}
