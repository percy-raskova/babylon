//! Real close controls for gift ownership, scarce work and delayed household food.
use super::*;

fn recipient() -> FinalDemandPrincipalId {
    FinalDemandPrincipalId::from_bytes([76; 32])
}
fn aid_opening(routed: bool) -> MaterialCircuitState {
    let mut state = opening();
    state.final_demand_principals.push(FinalDemandPrincipal {
        id: recipient(),
        location: state.final_demand_principals[0].location,
    });
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        panic!("monetary control");
    };
    let rows = economy.recurring.as_mut().unwrap();
    rows.household_purchases[0].enabled = false;
    rows.households.push(HouseholdCohort {
        principal_id: recipient(),
        kind: HouseholdKind::Ordinary,
        households: 1,
        persons: 1,
    });
    rows.household_stocks.push(HouseholdStock {
        principal_id: recipient(),
        good_id: good(2),
        unit_id: units(),
        quantity: 0,
    });
    rows.household_needs.push(HouseholdNeed {
        principal_id: recipient(),
        good_id: good(2),
        unit_id: units(),
        basis: HouseholdNeedBasis::Persons,
        units_per_basis: 1,
    });
    let mut recipient_purchase = rows.household_purchases[0].clone();
    recipient_purchase.principal_id = recipient();
    recipient_purchase.enabled = false;
    rows.household_purchases.push(recipient_purchase);
    let mut cash = economy.book.snapshot();
    cash.accounts.push(CashAccount {
        id: AccountId::Household(recipient()),
        cash: money(0),
    });
    economy.book = MonetaryBook::from_snapshot(cash).unwrap();
    let mut stocks = economy.costs.snapshot().stocks;
    stocks.push(StockCarryingValue {
        owner: AccountId::Household(recipient()),
        good_id: good(2),
        unit_id: units(),
        amount: money(0),
    });
    economy.costs =
        HistoricalCostBook::open(&economy.book, stocks, vec![], vec![], vec![]).unwrap();
    economy.household_time = HouseholdTimeAccounting::Modeled(
        HouseholdTimeBook::new(
            [household(), recipient()]
                .into_iter()
                .map(|principal_id| HouseholdTimePolicy {
                    principal_id,
                    labor_unit_id: hours(),
                    eligible_persons: if principal_id == household() { 4 } else { 1 },
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
                        unit_id: units(),
                        hours_per_unmet_unit: 5,
                    }],
                })
                .collect(),
        )
        .unwrap(),
    );
    economy.aid = AidBook {
        mandates: vec![mandate(routed)],
        freight: vec![],
    };
    state
}
fn input(quantity: u64) -> AidResolveInput {
    AidResolveInput {
        mandate_id: [91; 32],
        source_hash: [92; 32],
        admitted_period: 0,
        donor_actor: 10,
        recipient_actor: 20,
        quantity,
    }
}
fn close_aid(
    state: &MaterialCircuitState,
    inputs: &[AidResolveInput],
) -> Result<MaterialCircuitTransition, MaterialCircuitError> {
    advance_material_circuit_with_aid(state, inputs)
}
fn consumed(
    rows: &MaterialCircuitTransition,
    principal: FinalDemandPrincipalId,
) -> &HouseholdConsumptionReceipt {
    rows.household_consumption
        .iter()
        .find(|r| r.principal_id == principal)
        .unwrap()
}

