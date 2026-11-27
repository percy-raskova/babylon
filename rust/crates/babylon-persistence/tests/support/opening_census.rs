//! The census of the twelve-trade opening: what its people and workplaces are, before any recipe or price
//! matters. Every figure is a sum of the compiled opening's own rows (persons, hours and micros as integers).
//!
//! The census is read from the capture, not from the builder: a site's part (the code's financial domain) is
//! the part whose public body its operating-income tax goes to, an account's part is the part whose public body
//! its wage tax goes to, and an account's budget key is the capture's own.
use babylon_kernel::economic_identity::EconomicFunction;
use babylon_kernel::economic_location::{EconomicLocation, ForeignCounterpart};
use babylon_material_circuit::{
    AccountId, CommodityKind, FinalDemandPrincipalId, GoodId, LaborCompensation, PublicAccountId,
    SiteId, StaffingMemberId, TaxBasis, UnitId,
};
use babylon_persistence::economic_catalog::{
    CapturedEconomicCatalog, EconomicOpening, SourceArtifactKind,
};
use babylon_persistence::national_economy::grain::{
    ContributionDestination, FinancialDomainId, ReservePosition,
};
use babylon_persistence::national_economy::{
    self, GameMachines, GameProfile, GameProfileWage, NationalGamePolicy,
};
use babylon_persistence::national_household_allocation::HouseholdBudgetKey;
use babylon_persistence::national_trade_pay::NationalTradePayReference;
use flate2::read::GzDecoder;
use flate2::{Compression, GzBuilder};
use serde_json::{json, Map, Value};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::fmt::{Display, Formatter, Write as _};
use std::io::{Read, Write};

/// The most bytes the committed file may hold (the repository's size rule).
pub const MAX_GZ_BYTES: usize = 1_048_576;
/// The most bytes the census text may expand to when it is read.
pub const MAX_JSON_BYTES: usize = 8_388_608;
/// The crossing services of the census: the one the Director ruled (K1), whichever the scenario holds.
const CROSSING_SERVICES: [&str; 1] = ["business_services"];

/// Why the census could not be read from an opening: each refusal names what was found.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CensusError {
    /// A part of the capture the census reads is absent.
    Absent(&'static str),
    /// A site or an account of a county that belongs to no part, or an account with no budget key.
    Unplaced(String),
    /// Two accounts of one key in one part are dealt different sellers of a product.
    SellersDiffer {
        part: String,
        key: String,
        product: String,
    },
    /// A seller of a product that pays no wage.
    NoWage(String),
    /// A foreign region whose every site making a good has nobody at work (the region is named).
    RegionWithoutWork(String),
    /// A restocking row of the opening buys abroad from a region other than the one the census reads by the
    /// rotation (the compiler's path test sent the buyer elsewhere): the buyer's site, the good, the two regions.
    RotationDiffers {
        buyer: String,
        good: String,
        census: String,
        opening: String,
    },
    /// A figure past what an integer of the file holds.
    Overflow(&'static str),
    /// A trade with no figure where the policy must give one.
    Policy(&'static str),
}

impl Display for CensusError {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Absent(what) => write!(f, "the capture holds no {what}"),
            Self::Unplaced(what) => write!(f, "{what} belongs to no part"),
            Self::SellersDiffer { part, key, product } => write!(
                f,
                "the accounts of {key} in {part} are dealt different sellers of {product}"
            ),
            Self::NoWage(seller) => write!(f, "the seller {seller} pays no wage"),
            Self::RegionWithoutWork(region) => write!(f, "{region} has nobody at work"),
            Self::RotationDiffers {
                buyer,
                good,
                census,
                opening,
            } => write!(
                f,
                "{buyer} buys {good} abroad from {opening}, the census's rotation says {census}"
            ),
            Self::Overflow(what) => write!(f, "{what} overflows"),
            Self::Policy(what) => write!(f, "the policy has no {what}"),
        }
    }
}

impl std::error::Error for CensusError {}

type Result<T> = std::result::Result<T, CensusError>;

/// A tree of objects whose leaves are integers added up, or text set: the census as it is built.
struct Doc(Value);

impl Doc {
    fn new() -> Self {
        Self(Value::Object(Map::new()))
    }

    fn slot(&mut self, path: &[&str]) -> Result<&mut Value> {
        let mut at = &mut self.0;
        for step in path {
            if !at.is_object() {
                *at = Value::Object(Map::new());
            }
            at = at
                .as_object_mut()
                .ok_or(CensusError::Absent("object"))?
                .entry((*step).to_owned())
                .or_insert(Value::Null);
        }
        Ok(at)
    }

