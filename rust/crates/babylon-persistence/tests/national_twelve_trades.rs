//! The twelve-trade national scenario (policy schema 8): its sources, its compiler and, in later tasks, its world.
use babylon_kernel::currency::Currency;
use babylon_kernel::economic_identity::{EconomicFunction, QcewOwnership, TradeSet};
use babylon_kernel::economic_location::{EconomicLocation, ForeignCounterpart};
use babylon_kernel::geography::CountyGeoid;
use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};
use babylon_material_circuit::{
    AccountId, CommodityKind, FinalDemandPrincipalId, GoodId, HouseholdCohort, HouseholdKind,
    HouseholdNeedBasis, HouseholdWant, LaborCompensation, ProductiveEquipment, PublicAccountId,
    PublicProgramTerms, PublicSpendingRule, PublicTransferTreatment, RollingProcessSupply,
    ServiceConnection, SiteId, TaxBasis, WantTier,
};
use babylon_persistence::economic_catalog::{
    self, CapturedEconomicCatalog, EconomicCatalogError, EconomicCatalogInput, SourceArtifact,
    SourceArtifactKind as Kind,
};
use babylon_persistence::economic_catalog::{
    CatalogCapacity, EconomicHouseholdSeed, EconomicSiteSeed,
};
use babylon_persistence::identity::CampaignId;
use babylon_persistence::national_cohorts::CohortKey;
use babylon_persistence::national_economy::grain::{
    ContributionDestination, FinancialDomainId, ReservePosition,
};
use babylon_persistence::national_economy::GameMachines;
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

/// The fixture's counts of the rows that wants add to: purchase rows, handling rows and offers.
fn want_sensitive_counts(catalog: &CapturedEconomicCatalog) -> (usize, usize, usize) {
    let opening = catalog.opening();
    let handling = opening
        .sites
        .iter()
        .filter_map(|site| site.merchant.as_ref())
        .map(|merchant| merchant.handling.len())
        .sum();
    (
        opening.policies.household_purchases.len(),
        handling,
        opening.policies.offers.len(),
    )
}

#[test]
fn the_fixture_without_wants_keeps_its_rows() {
    let counts = want_sensitive_counts(captured());
    println!("purchase rows, handling rows, offers: {counts:?}");
    assert_eq!(counts, (10_876, 2_020, 8_350));
}

/// Two want rows on the fixture, as the builder will write them: a comfort of shop goods and a luxury
/// service, with the shop's handling row for the good that is only wanted.
fn wants_text(leisure_per_person: u64, scale: &str) -> String {
    let text = std::str::from_utf8(FIXTURE).expect("utf8").replacen(
        "[commodity.consumer_goods]\n",
        "[commodity.consumer_goods]\nhandling_hours = 1\nhandling_units = 1\n",
        1,
    );
    format!(
        "{text}\n[[household_wants]]\ngood = \"consumer_goods\"\ntier = \"comfort\"\nbasis = \"persons\"\nunits_per_basis = 3\n\n[[household_wants]]\ngood = \"leisure\"\ntier = \"luxury\"\nbasis = \"persons\"\nunits_per_basis = {leisure_per_person}\n{scale}"
    )
}

fn captured_text(text: &str) -> CapturedEconomicCatalog {
    let input =
        economic_catalog::national_catalog_input_for(text.as_bytes()).expect("the text parses");
    CapturedEconomicCatalog::capture(input, None).expect("the text captures")
}

/// The fixture with its wants, captured once.
fn wanting() -> &'static CapturedEconomicCatalog {
    static CATALOG: OnceLock<CapturedEconomicCatalog> = OnceLock::new();
    CATALOG.get_or_init(|| captured_text(&wants_text(2, "")))
}

fn cohort(row: &EconomicHouseholdSeed) -> HouseholdCohort {
    HouseholdCohort {
        kind: row.kind,
        principal_id: row.principal_id,
        households: row.households,
        persons: row.persons,
    }
}

#[test]
fn every_account_wants_its_tiers() {
    let text = wants_text(2, "");
    let policy = NationalGamePolicy::parse(&text).expect("the text admits");
    let opening = wanting().opening();
    let mut expected = Vec::new();
    for household in &opening.households {
        for want in &policy.household_wants {
            if household.kind == HouseholdKind::CollectiveResidence
                && want.basis == HouseholdNeedBasis::Households
            {
                continue;
            }
            let good = &policy.commodities[&want.key];
            expected.push(HouseholdWant {
                principal_id: household.principal_id,
                tier: want.tier,
                good_id: good.good_id,
                unit_id: good.unit_id,
                basis: want.basis,
                units_per_basis: want.units_per_basis,
                scale_bps: babylon_material_circuit::WANT_SCALE_ONE_BPS,
            });
        }
    }
    expected.sort_by_key(|w| (w.principal_id, w.tier, w.good_id, w.unit_id));
    let wants = &opening
        .market_clearing
        .as_ref()
        .expect("schema 8 clears by price")
        .household_wants;
    assert_eq!(wants.len(), opening.households.len() * 2);
    assert_eq!(wants, &expected);
    let seeds: BTreeMap<_, _> = opening
        .households
        .iter()
        .map(|h| (h.principal_id, h))
        .collect();
    for want in wants {
        let seed = seeds[&want.principal_id];
        let count = match want.basis {
            HouseholdNeedBasis::Persons => seed.persons,
            HouseholdNeedBasis::Households => seed.households,
        };
        assert_eq!(
            want.quantity(&cohort(seed)).expect("a quantity"),
            count * want.units_per_basis
        );
    }
}

