//! Household units in Wayne: what the pooled budget groups hold and are paid today, read from the
//! engine's own accounts.
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_kernel::currency::Currency;
use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};
use babylon_material_circuit::{
    self as engine, AccountId, AdjustmentReceipt, FinalDemandPrincipalId, MaterialCircuitState,
    RestartTest, StaffingMemberState, StopHold, TaxBasis, TaxPolicy,
};
use babylon_persistence::economic_catalog;
use babylon_persistence::economic_catalog::{
    CapturedEconomicCatalog, CommodityLabel, EconomicCatalogInput, EconomicOpening, SourceArtifact,
    SourceArtifactKind,
};
use babylon_persistence::identity::CampaignId;
use babylon_persistence::runtime_session::Band;
use babylon_practice_contract::CountyPeriodFacts;
use babylon_tick::material_replay::PreparedMaterialTick;
use babylon_tick::material_world;
use babylon_tick::replay_session::ReplayCommitDisposition;
use serde_json::{json, Map, Value};
use std::collections::{BTreeMap, BTreeSet};
use std::fmt::Write;
use std::path::{Path, PathBuf};
use uuid::Uuid;

#[path = "support/country_bench.rs"]
mod country_bench;
#[path = "support/country_fund.rs"]
mod country_fund;
#[path = "support/country_rules.rs"]
mod country_rules;
#[path = "support/country_seekers.rs"]
mod country_seekers;
#[path = "support/country_sizes.rs"]
mod country_sizes;
#[path = "support/economy_health.rs"]
mod economy_health;
#[path = "support/household_accounts.rs"]
mod household_accounts;
#[path = "support/supply_chain.rs"]
mod supply_chain;

use country_bench::{BenchError, BenchPeriod, CountryBench, RuleSet};
use country_seekers::Wages;
use country_sizes::{CountrySizes, PlaceKey, PlaceSizes, SEEKER_BOUND};
use economy_health::{BenchReceipts, Census, Opening};
use household_accounts::{AccountReading, AccountSpec, PeriodReading, Session, TopTenth};
use supply_chain::{ChainSite, Names};

/// The County Review's recorded campaign; no organizer commitment is made, so the run matches its
/// `no-contact` line.
fn campaign() -> CampaignId {
    CampaignId::from_uuid(Uuid::from_u128(0x0026_1631_7036))
}

/// One spec for each county group, in the config's order, with its households by band.
fn pooled_specs(session: &Session) -> Vec<AccountSpec> {
    let register = session
        .material()
        .county_review()
        .expect("the national opening has a county section");
    let (config, roster) = (register.config(), &register.state().roster);
    config
        .groups
        .iter()
        .enumerate()
        .map(|(at, group)| {
            let at = u32::try_from(at).expect("few groups");
            let mut bands = BTreeMap::<Band, u64>::new();
            for row in roster.rows.iter().filter(|row| row.key.group == at) {
                *bands.entry(row.key.band).or_default() += row.households;
            }
            AccountSpec {
                label: group.label.clone(),
                principal: FinalDemandPrincipalId::from_bytes(group.group_id),
                bands: bands
                    .into_iter()
                    .filter(|(_, households)| *households > 0)
                    .collect(),
            }
        })
        .collect()
}

fn opened_session(catalog: CapturedEconomicCatalog, name: &str) -> Session {
    catalog
        .create_foundation(
            ReplaySessionId::try_from(name).expect("session identity"),
            ReplaySeed::new(319),
        )
        .expect("foundation")
        .into_session()
        .expect("session")
}

fn pooled_catalog() -> CapturedEconomicCatalog {
    let catalog = CapturedEconomicCatalog::capture_national_campaign(
        economic_catalog::national_catalog_input(),
        campaign(),
    )
    .expect("the national campaign");
    assert_eq!(catalog.compiler_version(), "national-world-v12");
    catalog
}

/// The twelve-trade scenario's defines (policy schema 8): the plan's fixture.
const TWELVE_TRADES_DEFINES: &[u8] = include_bytes!("fixtures/national_twelve_trades.defines.toml");

/// The scenario a bench run names: the shipped one, or the twelve trades.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Scenario {
    Shipped,
    TwelveTrades,
}

impl Scenario {
    const fn name(self) -> &'static str {
        match self {
            Self::Shipped => "shipped",
            Self::TwelveTrades => "twelve-trades",
        }
    }

    fn input(self) -> EconomicCatalogInput {
        match self {
            Self::Shipped => economic_catalog::national_catalog_input(),
            Self::TwelveTrades => {
                economic_catalog::national_catalog_input_for(TWELVE_TRADES_DEFINES)
                    .expect("the twelve-trade defines parse")
            }
        }
    }

    const fn compiler(self) -> &'static str {
        match self {
            Self::Shipped => "national-world-v12",
            Self::TwelveTrades => "national-world-v13",
        }
    }

    /// The wage a seeker is offered where its pool pays none.
    const fn wages(self) -> Wages {
        match self {
            Self::Shipped => Wages::Default,
            Self::TwelveTrades => Wages::PlaceAverage,
        }
    }

    /// The scenario captured as the campaign compiler builds it, with the census its record reads.
    fn captured(self) -> (CapturedEconomicCatalog, Census) {
        let input = self.input();
        let wage = match self {
            Self::Shipped => Some(default_wage(&input)),
            Self::TwelveTrades => None,
        };
        let catalog = CapturedEconomicCatalog::capture_national_campaign(input, campaign())
            .expect("the national campaign");
        assert_eq!(catalog.compiler_version(), self.compiler());
        let census = match wage {
            Some(wage) => Census::new(catalog.opening(), wage),
            None => Census::observed(catalog.opening()),
        };
        (catalog, census)
    }
}

#[test]
fn the_pooled_opening_accounts_add_back() {
    let session = opened_session(pooled_catalog(), "household-units-pooled");
    let specs = pooled_specs(&session);
    let accounts = household_accounts::read_accounts(&session, &specs);
    assert_eq!(specs.len(), 8);
    assert!(
        specs[4].bands.is_empty(),
        "the collective residence has no roster rows"
    );
    let ordinary: Vec<_> = (0..8).filter(|&i| accounts[i].households > 0).collect();
    assert_eq!(ordinary.len(), 7);
    assert_eq!(
        ordinary
            .iter()
            .map(|&i| accounts[i].households)
            .sum::<u64>(),
        700_591
    );
    for (spec, account) in specs.iter().zip(&accounts) {
        assert_eq!(
            spec.bands.iter().map(|b| b.1).sum::<u64>(),
            account.households,
            "{}",
            spec.label
        );
        assert_eq!(
            account.net_assets_micros,
            account.cash_micros + account.pantry_cost_micros + account.other_assets_micros,
            "{}",
            spec.label
        );
    }
    let mut totals = BTreeMap::<Band, u64>::new();
    for (band, households) in specs.iter().flat_map(|spec| spec.bands.iter()) {
        *totals.entry(*band).or_default() += households;
    }
    assert_eq!(
        totals,
        BTreeMap::from([
            (Band::Top1, 7_006),
            (Band::Next9, 63_054),
            (Band::Next40, 280_236),
            (Band::Bottom50, 350_295),
        ])
    );
    let config = session
        .material()
        .county_review()
        .expect("county section")
        .config();
    let named: BTreeSet<usize> = (0..specs.len())
        .filter(|&i| household_accounts::is_top_tenth(&specs[i]))
        .collect();
    let owning: BTreeSet<usize> = (0..specs.len())
        .filter(|&i| !specs[i].bands.is_empty() && config.groups[i].has_ownership_income)
        .collect();
    assert_eq!(
        named, owning,
        "the top tenth is the groups with ownership income"
    );
    assert_eq!(
        household_accounts::top_tenth(&specs, &accounts, None).households,
        70_060
    );
}

/// The reader's figures against the county register's facts for the period just committed.
fn check_period(
    facts: &CountyPeriodFacts,
    specs: &[AccountSpec],
    accounts: &[AccountReading],
    period_readings: &[PeriodReading],
    period: u64,
) {
    assert_eq!(
        facts.period, period,
        "the register's facts are of this close"
    );
    for (at, spec) in specs.iter().enumerate() {
        let (account, read, group) = (&accounts[at], &period_readings[at], &facts.groups[at]);
        let label = &spec.label;
        assert_eq!(
            account.net_assets_micros,
            account.cash_micros + account.pantry_cost_micros + account.other_assets_micros,
            "{label}: net assets add back in period {period}"
        );
        assert_eq!(
            read.ownership_income_micros, group.ownership_income_micros,
            "{label}"
        );
        assert_eq!(read.support_micros, group.support_income_micros, "{label}");
        assert_eq!(read.aid_micros, group.aid_income_micros, "{label}");
        assert_eq!(
            read.wage_tax_collected_micros, group.wage_tax_collected_micros,
            "{label}"
        );
        assert_eq!(account.households, group.closing_households, "{label}");
        if period == 1 {
            assert_eq!(
                read.ownership_income_micros, 0,
                "{label}: nothing is paid in period 1"
            );
        }
    }
}

fn account_json(account: &AccountReading, period: Option<&PeriodReading>) -> Value {
    let mut row = json!({
        "households": account.households,
        "persons": account.persons,
        "labor_force": account.labor_force,
        "cash_micros": account.cash_micros.to_string(),
        "pantry_cost_micros": account.pantry_cost_micros.to_string(),
        "other_assets_micros": account.other_assets_micros.to_string(),
        "net_assets_micros": account.net_assets_micros.to_string(),
    });
    let Some(period) = period else { return row };
    let needs: Map<String, Value> = period
        .needs
        .iter()
        .map(|need| {
            (
                need.key.clone(),
                json!({
                    "required": need.required,
                    "unmet": need.unmet,
                    "unpaid": need.unpaid,
                    "unsupplied": need.unsupplied,
                    "cost_micros": need.cost_micros.to_string(),
                }),
            )
        })
        .collect();
    let flows = json!({
        "wages_micros": period.wages_micros.to_string(),
        "support_micros": period.support_micros.to_string(),
        "aid_micros": period.aid_micros.to_string(),
        "company_payouts_micros": period.company_payouts_micros.to_string(),
        "site_distributions_micros": period.site_distributions_micros.to_string(),
        "ownership_income_micros": period.ownership_income_micros.to_string(),
        "wage_tax_assessed_micros": period.wage_tax_assessed_micros.to_string(),
        "wage_tax_collected_micros": period.wage_tax_collected_micros.to_string(),
        "needs_cost_micros": period.needs_cost_micros.to_string(),
        "needs": needs,
    });
    row.as_object_mut()
        .expect("a JSON object")
        .extend(flows.as_object().expect("a JSON object").clone());
    row
}

fn top_tenth_json(sums: &TopTenth) -> Value {
    assert!(
        sums.household_net_assets_micros > 0,
        "households hold wealth to be measured"
    );
    let share_bps = sums.net_assets_micros * 10_000 / sums.household_net_assets_micros;
    let mut row = json!({
        "households": sums.households,
        "net_assets_micros": sums.net_assets_micros.to_string(),
        "household_net_assets_micros": sums.household_net_assets_micros.to_string(),
        "ownership_income_micros": sums.ownership_income_micros.to_string(),
        "needs_cost_micros": sums.needs_cost_micros.to_string(),
        "share_bps": share_bps.to_string(),
        "law_share": "2/3",
    });
    if sums.needs_cost_micros > 0 {
        let over = sums.ownership_income_micros * 10_000 / sums.needs_cost_micros;
        row["ownership_over_needs_bps"] = json!(over.to_string());
    }
    row
}