    /// Adds `n` to the integer at `path`, which is 0 where nothing is yet.
    fn add(&mut self, path: &[&str], n: u128) -> Result<()> {
        let slot = self.slot(path)?;
        let current = if slot.is_null() {
            0
        } else {
            slot.as_u64().ok_or(CensusError::Overflow("a figure"))?
        };
        let total = u64::try_from(u128::from(current) + n)
            .map_err(|_| CensusError::Overflow("a figure"))?;
        *slot = Value::from(total);
        Ok(())
    }

    /// Makes the integer at `path` exist.
    fn ensure(&mut self, path: &[&str]) -> Result<()> {
        self.add(path, 0)
    }

    fn set(&mut self, path: &[&str], value: Value) -> Result<()> {
        *self.slot(path)? = value;
        Ok(())
    }
}

/// The text of the census: `serde_json`'s pretty form with two spaces, every object's keys sorted, a trailing
/// newline. The keys are sorted here, not left to the map's own order.
#[must_use]
pub fn census_bytes(census: &Value) -> Vec<u8> {
    fn write(value: &Value, depth: usize, out: &mut String) {
        let pad = |out: &mut String, depth: usize| out.push_str(&"  ".repeat(depth));
        match value {
            Value::Object(map) if !map.is_empty() => {
                let mut keys: Vec<&String> = map.keys().collect();
                keys.sort();
                out.push_str("{\n");
                for (index, key) in keys.iter().enumerate() {
                    pad(out, depth + 1);
                    out.push_str(&Value::String((*key).clone()).to_string());
                    out.push_str(": ");
                    write(&map[*key], depth + 1, out);
                    out.push_str(if index + 1 < keys.len() { ",\n" } else { "\n" });
                }
                pad(out, depth);
                out.push('}');
            }
            Value::Array(items) if !items.is_empty() => {
                out.push_str("[\n");
                for (index, item) in items.iter().enumerate() {
                    pad(out, depth + 1);
                    write(item, depth + 1, out);
                    out.push_str(if index + 1 < items.len() { ",\n" } else { "\n" });
                }
                pad(out, depth);
                out.push(']');
            }
            other => out.push_str(&other.to_string()),
        }
    }
    let mut out = String::new();
    write(census, 0, &mut out);
    out.push('\n');
    out.into_bytes()
}

/// The text gzipped as the repository's reference tables are: mtime 0, no file name, the best compression.
///
/// # Errors
/// The writer's error, as text.
pub fn gzip_text(text: &[u8]) -> std::result::Result<Vec<u8>, String> {
    let mut encoder = GzBuilder::new()
        .mtime(0)
        .write(Vec::new(), Compression::best());
    encoder.write_all(text).map_err(|e| e.to_string())?;
    encoder.finish().map_err(|e| e.to_string())
}

/// The text of a gzipped census, refused past `MAX_JSON_BYTES`.
///
/// # Errors
/// The decoder's error, or the size, as text.
pub fn gunzip_text(bytes: &[u8]) -> std::result::Result<Vec<u8>, String> {
    let mut text = Vec::new();
    GzDecoder::new(bytes)
        .take(u64::try_from(MAX_JSON_BYTES).map_err(|e| e.to_string())? + 1)
        .read_to_end(&mut text)
        .map_err(|e| e.to_string())?;
    if text.len() > MAX_JSON_BYTES {
        return Err(format!("the census text is over {MAX_JSON_BYTES} bytes"));
    }
    Ok(text)
}

/// The scenario's text with the three edits of the census scenario (E3): `country_services` as the Director
/// ruled it; its `[[household_wants]]` rows replaced by one luxury row each of consumer goods, leisure and
/// business services (a person a unit); and a handling row on consumer goods where the text has none. The
/// dealing reads persons and force, never a want's amount or a handling figure, so the census is the same from
/// the fixture and from the rebuilt scenario.
#[must_use]
pub fn census_scenario(text: &str) -> String {
    const SERVICES: &str = r#"country_services = ["business_services", "leisure", "utility"]"#;
    let has_hours = section_has(text, "[commodity.consumer_goods]", "handling_hours");
    let has_units = section_has(text, "[commodity.consumer_goods]", "handling_units");
    let has_markets = text.lines().any(|line| line.trim() == "[markets]");
    let mut out = String::with_capacity(text.len() + 512);
    let mut section = String::new();
    let mut in_wants = false;
    let mut in_array = false;
    for line in text.lines() {
        let trimmed = line.trim();
        if in_array {
            in_array = !line.contains(']');
            continue;
        }
        if is_header(trimmed) {
            in_wants = trimmed == "[[household_wants]]";
            trimmed.clone_into(&mut section);
            if in_wants {
                continue;
            }
            out.push_str(line);
            out.push('\n');
            if section == "[markets]" {
                out.push_str(SERVICES);
                out.push('\n');
            }
            if section == "[commodity.consumer_goods]" {
                if !has_hours {
                    out.push_str("handling_hours = 1\n");
                }
                if !has_units {
                    out.push_str("handling_units = 1\n");
                }
            }
            continue;
        }
        if in_wants {
            continue;
        }
        if section == "[markets]" && is_key(trimmed, "country_services") {
            in_array = line.contains('[') && !line.contains(']');
            continue;
        }
        out.push_str(line);
        out.push('\n');
    }
    if !has_markets {
        out.push_str("\n[markets]\n");
        out.push_str(SERVICES);
        out.push('\n');
    }
    for good in ["consumer_goods", "leisure", "business_services"] {
        let _ = write!(
            out,
            "\n[[household_wants]]\ngood = \"{good}\"\ntier = \"luxury\"\nbasis = \"persons\"\nunits_per_basis = 1\n"
        );
    }
    out
}

