//! The twelve-trade national scenario (policy schema 8): its sources, its compiler and, in later tasks, its world.
use babylon_kernel::currency::Currency;
use babylon_kernel::economic_identity::{EconomicFunction, QcewOwnership, TradeSet};
use babylon_kernel::economic_location::{EconomicLocation, ForeignCounterpart};
use babylon_kernel::geography::CountyGeoid;
use babylon_material_circuit::{AccountId, LaborCompensation, SiteId};
use babylon_persistence::economic_catalog::EconomicSiteSeed;
use babylon_persistence::economic_catalog::{
    self, CapturedEconomicCatalog, EconomicCatalogError, EconomicCatalogInput, SourceArtifact,
    SourceArtifactKind as Kind,
};
use babylon_persistence::identity::CampaignId;
use babylon_persistence::national_cohorts::CohortKey;
use babylon_persistence::national_economy::{self, NationalGamePolicy, ResidentWorkplaceSource};
use babylon_persistence::national_household_allocation::{self, NationalHouseholdAllocation};
use babylon_persistence::national_household_allocation::{
    CountyHouseholdAllocation, HouseholdBudgetKey,
};
use babylon_persistence::national_household_refinement::{self, NationalHouseholdLeafRoster};
use babylon_persistence::national_resident_allocation::ResidentWorkplaceAllocation;
use babylon_persistence::{
    national_cohorts, national_counties, national_household_time_allocation, national_households,
    national_resident_allocation, national_resident_workforce, national_trade_pay,
};
use babylon_practice_contract::{Band, Roster};
use std::collections::{BTreeMap, BTreeSet};
use std::sync::OnceLock;
use uuid::Uuid;

const SHIPPED: &[u8] = include_bytes!("../../../../content/scenarios/national/defines.toml");
const FIXTURE: &[u8] = include_bytes!("fixtures/national_twelve_trades.defines.toml");
const COHORTS_V1: &[u8] = include_bytes!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../../src/babylon/data/reference/economy/national_cohort_reference_2024.csv.gz"
));
const MAPPING_V1: &[u8] = include_bytes!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../../contracts/national_qcew_function_mapping_v1.json"
));

fn row(input: &EconomicCatalogInput, kind: Kind) -> Option<&SourceArtifact> {
    input.sources.iter().find(|row| row.kind() == kind)
}

fn replace(input: &mut EconomicCatalogInput, kind: Kind, bytes: &[u8]) {
    let slot = input
        .sources
        .iter_mut()
        .find(|row| row.kind() == kind)
        .expect("the row exists");
    *slot = SourceArtifact::capture(kind, bytes.to_vec());
}

#[test]
fn the_shipped_input_keeps_its_sources() {
    let shipped = economic_catalog::national_catalog_input();
    let again =
        economic_catalog::national_catalog_input_for(SHIPPED).expect("the shipped defines parse");
    assert_eq!(shipped.sources.len(), 16);
    assert_eq!(again.sources.len(), shipped.sources.len());
    for (a, b) in shipped.sources.iter().zip(&again.sources) {
        assert_eq!((a.kind(), a.bytes()), (b.kind(), b.bytes()));
    }
    assert!(row(&again, Kind::NationalTradePay).is_none());
}

#[test]
fn the_fixture_input_carries_the_v2_sources() {
    let input = economic_catalog::national_catalog_input_for(FIXTURE).expect("the fixture parses");
    assert_eq!(input.sources.len(), 17);
    let cohorts = national_cohorts::national_cohort_reference_v2().expect("v2 cohorts");
    let pay = national_trade_pay::national_trade_pay_reference().expect("pay table");
    let digest = |kind| row(&input, kind).expect("the row exists").digest();
    assert_eq!(digest(Kind::NationalCohorts), cohorts.artifact_sha256());
    assert_eq!(
        digest(Kind::CohortFunctionMapping),
        cohorts.function_mapping_sha256()
    );
    assert_eq!(digest(Kind::NationalTradePay), pay.artifact_sha256());
    assert_eq!(
        row(&input, Kind::NationalGamePolicy)
            .expect("policy")
            .bytes(),
        FIXTURE
    );
    assert_eq!(
        input.sources.last().map(SourceArtifact::kind),
        Some(Kind::NationalTradePay)
    );
}

#[test]
fn a_twelve_trade_policy_with_ten_trade_tables_is_refused() {
    let mut input =
        economic_catalog::national_catalog_input_for(FIXTURE).expect("the fixture parses");
    replace(&mut input, Kind::NationalCohorts, COHORTS_V1);
    replace(&mut input, Kind::CohortFunctionMapping, MAPPING_V1);
    assert_eq!(
        CapturedEconomicCatalog::capture(input, None).err(),
        Some(EconomicCatalogError::Source(Kind::NationalCohorts))
    );
    let mut input =
        economic_catalog::national_catalog_input_for(FIXTURE).expect("the fixture parses");
    input
        .sources
        .retain(|row| row.kind() != Kind::NationalTradePay);
    assert_eq!(
        CapturedEconomicCatalog::capture(input, None).err(),
        Some(EconomicCatalogError::Source(Kind::NationalTradePay))
    );
}

