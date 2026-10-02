use babylon_kernel::{content_digest::sha256_of, currency::Currency};
use babylon_material_circuit::*;

fn money(value: i128) -> Currency {
    Currency::from_micro_units(value)
}

fn paid_state() -> MaterialCircuitState {
    let seller = SiteId::from_bytes([1; 32]);
    let buyer = SiteId::from_bytes([2; 32]);
    let household = FinalDemandPrincipalId::from_bytes([3; 32]);
    let good = GoodId::from_bytes([4; 32]);
    let unit = UnitId::from_bytes([5; 32]);
    let hours = UnitId::from_bytes([6; 32]);
    let mut book = MonetaryBook::open(vec![
        CashAccount {
            id: AccountId::Site(seller),
            cash: money(1_i128 << 100),
        },
        CashAccount {
            id: AccountId::Site(buyer),
            cash: money(1_i128 << 100),
        },
        CashAccount {
            id: AccountId::Household(household),
            cash: money((1_i128 << 90) + 3),
        },
        CashAccount {
            id: AccountId::Organization(OrganizationAccountId::from_bytes([1; 32])),
            cash: money(7),
        },
        CashAccount {
            id: AccountId::Public(PublicAccountId::from_bytes([1; 32])),
            cash: money(11),
        },
    ])
    .unwrap();
    let orders: Vec<_> = [10, 11]
        .into_iter()
        .map(|id| OrderRow {
            order_id: OrderId::from_bytes([id; 32]),
            access_mode: OrderAccessMode::CommoditySale,
            buyer_site_id: buyer,
            supplier_site_id: seller,
            good_id: good,
            unit_id: unit,
            ordered: 4,
            shipped: 0,
            lost: 0,
            delivered: 0,
            realized: 0,
        })
        .collect();
    for order in &orders {
        book.reserve_purchase(
            PurchaseEscrow::new(
                OutboundOrderId::Delivery(order.order_id),
                AccountId::Site(buyer),
                AccountId::Site(seller),
                order.ordered,
                money((1_i128 << 80) + 5),
            )
            .unwrap(),
        )
        .unwrap();
    }
    for id in [12, 13] {
        let shift = ShiftId::from_bytes([id; 32]);
        book.reserve_shift(
            FundedShift::new(
                shift,
                AccountId::Site(seller),
                AccountId::Household(household),
                1,
                4,
                money((1_i128 << 65) + 7),
            )
            .unwrap(),
        )
        .unwrap();
        book.accrue_shift(shift).unwrap();
    }
    MaterialCircuitState {
        capacity_supply: babylon_material_circuit::CapacitySupply::FiniteSchedule,
        period: 3,
        accounting: CircuitAccounting::Monetary(Box::new({
            let book = book;
            MonetaryCircuit {
                financial: {
                    let mut financial = FinancialInstitutions::empty();
                    financial.locations = vec![
                        InstitutionLocation {
                            account: AccountId::Organization(OrganizationAccountId::from_bytes(
                                [1; 32],
                            )),
                            location: "county:26163".parse().unwrap(),
                        },
                        InstitutionLocation {
                            account: AccountId::Public(PublicAccountId::from_bytes([1; 32])),
                            location: "county:26163".parse().unwrap(),
                        },
                    ];
                    financial
                },
                member_labor: [3, 4]
                    .into_iter()
                    .flat_map(|period| {
                        [seller, buyer]
                            .into_iter()
                            .map(move |site| (site, period, 0))
                    })
                    .map(|(site, period, available_hours)| {
                        babylon_material_circuit::MemberLaborCapacityRow {
                            member_id: babylon_material_circuit::StaffingMemberId::from_bytes(
                                site.as_bytes(),
                            ),
                            period,
                            available_hours,
                        }
                    })
                    .collect(),
                costs: HistoricalCostBook::open(
                    &book,
                    vec![StockCarryingValue {
                        owner: AccountId::Site(seller),
                        good_id: good,
                        unit_id: unit,
                        amount: money(0),
                    }],
                    vec![],
                    vec![],
                    vec![],
                )
                .unwrap(),
                book,
                recurring: None,
                employment: [seller, buyer]
                    .into_iter()
                    .map(|site_id| EmploymentTerms {
                        member_id: babylon_material_circuit::StaffingMemberId::from_bytes(
                            (site_id).as_bytes(),
                        ),
                        site_id,
                        unit_id: hours,
                        payee: household,
                        compensation: babylon_material_circuit::LaborCompensation::Wage(money(
                            (1_i128 << 65) + 7,
                        )),
                    })
                    .collect(),
            }
        })),
        site_logistics_nodes: [seller, buyer]
            .into_iter()
            .enumerate()
            .map(|(index, site_id)| SiteLogisticsNode {
                site_id,
                node_id: LogisticsNodeId::from_bytes([u8::try_from(index + 1).unwrap(); 32]),
            })
            .collect(),
        process_outputs: vec![],
        input_coefficients: vec![],
        labor_coefficients: vec![],
        service_connections: vec![],
        service_orders: vec![],
        commodities: vec![CommodityDefinition {
            good_id: good,
            unit_id: unit,
            kind: babylon_material_circuit::CommodityKind::Storable { grams_per_unit: 1 },
        }],
        supplier_routes: vec![SupplierRoute {
            buyer_site_id: buyer,
            supplier_site_id: seller,
            good_id: good,
            unit_id: unit,
            route_id: RouteId::from_bytes([7; 32]),
            transport_kind: SupplierTransport::Local,
        }],
        route_stages: vec![],
        route_stage_capacities: vec![],
        inventory: vec![InventoryRow {
            site_id: seller,
            good_id: good,
            unit_id: unit,
            quantity: 10,
        }],
        backlog: orders
            .iter()
            .map(|row| BacklogRow {
                order_id: row.order_id,
                quantity: row.ordered,
            })
            .collect(),
        orders,
        freight: vec![],
        corridor_capacities: vec![],
        capacities: vec![],
        labor: [3, 4]
            .into_iter()
            .flat_map(|period| {
                [seller, buyer]
                    .into_iter()
                    .map(move |site_id| LaborCapacityRow {
                        site_id,
                        unit_id: hours,
                        period,
                        available: 0,
                    })
            })
            .collect(),
        production_commitments: vec![],
        merchants: vec![],
        handling_coefficients: vec![],
        final_demand_principals: vec![FinalDemandPrincipal {
            id: household,
            location: "county:26163".parse().unwrap(),
        }],
        final_demand_orders: vec![],
        maintenance_binding: None,
        maintenance_service: None,
    }
}