/// A table header (`[table]` or `[[array]]`), not a row of nested arrays such as `[1, 2]` or `["a"]`.
fn is_header(line: &str) -> bool {
    line.strip_prefix("[[")
        .or_else(|| line.strip_prefix('['))
        .and_then(|rest| rest.chars().next())
        .is_some_and(|c| c.is_ascii_alphabetic() || c == '_')
}

fn is_key(line: &str, key: &str) -> bool {
    line.strip_prefix(key)
        .is_some_and(|rest| rest.trim_start().starts_with('='))
}

/// Whether the table `header` of `text` has a line of `key`.
fn section_has(text: &str, header: &str, key: &str) -> bool {
    let mut inside = false;
    for line in text.lines() {
        let trimmed = line.trim();
        if is_header(trimmed) {
            inside = trimmed == header;
        } else if inside && is_key(trimmed, key) {
            return true;
        }
    }
    false
}

/// What the census knows of a household account of a county.
struct Account {
    key: HouseholdBudgetKey,
    part: String,
    persons: u64,
    households: u64,
}

/// What the census knows of a site.
struct Site {
    function: EconomicFunction,
    location: EconomicLocation,
    process: bool,
    public: bool,
    /// The wage the site pays, micros an hour, as the compiler observed it (a site with no employee pays none).
    wage: Option<u128>,
    /// The persons in work or seeking it at the site.
    force: u64,
}

impl Site {
    const fn domestic(&self) -> bool {
        matches!(self.location, EconomicLocation::County(_))
    }
}

/// A storable good households or businesses buy, with the regions abroad that make it.
struct Good {
    key: String,
    id: GoodId,
    unit: UnitId,
    regions: Vec<EconomicLocation>,
}

/// Everything the census reads, found once.
struct Frame<'a> {
    opening: &'a EconomicOpening,
    policy: &'a NationalGamePolicy,
    pay: &'a NationalTradePayReference,
    /// Each part by its public body: its label and its hub.
    parts: BTreeMap<PublicAccountId, (String, String)>,
    accounts: BTreeMap<FinalDemandPrincipalId, Account>,
    sites: BTreeMap<SiteId, Site>,
    /// The label of the part each domestic site belongs to.
    site_part: BTreeMap<SiteId, String>,
    /// A seller's product by its good.
    products: BTreeMap<(GoodId, UnitId), (String, bool)>,
    goods: Vec<Good>,
}

fn part_label(hub: &str, position: Option<ReservePosition>) -> String {
    match position {
        None => hub.to_owned(),
        Some(position) => format!(
            "{hub}/{}",
            match position {
                ReservePosition::NoLaborForce => "none",
                ReservePosition::BelowCellReserveRate => "below",
                ReservePosition::AtCellReserveRate => "at",
                ReservePosition::AboveCellReserveRate => "above",
            }
        ),
    }
}

/// Every domestic part of the capture by its public body, from the capture's own witness.
fn read_parts(
    catalog: &CapturedEconomicCatalog,
) -> Result<BTreeMap<PublicAccountId, (String, String)>> {
    let witness = catalog
        .national_generation()
        .ok_or(CensusError::Absent("generation witness"))?;
    let mut found = BTreeMap::new();
    for county in &witness.counties {
        let (hub, position, domain) = match county.destination {
            ContributionDestination::Detailed(geoid) => (
                geoid,
                None,
                FinancialDomainId::detailed(
                    EconomicLocation::domestic_county(geoid)
                        .map_err(|_| CensusError::Absent("domestic hub"))?,
                ),
            ),
            ContributionDestination::Representative {
                catchment,
                position,
            } => {
                let hub = witness
                    .catchments
                    .iter()
                    .find(|c| c.id == catchment)
                    .ok_or(CensusError::Absent("catchment"))?
                    .key
                    .hub;
                (
                    hub,
                    Some(position),
                    FinancialDomainId {
                        location: EconomicLocation::domestic_county(hub)
                            .map_err(|_| CensusError::Absent("domestic hub"))?,
                        representative: Some((catchment, position)),
                    },
                )
            }
        };
        found.insert(
            domain.public_account(),
            (part_label(hub.as_str(), position), hub.as_str().to_owned()),
        );
    }
    Ok(found)
}

