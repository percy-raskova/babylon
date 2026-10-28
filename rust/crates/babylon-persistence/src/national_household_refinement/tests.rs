use super::refine;
use super::refine::{
    AuthoredCommitment, BackgroundHouseholdCohort, BackgroundWorkplaceCohort, CohortConservation,
    ConsolidationError, DetailConservation, ForegroundSelection, HouseholdCohortCounts,
    HouseholdLeafMargins, HouseholdRefinementError, HouseholdRefinementSpec,
};
use crate::economic_catalog::CommodityAmount;
use crate::economic_catalog::CompiledEconomicOpening;
use crate::economic_catalog::EconomicHouseholdSeed;
use crate::economic_catalog::EconomicOpening;
use crate::economic_catalog::EconomicSiteSeed;
use crate::economic_catalog::EconomicSiteSource;
use crate::economic_catalog::OpeningCommodityStock;
use crate::national_cohorts;
use crate::national_cohorts::WorkplaceCohortKey;
use crate::national_counties;
use crate::national_economy;
use crate::national_economy::GameCommodity;
use crate::national_economy::NationalAidCapture;
use crate::national_economy::NationalGamePolicy;
use crate::national_household_allocation::HouseholdBudgetKey;
use crate::national_household_allocation::HouseholdCohortKey;
use crate::national_household_refinement::NationalDetailPartition;
use crate::national_households;
use crate::national_resident_workforce;
use crate::national_transport;
use crate::world_reference;
use babylon_kernel::currency::Currency;
use babylon_kernel::economic_identity::EconomicFunction;
use babylon_kernel::economic_location::EconomicLocation;
use babylon_kernel::economic_location::ForeignCounterpart;
use babylon_kernel::economic_location::UsDependency;
use babylon_kernel::geography::CountyGeoid;
use babylon_material_circuit;
use babylon_material_circuit::AidTransport;
use babylon_material_circuit::CircuitAccounting;
use babylon_material_circuit::FinalDemandOrder;
use babylon_material_circuit::FinalDemandPrincipalId;
use babylon_material_circuit::GoodId;
use babylon_material_circuit::HouseholdCohort;
use babylon_material_circuit::HouseholdContributionUse;
use babylon_material_circuit::HouseholdKind;
use babylon_material_circuit::HouseholdNeedBasis;
use babylon_material_circuit::HouseholdTimeAccounting;
use babylon_material_circuit::HouseholdTimeCommitment;
use babylon_material_circuit::HouseholdTimeReceipt;
use babylon_material_circuit::MaterialCircuitError;
use babylon_material_circuit::MaterialCircuitState;
use babylon_material_circuit::MaterialPurchase;
use babylon_material_circuit::OrderId;
use babylon_material_circuit::RouteId;
use babylon_material_circuit::SellerOffer;
use babylon_material_circuit::SiteId;
use babylon_material_circuit::UnitId;
use std::collections::BTreeMap;
use std::collections::BTreeSet;
use std::sync::OnceLock;
fn county() -> CountyGeoid {
    CountyGeoid::try_from("26163").expect("the fixture value fits the target range")
}
fn margins() -> HouseholdLeafMargins {
    HouseholdLeafMargins {
        persons: 20,
        households: 8,
        employed: 8,
        reserve: 2,
        eligible_16_plus: 16,
        armed_forces: 1,
        inactive: 5,
        under_16: 4,
    }
}
fn child(tag: u8) -> HouseholdRefinementSpec {
    HouseholdRefinementSpec {
        county: county(),
        parent_key: HouseholdBudgetKey::EarningNonowner,
        child_tag: [tag; 32],
        margins: HouseholdLeafMargins {
            persons: 3,
            households: 1,
            employed: 1,
            reserve: 1,
            eligible_16_plus: 2,
            armed_forces: 0,
            inactive: 0,
            under_16: 1,
        },
    }
}
#[test]
fn exact_eight_margins_and_identity_survive_reordered_children_and_count_changes() {
    let first = child(1);
    let second = child(2);
    let forward =
        refine::refine_parent(county(), first.parent_key, margins(), vec![&first, &second])
            .expect("the fixture call `refine_parent` succeeds for the authored inputs");
    let backward =
        refine::refine_parent(county(), first.parent_key, margins(), vec![&second, &first])
            .expect("the fixture call `refine_parent` succeeds for the authored inputs");
    assert_eq!(forward, backward);
    for index in 0..8 {
        assert_eq!(
            forward
                .iter()
                .map(|row| row.margins.values()[index])
                .sum::<u64>(),
            margins().values()[index]
        );
    }
    let mut changed = first.clone();
    changed.margins.persons += 1;
    changed.margins.under_16 += 1;
    let altered = refine::refine_parent(
        county(),
        first.parent_key,
        margins(),
        vec![&changed, &second],
    )
    .expect("the fixture call `refine_parent` succeeds for the authored inputs");
    assert_eq!(
        forward
            .iter()
            .map(|row| row.principal_id)
            .collect::<Vec<_>>(),
        altered
            .iter()
            .map(|row| row.principal_id)
            .collect::<Vec<_>>()
    );
    assert_eq!(
        forward
            .last()
            .expect("the fixture sequence is non-empty")
            .principal_id,
        national_economy::household_principal(
            EconomicLocation::domestic_county(county())
                .expect("the fixture geoid names a domestic county"),
            first.parent_key
        )
    );
}
#[test]
fn inconsistent_child_excess_and_empty_ordinary_residual_are_refused() {
    let mut invalid = child(1).margins;
    invalid.eligible_16_plus = 0;
    assert_eq!(
        invalid.validate(false),
        Err(HouseholdRefinementError::Margin)
    );
    invalid = margins();
    invalid.employed = u64::MAX;
    assert_eq!(
        invalid.validate(false),
        Err(HouseholdRefinementError::Margin)
    );
    let mut excessive = child(1);
    excessive.margins = margins();
    excessive.margins.persons += 1;
    excessive.margins.under_16 += 1;
    assert_eq!(
        refine::refine_parent(county(), excessive.parent_key, margins(), vec![&excessive]),
        Err(HouseholdRefinementError::Excess)
    );
    excessive.margins = margins();
    assert_eq!(
        refine::refine_parent(county(), excessive.parent_key, margins(), vec![&excessive]),
        Err(HouseholdRefinementError::Margin)
    );
}
#[test]
fn collective_residence_keeps_positive_people_without_fabricating_households() {
    let mut collective = margins();
    collective.households = 0;
    let rows = refine::refine_parent(
        county(),
        HouseholdBudgetKey::CollectiveResidence,
        collective,
        vec![],
    )
    .expect("the fixture call `refine_parent` succeeds for the authored inputs");
    assert_eq!(rows.len(), 1);
    assert_eq!(rows[0].margins, collective);
    assert_eq!(
        collective.validate(false),
        Err(HouseholdRefinementError::Margin)
    );
}