fn accounting_offset(state: &MaterialCircuitState) -> usize {
    let mut control = state.clone();
    control.accounting = CircuitAccounting::PhysicalControl;
    // One accounting tag, one finite-capacity tag, and two empty service row counts.
    encode_material_circuit_state(&control).unwrap().len() - 10
}

// Language-neutral current monetary row widths, independent of Rust struct layout.
const ACCOUNT_BYTES: usize = 1 + 32 + 16;
const PURCHASE_BYTES: usize = 1 + 32 + 2 * (1 + 32) + 8 + 16 + 8 + 8;
const SHIFT_BYTES: usize = 32 + 2 * (1 + 32) + 8 + 8 + 16 + 1;
const EMPLOYMENT_BYTES: usize = 4 * 32 + 1 + 16;
const MEMBER_LABOR_BYTES: usize = 32 + 8 + 8;

#[test]
fn exact_i128_accounts_escrow_and_unpaid_wages_survive_restart() {
    let state = paid_state();
    let bytes = encode_material_circuit_state(&state).unwrap();
    let restored = decode_material_circuit_state(&bytes).unwrap();
    assert_eq!(restored, state);
    assert_eq!(encode_material_circuit_state(&restored).unwrap(), bytes);
    assert_eq!(
        material_circuit_state_digest(&restored).unwrap(),
        sha256_of(&bytes)
    );
    assert_eq!(
        advance_material_circuit(&restored).unwrap(),
        advance_material_circuit(&state).unwrap()
    );
    let CircuitAccounting::Monetary(economy) = &restored.accounting else {
        panic!("lost monetary mode");
    };
    assert_eq!(economy.book.snapshot().shifts.len(), 2);
    assert_eq!(economy.book.snapshot().purchases.len(), 2);
    assert_eq!(
        economy.employment[0].compensation.wage_rate().micro_units(),
        (1_i128 << 65) + 7
    );
    let offset = accounting_offset(&state);
    assert_eq!(bytes[offset], 1);
    assert_eq!(&bytes[offset + 1..offset + 5], &5_u32.to_be_bytes());
    assert_eq!(
        &bytes[offset + 5 + 33..offset + 5 + ACCOUNT_BYTES],
        &economy
            .book
            .cash(AccountId::Site(SiteId::from_bytes([1; 32])))
            .unwrap()
            .micro_units()
            .to_be_bytes()
    );
}

