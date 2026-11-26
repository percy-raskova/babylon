//! The national fund (schema 8): its share of both taxes by part, its place grants, its programs, and what
//! each account's own needs cost at its own sellers' posted prices.
use super::{templates, Builder, NationalOpeningError, Result};
use crate::economic_catalog::EconomicHouseholdSeed;
use crate::national_economy::grain::FinancialDomainId;
use crate::national_economy::{
    GameFundPolicy, GameProgram, GameProgramRecipients, GameProgramTerms,
    MAX_GAME_PROGRAM_SHARE_BPS,
};
use babylon_kernel::content_digest;
use babylon_kernel::currency::Currency;
use babylon_kernel::economic_identity::{EconomicFunction, QcewOwnership};
use babylon_kernel::economic_location::EconomicLocation;
use babylon_kernel::geography::CountyGeoid;
use babylon_material_circuit::{
    AccountId, CashAccount, FinalDemandPrincipalId, GoodId, HouseholdKind, HouseholdNeedBasis,
    InstitutionLocation, PublicAccountId, PublicBudget, PublicProgram, PublicProgramKey,
    PublicProgramTerms, PublicSpendingRule, SiteId, TaxBasis, UnitId, MAX_MATERIAL_CIRCUIT_ROWS,
    MAX_PUBLIC_PROGRAMS,
};
use std::cell::OnceCell;
use std::collections::{BTreeMap, BTreeSet};

// The scenario's bound and the engine's are one figure.
const _: () =
    assert!(MAX_GAME_PROGRAM_SHARE_BPS == babylon_material_circuit::MAX_PROGRAM_SHARE_BPS);

/// Where the fund sits: Washington, District of Columbia.
const FUND_COUNTY: &str = "11001";
/// The county whose City PD keeps its payroll site's grant wholly its own body's.
const CITY_PD_COUNTY: &str = "26163";
const BPS: u128 = 10_000;

/// The priority of a place grant in the fund's budget: above 255, the most a program's rank may be, so a
/// short fund cuts every grant before any program.
pub(in crate::national_economy) const PLACE_GRANT_PRIORITY: u32 = 256;

/// The fund's account: `PublicAccountId::from_bytes(sha256_of(b"NationalFundV1\0"))`.
#[must_use]
pub fn fund_account() -> PublicAccountId {
    PublicAccountId::from_bytes(content_digest::sha256_of(b"NationalFundV1\0"))
}

/// Where the fund sits: county 11001.
///
/// # Errors
/// `Policy` when the county is not a domestic county.
pub(in crate::national_economy) fn fund_location() -> Result<EconomicLocation> {
    county(FUND_COUNTY)
}

fn county(text: &str) -> Result<EconomicLocation> {
    let geoid = CountyGeoid::try_from(text).map_err(|_| NationalOpeningError::Policy)?;
    EconomicLocation::domestic_county(geoid).map_err(|_| NationalOpeningError::Policy)
}

/// A domestic payer's two rows for one tax: the place's share and the fund's.
/// (place, fund): fund = floor(rate x share / `10_000`), place = rate - fund.
pub(super) fn split_rate(rate_bps: u16, fund_share_bps: u16) -> (u16, u16) {
    let share = u32::from(fund_share_bps.min(10_000));
    let fund = (u32::from(rate_bps) * share / 10_000).min(u32::from(rate_bps));
    let fund = u16::try_from(fund).unwrap_or(rate_bps);
    (rate_bps - fund, fund)
}

/// The fund's share of a tax paid in `part` (its label): the part's entry of `share_by_part` when the table
/// is not empty, else the scenario's one share of that basis.
///
/// # Errors
/// `Policy` for a domestic part missing from a table that is not empty.
pub(super) fn fund_share(fund: &GameFundPolicy, part: &str, basis: TaxBasis) -> Result<u16> {
    if fund.share_by_part.is_empty() {
        return Ok(match basis {
            TaxBasis::WageIncome => fund.wage_tax_share_bps,
            TaxBasis::PositiveOperatingIncome => fund.operating_income_tax_share_bps,
        });
    }
    fund.share_by_part
        .get(part)
        .copied()
        .ok_or(NationalOpeningError::Policy)
}

