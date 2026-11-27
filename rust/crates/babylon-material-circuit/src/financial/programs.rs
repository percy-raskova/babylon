//! What each public program owes each of its recipients this period.
use super::layoffs;
use super::{PublicProgram, PublicProgramReceipt, PublicProgramTerms, Result};
use crate::{
    CircuitAccounting, FinalDemandPrincipalId, LaborCompensation, MaterialCircuitError,
    MaterialCircuitState,
};
use babylon_kernel::currency::Currency;
use std::collections::BTreeMap;

/// One claim for each program and recipient, in (program key, recipient) order. The receipt carries
/// the claim as `due`, with nothing paid yet.
///
/// A tag-3 program owes each recipient `floor(own amount x persons x share_bps / 10_000)`, the
/// amount being the recipient's own, kept beside it in `own_amounts`.
///
/// A per-person program owes `amount_per_person x persons` of the recipient's cohort, read from the
/// state as the period opens. A cohort of no persons owes nothing. An after-layoff program owes each
/// recipient the sum, over that household's members with a record of layoffs, of what the record is
/// owed (`layoff_due`) at the member's wage; a member that does not pay a wage owes nothing.
///
/// # Errors
/// `PublicProgramInvariant` for a recipient without a cohort; `Arithmetic` on overflow.
pub(crate) fn program_dues(
    state: &MaterialCircuitState,
    programs: &[PublicProgram],
) -> Result<Vec<(PublicProgramReceipt, Currency)>> {
    let mut dues = Vec::new();
    let persons_of: BTreeMap<FinalDemandPrincipalId, u64> = state
        .recurring_economy()
        .map(|r| {
            r.households
                .iter()
                .map(|h| (h.principal_id, h.persons))
                .collect()
        })
        .unwrap_or_default();
    for program in programs {
        let layoffs = match program.terms {
            PublicProgramTerms::AfterLayoff {
                wage_share_bps,
                half_periods,
            } => owed_by_household(state, wage_share_bps, half_periods)?,
            PublicProgramTerms::PerPerson { .. } | PublicProgramTerms::PerPersonOwn { .. } => {
                BTreeMap::new()
            }
        };
        for (index, &recipient) in program.recipients.iter().enumerate() {
            let (covered_persons, due) = match program.terms {
                PublicProgramTerms::PerPerson { amount_per_person } => {
                    let persons = *persons_of
                        .get(&recipient)
                        .ok_or(MaterialCircuitError::PublicProgramInvariant)?;
                    let owed = amount_per_person
                        .micro_units()
                        .checked_mul(i128::from(persons))
                        .ok_or(MaterialCircuitError::Arithmetic)?;
                    (persons, Currency::from_micro_units(owed))
                }
                PublicProgramTerms::PerPersonOwn { share_bps } => {
                    let persons = *persons_of
                        .get(&recipient)
                        .ok_or(MaterialCircuitError::PublicProgramInvariant)?;
                    let own = program
                        .own_amounts
                        .get(index)
                        .ok_or(MaterialCircuitError::PublicProgramInvariant)?;
                    (persons, own_due(*own, persons, share_bps)?)
                }
                PublicProgramTerms::AfterLayoff { .. } => layoffs
                    .get(&recipient)
                    .map_or((0, super::zero()), |&(persons, owed)| (persons, owed)),
            };
            dues.push((
                PublicProgramReceipt {
                    period: state.period,
                    public_account: program.payer,
                    program: program.key.clone(),
                    recipient,
                    rank: program.rank,
                    covered_persons,
                    due,
                    paid: super::zero(),
                    unfunded: due,
                },
                due,
            ));
        }
    }
    dues.sort_by(|a, b| (&a.0.program, a.0.recipient).cmp(&(&b.0.program, b.0.recipient)));
    Ok(dues)
}

/// `floor(own x persons x share_bps / 10_000)`, the product checked in `i128`.
fn own_due(own: Currency, persons: u64, share_bps: u32) -> Result<Currency> {
    let product = own
        .micro_units()
        .checked_mul(i128::from(persons))
        .and_then(|n| n.checked_mul(i128::from(share_bps)))
        .ok_or(MaterialCircuitError::Arithmetic)?;
    Ok(Currency::from_micro_units(product.div_euclid(10_000)))
}