/// The part of each site and each account, by the public body its tax goes to.
type Placement = (
    BTreeMap<SiteId, String>,
    BTreeMap<FinalDemandPrincipalId, String>,
);

fn placement(
    opening: &EconomicOpening,
    parts: &BTreeMap<PublicAccountId, (String, String)>,
) -> Placement {
    let mut sites = BTreeMap::new();
    let mut accounts = BTreeMap::new();
    for tax in &opening.institutions.taxes {
        let Some((label, _)) = parts.get(&tax.public_recipient) else {
            continue;
        };
        match (tax.payer, tax.basis) {
            (AccountId::Site(site), TaxBasis::PositiveOperatingIncome) => {
                sites.insert(site, label.clone());
            }
            (AccountId::Household(principal), TaxBasis::WageIncome) => {
                accounts.insert(principal, label.clone());
            }
            _ => {}
        }
    }
    (sites, accounts)
}

fn read_accounts(
    catalog: &CapturedEconomicCatalog,
    accounts_part: &BTreeMap<FinalDemandPrincipalId, String>,
) -> Result<BTreeMap<FinalDemandPrincipalId, Account>> {
    let mut found = BTreeMap::new();
    for row in &catalog.opening().households {
        if !matches!(row.location, EconomicLocation::County(_)) {
            continue;
        }
        let key = catalog
            .national_household_budget(row.principal_id)
            .ok_or_else(|| CensusError::Unplaced(format!("the account at {}", row.location)))?;
        let part = accounts_part
            .get(&row.principal_id)
            .ok_or_else(|| CensusError::Unplaced(format!("the account at {}", row.location)))?;
        found.insert(
            row.principal_id,
            Account {
                key,
                part: part.clone(),
                persons: row.persons,
                households: row.households,
            },
        );
    }
    Ok(found)
}

fn read_sites(catalog: &CapturedEconomicCatalog) -> BTreeMap<SiteId, Site> {
    let opening = catalog.opening();
    let public: BTreeSet<SiteId> = opening
        .institutions
        .ownership
        .iter()
        .filter(|claim| matches!(claim.beneficiary, AccountId::Public(_)))
        .map(|claim| claim.issuer_site_id)
        .collect();
    let mut sites: BTreeMap<SiteId, Site> = opening
        .sites
        .iter()
        .map(|site| {
            (
                site.site_id,
                Site {
                    function: site.function,
                    location: site.location,
                    process: !site.processes.is_empty(),
                    public: public.contains(&site.site_id),
                    wage: catalog
                        .national_workplace_wage(site.site_id)
                        .and_then(|wage| u128::try_from(wage.micro_units()).ok()),
                    force: 0,
                },
            )
        })
        .collect();
    for pool in &opening.staffing {
        if let Some(site) = sites.get_mut(&pool.pool.site_id()) {
            site.force += pool
                .members
                .iter()
                .map(|member| member.member.labor_force())
                .sum::<u64>();
        }
    }
    sites
}

fn region_key(location: EconomicLocation) -> Result<&'static str> {
    match location {
        EconomicLocation::Foreign(counterpart) => Ok(counterpart.as_str()),
        EconomicLocation::Dependency(_) => Ok("dependency"),
        EconomicLocation::County(_) => Err(CensusError::Absent("region abroad")),
    }
}

/// The regions abroad that make a good, or the region that stops the census.
fn regions_of(
    opening: &EconomicOpening,
    id: GoodId,
    unit: UnitId,
) -> Result<Vec<EconomicLocation>> {
    national_economy::crossing_regions(opening, id, unit)
        .map_err(|region| CensusError::RegionWithoutWork(region.to_string()))
}

fn frame<'a>(
    catalog: &'a CapturedEconomicCatalog,
    policy: &'a NationalGamePolicy,
    pay: &'a NationalTradePayReference,
) -> Result<Frame<'a>> {
    let opening = catalog.opening();
    let parts = read_parts(catalog)?;
    let (site_part, account_part) = placement(opening, &parts);
    let accounts = read_accounts(catalog, &account_part)?;
    let sites = read_sites(catalog);
    // A domestic site is in a part: a site with no tax row of a part is refused.
    for (id, site) in &sites {
        if site.domestic() && !site_part.contains_key(id) {
            return Err(CensusError::Unplaced(format!(
                "the site at {}",
                site.location
            )));
        }
    }
    let products = policy
        .commodities
        .iter()
        .map(|(key, good)| {
            (
                (good.good_id, good.unit_id),
                (
                    key.clone(),
                    matches!(good.kind, CommodityKind::Storable { .. }) && good.cargo.is_some(),
                ),
            )
        })
        .collect();
    let mut goods = Vec::new();
    for (key, good) in &policy.commodities {
        if matches!(good.kind, CommodityKind::Storable { .. }) && good.cargo.is_some() {
            goods.push(Good {
                key: key.clone(),
                id: good.good_id,
                unit: good.unit_id,
                regions: regions_of(opening, good.good_id, good.unit_id)?,
            });
        }
    }
    let frame = Frame {
        opening,
        policy,
        pay,
        parts,
        accounts,
        sites,
        site_part,
        products,
        goods,
    };
    Ok(frame)
}