/// The labels of the opening's domestic parts: the domain of every household account and every site that
/// sits in a county.
fn domestic_parts(builder: &Builder<'_>) -> Result<BTreeSet<String>> {
    let mut parts = BTreeSet::new();
    for household in &builder.opening.households {
        if matches!(household.location, EconomicLocation::County(_)) {
            let domain = builder.domain(
                AccountId::Household(household.principal_id),
                household.location,
            )?;
            parts.insert(templates::part_label(domain));
        }
    }
    for site in &builder.opening.sites {
        if matches!(site.location, EconomicLocation::County(_)) {
            let domain = builder.domain(AccountId::Site(site.site_id), site.location)?;
            parts.insert(templates::part_label(domain));
        }
    }
    Ok(parts)
}

/// A table of shares by part that is not empty names every domestic part of the opening and nothing else.
///
/// # Errors
/// `Policy` for a part missing from the table or an entry that names no part.
pub(super) fn check_share_table(builder: &Builder<'_>) -> Result<()> {
    let Some(fund) = &builder.policy.fund else {
        return Ok(());
    };
    if fund.share_by_part.is_empty() {
        return Ok(());
    }
    let parts = domestic_parts(builder)?;
    if parts
        .iter()
        .any(|part| !fund.share_by_part.contains_key(part))
        || fund.share_by_part.keys().any(|part| !parts.contains(part))
    {
        return Err(NationalOpeningError::Policy);
    }
    Ok(())
}

/// The fund's part of each funded public provider's own grant in one part: `row` dealt over the grants in
/// proportion to each, rounded down, then the micros left one each by largest remainder (equal remainders to
/// the lower site id). The parts sum to `row`; each is at most its grant.
///
/// # Errors
/// `Policy` for a row not above 0, above the grants' sum, or over no grant; `Arithmetic` on overflow.
pub(super) fn grant_parts(
    row: Currency,
    grants: &[(SiteId, Currency)],
) -> Result<Vec<(SiteId, Currency)>> {
    let row = row.micro_units();
    let mut total = 0_i128;
    for (_, grant) in grants {
        total = total
            .checked_add(grant.micro_units())
            .ok_or(NationalOpeningError::Arithmetic)?;
    }
    if row <= 0 || grants.is_empty() || row > total || grants.iter().any(|g| g.1.micro_units() < 0)
    {
        return Err(NationalOpeningError::Policy);
    }
    let mut parts = Vec::with_capacity(grants.len());
    let mut remainders = Vec::with_capacity(grants.len());
    let mut dealt = 0_i128;
    for (index, (site, grant)) in grants.iter().enumerate() {
        let product = row
            .checked_mul(grant.micro_units())
            .ok_or(NationalOpeningError::Arithmetic)?;
        let part = product / total;
        dealt += part;
        parts.push((*site, part));
        remainders.push((std::cmp::Reverse(product % total), *site, index));
    }
    remainders.sort_unstable();
    let left = usize::try_from(row - dealt).map_err(|_| NationalOpeningError::Arithmetic)?;
    for (_, _, index) in remainders.into_iter().take(left) {
        parts[index].1 += 1;
    }
    Ok(parts
        .into_iter()
        .map(|(site, part)| (site, Currency::from_micro_units(part)))
        .collect())
}

/// The City PD's payroll site: the local-government public provider in Wayne with the most employee
/// persons. Its grant stays wholly its own body's.
fn payroll_site(builder: &Builder<'_>) -> Result<Option<SiteId>> {
    let wayne = county(CITY_PD_COUNTY)?;
    let mut best: Option<(u64, SiteId)> = None;
    for actor in builder.actors.values() {
        if actor.location != wayne
            || actor.function != EconomicFunction::PublicProvisioning
            || actor.source_ownership != Some(QcewOwnership::LocalGovernment)
        {
            continue;
        }
        if best.is_none_or(|(most, _)| actor.employee_persons > most) {
            best = Some((actor.employee_persons, actor.site_id));
        }
    }
    Ok(best.map(|(_, site)| site))
}

