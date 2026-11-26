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
use babylon_persistence::national_household_allocation::HouseholdBudgetKey;
use babylon_persistence::national_household_allocation::{self, NationalHouseholdAllocation};
use babylon_persistence::national_household_refinement::{self, NationalHouseholdLeafRoster};
use babylon_persistence::{
    national_cohorts, national_counties, national_household_time_allocation, national_households,
    national_resident_allocation, national_resident_workforce, national_trade_pay,
};
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
    let pay = national_trade_pay::national_trade_pay_reference().expect("pay table");
    assert_eq!(pay.rows().len(), 65_065);
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
    assert!(allocation.workplaces.len() <= 131_072);
    assert!(members <= 262_144);
    assert_eq!(allocation.workplaces.len(), 68_281);
    assert_eq!(members, 113_737);
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
    let foreign: Vec<AccountId> = ForeignCounterpart::ALL
        .into_iter()
        .map(|c| pooled(EconomicLocation::Foreign(c)))
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
            assert!(
                claims(catalog, site.site_id)
                    .iter()
                    .all(|(who, _)| !foreign.contains(who)),
                "Wayne's capital goods site has no foreign claimant"
            );
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

#[test]
fn every_place_has_three_earning_accounts() {
    let catalog = captured();
    let rows = &catalog.opening().households;
    let accounts: BTreeMap<_, _> = rows.iter().map(|row| (row.principal_id, row)).collect();
    let locations: BTreeSet<_> = rows.iter().map(|row| row.location).collect();
    let mut places = 0_u64;
    for location in locations {
        let has =
            |key| accounts.contains_key(&national_economy::household_principal(location, key));
        assert!(
            !has(HouseholdBudgetKey::EarningNonowner),
            "{location:?} makes no account of the schema 7 band"
        );
        if matches!(location, EconomicLocation::County(_)) && BAND_KEYS.iter().any(|k| has(*k)) {
            places += 1;
            for key in BAND_KEYS {
                assert!(has(key), "{location:?} lacks the account {key:?}");
            }
        }
    }
    assert_ne!(places, 0);
    let budgets = household_budgets();
    let donor = catalog
        .national_aid_capture()
        .expect("the aid cohorts")
        .children
        .first()
        .expect("the donor")
        .clone();
    for code in ["26163", "17031"] {
        let location = county(code);
        let row = budgets
            .county(CountyGeoid::try_from(code).expect("county"))
            .expect("the county's budgets");
        for key in BAND_KEYS {
            let account = accounts
                .get(&national_economy::household_principal(location, key))
                .expect("the account exists");
            let carved = if code == "26163" && key == donor.budget {
                donor.households
            } else {
                0
            };
            let counted = row
                .budgets()
                .iter()
                .find(|budget| budget.key == key)
                .map_or(0, |budget| budget.households);
            assert_eq!(account.households + carved, counted, "{code} {key:?}");
        }
    }
}

#[test]
fn the_aid_donor_comes_from_the_lower_paid_half() {
    let catalog = captured();
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
}