struct NationalFixture {
    opening: EconomicOpening,
    aid: NationalAidCapture,
    detail: NationalDetailPartition,
}
fn national_fixture() -> &'static NationalFixture {
    static FIXTURE: OnceLock<NationalFixture> = OnceLock::new();
    FIXTURE.get_or_init(|| {
        let policy = NationalGamePolicy::parse(include_str!(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../../content/scenarios/national/defines.toml"
        )))
        .expect("the authored literal parses as the declared type");
        let counties = national_counties::national_county_reference()
            .expect("the county reference fixture loads");
        let cohorts = national_cohorts::national_cohort_reference()
            .expect("the cohort reference fixture loads");
        let residents = national_resident_workforce::national_resident_workforce_reference()
            .expect("the workforce reference fixture loads");
        let world = world_reference::world_reference().expect("the world reference fixture loads");
        let transport = national_transport::national_transport_reference()
            .expect("the transport reference fixture loads");
        let built = national_economy::build_national_opening(
            counties,
            cohorts,
            residents,
            national_households::national_household_reference()
                .expect("the household reference fixture loads"),
            world,
            transport,
            national_economy::NationalOpeningPolicy {
                policy: &policy,
                source_hash: babylon_kernel::content_digest::sha256_of(include_bytes!(concat!(
                    env!("CARGO_MANIFEST_DIR"),
                    "/../../../content/scenarios/national/defines.toml"
                ))),
            },
        )
        .expect("the authored national opening admits its conserved detail partition");
        NationalFixture {
            opening: built.opening,
            aid: built.aid,
            detail: built.detail,
        }
    })
}
fn compiled_fixture() -> &'static CompiledEconomicOpening {
    static COMPILED: OnceLock<CompiledEconomicOpening> = OnceLock::new();
    COMPILED.get_or_init(|| {
        national_fixture()
            .opening
            .compile()
            .expect("the conserved national opening compiles")
    })
}
fn household_location_counts(
    detail: &NationalDetailPartition,
) -> (
    BTreeSet<CountyGeoid>,
    BTreeSet<ForeignCounterpart>,
    BTreeSet<UsDependency>,
) {
    let mut domestic = BTreeSet::new();
    let mut foreign = BTreeSet::new();
    let mut dependencies = BTreeSet::new();
    for cohort in detail.background_households() {
        match cohort.key.location {
            EconomicLocation::County(county) => {
                domestic.insert(county.geoid());
            }
            EconomicLocation::Foreign(counterpart) => {
                foreign.insert(counterpart);
            }
            EconomicLocation::Dependency(dependency) => {
                dependencies.insert(dependency);
            }
        }
    }
    (domestic, foreign, dependencies)
}
struct HouseholdWork {
    counts: BTreeMap<FinalDemandPrincipalId, (u64, u64, u64)>,
    hours: BTreeMap<FinalDemandPrincipalId, u64>,
}
fn household_work(opening: &EconomicOpening) -> HouseholdWork {
    let mut work = BTreeMap::<FinalDemandPrincipalId, (u64, u64, u64)>::new();
    for pool in &opening.staffing {
        for member in &pool.members {
            let entry = work.entry(member.member.household_id()).or_default();
            entry.0 += member.employed;
            entry.1 += member.reserve;
            entry.2 += member.member.labor_force();
        }
    }
    let mut hours = BTreeMap::new();
    if let HouseholdTimeAccounting::Modeled(_) = &opening.policies.household_time {
        for policy in &opening.policies.household_time_policy {
            hours.insert(
                policy.principal_id,
                policy
                    .eligible_persons
                    .checked_mul(policy.hours_per_eligible_person)
                    .expect("the fixture arithmetic stays in range"),
            );
        }
    }
    HouseholdWork {
        counts: work,
        hours,
    }
}
fn household_totals_for(
    opening: &EconomicOpening,
    selected: impl Fn(&EconomicHouseholdSeed) -> bool,
) -> CohortConservation {
    let work = household_work(opening);
    let mut totals = CohortConservation::default();
    for household in &opening.households {
        if !selected(household) {
            continue;
        }
        totals.persons += household.persons;
        totals.households += household.households;
        totals.cash_micros += household.opening_cash.micro_units();
        let (employed, reserve, labor_force) = work
            .counts
            .get(&household.principal_id)
            .copied()
            .unwrap_or_default();
        totals.employed += employed;
        totals.reserve += reserve;
        totals.labor_force += labor_force;
        totals.endowment_hours += work
            .hours
            .get(&household.principal_id)
            .copied()
            .unwrap_or_default();
        add_stock_totals(&mut totals, &household.opening_stock);
    }
    totals
}
fn workplace_totals_for(
    opening: &EconomicOpening,
    selected: impl Fn(&EconomicSiteSeed) -> bool,
) -> CohortConservation {
    let mut work = BTreeMap::<SiteId, (u64, u64, u64)>::new();
    for pool in &opening.staffing {
        let entry = work.entry(pool.pool.site_id()).or_default();
        for member in &pool.members {
            entry.0 += member.employed;
            entry.1 += member.reserve;
            entry.2 += member.member.labor_force();
        }
    }
    let mut totals = CohortConservation::default();
    for site in &opening.sites {
        if !selected(site) {
            continue;
        }
        totals.cash_micros += site.opening_cash.micro_units();
        let (employed, reserve, labor_force) = work.get(&site.site_id).copied().unwrap_or_default();
        totals.employed += employed;
        totals.reserve += reserve;
        totals.labor_force += labor_force;
        add_stock_totals(&mut totals, &site.opening_stock);
    }
    totals
}
fn add_stock_totals(totals: &mut CohortConservation, rows: &[OpeningCommodityStock]) {
    for row in rows {
        totals.stock_quantity += row.amount.quantity;
        totals.stock_cost_micros += row.total_cost.micro_units();
    }
}
fn background_totals(detail: &NationalDetailPartition) -> DetailConservation {
    let mut households = CohortConservation::default();
    for cohort in detail.background_households() {
        households.persons += cohort.counts.persons;
        households.households += cohort.counts.households;
        households.employed += cohort.counts.employed;
        households.reserve += cohort.counts.reserve;
        households.labor_force += cohort.counts.employed + cohort.counts.reserve;
        households.endowment_hours += cohort.counts.endowment_hours;
        households.cash_micros += cohort.opening_cash.micro_units();
        add_stock_totals(&mut households, &cohort.opening_stock);
    }
    let mut workplaces = CohortConservation::default();
    for cohort in detail.background_workplaces() {
        workplaces.employed += cohort.employed;
        workplaces.reserve += cohort.reserve;
        workplaces.labor_force += cohort.labor_force;
        workplaces.cash_micros += cohort.opening_cash.micro_units();
        add_stock_totals(&mut workplaces, &cohort.opening_stock);
    }
    DetailConservation {
        households,
        workplaces,
    }
}
fn foreground_totals(
    opening: &EconomicOpening,
    detail: &NationalDetailPartition,
) -> DetailConservation {
    let foreground = detail.foreground();
    let households = household_totals_for(opening, |household| {
        foreground
            .household_principals()
            .contains(&household.principal_id)
    });
    let workplaces = workplace_totals_for(opening, |site| {
        foreground.workplaces().contains(&site.site_id)
            || foreground.partner_workplaces().contains(&site.site_id)
    });
    DetailConservation {
        households,
        workplaces,
    }
}
fn assert_location_coverage(fixture: &NationalFixture) {
    let detail = &fixture.detail;
    let (domestic, foreign, dependencies) = household_location_counts(detail);
    assert_eq!(
        domestic.len(),
        3_144,
        "every domestic county must participate"
    );
    assert_eq!(
        foreign.len(),
        12,
        "every bounded foreign counterpart participates"
    );
    assert_eq!(
        dependencies.len(),
        6,
        "every bounded dependency participates"
    );
    for child in &fixture.aid.children {
        assert!(
            detail
                .foreground()
                .household_principals()
                .contains(&child.principal),
            "the authored household principal must remain separately addressable"
        );
        assert!(
            detail
                .background_households()
                .iter()
                .all(|cohort| cohort.key.principal != child.principal),
            "a foreground principal cannot also be a background cohort"
        );
    }
    assert_eq!(
        detail.commitments().len(),
        fixture.aid.mandates.len(),
        "every active commitment remains a foreground identity"
    );
}
fn assert_merged_stock_order(detail: &NationalDetailPartition) {
    for cohort in detail.background_households() {
        assert!(
            cohort.opening_stock.windows(2).all(|pair| (
                pair[0].amount.good_id,
                pair[0].amount.unit_id
            ) < (
                pair[1].amount.good_id,
                pair[1].amount.unit_id
            )),
            "merged pantry rows retain one sorted identity per good and unit"
        );
    }
    for cohort in detail.background_workplaces() {
        assert!(
            cohort.opening_stock.windows(2).all(|pair| (
                pair[0].amount.good_id,
                pair[0].amount.unit_id
            ) < (
                pair[1].amount.good_id,
                pair[1].amount.unit_id
            )),
            "merged workplace stock rows retain one sorted identity per good and unit"
        );
    }
}
#[test]
fn national_background_conserves_all_domestic_foreign_and_dependency_cohorts() {
    let fixture = national_fixture();
    let detail = &fixture.detail;
    assert_location_coverage(fixture);
    let expected = DetailConservation {
        households: household_totals_for(&fixture.opening, |_| true),
        workplaces: workplace_totals_for(&fixture.opening, |_| true),
    };
    assert_eq!(
        detail.conservation(),
        expected,
        "the partition must retain every population, workforce, hour, stock and cash total"
    );
    let background = background_totals(detail);
    let foreground = foreground_totals(&fixture.opening, detail);
    assert_eq!(
        background
            .households
            .checked_add(foreground.households)
            .expect("the fixture arithmetic stays in range"),
        expected.households,
        "background and foreground household rows must reconstruct the source total"
    );
    assert_eq!(
        background
            .workplaces
            .checked_add(foreground.workplaces)
            .expect("the fixture arithmetic stays in range"),
        expected.workplaces,
        "background and foreground workplace rows must reconstruct the source total"
    );
    assert_merged_stock_order(detail);
    eprintln!(
        "national detail: background households {} workplaces {}; foreground households {} workplaces {} partner {}; commitments {}; persons {} households {} employed {} reserve {} hours {} stock {} cash {}",
        detail.background_households().len(),
        detail.background_workplaces().len(),
        detail.foreground().household_principals().len(),
        detail.foreground().workplaces().len(),
        detail.foreground().partner_workplaces().len(),
        detail.commitments().len(),
        detail.conservation().households.persons,
        detail.conservation().households.households,
        detail.conservation().households.employed,
        detail.conservation().households.reserve,
        detail.conservation().households.endowment_hours,
        detail.conservation().households.stock_quantity,
        detail.conservation().households.cash_micros,
    );
}
fn local_food_offer<'a>(
    opening: &'a EconomicOpening,
    policy: &'a NationalGamePolicy,
    location: EconomicLocation,
) -> (&'a SellerOffer, &'a GameCommodity) {
    let food = policy
        .commodities
        .get("food")
        .expect("the authored needs include food");
    let sites: BTreeMap<_, _> = opening
        .sites
        .iter()
        .map(|site| (site.site_id, site))
        .collect();
    let offer = opening
        .policies
        .offers
        .iter()
        .find(|offer| {
            offer.good_id == food.good_id
                && offer.unit_id == food.unit_id
                && sites[&offer.site_id].location == location
        })
        .expect("the county retains a local food retailer");
    (offer, food)
}
fn purchase_outcome(
    compiled: &CompiledEconomicOpening,
    offer: &SellerOffer,
    food: &GameCommodity,
    principal: FinalDemandPrincipalId,
    ordered: u64,
    order: u8,
) -> Result<(), MaterialCircuitError> {
    babylon_material_circuit::admit_material_purchase(
        &compiled.catalog,
        &compiled.state,
        MaterialPurchase::LocalFinalDemand(FinalDemandOrder {
            order_id: OrderId::from_bytes([order; 32]),
            retailer_site_id: offer.site_id,
            demand_principal_id: principal,
            good_id: food.good_id,
            unit_id: food.unit_id,
            ordered,
            fulfilled: 0,
        }),
        offer.unit_price,
    )
    .map(|_receipt| ())
}
#[test]
fn wealthy_owner_cannot_pay_a_wage_dependent_cohorts_unmet_food_need() {
    let fixture = national_fixture();
    let county = CountyGeoid::try_from("26125").expect("the fixture value fits the target range");
    let location = EconomicLocation::domestic_county(county)
        .expect("the fixture geoid names a domestic county");
    let owner = national_economy::household_principal(location, HouseholdBudgetKey::EarningOwner);
    let wage = national_economy::household_principal(location, HouseholdBudgetKey::EarningNonowner);
    let owner_cohort = fixture
        .detail
        .background_households()
        .iter()
        .find(|cohort| cohort.key.principal == owner)
        .expect("the owner cohort remains a background cohort");
    let wage_cohort = fixture
        .detail
        .background_households()
        .iter()
        .find(|cohort| cohort.key.principal == wage)
        .expect("the wage-dependent cohort remains a background cohort");
    assert_ne!(owner, wage);
    assert!(
        owner_cohort.key.budget.owner_exposure()
            && !wage_cohort.key.budget.owner_exposure()
            && !owner_cohort
                .key
                .budget
                .equivalent_for_consolidation(wage_cohort.key.budget),
        "owner exposure is a causal-key difference, never a pooled cash total"
    );
    let policy = NationalGamePolicy::parse(include_str!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../../content/scenarios/national/defines.toml"
    )))
    .expect("the authored literal parses as the declared type");
    let (offer, food) = local_food_offer(&fixture.opening, &policy, location);
    let wage_cash = wage_cohort.opening_cash.micro_units();
    let combined_cash = wage_cash
        .checked_add(owner_cohort.opening_cash.micro_units())
        .expect("the fixture arithmetic stays in range");
    let price = offer.unit_price.micro_units();
    let quantity =
        u64::try_from(wage_cash / price + 1).expect("the fixture value fits the target range");
    let cost = i128::from(quantity)
        .checked_mul(price)
        .expect("the fixture arithmetic stays in range");
    assert!(
        cost > wage_cash && cost <= combined_cash,
        "the unmet need is affordable only by an invalid pooled cohort"
    );
    let compiled = compiled_fixture();
    assert_eq!(
        purchase_outcome(compiled, offer, food, wage, quantity, 11).err(),
        Some(MaterialCircuitError::MonetaryInvariant),
        "the wage-dependent cohort cannot spend the owner cohort's cash"
    );
    assert!(
        purchase_outcome(compiled, offer, food, wage, 1, 12).is_ok(),
        "the refusal is the unaffordable amount, not an invalid purchase"
    );
}