/// What the fund pays each funded provider of the parts that have a place grant: `grants` are every domestic
/// public provider's own grant above 0, with its part's domain.
///
/// # Errors
/// `Policy` for a row over no funded provider or above their grants together; `Arithmetic` on overflow.
pub(super) fn place_grant_parts(
    builder: &Builder<'_>,
    grants: &[(FinancialDomainId, SiteId, Currency)],
) -> Result<BTreeMap<SiteId, Currency>> {
    let mut parts = BTreeMap::new();
    if builder.policy.place_grants.is_empty() {
        return Ok(parts);
    }
    let payroll = payroll_site(builder)?;
    for row in &builder.policy.place_grants {
        let funded: Vec<(SiteId, Currency)> = grants
            .iter()
            .filter(|(domain, site, _)| {
                templates::part_label(*domain) == row.part && Some(*site) != payroll
            })
            .map(|(_, site, grant)| (*site, *grant))
            .collect();
        for (site, part) in grant_parts(row.amount_per_period, &funded)? {
            parts.insert(site, part);
        }
    }
    Ok(parts)
}

/// The programs' recipients, by the household keys of the opening, in principal order.
///
/// # Errors
/// `Identity` for a household account with no budget key.
pub(super) fn recipients(
    builder: &Builder<'_>,
    rule: GameProgramRecipients,
) -> Result<Vec<FinalDemandPrincipalId>> {
    let mut found = Vec::new();
    for household in &builder.opening.households {
        if !matches!(household.location, EconomicLocation::County(_)) {
            continue;
        }
        let key = builder
            .household_keys
            .get(&household.principal_id)
            .ok_or(NationalOpeningError::Identity)?;
        let hit = match rule {
            GameProgramRecipients::NoEarnerAtOpening => matches!(
                key,
                crate::national_household_allocation::HouseholdBudgetKey::NoEarnerNonowner
                    | crate::national_household_allocation::HouseholdBudgetKey::NoEarnerOwner
            ),
            GameProgramRecipients::EarningOrResidenceAtOpening => key.earning() || key.collective(),
            GameProgramRecipients::CollectiveResidenceAtOpening => key.collective(),
        };
        if hit {
            found.push(household.principal_id);
        }
    }
    found.sort_unstable();
    Ok(found)
}

/// Indices of the opening's final rows, built once when the programs are worked out.
#[derive(Default)]
pub(super) struct Indices {
    purchases: OnceCell<BTreeMap<(FinalDemandPrincipalId, GoodId, UnitId), SiteId>>,
    staffed: OnceCell<Staffed>,
}

/// What the staffing members hold, by account: persons looking for work by (household, residence), and
/// persons at work by household.
#[derive(Default)]
struct Staffed {
    reserve: BTreeMap<(FinalDemandPrincipalId, EconomicLocation), u64>,
    employed: BTreeMap<FinalDemandPrincipalId, u64>,
}

fn add_count<K: Ord>(map: &mut BTreeMap<K, u64>, key: K, count: u64) -> Result<()> {
    let held = map.entry(key).or_default();
    *held = held
        .checked_add(count)
        .ok_or(NationalOpeningError::Arithmetic)?;
    Ok(())
}

fn staffed<'a>(builder: &'a Builder<'_>) -> Result<&'a Staffed> {
    if let Some(staffed) = builder.fund_indices.staffed.get() {
        return Ok(staffed);
    }
    let mut staffed = Staffed::default();
    for member in builder
        .opening
        .staffing
        .iter()
        .flat_map(|pool| &pool.members)
    {
        add_count(
            &mut staffed.reserve,
            (member.member.household_id(), member.member.residence()),
            member.reserve,
        )?;
        add_count(
            &mut staffed.employed,
            member.member.household_id(),
            member.employed,
        )?;
    }
    Ok(builder.fund_indices.staffed.get_or_init(|| staffed))
}