#[test]
fn all_monetary_row_families_reject_noncanonical_wire_order() {
    let state = paid_state();
    let bytes = encode_material_circuit_state(&state).unwrap();
    let accounts = accounting_offset(&state) + 1 + 4;
    let purchases = accounts + 5 * ACCOUNT_BYTES + 4;
    let shifts = purchases + 2 * PURCHASE_BYTES + 4;
    let employment = shifts + 2 * SHIFT_BYTES + 4;
    for (start, width) in [
        (accounts, ACCOUNT_BYTES),
        (purchases, PURCHASE_BYTES),
        (shifts, SHIFT_BYTES),
        (employment, EMPLOYMENT_BYTES),
        (employment + 2 * EMPLOYMENT_BYTES + 4, MEMBER_LABOR_BYTES),
    ] {
        let mut reversed = bytes.clone();
        reversed[start..start + 2 * width].rotate_left(width);
        assert_eq!(
            decode_material_circuit_state(&reversed),
            Err(MaterialCircuitError::WireNoncanonical)
        );
    }
}

#[test]
fn monetary_tags_counts_and_invalid_currency_are_refused() {
    let state = paid_state();
    let bytes = encode_material_circuit_state(&state).unwrap();
    let accounting = accounting_offset(&state);
    let accounts = accounting + 1 + 4;
    let purchases = accounts + 5 * ACCOUNT_BYTES + 4;
    let shifts = purchases + 2 * PURCHASE_BYTES + 4;
    for offset in [accounting, accounts, purchases, shifts + SHIFT_BYTES - 1] {
        let mut invalid = bytes.clone();
        invalid[offset] = 255;
        assert_eq!(
            decode_material_circuit_state(&invalid),
            Err(MaterialCircuitError::WireEnum)
        );
    }
    for (count_offset, excess) in [
        (accounting + 1, 131_073_u32),
        (purchases - 4, 65_537),
        (shifts - 4, 65_537),
        (shifts + 2 * SHIFT_BYTES, 131_073),
        (shifts + 2 * SHIFT_BYTES + 4 + 2 * EMPLOYMENT_BYTES, 131_073),
    ] {
        let mut excessive = bytes.clone();
        excessive[count_offset..count_offset + 4].copy_from_slice(&excess.to_be_bytes());
        assert_eq!(
            decode_material_circuit_state(&excessive),
            Err(MaterialCircuitError::WireLimit)
        );
    }
    let mut negative = bytes.clone();
    negative[accounts + 33..accounts + ACCOUNT_BYTES].copy_from_slice(&(-1_i128).to_be_bytes());
    assert_eq!(
        decode_material_circuit_state(&negative),
        Err(MaterialCircuitError::MonetaryInvariant)
    );
    let mut free = bytes.clone();
    let purchase_price = purchases + 33 + 66 + 8;
    free[purchase_price..purchase_price + 16].copy_from_slice(&0_i128.to_be_bytes());
    assert_eq!(
        decode_material_circuit_state(&free),
        Err(MaterialCircuitError::MonetaryInvariant)
    );
}