#[test]
fn every_want_has_a_seller_that_offers_it() {
    let text = wants_text(2, "");
    let policy = NationalGamePolicy::parse(&text).expect("the text admits");
    let opening = wanting().opening();
    let needed: BTreeSet<_> = policy
        .household_needs
        .iter()
        .map(|need| {
            let good = &policy.commodities[&need.key];
            (good.good_id, good.unit_id)
        })
        .collect();
    let wants = &opening
        .market_clearing
        .as_ref()
        .expect("schema 8 clears by price")
        .household_wants;
    assert_ne!(wants.len(), 0);
    let mut services = 0;
    for want in wants {
        let row = opening
            .policies
            .household_purchases
            .iter()
            .find(|row| {
                (row.principal_id, row.good_id, row.unit_id)
                    == (want.principal_id, want.good_id, want.unit_id)
            })
            .expect("a want has a purchase row");
        assert!(row.enabled);
        assert!(
            opening.policies.offers.iter().any(|offer| {
                (offer.site_id, offer.good_id, offer.unit_id)
                    == (row.retailer_site_id, want.good_id, want.unit_id)
            }),
            "the seller offers the good"
        );
        if !needed.contains(&(want.good_id, want.unit_id)) {
            assert_eq!(row.target_closing_stock, 0);
            assert!(row.maximum_purchase > 0);
        }
        let good = policy
            .commodities
            .values()
            .find(|g| (g.good_id, g.unit_id) == (want.good_id, want.unit_id))
            .expect("a want names a good");
        if matches!(good.kind, CommodityKind::PeriodService { .. }) {
            services += 1;
            let connection = ServiceConnection {
                provider_site_id: row.retailer_site_id,
                buyer: AccountId::Household(want.principal_id),
                good_id: want.good_id,
                unit_id: want.unit_id,
            };
            assert!(opening.policies.service_connections.contains(&connection));
        }
    }
    assert!(services > 0, "the luxury is a service");
}

#[test]
fn the_shop_handles_consumer_goods() {
    let text = wants_text(2, "");
    let policy = NationalGamePolicy::parse(&text).expect("the text admits");
    let goods = &policy.commodities["consumer_goods"];
    let key = (goods.good_id, goods.unit_id);
    let opening = wanting().opening();
    let retailers: BTreeSet<SiteId> = opening
        .policies
        .household_purchases
        .iter()
        .filter(|row| (row.good_id, row.unit_id) == key)
        .map(|row| row.retailer_site_id)
        .collect();
    assert_ne!(retailers.len(), 0);
    for retailer in retailers {
        let site = opening
            .sites
            .iter()
            .find(|site| site.site_id == retailer)
            .expect("the retailer is a site");
        let handling = &site.merchant.as_ref().expect("a merchant").handling;
        let row = handling
            .iter()
            .find(|row| (row.good_id, row.unit_id) == key)
            .expect("a handling row for consumer goods");
        assert_eq!((row.hours_per_unit, row.units), (1, 1));
        assert!(opening
            .policies
            .offers
            .iter()
            .any(|o| (o.site_id, o.good_id, o.unit_id) == (retailer, key.0, key.1)));
        assert!(site
            .opening_stock
            .iter()
            .any(|s| (s.amount.good_id, s.amount.unit_id) == key && s.amount.quantity > 0));
        assert!(opening.policies.replenishment.iter().any(|r| (
            r.buyer_site_id,
            r.good_id,
            r.unit_id
        ) == (retailer, key.0, key.1)));
    }
}

#[test]
fn a_scaled_account_wants_more_luxuries() {
    // Two a person at 12,500 basis points is floor(2 x persons x 5 / 4) in all: more than 2 a person,
    // and not a whole number a person.
    let text = wants_text(
        2,
        "\n[luxury_scale]\nby_account = { \"26163:earning-owner\" = 12500 }\n",
    );
    let policy = NationalGamePolicy::parse(&text).expect("the text admits");
    let catalog = captured_text(&text);
    let opening = catalog.opening();
    let owner: FinalDemandPrincipalId =
        national_economy::household_principal(county("26163"), HouseholdBudgetKey::EarningOwner);
    let leisure = &policy.commodities["leisure"];
    let seeds: BTreeMap<_, _> = opening
        .households
        .iter()
        .map(|h| (h.principal_id, h))
        .collect();
    let wants = &opening
        .market_clearing
        .as_ref()
        .expect("schema 8 clears by price")
        .household_wants;
    let mut scaled = 0;
    for want in wants {
        let seed = seeds[&want.principal_id];
        let quantity = want.quantity(&cohort(seed)).expect("a quantity");
        if want.principal_id == owner && want.good_id == leisure.good_id {
            scaled += 1;
            assert!(seed.persons > 0);
            assert_eq!(want.units_per_basis, 2, "the scenario's own figure");
            assert_eq!(want.scale_bps, 12_500);
            assert_eq!(quantity, 2 * seed.persons * 5 / 4);
            assert!(quantity > 2 * seed.persons);
            // Its purchase row is sized by the same number.
            let row = opening
                .policies
                .household_purchases
                .iter()
                .find(|row| row.principal_id == owner && row.good_id == leisure.good_id)
                .expect("a purchase row for the want");
            assert_eq!(
                row.maximum_purchase,
                quantity * policy.retailer_buffer_periods
            );
        } else if want.tier == WantTier::Luxury {
            assert_eq!(want.scale_bps, 10_000);
            assert_eq!(quantity, 2 * seed.persons, "no other luxury moves");
        } else {
            assert_eq!(want.scale_bps, 10_000);
            assert_eq!(quantity, 3 * seed.persons, "no comfort moves");
        }
    }
    assert_eq!(scaled, 1);
}

#[test]
fn a_scale_that_names_no_account_is_refused() {
    // A rightly formed label that no account of the opening has: Wayne holds no part at a position.
    let text = wants_text(
        2,
        "\n[luxury_scale]\nby_account = { \"26163/below:earning-owner\" = 12500 }\n",
    );
    NationalGamePolicy::parse(&text).expect("the text admits");
    let input =
        economic_catalog::national_catalog_input_for(text.as_bytes()).expect("the text parses");
    assert!(matches!(
        CapturedEconomicCatalog::capture(input, None),
        Err(EconomicCatalogError::NationalOpening(
            national_economy::NationalOpeningError::Policy
        ))
    ));
}

// ---- Task 4: the national fund, the split taxes, the place grants and the programs ----

const WAYNE: &str = "26163";
const PLACE_GRANT_PRIORITY: u32 = 256;

fn fixture_text() -> &'static str {
    std::str::from_utf8(FIXTURE).expect("utf8")
}