fn purchases<'a>(
    builder: &'a Builder<'_>,
) -> &'a BTreeMap<(FinalDemandPrincipalId, GoodId, UnitId), SiteId> {
    builder.fund_indices.purchases.get_or_init(|| {
        builder
            .opening
            .policies
            .household_purchases
            .iter()
            .map(|row| {
                (
                    (row.principal_id, row.good_id, row.unit_id),
                    row.retailer_site_id,
                )
            })
            .collect()
    })
}

/// What a household account's needs cost a period at its own sellers' posted opening prices: over the
/// scenario's `household_needs` (a residence's on a person basis only), each need's units for the account's
/// persons or households times the opening `unit_price` of its purchase row's seller of that product.
///
/// # Errors
/// `Policy` for a need with no purchase row or no offer of its seller; `Arithmetic` on overflow.
pub(super) fn needs_cost(
    builder: &Builder<'_>,
    household: &EconomicHouseholdSeed,
) -> Result<Currency> {
    let collective = household.kind == HouseholdKind::CollectiveResidence;
    let mut cost = Currency::from_micro_units(0);
    for need in &builder.policy.household_needs {
        if collective && need.basis == HouseholdNeedBasis::Households {
            continue;
        }
        let count = match need.basis {
            HouseholdNeedBasis::Persons => household.persons,
            HouseholdNeedBasis::Households => household.households,
        };
        let units = super::quantity(count, need.units_per_basis)?;
        let good = builder.commodity(&need.key)?;
        let seller = purchases(builder)
            .get(&(household.principal_id, good.good_id, good.unit_id))
            .ok_or(NationalOpeningError::Policy)?;
        let offer = builder
            .offer(*seller, good.good_id, good.unit_id)
            .ok_or(NationalOpeningError::Policy)?;
        cost = super::sum_amount(cost, super::amount(units, offer.unit_price)?)?;
    }
    Ok(cost)
}

/// What county support pays the account a period at the opening: its `reserve` persons (summed over the
/// staffing members whose household and residence are the account's, as `financial::wire` sums them) times
/// `county_support_unit_price`. 0 with no reserve person.
///
/// # Errors
/// `Policy` for a scenario with no food price; `Arithmetic` on overflow.
pub(super) fn county_support(
    builder: &Builder<'_>,
    household: &EconomicHouseholdSeed,
) -> Result<Currency> {
    if builder.policy.financial.reserve_food_support_periods == 0 {
        return Ok(Currency::from_micro_units(0));
    }
    let reserve = staffed(builder)?
        .reserve
        .get(&(household.principal_id, household.location))
        .copied()
        .unwrap_or(0);
    if reserve == 0 {
        return Ok(Currency::from_micro_units(0));
    }
    super::amount(
        reserve,
        super::financial::county_support_unit_price(builder.policy)?,
    )
}

/// The account's own amount a person, from its figures alone: `cost` its needs' cost, `support` its county
/// support, `persons`, and `jobless` (for a residence; `None` for a no-earner account). A no-earner
/// account's is `max(1, ceil((cost - support) / persons))`; a residence's, with `J` its jobless residents,
/// `max(1, ceil((cost x J - support x persons) / persons^2))`. `None` when it is no recipient: no persons,
/// or a residence with no jobless resident.
///
/// # Errors
/// `Arithmetic` on overflow.
pub(super) fn own_need_amount(
    cost: Currency,
    support: Currency,
    persons: u64,
    jobless: Option<u64>,
) -> Result<Option<Currency>> {
    if persons == 0 || jobless == Some(0) {
        return Ok(None);
    }
    let overflow = || NationalOpeningError::Arithmetic;
    let (cost, support) = (cost.micro_units(), support.micro_units());
    let people = i128::from(persons);
    let (owed, divisor) = match jobless {
        None => (cost.checked_sub(support).ok_or_else(overflow)?, people),
        Some(jobless) => (
            cost.checked_mul(i128::from(jobless))
                .and_then(|c| c.checked_sub(support.checked_mul(people)?))
                .ok_or_else(overflow)?,
            people.checked_mul(people).ok_or_else(overflow)?,
        ),
    };
    let per_person = if owed <= 0 {
        1
    } else {
        // ceil(owed / divisor), owed and divisor above 0
        ((owed - 1) / divisor).checked_add(1).ok_or_else(overflow)?
    };
    Ok(Some(Currency::from_micro_units(per_person.max(1))))
}

