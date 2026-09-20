//! Funded attendance and physical delivery share the material close.

use std::collections::BTreeSet;

use babylon_kernel::{content_digest::sha256_of, currency::Currency};

use crate::{
    AccountId, BacklogRow, FinalDemandOrder, FinalDemandPrincipalId, FundedShift,
    MaterialCircuitError, MaterialCircuitState, MonetaryBook, MonetaryError, MoneyTransferReceipt,
    OrderRow, OutboundOrderId, PurchaseEscrow, ShiftId, ShiftState, SiteId, UnitId,
    WageAccrualReceipt, MAX_MATERIAL_CIRCUIT_ROWS,
};

/// Derived close ceiling: one prior wage payment, two current payroll movements,
/// and at most two purchase movements per bounded principal family. The complete
/// receipt envelope still has its independent byte ceiling.
pub const MAX_MONEY_TRANSFERS_PER_PERIOD: usize = 5 * MAX_MATERIAL_CIRCUIT_ROWS;

/// Controls declare that they omit money; monetary campaigns never infer this
/// from missing accounts or prices. Both use the same physical allocator.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CircuitAccounting {
    PhysicalControl,
    Monetary(MonetaryCircuit),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MonetaryCircuit {
    pub book: MonetaryBook,
    pub employment: Vec<EmploymentTerms>,
}

/// A captured attendance wage for one workplace's exact labor unit. This binds
/// workplace hours to a resident payee; it does not turn jobs into people.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct EmploymentTerms {
    pub site_id: SiteId,
    pub unit_id: UnitId,
    pub payee: FinalDemandPrincipalId,
    pub hourly_rate: Currency,
}

/// Physical utilization is reported after work, independently of wage payment.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LaborUseReceipt {
    pub site_id: SiteId,
    pub unit_id: UnitId,
    pub payee: FinalDemandPrincipalId,
    pub period: u64,
    pub available_hours: u64,
    pub funded_hours: u64,
    pub unfunded_hours: u64,
    pub used_hours: u64,
    pub paid_idle_hours: u64,
}

/// Admission fixes the price and funds the entire accepted principal. Buyers
/// decide their affordable requested quantity before invoking this boundary.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum MaterialPurchase {
    Delivery(OrderRow),
    LocalFinalDemand(FinalDemandOrder),
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
        economy
            .employment
            .sort_by_key(|row| (row.site_id, row.unit_id));
    }
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
    if economy.employment.len() > MAX_MATERIAL_CIRCUIT_ROWS {
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
    for row in &economy.employment {
        if !employment.insert((row.site_id, row.unit_id))
            || !sites.contains(&row.site_id)
            || !households.contains(&row.payee)
            || row.hourly_rate.micro_units() <= 0
        {
            return Err(MaterialCircuitError::PayrollInvariant);
        }
    }
    if employment != labor_principals(state) {
        return Err(MaterialCircuitError::PayrollInvariant);
    }
    // A committed opening can contain previously earned but unpaid wages.
    // Half-completed attendance belongs only inside the detached close.
    for shift in &snapshot.shifts {
        if shift.period == 0 || shift.period >= state.period || shift.state != ShiftState::Accrued {
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
    if snapshot.purchases.len() != state.orders.len() + state.final_demand_orders.len() {
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
    economy.book.total_cash_and_reserves()?;
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
    let principal = match &purchase {
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

fn shift_id(period: u64, terms: &EmploymentTerms) -> ShiftId {
    let mut bytes = b"babylon.funded-attendance.v1\0".to_vec();
    bytes.extend_from_slice(&period.to_be_bytes());
    bytes.extend_from_slice(&terms.site_id.as_bytes());
    bytes.extend_from_slice(&terms.unit_id.as_bytes());
    bytes.extend_from_slice(&terms.payee.as_bytes());
    ShiftId::from_bytes(sha256_of(&bytes))
}

pub(crate) fn fund_attendance(
    state: &mut MaterialCircuitState,
    transfers: &mut Vec<MoneyTransferReceipt>,
    accruals: &mut Vec<WageAccrualReceipt>,
) -> Result<Vec<LaborUseReceipt>, MaterialCircuitError> {
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        return Ok(vec![]);
    };
    for shift in economy.book.snapshot().shifts {
        transfers.push(economy.book.pay_shift(shift.id)?);
        economy.book.retire_shift(shift.id)?;
    }
    let mut receipts = Vec::new();
    // Canonical site/unit order is the explicit priority when one employer's
    // cash cannot fund every kind of attendance. No fractional hour is hired.
    for labor in state
        .labor
        .iter_mut()
        .filter(|row| row.period == state.period)
    {
        let index = economy
            .employment
            .binary_search_by_key(&(labor.site_id, labor.unit_id), |row| {
                (row.site_id, row.unit_id)
            })
            .map_err(|_| MaterialCircuitError::PayrollInvariant)?;
        let terms = &economy.employment[index];
        let cash = economy
            .book
            .cash(AccountId::Site(terms.site_id))?
            .micro_units();
        let affordable = cash / terms.hourly_rate.micro_units();
        let funded = u64::try_from(affordable.min(i128::from(labor.available)))
            .map_err(|_| MaterialCircuitError::Arithmetic)?;
        receipts.push(LaborUseReceipt {
            site_id: labor.site_id,
            unit_id: labor.unit_id,
            payee: terms.payee,
            period: state.period,
            available_hours: labor.available,
            funded_hours: funded,
            unfunded_hours: labor.available - funded,
            used_hours: 0,
            paid_idle_hours: funded,
        });
        labor.available = funded;
        if funded == 0 {
            continue;
        }
        let id = shift_id(state.period, terms);
        transfers.push(economy.book.reserve_shift(FundedShift::new(
            id,
            AccountId::Site(terms.site_id),
            AccountId::Household(terms.payee),
            state.period,
            funded,
            terms.hourly_rate,
        )?)?);
        accruals.push(economy.book.accrue_shift(id)?);
        transfers.push(economy.book.pay_shift(id)?);
        economy.book.retire_shift(id)?;
    }
    Ok(receipts)
}

pub(crate) fn record_labor_use(
    state: &MaterialCircuitState,
    receipts: &mut [LaborUseReceipt],
) -> Result<(), MaterialCircuitError> {
    for receipt in receipts {
        let index = state
            .labor
            .binary_search_by_key(&(receipt.period, receipt.site_id, receipt.unit_id), |row| {
                (row.period, row.site_id, row.unit_id)
            })
            .map_err(|_| MaterialCircuitError::PayrollInvariant)?;
        let remaining = state.labor[index].available;
        receipt.used_hours = receipt
            .funded_hours
            .checked_sub(remaining)
            .ok_or(MaterialCircuitError::PayrollInvariant)?;
        receipt.paid_idle_hours = remaining;
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