/// The fixture with the fund's two shares at 2,530 and the table of shares by part, if any.
fn fund_text(table: &str) -> String {
    fixture_text().replacen(
        "wage_tax_share_bps = 0\noperating_income_tax_share_bps = 0\nreserve_periods = 2\n",
        &format!(
            "wage_tax_share_bps = 2530\noperating_income_tax_share_bps = 2530\nreserve_periods = 2\n{table}"
        ),
        1,
    )
}

const RESIDENCE_ROW: &str = "\n[[programs]]\nkey = \"residence\"\nkind = \"own_needs\"\nrank = 0\nshare_bps = 10000\nrecipients = \"collective_residence_at_opening\"\n";

/// The fixture with its fund at 2,530, `no_earner` paying each account its own needs and a `residence`
/// program, and what else the test adds (a table of shares by part before the programs, grant rows after).
fn programmed_text(table: &str, grants: &str) -> String {
    let text = fund_text(table).replacen(
        "kind = \"per_person\"\nrank = 0\namount_per_person_micros = 1595033714\n",
        "kind = \"own_needs\"\nrank = 0\nshare_bps = 10000\n",
        1,
    );
    format!("{text}{RESIDENCE_ROW}{grants}")
}

fn capture_text(text: &str) -> Result<CapturedEconomicCatalog, EconomicCatalogError> {
    let input =
        economic_catalog::national_catalog_input_for(text.as_bytes()).expect("the text parses");
    CapturedEconomicCatalog::capture(input, None)
}

fn refused_as_policy(text: &str) -> bool {
    matches!(
        capture_text(text),
        Err(EconomicCatalogError::NationalOpening(
            national_economy::NationalOpeningError::Policy
        ))
    )
}

/// The fixture with its fund at 2,530 only, captured once.
fn funded() -> &'static CapturedEconomicCatalog {
    static CATALOG: OnceLock<CapturedEconomicCatalog> = OnceLock::new();
    CATALOG.get_or_init(|| capture_text(&fund_text("")).expect("the funded fixture captures"))
}

/// The fixture with the fund, own-needs programs and a `residence` program, captured once.
fn programmed() -> &'static CapturedEconomicCatalog {
    static CATALOG: OnceLock<CapturedEconomicCatalog> = OnceLock::new();
    CATALOG.get_or_init(|| {
        capture_text(&programmed_text("", "")).expect("the programmed fixture captures")
    })
}

/// A part's label as the scenario writes it: the hub's geoid, then `/<position>` for a part with one.
fn part_label(hub: CountyGeoid, position: Option<ReservePosition>) -> String {
    match position {
        None => hub.as_str().to_owned(),
        Some(position) => format!(
            "{}/{}",
            hub.as_str(),
            match position {
                ReservePosition::NoLaborForce => "none",
                ReservePosition::BelowCellReserveRate => "below",
                ReservePosition::AtCellReserveRate => "at",
                ReservePosition::AboveCellReserveRate => "above",
            }
        ),
    }
}

