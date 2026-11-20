//! Household units in Wayne: what the pooled budget groups hold and are paid today, read from the
//! engine's own accounts.
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};
use babylon_material_circuit::FinalDemandPrincipalId;
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
use std::path::{Path, PathBuf};
use uuid::Uuid;

#[path = "support/economy_health.rs"]
mod economy_health;
#[path = "support/household_accounts.rs"]
mod household_accounts;
#[path = "support/supply_chain.rs"]
mod supply_chain;

use economy_health::{Census, Opening};
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
        let open = Opening::read(&census, &session);
        let receipts = close_period_with(&mut session, period, |_, candidate| {
            material_world::decode_material_receipts(candidate.material().receipt_bytes())
                .expect("canonical material receipts")
        });
        rows.push(economy_health::period_record(
            &census, &open, &receipts, &session,
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

/// Writes a record one period to a line, with a trailing newline, under 1 MiB.
fn write_compact(report: &Value, path: &Path) {
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
    assert_eq!(economy_health::session_counts(&census, &session), seeded);
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
    let money = economy_health::money_record(&census, &session);
    let book: i128 = economy_health::economy(&session)
        .book
        .snapshot()
        .accounts
        .iter()
        .map(|row| row.cash.micro_units())
        .sum();
    assert_eq!(money["cash_total"], json!(book.to_string()));
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
const CANDIDATES: [(&str, &[(&str, &str)]); 4] = [
    ("shipped", &[]),
    ("A", &[SWEEP_OFF]),
    ("B", &[SWEEP_OFF, BUSINESS_SERVICES_48]),
    ("C", &[SWEEP_OFF, BUSINESS_SERVICES_48, EXTRACTION_16]),
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
