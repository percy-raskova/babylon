//! Independent source totals and cash/stock/share conservation through native generation.
use babylon_kernel::economic_location::EconomicLocation;
use babylon_material_circuit::CommodityKind;
use babylon_material_circuit::FinalDemandPrincipalId;
use babylon_material_circuit::{AccountId, HouseholdKind, HouseholdNeedBasis};
use babylon_persistence::economic_catalog::EconomicHouseholdSeed;
use babylon_persistence::economic_catalog::EconomicOpening;
use babylon_persistence::national_counties;
use babylon_persistence::national_economy;
use babylon_persistence::national_economy::NationalAidCapture;
use babylon_persistence::national_economy::NationalGamePolicy;
use babylon_persistence::national_household_allocation;
use babylon_persistence::national_household_allocation::HouseholdBudgetKey;
use babylon_persistence::national_household_allocation::NationalHouseholdAllocation;
use babylon_persistence::national_households;
use babylon_persistence::national_resident_workforce;
use babylon_tick::material_world::MaterialWorldRegister;
use std::collections::{BTreeMap, BTreeSet};
use std::time::Instant;

pub(super) fn assert_people(
    opening: &EconomicOpening,
    policy: &NationalGamePolicy,
    aid: &NationalAidCapture,
) {
    let budgets = national_household_allocation::allocate_households(
        national_counties::national_county_reference().expect("the county reference fixture loads"),
        national_households::national_household_reference()
            .expect("the household reference fixture loads"),
        national_resident_workforce::national_resident_workforce_reference()
            .expect("the workforce reference fixture loads"),
        policy.households.private_owner_households_bps,
    )
    .expect("the fixture households fit the authored cohorts");
    let households: BTreeMap<_, _> = opening
        .households
        .iter()
        .map(|h| (h.principal_id, h))
        .collect();
    assert_eq!(households.len(), opening.households.len());
    let mut assigned = BTreeMap::<_, (u64, u64)>::new();
    for row in &opening.staffing {
        assert!(row.workplace.canonical_bytes().is_ok());
        for member in &row.members {
            assert!(member.subject.canonical_bytes().is_ok());
            let resident = households[&member.member.household_id()];
            assert_eq!(resident.location, member.member.residence());
            assert_eq!(
                member.employed + member.reserve,
                member.member.labor_force()
            );
            let total = assigned.entry(resident.principal_id).or_default();
            total.0 += member.employed;
            total.1 += member.reserve;
        }
    }
    let counted = assert_source_accounts(&budgets, &households, &assigned, aid);
    let domestic: Vec<_> = households
        .values()
        .filter(|h| matches!(h.location, EconomicLocation::County(_)))
        .collect();
    assert_eq!(domestic.len(), counted + aid.children.len());
    assert_eq!(
        domestic
            .iter()
            .map(|h| h.location)
            .collect::<BTreeSet<_>>()
            .len(),
        3_144
    );
    assert_eq!(domestic.iter().map(|h| h.persons).sum::<u64>(), 334_922_499);
    assert_eq!(
        domestic.iter().map(|h| h.households).sum::<u64>(),
        129_227_496
    );
    assert_eq!(
        domestic
            .iter()
            .filter(|h| h.kind == HouseholdKind::CollectiveResidence)
            .map(|h| h.persons)
            .sum::<u64>(),
        8_200_068
    );
    assert_eq!(opening.households.len() - counted - aid.children.len(), 18);
    assert_eq!(opening.sites.len(), 60_634);
    assert!(opening.orders.goods.is_empty() && opening.orders.final_demand.is_empty());
    assert_eq!(opening.recipes.len(), 9);
    assert_eq!(opening.household_templates.len(), 2);
}

fn assert_source_accounts(
    budgets: &NationalHouseholdAllocation,
    households: &BTreeMap<FinalDemandPrincipalId, &EconomicHouseholdSeed>,
    assigned: &BTreeMap<FinalDemandPrincipalId, (u64, u64)>,
    aid: &NationalAidCapture,
) -> usize {
    let mut counted = 0;
    for county in budgets.counties() {
        let location = EconomicLocation::domestic_county(county.county())
            .expect("the fixture geoid names a domestic county");
        for budget in county.budgets() {
            counted += 1;
            let principal = national_economy::household_principal(location, budget.key);
            let row = households[&principal];
            let children: Vec<_> = aid
                .children
                .iter()
                .filter(|child| child.parent == principal)
                .collect();
            let mut counted_people = (row.persons, row.households);
            let mut counted_work = assigned.get(&principal).copied().unwrap_or_default();
            for child in children {
                let actual = households[&child.principal];
                assert_eq!(
                    (actual.persons, actual.households),
                    (child.persons, child.households)
                );
                assert_eq!(actual.location, row.location);
                assert_eq!(actual.kind, HouseholdKind::Ordinary);
                counted_people.0 = counted_people
                    .0
                    .checked_add(actual.persons)
                    .expect("the fixture arithmetic stays in range");
                counted_people.1 = counted_people
                    .1
                    .checked_add(actual.households)
                    .expect("the fixture arithmetic stays in range");
                let work = assigned.get(&child.principal).copied().unwrap_or_default();
                assert_eq!(work, (child.employed, child.reserve));
                counted_work.0 = counted_work
                    .0
                    .checked_add(work.0)
                    .expect("the fixture arithmetic stays in range");
                counted_work.1 = counted_work
                    .1
                    .checked_add(work.1)
                    .expect("the fixture arithmetic stays in range");
            }
            assert_eq!(counted_people, (budget.persons, budget.households));
            assert_eq!(counted_work, (budget.employed, budget.reserve));
            assert!(budget.employed + budget.reserve <= counted_people.0);
            assert_eq!(
                row.kind == HouseholdKind::CollectiveResidence,
                budget.key == HouseholdBudgetKey::CollectiveResidence
            );
        }
    }
    counted
}

