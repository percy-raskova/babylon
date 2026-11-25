//! The national fund of the country bench, added to the opening in memory (benefits plan B, items 1 to
//! 5): one public account (opening with no cash) that takes half of every domestic tax rate and pays two programs, `no_earner`
//! and `laid_off`. Nothing here pays anyone at the opening, gives a foreign region a program or makes
//! money.
use super::country_bench::{BenchError, BenchPeriod};
use babylon_kernel::content_digest;
use babylon_kernel::currency::Currency;
use babylon_kernel::economic_location::EconomicLocation;
use babylon_kernel::geography::CountyGeoid;
use babylon_material_circuit::{
    AccountId, CashAccount, FinalDemandPrincipalId, InstitutionLocation, PublicAccountId,
    PublicBudget, PublicProgram, PublicProgramKey, PublicProgramTerms, PublicSpendingRule,
    TaxPolicy, MAX_TAX_POLICIES,
};
use babylon_persistence::economic_catalog::{EconomicCatalogError, EconomicOpening};
use std::collections::{BTreeMap, BTreeSet};

/// The `no_earner` program's key.
pub const NO_EARNER: &str = "no_earner";
/// The `laid_off` program's key.
pub const LAID_OFF: &str = "laid_off";

/// Washington, District of Columbia.
const FUND_COUNTY: &str = "11001";
/// Half periods of the `laid_off` program, and the share of the lost pay it pays, in basis points.
const LAID_OFF_HALF_PERIODS: u16 = 13;
const LAID_OFF_SHARE_BPS: u16 = 5_000;

fn refused(what: &'static str) -> BenchError {
    BenchError::Opening(EconomicCatalogError::Opening(what))
}

fn overflow() -> BenchError {
    BenchError::Arithmetic { period: 0 }
}

/// The fund's account: the first 32 bytes of `sha256_of(b"CountryBenchNationalFundV1\0")`.
pub fn fund_account() -> PublicAccountId {
    PublicAccountId::from_bytes(content_digest::sha256_of(b"CountryBenchNationalFundV1\0"))
}

/// Where the fund sits: Washington, District of Columbia (county 11001).
///
/// # Errors
/// `BenchError::Opening` when the geoid is not a domestic county.
pub fn fund_location() -> Result<EconomicLocation, BenchError> {
    let geoid = CountyGeoid::try_from(FUND_COUNTY)
        .map_err(|_| refused("the fund's county is not a county geoid"))?;
    EconomicLocation::domestic_county(geoid)
        .map_err(|_| refused("the fund's county is not a domestic county"))
}

/// Whether a location is a domestic county.
const fn is_domestic(location: EconomicLocation) -> bool {
    matches!(location, EconomicLocation::County(_))
}

/// The location of each account that pays tax: households and sites.
fn payer_locations(opening: &EconomicOpening) -> BTreeMap<AccountId, EconomicLocation> {
    let mut locations = BTreeMap::new();
    for household in &opening.households {
        locations.insert(
            AccountId::Household(household.principal_id),
            household.location,
        );
    }
    for site in &opening.sites {
        locations.insert(AccountId::Site(site.site_id), site.location);
    }
    locations
}

/// Each tax row of a domestic payer, as two: the place's body at the rate less its half, and the fund at
/// the half rounded down. A row of rate 0 or 1 keeps one row.
fn split_taxes(
    opening: &EconomicOpening,
    fund: PublicAccountId,
) -> Result<Vec<TaxPolicy>, BenchError> {
    let locations = payer_locations(opening);
    let mut taxes = Vec::with_capacity(opening.institutions.taxes.len().saturating_mul(2));
    for row in &opening.institutions.taxes {
        let domestic = locations.get(&row.payer).copied().is_some_and(is_domestic);
        let half = row.rate_bps / 2;
        if !domestic || half == 0 {
            taxes.push(row.clone());
            continue;
        }
        taxes.push(TaxPolicy {
            rate_bps: row.rate_bps - half,
            ..row.clone()
        });
        taxes.push(TaxPolicy {
            public_recipient: fund,
            rate_bps: half,
            ..row.clone()
        });
    }
    taxes.sort_unstable_by_key(|row| (row.payer, row.basis, row.public_recipient));
    if taxes.len() >= MAX_TAX_POLICIES {
        return Err(refused("the split taxes pass the bound of tax policies"));
    }
    println!(
        "the fund's split: {} tax rows became {}",
        opening.institutions.taxes.len(),
        taxes.len()
    );
    Ok(taxes)
}