#[test]
fn a_ten_trade_policy_refuses_the_pay_table() {
    let mut input = economic_catalog::national_catalog_input();
    input.sources.push(SourceArtifact::capture(
        Kind::NationalTradePay,
        b"not the pay table".to_vec(),
    ));
    assert_eq!(
        CapturedEconomicCatalog::capture(input, None).err(),
        Some(EconomicCatalogError::UnexpectedSource(
            Kind::NationalTradePay
        ))
    );
}

#[test]
fn a_twelve_trade_policy_with_an_experiment_is_refused() {
    let mut input =
        economic_catalog::national_catalog_input_for(FIXTURE).expect("the fixture parses");
    let text = std::str::from_utf8(FIXTURE).expect("utf8").replacen(
        "[companies]",
        "[companies]\nexperiment_controller_count = 300",
        1,
    );
    assert_ne!(text.as_bytes(), FIXTURE);
    replace(&mut input, Kind::NationalGamePolicy, text.as_bytes());
    "national-company-scale-experiment".clone_into(&mut input.preset_id);
    assert_eq!(
        CapturedEconomicCatalog::capture(input, None).err(),
        Some(EconomicCatalogError::ExperimentOnTwelveTrades)
    );
}

fn household_budgets() -> NationalHouseholdAllocation {
    national_household_allocation::allocate_households(
        national_counties::national_county_reference().expect("the county reference loads"),
        national_households::national_household_reference().expect("the household reference loads"),
        national_resident_workforce::national_resident_workforce_reference()
            .expect("the workforce reference loads"),
        1_000,
        Some(4_000),
    )
    .expect("the households fit the authored cohorts")
}

fn empty_leaves(budgets: &NationalHouseholdAllocation) -> NationalHouseholdLeafRoster {
    let time = national_household_time_allocation::allocate_household_time(
        national_counties::national_county_reference().expect("the county reference loads"),
        budgets,
    )
    .expect("the household time fits the authored budget");
    national_household_refinement::refine_households(budgets, &time, &[])
        .expect("the household refinement succeeds")
}

#[test]
fn the_twelve_trade_source_allocation_fits_its_bounds() {
    let policy = NationalGamePolicy::parse(std::str::from_utf8(FIXTURE).expect("utf8"))
        .expect("the fixture admits");
    let budgets = household_budgets();
    let allocation = national_resident_allocation::allocate_home_county(
        national_counties::national_county_reference().expect("the county reference loads"),
        national_cohorts::national_cohort_reference_v2().expect("v2 cohorts"),
        national_resident_workforce::national_resident_workforce_reference()
            .expect("the workforce reference loads"),
        &budgets,
        &empty_leaves(&budgets),
        &policy,
        Some(national_trade_pay::national_trade_pay_reference().expect("pay table")),
    )
    .expect("the twelve-trade source allocation fits its own bounds");
    let members: usize = allocation.workplaces.iter().map(|w| w.members.len()).sum();
    assert!(allocation.workplaces.len() < 131_072);
    assert!(members < 262_144);
    assert_eq!(allocation.workplaces.len(), 68_281);
    assert_eq!(members, 111_544);
}

/// The fixture, captured once: every test below reads this one catalog.
fn captured() -> &'static CapturedEconomicCatalog {
    static CATALOG: OnceLock<CapturedEconomicCatalog> = OnceLock::new();
    CATALOG.get_or_init(|| {
        let input =
            economic_catalog::national_catalog_input_for(FIXTURE).expect("the fixture parses");
        CapturedEconomicCatalog::capture(input, None).expect("the fixture captures")
    })
}

fn county(code: &str) -> EconomicLocation {
    EconomicLocation::domestic_county(CountyGeoid::try_from(code).expect("county"))
        .expect("a domestic county")
}

fn site_named<'a>(catalog: &'a CapturedEconomicCatalog, name: &str) -> &'a EconomicSiteSeed {
    catalog
        .opening()
        .sites
        .iter()
        .find(|site| {
            matches!(&site.subject,
                babylon_graph::stable_element::StableElementKey::Node { local_name, .. }
                    if local_name == name)
        })
        .expect("the site exists")
}

/// The wage every employee of a site is paid; the figure must be one for all of them.
fn site_wage(catalog: &CapturedEconomicCatalog, site: SiteId) -> Option<Currency> {
    let mut wages = catalog
        .opening()
        .employment
        .iter()
        .filter(|term| term.site_id == site)
        .filter_map(|term| match term.compensation {
            LaborCompensation::Wage(wage) => Some(wage),
            _ => None,
        });
    let first = wages.next()?;
    assert!(wages.all(|w| w == first), "one wage for one site");
    Some(first)
}