fn commitment_hours(commitment: &HouseholdTimeCommitment, cohort: &HouseholdCohort) -> u64 {
    let basis = match commitment.basis {
        HouseholdNeedBasis::Persons => cohort.persons,
        HouseholdNeedBasis::Households => cohort.households,
    };
    basis
        .checked_mul(commitment.hours_per_basis)
        .expect("the fixture arithmetic stays in range")
}
fn install_opening_receipts(
    catalog: &babylon_material_circuit::MaterialCatalog,
    state: &mut MaterialCircuitState,
) -> (FinalDemandPrincipalId, u64) {
    state.period = 2;
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        panic!("the national opening uses the monetary circuit")
    };
    let cohorts: BTreeMap<_, _> = economy
        .recurring
        .as_ref()
        .expect("the national opening has recurring household demand")
        .households
        .iter()
        .map(|row| (row.principal_id, (row.persons, row.households)))
        .collect();
    let HouseholdTimeAccounting::Modeled(book) = &mut economy.household_time else {
        panic!("the national opening models household time")
    };
    let mut receipts = Vec::with_capacity(catalog.household_time_policy.len());
    for policy in &catalog.household_time_policy {
        let (persons, households) = cohorts[&policy.principal_id];
        let cohort = HouseholdCohort {
            kind: HouseholdKind::Ordinary,
            principal_id: policy.principal_id,
            households,
            persons,
        };
        let endowment = policy
            .eligible_persons
            .checked_mul(policy.hours_per_eligible_person)
            .expect("the fixture arithmetic stays in range");
        let protected = commitment_hours(&policy.protected, &cohort);
        let protected_hours = protected.min(endowment);
        let protected_unresolved_hours = protected - protected_hours;
        let after_protected = endowment - protected_hours;
        let unpaid_requested_hours = commitment_hours(&policy.routine_provisioning, &cohort);
        let unpaid_allocated_hours = unpaid_requested_hours.min(after_protected);
        let unpaid_unresolved_hours = unpaid_requested_hours - unpaid_allocated_hours;
        receipts.push(HouseholdTimeReceipt {
            principal_id: policy.principal_id,
            period: 1,
            labor_unit_id: policy.labor_unit_id,
            endowment_hours: endowment,
            attended_hours: 0,
            protected_hours,
            protected_unresolved_hours,
            unpaid_requested_hours,
            unpaid_allocated_hours,
            unpaid_unresolved_hours,
            contribution_available_hours: after_protected - unpaid_allocated_hours,
        });
    }
    book.receipts = receipts;
    book.contributions.clear();
    let receipt = book
        .receipts
        .iter()
        .find(|row| row.contribution_available_hours > 1)
        .expect("the opening retains at least one spendable household hour");
    (receipt.principal_id, receipt.contribution_available_hours)
}
fn contribution(
    use_id: [u8; 32],
    principal: FinalDemandPrincipalId,
    actor: u64,
    contributor: u64,
    hours: u64,
) -> HouseholdContributionUse {
    HouseholdContributionUse {
        use_id,
        principal_id: principal,
        actor_id: actor,
        contributor_id: contributor,
        hours,
    }
}
#[test]
fn household_endowment_is_gross_not_the_receipts_spendable_remainder() {
    let fixture = national_fixture();
    let cohort = fixture
        .detail
        .background_households()
        .iter()
        .find(|cohort| cohort.counts.endowment_hours > 1)
        .expect("the national opening retains a background household endowment");
    let principal = cohort.key.principal;
    let gross = cohort.counts.endowment_hours;
    let compiled = compiled_fixture();
    let mut state = compiled.state.clone();
    install_opening_receipts(&compiled.catalog, &mut state);
    let CircuitAccounting::Monetary(economy) = &state.accounting else {
        panic!("the national opening uses the monetary circuit")
    };
    let HouseholdTimeAccounting::Modeled(book) = &economy.household_time else {
        panic!("the national opening models household time")
    };
    let receipt = book
        .receipts
        .iter()
        .find(|receipt| receipt.principal_id == principal)
        .expect("every modeled background household closes one receipt");
    assert_eq!(
        receipt.endowment_hours, gross,
        "the retained figure is the gross endowment, not the spendable remainder"
    );
    assert!(
        receipt.contribution_available_hours < gross,
        "protected and routine-provisioning commitments reduce the spendable figure"
    );
}

