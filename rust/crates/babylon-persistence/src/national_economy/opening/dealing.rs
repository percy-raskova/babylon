//! Buyers of a period service dealt to its providers in proportion to the persons at work there.
//!
//! The engine holds one provider a buyer and service, so the compiler decides who is given to whom. The
//! dealing reads no price and no want amount, and of a recipe only whether a trade buys the service at all.
use super::markets::{self, ProviderLocations, Providers};
use super::routes::Network;
use super::{Builder, NationalOpeningError, Result};
use crate::national_economy::NationalGamePolicy;
use crate::national_transport::CargoClass;

use babylon_kernel::economic_identity::{EconomicFunction, TradeSet};
use babylon_kernel::economic_location::EconomicLocation;
use babylon_material_circuit::{
    AccountId, CommodityKind, FinalDemandPrincipalId, GoodId, SiteId, UnitId,
};
use std::cmp::{Ordering, Reverse};
use std::collections::{BTreeMap, BTreeSet};

/// A buyer's whole kind is `2^32` parts.
const WHOLE: u128 = 1 << 32;

/// One buyer of one product among buyers of its kind: where it is and how much it counts.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(super) struct Custom {
    pub buyer: AccountId,
    pub location: EconomicLocation,
    pub weight: u64,
}

/// One seller of the product: where it is and its persons at work.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(super) struct Stall {
    pub site: SiteId,
    pub location: EconomicLocation,
    pub employed: u64,
}

/// The provider each domestic buyer was dealt, by good, unit and buyer.
pub(super) type Dealt = BTreeMap<(GoodId, UnitId, AccountId), SiteId>;

/// The shares dealt so far to each stall, with the stalls they are dealt to.
struct Ledger<'a> {
    stalls: &'a [Stall],
    dealt: Vec<u128>,
}

impl<'a> Ledger<'a> {
    fn new(stalls: &'a [Stall]) -> Result<Self> {
        if stalls.iter().any(|stall| stall.employed == 0) {
            return Err(NationalOpeningError::Policy);
        }
        Ok(Self {
            stalls,
            dealt: vec![0; stalls.len()],
        })
    }

    /// Whether the stall `a` is better than `b` for a share: a smaller ratio after it, then a stall at the
    /// buyer's own location, then the lower site id.
    fn better(&self, share: u128, at: EconomicLocation, a: usize, b: usize) -> bool {
        let after = |i: usize| self.dealt[i] + share;
        let left = after(a) * u128::from(self.stalls[b].employed);
        let right = after(b) * u128::from(self.stalls[a].employed);
        let key = |i: usize| (self.stalls[i].location != at, self.stalls[i].site);
        left.cmp(&right).then_with(|| key(a).cmp(&key(b))) == Ordering::Less
    }

    fn smallest(
        &self,
        share: u128,
        at: EconomicLocation,
        mut candidates: impl Iterator<Item = usize>,
    ) -> Option<usize> {
        let mut best = candidates.next()?;
        for index in candidates {
            if self.better(share, at, index, best) {
                best = index;
            }
        }
        Some(best)
    }
}

/// A kind's buyers in order, largest weight first and then by account, each with its share of the kind's
/// whole weight in parts of `2^32`, rounded down.
fn ordered(kind: &[Custom]) -> Vec<(Custom, u128)> {
    let mut buyers = kind.to_vec();
    buyers.sort_unstable_by_key(|custom| (Reverse(custom.weight), custom.buyer));
    let whole: u128 = buyers.iter().map(|custom| u128::from(custom.weight)).sum();
    buyers
        .into_iter()
        .map(|custom| {
            let share = (u128::from(custom.weight) * WHOLE)
                .checked_div(whole)
                .unwrap_or(0);
            (custom, share)
        })
        .collect()
}

fn give(
    ledger: &mut Ledger<'_>,
    map: &mut BTreeMap<AccountId, SiteId>,
    custom: Custom,
    share: u128,
    index: usize,
) {
    ledger.dealt[index] += share;
    map.insert(custom.buyer, ledger.stalls[index].site);
}

