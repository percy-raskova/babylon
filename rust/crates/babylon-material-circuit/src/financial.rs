//! Designed, cash-funded public/ownership policy in the existing atomic close.
mod close;
mod model;
mod receipts;
mod validation;
use crate::MaterialCircuitError;
use babylon_kernel::currency::Currency;
pub(crate) use close::FinancialClose;
pub use model::*;
pub use receipts::validate_distribution_receipts;
pub(crate) use validation::{canonicalize, validate};
type Result<T> = std::result::Result<T, MaterialCircuitError>;
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
fn available(cash: Currency, floor: Currency) -> Result<Currency> {
    Ok(sub(cash, floor)?.max(zero()))
}
/// Exact bounded fraction without multiplying an i128 money amount by shares.
fn fraction(value: Currency, numerator: u64, denominator: u64) -> Result<Currency> {
    if value.micro_units() < 0 || denominator == 0 || numerator > denominator {
        return Err(MaterialCircuitError::FinancialInvariant);
    }
    let divisor = i128::from(denominator);
    let whole = (value.micro_units() / divisor)
        .checked_mul(i128::from(numerator))
        .ok_or(MaterialCircuitError::Arithmetic)?;
    let remainder = u128::try_from(value.micro_units() % divisor)
        .map_err(|_| MaterialCircuitError::Arithmetic)?;
    let tail = remainder
        .checked_mul(u128::from(numerator))
        .ok_or(MaterialCircuitError::Arithmetic)?
        / u128::from(denominator);
    add(
        Currency::from_micro_units(whole),
        Currency::from_micro_units(
            i128::try_from(tail).map_err(|_| MaterialCircuitError::Arithmetic)?,
        ),
    )
}