#[test]
fn two_organizations_cannot_spend_the_same_household_contribution_hour() {
    let compiled = compiled_fixture();
    let mut state = compiled.state.clone();
    let (principal, available) = install_opening_receipts(&compiled.catalog, &mut state);
    let both = [
        contribution([21; 32], principal, 101, 201, available),
        contribution([22; 32], principal, 102, 202, 1),
    ];
    assert_eq!(
        babylon_material_circuit::consume_household_contributions(
            &compiled.catalog,
            &mut state,
            1,
            &both
        ),
        Err(MaterialCircuitError::HouseholdTimeInvariant),
        "two organizations cannot jointly spend more than the cohort's closed hours"
    );
    let exact = [
        contribution([21; 32], principal, 101, 201, available - 1),
        contribution([22; 32], principal, 102, 202, 1),
    ];
    let exact_result = babylon_material_circuit::consume_household_contributions(
        &compiled.catalog,
        &mut state,
        1,
        &exact,
    );
    assert!(
        exact_result.is_ok(),
        "distinct organizations may spend distinct hours from the one account: {exact_result:?}"
    );
    assert_eq!(
        babylon_material_circuit::consume_household_contributions(
            &compiled.catalog,
            &mut state,
            1,
            &[contribution([21; 32], principal, 101, 201, 1)]
        ),
        Err(MaterialCircuitError::HouseholdTimeInvariant),
        "a reused contribution identity cannot spend an already committed hour again"
    );
}