/// Deals the buyer to the stall of smallest ratio after it, among all the stalls.
fn deal_over_all(
    ledger: &mut Ledger<'_>,
    map: &mut BTreeMap<AccountId, SiteId>,
    custom: Custom,
    share: u128,
) -> Result<()> {
    let index = ledger
        .smallest(share, custom.location, 0..ledger.stalls.len())
        .ok_or(NationalOpeningError::Policy)?;
    give(ledger, map, custom, share, index);
    Ok(())
}

/// Deals whole buyers to sellers so that each seller's custom is in proportion to its persons at work.
/// `kinds` are dealt one after another; inside a kind the buyers in order of weight, largest first, then by
/// account. A buyer counts as its share of its own kind's whole weight, in parts of 2^32 rounded down. Each
/// goes to the seller for which `(shares dealt to it so far, over every kind, + this share) / employed` is
/// smallest (compared by cross-multiplying in u128), among equals a seller at the buyer's own location
/// first, then the lower site id. A stall with nobody at work is `Policy`. With no stall the map is empty:
/// the caller decides.
pub(super) fn deal(kinds: &[Vec<Custom>], stalls: &[Stall]) -> Result<BTreeMap<AccountId, SiteId>> {
    let mut ledger = Ledger::new(stalls)?;
    let mut map = BTreeMap::new();
    if stalls.is_empty() {
        return Ok(map);
    }
    for kind in kinds {
        for (custom, share) in ordered(kind) {
            deal_over_all(&mut ledger, &mut map, custom, share)?;
        }
    }
    Ok(map)
}

/// The state a stall or a buyer is in: `None` outside the counties.
fn state(location: EconomicLocation) -> Option<[u8; 2]> {
    match location {
        EconomicLocation::County(county) => Some(county.geoid().state_fips()),
        _ => None,
    }
}

/// D5: deals a country service over every domestic provider, at home first. Kinds one after another, shares
/// carried as in `deal`. For a kind, the national level is (the shares already dealt to every stall + the
/// shares of this kind) over every stall's persons at work. Inside the kind, the buyers in `deal`'s order: a
/// buyer goes to the stall of its own state for which `deal`'s ratio after it is smallest (ties as in `deal`)
/// when that stall's ratio BEFORE it is under the national level (`dealt x all employed < level shares x
/// employed`, in u128), the buyer carrying it past the level if it must (E1); else it waits. Only that one
/// stall is tested: the buyer waits even when another stall of its state is under the level. Then the
/// buyers of the kind that waited, in the same order, are dealt over every stall by `deal`'s rule, shares
/// carried. A buyer whose location is not a county has no own state and waits. The same refusals as `deal`.
pub(super) fn deal_at_home_first(
    kinds: &[Vec<Custom>],
    stalls: &[Stall],
) -> Result<BTreeMap<AccountId, SiteId>> {
    let mut ledger = Ledger::new(stalls)?;
    let mut map = BTreeMap::new();
    if stalls.is_empty() {
        return Ok(map);
    }
    let all_employed: u128 = stalls.iter().map(|stall| u128::from(stall.employed)).sum();
    let mut by_state = BTreeMap::<[u8; 2], Vec<usize>>::new();
    for (index, stall) in stalls.iter().enumerate() {
        if let Some(own) = state(stall.location) {
            by_state.entry(own).or_default().push(index);
        }
    }
    for kind in kinds {
        let buyers = ordered(kind);
        let kind_shares: u128 = buyers.iter().map(|(_, share)| share).sum();
        let level = ledger.dealt.iter().sum::<u128>() + kind_shares;
        let mut waiting = Vec::new();
        for (custom, share) in buyers {
            let home = state(custom.location).and_then(|own| by_state.get(&own));
            let chosen = home
                .and_then(|indices| {
                    ledger.smallest(share, custom.location, indices.iter().copied())
                })
                .filter(|&index| {
                    ledger.dealt[index] * all_employed < level * u128::from(stalls[index].employed)
                });
            match chosen {
                Some(index) => give(&mut ledger, &mut map, custom, share, index),
                None => waiting.push((custom, share)),
            }
        }
        for (custom, share) in waiting {
            deal_over_all(&mut ledger, &mut map, custom, share)?;
        }
    }
    Ok(map)
}

