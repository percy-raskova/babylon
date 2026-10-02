//! Funded attendance and physical delivery share the material close.

use std::collections::BTreeSet;

use babylon_kernel::currency::Currency;

use crate::{
    AccountId, BacklogRow, FinalDemandOrder, MaterialCircuitError, MaterialCircuitState,
    MonetaryBook, MonetaryError, MoneyTransferReceipt, OrderRow, OutboundOrderId, PurchaseEscrow,
    ShiftState, SiteId, UnitId, MAX_MATERIAL_CIRCUIT_ROWS,
};

/// Derived close ceiling: 3M member payroll, 2N old purchase movements, 3N household
/// admission/settlement/refund, 2N new firm admission/settlement, and 4N
/// service admission plus settlement/refund movements.
/// Another 4N bounds public budgets, taxes, owner payouts and contributions.
/// Another N admits ordinary equipment purchase reserves.
/// The complete receipt envelope retains its independent byte ceiling.
pub const MAX_MONEY_TRANSFERS_PER_PERIOD: usize =
    3 * crate::MAX_STAFFING_MEMBERS + 16 * MAX_MATERIAL_CIRCUIT_ROWS;

/// Controls declare that they omit money; monetary campaigns never infer this
/// from missing accounts or prices. Both use the same physical allocator.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CircuitAccounting {
    PhysicalControl,
    Monetary(Box<MonetaryCircuit>),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MonetaryCircuit {
    pub financial: crate::FinancialInstitutions,
    pub costs: crate::HistoricalCostBook,
    pub recurring: Option<Box<crate::RecurringEconomy>>,
    pub book: MonetaryBook,
    pub employment: Vec<EmploymentTerms>,
    pub member_labor: Vec<crate::MemberLaborCapacityRow>,
}

mod attendance;
pub(crate) use attendance::{fund_attendance, AttendanceLedger, LaborUse};
pub use attendance::{
    member_shift_id, EmploymentTerms, LaborCompensation, LaborUseReceipt, MemberLaborUseReceipt,
};

/// Admission fixes the price and funds the entire accepted principal. Buyers
/// decide their affordable requested quantity before invoking this boundary.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum MaterialPurchase {
    Delivery(OrderRow),
    LocalFinalDemand(FinalDemandOrder),
    Service(crate::ServiceOrder),
}

impl From<MonetaryError> for MaterialCircuitError {
    fn from(value: MonetaryError) -> Self {
        match value {
            MonetaryError::Arithmetic => Self::Arithmetic,
            MonetaryError::RowLimit => Self::RowLimit,
            _ => Self::MonetaryInvariant,
        }
    }
}

pub(crate) fn canonicalize(accounting: &mut CircuitAccounting) {
    if let CircuitAccounting::Monetary(economy) = accounting {
        if let Some(recurring) = &mut economy.recurring {
            crate::recurring::canonicalize(recurring);
        }
        crate::financial::canonicalize(&mut economy.financial);
        economy
            .employment
            .sort_by_key(|row| (row.site_id, row.unit_id, row.member_id));
        economy
            .member_labor
            .sort_by_key(|row| (row.period, row.member_id));
    }
}

fn validate_member_budgets(
    state: &MaterialCircuitState,
    economy: &MonetaryCircuit,
) -> Result<(), MaterialCircuitError> {
    use std::collections::BTreeMap;
    let terms: BTreeMap<_, _> = economy
        .employment
        .iter()
        .map(|row| (row.member_id, row))
        .collect();
    let mut seen = BTreeSet::new();
    let mut groups = BTreeMap::<_, (u64, usize)>::new();
    for row in &economy.member_labor {
        let term = terms
            .get(&row.member_id)
            .ok_or(MaterialCircuitError::PayrollInvariant)?;
        if row.period < state.period || !seen.insert((row.period, row.member_id)) {
            return Err(MaterialCircuitError::PayrollInvariant);
        }
        let group = groups
            .entry((row.period, term.site_id, term.unit_id))
            .or_default();
        group.0 = group
            .0
            .checked_add(row.available_hours)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        group.1 += 1;
    }
    let mut expected_members = BTreeMap::<_, usize>::new();
    for term in &economy.employment {
        *expected_members
            .entry((term.site_id, term.unit_id))
            .or_default() += 1;
    }
    for row in state.labor.iter().filter(|row| row.period >= state.period) {
        let actual = groups.remove(&(row.period, row.site_id, row.unit_id));
        let count = expected_members
            .get(&(row.site_id, row.unit_id))
            .copied()
            .unwrap_or(0);
        if !(row.available == 0 && count == 0 && actual.is_none())
            && actual != Some((row.available, count))
        {
            return Err(MaterialCircuitError::PayrollInvariant);
        }
    }
    if !groups.is_empty() {
        return Err(MaterialCircuitError::PayrollInvariant);
    }
    Ok(())
}