#[test]
fn twelve_trades_open() {
    let catalog = captured();
    let opening = catalog.opening();
    for function in TradeSet::Twelve.functions() {
        assert!(
            opening
                .sites
                .iter()
                .any(|s| s.function == *function
                    && matches!(s.location, EconomicLocation::County(_))),
            "{function:?} has a domestic site"
        );
    }
    for function in [
        EconomicFunction::ConsumerGoods,
        EconomicFunction::LeisureHospitality,
    ] {
        assert!(
            opening
                .sites
                .iter()
                .any(|s| s.function == function && s.location == county("26163")),
            "{function:?} has a site in Wayne"
        );
    }
    assert_eq!(opening.recipes.len(), 11);
    assert_eq!(opening.commodities.len(), 12);
    assert_eq!(catalog.compiler_version(), "national-world-v13");
}

#[test]
fn wayne_car_plants_pay_their_observed_wage() {
    let catalog = captured();
    let site = site_named(catalog, "site-26163-consumer-goods-5");
    let pay = national_trade_pay::national_trade_pay_reference().expect("pay table");
    let row = pay
        .row(CohortKey {
            county: CountyGeoid::try_from("26163").expect("county"),
            function: Some(EconomicFunction::ConsumerGoods),
            ownership: QcewOwnership::Private,
        })
        .expect("Wayne's private consumer goods row");
    let terms: Vec<_> = catalog
        .opening()
        .employment
        .iter()
        .filter(|term| term.site_id == site.site_id)
        .collect();
    assert_ne!(terms.len(), 0, "Wayne's plant employs people");
    for term in terms {
        assert_eq!(
            term.compensation,
            LaborCompensation::Wage(row.hourly_wage().expect("a wage")),
            "every employment term pays the row's wage"
        );
    }
}

/// A site's ownership claims as first authored: the company layer keeps them as its sources.
fn claims(catalog: &CapturedEconomicCatalog, site: SiteId) -> Vec<(AccountId, u64)> {
    let sourced: Vec<_> = catalog
        .national_company_finances()
        .map(|finances| {
            finances
                .sources
                .iter()
                .filter(|source| source.site == site)
                .map(|source| (source.beneficiary, source.original_shares))
                .collect()
        })
        .unwrap_or_default();
    if !sourced.is_empty() {
        return sourced;
    }
    catalog
        .opening()
        .institutions
        .ownership
        .iter()
        .filter(|claim| claim.issuer_site_id == site)
        .map(|claim| (claim.beneficiary, claim.shares))
        .collect()
}

fn claim_shares(catalog: &CapturedEconomicCatalog, site: SiteId, beneficiary: AccountId) -> u64 {
    claims(catalog, site)
        .into_iter()
        .filter(|(who, _)| *who == beneficiary)
        .map(|(_, shares)| shares)
        .sum()
}

fn pooled(location: EconomicLocation) -> AccountId {
    AccountId::Household(national_economy::household_principal(
        location,
        HouseholdBudgetKey::PooledExternal,
    ))
}

fn all_shares(catalog: &CapturedEconomicCatalog, site: SiteId) -> u64 {
    claims(catalog, site)
        .into_iter()
        .map(|(_, shares)| shares)
        .sum()
}

/// Wayne's owner households: the principals of the budget keys that carry owner exposure.
fn wayne_owners() -> Vec<AccountId> {
    [
        HouseholdBudgetKey::EarningOwner,
        HouseholdBudgetKey::NoEarnerOwner,
    ]
    .into_iter()
    .map(|key| AccountId::Household(national_economy::household_principal(county("26163"), key)))
    .collect()
}

fn owners_shares(catalog: &CapturedEconomicCatalog, site: SiteId) -> u64 {
    let owners = wayne_owners();
    claims(catalog, site)
        .into_iter()
        .filter(|(who, _)| owners.contains(who))
        .map(|(_, shares)| shares)
        .sum()
}