/// The buyers that one set of providers serves.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
enum Group {
    /// A service of the place: the providers at one location.
    Place(EconomicLocation),
    /// Any other service: the providers of one state.
    State([u8; 2]),
    /// A service of the country: every domestic provider.
    Country,
}

/// The group a domestic buyer at `location` belongs to for the service `key`; `None` for a buyer that is not
/// in a county, or a service of the place that nobody in its state makes.
fn group(
    policy: &NationalGamePolicy,
    providers: &ProviderLocations,
    network: &mut Network<'_>,
    key: &str,
    location: EconomicLocation,
) -> Result<Option<Group>> {
    let Some(own) = state(location) else {
        return Ok(None);
    };
    if policy.country_services.iter().any(|k| k == key) {
        return Ok(Some(Group::Country));
    }
    if !policy.place_services.iter().any(|k| k == key) {
        return Ok(Some(Group::State(own)));
    }
    if !providers.at(location).is_empty() {
        return Ok(Some(Group::Place(location)));
    }
    let candidates = providers
        .locations()
        .map(|(candidate, _)| candidate)
        .filter(|&candidate| state(candidate) == Some(own));
    Ok(network
        .nearest(location, CargoClass::General, candidates)?
        .map(Group::Place))
}

/// The providers of a group.
fn members(providers: &ProviderLocations, group: Group) -> Vec<SiteId> {
    match group {
        Group::Place(at) => providers.at(at).to_vec(),
        Group::State(own) => providers
            .locations()
            .filter(|&(location, _)| state(location) == Some(own))
            .flat_map(|(_, sites)| sites.iter().copied())
            .collect(),
        Group::Country => providers
            .locations()
            .filter(|&(location, _)| state(location).is_some())
            .flat_map(|(_, sites)| sites.iter().copied())
            .collect(),
    }
}

/// The providers a domestic buyer at `location` may be dealt for the service `key`: those at its own
/// location for a service of the place (`policy.place_services`); every domestic provider for a service of
/// the country (`policy.country_services`); those of its own state for any other. Where its own location has
/// none, a service of the place takes those of the nearest location of its state that has one, which is the
/// location `service_provider` reads today.
pub(super) fn reach(
    policy: &NationalGamePolicy,
    providers: &ProviderLocations,
    network: &mut Network<'_>,
    key: &str,
    location: EconomicLocation,
) -> Result<Vec<SiteId>> {
    Ok(group(policy, providers, network, key, location)?
        .map(|group| members(providers, group))
        .unwrap_or_default())
}

/// Whether a buyer at `location` is dealt its providers under the policy: the twelve trades, domestic buyers.
pub(super) fn applies(policy: &NationalGamePolicy, location: EconomicLocation) -> bool {
    policy.trades == TradeSet::Twelve && state(location).is_some()
}

/// The buyers of each service, by kind: the households first, then the buying sites of each trade.
#[derive(Default)]
struct Buyers {
    households: BTreeMap<String, Vec<Custom>>,
    sites: BTreeMap<String, BTreeMap<EconomicFunction, Vec<Custom>>>,
}

