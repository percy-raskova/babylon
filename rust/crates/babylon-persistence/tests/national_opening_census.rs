//! The census of the twelve-trade opening: the game's workforce, bands, wages, places and foreign rows, read once
//! from the compiled fixture and committed as a gzipped, pinned table that the stage 5 builder reads.
use babylon_kernel::economic_location::EconomicLocation;
use babylon_material_circuit::AccountId;
use babylon_persistence::economic_catalog::{self, CapturedEconomicCatalog};
use babylon_persistence::identity::CampaignId;
use babylon_persistence::national_economy::NationalGamePolicy;
use babylon_persistence::national_trade_pay;
use serde_json::Value;
use std::collections::{BTreeMap, BTreeSet};
use std::fmt::Write as _;
use std::path::PathBuf;
use uuid::Uuid;

#[path = "support/opening_census.rs"]
mod opening_census;

use opening_census::{MAX_GZ_BYTES, MAX_JSON_BYTES};

/// The sha256 of the census text (never of the gzipped file): the builder names the census by it.
const CENSUS_TEXT_SHA256: &str = "efa195be9d8da65cd0d28ae5967639833c41cba94d1118e6c0896aeeb1b2b215";

const FIXTURE: &str = include_str!("fixtures/national_twelve_trades.defines.toml");

/// The campaign of the bench's records: the County Review's, with no organizer commitment.
fn campaign() -> CampaignId {
    CampaignId::from_uuid(Uuid::from_u128(0x0026_1631_7036))
}

fn committed_path() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../../src/babylon/data/reference/economy/national_opening_census_v13.json.gz")
}

/// The fixture as the census scenario compiles it, captured as the campaign compiler builds it.
fn captured() -> (CapturedEconomicCatalog, NationalGamePolicy, String) {
    let text = opening_census::census_scenario(FIXTURE);
    let policy = NationalGamePolicy::parse(&text).expect("the census scenario admits");
    let input = economic_catalog::national_catalog_input_for(text.as_bytes())
        .expect("the census scenario parses");
    let catalog = CapturedEconomicCatalog::capture_national_campaign(input, campaign())
        .expect("the census scenario captures");
    (catalog, policy, text)
}

fn census_of(catalog: &CapturedEconomicCatalog, policy: &NationalGamePolicy) -> Value {
    let pay = national_trade_pay::national_trade_pay_reference().expect("the pay table loads");
    opening_census::opening_census(catalog, policy, pay)
        .unwrap_or_else(|error| panic!("the census: {error}"))
}

fn number(value: &Value) -> u128 {
    u128::from(value.as_u64().expect("an integer"))
}

fn at<'a>(value: &'a Value, path: &[&str]) -> &'a Value {
    path.iter().fold(value, |at, step| &at[*step])
}

fn members(value: &Value) -> impl Iterator<Item = (&String, &Value)> {
    value.as_object().expect("an object").iter()
}

#[test]
fn the_census_scenario_makes_three_edits() {
    let text = opening_census::census_scenario(FIXTURE);
    let policy = NationalGamePolicy::parse(&text).expect("the census scenario admits");
    assert_eq!(
        policy.country_services,
        ["business_services", "leisure", "utility"]
    );
    let wants: Vec<_> = policy
        .household_wants
        .iter()
        .map(|want| (want.key.as_str(), want.units_per_basis))
        .collect();
    assert_eq!(
        wants,
        [
            ("business_services", 1),
            ("consumer_goods", 1),
            ("leisure", 1)
        ]
    );
    let handling = policy.commodities["consumer_goods"]
        .handling
        .expect("handling");
    assert_eq!((handling.hours, handling.units), (1, 1));
    // The text has one `country_services` line and three want rows, and nothing else of it moved.
    assert_eq!(text.matches("country_services").count(), 1);
    assert_eq!(text.matches("[[household_wants]]").count(), 3);
}