#[test]
fn local_gift_conserves_cash_and_basis_without_a_sale_and_debits_actual_time() {
    let state = aid_opening(false);
    let before = encode_material_circuit_state(&state).unwrap();
    let ordinary = close_aid(&state, &[]).unwrap();
    let gifted = close_aid(&state, &[input(2)]).unwrap();
    assert_eq!(encode_material_circuit_state(&state).unwrap(), before);
    assert_eq!(consumed(&ordinary, recipient()).consumed_quantity, 0);
    assert_eq!(consumed(&gifted, recipient()).consumed_quantity, 1);
    assert_eq!(consumed(&gifted, household()).consumed_quantity, 4);
    let grant = gifted
        .aid
        .iter()
        .find(|r| r.outcome == AidOutcome::Granted)
        .unwrap();
    assert_eq!(
        (
            grant.quantity,
            grant.carrying_amount,
            grant.cash_amount,
            grant.contribution_hours
        ),
        (2, money(8), money(6), 4)
    );
    assert_eq!(
        economy(&gifted.state)
            .book
            .total_cash_and_reserves()
            .unwrap(),
        economy(&state).book.total_cash_and_reserves().unwrap()
    );
    assert_eq!(
        economy(&gifted.state)
            .book
            .cash(AccountId::Household(recipient()))
            .unwrap(),
        money(6)
    );
    let donor = gifted
        .income
        .iter()
        .find(|r| r.account == AccountId::Household(household()))
        .unwrap();
    let receiver = gifted
        .income
        .iter()
        .find(|r| r.account == AccountId::Household(recipient()))
        .unwrap();
    assert_eq!(donor.statement.gift_expense, money(14));
    assert_eq!(receiver.statement.gift_income, money(14));
    assert_eq!(receiver.statement.sales, money(0));
    assert_eq!(receiver.statement.public_transfer_income, money(0));
    assert!(economy(&gifted.state).book.snapshot().aid.is_empty());
    let HouseholdTimeAccounting::Modeled(time) = &economy(&gifted.state).household_time else {
        panic!("modeled");
    };
    assert_eq!(time.contributions[0].contribution.hours, 4);
    let restarted =
        decode_material_circuit_state(&encode_material_circuit_state(&gifted.state).unwrap())
            .unwrap();
    assert_eq!(restarted, gifted.state);
    assert_eq!(
        close_aid(
            &decode_material_circuit_state(&before).unwrap(),
            &[input(2)]
        )
        .unwrap(),
        gifted
    );
}

#[test]
fn routed_gift_shares_commercial_capacity_and_grants_only_after_actual_arrival() {
    let mut state = aid_opening(true);
    let total = economy(&state).book.total_cash_and_reserves().unwrap();
    let CircuitAccounting::Monetary(accounts) = &mut state.accounting else {
        panic!("monetary");
    };
    let mut cash = accounts.book.snapshot();
    // Both workplaces still fund their full payroll. The retailer then has six
    // spendable units and can reserve two real purchases at the supplier quote.
    cash.accounts
        .iter_mut()
        .find(|a| a.id == AccountId::Site(site(2)))
        .unwrap()
        .cash = money(10);
    cash.accounts
        .iter_mut()
        .find(|a| a.id == AccountId::Site(site(3)))
        .unwrap()
        .cash = money(10);
    accounts.book = MonetaryBook::from_snapshot(cash).unwrap();
    accounts.costs = HistoricalCostBook::open(
        &accounts.book,
        accounts.costs.snapshot().stocks,
        vec![],
        vec![],
        vec![],
    )
    .unwrap();
    assert_eq!(accounts.book.total_cash_and_reserves().unwrap(), total);
    recurring_mut(&mut state)
        .replenishment
        .iter_mut()
        .find(|r| r.buyer_site_id == site(3))
        .unwrap()
        .target_stock = 6;
    state
        .corridor_capacities
        .iter_mut()
        .filter(|r| r.corridor_id == corridor(2))
        .for_each(|r| r.available_grams = 2);
    let first = close_aid(&state, &[input(2)]).unwrap();
    assert_eq!(consumed(&first, recipient()).consumed_quantity, 0);
    assert!(!first.dispatches.is_empty());
    let commercial = first
        .procurement
        .iter()
        .find(|r| r.buyer_site_id == site(3))
        .unwrap();
    assert_eq!(
        (
            commercial.desired_quantity,
            commercial.admitted_quantity,
            commercial.unit_price
        ),
        (2, 2, money(3))
    );
    assert_eq!(
        first
            .member_labor_use
            .iter()
            .map(|r| r.attended_hours)
            .sum::<u64>(),
        16
    );
    assert_eq!(
        economy(&first.state)
            .book
            .total_cash_and_reserves()
            .unwrap(),
        total
    );
    let dispatch = first
        .aid
        .iter()
        .find(|r| r.outcome == AidOutcome::Dispatched)
        .unwrap();
    assert_eq!(dispatch.quantity, 1);
    assert_eq!(
        first
            .dispatches
            .iter()
            .filter(|r| r.route_id == route(2))
            .map(|r| r.quantity)
            .sum::<u64>(),
        1
    );
    assert_eq!(dispatch.contribution_hours, 2);
    let account = economy(&first.state)
        .book
        .aid_reserve(dispatch.commitment_id)
        .unwrap();
    assert_eq!(account.reserved_amount().unwrap(), money(3));
    assert_eq!(account.refunded, 1);
    assert_eq!(
        economy(&first.state)
            .book
            .cash(AccountId::Household(recipient()))
            .unwrap(),
        money(0)
    );
    let restored =
        decode_material_circuit_state(&encode_material_circuit_state(&first.state).unwrap())
            .unwrap();
    let second = close_aid(&restored, &[]).unwrap();
    assert_eq!(consumed(&second, recipient()).consumed_quantity, 1);
    assert_eq!(
        economy(&second.state)
            .book
            .cash(AccountId::Household(recipient()))
            .unwrap(),
        money(3)
    );
    assert!(economy(&second.state).aid.freight.is_empty());
    assert!(economy(&second.state).book.snapshot().aid.is_empty());
    assert!(second
        .aid
        .iter()
        .any(|r| r.outcome == AidOutcome::Granted && r.quantity == 1 && r.contribution_hours == 0));
}