/// The recipients of the two programs: `(no_earner, laid_off)`, each sorted. A household account of the
/// opening is domestic when it sits in a county. It is on `no_earner` when none of its members has anyone
/// employed (an account with no member at all is among them), and on `laid_off` otherwise.
fn recipients(
    opening: &EconomicOpening,
) -> Result<(Vec<FinalDemandPrincipalId>, Vec<FinalDemandPrincipalId>), BenchError> {
    let mut employed: BTreeMap<FinalDemandPrincipalId, u64> = BTreeMap::new();
    for member in opening.staffing.iter().flat_map(|pool| &pool.members) {
        let held = employed.entry(member.member.household_id()).or_default();
        *held = held.checked_add(member.employed).ok_or_else(overflow)?;
    }
    let mut no_earner = Vec::new();
    let mut laid_off = Vec::new();
    for household in opening
        .households
        .iter()
        .filter(|household| is_domestic(household.location))
    {
        if employed.get(&household.principal_id).copied().unwrap_or(0) == 0 {
            no_earner.push(household.principal_id);
        } else {
            laid_off.push(household.principal_id);
        }
    }
    no_earner.sort_unstable();
    laid_off.sort_unstable();
    Ok((no_earner, laid_off))
}

/// The persons of the domestic household accounts of a list.
fn persons_of(
    opening: &EconomicOpening,
    accounts: &BTreeSet<FinalDemandPrincipalId>,
) -> Result<u64, BenchError> {
    opening
        .households
        .iter()
        .filter(|household| accounts.contains(&household.principal_id))
        .try_fold(0_u64, |sum, household| sum.checked_add(household.persons))
        .ok_or_else(overflow)
}

/// The persons of the `no_earner` recipients.
fn no_earner_persons(opening: &EconomicOpening) -> Result<u64, BenchError> {
    let (no_earner, _) = recipients(opening)?;
    persons_of(opening, &no_earner.into_iter().collect())
}

/// The `no_earner` amount: the baseline's first-period spend on needs, per domestic person. The need is
/// `required_quantity x unit_price` of each household demand row and `requested_quantity x unit_price` of
/// each service row bought by a domestic household account, divided by those accounts' persons, rounded
/// down. A stand-in figure of the bench.
///
/// # Errors
/// `BenchError::Opening` when no domestic person is found or the arithmetic overflows.
pub fn no_earner_per_person(
    opening: &EconomicOpening,
    first: &BenchPeriod,
) -> Result<Currency, BenchError> {
    let domestic: BTreeSet<FinalDemandPrincipalId> = opening
        .households
        .iter()
        .filter(|household| is_domestic(household.location))
        .map(|household| household.principal_id)
        .collect();
    let persons = persons_of(opening, &domestic)?;
    if persons == 0 {
        return Err(refused("the domestic accounts hold no person"));
    }
    let mut need = 0_i128;
    let goods = first
        .receipts
        .household_demand
        .iter()
        .filter(|row| domestic.contains(&row.principal_id))
        .map(|row| (row.required_quantity, row.unit_price));
    let services = first
        .receipts
        .service_performance
        .iter()
        .filter(|row| match row.buyer {
            AccountId::Household(principal) => domestic.contains(&principal),
            _ => false,
        })
        .map(|row| (row.requested_quantity, row.unit_price));
    for (quantity, price) in goods.chain(services) {
        let cost = i128::from(quantity)
            .checked_mul(price.micro_units())
            .ok_or_else(overflow)?;
        need = need.checked_add(cost).ok_or_else(overflow)?;
    }
    let share = need / i128::from(persons);
    println!(
        "the no_earner amount: {share} micros a person ({need} micros over {persons} persons)"
    );
    Ok(Currency::from_micro_units(share))
}