/// Every domestic part of the opening, by label, with its domain, from the capture's own witness.
fn parts(catalog: &CapturedEconomicCatalog) -> BTreeMap<String, FinancialDomainId> {
    let witness = catalog.national_generation().expect("the witness");
    let mut found = BTreeMap::new();
    for county in &witness.counties {
        let (label, domain) = match county.destination {
            ContributionDestination::Detailed(geoid) => (
                part_label(geoid, None),
                FinancialDomainId::detailed(
                    EconomicLocation::domestic_county(geoid).expect("a domestic county"),
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
                    .expect("the catchment")
                    .key
                    .hub;
                (
                    part_label(hub, Some(position)),
                    FinancialDomainId {
                        location: EconomicLocation::domestic_county(hub)
                            .expect("a domestic county"),
                        representative: Some((catchment, position)),
                    },
                )
            }
        };
        found.insert(label, domain);
    }
    found
}

fn location_of(catalog: &CapturedEconomicCatalog) -> BTreeMap<AccountId, EconomicLocation> {
    let opening = catalog.opening();
    let mut found = BTreeMap::new();
    for household in &opening.households {
        found.insert(
            AccountId::Household(household.principal_id),
            household.location,
        );
    }
    for site in &opening.sites {
        found.insert(AccountId::Site(site.site_id), site.location);
    }
    found
}

/// The rows of each (payer, basis) of the opening's tax policy.
fn tax_rows(
    catalog: &CapturedEconomicCatalog,
) -> BTreeMap<(AccountId, TaxBasis), Vec<(PublicAccountId, u16)>> {
    let mut rows: BTreeMap<_, Vec<_>> = BTreeMap::new();
    for row in &catalog.opening().institutions.taxes {
        rows.entry((row.payer, row.basis))
            .or_default()
            .push((row.public_recipient, row.rate_bps));
    }
    rows
}

fn fund_part(rate: u16, share: u16) -> u16 {
    u16::try_from(u32::from(rate) * u32::from(share) / 10_000).expect("a rate")
}

#[test]
fn the_fund_takes_its_share_of_each_tax() {
    let catalog = funded();
    let policy = NationalGamePolicy::parse(&fund_text("")).expect("the text admits");
    let fund = national_economy::fund_account();
    let locations = location_of(catalog);
    let rows = tax_rows(catalog);
    let mut fund_rates = BTreeSet::new();
    for ((payer, basis), parts) in &rows {
        let rate = match basis {
            TaxBasis::WageIncome => policy.financial.wage_tax_bps,
            TaxBasis::PositiveOperatingIncome => policy.financial.operating_income_tax_bps,
        };
        let domestic = matches!(locations[payer], EconomicLocation::County(_));
        let to_fund: Vec<_> = parts.iter().filter(|(to, _)| *to == fund).collect();
        let total: u16 = parts.iter().map(|(_, r)| *r).sum();
        assert_eq!(total, rate, "{payer:?} {basis:?} pays its rate");
        if domestic {
            assert_eq!(parts.len(), 2, "{payer:?} {basis:?}");
            assert_eq!(to_fund.len(), 1);
            fund_rates.insert((rate, to_fund[0].1));
            assert_eq!(to_fund[0].1, fund_part(rate, 2_530));
        } else {
            assert!(to_fund.is_empty(), "no foreign payer pays the fund");
            assert_eq!(parts.len(), 1);
        }
    }
    println!(
        "tax rows: {}; fund rates by rate: {fund_rates:?}",
        catalog.opening().institutions.taxes.len()
    );
    assert!(catalog.opening().institutions.taxes.len() < 262_144);
    assert_eq!(fund_rates.len(), 1, "the fund's rate follows the rate");
}

/// The table of shares by part, as TOML text: `wayne` at 0, `special` at 10,000, every other at 2,530, a
/// part named `skip` left out and `extra` added.
fn share_table(
    labels: &BTreeSet<String>,
    special: &str,
    skip: Option<&str>,
    extra: Option<&str>,
) -> String {
    let mut entries: Vec<String> = labels
        .iter()
        .filter(|label| Some(label.as_str()) != skip)
        .map(|label| {
            let share = if label.starts_with(WAYNE) {
                0
            } else if label == special {
                10_000
            } else {
                2_530
            };
            format!("\"{label}\" = {share}")
        })
        .collect();
    if let Some(extra) = extra {
        entries.push(format!("\"{extra}\" = 2530"));
    }
    format!("share_by_part = {{ {} }}\n", entries.join(", "))
}

#[test]
fn a_part_s_own_share_sets_its_rows() {
    let parts = parts(funded());
    let labels: BTreeSet<String> = parts.keys().cloned().collect();
    assert_eq!(labels.len(), 316);
    let special = labels
        .iter()
        .find(|label| !label.contains('/') && !label.starts_with(WAYNE))
        .expect("a detailed part")
        .clone();
    let table = share_table(&labels, &special, None, None);
    let catalog = capture_text(&fund_text(&table)).expect("the table admits");
    let fund = national_economy::fund_account();
    let by_account: BTreeMap<PublicAccountId, String> = parts
        .iter()
        .map(|(label, domain)| (domain.public_account(), label.clone()))
        .collect();
    let policy = NationalGamePolicy::parse(&fund_text(&table)).expect("the text admits");
    let (mut at_zero, mut at_all) = (0_u64, 0_u64);
    for ((payer, basis), rows) in tax_rows(&catalog) {
        let rate = match basis {
            TaxBasis::WageIncome => policy.financial.wage_tax_bps,
            TaxBasis::PositiveOperatingIncome => policy.financial.operating_income_tax_bps,
        };
        let Some((place, place_rate)) = rows.iter().find(|(to, _)| *to != fund).copied() else {
            panic!("{payer:?} has no row to its own body");
        };
        let Some(label) = by_account.get(&place) else {
            continue; // a foreign payer's body
        };
        let to_fund = rows
            .iter()
            .find(|(to, _)| *to == fund)
            .map_or(0, |(_, rate)| *rate);
        if label.starts_with(WAYNE) {
            at_zero += 1;
            assert_eq!(to_fund, 0, "{label} sends nothing");
            assert_eq!(place_rate, rate);
        } else if *label == special {
            at_all += 1;
            assert_eq!(to_fund, rate, "{label} sends everything");
            assert_eq!(place_rate, 0);
        } else {
            assert_eq!(to_fund, fund_part(rate, 2_530), "{label}");
            assert_eq!(place_rate + to_fund, rate);
        }
    }
    assert!(at_zero > 0 && at_all > 0, "{at_zero} {at_all}");
    // A part left out of the table, and an entry for a county that is no part.
    let skip = labels
        .iter()
        .find(|label| *label != &special && !label.starts_with(WAYNE))
        .expect("another part");
    assert!(refused_as_policy(&fund_text(&share_table(
        &labels,
        &special,
        Some(skip),
        None
    ))));
    let witness = funded().national_generation().expect("the witness");
    let no_hub = witness
        .counties
        .iter()
        .map(|county| county.controls.county.as_str().to_owned())
        .find(|geoid| !labels.contains(geoid))
        .expect("a county that is no part");
    assert!(refused_as_policy(&fund_text(&share_table(
        &labels,
        &special,
        None,
        Some(&no_hub)
    ))));
}

/// Every provider operating grant of the opening from a public body at one priority: site -> (body, amount).
fn grants_at(
    catalog: &CapturedEconomicCatalog,
    account: Option<PublicAccountId>,
    priority: u32,
) -> BTreeMap<SiteId, (PublicAccountId, i128)> {
    let mut found = BTreeMap::new();
    for row in &catalog.opening().institutions.public_allocations {
        let (AccountId::Site(site), PublicTransferTreatment::ProviderOperatingGrant) =
            (row.recipient, row.treatment)
        else {
            continue;
        };
        if row.priority == priority && account.is_none_or(|a| a == row.public_account) {
            let slot = found.entry(site).or_insert((row.public_account, 0));
            slot.1 += row.amount_per_period.micro_units();
        }
    }
    found
}

fn payroll_site() -> SiteId {
    let config = campaign_catalog().city_pd_config().expect("the City PD");
    SiteId::from_bytes(config.payroll_site_account_id)
}

fn public_cap_and_cash(
    catalog: &CapturedEconomicCatalog,
    account: PublicAccountId,
) -> (i128, i128) {
    let opening = catalog.opening();
    let cap = opening
        .institutions
        .public_budgets
        .iter()
        .find(|b| b.public_account == account)
        .map_or(0, |b| b.period_cap.micro_units());
    let cash = opening
        .institutional_cash
        .iter()
        .find(|c| c.id == AccountId::Public(account))
        .map_or(0, |c| c.cash.micro_units());
    (cap, cash)
}

fn grant_row(part: &str, micros: i128) -> String {
    format!("\n[[place_grants]]\npart = \"{part}\"\namount_per_period_micros = {micros}\n")
}

/// The part of the largest public provider's own grant in Wayne, its funded providers' grants (the City PD's
/// payroll site left out), and its public body.
fn wayne_part(
    base: &CapturedEconomicCatalog,
    parts: &BTreeMap<String, FinancialDomainId>,
) -> (String, PublicAccountId, BTreeMap<SiteId, i128>) {
    let wayne = county(WAYNE);
    let wayne_sites: BTreeSet<SiteId> = base
        .opening()
        .sites
        .iter()
        .filter(|site| site.location == wayne)
        .map(|site| site.site_id)
        .collect();
    let own = grants_at(base, None, 0);
    let (_, (body, _)) = own
        .iter()
        .filter(|(site, _)| wayne_sites.contains(site))
        .max_by_key(|(_, (_, grant))| *grant)
        .expect("a public provider in Wayne");
    let label = parts
        .iter()
        .find(|(_, domain)| domain.public_account() == *body)
        .map(|(label, _)| label.clone())
        .expect("a part");
    let funded: BTreeMap<SiteId, i128> = own
        .iter()
        .filter(|(site, (account, _))| account == body && **site != payroll_site())
        .map(|(site, (_, grant))| (*site, *grant))
        .collect();
    (label, *body, funded)
}

#[test]
fn a_place_grant_is_paid_by_the_fund() {
    let base = captured();
    let parts = parts(base);
    let (label, body, funded_grants) = wayne_part(base, &parts);
    let total: i128 = funded_grants.values().sum();
    let row = total / 2;
    assert!(row > 0, "{label} has grants to share");
    let policy = NationalGamePolicy::parse(&programmed_text("", &grant_row(&label, row)))
        .expect("the text admits");
    let granted =
        capture_text(&programmed_text("", &grant_row(&label, row))).expect("the grant admits");
    let fund = national_economy::fund_account();
    let from_fund = grants_at(&granted, Some(fund), PLACE_GRANT_PRIORITY);
    let from_body = grants_at(&granted, Some(body), 0);
    assert_eq!(
        from_fund.values().map(|(_, part)| *part).sum::<i128>(),
        row,
        "the fund's parts sum to the row"
    );
    let own_before = grants_at(base, None, 0);
    for (site, (_, grant)) in own_before.iter().filter(|(_, (b, _))| *b == body) {
        let paid_by_fund = from_fund.get(site).map_or(0, |(_, part)| *part);
        let paid_by_body = from_body.get(site).map_or(0, |(_, part)| *part);
        assert_eq!(
            paid_by_fund + paid_by_body,
            *grant,
            "{site:?} keeps its grant"
        );
        if *site == payroll_site() {
            assert_eq!(paid_by_fund, 0, "the City PD's payroll site is its body's");
        }
    }
    assert!(from_fund
        .keys()
        .all(|site| funded_grants.contains_key(site)));
    let (cap_before, cash_before) = public_cap_and_cash(base, body);
    let (cap_after, cash_after) = public_cap_and_cash(&granted, body);
    assert_eq!(cap_after, cap_before - row);
    assert_eq!(
        cash_after,
        cash_before - i128::from(policy.working_capital_periods) * row
    );
    // No other part's rows move.
    for (other, domain) in &parts {
        if domain.public_account() != body {
            assert_eq!(
                public_cap_and_cash(&granted, domain.public_account()),
                public_cap_and_cash(base, domain.public_account()),
                "{other}"
            );
            assert_eq!(
                grants_at(&granted, Some(domain.public_account()), 0),
                grants_at(base, Some(domain.public_account()), 0),
                "{other}"
            );
        }
    }
    // A row above the part's grants, and a row for a part with no funded provider.
    assert!(refused_as_policy(&programmed_text(
        "",
        &grant_row(&label, total + 1)
    )));
    let labels: BTreeSet<String> = parts.keys().cloned().collect();
    let witness = base.national_generation().expect("the witness");
    let no_part = witness
        .counties
        .iter()
        .map(|county| county.controls.county.as_str().to_owned())
        .find(|geoid| !labels.contains(geoid))
        .expect("a county that is no part");
    assert!(refused_as_policy(&programmed_text(
        "",
        &grant_row(&no_part, 1)
    )));
}

/// The household accounts' class at the opening, by the fixture's own facts: a collective residence, an
/// account with no one at work, and an earning account.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Class {
    Residence,
    NoEarner,
    Earning,
}