/// Who buys which period service: a household account that is not carved from another buys each service its
/// needs or wants name, a site buys each service its trade's recipe names.
fn buyers(
    builder: &Builder<'_>,
    services: &BTreeSet<String>,
    carved: &BTreeSet<FinalDemandPrincipalId>,
) -> Result<Buyers> {
    let mut found = Buyers::default();
    for household in &builder.opening.households {
        if carved.contains(&household.principal_id) || state(household.location).is_none() {
            continue;
        }
        for row in markets::purchases(builder, household)? {
            if services.contains(&row.key) {
                found.households.entry(row.key).or_default().push(Custom {
                    buyer: AccountId::Household(household.principal_id),
                    location: household.location,
                    weight: household.persons,
                });
            }
        }
    }
    for actor in builder.actors.values() {
        if actor.process_id.is_none() || state(actor.location).is_none() {
            continue;
        }
        let recipe = builder
            .policy
            .recipes
            .get(&actor.function)
            .ok_or(NationalOpeningError::Policy)?;
        for key in recipe.inputs.keys().filter(|key| services.contains(*key)) {
            found
                .sites
                .entry(key.clone())
                .or_default()
                .entry(actor.function)
                .or_default()
                .push(Custom {
                    buyer: AccountId::Site(actor.site_id),
                    location: actor.location,
                    weight: actor.force,
                });
        }
    }
    Ok(found)
}

/// A group's representative buyer location and its kinds in order.
type Grouped = (EconomicLocation, Vec<Vec<Custom>>);

/// Splits the kinds of one service by group, each group holding its kinds in order.
fn grouped(
    builder: &Builder<'_>,
    locations: &ProviderLocations,
    network: &mut Network<'_>,
    key: &str,
    kinds: Vec<Vec<Custom>>,
) -> Result<BTreeMap<Group, Grouped>> {
    let mut cache = BTreeMap::<EconomicLocation, Option<Group>>::new();
    let mut groups = BTreeMap::<Group, Grouped>::new();
    for kind in kinds {
        let mut split = BTreeMap::<Group, (EconomicLocation, Vec<Custom>)>::new();
        for custom in kind {
            let found = if let Some(found) = cache.get(&custom.location) {
                *found
            } else {
                let found = group(builder.policy, locations, network, key, custom.location)?;
                cache.insert(custom.location, found);
                found
            };
            if let Some(found) = found {
                split
                    .entry(found)
                    .or_insert_with(|| (custom.location, Vec::new()))
                    .1
                    .push(custom);
            }
        }
        for (found, (representative, customs)) in split {
            groups
                .entry(found)
                .or_insert_with(|| (representative, Vec::new()))
                .1
                .push(customs);
        }
    }
    Ok(groups)
}

/// The stalls of a group's providers.
fn stalls(builder: &Builder<'_>, sites: &[SiteId]) -> Result<Vec<Stall>> {
    sites
        .iter()
        .map(|site| {
            let actor = builder
                .actors
                .get(site)
                .ok_or(NationalOpeningError::Identity)?;
            Ok(Stall {
                site: *site,
                location: actor.location,
                employed: actor.employed,
            })
        })
        .collect()
}

/// Deals every domestic buyer of every period service its provider, under the twelve trades. An account carved
/// from another (an aid donor or recipient, the support claimant) is not dealt: it takes its parent's provider.
/// Under any other trades the map is empty and `service_provider` decides, as before.
pub(super) fn deal_services(
    builder: &Builder<'_>,
    providers: &Providers,
    network: &mut Network<'_>,
) -> Result<Dealt> {
    let mut dealt = Dealt::new();
    if builder.policy.trades != TradeSet::Twelve {
        return Ok(dealt);
    }
    let mut parents = BTreeMap::<FinalDemandPrincipalId, Vec<FinalDemandPrincipalId>>::new();
    for child in &builder.aid.children {
        parents
            .entry(child.parent)
            .or_default()
            .push(child.principal);
    }
    if let Some(claimant) = &builder.support_claimant {
        parents
            .entry(claimant.parent)
            .or_default()
            .push(claimant.principal);
    }
    let carved: BTreeSet<_> = parents.values().flatten().copied().collect();
    let services: BTreeMap<String, (GoodId, UnitId)> = builder
        .policy
        .commodities
        .iter()
        .filter(|(_, good)| matches!(good.kind, CommodityKind::PeriodService { .. }))
        .filter(|(_, good)| providers.contains_key(&(good.good_id, good.unit_id)))
        .map(|(key, good)| (key.clone(), (good.good_id, good.unit_id)))
        .collect();
    let names: BTreeSet<String> = services.keys().cloned().collect();
    let mut found = buyers(builder, &names, &carved)?;
    for (key, (good, unit)) in &services {
        let locations = &providers[&(*good, *unit)];
        let mut kinds = vec![found.households.remove(key).unwrap_or_default()];
        kinds.extend(found.sites.remove(key).unwrap_or_default().into_values());
        kinds.retain(|kind| !kind.is_empty());
        for (kind, (representative, group_kinds)) in
            grouped(builder, locations, network, key, kinds)?
        {
            let sites = reach(builder.policy, locations, network, key, representative)?;
            let stalls = stalls(builder, &sites)?;
            let map = if kind == Group::Country {
                deal_at_home_first(&group_kinds, &stalls)?
            } else {
                deal(&group_kinds, &stalls)?
            };
            dealt.extend(
                map.into_iter()
                    .map(|(buyer, site)| ((*good, *unit, buyer), site)),
            );
        }
    }
    let given: Vec<_> = dealt
        .iter()
        .filter_map(|(&(good, unit, buyer), &site)| match buyer {
            AccountId::Household(parent) => parents
                .get(&parent)
                .map(|children| (good, unit, children, site)),
            _ => None,
        })
        .collect();
    for (good, unit, children, site) in given {
        for child in children {
            dealt.insert((good, unit, AccountId::Household(*child)), site);
        }
    }
    Ok(dealt)
}