/// What one period of the `no_earner` benefit costs: the amount times the persons of its recipients at the
/// opening. The fund opens with none of it; it pays from its half of the taxes as they come in.
///
/// # Errors
/// `BenchError::Arithmetic` when the product overflows.
pub fn no_earner_due_a_period(
    opening: &EconomicOpening,
    per_person: Currency,
) -> Result<i128, BenchError> {
    let persons = no_earner_persons(opening)?;
    per_person
        .micro_units()
        .checked_mul(i128::from(persons))
        .ok_or_else(overflow)
}

/// The cash the domestic public bodies hold between them at the opening.
///
/// # Errors
/// `BenchError::Arithmetic` when the sum overflows.
pub fn public_bodies_cash(opening: &EconomicOpening) -> Result<i128, BenchError> {
    let domestic_bodies: BTreeSet<AccountId> = opening
        .institutions
        .locations
        .iter()
        .filter(|row| matches!(row.account, AccountId::Public(_)) && is_domestic(row.location))
        .map(|row| row.account)
        .collect();
    opening
        .institutional_cash
        .iter()
        .filter(|row| domestic_bodies.contains(&row.id))
        .try_fold(0_i128, |sum, row| sum.checked_add(row.cash.micro_units()))
        .ok_or_else(overflow)
}

/// The opening with the fund (benefits plan B items 1 to 5). `per_person` is the `no_earner` amount.
///
/// # Errors
/// `BenchError::Opening` when a program key is refused; `BenchError::Arithmetic` when the arithmetic overflows.
pub fn with_fund(
    opening: &EconomicOpening,
    per_person: Currency,
) -> Result<EconomicOpening, BenchError> {
    let fund = fund_account();
    let mut funded = opening.clone();
    funded.institutions.taxes = split_taxes(opening, fund)?;
    funded.institutional_cash.push(CashAccount {
        id: AccountId::Public(fund),
        cash: Currency::from_micro_units(0),
    });
    funded.institutional_cash.sort_unstable_by_key(|row| row.id);
    funded.institutions.locations.push(InstitutionLocation {
        account: AccountId::Public(fund),
        location: fund_location()?,
    });
    funded
        .institutions
        .locations
        .sort_unstable_by_key(|row| row.account);
    funded.institutions.public_budgets.push(PublicBudget {
        public_account: fund,
        period_cap: Currency::from_micro_units(0),
        cash_floor: Currency::from_micro_units(0),
        rule: PublicSpendingRule::CashInProportion,
    });
    funded
        .institutions
        .public_budgets
        .sort_unstable_by_key(|row| row.public_account);
    let (no_earner, laid_off) = recipients(opening)?;
    let key = |text: &str| {
        PublicProgramKey::new(text).map_err(|_| refused("a program key of the fund is refused"))
    };
    let mut programs = Vec::new();
    if !no_earner.is_empty() {
        programs.push(PublicProgram {
            key: key(NO_EARNER)?,
            payer: fund,
            rank: 0,
            terms: PublicProgramTerms::PerPerson {
                amount_per_person: per_person,
            },
            recipients: no_earner,
        });
    }
    if !laid_off.is_empty() {
        programs.push(PublicProgram {
            key: key(LAID_OFF)?,
            payer: fund,
            rank: 0,
            terms: PublicProgramTerms::AfterLayoff {
                wage_share_bps: LAID_OFF_SHARE_BPS,
                half_periods: LAID_OFF_HALF_PERIODS,
            },
            recipients: laid_off,
        });
    }
    programs.sort_by(|a, b| a.key.cmp(&b.key));
    funded.institutions.programs = programs;
    Ok(funded)
}

/// The two programs' recipients of an opening with the fund, by key.
pub fn program_recipients(
    opening: &EconomicOpening,
) -> BTreeMap<String, Vec<FinalDemandPrincipalId>> {
    opening
        .institutions
        .programs
        .iter()
        .map(|program| (program.key.as_str().to_owned(), program.recipients.clone()))
        .collect()
}