#[test]
fn wayne_car_plants_carry_the_two_claims() {
    let catalog = captured();
    let japan = pooled(EconomicLocation::Foreign(ForeignCounterpart::Japan));
    let canada = pooled(EconomicLocation::Foreign(ForeignCounterpart::Canada));
    let wayne = site_named(catalog, "site-26163-consumer-goods-5");
    assert_eq!(claim_shares(catalog, wayne.site_id, japan), 2_000);
    assert_eq!(owners_shares(catalog, wayne.site_id), 8_000);
    assert_eq!(all_shares(catalog, wayne.site_id), 10_000);
    let canadian = catalog
        .opening()
        .sites
        .iter()
        .find(|s| {
            s.function == EconomicFunction::ConsumerGoods
                && s.location == EconomicLocation::Foreign(ForeignCounterpart::Canada)
        })
        .expect("Canada's consumer goods site");
    assert_eq!(claim_shares(catalog, canadian.site_id, canada), 8_000);
    assert_eq!(owners_shares(catalog, canadian.site_id), 2_000);
    assert_eq!(all_shares(catalog, canadian.site_id), 10_000);
    // Where each household account stands: a claim holder is foreign by its own location, not by
    // being a foreign counterpart's pooled account.
    let location_of: BTreeMap<_, _> = catalog
        .opening()
        .households
        .iter()
        .map(|row| (row.principal_id, row.location))
        .collect();
    for site in catalog.opening().sites.iter().filter(|s| {
        s.function == EconomicFunction::CapitalGoods
            && (s.location == county("26163")
                || s.location == EconomicLocation::Foreign(ForeignCounterpart::Canada))
    }) {
        assert_eq!(claim_shares(catalog, site.site_id, japan), 0);
        if site.location == EconomicLocation::Foreign(ForeignCounterpart::Canada) {
            assert_eq!(claim_shares(catalog, site.site_id, canada), 10_000);
        } else {
            for (who, _) in claims(catalog, site.site_id) {
                if let AccountId::Household(principal) = who {
                    let location = location_of
                        .get(&principal)
                        .expect("every household claim holder has an opening account");
                    assert!(
                        !matches!(location, EconomicLocation::Foreign(_)),
                        "Wayne's capital goods site has a foreign claimant at {location:?}"
                    );
                }
            }
        }
    }
}

#[test]
fn a_place_pays_its_counties_pay_over_jobs() {
    let catalog = captured();
    let witness = catalog.national_generation().expect("the witness");
    let pay = national_trade_pay::national_trade_pay_reference().expect("pay table");
    let mut by_site = BTreeMap::<SiteId, Vec<CohortKey>>::new();
    for incidence in &witness.source_incidence {
        if let ResidentWorkplaceSource::Qcew(key) = incidence.source {
            by_site
                .entry(incidence.destination_site)
                .or_default()
                .push(key);
        }
    }
    let (site, keys) = by_site
        .iter()
        .find(|(site, keys)| keys.len() >= 2 && site_wage(catalog, **site).is_some())
        .expect("a coarsened site of two or more source counties pays wages");
    let (payroll, jobs) = keys.iter().fold((0_u128, 0_u128), |(p, j), key| {
        let row = pay.row(*key).expect("the pay row");
        (p + u128::from(row.payroll_usd), j + u128::from(row.jobs))
    });
    assert!(jobs > 0);
    let expected = i128::try_from(payroll * 1_000_000 / (jobs * 2_080)).expect("fits");
    assert_eq!(
        site_wage(catalog, *site).expect("a wage").micro_units(),
        expected
    );
}

#[test]
fn a_representative_site_of_one_source_row_pays_the_place_wage() {
    let catalog = captured();
    let witness = catalog.national_generation().expect("the witness");
    let pay = national_trade_pay::national_trade_pay_reference().expect("pay table");
    let mut by_site = BTreeMap::<SiteId, Vec<CohortKey>>::new();
    for incidence in &witness.source_incidence {
        if let ResidentWorkplaceSource::Qcew(key) = incidence.source {
            if incidence.destination_site != incidence.source_site {
                by_site
                    .entry(incidence.destination_site)
                    .or_default()
                    .push(key);
            }
        }
    }
    let mut checked = 0;
    for (site, keys) in by_site.iter().filter(|(_, keys)| keys.len() == 1) {
        let Some(wage) = site_wage(catalog, *site) else {
            continue;
        };
        let row = pay.row(keys[0]).expect("the pay row");
        if row.jobs == 0 {
            continue;
        }
        let expected = i128::try_from(
            u128::from(row.payroll_usd) * 1_000_000 / (u128::from(row.jobs) * 2_080),
        )
        .expect("fits");
        assert_eq!(wage.micro_units(), expected, "{keys:?}");
        checked += 1;
    }
    assert!(checked > 0, "some one-row representative site was checked");
}