impl Frame<'_> {
    fn part_of(&self, site: SiteId) -> Option<String> {
        self.site_part.get(&site).cloned()
    }

    fn trades(&self) -> &'static [EconomicFunction] {
        self.policy.trades.functions()
    }

    fn hours(&self) -> u128 {
        u128::from(self.policy.work_hours_per_person)
    }
}

fn trade(function: EconomicFunction) -> &'static str {
    function.source_key()
}

fn wage_hours(wage: u128, employed: u64, hours: u128) -> u128 {
    wage * u128::from(employed) * hours
}

/// `trades`, the keys of `households` and the figures of `places` that follow the workforce.
fn workforce(frame: &Frame<'_>, doc: &mut Doc) -> Result<()> {
    let opening = frame.opening;
    let terms: BTreeMap<StaffingMemberId, (SiteId, LaborCompensation)> = opening
        .employment
        .iter()
        .map(|term| (term.member_id, (term.site_id, term.compensation)))
        .collect();
    let hours = frame.hours();
    for pool in &opening.staffing {
        let site_id = pool.pool.site_id();
        let Some(site) = frame.sites.get(&site_id).filter(|site| site.domestic()) else {
            continue;
        };
        let part = frame
            .part_of(site_id)
            .ok_or_else(|| CensusError::Unplaced(format!("the site at {}", site.location)))?;
        let name = trade(site.function);
        for seed in &pool.members {
            let member = &seed.member;
            let (_, compensation) = terms
                .get(&member.member_id())
                .ok_or(CensusError::Absent("employment term"))?;
            let account = frame
                .accounts
                .get(&member.household_id())
                .ok_or_else(|| CensusError::Unplaced("a member's account".into()))?;
            let key = account.key.label();
            doc.add(&["trades", name, "force"], u128::from(member.labor_force()))?;
            let employed = u128::from(seed.employed);
            let wage = match compensation {
                LaborCompensation::Wage(rate) => {
                    doc.add(&["trades", name, "employee_persons"], employed)?;
                    u128::try_from(rate.micro_units())
                        .map_err(|_| CensusError::Overflow("a wage"))?
                }
                LaborCompensation::WorkingOwner => {
                    doc.add(&["trades", name, "working_owner_persons"], employed)?;
                    0
                }
                LaborCompensation::UnpaidFamily => {
                    doc.add(&["trades", name, "unpaid_family_persons"], employed)?;
                    0
                }
            };
            let paid = matches!(compensation, LaborCompensation::Wage(_));
            let payroll = wage_hours(wage, seed.employed, hours);
            doc.add(&["trades", name, "payroll_micros_per_period"], payroll)?;
            if paid && site.public {
                doc.add(&["trades", name, "public_employee_persons"], employed)?;
                doc.add(
                    &["trades", name, "public_payroll_micros_per_period"],
                    payroll,
                )?;
            }
            for (path, n) in [
                ("employee_persons", if paid { employed } else { 0 }),
                ("payroll_micros_per_period", payroll),
                (
                    "public_employee_persons",
                    if paid && site.public { employed } else { 0 },
                ),
                (
                    "public_payroll_micros_per_period",
                    if paid && site.public { payroll } else { 0 },
                ),
            ] {
                doc.add(&["places", &part, "trades", name, path], n)?;
            }
            let resident = &account.part;
            doc.add(&["households", key, "employed"], employed)?;
            doc.add(&["households", key, "reserve"], u128::from(seed.reserve))?;
            doc.add(
                &["households", key, "wage_income_micros_per_period"],
                payroll,
            )?;
            doc.add(&["places", resident, "keys", key, "employed"], employed)?;
            doc.add(
                &["places", resident, "keys", key, "reserve"],
                u128::from(seed.reserve),
            )?;
            doc.add(
                &[
                    "places",
                    resident,
                    "keys",
                    key,
                    "wage_income_micros_per_period",
                ],
                payroll,
            )?;
        }
    }
    Ok(())
}

