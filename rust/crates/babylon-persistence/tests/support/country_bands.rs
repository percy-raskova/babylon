//! The bands of the twelve trades' country, read from the bench: which household account is which band,
//! what each band holds at the opening (jobs, pay) and what each band is paid, owed and holds in a period.
//!
//! A band is a household account's budget key (`HouseholdBudgetKey::label()`). The key of each domestic
//! account is read from the capture's own generation witness; an account carved from another (an aid donor,
//! the support claimant) is counted under its parent's key. Accounts abroad and in dependencies are not read.
use babylon_material_circuit::{
    AccountId, FinalDemandPrincipalId, LaborCompensation, MaterialCircuitState, MoneyLocation,
    MoneyTransferPurpose, MoneyTransferReceipt, PoolMembers, PublicProgramReceipt,
    StaffingMemberId,
};
use babylon_persistence::economic_catalog::{
    CapturedEconomicCatalog, EconomicCatalogError, EconomicOpening,
};
use babylon_persistence::national_household_allocation::HouseholdBudgetKey;
use serde_json::{json, Map, Value};
use std::collections::{BTreeMap, BTreeSet};

use super::country_bench::BenchError;
use super::economy_health;

/// The six keys a band's row may carry, in the order the legend names them.
pub const KEYS: [HouseholdBudgetKey; 6] = [
    HouseholdBudgetKey::EarningLowerPaidHalf,
    HouseholdBudgetKey::EarningBetterPaidForty,
    HouseholdBudgetKey::EarningOwner,
    HouseholdBudgetKey::NoEarnerNonowner,
    HouseholdBudgetKey::NoEarnerOwner,
    HouseholdBudgetKey::CollectiveResidence,
];

/// One domestic account: its band and its place (the hub county's geoid).
#[derive(Clone, Debug)]
struct Account {
    key: HouseholdBudgetKey,
    place: String,
}

/// Which band each household account of the opening is in; `None` for an account abroad or in a dependency.
pub struct Bands {
    accounts: BTreeMap<FinalDemandPrincipalId, Option<Account>>,
}

fn refused(what: &'static str) -> BenchError {
    BenchError::Opening(EconomicCatalogError::Opening(what))
}

impl Bands {
    /// Reads every household account of the capture's opening.
    ///
    /// # Errors
    /// `BenchError::Opening` when the capture holds no generation witness or an account has two keys;
    /// `BenchError::UnknownBand` when a domestic account's key cannot be found.
    pub fn read(catalog: &CapturedEconomicCatalog) -> Result<Self, BenchError> {
        let witness = catalog
            .national_generation()
            .ok_or_else(|| refused("the capture holds no generation witness"))?;
        let mut keys = BTreeMap::<FinalDemandPrincipalId, HouseholdBudgetKey>::new();
        for row in &witness.household_incidence {
            let key = row.margins.key;
            if *keys.entry(row.destination).or_insert(key) != key {
                return Err(refused("an account is in two bands"));
            }
        }
        let mut carved: Vec<(FinalDemandPrincipalId, FinalDemandPrincipalId)> = catalog
            .national_aid_capture()
            .map(|aid| {
                aid.children
                    .iter()
                    .map(|c| (c.principal, c.parent))
                    .collect()
            })
            .unwrap_or_default();
        if let Some(claimant) = catalog.national_support_claimant() {
            carved.push((claimant.principal, claimant.parent));
        }
        for (child, parent) in carved {
            let key = *keys
                .get(&parent)
                .ok_or(BenchError::UnknownBand { principal: child })?;
            keys.insert(child, key);
        }
        let mut accounts = BTreeMap::new();
        for row in &catalog.opening().households {
            let location = row.location.to_string();
            let account = match location.strip_prefix("county:") {
                Some(place) if economy_health::scope(&location) == "domestic" => {
                    let key = *keys.get(&row.principal_id).ok_or(BenchError::UnknownBand {
                        principal: row.principal_id,
                    })?;
                    Some(Account {
                        key,
                        place: place.to_owned(),
                    })
                }
                _ if economy_health::scope(&location) == "domestic" => {
                    return Err(refused("a domestic account is not in a county"));
                }
                _ => None,
            };
            accounts.insert(row.principal_id, account);
        }
        Ok(Self { accounts })
    }