/// `own_need_amount` on the account's `needs_cost`, `county_support`, persons and, for a residence, its
/// persons with no job at the opening (`persons` less the `employed` of the staffing members whose household
/// is the account).
///
/// # Errors
/// As the figures it reads and `own_need_amount`; `Arithmetic` for a residence with more at work than persons.
pub(super) fn own_amount(
    builder: &Builder<'_>,
    household: &EconomicHouseholdSeed,
    residence: bool,
) -> Result<Option<Currency>> {
    if household.persons == 0 {
        return Ok(None);
    }
    let jobless = if residence {
        let at_work = staffed(builder)?
            .employed
            .get(&household.principal_id)
            .copied()
            .unwrap_or(0);
        Some(
            household
                .persons
                .checked_sub(at_work)
                .ok_or(NationalOpeningError::Arithmetic)?,
        )
    } else {
        None
    };
    if jobless == Some(0) {
        return Ok(None);
    }
    own_need_amount(
        needs_cost(builder, household)?,
        county_support(builder, household)?,
        household.persons,
        jobless,
    )
}

/// One program as the engine holds it, with what it owes a period at the opening.
struct Compiled {
    program: PublicProgram,
    due: i128,
}

fn compile_program(
    builder: &Builder<'_>,
    game: &GameProgram,
    households: &BTreeMap<FinalDemandPrincipalId, &EconomicHouseholdSeed>,
) -> Result<Option<Compiled>> {
    let key = PublicProgramKey::new(&game.key).map_err(|_| NationalOpeningError::Policy)?;
    let ids = recipients(builder, game.recipients)?;
    let persons = |id: &FinalDemandPrincipalId| -> Result<u64> {
        households
            .get(id)
            .map(|household| household.persons)
            .ok_or(NationalOpeningError::Identity)
    };
    let mut due = 0_i128;
    let (terms, recipients, own_amounts) = match game.terms {
        GameProgramTerms::PerPerson { amount_per_person } => {
            for id in &ids {
                let owed = amount_per_person
                    .micro_units()
                    .checked_mul(i128::from(persons(id)?))
                    .ok_or(NationalOpeningError::Arithmetic)?;
                due = due
                    .checked_add(owed)
                    .ok_or(NationalOpeningError::Arithmetic)?;
            }
            (
                PublicProgramTerms::PerPerson { amount_per_person },
                ids,
                vec![],
            )
        }
        GameProgramTerms::AfterLayoff {
            wage_share_bps,
            half_periods,
        } => (
            PublicProgramTerms::AfterLayoff {
                wage_share_bps,
                half_periods,
            },
            ids,
            vec![],
        ),
        GameProgramTerms::OwnNeeds { share_bps } => {
            let residence = game.recipients == GameProgramRecipients::CollectiveResidenceAtOpening;
            let mut kept = Vec::new();
            let mut amounts = Vec::new();
            for id in ids {
                let household = households.get(&id).ok_or(NationalOpeningError::Identity)?;
                let Some(own) = own_amount(builder, household, residence)? else {
                    continue;
                };
                let owed = u128::try_from(own.micro_units())
                    .ok()
                    .and_then(|own| own.checked_mul(u128::from(household.persons)))
                    .and_then(|n| n.checked_mul(u128::from(share_bps)))
                    .map(|n| n / BPS)
                    .and_then(|n| i128::try_from(n).ok())
                    .ok_or(NationalOpeningError::Arithmetic)?;
                due = due
                    .checked_add(owed)
                    .ok_or(NationalOpeningError::Arithmetic)?;
                kept.push(id);
                amounts.push(own);
            }
            (
                PublicProgramTerms::PerPersonOwn { share_bps },
                kept,
                amounts,
            )
        }
    };
    if recipients.is_empty() {
        return Ok(None);
    }
    Ok(Some(Compiled {
        program: PublicProgram {
            key,
            payer: fund_account(),
            rank: game.rank,
            terms,
            recipients,
            own_amounts,
        },
        due,
    }))
}