#[test]
fn old_schema_missing_accounting_truncation_and_trailing_bytes_are_refused() {
    let state = paid_state();
    let bytes = encode_material_circuit_state(&state).unwrap();
    let mut old_schema = bytes.clone();
    let version = MATERIAL_CIRCUIT_STATE_DOMAIN_BYTES.len() + 1;
    old_schema[version..version + 2].copy_from_slice(&4_u16.to_be_bytes());
    assert_eq!(
        decode_material_circuit_state(&old_schema),
        Err(MaterialCircuitError::WireVersion)
    );
    for end in [
        accounting_offset(&state),
        accounting_offset(&state) + 1 + 4 + 40,
        bytes.len() - 1,
    ] {
        assert_eq!(
            decode_material_circuit_state(&bytes[..end]),
            Err(MaterialCircuitError::WireTruncated)
        );
    }
    let mut trailing = bytes;
    trailing.push(0);
    assert_eq!(
        decode_material_circuit_state(&trailing),
        Err(MaterialCircuitError::WireTrailing)
    );
    let mut control = state;
    control.accounting = CircuitAccounting::PhysicalControl;
    let bytes = encode_material_circuit_state(&control).unwrap();
    assert_eq!(bytes.last(), Some(&0));
    assert_eq!(decode_material_circuit_state(&bytes).unwrap(), control);
}

#[test]
fn physical_binding_and_employment_remain_required_after_decoding() {
    let state = paid_state();
    let bytes = encode_material_circuit_state(&state).unwrap();
    let purchases = accounting_offset(&state) + 1 + 4 + 5 * ACCOUNT_BYTES + 4;
    let shifts = purchases + 2 * PURCHASE_BYTES + 4;
    let mut quantity = bytes.clone();
    let principal_quantity = purchases + 33 + 66;
    quantity[principal_quantity..principal_quantity + 8].copy_from_slice(&5_u64.to_be_bytes());
    assert_eq!(
        decode_material_circuit_state(&quantity),
        Err(MaterialCircuitError::PurchaseInvariant)
    );
    let mut unearned = bytes.clone();
    unearned[shifts + SHIFT_BYTES - 1] = 1;
    assert_eq!(
        decode_material_circuit_state(&unearned),
        Err(MaterialCircuitError::PayrollInvariant)
    );
    let employment = shifts + 2 * SHIFT_BYTES + 4;
    let mut zero_wage = bytes;
    zero_wage[employment + 129..employment + EMPLOYMENT_BYTES]
        .copy_from_slice(&0_i128.to_be_bytes());
    assert_eq!(
        decode_material_circuit_state(&zero_wage),
        Err(MaterialCircuitError::WireEnum)
    );
}

#[test]
fn historical_cost_opening_accrued_wages_are_assets_and_liabilities_without_repeat_income() {
    let state = paid_state();
    let bytes = encode_material_circuit_state(&state).unwrap();
    let restored = decode_material_circuit_state(&bytes).unwrap();
    let result = advance_material_circuit(&restored).unwrap();
    let household = AccountId::Household(FinalDemandPrincipalId::from_bytes([3; 32]));
    let row = result
        .income
        .iter()
        .find(|r| r.account == household)
        .unwrap();
    let owed = 2 * 4 * ((1_i128 << 65) + 7);
    assert_eq!(row.opening_capital, money((1_i128 << 90) + 3 + owed));
    assert_eq!(row.statement.wage_income, money(0));
    assert_eq!(row.net_income, money(0));
    let CircuitAccounting::Monetary(economy) = &result.state.accounting else {
        panic!("paid control");
    };
    assert!(economy.book.snapshot().shifts.is_empty());
    assert_eq!(economy.book.cash(household).unwrap(), row.opening_capital);
}