fn labor_principals(state: &MaterialCircuitState) -> BTreeSet<(SiteId, UnitId)> {
    let mut result: BTreeSet<_> = state
        .labor
        .iter()
        .map(|row| (row.site_id, row.unit_id))
        .collect();
    for output in &state.process_outputs {
        if let Ok(index) = state
            .labor_coefficients
            .binary_search_by_key(&output.process_id, |row| row.process_id)
        {
            let coefficient = &state.labor_coefficients[index];
            result.insert((output.site_id, coefficient.unit_id));
        }
    }
    result.extend(
        state
            .merchants
            .iter()
            .map(|row| (row.site_id, row.labor_unit_id)),
    );
    if let Some(binding) = &state.maintenance_binding {
        result.insert((binding.provider_site_id, binding.labor_unit_id));
    }
    result
}

pub(crate) fn validate(state: &MaterialCircuitState) -> Result<(), MaterialCircuitError> {
    let CircuitAccounting::Monetary(economy) = &state.accounting else {
        return Ok(());
    };
    if economy.employment.len() > crate::MAX_STAFFING_MEMBERS
        || economy.member_labor.len() > crate::MAX_STAFFING_MEMBERS
    {
        return Err(MaterialCircuitError::RowLimit);
    }
    let sites: BTreeSet<_> = state
        .site_logistics_nodes
        .iter()
        .map(|row| row.site_id)
        .collect();
    let households: BTreeSet<_> = state
        .final_demand_principals
        .iter()
        .map(|row| row.id)
        .collect();
    for site in &sites {
        economy.book.cash(AccountId::Site(*site))?;
    }
    for household in &households {
        economy.book.cash(AccountId::Household(*household))?;
    }
    let snapshot = economy.book.snapshot();
    for account in &snapshot.accounts {
        match account.id {
            AccountId::Site(site) if !sites.contains(&site) => {
                return Err(MaterialCircuitError::MonetaryInvariant)
            }
            AccountId::Household(household) if !households.contains(&household) => {
                return Err(MaterialCircuitError::MonetaryInvariant)
            }
            _ => {}
        }
    }
    let mut employment = BTreeSet::new();
    let mut member_ids = BTreeSet::new();
    for row in &economy.employment {
        employment.insert((row.site_id, row.unit_id));
        if !member_ids.insert(row.member_id)
            || !sites.contains(&row.site_id)
            || !households.contains(&row.payee)
            || matches!(row.compensation, LaborCompensation::Wage(rate) if rate.micro_units() <= 0)
        {
            return Err(MaterialCircuitError::PayrollInvariant);
        }
    }
    let principals = labor_principals(state);
    if !employment.is_subset(&principals)
        || state.labor.iter().any(|r| {
            r.period >= state.period
                && r.available != 0
                && !employment.contains(&(r.site_id, r.unit_id))
        })
    {
        return Err(MaterialCircuitError::PayrollInvariant);
    }
    validate_member_budgets(state, economy)?;
    validate_opening_shifts(&snapshot.shifts, state.period, &sites, &households)?;
    if snapshot.purchases.len()
        != state.orders.len() + state.final_demand_orders.len() + state.service_orders.len()
    {
        return Err(MaterialCircuitError::PurchaseInvariant);
    }
    for order in &state.orders {
        if order.realized != order.delivered {
            return Err(MaterialCircuitError::PurchaseInvariant);
        }
        validate_purchase(
            &economy.book,
            OutboundOrderId::Delivery(order.order_id),
            AccountId::Site(order.buyer_site_id),
            AccountId::Site(order.supplier_site_id),
            order.ordered,
            order.delivered,
            order.lost,
        )?;
    }
    for order in &state.final_demand_orders {
        validate_purchase(
            &economy.book,
            OutboundOrderId::LocalFinalDemand(order.order_id),
            AccountId::Household(order.demand_principal_id),
            AccountId::Site(order.retailer_site_id),
            order.ordered,
            order.fulfilled,
            0,
        )?;
    }
    validate_service_purchases(state, &economy.book)?;
    economy.book.total_cash_and_reserves()?;
    crate::financial::validate(state)?;
    crate::recurring::validate(state)?;
    Ok(())
}

fn validate_opening_shifts(
    shifts: &[crate::FundedShift],
    period: u64,
    sites: &BTreeSet<SiteId>,
    households: &BTreeSet<crate::FinalDemandPrincipalId>,
) -> Result<(), MaterialCircuitError> {
    // A committed opening can contain previously earned but unpaid wages.
    // Half-completed attendance belongs only inside the detached close.
    for shift in shifts {
        if shift.period == 0 || shift.period >= period || shift.state != ShiftState::Accrued {
            return Err(MaterialCircuitError::PayrollInvariant);
        }
        let (AccountId::Site(site), AccountId::Household(payee)) = (shift.employer, shift.payee)
        else {
            return Err(MaterialCircuitError::PayrollInvariant);
        };
        if !sites.contains(&site) || !households.contains(&payee) {
            return Err(MaterialCircuitError::PayrollInvariant);
        }
    }
    Ok(())
}

