//! The cut of one public budget over ranked claims, in proportion inside the first rank it cannot cover.
use super::Result;
use crate::MaterialCircuitError;
use babylon_kernel::currency::Currency;

/// The shares of `budget` over claims sorted by rank, one result per claim, in the claims' order.
///
/// Ranks are paid lowest first. A rank whose total is at most what is left is paid in full. The first
/// rank that is not gets `floor(amount x left / rank total)` for each claim, and the micro-units still
/// left go one each to the claims of that rank in their order, skipping a claim already at its amount.
/// Later ranks get nothing.
///
/// # Errors
/// `FinancialInvariant` for a negative budget or claim, or ranks out of order; `Arithmetic` on overflow.
pub(crate) fn cut_in_proportion(
    budget: Currency,
    claims: &[(u32, Currency)],
) -> Result<Vec<Currency>> {
    let mut left = budget.micro_units();
    if left < 0
        || claims.iter().any(|&(_, c)| c.micro_units() < 0)
        || claims.windows(2).any(|w| w[0].0 > w[1].0)
    {
        return Err(MaterialCircuitError::FinancialInvariant);
    }
    let mut paid = vec![0_i128; claims.len()];
    let mut start = 0;
    while start < claims.len() && left > 0 {
        let rank = claims[start].0;
        let end = start + claims[start..].iter().take_while(|c| c.0 == rank).count();
        let total = claims[start..end].iter().try_fold(0_i128, |a, c| {
            a.checked_add(c.1.micro_units())
                .ok_or(MaterialCircuitError::Arithmetic)
        })?;
        if total <= left {
            for (slot, c) in paid[start..end].iter_mut().zip(&claims[start..end]) {
                *slot = c.1.micro_units();
            }
            left -= total;
        } else {
            share_rank(left, total, &claims[start..end], &mut paid[start..end])?;
            break;
        }
        start = end;
    }
    Ok(paid.into_iter().map(Currency::from_micro_units).collect())
}

/// One rank that `left` cannot cover: floors in proportion, then the remainder one micro-unit at a time.
fn share_rank(
    left: i128,
    total: i128,
    claims: &[(u32, Currency)],
    paid: &mut [i128],
) -> Result<()> {
    let mut given = 0_i128;
    for (slot, c) in paid.iter_mut().zip(claims) {
        *slot =
            c.1.micro_units()
                .checked_mul(left)
                .ok_or(MaterialCircuitError::Arithmetic)?
                / total;
        given += *slot;
    }
    let mut remainder = left - given;
    for (slot, c) in paid.iter_mut().zip(claims) {
        if remainder == 0 {
            break;
        }
        if *slot < c.1.micro_units() {
            *slot += 1;
            remainder -= 1;
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::cut_in_proportion;
    use crate::MaterialCircuitError;
    use babylon_kernel::currency::Currency;

    fn claims(rows: &[(u32, i128)]) -> Vec<(u32, Currency)> {
        rows.iter()
            .map(|&(r, a)| (r, Currency::from_micro_units(a)))
            .collect()
    }
    const SAMPLE: [(u32, i128); 5] = [(0, 30), (1, 60), (1, 40), (1, 20), (2, 5)];
    fn cut(budget: i128, rows: &[(u32, i128)]) -> Result<Vec<i128>, MaterialCircuitError> {
        Ok(
            cut_in_proportion(Currency::from_micro_units(budget), &claims(rows))?
                .into_iter()
                .map(Currency::micro_units)
                .collect(),
        )
    }

    #[test]
    fn enough_pays_everyone_in_full() {
        assert_eq!(cut(1_000, &SAMPLE), Ok(vec![30, 60, 40, 20, 5]));
    }
    #[test]
    fn a_short_rank_is_cut_in_proportion() {
        assert_eq!(cut(100, &SAMPLE), Ok(vec![30, 36, 23, 11, 0]));
    }
    #[test]
    fn a_rank_exactly_covered_leaves_nothing_after() {
        assert_eq!(cut(150, &SAMPLE), Ok(vec![30, 60, 40, 20, 0]));
    }
    #[test]
    fn nothing_in_the_budget_pays_nothing() {
        assert_eq!(cut(0, &SAMPLE), Ok(vec![0, 0, 0, 0, 0]));
    }
    #[test]
    fn a_zero_claim_gets_no_remainder() {
        assert_eq!(cut(5, &[(0, 0), (0, 10), (0, 10)]), Ok(vec![0, 3, 2]));
    }
    #[test]
    fn no_claims_give_no_shares() {
        assert_eq!(cut(7, &[]), Ok(vec![]));
    }

    #[test]
    fn the_laws_hold_for_every_budget() {
        let total: i128 = SAMPLE.iter().map(|r| r.1).sum();
        for budget in 0..=160 {
            let paid = cut(budget, &SAMPLE).expect("the sample cuts");
            assert_eq!(
                paid.iter().sum::<i128>(),
                budget.min(total),
                "budget {budget}"
            );
            assert!(paid.iter().zip(SAMPLE).all(|(p, r)| *p <= r.1 && *p >= 0));
            // The cut rank is the first whose total the remainder does not cover.
            let mut left = budget;
            for rank in 0..=2 {
                let rows: Vec<usize> = (0..SAMPLE.len()).filter(|&i| SAMPLE[i].0 == rank).collect();
                let rank_total: i128 = rows.iter().map(|&i| SAMPLE[i].1).sum();
                if rank_total > left {
                    for &i in &rows {
                        assert!(
                            paid[i] >= SAMPLE[i].1 * left / rank_total,
                            "budget {budget}"
                        );
                    }
                    break;
                }
                left -= rank_total;
            }
        }
    }

    #[test]
    fn bad_input_is_refused() {
        assert_eq!(
            cut(-1, &SAMPLE),
            Err(MaterialCircuitError::FinancialInvariant)
        );
        assert_eq!(
            cut(10, &[(0, -1)]),
            Err(MaterialCircuitError::FinancialInvariant)
        );
        assert_eq!(
            cut(10, &[(1, 5), (0, 5)]),
            Err(MaterialCircuitError::FinancialInvariant)
        );
        assert_eq!(
            cut(10, &[(0, i128::MAX / 2), (0, i128::MAX / 2)]),
            Err(MaterialCircuitError::Arithmetic)
        );
    }
}