/// Households in the roster rows of each spec's group that have no crew (nobody in the labor force).
fn crewless_households(session: &Session, specs: &[AccountSpec]) -> Vec<u64> {
    let register = session
        .material()
        .county_review()
        .expect("the national opening has a county section");
    let roster = &register.state().roster;
    (0..specs.len())
        .map(|at| {
            let at = u32::try_from(at).expect("few groups");
            roster
                .rows
                .iter()
                .filter(|row| row.key.group == at && row.key.crew.is_none())
                .map(|row| row.households)
                .sum()
        })
        .collect()
}

/// C8's test: at the opening, each ordinary account has a person outside the labor force for each
/// household. A crew row holds someone in the labor force for each household, so the opening's
/// persons rule can refuse only a group with crewless rows; the flag is `null` for the others.
fn other_persons_json(
    specs: &[AccountSpec],
    opening: &[AccountReading],
    crewless: &[u64],
) -> Vec<Value> {
    specs
        .iter()
        .zip(opening)
        .zip(crewless)
        .filter(|((_, account), _)| account.households > 0)
        .map(|((spec, account), &crewless)| {
            let other = account.persons - account.labor_force;
            json!({
                "label": spec.label,
                "persons": account.persons,
                "labor_force": account.labor_force,
                "households": account.households,
                "crewless_households": crewless,
                "other_persons": other,
                "admits_every_crewless_unit": (crewless > 0).then_some(other >= account.households),
            })
        })
        .collect()
}

fn period_json(
    specs: &[AccountSpec],
    accounts: &[AccountReading],
    period: Option<&[PeriodReading]>,
    at: u64,
) -> Value {
    let rows: Vec<Value> = accounts
        .iter()
        .enumerate()
        .map(|(i, account)| account_json(account, period.map(|rows| &rows[i])))
        .collect();
    json!({
        "period": at,
        "accounts": rows,
        "top_tenth": top_tenth_json(&household_accounts::top_tenth(specs, accounts, period)),
    })
}

/// Closes one period with no organizer commitment; `read` sees the candidate before it commits.
fn close_period_with<T>(
    session: &mut Session,
    period: u64,
    read: impl FnOnce(&Session, &PreparedMaterialTick<HypergraphStore>) -> T,
) -> T {
    let actions = babylon_practice_contract::organizer_action_batch(
        session.material().organizer_config().expect("organizer"),
        session.material().organizer_state().expect("state"),
        None,
        session.graph_session().session_identity().clone(),
    )
    .expect("the no-command organizer action batch");
    assert_eq!(actions.resolve_tick(), period);
    let candidate = session
        .prepare_advance(&actions)
        .expect("ordinary national close");
    let read = read(session, &candidate);
    session
        .commit_prepared_and_publish(&mut CollectingSink::default(), candidate, |_, _| {
            Ok::<_, &str>(ReplayCommitDisposition::Committed)
        })
        .expect("the period commits");
    read
}

/// Closes one period; returns the readings of the close and of the state after it.
fn close_period(
    session: &mut Session,
    labels: &[CommodityLabel],
    specs: &[AccountSpec],
    period: u64,
) -> (Vec<PeriodReading>, Vec<AccountReading>) {
    let readings = close_period_with(session, period, |session, candidate| {
        household_accounts::read_period(session, candidate, labels, specs)
    });
    (readings, household_accounts::read_accounts(session, specs))
}

#[test]
#[ignore = "writes reports/household-units-2026-11-20/wayne-pooled-accounts.json"]
fn record_wayne_pooled_accounts() {
    let catalog = pooled_catalog();
    let labels = catalog.opening().commodity_labels.clone();
    let compiler = catalog.compiler_version().to_owned();
    let mut session = opened_session(catalog, "household-units-pooled-record");
    let specs = pooled_specs(&session);
    let opening = household_accounts::read_accounts(&session, &specs);
    let crewless = crewless_households(&session, &specs);
    let mut periods = vec![period_json(&specs, &opening, None, 0)];
    for period in 1..=34 {
        let (readings, accounts) = close_period(&mut session, &labels, &specs, period);
        let facts = session
            .material()
            .county_review()
            .expect("county section")
            .state()
            .last_facts
            .clone()
            .expect("the close left facts");
        check_period(&facts, &specs, &accounts, &readings, period);
        periods.push(period_json(&specs, &accounts, Some(&readings), period));
    }
    let report = json!({
        "campaign": campaign().as_uuid().to_string(),
        "replay_seed": 319,
        "compiler": compiler,
        "accounts": specs.iter().map(|spec| json!({
            "label": spec.label,
            "bands": spec.bands.iter().map(|(band, households)| json!([band, households])).collect::<Vec<_>>(),
        })).collect::<Vec<_>>(),
        "periods": periods,
        "other_persons": other_persons_json(&specs, &opening, &crewless),
    });
    let text = serde_json::to_string_pretty(&report).expect("the report serializes") + "\n";
    assert!(text.len() < 1_048_576, "the report is {} bytes", text.len());
    let path = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../../reports/household-units-2026-11-20/wayne-pooled-accounts.json");
    std::fs::create_dir_all(path.parent().expect("the report has a directory"))
        .expect("the report directory is created");
    std::fs::write(&path, text).expect("the report is written");
}

/// One site's record across the recorded periods.
fn chain_json(site: &ChainSite, floors: &[Value], periods: &[Value]) -> Value {
    json!({
        "site": supply_chain::short(site.site),
        "label": site.label,
        "location": site.location,
        "roles": site.roles,
        "cash_floors": floors,
        "periods": periods,
    })
}

/// Households of one county in the opening, by principal.
fn county_principals(opening: &EconomicOpening, geoid: &str) -> BTreeSet<FinalDemandPrincipalId> {
    let location = format!("county:{geoid}");
    opening
        .households
        .iter()
        .filter(|row| row.location.to_string() == location && row.households > 0)
        .map(|row| row.principal_id)
        .collect()
}

/// Plays `periods` closes and returns the chain report: each Wayne need's seller, one step
/// upstream, the business-services providers of those, and the four needs of Wayne and Cook.
fn chain_report(catalog: CapturedEconomicCatalog, periods: u64) -> Value {
    let names = Names::new(catalog.opening());
    let cook = county_principals(catalog.opening(), "17031");
    let compiler = catalog.compiler_version().to_owned();
    let mut session = opened_session(catalog, "household-units-supply-chain");
    let names = names.with_processes(&session);
    let wayne: Vec<_> = pooled_specs(&session)
        .iter()
        .filter(|spec| !spec.bands.is_empty())
        .map(|spec| spec.principal)
        .collect();
    let sites = supply_chain::chain_sites(&session, &names, &wayne);
    let floors: Vec<_> = sites
        .iter()
        .map(|site| supply_chain::floors(&session, &names, site.site))
        .collect();
    let mut records = vec![Vec::new(); sites.len()];
    let mut counties = Vec::new();
    let wayne: BTreeSet<_> = wayne.into_iter().collect();
    for period in 1..=periods {
        let opening: Vec<_> = sites
            .iter()
            .map(|site| supply_chain::site_opening(&session, &names, site.site))
            .collect();
        let (closes, needs) = close_period_with(&mut session, period, |session, candidate| {
            let receipts =
                material_world::decode_material_receipts(candidate.material().receipt_bytes())
                    .expect("canonical material receipts");
            let closes: Vec<_> = sites
                .iter()
                .map(|site| supply_chain::site_close(&receipts, &names, site.site))
                .collect();
            let needs = json!({
                "period": period,
                "wayne_26163": supply_chain::county_needs(session, &receipts, &names, &wayne),
                "cook_17031": supply_chain::county_needs(session, &receipts, &names, &cook),
            });
            (closes, needs)
        });
        counties.push(needs);
        for (at, (open, close)) in opening.into_iter().zip(closes).enumerate() {
            let after = supply_chain::site_after(&session, &names, sites[at].site);
            records[at]
                .push(json!({"period": period, "opening": open, "close": close, "after": after}));
        }
    }
    json!({
        "campaign": campaign().as_uuid().to_string(),
        "replay_seed": 319,
        "compiler": compiler,
        "cook_household_principals": cook.len(),
        "county_needs": counties,
        "sites": sites.iter().zip(&floors).zip(&records).map(|((site, floors), periods)| chain_json(site, floors, periods)).collect::<Vec<_>>(),
    })
}

fn write_report(report: &Value, path: &Path) {
    let text = serde_json::to_string_pretty(report).expect("the report serializes") + "\n";
    assert!(text.len() < 1_048_576, "the report is {} bytes", text.len());
    std::fs::write(path, text).expect("the report is written");
}

#[test]
#[ignore = "writes reports/household-units-2026-11-20/wayne-supply-chain.json"]
fn record_wayne_supply_chain() {
    let report = chain_report(pooled_catalog(), 10);
    write_report(
        &report,
        &Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../../../reports/household-units-2026-11-20/wayne-supply-chain.json"),
    );
}

/// The shipped national policy text, as captured in the catalog input.
fn policy_text(input: &EconomicCatalogInput) -> String {
    let source = input
        .sources
        .iter()
        .find(|source| source.kind() == SourceArtifactKind::NationalGamePolicy)
        .expect("the national input carries its game policy");
    String::from_utf8(source.bytes().to_vec()).expect("the policy is text")
}

/// The national catalog input with `edits` made to its policy text, each exactly once.
fn edited_input(edits: &[(&str, &str)]) -> EconomicCatalogInput {
    let mut input = economic_catalog::national_catalog_input();
    let mut text = policy_text(&input);
    for (old, new) in edits {
        assert_eq!(text.matches(old).count(), 1, "one exact place for {old:?}");
        text = text.replacen(old, new, 1);
    }
    let source = input
        .sources
        .iter_mut()
        .find(|source| source.kind() == SourceArtifactKind::NationalGamePolicy)
        .expect("the national input carries its game policy");
    *source = SourceArtifact::capture(source.kind(), text.into_bytes());
    input
}

/// The policy's default wage, read from its text.
fn default_wage(input: &EconomicCatalogInput) -> i128 {
    let text = policy_text(input);
    let line = text
        .lines()
        .find_map(|line| line.strip_prefix("default_wage_micros_per_hour = "))
        .expect("the policy names a default wage");
    line.trim().parse().expect("the default wage is an integer")
}

/// Plays `periods` closes of one policy and returns its health record.
fn health_report(name: &str, edits: &[(&str, &str)], periods: u64) -> Value {
    let input = edited_input(edits);
    let wage = default_wage(&input);
    let catalog = CapturedEconomicCatalog::capture_national_campaign(input, campaign())
        .expect("the national campaign");
    let compiler = catalog.compiler_version().to_owned();
    let census = Census::new(catalog.opening(), wage);
    let mut session = opened_session(catalog, "economy-health");
    let mut rows = Vec::new();
    for period in 1..=periods {
        let open = Opening::read(&census, session.catalog(), session.material().state());
        let receipts = close_period_with(&mut session, period, |_, candidate| {
            material_world::decode_material_receipts(candidate.material().receipt_bytes())
                .expect("canonical material receipts")
        });
        rows.push(economy_health::period_record(
            &census,
            &open,
            &receipts,
            session.catalog(),
            session.material().state(),
        ));
    }
    let panel: Vec<Value> = census
        .panel
        .iter()
        .map(|county| json!({"name": county.name, "geoid": county.geoid, "rule": county.rule}))
        .collect();
    json!({
        "campaign": campaign().as_uuid().to_string(),
        "replay_seed": 319,
        "compiler": compiler,
        "candidate": name,
        "policy_edits": edits,
        "default_wage_micros_per_hour": wage.to_string(),
        "columns": economy_health::columns(),
        "panel": panel,
        "periods": rows,
    })
}