fn employed_by_household(
    catalog: &CapturedEconomicCatalog,
) -> BTreeMap<FinalDemandPrincipalId, u64> {
    let mut employed: BTreeMap<_, u64> = BTreeMap::new();
    for member in catalog
        .opening()
        .staffing
        .iter()
        .flat_map(|pool| &pool.members)
    {
        *employed.entry(member.member.household_id()).or_default() += member.employed;
    }
    employed
}

fn class_of(row: &EconomicHouseholdSeed, employed: u64) -> Class {
    if row.kind == HouseholdKind::CollectiveResidence {
        Class::Residence
    } else if employed == 0 {
        Class::NoEarner
    } else {
        Class::Earning
    }
}

fn recipients_of(catalog: &CapturedEconomicCatalog, key: &str) -> BTreeSet<FinalDemandPrincipalId> {
    catalog
        .opening()
        .institutions
        .programs
        .iter()
        .find(|program| program.key.as_str() == key)
        .map(|program| program.recipients.iter().copied().collect())
        .unwrap_or_default()
}

#[test]
fn every_domestic_account_is_in_its_programs() {
    let catalog = programmed();
    let employed = employed_by_household(catalog);
    let (no_earner, laid_off, residence) = (
        recipients_of(catalog, "no_earner"),
        recipients_of(catalog, "laid_off"),
        recipients_of(catalog, "residence"),
    );
    let mut seen = BTreeMap::<&str, u64>::new();
    for row in &catalog.opening().households {
        let id = row.principal_id;
        let domestic = matches!(row.location, EconomicLocation::County(_));
        let at_work = employed.get(&id).copied().unwrap_or(0);
        let class = class_of(row, at_work);
        let (n, l, r) = (
            no_earner.contains(&id),
            laid_off.contains(&id),
            residence.contains(&id),
        );
        if !domestic {
            assert!(!n && !l && !r, "a foreign account is no recipient");
            continue;
        }
        match class {
            Class::NoEarner => {
                assert_eq!((n, l, r), (row.persons > 0, false, false), "{id:?}");
                *seen.entry("no_earner").or_default() += u64::from(n);
            }
            Class::Earning => {
                assert_eq!((n, l, r), (false, true, false), "{id:?}");
                *seen.entry("earning").or_default() += 1;
            }
            Class::Residence => {
                assert!(!n && l, "{id:?}");
                assert_eq!(r, row.persons > at_work, "{id:?}");
                *seen.entry("residence").or_default() += u64::from(r);
            }
        }
    }
    println!("recipients: {seen:?}");
    assert!(seen.values().all(|count| *count > 0), "{seen:?}");
}