#[test]
fn a_fallback_workplace_pays_the_place_average() {
    let catalog = captured();
    let witness = catalog.national_generation().expect("the witness");
    let pay = national_trade_pay::national_trade_pay_reference().expect("pay table");
    let place_of = |county: CountyGeoid| {
        witness
            .counties
            .iter()
            .find(|c| c.controls.county == county)
            .expect("the county contributes")
            .destination
    };
    let mut checked = 0;
    let mut multi = 0;
    for incidence in witness.source_incidence.iter().filter(|i| {
        matches!(i.source, ResidentWorkplaceSource::ResidentEmployerFallback)
            && site_wage(catalog, i.destination_site).is_some()
    }) {
        let place = place_of(incidence.source_county);
        let counties: Vec<CountyGeoid> = witness
            .counties
            .iter()
            .filter(|c| c.destination == place)
            .map(|c| c.controls.county)
            .collect();
        let rows: Vec<_> = counties
            .iter()
            .flat_map(|county| pay.county_rows(*county))
            .collect();
        let jobs: u128 = rows.iter().map(|r| u128::from(r.jobs)).sum();
        let payroll: u128 = rows.iter().map(|r| u128::from(r.payroll_usd)).sum();
        let expected = if counties.len() == 1 || rows.is_empty() || jobs == 0 {
            pay.county_average(counties[0]).micro_units()
        } else {
            i128::try_from(payroll * 1_000_000 / (jobs * 2_080)).expect("fits")
        };
        assert_eq!(
            site_wage(catalog, incidence.destination_site)
                .expect("a wage")
                .micro_units(),
            expected,
            "a fallback site of {counties:?} pays its place's average"
        );
        checked += 1;
        multi += usize::from(counties.len() > 1);
    }
    assert!(checked > 0, "some fallback site was checked");
    assert!(
        multi > 0,
        "a fallback site of a multi-county place was checked"
    );
}

#[test]
fn foreign_plants_pay_a_fraction() {
    let catalog = captured();
    let pay = national_trade_pay::national_trade_pay_reference().expect("pay table");
    let site = catalog
        .opening()
        .sites
        .iter()
        .find(|s| {
            s.function == EconomicFunction::ConsumerGoods
                && s.location == EconomicLocation::Foreign(ForeignCounterpart::Canada)
        })
        .expect("Canada's consumer goods site");
    let expected = pay
        .national_wage(EconomicFunction::ConsumerGoods)
        .micro_units()
        * 8_333
        / 10_000;
    assert_eq!(
        site_wage(catalog, site.site_id)
            .expect("a wage")
            .micro_units(),
        expected
    );
}

/// The fixture captured as a campaign, once: the City PD and the county review read its opening.
fn campaign_catalog() -> &'static CapturedEconomicCatalog {
    static CATALOG: OnceLock<CapturedEconomicCatalog> = OnceLock::new();
    CATALOG.get_or_init(|| {
        let input =
            economic_catalog::national_catalog_input_for(FIXTURE).expect("the fixture parses");
        CapturedEconomicCatalog::capture_national_campaign(
            input,
            CampaignId::from_uuid(Uuid::from_u128(0x0026_1631_7036)),
        )
        .expect("the fixture captures as a campaign")
    })
}

#[test]
fn the_going_wage_is_wayne_average_pay() {
    let catalog = campaign_catalog();
    let pay = national_trade_pay::national_trade_pay_reference().expect("pay table");
    let wayne = CountyGeoid::try_from("26163").expect("Wayne");
    let config = catalog
        .county_review_config()
        .expect("the campaign carries the county review");
    assert_eq!(
        config.going_wage_micros,
        pay.county_average(wayne).micro_units()
    );
}

#[test]
fn the_city_pd_pays_its_payroll_site() {
    let catalog = campaign_catalog();
    let config = catalog.city_pd_config().expect("the City PD");
    let site = catalog
        .opening()
        .sites
        .iter()
        .find(|site| site.site_id.as_bytes() == config.payroll_site_account_id)
        .expect("the payroll site exists");
    let rate = site_wage(catalog, site.site_id).expect("the payroll site pays a wage");
    assert_eq!(config.hourly_wage_micros, rate.micro_units());
    let positions = i128::from(config.payroll_positions);
    assert_eq!(
        config.payroll_micros,
        positions * i128::from(config.payroll_hours_per_position) * rate.micro_units()
    );
    assert_eq!(config.payroll_hours_per_position, 160);
}

const BAND_KEYS: [HouseholdBudgetKey; 3] = [
    HouseholdBudgetKey::EarningOwner,
    HouseholdBudgetKey::EarningLowerPaidHalf,
    HouseholdBudgetKey::EarningBetterPaidForty,
];

/// The domains that carry the three earning accounts, pinned once from a run.
const PLACES: u64 = 316;