fn routed_route(fixture: &NationalFixture) -> RouteId {
    fixture
        .aid
        .mandates
        .iter()
        .find_map(|mandate| match mandate.transport {
            AidTransport::Routed { route_id, .. } => Some(route_id),
            AidTransport::Local => None,
        })
        .expect("the authored remote gift uses a staged route")
}
fn assert_route_bottleneck(opening: &EconomicOpening, route: RouteId) {
    let stages: Vec<_> = opening
        .logistics
        .route_stages
        .iter()
        .filter(|stage| stage.route_id == route)
        .collect();
    assert!(
        !stages.is_empty(),
        "the remote route retains its timed stage"
    );
    assert!(
        stages.iter().all(|stage| stage.travel_periods >= 1),
        "freight cannot arrive in its dispatch period"
    );
    let supplies: BTreeMap<_, _> = opening
        .logistics
        .shared_capacity
        .iter()
        .map(|row| (row.corridor_id, row.grams_per_period))
        .collect();
    let memberships: Vec<_> = opening
        .logistics
        .memberships
        .iter()
        .filter(|row| row.route_id == route)
        .collect();
    assert!(
        !memberships.is_empty(),
        "the remote route names its finite corridor memberships"
    );
    let capacities: Vec<u64> = memberships
        .iter()
        .map(|row| {
            *supplies
                .get(&row.corridor_id)
                .expect("every route membership has one shared finite capacity")
        })
        .collect();
    assert!(
        capacities.iter().all(|capacity| *capacity > 0),
        "a route cannot inherit an unbounded corridor"
    );
    let bottleneck = *capacities
        .iter()
        .min()
        .expect("the fixture sequence is non-empty");
    assert!(
        capacities.iter().all(|capacity| bottleneck <= *capacity),
        "the narrowest corridor bounds the whole cross-county route"
    );
    let corridors: BTreeSet<_> = opening
        .logistics
        .shared_capacity
        .iter()
        .map(|row| row.corridor_id)
        .collect();
    assert_eq!(
        corridors.len(),
        opening.logistics.shared_capacity.len(),
        "one authored pool owns one capacity row"
    );
    assert!(
        memberships.iter().any(|membership| opening
            .logistics
            .memberships
            .iter()
            .any(|other| other.corridor_id == membership.corridor_id
                && other.route_id != membership.route_id)),
        "bottleneck pressure propagates through a corridor shared by two routes"
    );
}
fn expected_workplace_key(site: &EconomicSiteSeed) -> WorkplaceCohortKey {
    match &site.source {
        EconomicSiteSource::Qcew(key) => WorkplaceCohortKey::source_backed(*key, site.location)
            .expect("the admitted QCEW site keeps its source county"),
        EconomicSiteSource::MichiganSector { .. } | EconomicSiteSource::Designed { .. } => {
            WorkplaceCohortKey::designed(site.location, site.function)
        }
    }
}