/// Writes a record one period to a line, with a trailing newline, and returns the file's size.
fn write_compact_unbounded(report: &Value, path: &Path) -> usize {
    let mut head = report.clone();
    let periods = head
        .as_object_mut()
        .expect("a JSON object")
        .remove("periods")
        .expect("a record has periods");
    let lines: Vec<String> = periods
        .as_array()
        .expect("periods are a list")
        .iter()
        .map(|row| serde_json::to_string(row).expect("a period serializes"))
        .collect();
    let mut text = serde_json::to_string_pretty(&head).expect("the head serializes");
    text.truncate(text.len() - 2);
    text += ",\n  \"periods\": [\n    ";
    text += &lines.join(",\n    ");
    text += "\n  ]\n}\n";
    let size = text.len();
    std::fs::create_dir_all(path.parent().expect("a directory")).expect("the directory is made");
    std::fs::write(path, text).expect("the record is written");
    size
}

/// Writes a record one period to a line, with a trailing newline, under 1 MiB.
fn write_compact(report: &Value, path: &Path) {
    let size = write_compact_unbounded(report, path);
    assert!(size < 1_048_576, "the record is {size} bytes");
}

#[test]
fn the_health_reader_adds_back_at_the_opening() {
    let input = economic_catalog::national_catalog_input();
    let wage = default_wage(&input);
    assert_eq!(wage, 24_000_000);
    let catalog = CapturedEconomicCatalog::capture_national_campaign(input, campaign())
        .expect("the national campaign");
    let census = Census::new(catalog.opening(), wage);
    let seeded = economy_health::opening_counts(catalog.opening());
    let sites = catalog.opening().sites.len();
    let session = opened_session(catalog, "economy-health-opening");
    assert_eq!(
        economy_health::session_counts(&census, session.material().state()),
        seeded
    );
    assert!(
        seeded["domestic"][0] > 100_000_000,
        "the nation's households"
    );
    assert_eq!(
        economy_health::site_counts(&census).values().sum::<u64>(),
        u64::try_from(sites).expect("few sites")
    );
    let geoids: Vec<&str> = census.panel.iter().map(|c| c.geoid.as_str()).collect();
    assert_eq!(geoids.len(), 6);
    assert_eq!(geoids[..4], ["26163", "17031", "06037", "48201"]);
    let money = economy_health::money_record(&census, session.material().state());
    let book: i128 = economy_health::economy(session.material().state())
        .book
        .snapshot()
        .accounts
        .iter()
        .map(|row| row.cash.micro_units())
        .sum();
    assert_eq!(money["cash_total"], json!(book.to_string()));
}

/// The lowercase hex of the shipped campaign's three-period health record, as the tick's reader
/// writes it. Filled in once, from the first run, and never edited after.
const THREE_PERIOD_RECORD_DIGEST: &str =
    "4976714827bc7c65e2b822b94a684828f3110b933f3ad2bbcae1def4898515b7";

#[test]
#[ignore = "three national periods through the tick; run by Task 2's gate"]
fn the_reader_writes_the_same_record_for_three_periods() {
    let record = health_report("shipped", &[], 3);
    let bytes = serde_json::to_vec(&record).expect("the record serializes");
    let mut digest = String::new();
    for byte in babylon_kernel::content_digest::sha256_of(&bytes) {
        write!(digest, "{byte:02x}").expect("a string takes text");
    }
    assert_eq!(digest, THREE_PERIOD_RECORD_DIGEST);
}

/// The periods the summaries and the README read.
const SUMMARY_PERIODS: [u64; 7] = [1, 2, 3, 4, 5, 13, 34];

fn int(value: &Value) -> i128 {
    value
        .as_str()
        .map_or_else(|| value.as_i64().map(i128::from), |text| text.parse().ok())
        .expect("an integer figure")
}

/// Unmet over required for each need, summed over every place abroad.
fn abroad_unmet(row: &Value) -> Map<String, Value> {
    let mut sums = BTreeMap::<&str, [u64; 2]>::new();
    for place in row["abroad"].as_object().expect("places abroad").values() {
        for need in economy_health::NEEDS {
            let cells = &place[need];
            let sum = sums.entry(need).or_default();
            sum[0] += cells[0].as_u64().unwrap_or(0);
            sum[1] += cells[1].as_u64().unwrap_or(0);
        }
    }
    sums.into_iter()
        .map(|(need, [required, unmet])| {
            let share = (required > 0).then(|| u128::from(unmet) * 10_000 / u128::from(required));
            (need.to_owned(), json!(share))
        })
        .collect()
}

/// Sites under each floor, idle with a plan, and the functions they are in.
fn business_summary(row: &Value) -> Value {
    let mut totals = [0_i128; 3];
    let mut under = BTreeSet::new();
    for (scope, functions) in row["businesses"].as_object().expect("businesses") {
        for (function, cells) in functions.as_object().expect("functions") {
            for (at, total) in totals.iter_mut().enumerate() {
                *total += int(&cells[at + 1]);
            }
            if int(&cells[1]) + int(&cells[2]) > 0 {
                under.insert(format!("{scope} {function}"));
            }
        }
    }
    json!({
        "under_service_input_floor": totals[0],
        "under_replenishment_floor": totals[1],
        "zero_output_with_a_plan": totals[2],
        "functions_with_sites_under_a_floor": under,
    })
}

/// The products whose designed process does not cover its cost.
fn below_cost(row: &Value) -> Vec<String> {
    let mut names = Vec::new();
    for (name, product) in row["products"].as_object().expect("products") {
        for process in product["processes"].as_array().expect("processes") {
            let verdict = process["verdict"].as_str().expect("a verdict");
            if verdict != "covers cost" {
                names.push(format!("{name}: {verdict}"));
            }
        }
    }
    names
}

fn summary_row(row: &Value) -> Value {
    let supply = &row["supply"];
    let mut unmet = Map::new();
    let mut bands = Map::new();
    for need in economy_health::NEEDS {
        unmet.insert(need.to_owned(), supply[need]["sum"][4].clone());
        bands.insert(need.to_owned(), supply[need]["county_bands"].clone());
    }
    let jobs = &row["jobs"];
    json!({
        "period": row["period"],
        "national_unmet_share_bps": unmet,
        "counties_by_band": bands,
        "abroad_unmet_share_bps": abroad_unmet(row),
        "domestic_at_work_close": jobs["domestic"]["all"][2],
        "domestic_looking_close": jobs["domestic"]["all"][3],
        "abroad_at_work_close": jobs["foreign"]["all"][2],
        "businesses": business_summary(row),
        "below_cost": below_cost(row),
    })
}

/// The README's table for one record.
fn summary(record: &Value) -> Vec<Value> {
    record["periods"]
        .as_array()
        .expect("periods")
        .iter()
        .filter(|row| SUMMARY_PERIODS.contains(&row["period"].as_u64().expect("a period")))
        .map(summary_row)
        .collect()
}

fn report_path(name: &str) -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../../reports/economy-repair-2026-11-20")
        .join(name)
}

#[test]
#[ignore = "writes reports/economy-repair-2026-11-20/national-economy-health.json"]
fn record_national_economy_health() {
    let record = health_report("shipped", &[], 34);
    write_compact(&record, &report_path("national-economy-health.json"));
}

/// Candidate repairs, each a set of exact edits to the shipped policy text.
const SWEEP_OFF: (&str, &str) = (
    "opening_treasury_bps = 1000\n",
    "opening_treasury_bps = 0\n",
);
const BUSINESS_SERVICES_48: (&str, &str) = (
    "output = \"business_services\"\noutput_units_per_batch = 16\n",
    "output = \"business_services\"\noutput_units_per_batch = 48\n",
);
const EXTRACTION_16: (&str, &str) = (
    "output = \"resources\"\noutput_units_per_batch = 8\nlabor_hours_per_batch = 16\ninputs = { resource_deposit = 8,",
    "output = \"resources\"\noutput_units_per_batch = 16\nlabor_hours_per_batch = 16\ninputs = { resource_deposit = 16,",
);
/// Round 1 after C: extraction makes 32 units a batch from 32 units of deposit (16 hours).
const EXTRACTION_32: (&str, &str) = (
    "output = \"resources\"\noutput_units_per_batch = 8\nlabor_hours_per_batch = 16\ninputs = { resource_deposit = 8,",
    "output = \"resources\"\noutput_units_per_batch = 32\nlabor_hours_per_batch = 16\ninputs = { resource_deposit = 32,",
);
/// Round 2: energy makes 320 units of utility a batch (16 hours, 8 units of resources).
const ENERGY_320: (&str, &str) = (
    "output = \"utility\"\noutput_units_per_batch = 160\n",
    "output = \"utility\"\noutput_units_per_batch = 320\n",
);
/// Round 3: no secondary supplier abroad; every retailer and producer buys its whole need at home.
const NO_FOREIGN_PROCUREMENT: (&str, &str) = (
    "foreign_procurement_bps = 2500 ",
    "foreign_procurement_bps = 0 ",
);
/// Round 4: the county pays each opening job-seeker sixteen periods of food a period (the most
/// the policy admits), not one.
const SUPPORT_16: (&str, &str) = (
    "reserve_food_support_periods = 1\n",
    "reserve_food_support_periods = 16\n",
);
/// Round 4: food makes 32 parcels a batch (16 hours, the same inputs).
const FOOD_32: (&str, &str) = (
    "output = \"food\"\noutput_units_per_batch = 16\n",
    "output = \"food\"\noutput_units_per_batch = 32\n",
);
const C_EDITS: [(&str, &str); 3] = [SWEEP_OFF, BUSINESS_SERVICES_48, EXTRACTION_16];
const E_EDITS: [(&str, &str); 4] = [SWEEP_OFF, BUSINESS_SERVICES_48, EXTRACTION_32, ENERGY_320];
const F_EDITS: [(&str, &str); 5] = [
    SWEEP_OFF,
    BUSINESS_SERVICES_48,
    EXTRACTION_32,
    ENERGY_320,
    NO_FOREIGN_PROCUREMENT,
];
const G_EDITS: [(&str, &str); 4] = [
    SWEEP_OFF,
    BUSINESS_SERVICES_48,
    EXTRACTION_16,
    NO_FOREIGN_PROCUREMENT,
];
const H_EDITS: [(&str, &str); 6] = [
    SWEEP_OFF,
    BUSINESS_SERVICES_48,
    EXTRACTION_32,
    ENERGY_320,
    NO_FOREIGN_PROCUREMENT,
    SUPPORT_16,
];
const I_EDITS: [(&str, &str); 6] = [
    SWEEP_OFF,
    BUSINESS_SERVICES_48,
    EXTRACTION_32,
    ENERGY_320,
    NO_FOREIGN_PROCUREMENT,
    FOOD_32,
];
/// Round 5: no wage tax and no operating-income tax, so no money leaves circulation into the
/// public accounts.
const NO_WAGE_TAX: (&str, &str) = ("wage_tax_bps = 1500\n", "wage_tax_bps = 0\n");
const NO_OPERATING_TAX: (&str, &str) = (
    "operating_income_tax_bps = 1500\n",
    "operating_income_tax_bps = 0\n",
);
const J_EDITS: [(&str, &str); 8] = [
    SWEEP_OFF,
    BUSINESS_SERVICES_48,
    EXTRACTION_32,
    ENERGY_320,
    NO_FOREIGN_PROCUREMENT,
    FOOD_32,
    NO_WAGE_TAX,
    NO_OPERATING_TAX,
];
const K_EDITS: [(&str, &str); 7] = [
    SWEEP_OFF,
    BUSINESS_SERVICES_48,
    EXTRACTION_32,
    ENERGY_320,
    NO_FOREIGN_PROCUREMENT,
    FOOD_32,
    SUPPORT_16,
];
const CANDIDATES: [(&str, &[(&str, &str)]); 12] = [
    ("shipped", &[]),
    ("A", &[SWEEP_OFF]),
    ("B", &[SWEEP_OFF, BUSINESS_SERVICES_48]),
    ("C", &C_EDITS),
    ("D", &[SWEEP_OFF, BUSINESS_SERVICES_48, EXTRACTION_32]),
    ("E", &E_EDITS),
    ("F", &F_EDITS),
    ("G", &G_EDITS),
    ("H", &H_EDITS),
    ("I", &I_EDITS),
    ("J", &J_EDITS),
    ("K", &K_EDITS),
];