#[test]
fn every_place_has_three_earning_accounts() {
    let catalog = captured();
    let accounts: BTreeMap<_, _> = catalog
        .opening()
        .households
        .iter()
        .map(|row| (row.principal_id, row))
        .collect();
    let witness = catalog
        .national_generation()
        .expect("the generation witness");
    // No county is missing from the household incidence, and none is extra.
    let incident: BTreeSet<CountyGeoid> = witness
        .household_incidence
        .iter()
        .map(|row| row.county)
        .collect();
    let budgeted: BTreeSet<CountyGeoid> = household_budgets()
        .counties()
        .iter()
        .map(CountyHouseholdAllocation::county)
        .collect();
    assert_eq!(incident, budgeted);
    // Each county's financial domain, as the capture itself recorded it.
    let domain_of: BTreeMap<CountyGeoid, String> = witness
        .counties
        .iter()
        .map(|c| (c.controls.county, format!("{:?}", c.destination)))
        .collect();
    let budgets = household_budgets();
    let donors = &catalog
        .national_aid_capture()
        .expect("the aid cohorts")
        .children;
    // domain -> key -> (account principal, households its member counties' budget rows sum to)
    let mut domains: BTreeMap<String, BTreeMap<HouseholdBudgetKey, (_, u64)>> = BTreeMap::new();
    for row in &witness.household_incidence {
        let key = row.margins.key;
        let from_budgets = budgets
            .county(row.county)
            .expect("the county's budgets")
            .budgets()
            .iter()
            .find(|budget| budget.key == key)
            .map_or(0, |budget| budget.households);
        assert_eq!(
            row.margins.households, from_budgets,
            "{:?} {key:?}",
            row.county
        );
        let domain = domain_of
            .get(&row.county)
            .expect("every county has a domain");
        let entry = domains
            .entry(domain.clone())
            .or_default()
            .entry(key)
            .or_insert((row.destination, 0));
        assert_eq!(entry.0, row.destination, "one account for {domain} {key:?}");
        entry.1 += from_budgets;
    }
    let mut places = 0_u64;
    for (domain, keys) in &domains {
        assert!(
            !keys.contains_key(&HouseholdBudgetKey::EarningNonowner),
            "{domain} makes no account of the schema 7 band"
        );
        if !BAND_KEYS.iter().any(|k| keys.contains_key(k)) {
            continue;
        }
        places += 1;
        for key in BAND_KEYS {
            let (principal, counted) = keys
                .get(&key)
                .unwrap_or_else(|| panic!("{domain} lacks the account {key:?}"));
            let account = accounts
                .get(principal)
                .unwrap_or_else(|| panic!("{domain} {key:?} has no opening account"));
            let carved: u64 = donors
                .iter()
                .filter(|d| d.parent == *principal)
                .map(|d| d.households)
                .sum();
            assert_eq!(account.households + carved, *counted, "{domain} {key:?}");
        }
    }
    assert_eq!(
        places, PLACES,
        "every pooled place and each detailed county"
    );
}

#[test]
fn the_aid_donor_comes_from_the_lower_paid_half() {
    let catalog = campaign_catalog();
    let aid = catalog.national_aid_capture().expect("the aid cohorts");
    let donor = aid.children.first().expect("the donor is the first child");
    assert_eq!(donor.budget, HouseholdBudgetKey::EarningLowerPaidHalf);
    assert_eq!(
        donor.parent,
        national_economy::household_principal(
            donor.location,
            HouseholdBudgetKey::EarningLowerPaidHalf
        )
    );
    // Its one employing site is the organizer's workplace.
    let opening = catalog.opening();
    let employed: Vec<_> = opening
        .employment
        .iter()
        .filter(|term| term.payee == donor.principal)
        .collect();
    assert_eq!(employed.len(), 1);
    let site = opening
        .sites
        .iter()
        .find(|site| site.site_id == employed[0].site_id)
        .expect("the donor's site");
    let organizer = catalog.organizer_config().expect("the organizer");
    assert_eq!(organizer.workplace_label, site.label);
    assert_eq!(
        organizer.workplace_process_id,
        site.processes[0].process_id.as_bytes()
    );
}

/// The county-level allocation of the fixture world, made once: who works where, by band.
fn county_allocation() -> &'static ResidentWorkplaceAllocation {
    static ALLOCATION: OnceLock<ResidentWorkplaceAllocation> = OnceLock::new();
    ALLOCATION.get_or_init(|| {
        let policy = NationalGamePolicy::parse(std::str::from_utf8(FIXTURE).expect("utf8"))
            .expect("the fixture admits");
        let budgets = household_budgets();
        national_resident_allocation::allocate_home_county(
            national_counties::national_county_reference().expect("the county reference loads"),
            national_cohorts::national_cohort_reference_v2().expect("v2 cohorts"),
            national_resident_workforce::national_resident_workforce_reference()
                .expect("the workforce reference loads"),
            &budgets,
            &empty_leaves(&budgets),
            &policy,
            Some(national_trade_pay::national_trade_pay_reference().expect("pay table")),
        )
        .expect("the county-level allocation")
    })
}