pub(super) fn assert_endowments_and_ownership(
    opening: &EconomicOpening,
    policy: &NationalGamePolicy,
    aid: &NationalAidCapture,
) {
    let mut totals = BTreeMap::<EconomicLocation, (u64, u64, i128)>::new();
    let mut stock = BTreeMap::<(EconomicLocation, _, _), (u64, i128)>::new();
    let mut domestic_owners = BTreeSet::new();
    for household in &opening.households {
        if !matches!(household.location, EconomicLocation::County(_)) {
            continue;
        }
        let total = totals.entry(household.location).or_default();
        total.0 += household.persons;
        total.1 += household.households;
        total.2 += household.opening_cash.micro_units();
        for row in &household.opening_stock {
            let value = stock
                .entry((household.location, row.amount.good_id, row.amount.unit_id))
                .or_default();
            value.0 += row.amount.quantity;
            value.1 += row.total_cost.micro_units();
        }
        if [
            HouseholdBudgetKey::EarningOwner,
            HouseholdBudgetKey::NoEarnerOwner,
        ]
        .into_iter()
        .any(|key| {
            household.principal_id == national_economy::household_principal(household.location, key)
        }) {
            domestic_owners.insert(household.principal_id);
        }
    }
    let payer = aid.mandates[0].payer;
    assert!(matches!(payer, AccountId::Organization(_)));
    let organization = opening
        .institutional_cash
        .iter()
        .filter(|account| account.id == payer)
        .collect::<Vec<_>>();
    assert_eq!(organization.len(), 1);
    assert_eq!(
        organization[0].cash.micro_units(),
        policy.aid.organization_opening_cash_micros
    );
    let donor = opening
        .households
        .iter()
        .find(|household| household.principal_id == aid.children[0].principal)
        .expect("the fixture holds the searched element");
    assert!(opening
        .institutions
        .locations
        .iter()
        .any(|row| row.account == payer && row.location == donor.location));
    let total = totals
        .get_mut(&donor.location)
        .expect("the fixture holds the addressed entry");
    total.2 = total
        .2
        .checked_add(organization[0].cash.micro_units())
        .expect("the fixture arithmetic stays in range");
    for (location, (persons, households, cash)) in &totals {
        let mut period_cost = 0;
        for need in &policy.household_needs {
            let units = match need.basis {
                HouseholdNeedBasis::Persons => persons,
                HouseholdNeedBasis::Households => households,
            } * need.units_per_basis;
            let good = &policy.commodities[&need.key];
            let price = good
                .price
                .as_ref()
                .expect("the fixture set the optional field before this read")
                .opening
                .micro_units();
            period_cost += i128::from(units) * price;
            if matches!(good.kind, CommodityKind::Storable { .. }) {
                let pantry = units * policy.opening_pantry_periods;
                assert_eq!(
                    stock[&(*location, good.good_id, good.unit_id)],
                    (pantry, i128::from(pantry) * price)
                );
            }
        }
        assert_eq!(
            *cash,
            period_cost * i128::from(policy.working_capital_periods)
        );
    }
    assert_ownership(opening, &domestic_owners);
    assert_retail_aggregation(opening, policy);
}

fn assert_ownership(opening: &EconomicOpening, domestic_owners: &BTreeSet<FinalDemandPrincipalId>) {
    let locations: BTreeMap<_, _> = opening
        .households
        .iter()
        .map(|h| (h.principal_id, h.location))
        .collect();
    let mut issuer_shares = BTreeMap::<_, u64>::new();
    let mut cross_border = false;
    let sites: BTreeMap<_, _> = opening.sites.iter().map(|s| (s.site_id, s)).collect();
    for claim in &opening.institutions.ownership {
        *issuer_shares.entry(claim.issuer_site_id).or_default() += claim.shares;
        if let AccountId::Household(principal) = claim.beneficiary {
            if matches!(locations[&principal], EconomicLocation::County(_)) {
                assert!(domestic_owners.contains(&principal));
                cross_border |= matches!(
                    sites[&claim.issuer_site_id].location,
                    EconomicLocation::Foreign(_)
                );
            }
        }
    }
    assert_eq!(issuer_shares.len(), opening.sites.len());
    assert!(issuer_shares.values().all(|shares| *shares == 10_000));
    assert!(
        cross_border,
        "the existing Canadian claim reaches domestic owner budgets"
    );
    assert_eq!(opening.equity.len(), opening.institutions.ownership.len());
}