#[test]
#[ignore = "writes reports/economy-repair-2026-11-20/experiments.json; ECONOMY_CANDIDATES=A,B plays only those"]
fn record_economy_repair_candidates() {
    let only = std::env::var("ECONOMY_CANDIDATES").ok();
    let chosen = |name: &str| {
        only.as_deref()
            .is_none_or(|list| list.split(',').any(|n| n == name))
    };
    let mut rows = Vec::new();
    for (name, edits) in CANDIDATES.iter().filter(|(name, _)| chosen(name)) {
        let record = health_report(name, edits, 34);
        let full =
            Path::new(env!("CARGO_TARGET_TMPDIR")).join(format!("economy-repair/{name}.json"));
        write_compact(&record, &full);
        rows.push(json!({"candidate": name, "policy_edits": edits, "summary": summary(&record)}));
    }
    let path = match only {
        None => report_path("experiments.json"),
        Some(_) => {
            Path::new(env!("CARGO_TARGET_TMPDIR")).join("economy-repair/experiments-partial.json")
        }
    };
    write_report(&json!({"candidates": rows}), &path);
}

#[test]
#[ignore = "writes the Wayne supply chain of one candidate (ECONOMY_CANDIDATE) under the target's tmp"]
fn record_wayne_supply_chain_of_a_candidate() {
    let name = std::env::var("ECONOMY_CANDIDATE").unwrap_or_else(|_| "C".to_owned());
    let (_, edits) = CANDIDATES
        .iter()
        .find(|(candidate, _)| *candidate == name)
        .expect("a named candidate");
    let catalog =
        CapturedEconomicCatalog::capture_national_campaign(edited_input(edits), campaign())
            .expect("the national campaign");
    let path =
        Path::new(env!("CARGO_TARGET_TMPDIR")).join(format!("economy-repair/chain-{name}.json"));
    write_report(&chain_report(catalog, 10), &path);
}

/// The twenty places with the most new seeker rows, from the most, then by place.
fn busiest_places(sizes: &CountrySizes) -> Vec<(&PlaceKey, &PlaceSizes)> {
    let mut places: Vec<_> = sizes.by_place.iter().collect();
    places.sort_by(|a, b| b.1.new_rows.cmp(&a.1.new_rows).then(a.0.cmp(b.0)));
    places.truncate(20);
    places
}

/// A sum of sizes, failing with words rather than wrapping.
fn sum(mut values: impl Iterator<Item = u64>) -> u64 {
    values
        .try_fold(0_u64, u64::checked_add)
        .expect("a sum of sizes overflowed u64")
}

#[test]
fn the_country_s_sizes() {
    let catalog = pooled_catalog();
    let opening = catalog.opening();
    let compiled = opening.compile().expect("the shipped opening compiles");
    let sizes = country_sizes::country_sizes(opening, &compiled);
    println!(
        "members_with_seekers {} against SEEKER_BOUND {SEEKER_BOUND}: {}",
        sizes.members_with_seekers,
        if sizes.members_with_seekers <= SEEKER_BOUND {
            "fits"
        } else {
            "does not fit"
        }
    );
    for (key, place) in busiest_places(&sizes) {
        println!("{} {place:?}", key.0);
    }
    println!("{sizes:#?}");
    assert_eq!(
        sum(sizes.workplaces_by_scope.values().copied()),
        u64::try_from(opening.sites.len()).expect("a count")
    );
    assert_eq!(
        sizes.seeker_rows,
        sum(sizes.by_place.values().map(|p| p.seeker_rows))
    );
    assert_eq!(sizes.places_with_households, 187);
    assert_eq!(
        sizes.workplaces_by_scope,
        BTreeMap::from([("dependency", 60), ("domestic", 7283), ("foreign", 120)])
    );
    assert_eq!(
        sizes.household_accounts_by_scope,
        BTreeMap::from([("dependency", 6), ("domestic", 1584), ("foreign", 12)])
    );
    assert_eq!(sizes.pools, 7463);
    assert_eq!(sizes.members, 21062);
    assert_eq!(sizes.employment_terms, 21062);
    assert_eq!(sizes.member_labor_rows, 21062);
    assert_eq!(sizes.offers_goods, 2123);
    assert_eq!(sizes.offers_services, 4999);
    assert_eq!(sizes.market_rows_at_most, 9245);
    assert_eq!(sizes.members_outside_their_place, 0);
    assert_eq!(sizes.seeker_rows, 67461);
    assert_eq!(sizes.members_with_seekers, 67509);
}

/// The bench opens on the state the game's session opens with. Both states are digested under the
/// session's catalog: the digest covers the catalog's own digest (`wire/state.rs:542-558`), and the
/// bench's catalog differs from the session's by its portfolios setting (the bench leaves the
/// companies' portfolio choice out), so a digest under each one's own catalog would differ.
#[test]
fn the_bench_opens_on_the_session_s_state() {
    let catalog = pooled_catalog();
    let bench = CountryBench::open(catalog.opening(), RuleSet::None).expect("the bench opens");
    let session = opened_session(catalog, "country-bench-opening");
    let of_session =
        engine::material_circuit_state_digest(session.catalog(), session.material().state())
            .expect("the session's state digests");
    let of_bench = engine::material_circuit_state_digest(session.catalog(), bench.state())
        .expect("the bench's state digests under the session's catalog");
    assert_eq!(of_bench, of_session);
}

#[test]
fn one_bench_period_conserves_money_and_persons() {
    let catalog = pooled_catalog();
    let mut bench = CountryBench::open(catalog.opening(), RuleSet::None).expect("the bench opens");
    let money_of = |state: &MaterialCircuitState| {
        economy_health::economy(state)
            .book
            .total_cash_and_reserves()
            .expect("the book totals")
            .micro_units()
    };
    let opening_money = money_of(bench.state());
    let period = bench.step().expect("the first period closes");
    println!("one baseline period took {:?}", period.elapsed);
    assert_eq!(period.receipts.resolve_tick, 1);
    assert_eq!(money_of(bench.state()), opening_money);
    assert_ne!(period.receipts.staffing_members.len(), 0);
}

/// Each check passes when its two sides are equal and refuses a difference of one either way.
#[test]
fn the_three_checks_refuse_a_difference_of_one() {
    assert!(country_bench::check_money(7, 100, 100).is_ok());
    for closing in [101, 99] {
        assert!(matches!(
            country_bench::check_money(7, 100, closing),
            Err(BenchError::MoneyNotConserved { period: 7, opening: 100, closing: c }) if c == closing
        ));
    }
    assert!(country_bench::check_persons(7, 100, 3, 2, 101).is_ok());
    for closing in [100, 102] {
        assert!(matches!(
            country_bench::check_persons(7, 100, 3, 2, closing),
            Err(BenchError::PersonsNotExplained { period: 7, expected: 101, closing: c }) if c == closing
        ));
    }
    assert!(country_bench::check_labor_force(7, 50, 4, 46).is_ok());
    for closing in [47, 45] {
        assert!(matches!(
            country_bench::check_labor_force(7, 50, 4, closing),
            Err(BenchError::LaborForceNotExplained { period: 7, expected: 46, closing: c }) if c == closing
        ));
    }
}

/// What the bench's period holds beside the tick's receipts, as the reader takes it.
fn bench_receipts(stepped: &BenchPeriod) -> BenchReceipts<'_> {
    BenchReceipts {
        market_clearings: &stepped.market_clearings,
        adjustments: &stepped.adjustments,
        public_programs: &stepped.public_programs,
        closing_members: &stepped.closing_members,
        spare_money_raised: stepped.spare_money_raised,
    }
}

/// One bench period's row: the tick's reader with the market, the rules and the jobs after the moves.
fn bench_row(
    census: &Census,
    open: &Opening,
    stepped: &BenchPeriod,
    bench: &CountryBench,
) -> Value {
    let mut row = economy_health::period_record(
        census,
        open,
        &stepped.receipts,
        bench.catalog(),
        bench.state(),
    );
    let beside = bench_receipts(stepped);
    let object = row.as_object_mut().expect("a period row is an object");
    object.insert(
        "markets".to_owned(),
        economy_health::markets_record(census, &beside),
    );
    object.insert("rules".to_owned(), economy_health::rules_record(&beside));
    object.insert(
        "jobs_after_moves".to_owned(),
        economy_health::jobs_after_moves(census, beside.closing_members, bench.staffing()),
    );
    object.insert(
        "public".to_owned(),
        economy_health::public_record(open.providers(), &beside, bench.state(), bench.staffing()),
    );
    let fund_cash = bench.no_earner_per_person().map(|_| {
        economy_health::economy(bench.state())
            .book
            .cash(AccountId::Public(country_fund::fund_account()))
            .map(Currency::micro_units)
            .expect(
                "the fund's account is held at the close: a missing account is a failure, not 0",
            )
    });
    object.insert(
        "benefits".to_owned(),
        economy_health::benefits_record(
            &beside,
            &[country_fund::NO_EARNER, country_fund::LAID_OFF],
            fund_cash,
        ),
    );
    row
}

/// Plays up to `periods` closes of the bench under one rule set and returns its record (head,
/// columns, panel, periods) and its refusal, if any. A refusal is written into the record, not
/// thrown: the record keeps the periods that closed, the error in the engine's words and the full row
/// of the period before it.
fn bench_report(set: RuleSet, periods: u64) -> (Value, Option<BenchError>) {
    scenario_report(Scenario::Shipped, set, periods)
}

/// The head of a record: the shipped scenario's is the committed one; the twelve trades' names its
/// scenario, its compiler and what pays labor and seekers.
fn scenario_header(scenario: Scenario, set: RuleSet) -> Value {
    let mut head = country_bench::bench_header(set);
    if scenario == Scenario::TwelveTrades {
        let object = head.as_object_mut().expect("the header is an object");
        object.insert("bench".to_owned(), json!("country-opening-2026-11"));
        object.insert("scenario".to_owned(), json!(scenario.name()));
        object.insert("compiler".to_owned(), json!(scenario.compiler()));
        object.insert(
            "judged_against".to_owned(),
            json!("the bench's own baseline (twelve-trades-baseline.json), never a record of the shipped scenario"),
        );
        object.insert(
            "labor_cost".to_owned(),
            json!("The labor of a batch, in the products' costs, is its hours times the wage of the persons employed at the process's sites: the sum of wage times employed persons over the members paid a wage, divided by the sum of those persons, rounded down; a process with none takes the same average over the whole opening. A seeker whose pool pays no wage is offered its place's average wage, found the same way."),
        );
    }
    head
}