/// For each household, the persons covered and the amount owed over the records of its members.
fn owed_by_household(
    state: &MaterialCircuitState,
    wage_share_bps: u16,
    half_periods: u16,
) -> Result<BTreeMap<FinalDemandPrincipalId, (u64, Currency)>> {
    let CircuitAccounting::Monetary(e) = &state.accounting else {
        return Ok(BTreeMap::new());
    };
    let terms: BTreeMap<_, _> = e.employment.iter().map(|t| (t.member_id, t)).collect();
    let mut owed = BTreeMap::new();
    for record in &e.financial.layoffs {
        let Some(term) = terms.get(&record.member_id) else {
            continue;
        };
        let LaborCompensation::Wage(wage) = term.compensation else {
            continue;
        };
        let (persons, due) = layoffs::layoff_due(
            wage,
            record.hours_per_person,
            wage_share_bps,
            half_periods,
            &record.cohorts,
        )?;
        let entry = owed.entry(term.payee).or_insert((0_u64, super::zero()));
        entry.0 = entry
            .0
            .checked_add(persons)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        entry.1 = super::add(entry.1, due)?;
    }
    Ok(owed)
}

#[cfg(test)]
mod tests {
    use super::program_dues;
    use crate::{
        AidBook, CapacityReservations, CircuitAccounting, FinalDemandPrincipalId,
        FinancialInstitutions, HistoricalCostBook, HouseholdCohort, HouseholdKind,
        HouseholdTimeAccounting, MaterialCircuitState, MonetaryBook, MonetaryCircuit,
        PublicAccountId, PublicProgram, PublicProgramKey, PublicProgramTerms, RecurringEconomy,
    };
    use babylon_kernel::currency::Currency;

    fn principal(n: u8) -> FinalDemandPrincipalId {
        FinalDemandPrincipalId::from_bytes([n; 32])
    }

    /// A state with nothing but cohorts, which is all the dues read.
    fn state(cohorts: &[(u8, u64)]) -> MaterialCircuitState {
        let book = MonetaryBook::open(vec![]).expect("an empty book opens");
        let costs = HistoricalCostBook::open(&book, vec![], vec![], vec![], vec![])
            .expect("empty costs open");
        let recurring = RecurringEconomy {
            households: cohorts
                .iter()
                .map(|&(n, persons)| HouseholdCohort {
                    kind: HouseholdKind::Ordinary,
                    principal_id: principal(n),
                    households: 1,
                    persons,
                })
                .collect(),
            household_stocks: vec![],
            household_purchases: vec![],
            offers: vec![],
            replenishment: vec![],
            production: vec![],
            attendance: vec![],
            last_household_admission_period: 0,
            last_household_consumption_period: 0,
        };
        MaterialCircuitState {
            period: 3,
            accounting: CircuitAccounting::Monetary(Box::new(MonetaryCircuit {
                aid: AidBook::default(),
                household_time: HouseholdTimeAccounting::NotModeled,
                financial: FinancialInstitutions::empty(),
                member_labor: vec![],
                costs,
                book,
                recurring: Some(Box::new(recurring)),
                employment: vec![],
            })),
            service_connections: vec![],
            service_orders: vec![],
            route_stage_capacities: vec![],
            inventory: vec![],
            orders: vec![],
            freight: vec![],
            corridor_capacities: vec![],
            capacities: vec![],
            labor: vec![],
            production_commitments: vec![],
            final_demand_principals: vec![],
            final_demand_orders: vec![],
            maintenance_service: None,
            capacity_reservations: CapacityReservations::default(),
        }
    }

    fn program(key: &str, amount: i128, recipients: &[u8]) -> PublicProgram {
        PublicProgram {
            key: PublicProgramKey::new(key).expect("a well-formed key"),
            payer: PublicAccountId::from_bytes([9; 32]),
            rank: 2,
            terms: PublicProgramTerms::PerPerson {
                amount_per_person: Currency::from_micro_units(amount),
            },
            recipients: recipients.iter().map(|&n| principal(n)).collect(),
            own_amounts: vec![],
        }
    }

    fn own_program(share_bps: u32, recipients: &[u8], amounts: &[i128]) -> PublicProgram {
        PublicProgram {
            terms: PublicProgramTerms::PerPersonOwn { share_bps },
            own_amounts: amounts
                .iter()
                .map(|&a| Currency::from_micro_units(a))
                .collect(),
            ..program("o", 0, recipients)
        }
    }

    fn dues_of(share_bps: u32, cohorts: &[(u8, u64)], amounts: &[i128]) -> Vec<i128> {
        let ids: Vec<u8> = cohorts.iter().map(|c| c.0).collect();
        program_dues(&state(cohorts), &[own_program(share_bps, &ids, amounts)])
            .expect("dues")
            .iter()
            .map(|(_, d)| d.micro_units())
            .collect()
    }