#[test]
fn the_census_scenario_replaces_what_the_text_has() {
    let own = FIXTURE
        .replacen(
            "[markets]\n",
            "[markets]\ncountry_services = [\n  \"housing\",\n]\n",
            1,
        )
        .replacen(
            "[commodity.consumer_goods]\n",
            "[commodity.consumer_goods]\nhandling_hours = 2\nhandling_units = 3\n",
            1,
        )
        + "\n[[household_wants]]\ngood = \"leisure\"\ntier = \"comfort\"\nbasis = \"persons\"\nunits_per_basis = 9\n";
    let text = opening_census::census_scenario(&own);
    let policy = NationalGamePolicy::parse(&text).expect("the census scenario admits");
    assert_eq!(
        policy.country_services,
        ["business_services", "leisure", "utility"]
    );
    assert_eq!(policy.household_wants.len(), 3);
    assert!(policy
        .household_wants
        .iter()
        .all(|want| want.units_per_basis == 1));
    let handling = policy.commodities["consumer_goods"]
        .handling
        .expect("handling");
    assert_eq!((handling.hours, handling.units), (2, 3));
}

#[test]
fn the_committed_census_is_the_opening_s() {
    let (catalog, policy, _) = captured();
    let fresh = opening_census::census_bytes(&census_of(&catalog, &policy));
    let committed = std::fs::read(committed_path()).expect("the committed census exists");
    assert!(committed.len() < MAX_GZ_BYTES);
    let text = opening_census::gunzip_text(&committed).expect("the committed census expands");
    assert!(
        text == fresh,
        "the committed census differs from the opening's: run the recorder"
    );
    assert_eq!(opening_census::sha_hex(&text), CENSUS_TEXT_SHA256);
}

/// The sum of one field over the nation's rows of `block` (`trades` or `households`).
fn nation(census: &Value, block: &str, field: &str) -> u128 {
    members(at(census, &[block]))
        .map(|(_, row)| number(&row[field]))
        .sum()
}

/// 316 parts over 187 hubs, each named by its hub.
fn check_parts(places: &Value) {
    assert_eq!(members(places).count(), 316);
    let hubs: BTreeSet<&str> = members(places)
        .map(|(_, part)| part["hub"].as_str().expect("a hub"))
        .collect();
    assert_eq!(hubs.len(), 187);
    for (label, part) in members(places) {
        let hub = part["hub"].as_str().expect("a hub");
        assert!(
            label == hub || label.starts_with(&format!("{hub}/")),
            "{label}"
        );
    }
}

/// The nation's keys and trades are the sums of the parts', and the persons at work are the same persons
/// counted by trade or by key.
fn check_sums(census: &Value) {
    let places = at(census, &["places"]);
    for (key, row) in members(at(census, &["households"])) {
        for field in [
            "households",
            "persons",
            "employed",
            "reserve",
            "wage_income_micros_per_period",
        ] {
            let sum: u128 = members(places)
                .map(|(_, part)| part["keys"].get(key).map_or(0, |k| number(&k[field])))
                .sum();
            assert_eq!(sum, number(&row[field]), "{key} {field}");
        }
    }
    for (name, row) in members(at(census, &["trades"])) {
        for field in [
            "employee_persons",
            "payroll_micros_per_period",
            "public_employee_persons",
            "public_payroll_micros_per_period",
        ] {
            let sum: u128 = members(places)
                .map(|(_, part)| number(&part["trades"][name][field]))
                .sum();
            assert_eq!(sum, number(&row[field]), "{name} {field}");
        }
    }
    assert_eq!(
        nation(census, "trades", "employee_persons")
            + nation(census, "trades", "working_owner_persons")
            + nation(census, "trades", "unpaid_family_persons"),
        nation(census, "households", "employed")
    );
    assert_eq!(
        nation(census, "trades", "payroll_micros_per_period"),
        nation(census, "households", "wage_income_micros_per_period")
    );
    // Every domestic person is served by one part's public providers.
    let served: u128 = members(places)
        .map(|(_, part)| number(&part["public_persons_served"]))
        .sum();
    assert_eq!(served, nation(census, "households", "persons"));
    let machines: u128 = members(places)
        .map(|(_, part)| number(&part["trades"]["public_provisioning"]["machines"]))
        .sum();
    assert_eq!(
        machines,
        number(at(census, &["trades", "public_provisioning", "machines"]))
    );
}

