//! Exact splits by largest remainder, on whole numbers.
use super::types::CountyReviewError;

/// What to do with units that fall inside a run of exactly equal remainders.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Ties {
    /// Give none of the run anything and report the units as withheld.
    Withhold,
    /// Give them to the earlier parts.
    InOrder,
}

/// A split: each part's share and the units no part received.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Apportionment {
    /// One share per weight, in order.
    pub shares: Vec<u64>,
    /// Units left unassigned by a tie under `Ties::Withhold`.
    pub withheld: u64,
}

/// Splits `total` over `weights` by largest remainder.
///
/// Part `i` gets `total * weights[i] / sum(weights)` rounded down. The units left over go one each
/// to the largest remainders. Inside a run of equal remainders that the cut divides, `ties` says
/// what happens. A sum of zero returns all zeros.
///
/// # Errors
///
/// `SplitExceedsWeights` when `total` is more than the weights hold, and `Arithmetic` when a sum
/// leaves its range.
pub fn apportion(
    total: u64,
    weights: &[u64],
    ties: Ties,
) -> Result<Apportionment, CountyReviewError> {
    let sum = weights.iter().try_fold(0_u128, |acc, w| {
        acc.checked_add(u128::from(*w))
            .ok_or(CountyReviewError::Arithmetic)
    })?;
    if u128::from(total) > sum {
        return Err(CountyReviewError::SplitExceedsWeights);
    }
    if sum == 0 {
        return Ok(Apportionment {
            shares: vec![0; weights.len()],
            withheld: 0,
        });
    }
    let mut shares: Vec<u64> = Vec::with_capacity(weights.len());
    let mut remainders: Vec<(u128, usize)> = Vec::with_capacity(weights.len());
    for (index, weight) in weights.iter().enumerate() {
        let numerator = u128::from(total)
            .checked_mul(u128::from(*weight))
            .ok_or(CountyReviewError::Arithmetic)?;
        shares.push(u64::try_from(numerator / sum).map_err(|_| CountyReviewError::Arithmetic)?);
        remainders.push((numerator % sum, index));
    }
    let assigned = shares.iter().try_fold(0_u64, |acc, s| {
        acc.checked_add(*s).ok_or(CountyReviewError::Arithmetic)
    })?;
    let leftover = total
        .checked_sub(assigned)
        .ok_or(CountyReviewError::Arithmetic)?;
    let withheld = hand_out_leftover(&mut shares, &mut remainders, leftover, ties)?;
    Ok(Apportionment { shares, withheld })
}

/// Gives the leftover units to the largest remainders and returns the units withheld.
fn hand_out_leftover(
    shares: &mut [u64],
    remainders: &mut [(u128, usize)],
    leftover: u64,
    ties: Ties,
) -> Result<u64, CountyReviewError> {
    let cut = usize::try_from(leftover).map_err(|_| CountyReviewError::Arithmetic)?;
    if cut == 0 {
        return Ok(0);
    }
    // Largest remainder first; equal remainders keep the caller's order.
    remainders.sort_by(|a, b| b.0.cmp(&a.0).then(a.1.cmp(&b.1)));
    let at_cut = remainders
        .get(cut - 1)
        .ok_or(CountyReviewError::Arithmetic)?
        .0;
    let next_equal = remainders.get(cut).is_some_and(|r| r.0 == at_cut);
    let mut withheld = 0_u64;
    for (remainder, index) in remainders.iter().take(cut) {
        let inside_tied_run = next_equal && *remainder == at_cut;
        if inside_tied_run && ties == Ties::Withhold {
            withheld = withheld
                .checked_add(1)
                .ok_or(CountyReviewError::Arithmetic)?;
            continue;
        }
        let share = shares
            .get_mut(*index)
            .ok_or(CountyReviewError::Arithmetic)?;
        *share = share.checked_add(1).ok_or(CountyReviewError::Arithmetic)?;
    }
    Ok(withheld)
}

/// Splits `total` in the ratio `upper : lower`.
///
/// Each part is `total * part / (upper + lower)` rounded down. The household left over goes to the
/// larger remainder, and to `lower` on an exact tie.
///
/// # Errors
///
/// `SplitExceedsWeights` when a nonzero `total` has no weight to split over, and `Arithmetic` when
/// a product leaves its range.
pub fn ratio_split(total: u64, upper: u64, lower: u64) -> Result<(u64, u64), CountyReviewError> {
    let sum = u128::from(upper)
        .checked_add(u128::from(lower))
        .ok_or(CountyReviewError::Arithmetic)?;
    if sum == 0 {
        return if total == 0 {
            Ok((0, 0))
        } else {
            Err(CountyReviewError::SplitExceedsWeights)
        };
    }
    let upper_numerator = u128::from(total)
        .checked_mul(u128::from(upper))
        .ok_or(CountyReviewError::Arithmetic)?;
    let lower_numerator = u128::from(total)
        .checked_mul(u128::from(lower))
        .ok_or(CountyReviewError::Arithmetic)?;
    let mut upper_part =
        u64::try_from(upper_numerator / sum).map_err(|_| CountyReviewError::Arithmetic)?;
    let mut lower_part =
        u64::try_from(lower_numerator / sum).map_err(|_| CountyReviewError::Arithmetic)?;
    let assigned = upper_part
        .checked_add(lower_part)
        .ok_or(CountyReviewError::Arithmetic)?;
    let leftover = total
        .checked_sub(assigned)
        .ok_or(CountyReviewError::Arithmetic)?;
    // Two remainders, each below the sum, add to at most one whole sum.
    if leftover == 1 {
        if upper_numerator % sum > lower_numerator % sum {
            upper_part = upper_part
                .checked_add(1)
                .ok_or(CountyReviewError::Arithmetic)?;
        } else {
            lower_part = lower_part
                .checked_add(1)
                .ok_or(CountyReviewError::Arithmetic)?;
        }
    } else if leftover != 0 {
        return Err(CountyReviewError::Arithmetic);
    }
    Ok((upper_part, lower_part))
}
