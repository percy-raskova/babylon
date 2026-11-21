//! What each public program owes each of its recipients this period.
use super::{PublicProgram, PublicProgramReceipt, PublicProgramTerms, Result};
use crate::{MaterialCircuitError, MaterialCircuitState};
use babylon_kernel::currency::Currency;

/// One claim for each program and recipient, in (program key, recipient) order. The receipt carries
/// the claim as `due`, with nothing paid yet.
///
/// A per-person program owes `amount_per_person x persons` of the recipient's cohort, read from the
/// state as the period opens. A cohort of no persons owes nothing. An after-layoff program owes
/// nothing until a record of layoffs says whom it covers.
///
/// # Errors
/// `PublicProgramInvariant` for a recipient without a cohort; `Arithmetic` on overflow.
pub(crate) fn program_dues(
    state: &MaterialCircuitState,
    programs: &[PublicProgram],
) -> Result<Vec<(PublicProgramReceipt, Currency)>> {
    let mut dues = Vec::new();
    for program in programs {
        for &recipient in &program.recipients {
            let (covered_persons, due) = match program.terms {
                PublicProgramTerms::PerPerson { amount_per_person } => {
                    let persons = state
                        .recurring_economy()
                        .and_then(|r| r.households.iter().find(|h| h.principal_id == recipient))
                        .ok_or(MaterialCircuitError::PublicProgramInvariant)?
                        .persons;
                    let owed = amount_per_person
                        .micro_units()
                        .checked_mul(i128::from(persons))
                        .ok_or(MaterialCircuitError::Arithmetic)?;
                    (persons, Currency::from_micro_units(owed))
                }
                PublicProgramTerms::AfterLayoff { .. } => (0, super::zero()),
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
        }
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