#[cfg(test)]
mod tests {
    use super::*;
    use babylon_kernel::economic_location::ForeignCounterpart;
    use babylon_kernel::geography::CountyGeoid;

    fn county(code: &str) -> EconomicLocation {
        EconomicLocation::domestic_county(CountyGeoid::try_from(code).expect("a county"))
            .expect("a domestic county")
    }

    fn account(id: u8) -> AccountId {
        AccountId::Site(SiteId::from_bytes([id; 32]))
    }

    fn stall(id: u8, code: &str, employed: u64) -> Stall {
        Stall {
            site: SiteId::from_bytes([id; 32]),
            location: county(code),
            employed,
        }
    }

    fn custom(id: u8, code: &str, weight: u64) -> Custom {
        Custom {
            buyer: account(id),
            location: county(code),
            weight,
        }
    }

    fn site(id: u8) -> SiteId {
        SiteId::from_bytes([id; 32])
    }

    #[test]
    fn whole_buyers_are_dealt_in_proportion() {
        let stalls = [
            stall(1, "26163", 60),
            stall(2, "26163", 30),
            stall(3, "26163", 10),
        ];
        let kind: Vec<_> = (10..20).map(|id| custom(id, "26163", 10)).collect();
        let map = deal(&[kind], &stalls).expect("deals");
        let count = |id: u8| map.values().filter(|&&s| s == site(id)).count();
        assert_eq!((count(1), count(2), count(3)), (6, 3, 1));

        let stalls = [stall(1, "26163", 50), stall(2, "26163", 50)];
        let map = deal(
            &[vec![custom(10, "26163", 70), custom(11, "26163", 30)]],
            &stalls,
        )
        .expect("deals");
        assert_ne!(map[&account(10)], map[&account(11)]);

        let map = deal(
            &[vec![custom(10, "26163", 70), custom(11, "26163", 30)]],
            &stalls[..1],
        )
        .expect("deals");
        assert!(map.values().all(|&s| s == site(1)));
    }

    #[test]
    fn equal_ratios_go_to_the_buyers_own_location_then_the_lower_site() {
        let stalls = [stall(1, "26163", 10), stall(2, "17031", 10)];
        let map = deal(&[vec![custom(10, "17031", 10)]], &stalls).expect("deals");
        assert_eq!(map[&account(10)], site(2));
        let map = deal(&[vec![custom(10, "36061", 10)]], &stalls).expect("deals");
        assert_eq!(map[&account(10)], site(1));
        assert_eq!(
            deal(&[vec![custom(10, "26163", 10)]], &[stall(1, "26163", 0)]),
            Err(NationalOpeningError::Policy)
        );
        assert_eq!(
            deal(&[vec![custom(10, "26163", 10)]], &[]),
            Ok(BTreeMap::new())
        );
    }