/// Plays up to `periods` closes of one scenario under one rule set: `bench_report` for any scenario.
fn scenario_report(scenario: Scenario, set: RuleSet, periods: u64) -> (Value, Option<BenchError>) {
    let (catalog, census) = scenario.captured();
    let mut bench =
        CountryBench::open_with(catalog.opening(), set, scenario.wages()).expect("the bench opens");
    let mut rows: Vec<Value> = Vec::new();
    let mut refusal = None;
    let mut total_nanos = 0_u128;
    for _ in 0..periods {
        let open = Opening::read(&census, bench.catalog(), bench.state());
        let stepped = match bench.step() {
            Ok(stepped) => stepped,
            Err(error) => {
                refusal = Some(error);
                break;
            }
        };
        let mut row = bench_row(&census, &open, &stepped, &bench);
        assert_eq!(row["period"], json!(stepped.period));
        total_nanos += stepped.elapsed.as_nanos();
        let elapsed_ms = u64::try_from(stepped.elapsed.as_millis()).expect("a short time");
        row.as_object_mut()
            .expect("a period row is an object")
            .insert("elapsed_ms".to_owned(), json!(elapsed_ms));
        rows.push(row);
    }
    let panel: Vec<Value> = census
        .panel
        .iter()
        .map(|county| json!({"name": county.name, "geoid": county.geoid, "rule": county.rule}))
        .collect();
    let mut record = scenario_header(scenario, set);
    let head = record.as_object_mut().expect("the header is an object");
    head.insert("columns".to_owned(), economy_health::bench_columns());
    head.insert("panel".to_owned(), json!(panel));
    head.insert("periods".to_owned(), json!(rows));
    if let Some(amount) = bench.no_earner_per_person() {
        let opening = catalog.opening();
        head.insert(
            "no_earner_per_person_micros".to_owned(),
            json!(amount.micro_units().to_string()),
        );
        let due = country_fund::no_earner_due_a_period(opening, amount).expect("the due figure");
        let bodies_cash = country_fund::public_bodies_cash(opening).expect("the bodies' cash");
        let reserve = if due > bodies_cash {
            "none: one period of the no-earner benefit is more than the country's public bodies hold between them"
        } else {
            "none: the fund opens with no cash"
        };
        head.insert("fund_reserve".to_owned(), json!(reserve));
        head.insert(
            "no_earner_due_a_period_micros".to_owned(),
            json!(due.to_string()),
        );
        head.insert(
            "public_bodies_cash_micros".to_owned(),
            json!(bodies_cash.to_string()),
        );
    }
    head.insert("total_ms".to_owned(), json!(total_nanos / 1_000_000));
    head.insert("slowest_period".to_owned(), slowest_period(&rows));
    let acted_lists = acted(&record);
    let head = record.as_object_mut().expect("the header is an object");
    head.insert("acted".to_owned(), acted_lists);
    if let Some(error) = &refusal {
        let before = rows.last().cloned().unwrap_or(Value::Null);
        head.insert(
            "refused".to_owned(),
            json!({
                "period": rows.len() + 1,
                "error": format!("{error:?}"),
                "row_before": before,
            }),
        );
    }
    (record, refusal)
}

/// The period with the greatest `elapsed_ms` (the first, on a tie) and that time.
fn slowest_period(rows: &[Value]) -> Value {
    let mut slowest: Option<(&Value, u64)> = None;
    for row in rows {
        let elapsed = row["elapsed_ms"].as_u64().expect("a timed row");
        if slowest.is_none_or(|(_, best)| elapsed > best) {
            slowest = Some((&row["period"], elapsed));
        }
    }
    slowest.map_or(
        Value::Null,
        |(period, elapsed_ms)| json!({"period": period, "elapsed_ms": elapsed_ms}),
    )
}

/// For each kind of the `rules` column, the periods in which its first count was not zero.
fn acted(record: &Value) -> Value {
    let mut lists: Map<String, Value> = Map::new();
    for row in record["periods"].as_array().expect("periods are a list") {
        for (kind, count) in row["rules"].as_object().expect("a rules column") {
            let first = count.as_array().map_or(count, |counts| &counts[0]);
            let list = lists.entry(kind.clone()).or_insert_with(|| json!([]));
            if first.as_u64().expect("a count") != 0 {
                list.as_array_mut()
                    .expect("a list")
                    .push(row["period"].clone());
            }
        }
    }
    Value::Object(lists)
}

fn bench_report_path(name: &str) -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../../reports/country-bench-2026-11-24")
        .join(name)
}

/// The rule sets, the baseline first, named by `COUNTRY_BENCH_SET` or all of them.
fn chosen_sets() -> Vec<RuleSet> {
    let all = [
        RuleSet::None,
        RuleSet::Market,
        RuleSet::NoSeekers,
        RuleSet::AllSix,
        RuleSet::AllSixWithBenefits,
    ];
    match std::env::var("COUNTRY_BENCH_SET") {
        Ok(name) => {
            let chosen: Vec<RuleSet> = all.into_iter().filter(|set| set.name() == name).collect();
            assert!(!chosen.is_empty(), "no rule set is named {name}");
            chosen
        }
        Err(_) => all.to_vec(),
    }
}

/// Every money total of a record's rows is equal: the bench's own check, seen again in the record.
fn assert_money_totals_equal(record: &Value) {
    let totals: Vec<&Value> = record["periods"]
        .as_array()
        .expect("periods")
        .iter()
        .map(|row| &row["money"]["total"])
        .collect();
    assert!(
        totals.iter().all(|total| *total == totals[0]),
        "the money total of every row is equal"
    );
}

#[test]
#[ignore = "writes the sets' records under reports/country-bench-2026-11-24/; COUNTRY_BENCH_SET=<name> plays one"]
fn record_country_bench_sets() {
    for set in chosen_sets() {
        let (record, refusal) = bench_report(set, 34);
        write_compact(&record, &bench_report_path(&format!("{}.json", set.name())));
        println!(
            "{}: {} rows",
            set.name(),
            record["periods"].as_array().map_or(0, Vec::len)
        );
        match refusal {
            Some(error) => println!("{}: refused: {error}", set.name()),
            None => assert_eq!(record["periods"].as_array().map(Vec::len), Some(34)),
        }
        assert_money_totals_equal(&record);
    }
}

/// The periods a long run's summary keeps: those of this list that exist, and the last.
const LONG_SUMMARY_PERIODS: [u64; 10] = [1, 2, 3, 4, 5, 13, 34, 100, 200, 400];

/// A record's head and `acted` with only the rows of the summary's periods.
fn long_summary(record: &Value) -> Value {
    rows_of(record, &LONG_SUMMARY_PERIODS)
}

/// A record whole but for its rows: only those of `keep` that exist, and the last.
fn rows_of(record: &Value, keep: &[u64]) -> Value {
    let rows = record["periods"].as_array().expect("periods are a list");
    let last = rows.last().map(|row| row["period"].clone());
    let kept: Vec<Value> = rows
        .iter()
        .filter(|row| {
            row["period"]
                .as_u64()
                .is_some_and(|period| keep.contains(&period))
                || Some(&row["period"]) == last.as_ref()
        })
        .cloned()
        .collect();
    let mut summary = record.clone();
    summary
        .as_object_mut()
        .expect("a record is an object")
        .insert("periods".to_owned(), json!(kept));
    summary
}

/// 400 periods (`COUNTRY_BENCH_LONG_PERIODS` sets the number) for the baseline and the set with
/// benefits. The whole records go under the target's tmp and are not committed; the summaries are.
#[test]
#[ignore = "400 periods; writes summaries under reports/country-bench-2026-11-24/"]
fn record_country_bench_long() {
    let periods: u64 = std::env::var("COUNTRY_BENCH_LONG_PERIODS")
        .map_or(400, |text| text.parse().expect("a number of periods"));
    for set in [RuleSet::None, RuleSet::AllSixWithBenefits] {
        let (record, refusal) = bench_report(set, periods);
        let whole = Path::new(env!("CARGO_TARGET_TMPDIR"))
            .join(format!("country-bench/long-{}.json", set.name()));
        let size = write_compact_unbounded(&record, &whole);
        let written: Value = serde_json::from_str(
            &std::fs::read_to_string(&whole).expect("the whole record is read back"),
        )
        .expect("the whole record is JSON");
        println!(
            "{}: whole record {} ({size} bytes, {} rows)",
            set.name(),
            whole.display(),
            written["periods"].as_array().map_or(0, Vec::len)
        );
        assert_eq!(written["periods"], record["periods"]);
        write_compact(
            &long_summary(&record),
            &bench_report_path(&format!("long-{}-summary.json", set.name())),
        );
        if let Some(error) = refusal {
            println!("{}: refused: {error}", set.name());
        }
        assert_money_totals_equal(&record);
    }
}

fn open_census(set: RuleSet) -> (CapturedEconomicCatalog, Census, CountryBench) {
    let input = economic_catalog::national_catalog_input();
    let wage = default_wage(&input);
    let catalog = CapturedEconomicCatalog::capture_national_campaign(input, campaign())
        .expect("the national campaign");
    let census = Census::new(catalog.opening(), wage);
    let bench = CountryBench::open(catalog.opening(), set).expect("the bench opens");
    (catalog, census, bench)
}

#[test]
fn a_market_policy_names_every_storable_need() {
    let catalog = pooled_catalog();
    let policy = country_rules::market_policy(catalog.opening(), RuleSet::Market)
        .expect("the labels are in the opening")
        .expect("the market set has a policy");
    assert_eq!(policy.paying_order.len(), 7);
    assert_eq!(policy.paying_order.len(), country_rules::PAYING_ORDER.len());
    assert!(!policy.plans_from_spare_money);
    assert_eq!(policy.adjustments.len(), 0);
    assert!(
        country_rules::market_policy(catalog.opening(), RuleSet::None)
            .expect("the baseline has no policy")
            .is_none()
    );
    let bench = CountryBench::open(catalog.opening(), RuleSet::Market)
        .expect("the catalog admits the policy");
    assert_eq!(
        bench
            .catalog()
            .market_clearing
            .as_ref()
            .map(|p| p.paying_order.len()),
        Some(7)
    );
}

/// The count of adjustment rows of each kind, in the order of the `rules` column's keys.
fn counted(period: &BenchPeriod) -> [u64; 8] {
    let mut counts = [0_u64; 8];
    for row in &period.adjustments {
        let at = match row {
            AdjustmentReceipt::HiringBound(_) => 0,
            AdjustmentReceipt::PlaceMove(_) => 1,
            AdjustmentReceipt::Stop(_) => 2,
            AdjustmentReceipt::RestingPrice(_) => 3,
            AdjustmentReceipt::RestingPriceToCost(_) => 4,
            AdjustmentReceipt::Restart(_) => 5,
            AdjustmentReceipt::OwnerSpare(_) => 6,
            AdjustmentReceipt::GoodsOffer(_) => 7,
        };
        counts[at] += 1;
    }
    counts
}