/// What the account's needs cost, from its purchase rows and its sellers' offers.
fn needs_cost_of(
    catalog: &CapturedEconomicCatalog,
    policy: &NationalGamePolicy,
    row: &EconomicHouseholdSeed,
) -> i128 {
    let opening = catalog.opening();
    let mut cost = 0_i128;
    for need in &policy.household_needs {
        if row.kind == HouseholdKind::CollectiveResidence
            && need.basis == HouseholdNeedBasis::Households
        {
            continue;
        }
        let count = match need.basis {
            HouseholdNeedBasis::Persons => row.persons,
            HouseholdNeedBasis::Households => row.households,
        };
        let good = &policy.commodities[&need.key];
        let seller = opening
            .policies
            .household_purchases
            .iter()
            .find(|p| {
                (p.principal_id, p.good_id, p.unit_id)
                    == (row.principal_id, good.good_id, good.unit_id)
            })
            .expect("a need has a purchase row")
            .retailer_site_id;
        let offer = opening
            .policies
            .offers
            .iter()
            .find(|o| (o.site_id, o.good_id, o.unit_id) == (seller, good.good_id, good.unit_id))
            .expect("the seller offers the good");
        cost += i128::from(count * need.units_per_basis) * offer.unit_price.micro_units();
    }
    cost
}

/// What county support pays the account a period: its reserve persons times a period of the food need.
fn support_of(
    catalog: &CapturedEconomicCatalog,
    policy: &NationalGamePolicy,
    row: &EconomicHouseholdSeed,
) -> i128 {
    let reserve: u64 = catalog
        .opening()
        .staffing
        .iter()
        .flat_map(|pool| &pool.members)
        .filter(|m| {
            m.member.household_id() == row.principal_id && m.member.residence() == row.location
        })
        .map(|m| m.reserve)
        .sum();
    let food = policy.commodities["food"]
        .price
        .as_ref()
        .expect("a price")
        .opening;
    let units = policy
        .household_needs
        .iter()
        .find(|need| need.key == "food")
        .expect("food is a need")
        .units_per_basis;
    i128::from(reserve * policy.financial.reserve_food_support_periods * units) * food.micro_units()
}

/// ceil(numerator / divisor) for a divisor above 0, at least 1.
fn ceil_at_least_one(numerator: i128, divisor: i128) -> i128 {
    if numerator <= 0 {
        1
    } else {
        ((numerator - 1) / divisor + 1).max(1)
    }
}

#[test]
fn each_account_is_paid_its_own_needs() {
    let catalog = programmed();
    let policy = NationalGamePolicy::parse(&programmed_text("", "")).expect("the text admits");
    let opening = catalog.opening();
    let employed = employed_by_household(catalog);
    let households: BTreeMap<_, _> = opening
        .households
        .iter()
        .map(|row| (row.principal_id, row))
        .collect();
    let carved: BTreeSet<_> = catalog
        .national_aid_capture()
        .map(|aid| aid.children.iter().map(|child| child.principal).collect())
        .unwrap_or_default();
    let mut carved_recipients = 0_u64;
    let mut programs_of_own_needs = 0;
    for program in &opening.institutions.programs {
        let PublicProgramTerms::PerPersonOwn { share_bps } = program.terms else {
            assert_eq!(program.key.as_str(), "laid_off");
            continue;
        };
        programs_of_own_needs += 1;
        assert_eq!(share_bps, 10_000);
        assert_eq!(program.own_amounts.len(), program.recipients.len());
        let residence = program.key.as_str() == "residence";
        let mut amounts: Vec<i128> = Vec::new();
        for (id, own) in program.recipients.iter().zip(&program.own_amounts) {
            let row = households[id];
            assert!(row.persons > 0, "an account of no persons is no recipient");
            let persons = i128::from(row.persons);
            let cost = needs_cost_of(catalog, &policy, row);
            let support = support_of(catalog, &policy, row);
            let own = own.micro_units();
            amounts.push(own);
            let income = own * persons + support;
            if residence {
                let jobless = persons - i128::from(employed.get(id).copied().unwrap_or(0));
                assert!(jobless > 0);
                // Needs of the jobless residents over persons: cost x jobless / persons.
                let numerator = cost * jobless - support * persons;
                assert_eq!(
                    own,
                    ceil_at_least_one(numerator, persons * persons),
                    "{id:?}"
                );
                if own > 1 {
                    assert!(
                        income * persons >= cost * jobless,
                        "{id:?} covers its needs"
                    );
                    assert!(
                        income * persons < cost * jobless + persons * persons,
                        "{id:?} is paid above its needs"
                    );
                }
            } else {
                assert_eq!(
                    own,
                    ceil_at_least_one(cost - support, persons),
                    "{} {id:?}: cost {cost} support {support} persons {persons} at {}",
                    program.key.as_str(),
                    row.location
                );
                if own > 1 {
                    assert!(income >= cost, "{id:?} covers its needs");
                    assert!(income < cost + persons, "{id:?} is paid above its needs");
                }
                carved_recipients += u64::from(carved.contains(id));
            }
        }
        amounts.sort_unstable();
        println!(
            "{}: lowest {} median {} highest {} micros a person over {} recipients",
            program.key.as_str(),
            amounts[0],
            amounts[amounts.len() / 2],
            amounts[amounts.len() - 1],
            amounts.len()
        );
    }
    assert_eq!(programs_of_own_needs, 2, "no_earner and residence");
    println!("carved no-earner recipients: {carved_recipients}");
    assert!(
        carved_recipients > 0,
        "Wayne's carved accounts are recipients"
    );
}

