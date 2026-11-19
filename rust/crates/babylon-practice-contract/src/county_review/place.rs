//! A household's place on the county's list: an exact, non-negative fraction.
//!
//! A place is a rate worked out from totals (design 7.4): the household's people at work, times
//! the wages its crew was paid divided by the crew's people at work, times the share of the
//! group's taxed wages that the county collected as tax. Places are compared by
//! cross-multiplication in 256 bits, so no rounding can rank one position above another.
use std::cmp::Ordering;

use super::types::CountyReviewError;

/// Low 64 bits of a `u128`.
const LOW_MASK: u128 = (1_u128 << 64) - 1;

/// An exact, non-negative fraction. Ordered by cross-multiplication in 256 bits.
#[derive(Clone, Copy, Debug)]
pub struct Place {
    numerator: u128,
    /// Never zero.
    denominator: u128,
}

impl Place {
    /// A position with no wage tax paid.
    pub const ZERO: Place = Place {
        numerator: 0,
        denominator: 1,
    };

    /// Whether nobody in the position paid wage tax.
    #[must_use]
    pub fn is_zero(&self) -> bool {
        self.numerator == 0
    }

    /// The place in whole micro-dollars, rounded down. It is for display only: places are ranked
    /// by comparison, never by this figure.
    ///
    /// # Errors
    ///
    /// `Arithmetic` when the figure does not fit an `i128`.
    pub fn floor_micros(&self) -> Result<i128, CountyReviewError> {
        i128::try_from(self.numerator / self.denominator).map_err(|_| CountyReviewError::Arithmetic)
    }
}

/// The 256-bit product of two `u128`, as `(high, low)`.
fn wide_mul(a: u128, b: u128) -> (u128, u128) {
    let (a_high, a_low) = (a >> 64, a & LOW_MASK);
    let (b_high, b_low) = (b >> 64, b & LOW_MASK);
    // Each partial product is at most (2^64 - 1)^2, which fits a `u128`.
    let low_low = a_low * b_low;
    let low_high = a_low * b_high;
    let high_low = a_high * b_low;
    let high_high = a_high * b_high;
    // The middle column adds three terms below 2^64 and a carry: far below 2^128.
    let middle = (low_low >> 64) + (low_high & LOW_MASK) + (high_low & LOW_MASK);
    let low = (low_low & LOW_MASK) | ((middle & LOW_MASK) << 64);
    // The whole product is below 2^256, so the high half cannot overflow.
    let high = high_high + (low_high >> 64) + (high_low >> 64) + (middle >> 64);
    (high, low)
}

impl Ord for Place {
    fn cmp(&self, other: &Self) -> Ordering {
        wide_mul(self.numerator, other.denominator)
            .cmp(&wide_mul(other.numerator, self.denominator))
    }
}

impl PartialOrd for Place {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl PartialEq for Place {
    fn eq(&self, other: &Self) -> bool {
        self.cmp(other) == Ordering::Equal
    }
}

impl Eq for Place {}

fn gcd(mut a: u128, mut b: u128) -> u128 {
    while b != 0 {
        (a, b) = (b, a % b);
    }
    a
}

/// Reduces `numerator / denominator` by their greatest common divisor. Both are nonzero.
fn reduced(numerator: u128, denominator: u128) -> (u128, u128) {
    let divisor = gcd(numerator, denominator).max(1);
    (numerator / divisor, denominator / divisor)
}

/// The place of a household with `at_work` people at work.
///
/// `crew_wages_micros` and `crew_at_work` are the wages its crew was paid and the people at work
/// there; `group_tax_collected_micros` and `group_taxed_wages_micros` are the wage tax the county
/// collected from its budget group and the wages that were taxed. The place is zero when any
/// factor is zero. Both ratios are reduced by their greatest common divisors before they are
/// multiplied.
///
/// # Errors
///
/// `Arithmetic` for a negative amount, or a product that still overflows `u128`.
pub fn place(
    at_work: u16,
    crew_wages_micros: i128,
    crew_at_work: u64,
    group_tax_collected_micros: i128,
    group_taxed_wages_micros: i128,
) -> Result<Place, CountyReviewError> {
    let nonnegative =
        |amount: i128| u128::try_from(amount).map_err(|_| CountyReviewError::Arithmetic);
    let wages = nonnegative(crew_wages_micros)?;
    let collected = nonnegative(group_tax_collected_micros)?;
    let taxed = nonnegative(group_taxed_wages_micros)?;
    let people = u128::from(crew_at_work);
    if at_work == 0 || wages == 0 || people == 0 || collected == 0 || taxed == 0 {
        return Ok(Place::ZERO);
    }
    let (wage_each, crew_people) = reduced(wages, people);
    let (tax_share, taxed_share) = reduced(collected, taxed);
    let numerator = u128::from(at_work)
        .checked_mul(wage_each)
        .and_then(|n| n.checked_mul(tax_share))
        .ok_or(CountyReviewError::Arithmetic)?;
    let denominator = crew_people
        .checked_mul(taxed_share)
        .ok_or(CountyReviewError::Arithmetic)?;
    let (numerator, denominator) = reduced(numerator, denominator);
    Ok(Place {
        numerator,
        denominator,
    })
}