/// Pins the columns' arithmetic only: it passes when every rule does nothing.
#[test]
fn the_rule_columns_add_back() {
    let (_catalog, census, mut bench) = open_census(RuleSet::NoSeekers);
    let open = Opening::read(&census, bench.catalog(), bench.state());
    let stepped = bench.step().expect("the first period closes");
    let row = bench_row(&census, &open, &stepped, &bench);
    let counts = counted(&stepped);
    let rules = &row["rules"];
    let first = |key: &str| rules[key][0].as_u64().or_else(|| rules[key].as_u64());
    assert_eq!(first("hiring_bound"), Some(counts[0]));
    assert_eq!(first("moves"), Some(counts[1]));
    assert_eq!(first("stops"), Some(counts[2]));
    assert_eq!(first("resting_prices"), Some(counts[3]));
    assert_eq!(first("resting_to_cost"), Some(counts[4]));
    let restarts: u64 = (0..3)
        .map(|at| rules["restarts"][at].as_u64().expect("a count"))
        .sum();
    let not_tested = u64::try_from(
        stepped
            .adjustments
            .iter()
            .filter(|row| {
                matches!(row, AdjustmentReceipt::Restart(r) if r.test == RestartTest::NotTested)
            })
            .count(),
    )
    .expect("few rows");
    assert_eq!(
        restarts + not_tested,
        counts[5],
        "restarted + failed + no buyer + not tested = the restart rows"
    );
    assert_eq!(first("owner_spare"), Some(counts[6]));
    assert_eq!(first("goods_offers"), Some(counts[7]));
    assert_eq!(
        rules["spare_money_raised"].as_u64(),
        Some(stepped.spare_money_raised)
    );
    let short: u64 = row["markets"]
        .as_object()
        .expect("markets are an object")
        .values()
        .flat_map(|scopes| scopes.as_object().expect("scopes are an object").values())
        .map(|cell| cell[0].as_u64().expect("a count"))
        .sum();
    assert_eq!(
        short,
        u64::try_from(stepped.market_clearings.len()).expect("few rows")
    );
    let after_moves = row["jobs_after_moves"].as_object().expect("jobs by scope");
    for (scope, cells) in after_moves {
        let close = &row["jobs"][scope]["all"];
        assert_eq!(cells[0], close[2], "at work, {scope}");
        assert_eq!(cells[1], close[3], "looking, {scope}");
    }
    for scope in row["jobs"].as_object().expect("jobs by scope").keys() {
        assert!(
            after_moves.contains_key(scope),
            "jobs_after_moves lacks {scope}"
        );
    }
    println!(
        "NoSeekers period 1: rules {rules}; short markets {short}; spare money raised {}; took {:?}",
        stepped.spare_money_raised, stepped.elapsed
    );
}

/// Rule A6 is off in the Market set, so no policy is raised above its plan there.
#[test]
fn spare_money_raises_nothing_where_rule_a6_is_off() {
    let (_catalog, _census, mut bench) = open_census(RuleSet::Market);
    let stepped = bench.step().expect("the first period closes");
    assert_eq!(
        stepped.spare_money_raised, 0,
        "the Market set has no spare-money rule"
    );
}

#[test]
fn one_period_of_each_set_without_seekers_closes() {
    for set in [RuleSet::Market, RuleSet::NoSeekers] {
        let catalog = pooled_catalog();
        let mut bench = CountryBench::open(catalog.opening(), set).expect("the bench opens");
        let opening_money = economy_health::economy(bench.state())
            .book
            .total_cash_and_reserves()
            .expect("the book totals");
        let period = bench
            .step()
            .unwrap_or_else(|error| panic!("{}: {error}", set.name()));
        assert_eq!(period.receipts.resolve_tick, 1);
        let closing_money = economy_health::economy(bench.state())
            .book
            .total_cash_and_reserves()
            .expect("the book totals");
        assert_eq!(closing_money, opening_money, "{}", set.name());
        println!("{} period 1 took {:?}", set.name(), period.elapsed);
    }
}

/// Persons of every household cohort of a state.
fn state_persons(state: &MaterialCircuitState) -> u64 {
    economy_health::economy(state)
        .recurring
        .as_deref()
        .expect("the national opening has a recurring economy")
        .households
        .iter()
        .map(|cohort| cohort.persons)
        .sum()
}

/// Every pool of a place holds a member of every household of the place, and the opening's members
/// grow to the count Task 1 found.
#[test]
fn every_pool_has_a_member_for_each_household_of_its_place() {
    let catalog = pooled_catalog();
    let bench = CountryBench::open(catalog.opening(), RuleSet::AllSix).expect("the bench opens");
    let held: BTreeMap<_, _> = bench
        .members()
        .iter()
        .map(|pool| (pool.pool_id, pool))
        .collect();
    let mut total = 0_usize;
    for place in bench.places() {
        let households: BTreeSet<_> = place
            .pools
            .iter()
            .flat_map(|pool| held[pool].members.iter())
            .map(|member| member.binding().household_id())
            .collect();
        for pool in &place.pools {
            let in_pool: BTreeSet<_> = held[pool]
                .members
                .iter()
                .map(|member| member.binding().household_id())
                .collect();
            assert_eq!(in_pool, households, "a pool lacks a household of its place");
        }
    }
    for pool in bench.members() {
        total += pool.members.len();
    }
    assert_eq!(total, 67_509);
    let rows = country_seekers::seeker_rows(catalog.opening(), bench.places(), Wages::Default)
        .expect("the seekers' rows build");
    assert_eq!(rows.members.len(), 67_509 - 21_062);
    assert_eq!(rows.terms.len(), rows.members.len());
    assert_eq!(rows.hours.len(), rows.members.len());
}

/// The rows add no person, no labor force and no money, and the state with them encodes.
#[test]
fn the_seekers_rows_keep_every_person() {
    let catalog = pooled_catalog();
    let plain = CountryBench::open(catalog.opening(), RuleSet::None).expect("the bench opens");
    let seekers = CountryBench::open(catalog.opening(), RuleSet::AllSix).expect("the bench opens");
    assert_eq!(state_persons(seekers.state()), state_persons(plain.state()));
    let money = |state: &MaterialCircuitState| {
        economy_health::economy(state)
            .book
            .total_cash_and_reserves()
            .expect("the book totals")
    };
    assert_eq!(money(seekers.state()), money(plain.state()));
    let force = |bench: &CountryBench| -> u64 {
        bench
            .staffing()
            .pools()
            .iter()
            .map(|pool| pool.employed() + pool.reserve())
            .sum()
    };
    assert_eq!(force(&seekers), force(&plain));
    let held: u64 = seekers
        .members()
        .iter()
        .flat_map(|pool| pool.members.iter())
        .map(|member| member.employed() + member.reserve())
        .sum();
    assert_eq!(held, force(&seekers), "the members hold every person once");
    engine::encode_material_circuit_state(seekers.catalog(), seekers.state())
        .expect("the state with the seekers' rows encodes");
}

/// All six rules close the country's first period; the counts of each kind of row are printed.
#[test]
fn one_period_with_all_six_rules_closes() {
    let (_catalog, _census, mut bench) = open_census(RuleSet::AllSix);
    let stepped = bench.step().expect("the first period closes");
    let counts = counted(&stepped);
    let mut persons_moved = 0_u64;
    let mut held = 0_u64;
    let mut restarts = [0_u64; 4];
    for row in &stepped.adjustments {
        match row {
            AdjustmentReceipt::PlaceMove(m) => {
                persons_moved = persons_moved
                    .checked_add(m.persons)
                    .expect("the persons moved fit");
            }
            AdjustmentReceipt::Stop(s) if s.hold == StopHold::Held => held += 1,
            AdjustmentReceipt::Restart(r) => match r.test {
                RestartTest::NotTested => restarts[0] += 1,
                RestartTest::Failed => restarts[1] += 1,
                RestartTest::NoBuyer => restarts[2] += 1,
                RestartTest::Restarted => restarts[3] += 1,
            },
            _ => {}
        }
    }
    println!(
        "AllSix period 1: place moves {} ({persons_moved} persons moved); stops {} ({held} held); \
         hiring bounds {}; resting prices {}; resting-price-to-cost {}; restarts {} (not tested {}, \
         failed {}, no buyer {}, restarted {}); owner spare {}; goods offers {}; took {:?}",
        counts[1],
        counts[2],
        counts[0],
        counts[3],
        counts[4],
        counts[5],
        restarts[0],
        restarts[1],
        restarts[2],
        restarts[3],
        counts[6],
        counts[7],
        stepped.elapsed
    );
    assert_eq!(stepped.receipts.resolve_tick, 1);
}

/// A figure for the money tests: the amount does not matter to them, only that it is positive.
const TEST_PER_PERSON_MICROS: i128 = 1_000_000;

fn with_test_fund(opening: &EconomicOpening) -> EconomicOpening {
    country_fund::with_fund(opening, Currency::from_micro_units(TEST_PER_PERSON_MICROS))
        .expect("the fund is added")
}

fn opening_money(opening: &EconomicOpening) -> i128 {
    let cash = |amount: Currency| amount.micro_units();
    let institutions: i128 = opening
        .institutional_cash
        .iter()
        .map(|row| cash(row.cash))
        .sum();
    let sites: i128 = opening
        .sites
        .iter()
        .map(|site| cash(site.opening_cash))
        .sum();
    let households: i128 = opening
        .households
        .iter()
        .map(|household| cash(household.opening_cash))
        .sum();
    institutions + sites + households
}

/// The fund adds no money and takes none: the opening's total is the same, every domestic public body
/// keeps the cash it held, and the fund opens with none.
#[test]
fn the_fund_keeps_the_opening_s_money() {
    let catalog = pooled_catalog();
    let before = catalog.opening();
    let after = with_test_fund(before);
    assert_eq!(opening_money(&after), opening_money(before));
    let fund_id = AccountId::Public(country_fund::fund_account());
    let cash_of = |opening: &EconomicOpening| -> BTreeMap<AccountId, i128> {
        opening
            .institutional_cash
            .iter()
            .map(|row| (row.id, row.cash.micro_units()))
            .collect()
    };
    let held_before = cash_of(before);
    let mut held_after = cash_of(&after);
    let fund_cash = held_after.remove(&fund_id).expect("the fund has a row");
    assert_eq!(fund_cash, 0, "the fund opens with no cash");
    assert_eq!(
        held_after, held_before,
        "every body keeps exactly the cash it held"
    );
    println!(
        "{} bodies keep their cash; the fund opens with 0",
        held_after.len()
    );
}

/// Each payer's rows after the split sum to its rate before, basis by basis.
#[test]
fn the_split_taxes_keep_each_rate() {
    let catalog = pooled_catalog();
    let before = catalog.opening();
    let after = with_test_fund(before);
    let sums = |rows: &[TaxPolicy]| {
        let mut sums = BTreeMap::<(AccountId, TaxBasis), u64>::new();
        for row in rows {
            *sums.entry((row.payer, row.basis)).or_default() += u64::from(row.rate_bps);
        }
        sums
    };
    assert_eq!(
        sums(&after.institutions.taxes),
        sums(&before.institutions.taxes)
    );
    println!(
        "tax rows: {} before, {} after",
        before.institutions.taxes.len(),
        after.institutions.taxes.len()
    );
}

/// Each domestic household account is a recipient of exactly one of the two programs.
#[test]
fn every_domestic_account_is_in_one_program() {
    let catalog = pooled_catalog();
    let after = with_test_fund(catalog.opening());
    let programs = country_fund::program_recipients(&after);
    assert_eq!(programs.len(), 2);
    let no_earner: BTreeSet<_> = programs[country_fund::NO_EARNER].iter().copied().collect();
    let laid_off: BTreeSet<_> = programs[country_fund::LAID_OFF].iter().copied().collect();
    assert!(no_earner.is_disjoint(&laid_off));
    for household in &after.households {
        let domestic = household.location.to_string().starts_with("county:");
        let listed = u8::from(no_earner.contains(&household.principal_id))
            + u8::from(laid_off.contains(&household.principal_id));
        assert_eq!(listed, u8::from(domestic), "{}", household.location);
    }
    println!(
        "no_earner recipients {}; laid_off recipients {}",
        no_earner.len(),
        laid_off.len()
    );
}