    /// The account's band and place; `None` for an account abroad or in a dependency.
    fn account(&self, principal: FinalDemandPrincipalId) -> Result<Option<&Account>, BenchError> {
        self.accounts
            .get(&principal)
            .map(Option::as_ref)
            .ok_or(BenchError::UnknownBand { principal })
    }

    /// The domestic accounts' principals with their bands.
    fn domestic(&self) -> impl Iterator<Item = (FinalDemandPrincipalId, HouseholdBudgetKey)> + '_ {
        self.accounts
            .iter()
            .filter_map(|(principal, account)| account.as_ref().map(|a| (*principal, a.key)))
    }
}

/// What one band holds in one place, or in the nation, at the opening.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct Held {
    pub accounts: u64,
    pub households: u64,
    pub persons: u64,
    pub employed_persons: u64,
    pub looking_persons: u64,
    /// The employed persons of the members whose compensation is a wage (a working owner and an unpaid
    /// member of a family are at work and draw none).
    pub waged_persons: u64,
    /// One period's wages: wage times employed persons times hours a person, over the members paid a wage.
    pub wage_bill_micros: i128,
}

impl Held {
    /// The figures in the legend's order, money as a string as the records write it.
    fn json(self) -> Value {
        json!([
            self.accounts,
            self.households,
            self.persons,
            self.employed_persons,
            self.looking_persons,
            self.waged_persons,
            self.wage_bill_micros.to_string(),
        ])
    }

    /// Adds another's figures. Period 0 in an overflow error means the opening, which has no period.
    fn add(&mut self, other: Self) -> Result<(), BenchError> {
        let sum = |a: u64, b: u64| a.checked_add(b).ok_or(BenchError::Arithmetic { period: 0 });
        self.accounts = sum(self.accounts, other.accounts)?;
        self.households = sum(self.households, other.households)?;
        self.persons = sum(self.persons, other.persons)?;
        self.employed_persons = sum(self.employed_persons, other.employed_persons)?;
        self.looking_persons = sum(self.looking_persons, other.looking_persons)?;
        self.waged_persons = sum(self.waged_persons, other.waged_persons)?;
        self.wage_bill_micros = self
            .wage_bill_micros
            .checked_add(other.wage_bill_micros)
            .ok_or(BenchError::Arithmetic { period: 0 })?;
        Ok(())
    }

    /// Average hourly pay of the band's persons paid a wage, in millionths of a dollar, rounded down.
    #[must_use]
    pub fn hourly_pay_micros(&self, hours_per_person: u64) -> Option<i128> {
        let hours = i128::from(self.waged_persons).checked_mul(i128::from(hours_per_person))?;
        (hours > 0).then(|| self.wage_bill_micros / hours)
    }
}

/// The opening by place and band, and the nation's by band.
pub struct OpeningBands {
    /// Every pool's hours a person; the opening refuses pools that differ.
    pub hours_per_person: u64,
    pub nation: BTreeMap<&'static str, Held>,
    pub places: BTreeMap<String, BTreeMap<&'static str, Held>>,
}