fn assert_household_identity_sets(detail: &NationalDetailPartition, opening: &EconomicOpening) {
    let foreground_households: BTreeSet<_> = detail
        .foreground()
        .household_principals()
        .iter()
        .copied()
        .collect();
    let background_households: BTreeSet<_> = detail
        .background_households()
        .iter()
        .map(|cohort| cohort.key.principal)
        .collect();
    assert_eq!(
        background_households.len(),
        detail.background_households().len(),
        "one background row per household causal key"
    );
    assert!(
        background_households.is_disjoint(&foreground_households),
        "a foreground household principal cannot also be background"
    );
    let opening_households: BTreeSet<_> = opening
        .households
        .iter()
        .map(|household| household.principal_id)
        .collect();
    assert_eq!(
        background_households
            .union(&foreground_households)
            .copied()
            .collect::<BTreeSet<_>>(),
        opening_households,
        "background and foreground household identities partition the source roster"
    );
    assert_eq!(
        detail.background_households().len() + foreground_households.len(),
        opening.households.len(),
        "the authored opening has one household seed per causal key, so no household merge is possible"
    );
}

fn assert_workplace_identity_sets(detail: &NationalDetailPartition, opening: &EconomicOpening) {
    let foreground_sites: BTreeSet<_> = detail
        .foreground()
        .workplaces()
        .iter()
        .chain(detail.foreground().partner_workplaces())
        .copied()
        .collect();
    let background_sites: u64 = detail
        .background_workplaces()
        .iter()
        .map(|cohort| cohort.sites)
        .sum();
    assert_eq!(
        u64::try_from(foreground_sites.len())
            .expect("the fixture site count fits the target range")
            .checked_add(background_sites)
            .expect("the fixture arithmetic stays in range"),
        u64::try_from(opening.sites.len()).expect("the fixture site count fits the target range"),
        "every admitted site is exactly one foreground identity or one counted background site"
    );
    let background_keys: BTreeMap<_, _> = detail
        .background_workplaces()
        .iter()
        .map(|cohort| (cohort.key, cohort.sites))
        .collect();
    assert_eq!(
        background_keys.len(),
        detail.background_workplaces().len(),
        "one background row per workplace causal key"
    );
    let mut expected_keys = BTreeSet::new();
    let mut represented = 0_u64;
    for site in &opening.sites {
        if foreground_sites.contains(&site.site_id) {
            continue;
        }
        let key = expected_workplace_key(site);
        assert!(
            background_keys.contains_key(&key),
            "every non-foreground site maps to its counted workplace key"
        );
        expected_keys.insert(key);
        represented = represented
            .checked_add(1)
            .expect("the fixture arithmetic stays in range");
    }
    assert_eq!(
        represented, background_sites,
        "the key set and the retained site count conserve the same source sites"
    );
    assert_eq!(
        background_keys.len(),
        expected_keys.len(),
        "background rows are exactly the distinct non-foreground causal keys"
    );
    assert_eq!(
        background_sites
            .checked_sub(
                u64::try_from(background_keys.len())
                    .expect("the fixture workplace count fits the target range")
            )
            .expect("the fixture arithmetic stays in range"),
        2,
        "two counties hold both a household-enterprise and a resident-employer fallback site \
         with the same location/function/ownership, so those equivalent sites merge; all other \
         non-foreground sites already have distinct causal keys"
    );
}