/// The force a rotation puts in each region, summed over regions, by trade.
fn force_by_trade(regions: &Value) -> BTreeMap<&str, u128> {
    let mut sums = BTreeMap::<&str, u128>::new();
    for (_, trades) in members(regions) {
        for (name, force) in members(trades) {
            *sums.entry(name.as_str()).or_default() += number(force);
        }
    }
    sums
}

/// The rotation reads the same sites for every good and every crossing service, and the shop goods' retail
/// assignment is the persons of the accounts that buy them.
fn check_rotation(census: &Value) {
    let mut forces = BTreeSet::new();
    for block in ["assignment", "crossing_force"] {
        let rows = if block == "assignment" {
            at(census, &[block, "sites"])
        } else {
            at(census, &[block])
        };
        for (_, regions) in members(rows) {
            forces.insert(force_by_trade(regions));
        }
    }
    assert_eq!(forces.len(), 1, "every rotation sums to the sites' force");
    for (name, force) in forces.iter().flatten() {
        assert!(*force <= number(at(census, &["trades", name, "force"])));
    }
    let persons = nation(census, "households", "persons");
    // A collective residence's need of materials is by household, which it has none of.
    let collective = number(at(
        census,
        &["households", "collective-residence", "persons"],
    ));
    for (good, regions) in members(at(census, &["assignment", "households"])) {
        let sum: u128 = members(regions).map(|(_, n)| number(n)).sum();
        let expected = match good.as_str() {
            "food" | "consumer_goods" => persons,
            "materials" => persons - collective,
            _ => 0,
        };
        assert_eq!(sum, expected, "{good}");
    }
}

#[test]
fn the_census_adds_up() {
    let (catalog, policy, _) = captured();
    let census = census_of(&catalog, &policy);
    check_parts(at(&census, &["places"]));
    check_sums(&census);
    check_rotation(&census);
    assert_eq!(
        at(&census, &["sources", "country_services"]),
        &serde_json::json!(["business_services", "leisure", "utility"])
    );
}

/// The state of a county location, as its first two digits.
fn state_of(location: EconomicLocation) -> Option<String> {
    location
        .to_string()
        .strip_prefix("county:")
        .map(|geoid| geoid[..2].to_owned())
}

/// For each country service, the accounts and persons dealt a provider in another state, over all.
fn out_of_state(catalog: &CapturedEconomicCatalog, policy: &NationalGamePolicy) -> String {
    let opening = catalog.opening();
    let sites: BTreeMap<_, _> = opening
        .sites
        .iter()
        .map(|s| (s.site_id, s.location))
        .collect();
    let accounts: BTreeMap<_, _> = opening
        .households
        .iter()
        .map(|h| {
            (
                AccountId::Household(h.principal_id),
                (h.location, h.persons),
            )
        })
        .collect();
    let mut text = String::new();
    for key in &policy.country_services {
        let good = &policy.commodities[key];
        let (mut rows, mut persons, mut out_rows, mut out_persons) = (0_u64, 0_u64, 0_u64, 0_u64);
        for row in &opening.policies.household_purchases {
            if (row.good_id, row.unit_id) != (good.good_id, good.unit_id) {
                continue;
            }
            let (at, people) = accounts[&AccountId::Household(row.principal_id)];
            let Some(home) = state_of(at) else { continue };
            rows += 1;
            persons += people;
            if state_of(sites[&row.retailer_site_id]).as_deref() != Some(home.as_str()) {
                out_rows += 1;
                out_persons += people;
            }
        }
        let _ = writeln!(
            text,
            "{key}: {out_rows} of {rows} accounts, {out_persons} of {persons} persons dealt a provider in another state"
        );
    }
    text
}