/// The `no_earner` benefit reaches every domestic account with no earner (no member with anyone
/// employed, or no member at all); `laid_off` takes every other domestic account.
#[test]
fn the_no_earner_benefit_reaches_every_account_with_no_earner() {
    let catalog = pooled_catalog();
    let opening = catalog.opening();
    let after = with_test_fund(opening);
    let mut employed: BTreeMap<FinalDemandPrincipalId, u64> = BTreeMap::new();
    for member in opening.staffing.iter().flat_map(|pool| &pool.members) {
        *employed.entry(member.member.household_id()).or_default() += member.employed;
    }
    let programs = country_fund::program_recipients(&after);
    let no_earner = &programs[country_fund::NO_EARNER];
    let laid_off = &programs[country_fund::LAID_OFF];
    for account in no_earner {
        assert_eq!(
            employed.get(account).copied().unwrap_or(0),
            0,
            "a no_earner recipient has an earner"
        );
    }
    for account in laid_off {
        assert!(
            employed.get(account).copied().unwrap_or(0) > 0,
            "a laid_off recipient has no earner"
        );
    }
    let mut listed: Vec<_> = no_earner.iter().chain(laid_off).copied().collect();
    listed.sort_unstable();
    let mut domestic: Vec<_> = opening
        .households
        .iter()
        .filter(|household| household.location.to_string().starts_with("county:"))
        .map(|household| household.principal_id)
        .collect();
    domestic.sort_unstable();
    assert_eq!(listed, domestic);
}

/// The set with benefits closes the country's first period, and no program row is paid more than due.
#[test]
fn one_period_with_benefits_closes() {
    let (_catalog, _census, mut bench) = open_census(RuleSet::AllSixWithBenefits);
    let stepped = bench.step().expect("the first period closes");
    assert_eq!(stepped.receipts.resolve_tick, 1);
    for row in &stepped.public_programs {
        assert!(row.paid <= row.due, "a program row is paid more than due");
    }
    println!(
        "all-six-with-benefits period 1: {} program rows, no_earner {:?} micros a person, took {:?}",
        stepped.public_programs.len(),
        bench.no_earner_per_person().map(Currency::micro_units),
        stepped.elapsed
    );
}

/// The set with benefits closes the country's first three periods. Each period prints, for each of the two
/// programs, the rows, the sum due, the sum paid and the sum unfunded, and the fund's cash at that close.
#[test]
#[ignore = "three national periods with all six rules and benefits: about two minutes"]
fn three_periods_with_benefits_close() {
    let (_catalog, _census, mut bench) = open_census(RuleSet::AllSixWithBenefits);
    for period in 1..=3_u64 {
        let stepped = bench
            .step()
            .unwrap_or_else(|error| panic!("period {period} is refused: {error}"));
        assert_eq!(stepped.receipts.resolve_tick, period);
        let mut programs: BTreeMap<String, (usize, i128, i128, i128)> = BTreeMap::new();
        for row in &stepped.public_programs {
            let total = programs.entry(row.program.as_str().to_owned()).or_default();
            total.0 = total.0.checked_add(1).expect("the count of rows fits");
            total.1 = total
                .1
                .checked_add(row.due.micro_units())
                .expect("the sum due fits");
            total.2 = total
                .2
                .checked_add(row.paid.micro_units())
                .expect("the sum paid fits");
            total.3 = total
                .3
                .checked_add(row.unfunded.micro_units())
                .expect("the sum unfunded fits");
        }
        let fund_cash = economy_health::economy(bench.state())
            .book
            .cash(AccountId::Public(country_fund::fund_account()))
            .map(Currency::micro_units)
            .expect(
                "the fund's account is held at the close: a missing account is a failure, not 0",
            );
        for (program, (rows, due, paid, unfunded)) in &programs {
            println!(
                "period {period} {program}: rows {rows}, due {due}, paid {paid}, unfunded {unfunded} micros"
            );
        }
        println!("period {period} fund cash at the close: {fund_cash} micros");
    }
}

/// One period of each set built so far, timed, beside the baseline's.
#[test]
#[ignore = "writes reports/country-bench-2026-11-24/timings.json"]
fn record_country_bench_timings() {
    let mut rows = Vec::new();
    let mut baseline = 0_u128;
    for set in [
        RuleSet::None,
        RuleSet::Market,
        RuleSet::NoSeekers,
        RuleSet::AllSix,
        RuleSet::AllSixWithBenefits,
    ] {
        let catalog = pooled_catalog();
        let mut bench = CountryBench::open(catalog.opening(), set).expect("the bench opens");
        let period = bench
            .step()
            .unwrap_or_else(|error| panic!("{}: {error}", set.name()));
        let nanos = period.elapsed.as_nanos();
        if matches!(set, RuleSet::None) {
            baseline = nanos;
        }
        assert!(
            baseline > 0,
            "the baseline period took no time to divide by"
        );
        let ratio = nanos * 10_000 / baseline;
        let elapsed_ms = u64::try_from(period.elapsed.as_millis()).expect("a short time");
        println!(
            "{:<12} {elapsed_ms:>8} ms {ratio:>8} bps of the baseline",
            set.name()
        );
        rows.push(json!({
            "set": set.name(),
            "elapsed_ms": elapsed_ms,
            "ratio_to_baseline_bps": u64::try_from(ratio).expect("a small ratio"),
        }));
    }
    let record = json!({
        "bench": "country-bench-2026-11-24",
        "periods_timed": 1,
        "sets": rows,
    });
    let path = bench_report_path("timings.json");
    std::fs::create_dir_all(path.parent().expect("a directory")).expect("the directory is made");
    let text = serde_json::to_string_pretty(&record).expect("the record serializes");
    std::fs::write(path, text + "\n").expect("the record is written");
}

/// The sites of public provisioning at the opening, by scope: all, and those funded by a grant.
/// The lead measured 977 (976 with a grant): 959 domestic (958), 6 in dependencies, 12 foreign.
#[test]
fn the_country_s_public_providers() {
    let (_catalog, census, bench) = open_census(RuleSet::None);
    let providers = economy_health::public_providers(&census, bench.state());
    let count = |scope: &str, granted: bool| {
        providers
            .values()
            .filter(|p| (scope.is_empty() || p.scope == scope) && (!granted || p.grant))
            .count()
    };
    let figures = [
        count("", false),
        count("", true),
        count("domestic", false),
        count("domestic", true),
        count("dependency", false),
        count("foreign", false),
    ];
    println!("public providers [all, granted, domestic, domestic granted, dependency, foreign]: {figures:?}");
    assert_eq!(figures, [977, 976, 959, 958, 6, 12]);
}

/// In the first period with all six rules, the `public` column holds every public-provider receipt of
/// each kind, split in two, and the persons at work at their pools.
#[test]
fn the_public_column_adds_back() {
    let (_catalog, census, mut bench) = open_census(RuleSet::AllSix);
    let open = Opening::read(&census, bench.catalog(), bench.state());
    let stepped = bench.step().expect("the first period closes");
    let row = bench_row(&census, &open, &stepped, &bench);
    let public = &row["public"];
    let providers = open.providers();
    let sum = |key: &str| -> u64 {
        public[key]
            .as_array()
            .expect("a pair")
            .iter()
            .map(|cell| cell.as_u64().expect("a count"))
            .sum()
    };
    let mut want = [0_u64; 7];
    for receipt in &stepped.adjustments {
        match receipt {
            AdjustmentReceipt::Stop(r) if providers.contains_key(&r.site_id) => {
                want[0] += 1;
                want[1] += u64::from(r.hold == StopHold::Held);
            }
            AdjustmentReceipt::HiringBound(r)
                if providers.contains_key(&r.site_id) && r.bound_hours < r.asked_hours =>
            {
                want[2] += 1;
            }
            AdjustmentReceipt::RestingPrice(r) if providers.contains_key(&r.site_id) => {
                want[3] += 1;
            }
            AdjustmentReceipt::RestingPriceToCost(r) if providers.contains_key(&r.site_id) => {
                want[4] += 1;
            }
            AdjustmentReceipt::Restart(r)
                if providers.contains_key(&r.site_id) && r.test != RestartTest::NotTested =>
            {
                want[5] += 1;
            }
            _ => {}
        }
    }
    assert_eq!(sum("stops"), want[0], "stop rows");
    assert_eq!(sum("stops_held"), want[1], "held stop rows");
    assert_eq!(
        sum("hiring_bound_below"),
        want[2],
        "hiring bound rows below asked"
    );
    assert_eq!(sum("resting"), want[3], "resting price rows");
    assert_eq!(sum("raised"), want[4], "resting price to cost rows");
    let restarts: u64 = public["restarts"]
        .as_array()
        .expect("a pair")
        .iter()
        .flat_map(|side| side.as_array().expect("three counts"))
        .map(|cell| cell.as_u64().expect("a count"))
        .sum();
    assert_eq!(restarts, want[5], "tested restart rows");
    let sites: BTreeMap<_, _> = bench
        .staffing()
        .pools()
        .iter()
        .map(|pool| (pool.binding().pool_id(), pool.binding().site_id()))
        .collect();
    let employed: u64 = stepped
        .closing_members
        .iter()
        .filter(|held| providers.contains_key(&sites[&held.pool_id]))
        .flat_map(|held| &held.members)
        .map(StaffingMemberState::employed)
        .sum();
    assert_eq!(sum("at_work"), employed, "persons at work");
    println!("AllSix period 1: public {public}");
}

/// In the first period with benefits, the `benefits` column holds every program receipt.
#[test]
fn the_benefits_column_adds_back() {
    let (_catalog, census, mut bench) = open_census(RuleSet::AllSixWithBenefits);
    let open = Opening::read(&census, bench.catalog(), bench.state());
    let stepped = bench.step().expect("the first period closes");
    let row = bench_row(&census, &open, &stepped, &bench);
    let benefits = &row["benefits"];
    let keys = [country_fund::NO_EARNER, country_fund::LAID_OFF];
    let total = |at: usize| -> i128 {
        keys.iter()
            .map(|key| {
                let cell = &benefits[*key][at];
                cell.as_str().map_or_else(
                    || i128::from(cell.as_u64().expect("a count")),
                    |text| text.parse::<i128>().expect("a money figure"),
                )
            })
            .sum()
    };
    assert_eq!(
        total(0),
        i128::try_from(stepped.public_programs.len()).expect("few rows")
    );
    let rules = &row["rules"]["programs"];
    let figure = |cell: &Value| {
        cell.as_str()
            .expect("money")
            .parse::<i128>()
            .expect("micros")
    };
    assert_eq!(total(2), figure(&rules[1]), "paid");
    assert_eq!(total(3), figure(&rules[2]), "unfunded");
    for key in keys {
        let cell = &benefits[key];
        let part = |at: usize| figure(&cell[at]);
        assert_eq!(part(1), part(2) + part(3), "{key}: due = paid + unfunded");
    }
    assert!(benefits["fund_cash_micros"].is_string());
    println!("AllSixWithBenefits period 1: public {}", row["public"]);
    println!("AllSixWithBenefits period 1: benefits {benefits}");
}