/// The sites of each trade, their machines and the zero of every figure of a trade and a part.
fn sites_and_machines(frame: &Frame<'_>, doc: &mut Doc) -> Result<()> {
    let GameMachines::Workers {
        workers_per_machine,
        ..
    } = &frame.policy.equipment.machines
    else {
        return Err(CensusError::Policy("workers per machine"));
    };
    for function in frame.trades() {
        let name = trade(*function);
        for field in [
            "employee_persons",
            "working_owner_persons",
            "unpaid_family_persons",
            "payroll_micros_per_period",
            "force",
            "sites",
            "public_employee_persons",
            "public_payroll_micros_per_period",
            "machines",
        ] {
            doc.ensure(&["trades", name, field])?;
        }
        doc.set(
            &["trades", name, "national_wage_micros"],
            Value::from(
                u64::try_from(frame.pay.national_wage(*function).micro_units())
                    .map_err(|_| CensusError::Overflow("a national wage"))?,
            ),
        )?;
        for (label, _) in frame.parts.values() {
            for field in [
                "employee_persons",
                "payroll_micros_per_period",
                "public_employee_persons",
                "public_payroll_micros_per_period",
            ] {
                doc.ensure(&["places", label, "trades", name, field])?;
            }
        }
    }
    for (label, _) in frame.parts.values() {
        doc.ensure(&[
            "places",
            label,
            "trades",
            trade(EconomicFunction::PublicProvisioning),
            "machines",
        ])?;
    }
    for (id, site) in frame.sites.iter().filter(|(_, site)| site.domestic()) {
        let name = trade(site.function);
        doc.add(&["trades", name, "sites"], 1)?;
        if site.process {
            let workers = workers_per_machine
                .get(&site.function)
                .copied()
                .filter(|workers| *workers > 0)
                .ok_or(CensusError::Policy("workers per machine of a trade"))?;
            let machines = u128::from(site.force.div_ceil(workers));
            doc.add(&["trades", name, "machines"], machines)?;
            if site.function == EconomicFunction::PublicProvisioning {
                let part = frame.part_of(*id).ok_or_else(|| {
                    CensusError::Unplaced(format!("the site at {}", site.location))
                })?;
                doc.add(&["places", &part, "trades", name, "machines"], machines)?;
            }
        }
    }
    for (function, workers) in workers_per_machine {
        doc.set(
            &["workers_per_machine", trade(*function)],
            Value::from(*workers),
        )?;
    }
    Ok(())
}

/// `households` and the keys of `places` that follow the accounts, and each part's hub.
fn accounts(frame: &Frame<'_>, doc: &mut Doc) -> Result<()> {
    for (label, hub) in frame.parts.values() {
        doc.set(&["places", label, "hub"], Value::from(hub.clone()))?;
        doc.ensure(&["places", label, "owner_households"])?;
        doc.ensure(&["places", label, "public_persons_served"])?;
    }
    for account in frame.accounts.values() {
        let key = account.key.label();
        doc.add(&["households", key, "accounts"], 1)?;
        doc.add(
            &["households", key, "households"],
            u128::from(account.households),
        )?;
        doc.add(&["households", key, "persons"], u128::from(account.persons))?;
        for field in ["employed", "reserve", "wage_income_micros_per_period"] {
            doc.ensure(&["households", key, field])?;
            doc.ensure(&["places", &account.part, "keys", key, field])?;
        }
        doc.add(
            &["places", &account.part, "keys", key, "households"],
            u128::from(account.households),
        )?;
        doc.add(
            &["places", &account.part, "keys", key, "persons"],
            u128::from(account.persons),
        )?;
        if account.key.owner_exposure() {
            doc.add(
                &["places", &account.part, "owner_households"],
                u128::from(account.households),
            )?;
        }
    }
    Ok(())
}