#[test]
fn the_best_paid_jobs_go_to_the_owners() {
    use national_resident_allocation::ResidentAttendanceMode::Employee;
    let allocation = county_allocation();
    // Per county and band: the lowest and the highest wage among employee members.
    let mut spans: BTreeMap<(EconomicLocation, HouseholdBudgetKey), (Currency, Currency)> =
        BTreeMap::new();
    let mut counties = Vec::new();
    for workplace in &allocation.workplaces {
        let wage = workplace.county_wage.expect("observed pay ranks every job");
        for member in workplace
            .members
            .iter()
            .filter(|m| m.mode == Employee && m.seed.employed > 0)
        {
            let location = member.seed.member.residence();
            let Some(band) = BAND_KEYS.into_iter().find(|key| {
                national_economy::household_principal(location, *key)
                    == member.seed.member.household_id()
            }) else {
                continue;
            };
            counties.push(location);
            let span = spans.entry((location, band)).or_insert((wage, wage));
            span.0 = span.0.min(wage);
            span.1 = span.1.max(wage);
        }
    }
    counties.sort();
    counties.dedup();
    let mut compared = 0_u64;
    for location in counties {
        let span = |key| spans.get(&(location, key));
        for (better, worse) in [
            (
                HouseholdBudgetKey::EarningOwner,
                HouseholdBudgetKey::EarningBetterPaidForty,
            ),
            (
                HouseholdBudgetKey::EarningBetterPaidForty,
                HouseholdBudgetKey::EarningLowerPaidHalf,
            ),
        ] {
            if let (Some(better_span), Some(worse_span)) = (span(better), span(worse)) {
                assert!(
                    better_span.0 >= worse_span.1,
                    "{location:?}: {better:?} lowest {:?} under {worse:?} highest {:?}",
                    better_span.0,
                    worse_span.1
                );
                compared += 1;
            }
        }
    }
    assert!(compared > 100, "counties compared: {compared}");
    let wayne = county("26163");
    for key in BAND_KEYS {
        assert!(spans.contains_key(&(wayne, key)), "Wayne {key:?} works");
    }
}

const WAYNE_NEXT_FORTY_HOUSEHOLDS: u64 = 280_236;
const WAYNE_BETTER_PAID_HOUSEHOLDS: u64 = 202_903;

#[test]
fn the_county_review_sees_three_earning_groups() {
    let catalog = campaign_catalog();
    let config = catalog.county_review_config().expect("the county review");
    let labels: Vec<_> = config.groups.iter().map(|g| g.label.as_str()).collect();
    for want in [
        "earning-lower-paid-half",
        "earning-better-paid-forty",
        "earning-owner",
        "earning-lower-paid-half (aid donors)",
    ] {
        assert!(labels.contains(&want), "{want} in {labels:?}");
    }
    let roster = review_roster();
    babylon_practice_contract::validate_roster(config, &roster).expect("the roster builds");
    for row in &roster.rows {
        if matches!(row.key.band, Band::Top1 | Band::Next9) {
            assert!(
                config.groups[row.key.group as usize].has_ownership_income,
                "{} has no ownership income",
                config.groups[row.key.group as usize].label
            );
        }
    }
}

/// The county review's roster, from a campaign captured afresh: the foundation takes its catalog.
fn review_roster() -> Roster {
    use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};
    let input = economic_catalog::national_catalog_input_for(FIXTURE).expect("the fixture parses");
    CapturedEconomicCatalog::capture_national_campaign(
        input,
        CampaignId::from_uuid(Uuid::from_u128(0x0026_1631_7036)),
    )
    .expect("the fixture captures as a campaign")
    .create_foundation(
        ReplaySessionId::try_from("twelve-trades-review").expect("session identity"),
        ReplaySeed::new(319),
    )
    .expect("the review opens inside the material register")
    .initial_register()
    .county_review()
    .expect("the opening register carries the county section")
    .state()
    .roster
    .clone()
}

#[test]
fn the_review_and_the_accounts_use_their_own_words() {
    let catalog = campaign_catalog();
    let config = catalog.county_review_config().expect("the county review");
    let roster = review_roster();
    let next_forty = roster.band_counts()[2].households;
    let better_paid = household_budgets()
        .county(CountyGeoid::try_from("26163").expect("Wayne"))
        .expect("Wayne's budgets")
        .budgets()
        .iter()
        .find(|b| b.key == HouseholdBudgetKey::EarningBetterPaidForty)
        .map_or(0, |b| b.households);
    assert_eq!(next_forty, WAYNE_NEXT_FORTY_HOUSEHOLDS);
    assert_eq!(better_paid, WAYNE_BETTER_PAID_HOUSEHOLDS);
    assert_ne!(next_forty, better_paid, "two cuts, two counts");
    for group in &config.groups {
        for word in ["Top", "Next", "Bottom", "%"] {
            assert!(!group.label.contains(word), "{} holds {word}", group.label);
        }
    }
    for band in [Band::Top1, Band::Next9, Band::Next40, Band::Bottom50] {
        assert!(!babylon_practice_contract::band_label(band).contains("paid"));
    }
}

#[test]
fn owners_keep_the_business_shares() {
    let catalog = captured();
    let witness = catalog
        .national_generation()
        .expect("the generation witness");
    let key_of: BTreeMap<_, _> = witness
        .household_incidence
        .iter()
        .map(|row| (row.destination, row.margins.key))
        .collect();
    let mut domestic_claims = 0_u64;
    for claim in &catalog.opening().institutions.ownership {
        let AccountId::Household(principal) = claim.beneficiary else {
            continue;
        };
        let Some(key) = key_of.get(&principal) else {
            continue;
        };
        domestic_claims += 1;
        assert!(key.owner_exposure(), "{key:?} holds a claim");
    }
    assert!(domestic_claims > 0, "domestic owners hold claims");
}