#[test]
fn physical_loss_refunds_donor_cash_and_never_grants_phantom_food() {
    let mut state = aid_opening(true);
    state
        .route_stages
        .iter_mut()
        .find(|r| r.route_id == route(2))
        .unwrap()
        .loss_ppm = 1_000_000;
    let first = close_aid(&state, &[input(2)]).unwrap();
    let second = close_aid(&first.state, &[]).unwrap();
    assert_eq!(consumed(&second, recipient()).consumed_quantity, 0);
    assert_eq!(
        economy(&second.state)
            .book
            .cash(AccountId::Household(recipient()))
            .unwrap(),
        money(0)
    );
    assert!(second.aid.iter().any(|r| r.outcome == AidOutcome::Lost));
    assert!(second
        .money_transfers
        .iter()
        .any(|r| matches!(r.purpose, MoneyTransferPurpose::AidRefund(_))));
    assert!(economy(&second.state).book.snapshot().aid.is_empty());
}

#[test]
fn scarce_donor_time_protects_own_food_and_shared_actor_aliases_cannot_double_spend() {
    let mut state = aid_opening(false);
    let CircuitAccounting::Monetary(accounts) = &mut state.accounting else {
        panic!("monetary");
    };
    let mut second = accounts.aid.mandates[0].clone();
    second.id = [93; 32];
    second.donor_actor = 11;
    accounts.aid.mandates.push(second);
    let mut alias = input(2);
    alias.mandate_id = [93; 32];
    alias.donor_actor = 11;
    let result = close_aid(&state, &[input(2), alias]).unwrap();
    assert_eq!(consumed(&result, household()).consumed_quantity, 4);
    assert_eq!(
        result
            .aid
            .iter()
            .filter(|r| r.outcome == AidOutcome::Granted)
            .map(|r| r.quantity)
            .sum::<u64>(),
        2
    );
    assert_eq!(
        result
            .aid_contributions
            .iter()
            .map(|r| r.hours)
            .sum::<u64>(),
        4
    );
    assert_eq!(
        economy(&result.state)
            .book
            .cash(AccountId::Household(recipient()))
            .unwrap(),
        money(6)
    );
}

#[test]
fn stale_changed_duplicate_and_uncaptured_aid_refuse_atomically() {
    let state = aid_opening(false);
    let before = encode_material_circuit_state(&state).unwrap();
    let mut stale = input(2);
    stale.admitted_period = 1;
    assert_eq!(
        close_aid(&state, &[stale]),
        Err(MaterialCircuitError::PeriodInvariant)
    );
    let mut changed = input(2);
    changed.source_hash = [94; 32];
    assert_eq!(
        close_aid(&state, &[changed]),
        Err(MaterialCircuitError::AidAuthority)
    );
    assert_eq!(
        close_aid(&state, &[input(2), input(2)]),
        Err(MaterialCircuitError::AidAuthority)
    );
    let mut absent = input(2);
    absent.mandate_id = [95; 32];
    assert_eq!(
        close_aid(&state, &[absent]),
        Err(MaterialCircuitError::AidAuthority)
    );
    assert_eq!(encode_material_circuit_state(&state).unwrap(), before);
}