/// Reads the opening by place and band.
///
/// # Errors
/// `BenchError::UnknownBand` for a member whose household is not an account of the opening;
/// `BenchError::Opening` when the pools differ in hours a person; `BenchError::Arithmetic` on overflow.
pub fn opening_bands(opening: &EconomicOpening, bands: &Bands) -> Result<OpeningBands, BenchError> {
    let mut places = BTreeMap::<String, BTreeMap<&'static str, Held>>::new();
    let mut put = |place: &str, key: HouseholdBudgetKey, held: Held| -> Result<(), BenchError> {
        places
            .entry(place.to_owned())
            .or_default()
            .entry(key.label())
            .or_default()
            .add(held)
    };
    for row in &opening.households {
        if let Some(account) = bands.account(row.principal_id)? {
            put(
                &account.place,
                account.key,
                Held {
                    accounts: 1,
                    households: row.households,
                    persons: row.persons,
                    ..Held::default()
                },
            )?;
        }
    }
    let rates: BTreeMap<StaffingMemberId, i128> = opening
        .employment
        .iter()
        .filter_map(|term| match term.compensation {
            LaborCompensation::Wage(rate) => Some((term.member_id, rate.micro_units())),
            LaborCompensation::WorkingOwner | LaborCompensation::UnpaidFamily => None,
        })
        .collect();
    let mut hours_seen = BTreeSet::new();
    for seed in &opening.staffing {
        let hours = seed.pool.policy().hours_per_person();
        hours_seen.insert(hours);
        for member in &seed.members {
            let Some(account) = bands.account(member.member.household_id())? else {
                continue;
            };
            let rate = rates.get(&member.member.member_id());
            let waged_persons = if rate.is_some() { member.employed } else { 0 };
            let wage_bill_micros = rate.map_or(Ok(0), |rate| {
                rate.checked_mul(i128::from(member.employed))
                    .and_then(|paid| paid.checked_mul(i128::from(hours)))
                    .ok_or(BenchError::Arithmetic { period: 0 })
            })?;
            put(
                &account.place,
                account.key,
                Held {
                    employed_persons: member.employed,
                    looking_persons: member.reserve,
                    waged_persons,
                    wage_bill_micros,
                    ..Held::default()
                },
            )?;
        }
    }
    if hours_seen.is_empty() {
        return Err(refused("the opening holds no staffing pools"));
    }
    let [hours_per_person] = hours_seen.iter().copied().collect::<Vec<_>>()[..] else {
        return Err(refused("the pools differ in hours a person"));
    };
    let mut nation = BTreeMap::<&'static str, Held>::new();
    for keys in places.values() {
        for (key, held) in keys {
            nation.entry(key).or_default().add(*held)?;
        }
    }
    Ok(OpeningBands {
        hours_per_person,
        nation,
        places,
    })
}

impl OpeningBands {
    /// The file `bands-opening.json` holds: the head, then one line for the nation and one for each place.
    #[must_use]
    pub fn record(&self, scenario: &str, compiler: &str) -> Value {
        let rows = |keys: &BTreeMap<&'static str, Held>| -> Value {
            Value::Object(
                keys.iter()
                    .map(|(key, held)| ((*key).to_owned(), held.json()))
                    .collect::<Map<_, _>>(),
            )
        };
        let places: Map<String, Value> = self
            .places
            .iter()
            .map(|(geoid, keys)| (geoid.clone(), rows(keys)))
            .collect();
        json!({
            "bench": "country-opening-2026-11",
            "scenario": scenario,
            "compiler": compiler,
            "places_count": self.places.len(),
            "hours_per_person": self.hours_per_person,
            "legend": opening_legend(),
            "nation": rows(&self.nation),
            "places": places,
        })
    }
}

/// What the six figures of the opening's rows are, in plain words.
fn opening_legend() -> Value {
    json!({
        "figures": [
            "accounts", "households", "persons", "employed_persons", "looking_persons",
            "waged_persons", "wage_bill_micros"
        ],
        "accounts": "domestic household accounts of the band, the accounts carved from one counted under its parent's band",
        "households": "households of those accounts",
        "persons": "persons of those accounts, at work, looking or neither",
        "employed_persons": "persons at work at the opening, over the members of the accounts",
        "looking_persons": "persons looking for work at the opening",
        "waged_persons": "the employed persons of the members whose compensation is a wage; a working owner and an unpaid member of a family are at work and are paid none, so employed_persons less waged_persons is the persons at work for no wage",
        "wage_bill_micros": "one period's wages in millionths of a dollar: the wage times the member's employed persons times the member's hours a person, over the members paid a wage",
        "average_hourly_pay": "the wage bill over the waged persons and the hours a person (hours_per_person), rounded down",
        "key": "the household account's budget key: earning-lower-paid-half, earning-better-paid-forty, earning-owner, no-earner-nonowner, no-earner-owner, collective-residence",
        "place": "the hub county's geoid of a pooled place; the nation is the sum of the places",
    })
}

/// The legend of a period's `earners` column, for the record's `columns`.
#[must_use]
pub fn earners_legend() -> Value {
    json!({
        "by_key": ["at_work", "looking", "wages_received_micros", "benefits_received_micros", "money_micros"],
        "at_work": "persons at work at the close, after the moves of people who look for work; working owners and unpaid members of a family at work are counted, though they draw no wage",
        "looking": "persons looking for work at the close, counted as jobs_after_moves counts them",
        "wages_received_micros": "wages the band's accounts were paid in the period",
        "benefits_received_micros": "what the fund's programs paid the band's accounts in the period",
        "money_micros": "the band's cash at the close",
    })
}

