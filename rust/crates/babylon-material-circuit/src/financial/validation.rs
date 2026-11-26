use super::FinancialInstitutions;
use super::PublicProgramTerms;
use super::PublicSpendingRule;
use super::PublicTransferTreatment;
use super::Result;
use super::{MAX_LAYOFF_HALF_PERIODS, MAX_LAYOFF_PERIODS, MAX_PROGRAM_SHARE_BPS};
use crate::MonetaryBook;
use crate::{
    AccountId, CircuitAccounting, LaborCompensation, MaterialCircuitError, MaterialCircuitState,
    MonetaryCircuit, MAX_MATERIAL_CIRCUIT_ROWS, MAX_PUBLIC_PROGRAMS, MAX_STAFFING_MEMBERS,
};
use std::collections::{BTreeMap, BTreeSet};

pub(crate) fn canonicalize(f: &mut FinancialInstitutions) {
    f.locations.sort_by_key(|r| r.account);
    f.ownership
        .sort_by_key(|r| (r.issuer_site_id, r.beneficiary));
    f.distributions.sort_by_key(|r| r.issuer_site_id);
    f.taxes
        .sort_by_key(|r| (r.payer, r.basis, r.public_recipient));
    f.public_budgets.sort_by_key(|r| r.public_account);
    f.public_allocations
        .sort_by_key(|r| (r.public_account, r.priority, r.recipient, r.treatment));
    f.contributions.sort_by_key(|r| r.id);
    f.programs.sort_by(|a, b| a.key.cmp(&b.key));
    f.layoffs.sort_by_key(|r| r.member_id);
    for program in &mut f.programs {
        if program.own_amounts.len() == program.recipients.len() {
            // An own amount stays with its recipient.
            let mut pairs: Vec<_> = program
                .recipients
                .iter()
                .copied()
                .zip(program.own_amounts.iter().copied())
                .collect();
            pairs.sort_by_key(|p| p.0);
            program.recipients = pairs.iter().map(|p| p.0).collect();
            program.own_amounts = pairs.iter().map(|p| p.1).collect();
        } else {
            program.recipients.sort();
        }
    }
}
fn unique<T, K: Ord>(rows: &[T], key: impl Fn(&T) -> K) -> Result<()> {
    bounded_unique(rows, MAX_MATERIAL_CIRCUIT_ROWS, key)
}
fn bounded_unique<T, K: Ord>(rows: &[T], limit: usize, key: impl Fn(&T) -> K) -> Result<()> {
    if rows.len() > limit {
        return Err(MaterialCircuitError::RowLimit);
    }
    let mut keys = BTreeSet::new();
    if rows.iter().any(|r| !keys.insert(key(r))) {
        return Err(MaterialCircuitError::DuplicateRow);
    }
    Ok(())
}
fn structure(f: &FinancialInstitutions) -> Result<()> {
    unique(&f.locations, |r| r.account)?;
    bounded_unique(&f.ownership, crate::MAX_OWNERSHIP_CLAIMS, |r| {
        (r.issuer_site_id, r.beneficiary)
    })?;
    unique(&f.distributions, |r| r.issuer_site_id)?;
    bounded_unique(&f.taxes, crate::MAX_TAX_POLICIES, |r| {
        (r.payer, r.basis, r.public_recipient)
    })?;
    unique(&f.public_budgets, |r| r.public_account)?;
    unique(&f.public_allocations, |r| {
        (r.public_account, r.recipient, r.treatment)
    })?;
    unique(&f.contributions, |r| r.id)
}
pub(crate) fn validate(state: &MaterialCircuitState) -> Result<()> {
    let CircuitAccounting::Monetary(e) = &state.accounting else {
        return Ok(());
    };
    let f = &e.financial;
    structure(f)?;
    let snapshot = e.book.snapshot();
    let institutions: BTreeSet<_> = snapshot
        .accounts
        .iter()
        .filter_map(|r| {
            matches!(r.id, AccountId::Organization(_) | AccountId::Public(_)).then_some(r.id)
        })
        .collect();
    if institutions != f.locations.iter().map(|r| r.account).collect() {
        return Err(MaterialCircuitError::FinancialInvariant);
    }
    let mut shares = BTreeMap::new();
    let mut claims = BTreeSet::new();
    for r in &f.ownership {
        e.book.cash(AccountId::Site(r.issuer_site_id))?;
        e.book.cash(r.beneficiary)?;
        if r.shares == 0 || r.beneficiary == AccountId::Site(r.issuer_site_id) {
            return Err(MaterialCircuitError::FinancialInvariant);
        }
        let total = shares.entry(r.issuer_site_id).or_insert(0_u64);
        *total = total
            .checked_add(r.shares)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        claims.insert((r.beneficiary, r.issuer_site_id));
    }
    let companies: BTreeSet<_> = snapshot
        .accounts
        .iter()
        .filter_map(|r| match r.id {
            AccountId::Company(id) => Some(id),
            _ => None,
        })
        .collect();
    let mut subsidiaries = BTreeSet::new();
    let mut parents = BTreeSet::new();
    for claim in &f.ownership {
        if let AccountId::Company(id) = claim.beneficiary {
            if shares[&claim.issuer_site_id] != claim.shares
                || !subsidiaries.insert(claim.issuer_site_id)
            {
                return Err(MaterialCircuitError::FinancialInvariant);
            }
            parents.insert(id);
        }
    }
    if parents != companies {
        return Err(MaterialCircuitError::FinancialInvariant);
    }
    if claims
        != e.costs
            .snapshot()
            .equity
            .iter()
            .map(|r| (r.owner, r.issuer_site_id))
            .collect()
    {
        return Err(MaterialCircuitError::FinancialInvariant);
    }
    for r in &f.distributions {
        if !shares.contains_key(&r.issuer_site_id)
            || r.earnings_fraction_bps > 10_000
            || r.period_cap.micro_units() < 0
            || r.cash_floor.micro_units() < 0
        {
            return Err(MaterialCircuitError::FinancialInvariant);
        }
    }
    validate_public(f, &e.book)?;
    validate_programs(state, f)?;
    for r in &f.contributions {
        if r.due_period < state.period
            || r.amount.micro_units() <= 0
            || !claims.contains(&(r.contributor, r.issuer_site_id))
        {
            return Err(MaterialCircuitError::FinancialInvariant);
        }
    }
    Ok(())
}
fn validate_public(f: &FinancialInstitutions, book: &MonetaryBook) -> Result<()> {
    let mut budgets = BTreeSet::new();
    for r in &f.public_budgets {
        book.cash(AccountId::Public(r.public_account))?;
        // A budget in proportion does not read its cap, so a cap is refused, never ignored.
        if r.period_cap.micro_units() < 0
            || r.cash_floor.micro_units() < 0
            || (r.rule == PublicSpendingRule::CashInProportion && r.period_cap.micro_units() != 0)
        {
            return Err(MaterialCircuitError::FinancialInvariant);
        }
        budgets.insert(r.public_account);
    }
    for r in &f.public_allocations {
        book.cash(r.recipient)?;
        let valid = matches!(
            (r.treatment, r.recipient),
            (
                PublicTransferTreatment::HouseholdIncomeSupport,
                AccountId::Household(_)
            ) | (
                PublicTransferTreatment::ProviderOperatingGrant,
                AccountId::Site(_)
            ) | (
                PublicTransferTreatment::AgencyAppropriation,
                AccountId::Organization(_)
            )
        );
        if !valid || !budgets.contains(&r.public_account) || r.amount_per_period.micro_units() <= 0
        {
            return Err(MaterialCircuitError::FinancialInvariant);
        }
    }
    for r in &f.taxes {
        book.cash(r.payer)?;
        book.cash(AccountId::Public(r.public_recipient))?;
        if r.payer == AccountId::Public(r.public_recipient)
            || r.rate_bps > 10_000
            || r.cash_floor.micro_units() < 0
        {
            return Err(MaterialCircuitError::FinancialInvariant);
        }
    }
    Ok(())
}
/// Keys unique, payer in proportion, recipients household accounts; per person, each with a cohort.
fn validate_programs(state: &MaterialCircuitState, f: &FinancialInstitutions) -> Result<()> {
    let CircuitAccounting::Monetary(e) = &state.accounting else {
        return Ok(());
    };
    let invalid = MaterialCircuitError::PublicProgramInvariant;
    if f.programs.len() > MAX_PUBLIC_PROGRAMS {
        return Err(invalid);
    }
    let cohort_ids: BTreeSet<_> = e
        .recurring
        .iter()
        .flat_map(|r| r.households.iter().map(|h| h.principal_id))
        .collect();
    let mut keys = BTreeSet::new();
    let mut after_layoff = BTreeSet::new();
    let mut recipients = 0_usize;
    for program in &f.programs {
        let in_proportion = f.public_budgets.iter().any(|b| {
            b.public_account == program.payer && b.rule == PublicSpendingRule::CashInProportion
        });
        let mut seen = BTreeSet::new();
        recipients = recipients.saturating_add(program.recipients.len());
        if !keys.insert(&program.key)
            || !in_proportion
            || program.recipients.is_empty()
            || program.recipients.iter().any(|r| !seen.insert(*r))
            || program
                .recipients
                .iter()
                .any(|r| e.book.cash(AccountId::Household(*r)).is_err())
        {
            return Err(invalid);
        }
        let own_ok = match program.terms {
            PublicProgramTerms::PerPersonOwn { share_bps } => {
                (1..=MAX_PROGRAM_SHARE_BPS).contains(&share_bps)
                    && program.own_amounts.len() == program.recipients.len()
                    && program.own_amounts.iter().all(|a| a.micro_units() > 0)
            }
            _ => program.own_amounts.is_empty(),
        };
        if !own_ok {
            return Err(invalid);
        }
        match program.terms {
            PublicProgramTerms::PerPerson { amount_per_person } => {
                if amount_per_person.micro_units() <= 0
                    || program.recipients.iter().any(|r| !cohort_ids.contains(r))
                {
                    return Err(invalid);
                }
            }
            PublicProgramTerms::PerPersonOwn { .. } => {
                if program.recipients.iter().any(|r| !cohort_ids.contains(r)) {
                    return Err(invalid);
                }
            }
            PublicProgramTerms::AfterLayoff {
                wage_share_bps,
                half_periods,
            } => {
                // A household is a recipient of at most one program of this kind.
                if !(1..=10_000).contains(&wage_share_bps)
                    || !(1..=MAX_LAYOFF_HALF_PERIODS).contains(&half_periods)
                    || program.recipients.iter().any(|r| !after_layoff.insert(*r))
                {
                    return Err(invalid);
                }
            }
        }
    }
    if recipients > MAX_MATERIAL_CIRCUIT_ROWS {
        return Err(invalid);
    }
    validate_layoffs(e, f)
}
/// Records unique and sorted by member, each of a member with a wage: a schedule, one to thirteen
/// cohorts, the last not 0. A record whose payee is no longer a recipient is valid and owed nothing,
/// so a change of programs never makes the state unreadable.
fn validate_layoffs(e: &MonetaryCircuit, f: &FinancialInstitutions) -> Result<()> {
    let invalid = MaterialCircuitError::PublicProgramInvariant;
    if f.layoffs.len() > MAX_STAFFING_MEMBERS {
        return Err(invalid);
    }
    let wage_members: BTreeSet<_> = e
        .employment
        .iter()
        .filter(|t| matches!(t.compensation, LaborCompensation::Wage(_)))
        .map(|t| t.member_id)
        .collect();
    let mut members = BTreeSet::new();
    for record in &f.layoffs {
        if !wage_members.contains(&record.member_id)
            || record.hours_per_person == 0
            || !(1..=MAX_LAYOFF_PERIODS).contains(&record.cohorts.len())
            || record.cohorts.last() == Some(&0)
            || !members.insert(record.member_id)
        {
            return Err(invalid);
        }
    }
    if f.layoffs
        .windows(2)
        .any(|w| w[0].member_id > w[1].member_id)
    {
        return Err(invalid);
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::{validate_layoffs, validate_programs};
    use crate::AccountId;
    use crate::{
        AidBook, CapacityReservations, CashAccount, CircuitAccounting, EmploymentTerms,
        FinalDemandPrincipalId, FinancialInstitutions, HistoricalCostBook, HouseholdCohort,
        HouseholdKind, HouseholdTimeAccounting, LaborCompensation, LayoffRecord,
        MaterialCircuitState, MonetaryBook, MonetaryCircuit, PublicAccountId, PublicBudget,
        PublicProgram, PublicProgramKey, PublicProgramTerms, PublicSpendingRule, RecurringEconomy,
        SiteId, StaffingMemberId, UnitId,
    };
    use babylon_kernel::currency::Currency;

    const N: u16 = 2_000;

    fn bytes(tag: u8, n: u16) -> [u8; 32] {
        let mut b = [tag; 32];
        b[..2].copy_from_slice(&n.to_be_bytes());
        b
    }

    fn state(
        households: &[FinalDemandPrincipalId],
        employment: Vec<EmploymentTerms>,
    ) -> MaterialCircuitState {
        let book = MonetaryBook::open(
            households
                .iter()
                .map(|&h| CashAccount {
                    id: AccountId::Household(h),
                    cash: Currency::from_micro_units(0),
                })
                .collect(),
        )
        .expect("the book opens");
        let costs = HistoricalCostBook::open(&book, vec![], vec![], vec![], vec![])
            .expect("empty costs open");
        let recurring = RecurringEconomy {
            households: households
                .iter()
                .map(|&principal_id| HouseholdCohort {
                    kind: HouseholdKind::Ordinary,
                    principal_id,
                    households: 1,
                    persons: 1,
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
                employment,
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

    /// Two thousand recipients are checked against the cohorts and the book: it finishes. A return of a
    /// scan of every cohort for each recipient is what it is there to catch, not to time.
    #[test]
    fn two_thousand_recipients_validate() {
        let households: Vec<_> = (0..N)
            .map(|n| FinalDemandPrincipalId::from_bytes(bytes(1, n)))
            .collect();
        let state = state(&households, vec![]);
        let payer = PublicAccountId::from_bytes([9; 32]);
        let mut f = FinancialInstitutions::empty();
        f.public_budgets = vec![PublicBudget {
            public_account: payer,
            period_cap: Currency::from_micro_units(0),
            cash_floor: Currency::from_micro_units(0),
            rule: PublicSpendingRule::CashInProportion,
        }];
        f.programs = vec![PublicProgram {
            key: PublicProgramKey::new("p").expect("a key"),
            payer,
            rank: 0,
            terms: PublicProgramTerms::PerPerson {
                amount_per_person: Currency::from_micro_units(1),
            },
            recipients: households,
            own_amounts: vec![],
        }];
        validate_programs(&state, &f).expect("the program validates");
    }

    fn own_state(f: &mut FinancialInstitutions, share_bps: u32, amounts: Vec<i128>) {
        let households: Vec<_> = (0..N)
            .map(|n| FinalDemandPrincipalId::from_bytes(bytes(1, n)))
            .collect();
        let payer = PublicAccountId::from_bytes([9; 32]);
        f.public_budgets = vec![PublicBudget {
            public_account: payer,
            period_cap: Currency::from_micro_units(0),
            cash_floor: Currency::from_micro_units(0),
            rule: PublicSpendingRule::CashInProportion,
        }];
        f.programs = vec![PublicProgram {
            key: PublicProgramKey::new("p").expect("a key"),
            payer,
            rank: 0,
            terms: PublicProgramTerms::PerPersonOwn { share_bps },
            recipients: households,
            own_amounts: amounts
                .into_iter()
                .map(Currency::from_micro_units)
                .collect(),
        }];
    }

    #[test]
    fn tag_3_is_validated() {
        let households: Vec<_> = (0..N)
            .map(|n| FinalDemandPrincipalId::from_bytes(bytes(1, n)))
            .collect();
        let state = state(&households, vec![]);
        let ones = || vec![1_i128; usize::from(N)];
        let mut f = FinancialInstitutions::empty();
        let invalid = Some(crate::MaterialCircuitError::PublicProgramInvariant);
        own_state(&mut f, 10_000, ones());
        validate_programs(&state, &f).expect("one micro each validates");
        for share in [1, 100_000] {
            own_state(&mut f, share, ones());
            validate_programs(&state, &f).expect("the ends of the share validate");
        }
        for share in [0, 100_001] {
            own_state(&mut f, share, ones());
            assert_eq!(validate_programs(&state, &f).err(), invalid);
        }
        let mut with_zero = ones();
        with_zero[0] = 0;
        own_state(&mut f, 10_000, with_zero);
        assert_eq!(validate_programs(&state, &f).err(), invalid);
        let mut short = ones();
        short.pop();
        own_state(&mut f, 10_000, short);
        assert_eq!(validate_programs(&state, &f).err(), invalid);
        own_state(&mut f, 10_000, ones());
        f.programs[0].terms = PublicProgramTerms::PerPerson {
            amount_per_person: Currency::from_micro_units(1),
        };
        f.programs[0].own_amounts.truncate(1);
        assert_eq!(validate_programs(&state, &f).err(), invalid);
    }

    #[test]
    fn amounts_are_sorted_with_their_recipients() {
        let one = FinalDemandPrincipalId::from_bytes(bytes(1, 1));
        let two = FinalDemandPrincipalId::from_bytes(bytes(1, 2));
        let mut f = FinancialInstitutions::empty();
        own_state(&mut f, 10_000, vec![20, 10]);
        f.programs[0].recipients = vec![two, one];
        super::canonicalize(&mut f);
        assert_eq!(f.programs[0].recipients, vec![one, two]);
        assert_eq!(
            f.programs[0].own_amounts,
            vec![
                Currency::from_micro_units(10),
                Currency::from_micro_units(20)
            ]
        );
    }

    /// Two thousand records are checked against the employment rows: it finishes.
    #[test]
    fn two_thousand_records_validate() {
        let employment: Vec<_> = (0..N)
            .map(|n| EmploymentTerms {
                member_id: StaffingMemberId::from_bytes(bytes(2, n)),
                site_id: SiteId::from_bytes([3; 32]),
                unit_id: UnitId::from_bytes([4; 32]),
                payee: FinalDemandPrincipalId::from_bytes(bytes(1, n)),
                compensation: LaborCompensation::Wage(Currency::from_micro_units(10)),
            })
            .collect();
        let mut records: Vec<_> = (0..N)
            .map(|n| LayoffRecord {
                member_id: StaffingMemberId::from_bytes(bytes(2, n)),
                hours_per_person: 1,
                cohorts: vec![1],
            })
            .collect();
        records.sort_by_key(|r| r.member_id);
        let state = state(&[], employment);
        let CircuitAccounting::Monetary(e) = &state.accounting else {
            panic!("monetary")
        };
        let mut f = FinancialInstitutions::empty();
        f.layoffs = records;
        validate_layoffs(e, &f).expect("the records validate");
        f.layoffs.swap(0, 1);
        assert_eq!(
            validate_layoffs(e, &f).err(),
            Some(crate::MaterialCircuitError::PublicProgramInvariant),
            "unsorted records are refused with the one class of refusal"
        );
    }
}