#[test]
fn real_organization_funds_pay_gift_cash_while_household_goods_keep_their_owner() {
    let mut state = aid_opening(false);
    let total = economy(&state).book.total_cash_and_reserves().unwrap();
    let payer = AccountId::Organization(OrganizationAccountId::from_bytes([96; 32]));
    let CircuitAccounting::Monetary(accounts) = &mut state.accounting else {
        panic!("monetary");
    };
    let mut snapshot = accounts.book.snapshot();
    snapshot
        .accounts
        .iter_mut()
        .find(|a| a.id == AccountId::Site(site(3)))
        .unwrap()
        .cash = money(2);
    snapshot
        .accounts
        .iter_mut()
        .find(|a| a.id == AccountId::Household(household()))
        .unwrap()
        .cash = money(6);
    snapshot.accounts.push(CashAccount {
        id: payer,
        cash: money(0),
    });
    accounts.book = MonetaryBook::from_snapshot(snapshot).unwrap();
    accounts
        .book
        .transfer_cash(
            AccountId::Household(household()),
            payer,
            money(6),
            CashTransferPurpose::MutualAid,
        )
        .unwrap();
    accounts.aid.mandates[0].payer = payer;
    accounts.costs = HistoricalCostBook::open(
        &accounts.book,
        accounts.costs.snapshot().stocks,
        vec![],
        vec![],
        vec![],
    )
    .unwrap();
    assert_eq!(accounts.book.total_cash_and_reserves().unwrap(), total);
    // A cash namespace alone is not authenticated institution geography.
    assert_eq!(
        close_aid(&state, &[input(2)]),
        Err(MaterialCircuitError::FinancialInvariant)
    );
    let location = state
        .final_demand_principals
        .iter()
        .find(|p| p.id == household())
        .unwrap()
        .location;
    let CircuitAccounting::Monetary(accounts) = &mut state.accounting else {
        panic!("monetary");
    };
    accounts.financial.locations.push(InstitutionLocation {
        account: payer,
        location,
    });
    let donor_account = AccountId::Household(household());
    let after_funding = economy(&state).book.cash(donor_account).unwrap();
    assert_eq!(after_funding, money(0));
    let result = close_aid(&state, &[input(2)]).unwrap();
    let donor_postings = result
        .money_transfers
        .iter()
        .flat_map(|row| [&row.debit, &row.credit]);
    let closing_cash = donor_postings
        .filter(|posting| posting.location == MoneyLocation::Cash(donor_account))
        .try_fold(after_funding.micro_units(), |cash, posting| {
            cash.checked_add(posting.delta.micro_units())
        })
        .unwrap();
    let paid_wages = result
        .money_transfers
        .iter()
        .filter(|row| matches!(row.purpose, MoneyTransferPurpose::WagePayment(_)))
        .filter(|row| row.credit.location == MoneyLocation::Cash(donor_account))
        .try_fold(0_i128, |paid, row| {
            paid.checked_add(row.credit.delta.micro_units())
        })
        .unwrap();
    // Site 3 has only two cash units after the conserved opening redistribution.
    // Actual payroll is 4 + 8 + 2; unfunded attendance cannot mint the other two.
    assert_eq!(paid_wages, money(14).micro_units());
    assert_eq!(closing_cash, after_funding.micro_units() + paid_wages);
    assert!(result
        .money_transfers
        .iter()
        .filter(|row| matches!(
            row.purpose,
            MoneyTransferPurpose::AidReservation(_)
                | MoneyTransferPurpose::AidGrant(_)
                | MoneyTransferPurpose::AidRefund(_)
        ))
        .flat_map(|row| [&row.debit, &row.credit])
        .all(|posting| posting.location != MoneyLocation::Cash(donor_account)));
    assert_eq!(economy(&result.state).book.cash(payer).unwrap(), money(0));
    assert_eq!(
        economy(&result.state)
            .book
            .cash(AccountId::Household(household()))
            .unwrap(),
        Currency::from_micro_units(closing_cash)
    );
    assert_eq!(
        economy(&result.state)
            .book
            .cash(AccountId::Household(recipient()))
            .unwrap(),
        money(6)
    );
    let organization = result.income.iter().find(|r| r.account == payer).unwrap();
    let donor = result
        .income
        .iter()
        .find(|r| r.account == AccountId::Household(household()))
        .unwrap();
    assert_eq!(organization.statement.gift_expense, money(6));
    assert_eq!(donor.statement.gift_expense, money(8));
    assert!(result.aid.iter().all(|r| r.payer == payer));
    assert_eq!(
        economy(&result.state)
            .book
            .total_cash_and_reserves()
            .unwrap(),
        total
    );
}