fn assert_partition_identity_sets(detail: &NationalDetailPartition, opening: &EconomicOpening) {
    assert_household_identity_sets(detail, opening);
    assert_workplace_identity_sets(detail, opening);
}
#[test]
fn cross_county_bottleneck_and_delayed_freight_keep_the_authored_actor_roster() {
    let fixture = national_fixture();
    assert_route_bottleneck(&fixture.opening, routed_route(fixture));
    assert_partition_identity_sets(&fixture.detail, &fixture.opening);
}

fn stock(good: u8, unit: u8, quantity: u64, cost: i128) -> OpeningCommodityStock {
    OpeningCommodityStock {
        amount: CommodityAmount {
            good_id: GoodId::from_bytes([good; 32]),
            unit_id: UnitId::from_bytes([unit; 32]),
            quantity,
        },
        total_cost: Currency::from_micro_units(cost),
    }
}
#[test]
fn equivalent_pantry_rows_merge_only_within_one_good_and_unit() {
    let merged = refine::merge_stock(vec![
        stock(1, 1, 2, 20),
        stock(2, 1, 5, 50),
        stock(1, 1, 3, 30),
        stock(1, 2, 4, 40),
    ])
    .expect("the fixture stock rows merge without overflow");
    assert_eq!(merged.len(), 3);
    assert_eq!(merged[0].amount.good_id, GoodId::from_bytes([1; 32]));
    assert_eq!(merged[0].amount.unit_id, UnitId::from_bytes([1; 32]));
    assert_eq!(merged[0].amount.quantity, 5);
    assert_eq!(merged[0].total_cost.micro_units(), 50);
    assert_eq!(merged[1].amount.unit_id, UnitId::from_bytes([2; 32]));
    assert_eq!(merged[2].amount.good_id, GoodId::from_bytes([2; 32]));
}

fn household_cohort(
    key: HouseholdCohortKey,
    persons: u64,
    cash: i128,
    quantity: u64,
) -> BackgroundHouseholdCohort {
    BackgroundHouseholdCohort {
        key,
        counts: HouseholdCohortCounts {
            persons,
            households: persons,
            employed: 0,
            reserve: 0,
            eligible_persons: persons,
            endowment_hours: persons
                .checked_mul(10)
                .expect("the fixture arithmetic stays in range"),
        },
        opening_cash: Currency::from_micro_units(cash),
        opening_stock: vec![stock(1, 1, quantity, i128::from(quantity) * 10)],
    }
}

fn workplace_cohort(
    key: WorkplaceCohortKey,
    employed: u64,
    cash: i128,
    quantity: u64,
) -> BackgroundWorkplaceCohort {
    BackgroundWorkplaceCohort {
        key,
        sites: 1,
        employed,
        reserve: 0,
        labor_force: employed,
        opening_cash: Currency::from_micro_units(cash),
        opening_stock: vec![stock(2, 1, quantity, i128::from(quantity) * 10)],
    }
}