/// What each account is dealt: its sellers and the region of each shop's second supplier abroad, the persons
/// each public part serves, and the retail half of `assignment`.
fn purchases(frame: &Frame<'_>, doc: &mut Doc) -> Result<()> {
    let regions: BTreeMap<(GoodId, UnitId), &Good> = frame
        .goods
        .iter()
        .map(|good| ((good.id, good.unit), good))
        .collect();
    let mut dealt = BTreeMap::<(String, &'static str, String), SiteId>::new();
    let mut wageless = BTreeSet::<(String, SiteId)>::new();
    for row in &frame.opening.policies.household_purchases {
        let Some(account) = frame.accounts.get(&row.principal_id) else {
            continue;
        };
        let (product, storable) = frame
            .products
            .get(&(row.good_id, row.unit_id))
            .ok_or(CensusError::Absent("product of a purchase"))?;
        let seller = frame
            .sites
            .get(&row.retailer_site_id)
            .ok_or(CensusError::Absent("seller of a purchase"))?;
        let Some(wage) = seller.wage else {
            wageless.insert((product.clone(), row.retailer_site_id));
            continue;
        };
        let key = account.key.label();
        let slot = (account.part.clone(), key, product.clone());
        if *dealt.entry(slot).or_insert(row.retailer_site_id) != row.retailer_site_id {
            return Err(CensusError::SellersDiffer {
                part: account.part.clone(),
                key: key.to_owned(),
                product: product.clone(),
            });
        }
        doc.set(
            &["places", &account.part, "sellers", key, product],
            Value::from(u64::try_from(wage).map_err(|_| CensusError::Overflow("a wage"))?),
        )?;
        if *storable {
            let good = regions
                .get(&(row.good_id, row.unit_id))
                .ok_or(CensusError::Absent("storable good"))?;
            if let Some(region) =
                national_economy::crossing_region(&good.regions, row.retailer_site_id)
            {
                let name = region_key(region)?;
                doc.set(
                    &["places", &account.part, "abroad", key, product],
                    Value::from(name),
                )?;
                doc.add(
                    &["assignment", "households", product, name],
                    u128::from(account.persons),
                )?;
            }
        }
        if product == "public_provision" {
            let part = frame.part_of(row.retailer_site_id).ok_or_else(|| {
                CensusError::Unplaced(format!("the public provider at {}", seller.location))
            })?;
            doc.add(
                &["places", &part, "public_persons_served"],
                u128::from(account.persons),
            )?;
        }
    }
    if !wageless.is_empty() {
        let mut by_product = BTreeMap::<&str, usize>::new();
        for (product, _) in &wageless {
            *by_product.entry(product).or_default() += 1;
        }
        return Err(CensusError::NoWage(format!("{by_product:?}")));
    }
    Ok(())
}

/// The domestic buying sites' half of `assignment`, and `crossing_force`: the force of the sites with a
/// process, by the region the rotation gives them, whether their recipes buy the good or not.
fn rotation(frame: &Frame<'_>, doc: &mut Doc) -> Result<()> {
    let makers: Vec<EconomicFunction> = frame.policy.recipes.keys().copied().collect();
    for good in &frame.goods {
        for region in &good.regions {
            let name = region_key(*region)?;
            doc.ensure(&["assignment", "households", &good.key, name])?;
            for function in &makers {
                doc.ensure(&["assignment", "sites", &good.key, name, trade(*function)])?;
            }
        }
    }
    let services: Vec<(String, Vec<EconomicLocation>)> = CROSSING_SERVICES
        .iter()
        .map(|key| {
            let good = frame
                .policy
                .commodities
                .get(*key)
                .ok_or(CensusError::Policy("crossing service"))?;
            Ok((
                (*key).to_owned(),
                regions_of(frame.opening, good.good_id, good.unit_id)?,
            ))
        })
        .collect::<Result<_>>()?;
    for (service, _) in &services {
        for name in ForeignCounterpart::ALL
            .iter()
            .map(|c| c.as_str())
            .chain(["dependency"])
        {
            for function in &makers {
                doc.ensure(&["crossing_force", service, name, trade(*function)])?;
            }
        }
    }
    for (id, site) in frame
        .sites
        .iter()
        .filter(|(_, s)| s.domestic() && s.process)
    {
        let name = trade(site.function);
        for good in &frame.goods {
            if let Some(region) = national_economy::crossing_region(&good.regions, *id) {
                doc.add(
                    &["assignment", "sites", &good.key, region_key(region)?, name],
                    u128::from(site.force),
                )?;
            }
        }
        for (service, regions) in &services {
            if let Some(region) = national_economy::crossing_region(regions, *id) {
                doc.add(
                    &["crossing_force", service, region_key(region)?, name],
                    u128::from(site.force),
                )?;
            }
        }
    }
    Ok(())
}

/// The census reads a buyer's region abroad by the first rotated region; the compiler skips a region with no
/// path for the cargo. Where the opening's restocking rows buy a good abroad for a domestic buyer, the
/// supplier's location must be the region the census names: the rows are a check and give no figure.
///
/// # Errors
/// `RotationDiffers` for a row that buys elsewhere; `Absent` when no row buys abroad (the check would be empty).
fn rotation_agrees(frame: &Frame<'_>) -> Result<()> {
    let mut checked = 0_usize;
    for row in &frame.opening.policies.replenishment {
        let (Some(buyer), Some(supplier)) = (
            frame.sites.get(&row.buyer_site_id),
            frame.sites.get(&row.supplier_site_id),
        ) else {
            continue;
        };
        if !buyer.domestic() || supplier.domestic() {
            continue;
        }
        let Some(good) = frame
            .goods
            .iter()
            .find(|good| (good.id, good.unit) == (row.good_id, row.unit_id))
        else {
            continue;
        };
        checked += 1;
        let census = national_economy::crossing_region(&good.regions, row.buyer_site_id);
        if census != Some(supplier.location) {
            return Err(CensusError::RotationDiffers {
                buyer: format!("{:?}", row.buyer_site_id),
                good: good.key.clone(),
                census: format!("{census:?}"),
                opening: format!("{:?}", supplier.location),
            });
        }
    }
    if checked == 0 {
        return Err(CensusError::Absent("restocking row abroad"));
    }
    Ok(())
}

/// The profile's pay in trade `function`: `floor(national_wage x bps / 10_000)`, or the designed hourly wage.
fn region_wage(
    frame: &Frame<'_>,
    profile: &GameProfile,
    function: EconomicFunction,
) -> Result<u64> {
    let micros = match profile.wage {
        GameProfileWage::PerHour(wage) => wage.micro_units(),
        GameProfileWage::FractionOfUnitedStates { bps } => {
            frame
                .pay
                .national_wage(function)
                .micro_units()
                .checked_mul(i128::from(bps))
                .ok_or(CensusError::Overflow("a foreign wage"))?
                / 10_000
        }
    };
    u64::try_from(micros).map_err(|_| CensusError::Overflow("a foreign wage"))
}

/// `abroad`: the persons, households, labor force and employed of each region and of the dependencies together,
/// and what each trade pays there.
fn abroad(frame: &Frame<'_>, doc: &mut Doc) -> Result<()> {
    for row in &frame.opening.households {
        if !matches!(row.location, EconomicLocation::County(_)) {
            let name = region_key(row.location)?;
            doc.add(&["abroad", name, "persons"], u128::from(row.persons))?;
            doc.add(&["abroad", name, "households"], u128::from(row.households))?;
        }
    }
    for pool in &frame.opening.staffing {
        let Some(site) = frame.sites.get(&pool.pool.site_id()) else {
            continue;
        };
        if site.domestic() {
            continue;
        }
        let name = region_key(site.location)?;
        for seed in &pool.members {
            doc.add(&["abroad", name, "employed"], u128::from(seed.employed))?;
            doc.add(
                &["abroad", name, "labor_force"],
                u128::from(seed.member.labor_force()),
            )?;
        }
    }
    let regions = ForeignCounterpart::ALL
        .iter()
        .filter_map(|c| frame.policy.counterparts.get(c).map(|p| (c.as_str(), p)))
        .chain([("dependency", &frame.policy.dependency.profile)]);
    for (name, profile) in regions {
        for field in ["persons", "households", "labor_force", "employed"] {
            doc.ensure(&["abroad", name, field])?;
        }
        for function in frame.trades() {
            doc.set(
                &["abroad", name, "wage_micros", trade(*function)],
                Value::from(region_wage(frame, profile, *function)?),
            )?;
        }
    }
    Ok(())
}

/// The sha256 of bytes as lowercase hex.
#[must_use]
pub fn sha_hex(bytes: &[u8]) -> String {
    let mut text = String::new();
    for byte in Sha256::digest(bytes) {
        let _ = write!(text, "{byte:02x}");
    }
    text
}

fn sources(
    catalog: &CapturedEconomicCatalog,
    policy: &NationalGamePolicy,
    doc: &mut Doc,
) -> Result<()> {
    for (name, kind) in [
        ("cohorts_sha256", SourceArtifactKind::NationalCohorts),
        ("counties_sha256", SourceArtifactKind::NationalCounties),
        ("households_sha256", SourceArtifactKind::NationalHouseholds),
        ("pay_sha256", SourceArtifactKind::NationalTradePay),
    ] {
        let bytes = catalog
            .source(kind)
            .ok_or(CensusError::Absent("source table"))?;
        doc.set(&["sources", name], Value::from(sha_hex(bytes)))?;
    }
    let mut services = policy.country_services.clone();
    services.sort();
    doc.set(&["sources", "country_services"], json!(services))
}

/// What the opening's people and workplaces are, before any recipe or price matters.
///
/// # Errors
/// `CensusError`: a site or account in no part, two accounts of one key and part dealt different sellers, a
/// region abroad with nobody at work, a seller that pays no wage, or a figure past an integer.
pub fn opening_census(
    catalog: &CapturedEconomicCatalog,
    policy: &NationalGamePolicy,
    pay: &NationalTradePayReference,
) -> Result<Value> {
    let frame = frame(catalog, policy, pay)?;
    let mut doc = Doc::new();
    sites_and_machines(&frame, &mut doc)?;
    accounts(&frame, &mut doc)?;
    workforce(&frame, &mut doc)?;
    purchases(&frame, &mut doc)?;
    rotation(&frame, &mut doc)?;
    rotation_agrees(&frame)?;
    abroad(&frame, &mut doc)?;
    sources(catalog, policy, &mut doc)?;
    Ok(doc.0)
}