fn mandate(routed: bool) -> AidMandate {
    AidMandate {
        id: [91; 32],
        source_hash: [92; 32],
        donor_actor: 10,
        donor_contributor_id: 100,
        recipient_actor: 20,
        payer: AccountId::Household(household()),
        donor: household(),
        recipient: recipient(),
        good_id: good(2),
        unit_id: units(),
        labor_unit_id: hours(),
        hours_per_unit: 2,
        maximum_quantity: 4,
        cash_per_unit: money(3),
        transport: if routed {
            AidTransport::Routed {
                route_id: route(2),
                from_node_id: node(2),
                to_node_id: node(3),
            }
        } else {
            AidTransport::Local
        },
    }
}

#[test]
fn serialized_pending_gift_refuses_invented_arrival_cash_owner_and_principal() {
    let first = close_aid(&aid_opening(true), &[input(2)]).unwrap();
    let before = encode_material_circuit_state(&first.state).unwrap();
    let mut wrong_arrival = first.state.clone();
    let CircuitAccounting::Monetary(accounts) = &mut wrong_arrival.accounting else {
        panic!("monetary");
    };
    accounts.aid.freight[0].stage_arrival_period += 1;
    assert_eq!(
        encode_material_circuit_state(&wrong_arrival),
        Err(MaterialCircuitError::AidInvariant)
    );
    let mut wrong_owner = first.state.clone();
    let CircuitAccounting::Monetary(accounts) = &mut wrong_owner.accounting else {
        panic!("monetary");
    };
    let mut snapshot = accounts.book.snapshot();
    snapshot.aid[0].payer = AccountId::Site(site(1));
    accounts.book = MonetaryBook::from_snapshot(snapshot).unwrap();
    assert_eq!(
        encode_material_circuit_state(&wrong_owner),
        Err(MaterialCircuitError::AidInvariant)
    );
    let mut wrong_principal = first.state.clone();
    let CircuitAccounting::Monetary(accounts) = &mut wrong_principal.accounting else {
        panic!("monetary");
    };
    accounts.aid.freight[0].commitment_id = OrderId::from_bytes([97; 32]);
    assert_eq!(
        encode_material_circuit_state(&wrong_principal),
        Err(MaterialCircuitError::AidInvariant)
    );
    assert_eq!(decode_material_circuit_state(&before).unwrap(), first.state);
    let mut trailing = before;
    trailing.push(0);
    assert!(decode_material_circuit_state(&trailing).is_err());
}

#[test]
fn donor_own_food_need_is_protected_even_when_requested_time_and_cash_are_available() {
    let mut state = aid_opening(false);
    let CircuitAccounting::Monetary(accounts) = &mut state.accounting else {
        panic!("monetary");
    };
    accounts.recurring.as_mut().unwrap().household_stocks[0].quantity = 5;
    let result = close_aid(&state, &[input(2)]).unwrap();
    assert_eq!(consumed(&result, household()).consumed_quantity, 4);
    assert_eq!(consumed(&result, household()).unmet_quantity, 0);
    let grant = result
        .aid
        .iter()
        .find(|r| r.outcome == AidOutcome::Granted)
        .unwrap();
    assert_eq!(grant.quantity, 1);
    assert_eq!(grant.carrying_amount, money(6));
    assert!(result
        .aid
        .iter()
        .any(|r| r.outcome == AidOutcome::Unshipped && r.quantity == 1));
}