#[test]
fn background_rows_merge_only_equivalent_causal_keys() {
    let location = EconomicLocation::domestic_county(county())
        .expect("the fixture geoid names a domestic county");
    let principal = FinalDemandPrincipalId::from_bytes([1; 32]);
    let other = FinalDemandPrincipalId::from_bytes([2; 32]);
    let key = HouseholdCohortKey {
        principal,
        location,
        budget: HouseholdBudgetKey::EarningNonowner,
    };
    let same_key_other_persons = HouseholdCohortKey {
        budget: HouseholdBudgetKey::NoEarnerNonowner,
        ..key
    };
    let different_owner = HouseholdCohortKey {
        principal: other,
        ..key
    };
    let merged = refine::consolidate_household_rows(vec![
        household_cohort(key, 2, 10, 2),
        household_cohort(same_key_other_persons, 3, 5, 3),
        household_cohort(different_owner, 4, 7, 4),
    ])
    .expect("the fixture household rows merge without overflow");
    assert_eq!(
        merged.len(),
        3,
        "a different owner or budget axis is not an equivalent causal key"
    );
    let merged = refine::consolidate_household_rows(vec![
        household_cohort(key, 2, 10, 2),
        household_cohort(key, 3, 5, 3),
    ])
    .expect("the fixture household rows merge without overflow");
    assert_eq!(merged.len(), 1);
    assert_eq!(merged[0].counts.persons, 5);
    assert_eq!(merged[0].counts.eligible_persons, 5);
    assert_eq!(merged[0].opening_cash.micro_units(), 15);
    assert_eq!(merged[0].opening_stock.len(), 1);
    assert_eq!(merged[0].opening_stock[0].amount.quantity, 5);
    assert_eq!(merged[0].opening_stock[0].total_cost.micro_units(), 50);

    let workplace = WorkplaceCohortKey::designed(location, EconomicFunction::Food);
    let other_function = WorkplaceCohortKey::designed(location, EconomicFunction::Manufacturing);
    let merged = refine::consolidate_workplace_rows(vec![
        workplace_cohort(workplace, 2, 10, 2),
        workplace_cohort(other_function, 3, 5, 3),
        workplace_cohort(workplace, 4, 7, 4),
    ])
    .expect("the fixture workplace rows merge without overflow");
    assert_eq!(
        merged.len(),
        2,
        "a different function is not an equivalent workplace key"
    );
    let food = merged
        .iter()
        .find(|row| row.key == workplace)
        .expect("the merged row keeps its causal key");
    assert_eq!(food.sites, 2);
    assert_eq!(food.employed, 6);
    assert_eq!(food.labor_force, 6);
    assert_eq!(food.opening_cash.micro_units(), 17);
    assert_eq!(food.opening_stock.len(), 1);
    assert_eq!(food.opening_stock[0].amount.quantity, 6);
}

fn consolidate(
    opening: &EconomicOpening,
    budgets: &BTreeMap<FinalDemandPrincipalId, HouseholdBudgetKey>,
    foreground: ForegroundSelection,
    commitments: &[AuthoredCommitment],
) -> Result<NationalDetailPartition, ConsolidationError> {
    refine::consolidate_background(
        opening,
        budgets,
        &opening.policies.household_time,
        foreground,
        commitments,
    )
}

fn fixture_commitment(
    donor: FinalDemandPrincipalId,
    recipient: FinalDemandPrincipalId,
) -> AuthoredCommitment {
    AuthoredCommitment {
        id: [9; 32],
        donor,
        recipient,
        location: EconomicLocation::domestic_county(county())
            .expect("the fixture geoid names a domestic county"),
        good_id: GoodId::from_bytes([1; 32]),
        unit_id: UnitId::from_bytes([1; 32]),
        maximum_quantity: 1,
    }
}

#[test]
fn unknown_foreground_principal_is_refused() {
    let fixture = national_fixture();
    let mut foreground = ForegroundSelection::default();
    foreground
        .household_principals
        .insert(FinalDemandPrincipalId::from_bytes([99; 32]));
    assert_eq!(
        consolidate(&fixture.opening, &BTreeMap::new(), foreground, &[]),
        Err(ConsolidationError::UnknownForeground)
    );
}

#[test]
fn duplicate_commitment_identity_is_refused() {
    let fixture = national_fixture();
    let commitment = fixture_commitment(
        FinalDemandPrincipalId::from_bytes([1; 32]),
        FinalDemandPrincipalId::from_bytes([2; 32]),
    );
    let mut foreground = ForegroundSelection::default();
    foreground.commitments.insert(commitment.id);
    assert_eq!(
        consolidate(
            &fixture.opening,
            &BTreeMap::new(),
            foreground,
            &[commitment.clone(), commitment],
        ),
        Err(ConsolidationError::DuplicateForeground)
    );
}

#[test]
fn commitment_without_a_foreground_counterparty_is_refused() {
    let fixture = national_fixture();
    let commitment = fixture_commitment(
        FinalDemandPrincipalId::from_bytes([1; 32]),
        FinalDemandPrincipalId::from_bytes([2; 32]),
    );
    let mut foreground = ForegroundSelection::default();
    foreground.commitments.insert(commitment.id);
    assert_eq!(
        consolidate(
            &fixture.opening,
            &BTreeMap::new(),
            foreground,
            &[commitment],
        ),
        Err(ConsolidationError::Commitment)
    );
}

#[test]
fn background_household_without_a_captured_budget_is_refused() {
    let fixture = national_fixture();
    assert_eq!(
        consolidate(
            &fixture.opening,
            &BTreeMap::new(),
            ForegroundSelection::default(),
            &[],
        ),
        Err(ConsolidationError::MissingBudget)
    );
}

#[test]
fn duplicate_source_household_identity_is_refused() {
    let fixture = national_fixture();
    let mut opening = fixture.opening.clone();
    let duplicate = opening
        .households
        .first()
        .expect("the national opening retains households")
        .clone();
    opening.households.push(duplicate);
    assert_eq!(
        consolidate(
            &opening,
            &BTreeMap::new(),
            ForegroundSelection::default(),
            &[]
        ),
        Err(ConsolidationError::SourceRoster)
    );
}
