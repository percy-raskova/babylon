//! Independent source totals and cash/stock/share conservation through native generation.
use super::*;
use babylon_material_circuit::{AccountId, HouseholdKind, HouseholdNeedBasis};
use babylon_persistence::{
    national_economy::household_principal,
    national_household_allocation::{allocate_households, HouseholdBudgetKey},
    national_households::national_household_reference,
};

pub(super) fn assert_people(opening: &EconomicOpening, policy: &NationalGamePolicy) {
    let budgets = allocate_households(
        national_county_reference().unwrap(),
        national_household_reference().unwrap(),
        national_resident_workforce_reference().unwrap(),
        policy.households.private_owner_households_bps,
    )
    .unwrap();
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
    let mut counted = 0;
    for county in budgets.counties() {
        let location = EconomicLocation::domestic_county(county.county()).unwrap();
        for budget in county.budgets() {
            counted += 1;
            let principal = household_principal(location, budget.key);
            let row = households[&principal];
            assert_eq!(
                (row.persons, row.households),
                (budget.persons, budget.households)
            );
            assert_eq!(
                assigned.get(&principal).copied().unwrap_or_default(),
                (budget.employed, budget.reserve)
            );
            assert!(budget.employed + budget.reserve <= row.persons);
            assert_eq!(
                row.kind == HouseholdKind::CollectiveResidence,
                budget.key == HouseholdBudgetKey::CollectiveResidence
            );
        }
    }
    let domestic: Vec<_> = households
        .values()
        .filter(|h| matches!(h.location, EconomicLocation::County(_)))
        .collect();
    assert_eq!(domestic.len(), counted);
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
    assert_eq!(opening.households.len() - counted, 18);
    assert_eq!(opening.sites.len(), 60_634);
    assert!(opening.orders.goods.is_empty() && opening.orders.final_demand.is_empty());
    assert_eq!(opening.recipes.len(), 9);
    assert_eq!(opening.household_templates.len(), 2);
}

pub(super) fn assert_endowments_and_ownership(
    opening: &EconomicOpening,
    policy: &NationalGamePolicy,
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
        .any(|key| household.principal_id == household_principal(household.location, key))
        {
            domestic_owners.insert(household.principal_id);
        }
    }
    for (location, (persons, households, cash)) in &totals {
        let mut period_cost = 0;
        for need in &policy.household_needs {
            let units = match need.basis {
                HouseholdNeedBasis::Persons => persons,
                HouseholdNeedBasis::Households => households,
            } * need.units_per_basis;
            let good = &policy.commodities[&need.key];
            let price = good.price.as_ref().unwrap().opening.micro_units();
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
    assert_retail_aggregation(opening, policy);
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
            .unwrap();
        if !matches!(good.kind, CommodityKind::Storable { .. }) {
            continue;
        }
        let household = households[&purchase.principal_id];
        let template = opening
            .household_templates
            .iter()
            .find(|t| t.id == household.template)
            .unwrap();
        let need = template
            .needs
            .iter()
            .find(|n| n.good_id == purchase.good_id && n.unit_id == purchase.unit_id)
            .unwrap();
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
pub fn assert_admitted_state(opening: &EconomicOpening) {
    use babylon_material_circuit::{encode_material_circuit_state, CircuitAccounting};
    let start = std::time::Instant::now();
    let compiled = opening
        .compile()
        .expect("complete state16 household opening must admit");
    eprintln!("state16 common admission: {:?}", start.elapsed());
    let state_bytes = encode_material_circuit_state(&compiled.state).unwrap();
    let CircuitAccounting::Monetary(e) = &compiled.state.accounting else {
        panic!("national monetary circuit");
    };
    let recurring = e.recurring.as_ref().unwrap();
    assert_eq!(recurring.household_needs.len(), 87_960);
    assert_eq!(recurring.household_purchases.len(), 87_960);
    assert_eq!(e.financial.ownership.len(), 90_794);
    assert_eq!(e.costs.snapshot().equity.len(), 90_794);
    assert_eq!(e.financial.taxes.len(), 76_327);
    assert_eq!(e.employment.len(), 100_301);
    eprintln!("state16 canonical bytes: {}", state_bytes.len());
    eprintln!(
        "state16 SHA256: {:02x?}",
        babylon_kernel::content_digest::sha256_of(&state_bytes)
    );
    drop(state_bytes);
    let start = std::time::Instant::now();
    let register = babylon_tick::material_world::MaterialWorldRegister::try_new(0, compiled.state)
        .expect("complete state16 opening register must admit");
    eprintln!(
        "state16 register bytes: {}, elapsed: {:?}",
        register.canonical_bytes().len(),
        start.elapsed()
    );
}