/// What a program owes at the opening, by the engine's rule at each recipient's persons.
fn dues_of(catalog: &CapturedEconomicCatalog) -> i128 {
    let opening = catalog.opening();
    let persons: BTreeMap<_, _> = opening
        .households
        .iter()
        .map(|row| (row.principal_id, i128::from(row.persons)))
        .collect();
    let mut dues = 0_i128;
    for program in &opening.institutions.programs {
        match program.terms {
            PublicProgramTerms::PerPerson { amount_per_person } => {
                dues += program
                    .recipients
                    .iter()
                    .map(|id| amount_per_person.micro_units() * persons[id])
                    .sum::<i128>();
            }
            PublicProgramTerms::PerPersonOwn { share_bps } => {
                dues += program
                    .recipients
                    .iter()
                    .zip(&program.own_amounts)
                    .map(|(id, own)| {
                        own.micro_units() * persons[id] * i128::from(share_bps) / 10_000
                    })
                    .sum::<i128>();
            }
            PublicProgramTerms::AfterLayoff { .. } => {}
        }
    }
    dues
}

fn fund_cash_and_budget(catalog: &CapturedEconomicCatalog) -> (i128, i128) {
    let opening = catalog.opening();
    let fund = national_economy::fund_account();
    let cash = opening
        .institutional_cash
        .iter()
        .find(|row| row.id == AccountId::Public(fund))
        .expect("the fund holds cash")
        .cash
        .micro_units();
    let budgets: Vec<_> = opening
        .institutions
        .public_budgets
        .iter()
        .filter(|row| row.public_account == fund)
        .collect();
    assert_eq!(budgets.len(), 1, "one budget for the fund");
    assert_eq!(budgets[0].rule, PublicSpendingRule::CashInProportion);
    assert_eq!(budgets[0].period_cap.micro_units(), 0);
    assert_eq!(budgets[0].cash_floor.micro_units(), 0);
    assert_eq!(
        opening
            .institutions
            .locations
            .iter()
            .filter(|row| row.account == AccountId::Public(fund))
            .count(),
        1
    );
    assert!(opening.institutions.layoffs.is_empty(), "no layoff record");
    let grants: i128 = opening
        .institutions
        .public_allocations
        .iter()
        .filter(|row| row.public_account == fund)
        .map(|row| row.amount_per_period.micro_units())
        .sum();
    (cash, 2 * (dues_of(catalog) + grants))
}

#[test]
fn the_fund_opens_with_two_periods_of_its_payments() {
    for (name, catalog) in [("fixture", captured()), ("programmed", programmed())] {
        let (cash, expected) = fund_cash_and_budget(catalog);
        println!("{name}: the fund opens with {cash} micros");
        assert_eq!(cash, expected, "{name}");
        assert!(cash > 0, "{name}");
    }
}

#[test]
fn a_short_fund_cuts_the_grants_first() {
    let base = captured();
    let parts = parts(base);
    let (label, _, funded_grants) = wayne_part(base, &parts);
    let row = funded_grants.values().sum::<i128>() / 2;
    let text = programmed_text("", &grant_row(&label, row));
    let catalog = capture_text(&text).expect("the grant admits");
    let fund = national_economy::fund_account();
    let rows: Vec<_> = catalog
        .opening()
        .institutions
        .public_allocations
        .iter()
        .filter(|r| r.public_account == fund)
        .collect();
    assert_ne!(rows.len(), 0, "rows exist");
    assert!(rows.iter().all(|r| r.priority == PLACE_GRANT_PRIORITY));
    assert!(catalog
        .opening()
        .institutions
        .programs
        .iter()
        .all(|program| program.rank <= 255));
}

#[test]
fn the_support_unit_is_a_period_of_food() {
    let catalog = captured();
    let policy = NationalGamePolicy::parse(fixture_text()).expect("the text admits");
    let unit = i128::from(policy.financial.reserve_food_support_periods)
        * i128::from(
            policy
                .household_needs
                .iter()
                .find(|need| need.key == "food")
                .expect("food is a need")
                .units_per_basis,
        )
        * policy.commodities["food"]
            .price
            .as_ref()
            .expect("a price")
            .opening
            .micro_units();
    let opening = catalog.opening();
    let rows: Vec<_> = opening
        .institutions
        .public_allocations
        .iter()
        .filter(|r| r.treatment == PublicTransferTreatment::HouseholdIncomeSupport)
        .collect();
    assert_ne!(rows.len(), 0, "rows exist");
    let mut domestic = 0_u64;
    for row in rows {
        let AccountId::Household(id) = row.recipient else {
            panic!("support pays a household");
        };
        let account = opening
            .households
            .iter()
            .find(|h| h.principal_id == id)
            .expect("the household");
        if !matches!(account.location, EconomicLocation::County(_)) {
            continue; // a region abroad is paid at its own price scale
        }
        domestic += 1;
        let reserve: u64 = opening
            .staffing
            .iter()
            .flat_map(|pool| &pool.members)
            .filter(|m| m.member.household_id() == id && m.member.residence() == account.location)
            .map(|m| m.reserve)
            .sum();
        assert_eq!(
            row.amount_per_period.micro_units(),
            i128::from(reserve) * unit,
            "{id:?} at {} holds {} persons, reserve {reserve}, unit {unit}",
            account.location,
            account.persons
        );
    }
    assert!(domestic > 0);
}

#[test]
fn a_public_provider_s_grant_covers_its_wear() {
    // A grant is payroll + inputs + wear - receipts (never below 0), recomputed from the opening's own rows;
    // a machine's wear is its $4,000.00 over a life of 100 periods, $40.00, so the rest is whole machines.
    let catalog = captured();
    let policy = NationalGamePolicy::parse(fixture_text()).expect("the text admits");
    let opening = catalog.opening();
    let price_of = |good: GoodId| {
        policy
            .commodities
            .values()
            .find(|c| c.good_id == good)
            .and_then(|c| c.price.as_ref())
            .expect("a priced good")
            .opening
            .micro_units()
    };
    let grants = grants_at(catalog, None, 0);
    let (mut checked, mut machines) = (0_u64, 0_i128);
    for site in opening.sites.iter().filter(|site| {
        site.function == EconomicFunction::PublicProvisioning
            && matches!(site.location, EconomicLocation::County(_))
    }) {
        let Some((_, grant)) = grants.get(&site.site_id) else {
            continue;
        };
        let process = &site.processes[0];
        let recipe = opening
            .recipes
            .iter()
            .find(|r| r.id == process.recipe)
            .expect("the recipe");
        let batches = i128::from(process.planned_batches);
        let inputs: i128 = recipe
            .inputs
            .iter()
            .map(|i| batches * i128::from(i.quantity) * price_of(i.good_id))
            .sum();
        let receipts =
            batches * i128::from(recipe.output.quantity) * price_of(recipe.output.good_id);
        let without_wear = payroll_of(catalog, site) + inputs - receipts;
        let wear = grant - without_wear;
        assert!(
            wear >= 0,
            "{}: the grant covers more than payroll and inputs",
            site.label
        );
        assert_eq!(
            wear % 40_000_000,
            0,
            "{}: wear comes in machines",
            site.label
        );
        machines += wear / 40_000_000;
        checked += 1;
    }
    println!("public providers checked: {checked}; machines worn: {machines}");
    assert!(checked > 0 && machines > 0);
}