/// A period's figures of one band.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
struct Earned {
    at_work: u64,
    looking: u64,
    wages: i128,
    benefits: i128,
    money: i128,
}

/// The nation's period by band, with the checks of the bench's decision 4.
///
/// # Errors
/// `BenchError::UnknownBand` for an account the bands do not know; `BenchError::NoAccount` for a domestic
/// account the book does not hold; `BenchError::BandsDiffer` when a sum of the bands differs from the
/// record's own figure; `BenchError::Arithmetic` on overflow.
pub fn earners(
    period: u64,
    bands: &Bands,
    state: &MaterialCircuitState,
    closing_members: &[PoolMembers],
    transfers: &[MoneyTransferReceipt],
    programs: &[PublicProgramReceipt],
    row: &Value,
) -> Result<Value, BenchError> {
    let mut by = BTreeMap::<&'static str, Earned>::new();
    for held in closing_members {
        for member in &held.members {
            if let Some(account) = bands.account(member.binding().household_id())? {
                let earned = by.entry(account.key.label()).or_default();
                earned.at_work = earned
                    .at_work
                    .checked_add(member.employed())
                    .ok_or(BenchError::Arithmetic { period })?;
                earned.looking = earned
                    .looking
                    .checked_add(member.reserve())
                    .ok_or(BenchError::Arithmetic { period })?;
            }
        }
    }
    for transfer in transfers {
        if !matches!(transfer.purpose, MoneyTransferPurpose::WagePayment(_)) {
            continue;
        }
        if let MoneyLocation::Cash(AccountId::Household(principal)) = transfer.credit.location {
            if let Some(account) = bands.account(principal)? {
                let earned = by.entry(account.key.label()).or_default();
                earned.wages = earned
                    .wages
                    .checked_add(transfer.credit.delta.micro_units())
                    .ok_or(BenchError::Arithmetic { period })?;
            }
        }
    }
    for program in programs {
        if let Some(account) = bands.account(program.recipient)? {
            let earned = by.entry(account.key.label()).or_default();
            earned.benefits = earned
                .benefits
                .checked_add(program.paid.micro_units())
                .ok_or(BenchError::Arithmetic { period })?;
        }
    }
    let book = &economy_health::economy(state).book;
    for (principal, key) in bands.domestic() {
        let cash = book
            .cash(AccountId::Household(principal))
            .map_err(|_| BenchError::NoAccount { period, principal })?;
        let earned = by.entry(key.label()).or_default();
        earned.money = earned
            .money
            .checked_add(cash.micro_units())
            .ok_or(BenchError::Arithmetic { period })?;
    }
    check_sums(period, &by, row)?;
    let out: Map<String, Value> = by
        .iter()
        .map(|(key, earned)| {
            (
                (*key).to_owned(),
                json!([
                    earned.at_work,
                    earned.looking,
                    earned.wages.to_string(),
                    earned.benefits.to_string(),
                    earned.money.to_string(),
                ]),
            )
        })
        .collect();
    Ok(Value::Object(out))
}

/// The sums that must hold: at work and looking equal the domestic figures of `jobs_after_moves`, and the
/// money equals the record's domestic households' money.
fn check_sums(
    period: u64,
    by: &BTreeMap<&'static str, Earned>,
    row: &Value,
) -> Result<(), BenchError> {
    let differs = |what: &'static str, bands: i128, expected: i128| {
        if bands == expected {
            Ok(())
        } else {
            Err(BenchError::BandsDiffer {
                period,
                what,
                bands,
                expected,
            })
        }
    };
    let jobs = &row["jobs_after_moves"]["domestic"];
    let figure = |at: usize| {
        jobs[at]
            .as_u64()
            .map(i128::from)
            .ok_or(BenchError::Arithmetic { period })
    };
    let money: i128 = row["money"]["households_domestic"]
        .as_str()
        .and_then(|text| text.parse().ok())
        .ok_or(BenchError::Arithmetic { period })?;
    let sum = |pick: fn(&Earned) -> i128| by.values().map(pick).sum::<i128>();
    differs("at_work", sum(|e| i128::from(e.at_work)), figure(0)?)?;
    differs("looking", sum(|e| i128::from(e.looking)), figure(1)?)?;
    differs("money", sum(|e| e.money), money)
}
