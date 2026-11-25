//! The country's sizes: what the shipped national opening holds, counted by place, so that the
//! seekers' member rows can be sized before anything is built on them.
use babylon_kernel::economic_location::EconomicLocation;
use babylon_material_circuit::{
    CircuitAccounting, CommodityKind, FinalDemandPrincipalId, GoodId, SiteId, UnitId,
};
use babylon_persistence::economic_catalog::{CompiledEconomicOpening, EconomicOpening};

use super::economy_health;
use std::collections::{BTreeMap, BTreeSet};

/// One place: an `EconomicLocation` that some site or household account has.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub struct PlaceKey(pub EconomicLocation);

/// The sizes of one place.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct PlaceSizes {
    /// Sites located here.
    pub workplaces: u64,
    /// Staffing pools whose site is here.
    pub pools: u64,
    /// Distinct household ids among the members of those pools.
    pub households: u64,
    /// Existing members of those pools.
    pub members: u64,
    /// Households times pools.
    pub seeker_rows: u64,
    /// `seeker_rows` less the (pool, household) pairs that already have a member.
    pub new_rows: u64,
}

/// The sizes of the whole opening.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CountrySizes {
    pub places_with_households: u64,
    pub workplaces_by_scope: BTreeMap<&'static str, u64>,
    pub household_accounts_by_scope: BTreeMap<&'static str, u64>,
    pub pools: u64,
    pub members: u64,
    pub employment_terms: u64,
    pub member_labor_rows: u64,
    pub offers_goods: u64,
    pub offers_services: u64,
    pub market_rows_at_most: u64,
    pub members_outside_their_place: u64,
    pub seeker_rows: u64,
    pub members_with_seekers: u64,
    pub by_place: BTreeMap<PlaceKey, PlaceSizes>,
}

/// The bound the seekers must fit: the smaller of `MAX_STAFFING_MEMBERS` and the contract's
/// `employment_and_member_labor_rows` (131,072, `contracts/material_circuit_v4.yaml:708`).
pub const SEEKER_BOUND: u64 = 131_072;

fn count(n: usize) -> u64 {
    u64::try_from(n).expect("a count fits in u64")
}

/// `total += by`, failing with words on overflow.
fn add(total: &mut u64, by: u64, what: &str) {
    *total = total
        .checked_add(by)
        .unwrap_or_else(|| panic!("{what} overflowed u64"));
}

fn bump(counts: &mut BTreeMap<&'static str, u64>, location: EconomicLocation) {
    add(
        counts
            .entry(economy_health::scope(&location.to_string()))
            .or_default(),
        1,
        "a scope's count",
    );
}

/// What one place gathers while the pools are read.
#[derive(Default)]
struct PlaceGather {
    households: BTreeSet<FinalDemandPrincipalId>,
    pairs: u64,
}

struct Offers {
    goods: u64,
    services: u64,
}

fn count_offers(opening: &EconomicOpening) -> Offers {
    let kinds: BTreeMap<(GoodId, UnitId), bool> = opening
        .commodities
        .iter()
        .map(|c| {
            (
                (c.good_id, c.unit_id),
                matches!(c.kind, CommodityKind::Storable { .. }),
            )
        })
        .collect();
    let mut offers = Offers {
        goods: 0,
        services: 0,
    };
    for offer in &opening.policies.offers {
        match kinds.get(&(offer.good_id, offer.unit_id)) {
            Some(true) => add(&mut offers.goods, 1, "the goods offers"),
            Some(false) => add(&mut offers.services, 1, "the services offers"),
            None => panic!("an offer names a commodity the opening does not define"),
        }
    }
    offers
}