/// The fund's account, budget, location, opening cash and programs. Runs after `financial::wire`, so after
/// every offer of the opening is final.
///
/// # Errors
/// `Policy`, `Identity`, `Bounds` or `Arithmetic` as the decisions of the opening say.
pub(super) fn wire(builder: &mut Builder<'_>) -> Result<()> {
    let Some(fund) = builder.policy.fund.clone() else {
        return Ok(());
    };
    let households: BTreeMap<_, _> = builder
        .opening
        .households
        .iter()
        .map(|household| (household.principal_id, household))
        .collect();
    let mut programs = Vec::new();
    let mut dues = 0_i128;
    for game in &builder.policy.programs {
        if let Some(compiled) = compile_program(builder, game, &households)? {
            dues = dues
                .checked_add(compiled.due)
                .ok_or(NationalOpeningError::Arithmetic)?;
            programs.push(compiled.program);
        }
    }
    programs.sort_by(|a, b| a.key.cmp(&b.key));
    let recipient_rows = programs
        .iter()
        .try_fold(0_usize, |sum, p| sum.checked_add(p.recipients.len()))
        .ok_or(NationalOpeningError::Arithmetic)?;
    if programs.len() > MAX_PUBLIC_PROGRAMS || recipient_rows > MAX_MATERIAL_CIRCUIT_ROWS {
        return Err(NationalOpeningError::Bounds);
    }
    let account = fund_account();
    let mut payments = dues;
    for row in &builder.opening.institutions.public_allocations {
        if row.public_account == account {
            payments = payments
                .checked_add(row.amount_per_period.micro_units())
                .ok_or(NationalOpeningError::Arithmetic)?;
        }
    }
    let cash = payments
        .checked_mul(i128::from(fund.reserve_periods))
        .ok_or(NationalOpeningError::Arithmetic)?;
    let opening = &mut builder.opening;
    opening.institutional_cash.push(CashAccount {
        id: AccountId::Public(account),
        cash: Currency::from_micro_units(cash),
    });
    opening.institutions.locations.push(InstitutionLocation {
        account: AccountId::Public(account),
        location: fund_location()?,
    });
    opening.institutions.public_budgets.push(PublicBudget {
        public_account: account,
        period_cap: Currency::from_micro_units(0),
        cash_floor: Currency::from_micro_units(0),
        rule: PublicSpendingRule::CashInProportion,
    });
    opening.institutions.programs = programs;
    opening
        .institutions
        .taxes
        .sort_unstable_by_key(|row| (row.payer, row.basis, row.public_recipient));
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn micros(value: i128) -> Currency {
        Currency::from_micro_units(value)
    }

    fn site(id: u8) -> SiteId {
        SiteId::from_bytes([id; 32])
    }

    #[test]
    fn split_rate_keeps_each_rate() {
        assert_eq!(split_rate(2320, 2530), (1734, 586));
        assert_eq!(split_rate(1, 5000), (1, 0));
        for rate in 0..=10_000_u16 {
            for share in [0_u16, 2530, 10_000] {
                let (place, fund) = split_rate(rate, share);
                assert_eq!(place + fund, rate, "{rate} at {share}");
            }
        }
    }

    #[test]
    fn grant_parts_follow_each_grant() {
        let dollars = |n: i128| micros(n * 1_000_000);
        let amounts = |parts: Result<Vec<(SiteId, Currency)>>| -> Vec<i128> {
            parts
                .expect("parts")
                .iter()
                .map(|(_, part)| part.micro_units())
                .collect()
        };
        let grants = [
            (site(1), dollars(60)),
            (site(2), dollars(30)),
            (site(3), dollars(10)),
        ];
        assert_eq!(
            amounts(grant_parts(dollars(100), &grants)),
            [60_000_000, 30_000_000, 10_000_000]
        );
        let three = [
            (site(1), micros(3)),
            (site(2), micros(3)),
            (site(3), micros(3)),
        ];
        assert_eq!(amounts(grant_parts(micros(5), &three)), [2, 2, 1]);
        assert_eq!(amounts(grant_parts(micros(9), &three)), [3, 3, 3]);
        assert_eq!(
            grant_parts(micros(10), &three),
            Err(NationalOpeningError::Policy)
        );
        assert_eq!(
            grant_parts(micros(0), &three),
            Err(NationalOpeningError::Policy)
        );
        assert_eq!(
            grant_parts(micros(1), &[]),
            Err(NationalOpeningError::Policy)
        );
        let two = [(site(1), micros(5)), (site(2), micros(2))];
        assert_eq!(amounts(grant_parts(micros(7), &two)), [5, 2]);
    }

    fn fund_policy(table: &[(&str, u16)]) -> GameFundPolicy {
        GameFundPolicy {
            wage_tax_share_bps: 1_000,
            operating_income_tax_share_bps: 2_000,
            reserve_periods: 2,
            share_by_part: table.iter().map(|(k, v)| ((*k).to_owned(), *v)).collect(),
        }
    }

    #[test]
    fn fund_share_reads_the_part() {
        let plain = fund_policy(&[]);
        assert_eq!(fund_share(&plain, "26163", TaxBasis::WageIncome), Ok(1_000));
        assert_eq!(
            fund_share(&plain, "26163", TaxBasis::PositiveOperatingIncome),
            Ok(2_000)
        );
        let table = fund_policy(&[("26163", 2600)]);
        assert_eq!(fund_share(&table, "26163", TaxBasis::WageIncome), Ok(2_600));
        assert_eq!(
            fund_share(&table, "26163", TaxBasis::PositiveOperatingIncome),
            Ok(2_600)
        );
        assert_eq!(
            fund_share(&table, "01073/below", TaxBasis::WageIncome),
            Err(NationalOpeningError::Policy)
        );
    }

    #[test]
    fn own_needs_follow_the_prices() {
        // 30 units at 7 micros and 2 units a household at 5 micros: 220 micros for 4 persons.
        let cost = micros(30 * 7 + 2 * 5);
        let own = |cost, support, persons, jobless| {
            own_need_amount(micros(cost), micros(support), persons, jobless)
                .expect("no overflow")
                .map(Currency::micro_units)
        };
        assert_eq!(own(220, 0, 4, None), Some(55));
        assert_eq!(cost, micros(220));
        assert_eq!(own(220, 60, 4, None), Some(40));
        assert_eq!(40 * 4 + 60, 220);
        assert_eq!(own(220, 60, 3, None), Some(54));
        assert_eq!(54 * 3 + 60, 222);
        assert_eq!(own(50, 60, 4, None), Some(1));
        assert_eq!(own(1_000, 0, 10, Some(3)), Some(30));
        assert_eq!(own(1_000, 60, 10, Some(3)), Some(24));
        assert_eq!(own(220, 0, 0, None), None);
        assert_eq!(own(1_000, 0, 10, Some(0)), None);
        assert_eq!(
            own_need_amount(micros(i128::MAX), micros(0), 2, Some(2)),
            Err(NationalOpeningError::Arithmetic)
        );
    }
}