/// The figures Step 2 hands over, as text.
fn figures(
    census: &Value,
    catalog: &CapturedEconomicCatalog,
    policy: &NationalGamePolicy,
) -> String {
    let mut text = String::new();
    let places = at(census, &["places"]);
    let hubs: BTreeSet<&str> = members(places)
        .map(|(_, part)| part["hub"].as_str().expect("hub"))
        .collect();
    let _ = writeln!(
        text,
        "parts {} hubs {}",
        members(places).count(),
        hubs.len()
    );
    for (name, row) in members(at(census, &["trades"])) {
        let _ = writeln!(
            text,
            "trade {name}: employee {} owners {} unpaid {} force {} sites {} machines {} public {}",
            row["employee_persons"],
            row["working_owner_persons"],
            row["unpaid_family_persons"],
            row["force"],
            row["sites"],
            row["machines"],
            row["public_employee_persons"]
        );
    }
    for (key, row) in members(at(census, &["households"])) {
        let _ = writeln!(
            text,
            "key {key}: accounts {} households {} persons {} employed {} reserve {}",
            row["accounts"], row["households"], row["persons"], row["employed"], row["reserve"]
        );
    }
    let mut wages = BTreeMap::<&str, (u64, u64)>::new();
    for (_, part) in members(places) {
        for (_, sellers) in members(&part["sellers"]) {
            for (product, wage) in members(sellers) {
                let wage = wage.as_u64().expect("a wage");
                let slot = wages.entry(product.as_str()).or_insert((wage, wage));
                *slot = (slot.0.min(wage), slot.1.max(wage));
            }
        }
    }
    for (product, (low, high)) in &wages {
        let _ = writeln!(
            text,
            "seller wage {product}: lowest {low} highest {high} micros an hour"
        );
    }
    text.push_str(&out_of_state(catalog, policy));
    for good in ["food", "materials", "consumer_goods"] {
        let (mut with, mut all) = (0_u64, 0_u64);
        for (_, part) in members(places) {
            for (_, sellers) in members(&part["sellers"]) {
                if sellers.get(good).is_some() {
                    all += 1;
                }
            }
            for (_, abroad) in members(&part["abroad"]) {
                if abroad.get(good).is_some() {
                    with += 1;
                }
            }
        }
        let _ = writeln!(
            text,
            "shop good {good}: {with} of {all} seller rows have an abroad region"
        );
    }
    for (service, regions) in members(at(census, &["crossing_force"])) {
        for (region, trades) in members(regions) {
            let sum: u128 = members(trades).map(|(_, force)| number(force)).sum();
            let _ = writeln!(text, "crossing {service} {region}: force {sum}");
        }
    }
    text
}

#[test]
#[ignore = "writes src/babylon/data/reference/economy/national_opening_census_v13.json.gz; run once, by name"]
fn record_national_opening_census() {
    let (catalog, policy, _) = captured();
    let census = census_of(&catalog, &policy);
    let text = opening_census::census_bytes(&census);
    assert!(text.len() <= MAX_JSON_BYTES);
    let gzipped = opening_census::gzip_text(&text).expect("the census gzips");
    assert!(gzipped.len() < MAX_GZ_BYTES);
    assert_eq!(
        opening_census::gunzip_text(&gzipped).expect("it expands"),
        text
    );
    std::fs::write(committed_path(), &gzipped).expect("the census is written");
    println!(
        "census: {} bytes of text, {} bytes gzipped, {} places",
        text.len(),
        gzipped.len(),
        members(at(&census, &["places"])).count()
    );
    println!("text sha256 {}", opening_census::sha_hex(&text));
    println!("file sha256 {}", opening_census::sha_hex(&gzipped));
    println!("{}", figures(&census, &catalog, &policy));
}