/// Fills each place's households and seeker rows; returns the totals (seeker rows, new rows).
fn size_seekers(
    by_place: &mut BTreeMap<PlaceKey, PlaceSizes>,
    gather: &mut BTreeMap<PlaceKey, PlaceGather>,
) -> (u64, u64) {
    let mut seeker_rows = 0_u64;
    let mut new_rows = 0_u64;
    for (key, sizes) in by_place {
        let gathered = gather.remove(key).unwrap_or_default();
        sizes.households = count(gathered.households.len());
        sizes.seeker_rows = sizes
            .households
            .checked_mul(sizes.pools)
            .expect("a place's households times its pools overflowed u64");
        sizes.new_rows = sizes
            .seeker_rows
            .checked_sub(gathered.pairs)
            .expect("a place has more member pairs than households times pools");
        add(&mut seeker_rows, sizes.seeker_rows, "the seeker rows");
        add(&mut new_rows, sizes.new_rows, "the new rows");
    }
    (seeker_rows, new_rows)
}

/// The sizes of an opening, counted from the opening and its compiled form.
pub fn country_sizes(
    opening: &EconomicOpening,
    compiled: &CompiledEconomicOpening,
) -> CountrySizes {
    let site_place: BTreeMap<SiteId, EconomicLocation> = opening
        .sites
        .iter()
        .map(|site| (site.site_id, site.location))
        .collect();
    let mut by_place = BTreeMap::<PlaceKey, PlaceSizes>::new();
    let mut gather = BTreeMap::<PlaceKey, PlaceGather>::new();
    let mut workplaces_by_scope = BTreeMap::new();
    for site in &opening.sites {
        bump(&mut workplaces_by_scope, site.location);
        add(
            &mut by_place
                .entry(PlaceKey(site.location))
                .or_default()
                .workplaces,
            1,
            "a place's workplaces",
        );
    }
    let mut household_accounts_by_scope = BTreeMap::new();
    let mut with_households = BTreeSet::new();
    for household in &opening.households {
        bump(&mut household_accounts_by_scope, household.location);
        by_place.entry(PlaceKey(household.location)).or_default();
        if matches!(household.location, EconomicLocation::County(_)) {
            with_households.insert(household.location);
        }
    }
    let mut members = 0_u64;
    let mut outside = 0_u64;
    for seed in &opening.staffing {
        let place = *site_place
            .get(&seed.pool.site_id())
            .expect("a pool's site is a site of the opening");
        let key = PlaceKey(place);
        let sizes = by_place.entry(key).or_default();
        add(&mut sizes.pools, 1, "a place's pools");
        add(
            &mut sizes.members,
            count(seed.members.len()),
            "a place's members",
        );
        let entry = gather.entry(key).or_default();
        let mut pool_households = BTreeSet::new();
        for member in &seed.members {
            add(&mut members, 1, "the members");
            if member.member.residence() != place {
                add(&mut outside, 1, "the members outside their place");
            }
            entry.households.insert(member.member.household_id());
            pool_households.insert(member.member.household_id());
        }
        add(
            &mut entry.pairs,
            count(pool_households.len()),
            "a place's pairs",
        );
    }
    let (seeker_rows, new_rows) = size_seekers(&mut by_place, &mut gather);
    let offers = count_offers(opening);
    let (employment_terms, member_labor_rows) = match &compiled.state.accounting {
        CircuitAccounting::Monetary(book) => {
            (count(book.employment.len()), count(book.member_labor.len()))
        }
        CircuitAccounting::PhysicalControl => (0, 0),
    };
    let market_rows_at_most = offers
        .goods
        .checked_mul(2)
        .and_then(|goods| goods.checked_add(offers.services))
        .expect("the market rows overflowed u64");
    let members_with_seekers = members
        .checked_add(new_rows)
        .expect("the members with seekers overflowed u64");
    CountrySizes {
        places_with_households: count(with_households.len()),
        workplaces_by_scope,
        household_accounts_by_scope,
        pools: count(opening.staffing.len()),
        members,
        employment_terms,
        member_labor_rows,
        offers_goods: offers.goods,
        offers_services: offers.services,
        market_rows_at_most,
        members_outside_their_place: outside,
        seeker_rows,
        members_with_seekers,
        by_place,
    }
}