    #[test]
    fn a_later_kind_goes_where_room_is_left() {
        let stalls = [stall(1, "26163", 60), stall(2, "26163", 40)];
        let kinds = [vec![custom(10, "26163", 5)], vec![custom(11, "26163", 5)]];
        let map = deal(&kinds, &stalls).expect("deals");
        assert_eq!(map[&account(10)], site(1));
        assert_eq!(map[&account(11)], site(2));
    }

    fn rotated<T: Clone>(rows: &[T], turn: usize) -> Vec<T> {
        let mut rows = rows.to_vec();
        let turn = turn % rows.len();
        rows.rotate_left(turn);
        rows.reverse();
        rows
    }

    #[test]
    fn the_dealing_is_the_same_in_any_order() {
        let stalls = [
            stall(1, "26163", 60),
            stall(2, "26163", 20),
            stall(3, "22033", 20),
            stall(4, "22033", 35),
        ];
        let first = vec![
            custom(10, "26163", 50),
            custom(11, "26163", 20),
            custom(12, "22033", 30),
            custom(13, "22033", 10),
            custom(14, "22033", 10),
        ];
        let second = vec![custom(20, "26163", 3), custom(21, "22033", 3)];
        let kinds = [first.clone(), second.clone()];
        let home = deal_at_home_first(&kinds, &stalls).expect("deals");
        let plain = deal(&kinds, &stalls).expect("deals");
        for turn in 1..5 {
            let kinds = [rotated(&first, turn), rotated(&second, turn)];
            let stalls = rotated(&stalls, turn);
            assert_eq!(deal_at_home_first(&kinds, &stalls).expect("deals"), home);
            assert_eq!(deal(&kinds, &stalls).expect("deals"), plain);
        }
    }

    #[test]
    fn a_country_service_is_bought_at_home_first() {
        let stalls = [
            stall(1, "26163", 60),
            stall(2, "26163", 20),
            stall(3, "22033", 20),
        ];
        let kind = vec![
            custom(50, "26163", 50),
            custom(20, "26163", 20),
            custom(30, "22033", 30),
            custom(10, "22033", 10),
        ];
        let map = deal_at_home_first(std::slice::from_ref(&kind), &stalls).expect("deals");
        assert_eq!(
            map,
            BTreeMap::from([
                (account(50), site(1)),
                (account(30), site(3)),
                (account(20), site(2)),
                (account(10), site(1)),
            ])
        );
        // Each state dealt on its own, as a service that is not of the country is.
        let own = |code: &str| -> Vec<Custom> {
            kind.iter()
                .filter(|c| c.location == county(code))
                .copied()
                .collect()
        };
        let mut by_state = deal(&[own("26163")], &stalls[..2]).expect("deals");
        by_state.extend(deal(&[own("22033")], &stalls[2..]).expect("deals"));
        assert_eq!(
            by_state,
            BTreeMap::from([
                (account(50), site(1)),
                (account(20), site(2)),
                (account(30), site(3)),
                (account(10), site(3)),
            ])
        );
        let abroad = Custom {
            buyer: account(60),
            location: EconomicLocation::Foreign(ForeignCounterpart::Canada),
            weight: 10,
        };
        let map = deal_at_home_first(&[vec![abroad]], &stalls).expect("deals");
        assert_eq!(map.len(), 1);
    }

    #[test]
    fn only_the_nearest_ratio_is_tested() {
        let stalls = [
            stall(1, "26163", 100),
            stall(2, "26163", 5),
            stall(3, "22033", 95),
        ];
        let kind = vec![
            custom(100, "26163", 100),
            custom(10, "26163", 10),
            custom(90, "22033", 90),
        ];
        let map = deal_at_home_first(&[kind], &stalls).expect("deals");
        assert_eq!(
            map,
            BTreeMap::from([
                (account(100), site(1)),
                (account(90), site(3)),
                (account(10), site(3)),
            ])
        );
    }
}