    #[test]
    fn own_amounts_are_owed_by_their_share() {
        let cohorts = [(1, 3), (2, 2)];
        let amounts = [846_000_000, 1_691_000_000];
        assert_eq!(
            dues_of(10_000, &cohorts, &amounts),
            [2_538_000_000, 3_382_000_000]
        );
        assert_eq!(
            dues_of(9_000, &cohorts, &amounts),
            [2_284_200_000, 3_043_800_000]
        );
        assert_eq!(
            dues_of(15_000, &cohorts, &amounts),
            [3_807_000_000, 5_073_000_000]
        );
        assert_eq!(dues_of(5_000, &[(1, 3)], &[1]), [1]);
        let zero =
            program_dues(&state(&[(1, 0)]), &[own_program(10_000, &[1], &[7])]).expect("dues");
        assert_eq!(zero[0].0.covered_persons, 0);
        assert_eq!(zero[0].1.micro_units(), 0);
        assert_eq!(
            program_dues(
                &state(&[(1, 2)]),
                &[own_program(10_000, &[1], &[i128::MAX])]
            )
            .err(),
            Some(crate::MaterialCircuitError::Arithmetic)
        );
    }

    #[test]
    fn a_short_list_of_amounts_is_refused() {
        assert_eq!(
            program_dues(
                &state(&[(1, 3), (2, 2)]),
                &[own_program(10_000, &[1, 2], &[5])]
            )
            .err(),
            Some(crate::MaterialCircuitError::PublicProgramInvariant)
        );
    }

    #[test]
    fn a_cohort_of_nobody_owes_nothing() {
        let dues = program_dues(&state(&[(1, 0)]), &[program("p", 60, &[1])]).expect("dues");
        let [(receipt, due)] = dues.as_slice() else {
            panic!("one program and one recipient give one claim")
        };
        assert_eq!(due.micro_units(), 0);
        assert_eq!(receipt.covered_persons, 0);
        assert_eq!(receipt.due.micro_units(), 0);
        assert_eq!(receipt.paid.micro_units(), 0);
        assert_eq!((receipt.period, receipt.rank), (3, 2));
        receipt.validate().expect("a receipt of nothing is valid");
    }

    #[test]
    fn dues_follow_persons_and_come_in_key_then_recipient_order() {
        let programs = [program("b", 10, &[1, 2]), program("a", 7, &[2])];
        let dues = program_dues(&state(&[(1, 3), (2, 5)]), &programs).expect("dues");
        let rows: Vec<_> = dues
            .iter()
            .map(|(r, d)| (r.program.as_str().to_owned(), r.recipient, d.micro_units()))
            .collect();
        assert_eq!(
            rows,
            [
                ("a".to_owned(), principal(2), 35),
                ("b".to_owned(), principal(1), 30),
                ("b".to_owned(), principal(2), 50),
            ]
        );
    }

    /// Two thousand recipients of one program finish: a return of a scan of every cohort for each
    /// recipient would make this slow, which is all it is there to catch.
    #[test]
    fn two_thousand_recipients_are_owed_their_persons() {
        let cohorts: Vec<(u8, u64)> = vec![];
        let mut state = state(&cohorts);
        let ids: Vec<_> = (0..2_000_u16)
            .map(|n| {
                let mut bytes = [7_u8; 32];
                bytes[..2].copy_from_slice(&n.to_be_bytes());
                FinalDemandPrincipalId::from_bytes(bytes)
            })
            .collect();
        let crate::CircuitAccounting::Monetary(e) = &mut state.accounting else {
            panic!("the helper builds a monetary state")
        };
        let recurring = e.recurring.as_mut().expect("the helper builds cohorts");
        recurring.households = ids
            .iter()
            .map(|&principal_id| HouseholdCohort {
                kind: HouseholdKind::Ordinary,
                principal_id,
                households: 1,
                persons: 2,
            })
            .collect();
        let mut one = program("p", 3, &[]);
        one.recipients = ids;
        let dues = program_dues(&state, &[one]).expect("dues");
        assert_eq!(dues.len(), 2_000);
        assert!(dues
            .iter()
            .all(|(r, d)| r.covered_persons == 2 && d.micro_units() == 6));
    }

    #[test]
    fn a_recipient_without_a_cohort_is_refused() {
        assert_eq!(
            program_dues(&state(&[(1, 3)]), &[program("p", 10, &[2])]).err(),
            Some(crate::MaterialCircuitError::PublicProgramInvariant)
        );
    }

    #[test]
    fn a_due_too_large_for_money_is_an_arithmetic_error() {
        assert_eq!(
            program_dues(&state(&[(1, 2)]), &[program("p", i128::MAX, &[1])]).err(),
            Some(crate::MaterialCircuitError::Arithmetic)
        );
    }
}
