//! Designed historical-cost bookkeeping over the authoritative physical close.
//! No price revaluation, credit, money issuance, or claim to measure surplus value.

mod book;
mod close;
mod equipment;
mod financial;
mod model;
mod validation;
pub(crate) use close::CostClose;
pub(crate) use validation::validate;

use crate::MaterialCircuitError;
use babylon_kernel::currency::Currency;
pub use book::HistoricalCostBook;
pub use model::*;

type Result<T> = std::result::Result<T, MaterialCircuitError>;
pub const MAX_CARRYING_STOCKS: usize = 2 * crate::MAX_MATERIAL_CIRCUIT_ROWS;

fn zero() -> Currency {
    Currency::from_micro_units(0)
}
fn add(a: Currency, b: Currency) -> Result<Currency> {
    a.checked_add(b)
        .map_err(|_| MaterialCircuitError::Arithmetic)
}
fn sub(a: Currency, b: Currency) -> Result<Currency> {
    a.checked_sub(b)
        .map_err(|_| MaterialCircuitError::Arithmetic)
}
fn amount(quantity: u64, rate: Currency) -> Result<Currency> {
    rate.micro_units()
        .checked_mul(i128::from(quantity))
        .map(Currency::from_micro_units)
        .ok_or(MaterialCircuitError::Arithmetic)
}

/// Exact ordered proportional withdrawal. The residual stays on remaining units;
/// withdrawing every remaining unit always transfers every remaining micro-unit.
pub(crate) fn portion(carrying: Currency, available: u64, quantity: u64) -> Result<Currency> {
    let cost = carrying.micro_units();
    if cost < 0 || quantity > available || (available == 0 && cost != 0) {
        return Err(MaterialCircuitError::ValuationInvariant);
    }
    if quantity == 0 {
        return Ok(zero());
    }
    if quantity == available {
        return Ok(carrying);
    }
    let denominator = i128::from(available);
    let whole = (cost / denominator)
        .checked_mul(i128::from(quantity))
        .ok_or(MaterialCircuitError::Arithmetic)?;
    let remainder =
        u128::try_from(cost % denominator).map_err(|_| MaterialCircuitError::Arithmetic)?;
    let fraction = remainder
        .checked_mul(u128::from(quantity))
        .ok_or(MaterialCircuitError::Arithmetic)?
        / u128::from(available);
    add(
        Currency::from_micro_units(whole),
        Currency::from_micro_units(
            i128::try_from(fraction).map_err(|_| MaterialCircuitError::Arithmetic)?,
        ),
    )
}

impl IncomeStatement {
    pub(crate) fn empty() -> Self {
        Self {
            sales: zero(),
            wage_income: zero(),
            cost_of_goods_sold: zero(),
            productive_labor_capitalized: zero(),
            installation_labor_capitalized: zero(),
            equipment_wear_capitalized: zero(),
            idle_labor_expense: zero(),
            handling_expense: zero(),
            maintenance_labor_expense: zero(),
            maintenance_material_expense: zero(),
            freight_loss_expense: zero(),
            consumption_expense: zero(),
            final_demand_outlay: zero(),
            unused_service_expense: zero(),
            tax_income: zero(),
            tax_expense: zero(),
            public_transfer_income: zero(),
            public_transfer_expense: zero(),
            distribution_income: zero(),
        }
    }

    fn expenses(&self) -> [Currency; 9] {
        [
            self.cost_of_goods_sold,
            self.idle_labor_expense,
            self.handling_expense,
            self.maintenance_labor_expense,
            self.maintenance_material_expense,
            self.freight_loss_expense,
            self.consumption_expense,
            self.final_demand_outlay,
            self.unused_service_expense,
        ]
    }
    /// Operating sales less consumed costs; excludes all income/capital transfers.
    /// # Errors
    /// Refuses invalid amounts or unrepresentable sums.
    pub fn operating_income(&self) -> Result<Currency> {
        let expenses = self.expenses();
        if self.sales.micro_units() < 0 || expenses.iter().any(|x| x.micro_units() < 0) {
            return Err(MaterialCircuitError::ValuationInvariant);
        }
        sub(self.sales, expenses.into_iter().try_fold(zero(), add)?)
    }
    /// Period book income. Issuer distributions are an equity withdrawal; property
    /// income must be eliminated against those withdrawals in consolidated reports.
    /// # Errors
    /// Refuses negative flow amounts or unrepresentable sums.
    pub fn net_income(&self) -> Result<Currency> {
        let incomes = [
            self.wage_income,
            self.tax_income,
            self.public_transfer_income,
            self.distribution_income,
        ];
        let outlays = [self.tax_expense, self.public_transfer_expense];
        if incomes
            .iter()
            .chain(outlays.iter())
            .any(|x| x.micro_units() < 0)
            || self.productive_labor_capitalized.micro_units() < 0
            || self.installation_labor_capitalized.micro_units() < 0
            || self.equipment_wear_capitalized.micro_units() < 0
        {
            return Err(MaterialCircuitError::ValuationInvariant);
        }
        sub(
            add(
                self.operating_income()?,
                incomes.into_iter().try_fold(zero(), add)?,
            )?,
            outlays.into_iter().try_fold(zero(), add)?,
        )
    }
}

impl IncomeReceipt {
    /// Validate the equations this standalone receipt can establish.
    /// # Errors
    /// Refuses a zero period, invalid flows or inconsistent retained earnings.
    pub fn validate(&self) -> Result<()> {
        if self.period == 0
            || self.opening_capital.micro_units() < 0
            || self.opening_contributed_capital.micro_units() < 0
            || self.contributions_received.micro_units() < 0
            || self.distributions_paid.micro_units() < 0
            || self.closing_contributed_capital
                != add(
                    self.opening_contributed_capital,
                    self.contributions_received,
                )?
            || self.net_income != self.statement.net_income()?
            || self.closing_retained_earnings
                != sub(
                    add(self.opening_retained_earnings, self.net_income)?,
                    self.distributions_paid,
                )?
        {
            return Err(MaterialCircuitError::ValuationInvariant);
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn proportional_cost_preserves_exact_remainder_even_at_i128_and_u64_limits() {
        let cost = Currency::from_micro_units(i128::MAX);
        let partial = portion(cost, u64::MAX, u64::MAX - 1).unwrap();
        let residual = sub(cost, partial).unwrap();
        assert!(partial.micro_units() > 0);
        assert_eq!(
            add(partial, portion(residual, 1, 1).unwrap()).unwrap(),
            cost
        );
        let seven = Currency::from_micro_units(7);
        assert_eq!(portion(seven, 4, 3).unwrap(), Currency::from_micro_units(5));
        assert_eq!(
            portion(Currency::from_micro_units(2), 1, 1).unwrap(),
            Currency::from_micro_units(2)
        );
        assert_eq!(
            portion(seven, 0, 0),
            Err(MaterialCircuitError::ValuationInvariant)
        );
        assert_eq!(
            portion(seven, 4, 5),
            Err(MaterialCircuitError::ValuationInvariant)
        );
    }
}