fn validate_service_purchases(
    state: &MaterialCircuitState,
    book: &MonetaryBook,
) -> Result<(), MaterialCircuitError> {
    for order in &state.service_orders {
        validate_purchase(
            book,
            OutboundOrderId::Service(order.order_id),
            order.buyer,
            AccountId::Site(order.provider_site_id),
            order.quantity,
            0,
            0,
        )?;
    }
    Ok(())
}

fn validate_purchase(
    book: &MonetaryBook,
    id: OutboundOrderId,
    buyer: AccountId,
    seller: AccountId,
    quantity: u64,
    delivered: u64,
    refunded: u64,
) -> Result<(), MaterialCircuitError> {
    let purchase = book
        .purchase(id)
        .map_err(|_| MaterialCircuitError::PurchaseInvariant)?;
    if (
        purchase.buyer,
        purchase.seller,
        purchase.quantity,
        purchase.delivered,
        purchase.refunded,
    ) != (buyer, seller, quantity, delivered, refunded)
    {
        return Err(MaterialCircuitError::PurchaseInvariant);
    }
    Ok(())
}

/// Admit a new physical order and its exact reserve as one detached change.
///
/// # Errors
/// Refuses physical controls, malformed/duplicate principals, missing parties,
/// insufficient funds and any invalid resulting physical state. No mutation of
/// `opening` or partial receipt escapes a refusal.
pub fn admit_material_purchase(
    opening: &MaterialCircuitState,
    purchase: MaterialPurchase,
    unit_price: Currency,
) -> Result<(MaterialCircuitState, MoneyTransferReceipt), MaterialCircuitError> {
    let mut state = crate::transition::canonical_state(opening)?;
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        return Err(MaterialCircuitError::MonetaryInvariant);
    };
    if state.orders.len() + state.final_demand_orders.len() + state.service_orders.len()
        >= MAX_MATERIAL_CIRCUIT_ROWS
    {
        return Err(MaterialCircuitError::RowLimit);
    }
    let principal = match &purchase {
        MaterialPurchase::Service(order) => PurchaseEscrow::new(
            OutboundOrderId::Service(order.order_id),
            order.buyer,
            AccountId::Site(order.provider_site_id),
            order.quantity,
            unit_price,
        )?,
        MaterialPurchase::Delivery(order) => {
            if order.shipped != 0 || order.lost != 0 || order.delivered != 0 || order.realized != 0
            {
                return Err(MaterialCircuitError::PurchaseInvariant);
            }
            PurchaseEscrow::new(
                OutboundOrderId::Delivery(order.order_id),
                AccountId::Site(order.buyer_site_id),
                AccountId::Site(order.supplier_site_id),
                order.ordered,
                unit_price,
            )?
        }
        MaterialPurchase::LocalFinalDemand(order) => {
            if order.fulfilled != 0 {
                return Err(MaterialCircuitError::PurchaseInvariant);
            }
            PurchaseEscrow::new(
                OutboundOrderId::LocalFinalDemand(order.order_id),
                AccountId::Household(order.demand_principal_id),
                AccountId::Site(order.retailer_site_id),
                order.ordered,
                unit_price,
            )?
        }
    };
    let receipt = economy.book.reserve_purchase(principal)?;
    match purchase {
        MaterialPurchase::Service(order) => state.service_orders.push(order),
        MaterialPurchase::Delivery(order) => {
            state.backlog.push(BacklogRow {
                order_id: order.order_id,
                quantity: order.ordered,
            });
            state.orders.push(order);
        }
        MaterialPurchase::LocalFinalDemand(order) => state.final_demand_orders.push(order),
    }
    Ok((crate::transition::canonical_state(&state)?, receipt))
}

pub(crate) fn settle_deliveries(
    state: &mut MaterialCircuitState,
    transfers: &mut Vec<MoneyTransferReceipt>,
) -> Result<(), MaterialCircuitError> {
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        return Ok(());
    };
    for order in &state.orders {
        let id = OutboundOrderId::Delivery(order.order_id);
        if order.lost > economy.book.purchase(id)?.refunded {
            transfers.push(economy.book.refund_purchase(id, order.lost)?.transfer);
        }
        if order.delivered > economy.book.purchase(id)?.delivered {
            transfers.push(economy.book.settle_purchase(id, order.delivered)?.transfer);
        }
    }
    for order in &state.final_demand_orders {
        let id = OutboundOrderId::LocalFinalDemand(order.order_id);
        if order.fulfilled > economy.book.purchase(id)?.delivered {
            transfers.push(economy.book.settle_purchase(id, order.fulfilled)?.transfer);
        }
    }
    Ok(())
}

pub(crate) fn conserved(
    opening: &MaterialCircuitState,
    closing: &MaterialCircuitState,
) -> Result<(), MaterialCircuitError> {
    match (&opening.accounting, &closing.accounting) {
        (CircuitAccounting::PhysicalControl, CircuitAccounting::PhysicalControl) => Ok(()),
        (CircuitAccounting::Monetary(before), CircuitAccounting::Monetary(after))
            if before.book.total_cash_and_reserves()?
                == after.book.total_cash_and_reserves()? =>
        {
            Ok(())
        }
        _ => Err(MaterialCircuitError::MonetaryInvariant),
    }
}