fn assert_retail_aggregation(opening: &EconomicOpening, policy: &NationalGamePolicy) {
    let households: BTreeMap<_, _> = opening
        .households
        .iter()
        .map(|h| (h.principal_id, h))
        .collect();
    let mut required = BTreeMap::<_, u64>::new();
    for purchase in &opening.policies.household_purchases {
        let good = policy
            .commodities
            .values()
            .find(|g| g.good_id == purchase.good_id && g.unit_id == purchase.unit_id)
            .expect("the fixture holds the searched element");
        if !matches!(good.kind, CommodityKind::Storable { .. }) {
            continue;
        }
        let household = households[&purchase.principal_id];
        let template = opening
            .household_templates
            .iter()
            .find(|t| t.id == household.template)
            .expect("the fixture holds the searched element");
        let need = template
            .needs
            .iter()
            .find(|n| n.good_id == purchase.good_id && n.unit_id == purchase.unit_id)
            .expect("the fixture holds the searched element");
        let basis = match need.basis {
            HouseholdNeedBasis::Persons => household.persons,
            HouseholdNeedBasis::Households => household.households,
        };
        *required
            .entry((
                purchase.retailer_site_id,
                purchase.good_id,
                purchase.unit_id,
            ))
            .or_default() += basis * need.units_per_basis;
    }
    let offers: BTreeMap<_, _> = opening
        .policies
        .offers
        .iter()
        .map(|o| ((o.site_id, o.good_id, o.unit_id), o))
        .collect();
    for (key, required) in required {
        let babylon_material_circuit::PricePolicy::Responsive { target_stock, .. } =
            offers[&key].pricing
        else {
            panic!("retail offer must expose finite aggregate buffer")
        };
        assert_eq!(target_stock, required * policy.retailer_buffer_periods);
        let supply: Vec<_> = opening
            .policies
            .replenishment
            .iter()
            .filter(|p| (p.buyer_site_id, p.good_id, p.unit_id) == key)
            .collect();
        let unique: BTreeSet<_> = supply.iter().map(|p| p.supplier_site_id).collect();
        assert_eq!(unique.len(), supply.len());
    }
}

/// Exercise the actual compiler and material register, independently of the source census.
pub fn assert_admitted_state(opening: &EconomicOpening, aid: &NationalAidCapture) {
    use babylon_material_circuit::CircuitAccounting;
    let start = Instant::now();
    let compiled = opening
        .compile()
        .expect("complete current household opening must admit");
    eprintln!("current common admission: {:?}", start.elapsed());
    let state_bytes =
        babylon_material_circuit::encode_material_circuit_state(&compiled.catalog, &compiled.state)
            .expect("the canonical material state encodes");
    let CircuitAccounting::Monetary(e) = &compiled.state.accounting else {
        panic!("national monetary circuit");
    };
    let recurring = e
        .recurring
        .as_ref()
        .expect("the fixture set the optional field before this read");
    assert_eq!(e.aid.mandates, aid.mandates);
    assert!(e.aid.freight.is_empty());
    let added_needs = aid
        .children
        .iter()
        .map(|child| {
            let household = opening
                .households
                .iter()
                .find(|h| h.principal_id == child.principal)
                .expect("the fixture holds the searched element");
            opening
                .household_templates
                .iter()
                .find(|t| t.id == household.template)
                .expect("the fixture holds the searched element")
                .needs
                .len()
        })
        .sum::<usize>();
    assert_eq!(recurring.household_needs.len(), 87_960 + added_needs);
    assert_eq!(recurring.household_purchases.len(), 87_960 + added_needs);
    assert_eq!(e.financial.ownership.len(), 90_794);
    assert_eq!(e.costs.snapshot().equity.len(), 90_794);
    assert_eq!(e.financial.taxes.len(), 76_327 + aid.children.len());
    assert_eq!(e.employment.len(), 100_301 + 1);
    eprintln!("current canonical bytes: {}", state_bytes.len());
    eprintln!(
        "current SHA256: {:02x?}",
        babylon_kernel::content_digest::sha256_of(&state_bytes)
    );
    drop(state_bytes);
    let start = Instant::now();
    let register = MaterialWorldRegister::try_new(&compiled.catalog, 0, compiled.state)
        .expect("complete current opening register must admit");
    eprintln!(
        "current register bytes: {}, elapsed: {:?}",
        register.canonical_bytes().len(),
        start.elapsed()
    );
}