// ---- Task 6: machines by trade, of every age, for the whole workforce ----

/// The fixture's productive equipment, as the compiler wrote it.
fn productive_equipment(catalog: &CapturedEconomicCatalog) -> &ProductiveEquipment {
    let CatalogCapacity::Rolling(RollingProcessSupply::Equipment(equipment)) =
        &catalog.opening().capacity
    else {
        panic!("the fixture has rolling equipment");
    };
    equipment
}

fn workers_per_machine() -> BTreeMap<EconomicFunction, u64> {
    let policy = NationalGamePolicy::parse(fixture_text()).expect("the fixture's policy");
    let GameMachines::Workers {
        workers_per_machine,
        ..
    } = policy.equipment.machines
    else {
        panic!("the fixture counts workers a machine");
    };
    workers_per_machine
}

#[test]
fn the_engine_admits_a_definition_per_trade() {
    let catalog = captured();
    let equipment = productive_equipment(catalog);
    assert_eq!(equipment.definitions.len(), 11, "one definition a trade");
    let good = equipment.definitions[0].equipment_good_id;
    assert!(equipment
        .definitions
        .iter()
        .all(|d| d.equipment_good_id == good));
    assert_eq!(equipment.installation_inputs.len(), 11);
    for definition in &equipment.definitions {
        let rows: Vec<_> = equipment
            .installation_inputs
            .iter()
            .filter(|input| input.definition_id == definition.id)
            .collect();
        assert_eq!(rows.len(), 1, "each definition has its own input row");
        assert_eq!(rows[0].quantity_per_equipment_unit, 4);
    }
    // The foundation admits the material catalog: `MaterialCatalog::try_new` returns `Ok`.
    capture_text(fixture_text())
        .expect("the fixture captures again")
        .create_foundation(
            ReplaySessionId::try_from("twelve-trade-machines").expect("session identity"),
            ReplaySeed::new(6),
        )
        .expect("the foundation admits every definition");
}

/// Per site with a process: its machines (the cohorts' units) and its labor force.
fn machines_and_force(
    catalog: &CapturedEconomicCatalog,
) -> Vec<(EconomicFunction, u64, u64, bool)> {
    let opening = catalog.opening();
    let mut units = BTreeMap::<_, u64>::new();
    for cohort in &opening.equipment_position.cohorts {
        *units.entry(cohort.process_id).or_default() += cohort.units;
    }
    let force: BTreeMap<SiteId, u64> = opening
        .staffing
        .iter()
        .map(|s| (s.pool.site_id(), s.pool.labor_force()))
        .collect();
    opening
        .sites
        .iter()
        .filter(|site| !site.processes.is_empty())
        .map(|site| {
            (
                site.function,
                units
                    .get(&site.processes[0].process_id)
                    .copied()
                    .unwrap_or(0),
                force.get(&site.site_id).copied().unwrap_or(0),
                matches!(site.location, EconomicLocation::County(_)),
            )
        })
        .collect()
}

#[test]
fn coarsened_sites_have_machines_for_their_force() {
    let workers = workers_per_machine();
    let rows = machines_and_force(captured());
    let mut checked = 0_u64;
    for (function, machines, force, domestic) in rows {
        if !domestic {
            continue;
        }
        assert_eq!(
            machines,
            force.div_ceil(workers[&function]),
            "{function:?}: {force} workers"
        );
        checked += 1;
    }
    println!("domestic sites with a process: {checked}");
    assert!(checked > 0);
}

/// Pinned once from the first run: the domestic processes with machines and the cohorts they open with.
const PROCESSES_WITH_MACHINES: u64 = 7_462;
const OPENING_COHORTS: u64 = 54_049;

#[test]
fn about_one_machine_in_a_hundred_is_due() {
    let catalog = captured();
    let equipment = productive_equipment(catalog);
    let per_period: BTreeMap<_, _> = equipment
        .definitions
        .iter()
        .map(|d| (d.id, d.batches_per_unit_per_period))
        .collect();
    let definition_of: BTreeMap<_, _> = equipment
        .bindings
        .iter()
        .map(|b| (b.process_id, b.definition_id))
        .collect();
    let domestic: BTreeSet<_> = catalog
        .opening()
        .sites
        .iter()
        .filter(|s| matches!(s.location, EconomicLocation::County(_)))
        .flat_map(|s| s.processes.iter().map(|p| p.process_id))
        .collect();
    let cohorts: Vec<_> = catalog
        .opening()
        .equipment_position
        .cohorts
        .iter()
        .filter(|c| domestic.contains(&c.process_id))
        .collect();
    let (mut machines, mut due) = (0_u128, 0_u128);
    for cohort in &cohorts {
        let batches = per_period[&definition_of[&cohort.process_id]];
        machines += u128::from(cohort.units);
        if cohort.remaining_service_batches <= cohort.units * batches {
            due += u128::from(cohort.units);
        }
    }
    let processes: BTreeSet<_> = cohorts.iter().map(|c| c.process_id).collect();
    println!(
        "machines {machines}, due within a period {due} ({} per 10,000); processes with machines {}; cohorts {}",
        due * 10_000 / machines,
        processes.len(),
        cohorts.len()
    );
    assert!(due * 1_000 >= machines * 5 && due * 1_000 <= machines * 15);
    assert_eq!(processes.len() as u64, PROCESSES_WITH_MACHINES);
    assert_eq!(cohorts.len() as u64, OPENING_COHORTS);
}