/// One period of a set as the pin keeps it: set, period, state digest in hex, adjustment receipts, market clearings.
type PinnedPeriod = (&'static str, u64, String, usize, usize);

/// The state's digest in lowercase hex.
fn digest_hex(bench: &CountryBench) -> String {
    let digest = engine::material_circuit_state_digest(bench.catalog(), bench.state())
        .expect("the state digests");
    digest.iter().fold(String::new(), |mut out, byte| {
        let _ = write!(out, "{byte:02x}");
        out
    })
}

/// What the bench's periods were before the squares of the engine were mended, filled in once from the first run.
const PINNED: &[(&str, u64, &str, usize, usize)] = &[
    (
        "baseline",
        1,
        "5c5c7a178e2a10c66a16f6ccc79357e7c694697d468a235e3696af6577f54c71",
        0,
        0,
    ),
    (
        "baseline",
        2,
        "1b0c9c574a31100469f6e1b511362511089ca0c2c39181aba4ce7b80a774747a",
        0,
        0,
    ),
    (
        "market",
        1,
        "175e2c2f1e4256f398b788cc3c2c789cdacc0c2ebd0641fa73bd1e493ca2d861",
        0,
        728,
    ),
    (
        "market",
        2,
        "adb6ee9c296a21c32c1ae426523d73861443f3f64adb57f86239a6e20e37daf8",
        0,
        949,
    ),
    (
        "no-seekers",
        1,
        "cc54c0741fe27efc04b84f91bbcf5cc05a4d46802819b7dd48c9f8d1a8297dbb",
        8873,
        728,
    ),
    (
        "no-seekers",
        2,
        "bcfe71102958e762858a1398c85789d3013a117cf24721165d382dd376d621ce",
        8873,
        953,
    ),
    (
        "all-six",
        1,
        "212af063b5ea7f1fb5bfae2501d1def17a71488acf220edb7791f320e4156964",
        17427,
        728,
    ),
    (
        "all-six",
        2,
        "b69d9919d443d9620b62385b782ea8fda1211addeffec46c019e07c172f71c5f",
        17426,
        954,
    ),
    (
        "all-six",
        3,
        "9eae057310424a8802a5d93714f5c32ec6322d4629efe6f1985ec6b17a472b90",
        24373,
        976,
    ),
    (
        "all-six",
        4,
        "07c0f1aab5343e7724df3f6f61f8c1e78d8b4d7c07f1db2d35ceb58133157d77",
        27023,
        1057,
    ),
    (
        "all-six",
        5,
        "08d47735dd9ffe02d196fb80a031d5a81c16c632c3016dd1382ad8dfd0cac550",
        27126,
        1059,
    ),
    (
        "all-six-with-benefits",
        1,
        "da772b3785b2dbc720d29e2aae6eb017324f3aa89360e8cd4bd4fe31f2ba1e76",
        17427,
        728,
    ),
    (
        "all-six-with-benefits",
        2,
        "c84553610800183bc1895b82e41f3d6053481f74bd505183eedf6a265207ad19",
        17426,
        964,
    ),
    (
        "all-six-with-benefits",
        3,
        "cbc2bf208a42c2bb14254eabcc4d8ca1cb47bb6f7fb9bf9a6b0b966ef47fd489",
        24372,
        1030,
    ),
    (
        "all-six-with-benefits",
        4,
        "11fc758dc82f783e33e72caf764647a1630de64560f30d69a2ccf35eaa43834f",
        26995,
        1095,
    ),
    (
        "all-six-with-benefits",
        5,
        "e9945af51e2e43244ba1098728acb077e44313e93d46853cb5420318f7baf288",
        27124,
        1099,
    ),
];

/// The bench's own periods before the squares of the engine are mended: the state's digest, the adjustment
/// receipts and the market clearings of each period, for every set. The restart tests nothing before period
/// 3, so the sets with the stop rule step five periods.
#[test]
#[ignore = "national periods of every set; run by Task 7's gate"]
fn the_bench_digests_before_the_squares() {
    let mut actual: Vec<PinnedPeriod> = Vec::new();
    for (set, periods) in [
        (RuleSet::None, 2_u64),
        (RuleSet::Market, 2),
        (RuleSet::NoSeekers, 2),
        (RuleSet::AllSix, 5),
        (RuleSet::AllSixWithBenefits, 5),
    ] {
        let catalog = pooled_catalog();
        let mut bench = CountryBench::open(catalog.opening(), set).expect("the bench opens");
        for _ in 0..periods {
            let period = bench
                .step()
                .unwrap_or_else(|error| panic!("{}: {error}", set.name()));
            actual.push((
                set.name(),
                period.period,
                digest_hex(&bench),
                period.adjustments.len(),
                period.market_clearings.len(),
            ));
        }
    }
    let expected: Vec<PinnedPeriod> = PINNED
        .iter()
        .map(|&(set, period, digest, adjustments, clearings)| {
            (set, period, digest.to_string(), adjustments, clearings)
        })
        .collect();
    assert_eq!(actual, expected, "the bench's periods");
}

/// The country bench's records of the twelve-trade scenario.
fn twelve_trades_path(name: &str) -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../../reports/country-opening-2026-11")
        .join(name)
}

/// The sets the twelve trades are recorded under (`TWELVE_TRADES_SET=<name>` plays one): the
/// scenario's own policy is the baseline and the `market` set would be the same run.
fn twelve_trades_sets() -> Vec<RuleSet> {
    let all = [RuleSet::None, RuleSet::AllSix, RuleSet::AllSixWithBenefits];
    match std::env::var("TWELVE_TRADES_SET") {
        Ok(name) => {
            let chosen: Vec<RuleSet> = all.into_iter().filter(|set| set.name() == name).collect();
            assert!(!chosen.is_empty(), "no rule set is named {name}");
            chosen
        }
        Err(_) => all.to_vec(),
    }
}

/// What the twelve trades' opening holds, counted as `the_country_s_sizes` counts the shipped one.
#[test]
fn the_twelve_trades_sizes() {
    let (catalog, _census) = Scenario::TwelveTrades.captured();
    let opening = catalog.opening();
    let compiled = opening
        .compile()
        .expect("the twelve-trade opening compiles");
    let sizes = country_sizes::country_sizes(opening, &compiled);
    println!(
        "members_with_seekers {} against SEEKER_BOUND {SEEKER_BOUND}: {}",
        sizes.members_with_seekers,
        if sizes.members_with_seekers <= SEEKER_BOUND {
            "fits"
        } else {
            "does not fit"
        }
    );
    for (key, place) in busiest_places(&sizes) {
        println!("{} {place:?}", key.0);
    }
    println!("{sizes:#?}");
    assert!(
        sizes.members_with_seekers <= SEEKER_BOUND,
        "the seekers' rows do not fit: stop and report"
    );
    assert_eq!(
        sum(sizes.workplaces_by_scope.values().copied()),
        u64::try_from(opening.sites.len()).expect("a count")
    );
    assert_eq!(
        sizes.seeker_rows,
        sum(sizes.by_place.values().map(|p| p.seeker_rows))
    );
    assert_eq!(sizes.places_with_households, 187);
    assert_eq!(
        sizes.workplaces_by_scope,
        BTreeMap::from([("dependency", 72), ("domestic", 8475), ("foreign", 144)])
    );
    assert_eq!(
        sizes.household_accounts_by_scope,
        BTreeMap::from([("dependency", 6), ("domestic", 1584), ("foreign", 12)])
    );
    assert_eq!(sizes.pools, 8691);
    assert_eq!(sizes.members, 23877);
    assert_eq!(sizes.employment_terms, 23877);
    assert_eq!(sizes.member_labor_rows, 23877);
    assert_eq!(sizes.offers_goods, 2436);
    assert_eq!(sizes.offers_services, 5914);
    assert_eq!(sizes.market_rows_at_most, 10786);
    assert_eq!(sizes.members_outside_their_place, 0);
    assert_eq!(sizes.seeker_rows, 78715);
    assert_eq!(sizes.members_with_seekers, 78763);
}

/// The twelve trades open on the bench: the baseline closes one period under the scenario's own policy,
/// and the bench's own checks (money, persons, the labor force) pass.
#[test]
fn the_twelve_trades_open_on_the_bench() {
    let (catalog, _census) = Scenario::TwelveTrades.captured();
    assert!(
        catalog.opening().market_clearing.is_some(),
        "schema 8 names its own order of paying"
    );
    let mut bench = CountryBench::open_with(
        catalog.opening(),
        RuleSet::None,
        Scenario::TwelveTrades.wages(),
    )
    .expect("the bench opens");
    let money_of = |state: &MaterialCircuitState| {
        economy_health::economy(state)
            .book
            .total_cash_and_reserves()
            .expect("the book totals")
            .micro_units()
    };
    let opening_money = money_of(bench.state());
    let period = bench.step().expect("the first period closes");
    println!("one baseline period took {:?}", period.elapsed);
    assert_eq!(period.receipts.resolve_tick, 1);
    assert_eq!(money_of(bench.state()), opening_money);
    assert_ne!(period.receipts.staffing_members.len(), 0);
}

/// One period of each set, timed, for the twelve trades.
#[test]
#[ignore = "writes reports/country-opening-2026-11/twelve-trades-timings.json"]
fn record_twelve_trades_timings() {
    let mut rows = Vec::new();
    let mut baseline = 0_u128;
    for set in [
        RuleSet::None,
        RuleSet::NoSeekers,
        RuleSet::AllSix,
        RuleSet::AllSixWithBenefits,
    ] {
        let (catalog, _census) = Scenario::TwelveTrades.captured();
        let mut bench =
            CountryBench::open_with(catalog.opening(), set, Scenario::TwelveTrades.wages())
                .expect("the bench opens");
        match bench.step() {
            Ok(period) => {
                let nanos = period.elapsed.as_nanos();
                if matches!(set, RuleSet::None) {
                    baseline = nanos;
                }
                assert!(
                    baseline > 0,
                    "the baseline period took no time to divide by"
                );
                let ratio = nanos * 10_000 / baseline;
                let elapsed_ms = u64::try_from(period.elapsed.as_millis()).expect("a short time");
                println!(
                    "{:<12} {elapsed_ms:>8} ms {ratio:>8} bps of the baseline",
                    set.name()
                );
                rows.push(json!({
                    "set": set.name(),
                    "elapsed_ms": elapsed_ms,
                    "ratio_to_baseline_bps": u64::try_from(ratio).expect("a small ratio"),
                }));
            }
            Err(error) => {
                println!("{}: refused: {error}", set.name());
                rows.push(json!({"set": set.name(), "refused": format!("{error:?}")}));
            }
        }
    }
    let record = json!({
        "bench": "country-opening-2026-11",
        "scenario": Scenario::TwelveTrades.name(),
        "periods_timed": 1,
        "sets": rows,
    });
    let path = twelve_trades_path("twelve-trades-timings.json");
    std::fs::create_dir_all(path.parent().expect("a directory")).expect("the directory is made");
    let text = serde_json::to_string_pretty(&record).expect("the record serializes");
    std::fs::write(path, text + "\n").expect("the record is written");
}

/// 34 periods of the baseline, of all six rules and of all six with benefits. A record over the
/// hygiene budget is written whole under the target's tmp, and its rows of the summary's periods are
/// committed instead.
#[test]
#[ignore = "writes the twelve trades' records under reports/country-opening-2026-11/; TWELVE_TRADES_SET=<name> plays one"]
fn record_twelve_trades_sets() {
    for set in twelve_trades_sets() {
        let (record, refusal) = scenario_report(Scenario::TwelveTrades, set, 34);
        let name = format!("twelve-trades-{}", set.name());
        let whole =
            Path::new(env!("CARGO_TARGET_TMPDIR")).join(format!("country-opening/{name}.json"));
        let size = write_compact_unbounded(&record, &whole);
        println!(
            "{}: {} rows, whole record {} bytes at {}",
            set.name(),
            record["periods"].as_array().map_or(0, Vec::len),
            size,
            whole.display()
        );
        if size < 1_048_576 {
            write_compact(&record, &twelve_trades_path(&format!("{name}.json")));
        } else {
            write_compact(
                &rows_of(&record, &SUMMARY_PERIODS),
                &twelve_trades_path(&format!("{name}-summary.json")),
            );
        }
        match refusal {
            Some(error) => println!("{}: refused: {error}", set.name()),
            None => assert_eq!(record["periods"].as_array().map(Vec::len), Some(34)),
        }
        assert_money_totals_equal(&record);
    }
}