/// The fixture's work hours a person, as its policy states them.
const WORK_HOURS_PER_PERSON: i128 = 160;

/// A site's payroll for one period: its employed persons paid a wage, at their wage and the policy's hours.
fn payroll_of(catalog: &CapturedEconomicCatalog, site: &EconomicSiteSeed) -> i128 {
    let opening = catalog.opening();
    let wages: BTreeMap<_, _> = opening
        .employment
        .iter()
        .filter(|term| term.site_id == site.site_id)
        .filter_map(|term| match term.compensation {
            LaborCompensation::Wage(wage) => Some((term.member_id, wage.micro_units())),
            _ => None,
        })
        .collect();
    opening
        .staffing
        .iter()
        .filter(|pool| pool.workplace == site.subject)
        .flat_map(|pool| pool.members.iter())
        .filter_map(|member| {
            wages
                .get(&member.member.member_id())
                .map(|wage| i128::from(member.employed) * WORK_HOURS_PER_PERSON * wage)
        })
        .sum()
}

/// What a site's service inputs of one period cost at their providers' opening prices.
fn service_input_cost(catalog: &CapturedEconomicCatalog, site: SiteId) -> i128 {
    let policies = &catalog.opening().policies;
    policies
        .service_inputs
        .iter()
        .filter(|row| row.buyer_site_id == site)
        .map(|row| {
            let offer = policies
                .offers
                .iter()
                .find(|offer| {
                    offer.site_id == row.provider_site_id
                        && offer.good_id == row.good_id
                        && offer.unit_id == row.unit_id
                })
                .expect("a provider of a service input offers it");
            i128::from(row.quantity_per_period) * offer.unit_price.micro_units()
        })
        .sum()
}

#[test]
fn every_workplace_can_pay_for_its_first_period() {
    let catalog = captured();
    let opening = catalog.opening();
    let mut short: BTreeMap<String, (u64, u64)> = BTreeMap::new();
    let mut shown = 0;
    let mut checked = 0_u64;
    for site in opening
        .sites
        .iter()
        .filter(|site| matches!(site.location, EconomicLocation::County(_)))
    {
        let floor = opening
            .policies
            .service_inputs
            .iter()
            .filter(|row| row.buyer_site_id == site.site_id)
            .map(|row| row.cash_floor.micro_units())
            .max();
        let Some(floor) = floor else {
            continue;
        };
        checked += 1;
        let payroll = payroll_of(catalog, site);
        let inputs = service_input_cost(catalog, site.site_id);
        let cash = site.opening_cash.micro_units();
        if cash - payroll - floor < inputs {
            let workers = opening
                .staffing
                .iter()
                .filter(|pool| pool.workplace == site.subject)
                .flat_map(|pool| pool.members.iter())
                .map(|member| member.employed)
                .sum::<u64>();
            let entry = short.entry(format!("{:?}", site.function)).or_default();
            entry.0 += 1;
            entry.1 += workers;
            if shown < 10 {
                shown += 1;
                println!(
                    "short: {} cash {cash} payroll {payroll} floor {floor} inputs {inputs}",
                    site.label
                );
            }
        }
    }
    println!("workplaces with a service input: {checked}");
    println!("short by trade (workplaces, workers): {short:?}");
    assert!(short.is_empty(), "workplaces short: {short:?}");
}

#[test]
fn a_company_takes_nothing_at_the_opening() {
    let catalog = campaign_catalog();
    let finances = catalog
        .national_company_finances()
        .expect("the campaign carries the companies' finances");
    assert_eq!(finances.sweep_bps, 0);
    assert!(
        finances.members.len() > 1,
        "the fixture has company members"
    );
    for member in &finances.members {
        assert_eq!(member.swept.micro_units(), 0, "{:?}", member.site);
        assert_eq!(member.remaining_cash, member.original_cash);
        let site = catalog
            .opening()
            .sites
            .iter()
            .find(|site| site.site_id == member.site)
            .expect("a company's workplace is a site");
        assert_eq!(site.opening_cash, member.original_cash);
    }
    assert!(finances.treasuries.len() > 1, "the fixture has companies");
    for treasury in &finances.treasuries {
        assert_eq!(treasury.cash.micro_units(), 0, "{:?}", treasury.company);
    }
    let company_money: i128 = catalog
        .opening()
        .institutional_cash
        .iter()
        .filter(|account| matches!(account.id, AccountId::Company(_)))
        .map(|account| account.cash.micro_units())
        .sum();
    assert_eq!(company_money, 0);
}
