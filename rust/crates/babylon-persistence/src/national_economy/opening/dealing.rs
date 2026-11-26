//! Buyers of a period service dealt to its providers in proportion to the persons at work there.
//!
//! The engine holds one provider a buyer and service, so the compiler decides who is given to whom. The
//! dealing reads no price and no want amount, and of a recipe only whether a trade buys the service at all.
use super::markets::{self, Preferences, ProviderLocations, Providers};
use super::routes::Network;
use super::{ActorContext, Builder, NationalOpeningError, Result};
use crate::national_economy::NationalGamePolicy;
use crate::national_transport::CargoClass;

use crate::economic_catalog::EconomicOpening;
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

/// A buyer's share at one maker: `part` of `whole`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(super) struct Share {
    pub maker: SiteId,
    pub part: u128,
    pub whole: u128,
}

fn as_signed(value: u128) -> Result<i128> {
    i128::try_from(value).map_err(|_| NationalOpeningError::Arithmetic)
}

/// The stall with the most room left, among those not yet used by this buyer: the lower site id on a tie.
/// A stall's room is `employed x whole weight - taken x all stalls' employed`, exact in `i128`.
fn most_room(
    stalls: &[Stall],
    taken: &[i128],
    used: &[bool],
    weight: i128,
    all: i128,
) -> Option<usize> {
    (0..stalls.len())
        .filter(|&index| !used[index])
        .max_by_key(|&index| {
            let room = i128::from(stalls[index].employed) * weight - taken[index] * all;
            (room, Reverse(stalls[index].site))
        })
}

/// Deals buyers' weights over stalls by room alone. A stall's room is its persons at work over all stalls'
/// times the buyers' whole weight, kept exact as `employed x whole weight - taken x all stalls' employed`.
/// Buyers in order of weight, largest first, then by account; each takes from the stalls with the MOST room
/// left first (the lower site id on a tie), as much as each has left (rounded up to a whole unit), up to
/// `most` stalls; the last of them takes whatever is left, past its room if it must. A share's `part` is the
/// weight taken there and its `whole` the buyer's weight. A stall with nobody at work is `Policy`; no stall
/// gives an empty map.
pub(super) fn deal_by_most_room(
    custom: &[Custom],
    stalls: &[Stall],
    most: usize,
) -> Result<BTreeMap<AccountId, Vec<Share>>> {
    if stalls.iter().any(|stall| stall.employed == 0) {
        return Err(NationalOpeningError::Policy);
    }
    let mut map = BTreeMap::new();
    if stalls.is_empty() {
        return Ok(map);
    }
    let all: i128 = stalls.iter().map(|stall| i128::from(stall.employed)).sum();
    let weight = as_signed(custom.iter().map(|c| u128::from(c.weight)).sum())?;
    let mut taken = vec![0_i128; stalls.len()];
    let mut buyers = custom.to_vec();
    buyers.sort_unstable_by_key(|c| (Reverse(c.weight), c.buyer));
    for buyer in buyers.into_iter().filter(|c| c.weight > 0) {
        let whole = u128::from(buyer.weight);
        let mut remaining = i128::from(buyer.weight);
        let mut used = vec![false; stalls.len()];
        let mut shares = Vec::<Share>::new();
        while remaining > 0 {
            let Some(index) = most_room(stalls, &taken, &used, weight, all) else {
                return Err(NationalOpeningError::Policy);
            };
            let room = i128::from(stalls[index].employed) * weight - taken[index] * all;
            let last = shares.len() + 1 >= most.max(1) || used.iter().filter(|u| !**u).count() == 1;
            let own = if room > 0 {
                (room + all - 1) / all
            } else {
                remaining
            };
            let part = if last { remaining } else { remaining.min(own) };
            used[index] = true;
            taken[index] += part;
            remaining -= part;
            shares.push(Share {
                maker: stalls[index].site,
                part: u128::try_from(part).map_err(|_| NationalOpeningError::Arithmetic)?,
                whole,
            });
        }
        map.insert(buyer.buyer, shares);
    }
    Ok(map)
}

/// A cap dealt over shares by largest remainder (equal remainders to the lower site id), so that the parts
/// sum to `cap`; a part that comes to 0 gives no row. The rows come in the order of the shares.
pub(super) fn caps(cap: u64, shares: &[Share]) -> Result<Vec<(SiteId, u64)>> {
    let total: u128 = shares.iter().map(|share| share.part).sum();
    if total == 0 {
        return Ok(Vec::new());
    }
    let mut rows: Vec<(SiteId, u128, u128)> = shares
        .iter()
        .map(|share| {
            let scaled = u128::from(cap) * share.part;
            (share.maker, scaled / total, scaled % total)
        })
        .collect();
    let given: u128 = rows.iter().map(|row| row.1).sum();
    let mut left = u128::from(cap) - given;
    let mut order: Vec<usize> = (0..rows.len()).collect();
    order.sort_unstable_by_key(|&index| (Reverse(rows[index].2), rows[index].0));
    for index in order {
        if left == 0 {
            break;
        }
        rows[index].1 += 1;
        left -= 1;
    }
    rows.into_iter()
        .filter(|row| row.1 > 0)
        .map(|(maker, part, _)| {
            Ok((
                maker,
                u64::try_from(part).map_err(|_| NationalOpeningError::Arithmetic)?,
            ))
        })
        .collect()
}

/// The foreign regions holding a provider of a product with persons at work, in location order: the list
/// `ProviderLocations::secondary_candidates` rotates for a county buyer (dependencies are not in it).
///
/// # Errors
/// The region, for a foreign region whose every site making the product has nobody at work: a stop, named.
pub fn crossing_regions(
    opening: &EconomicOpening,
    good: GoodId,
    unit: UnitId,
) -> std::result::Result<Vec<EconomicLocation>, EconomicLocation> {
    let recipes: BTreeSet<_> = opening
        .recipes
        .iter()
        .filter(|recipe| (recipe.output.good_id, recipe.output.unit_id) == (good, unit))
        .map(|recipe| recipe.id)
        .collect();
    let mut work = BTreeMap::<SiteId, u64>::new();
    for pool in &opening.staffing {
        *work.entry(pool.pool.site_id()).or_default() += pool
            .members
            .iter()
            .map(|member| member.employed)
            .sum::<u64>();
    }
    let mut regions = BTreeMap::<EconomicLocation, u64>::new();
    for site in &opening.sites {
        let makes = site
            .processes
            .iter()
            .any(|process| recipes.contains(&process.recipe));
        if makes && matches!(site.location, EconomicLocation::Foreign(_)) {
            *regions.entry(site.location).or_default() +=
                work.get(&site.site_id).copied().unwrap_or(0);
        }
    }
    if let Some((&region, _)) = regions.iter().find(|(_, persons)| **persons == 0) {
        return Err(region);
    }
    Ok(regions.into_keys().collect())
}

/// A domestic buyer's region abroad: `regions[u32::from_be_bytes(first four bytes of the site id) %
/// regions.len()]`, the first location of `secondary_candidates`' rotation; `None` with no region. Reads no
/// number.
#[must_use]
pub fn crossing_region(regions: &[EconomicLocation], buyer: SiteId) -> Option<EconomicLocation> {
    let bytes = buyer.as_bytes();
    let turn =
        usize::try_from(u32::from_be_bytes([bytes[0], bytes[1], bytes[2], bytes[3]])).ok()?;
    regions.get(turn.checked_rem(regions.len())?).copied()
}

/// The provider abroad of a domestic buying site of a crossing service: at `crossing_region`'s region, its
/// largest provider (the location's first site, `ProviderLocations::new`'s order). Reads no number of the
/// scenario. A buyer that is not in a county has none.
#[allow(
    clippy::unnecessary_wraps,
    reason = "the plan fixes this signature, as every function of the dealing returns `Result`"
)]
pub(super) fn provider_abroad(
    providers: &ProviderLocations,
    buyer: SiteId,
    location: EconomicLocation,
) -> Result<Option<SiteId>> {
    if state(location).is_none() {
        return Ok(None);
    }
    Ok(crossing_region(providers.regions(), buyer)
        .and_then(|region| providers.at(region).first().copied()))
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

/// What each buyer abroad (or in a dependency) of a crossing service takes from the domestic providers, by
/// good, unit and buyer: the rows of its export part.
pub(super) type Exports = BTreeMap<(GoodId, UnitId, SiteId), Vec<(SiteId, u64)>>;

/// `floor(required x share / 10_000)`.
fn part_of(required: u64, share: u16) -> Result<u64> {
    u64::try_from(u128::from(required) * u128::from(share) / 10_000)
        .map_err(|_| NationalOpeningError::Arithmetic)
}

/// A region abroad whose every site making the service has nobody at work is a stop (decision 4b).
fn check_regions(builder: &Builder<'_>, key: &str) -> Result<()> {
    let mut persons = BTreeMap::<EconomicLocation, u64>::new();
    for actor in builder.actors.values() {
        let makes = actor.process_id.is_some()
            && matches!(actor.location, EconomicLocation::Foreign(_))
            && builder
                .policy
                .recipes
                .get(&actor.function)
                .is_some_and(|recipe| recipe.output == key);
        if makes {
            *persons.entry(actor.location).or_default() += actor.employed;
        }
    }
    if persons.values().any(|&employed| employed == 0) {
        return Err(NationalOpeningError::Policy);
    }
    Ok(())
}

/// Deals the export part of every buyer abroad of each crossing service over the domestic providers by room,
/// one dealing a service over all those buyers together. A buyer with no provider at its own location, or no
/// export, has no row.
pub(super) fn exports(
    builder: &Builder<'_>,
    providers: &Providers,
    network: &mut Network<'_>,
    preferences: &mut Preferences,
) -> Result<Exports> {
    let mut exported = Exports::new();
    for key in &builder.policy.crossing_services {
        let good = builder.commodity(key)?;
        let (good_id, unit_id) = (good.good_id, good.unit_id);
        let Some(locations) = providers.get(&(good_id, unit_id)) else {
            continue;
        };
        check_regions(builder, key)?;
        let sites: Vec<SiteId> = locations
            .locations()
            .filter(|&(location, _)| state(location).is_some())
            .flat_map(|(_, sites)| sites.iter().copied())
            .collect();
        let stalls = stalls(builder, &sites)?;
        let mut customs = Vec::new();
        for actor in builder.actors.values() {
            let buys = actor.process_id.is_some()
                && state(actor.location).is_none()
                && builder
                    .policy
                    .recipes
                    .get(&actor.function)
                    .is_some_and(|recipe| recipe.inputs.contains_key(key));
            if !buys {
                continue;
            }
            let required = markets::required_input(builder, actor, key)?;
            let export = part_of(
                required,
                markets::foreign_share_bps(builder.policy, actor.location, key)?,
            )?;
            let own = markets::service_provider(
                providers,
                network,
                preferences,
                actor.location,
                good_id,
                unit_id,
            )?;
            if export > 0 && own.is_some() {
                customs.push(Custom {
                    buyer: AccountId::Site(actor.site_id),
                    location: actor.location,
                    weight: export,
                });
            }
        }
        for (buyer, shares) in deal_by_most_room(&customs, &stalls, stalls.len())? {
            let (AccountId::Site(site), Some(share)) = (buyer, shares.first()) else {
                return Err(NationalOpeningError::Identity);
            };
            let rows = caps(
                u64::try_from(share.whole).map_err(|_| NationalOpeningError::Arithmetic)?,
                &shares,
            )?;
            exported.insert((good_id, unit_id, site), rows);
        }
    }
    Ok(exported)
}

/// The rows a buying site holds of the service `key`, as (provider, cap): `home` is the provider it is dealt
/// at its own side of the border. A service that does not cross gives one row at its provider, of the whole
/// requirement. A crossing service gives a domestic site its home row at `required - abroad` and one more at
/// its provider abroad at `abroad`; a site abroad its own provider at `required - export` and its export rows.
pub(super) fn service_rows(
    builder: &Builder<'_>,
    providers: &Providers,
    exported: &Exports,
    actor: &ActorContext,
    key: &str,
    home: Option<SiteId>,
    required: u64,
) -> Result<Vec<(SiteId, u64)>> {
    let policy = builder.policy;
    if !policy.crossing_services.iter().any(|k| k == key) {
        return Ok(home
            .map(|provider| (provider, required))
            .into_iter()
            .collect());
    }
    let good = builder.commodity(key)?;
    let locations = providers.get(&(good.good_id, good.unit_id));
    let mut rows = Vec::new();
    if state(actor.location).is_some() {
        let abroad = locations
            .map(|locations| provider_abroad(locations, actor.site_id, actor.location))
            .transpose()?
            .flatten()
            .map(|provider| {
                markets::foreign_share_bps(policy, actor.location, key)
                    .and_then(|share| part_of(required, share))
                    .map(|cap| (provider, cap))
            })
            .transpose()?
            .filter(|&(_, cap)| cap > 0);
        let home_cap = required - abroad.map_or(0, |(_, cap)| cap);
        rows.extend(
            home.filter(|_| home_cap > 0)
                .map(|provider| (provider, home_cap)),
        );
        rows.extend(abroad);
    } else if let Some(provider) = home {
        let export = exported
            .get(&(good.good_id, good.unit_id, actor.site_id))
            .map_or(&[][..], Vec::as_slice);
        let sent: u64 = export.iter().map(|&(_, cap)| cap).sum();
        let home_cap = required
            .checked_sub(sent)
            .ok_or(NationalOpeningError::Arithmetic)?;
        rows.extend((home_cap > 0).then_some((provider, home_cap)));
        rows.extend(export.iter().copied());
    }
    Ok(rows)
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

    fn share(id: u8, part: u128, whole: u128) -> Share {
        Share {
            maker: site(id),
            part,
            whole,
        }
    }

    #[test]
    fn caps_sum_to_the_cap() {
        let shares = [share(1, 1, 3), share(2, 1, 3), share(3, 1, 3)];
        assert_eq!(
            caps(10, &shares),
            Ok(vec![(site(1), 4), (site(2), 3), (site(3), 3)])
        );
        // The remainder goes to the lowest site id whatever the order of the shares.
        let shares = [share(3, 1, 3), share(2, 1, 3), share(1, 1, 3)];
        assert_eq!(
            caps(10, &shares),
            Ok(vec![(site(3), 3), (site(2), 3), (site(1), 4)])
        );
        // A part that comes to 0 gives no row.
        let shares = [share(1, 9, 10), share(2, 1, 10)];
        assert_eq!(caps(5, &shares), Ok(vec![(site(1), 5)]));
        let sum: u64 = caps(
            1_000_003,
            &[share(1, 7, 20), share(2, 5, 20), share(3, 8, 20)],
        )
        .expect("deals")
        .iter()
        .map(|row| row.1)
        .sum();
        assert_eq!(sum, 1_000_003);
        assert_eq!(caps(7, &[]), Ok(Vec::new()));
    }

    #[test]
    fn the_most_room_goes_first() {
        let stalls = [
            stall(1, "26163", 60),
            stall(2, "26163", 30),
            stall(3, "26163", 10),
        ];
        let buyers = [
            custom(10, "26163", 50),
            custom(11, "26163", 30),
            custom(12, "26163", 20),
        ];
        let map = deal_by_most_room(&buyers, &stalls, 3).expect("deals");
        assert_eq!(map[&account(10)], vec![share(1, 50, 50)]);
        assert_eq!(map[&account(11)], vec![share(2, 30, 30)]);
        assert_eq!(map[&account(12)], vec![share(1, 10, 20), share(3, 10, 20)]);
        // With one stall at most, the 20 takes all of A: 70 asked of a room of 60.
        let map = deal_by_most_room(&buyers, &stalls, 1).expect("deals");
        assert_eq!(map[&account(12)], vec![share(1, 20, 20)]);
        assert_eq!(
            deal_by_most_room(&buyers, &[stall(1, "26163", 0)], 3),
            Err(NationalOpeningError::Policy)
        );
        assert_eq!(deal_by_most_room(&buyers, &[], 3), Ok(BTreeMap::new()));
    }

    fn actor_at(id: u8, location: EconomicLocation, employed: u64) -> (SiteId, ActorContext) {
        use babylon_kernel::currency::Currency;
        (
            site(id),
            ActorContext {
                site_id: site(id),
                function: EconomicFunction::BusinessServices,
                source_ownership: None,
                location,
                employed,
                employee_persons: employed,
                force: employed,
                wage: Currency::from_micro_units(1),
                price_scale_bps: 10_000,
                planned_batches: 1,
                process_id: None,
            },
        )
    }

    fn providers_abroad(rows: &[(u8, ForeignCounterpart, u64)]) -> ProviderLocations {
        let actors: BTreeMap<_, _> = rows
            .iter()
            .map(|&(id, region, employed)| {
                actor_at(id, EconomicLocation::Foreign(region), employed)
            })
            .collect();
        let mut sites = BTreeMap::<EconomicLocation, Vec<SiteId>>::new();
        for &(id, region, _) in rows {
            sites
                .entry(EconomicLocation::Foreign(region))
                .or_default()
                .push(site(id));
        }
        ProviderLocations::new(sites, &actors)
    }

    fn buyer_id(first: u32) -> SiteId {
        let mut bytes = [0_u8; 32];
        bytes[..4].copy_from_slice(&first.to_be_bytes());
        SiteId::from_bytes(bytes)
    }

    #[test]
    fn the_provider_abroad_reads_no_number() {
        let (a, b, c) = (
            EconomicLocation::Foreign(ForeignCounterpart::Canada),
            EconomicLocation::Foreign(ForeignCounterpart::Mexico),
            EconomicLocation::Foreign(ForeignCounterpart::China),
        );
        let regions = [a, b, c];
        assert_eq!(crossing_region(&regions, buyer_id(4)), Some(b));
        assert_eq!(crossing_region(&regions, buyer_id(5)), Some(c));
        assert_eq!(crossing_region(&[], buyer_id(5)), None);
        let rows = [
            (1, ForeignCounterpart::Canada, 5),
            (2, ForeignCounterpart::Mexico, 7),
            (3, ForeignCounterpart::Mexico, 9),
            (4, ForeignCounterpart::China, 1),
        ];
        let wayne = county("26163");
        let providers = providers_abroad(&rows);
        // A location with two providers gives the one with more at work (3 over 2 in Mexico).
        for (buyer, provider) in [(3, 1), (4, 3), (5, 4)] {
            assert_eq!(
                provider_abroad(&providers, buyer_id(buyer), wayne),
                Ok(Some(site(provider)))
            );
        }
        // The same whatever the order the providers were given in.
        let mut turned = rows;
        turned.reverse();
        assert_eq!(
            provider_abroad(&providers_abroad(&turned), buyer_id(4), wayne),
            Ok(Some(site(3)))
        );
        // A buyer outside the counties has none; neither does a country without a provider abroad.
        assert_eq!(provider_abroad(&providers, buyer_id(4), a), Ok(None));
        let none = ProviderLocations::new(BTreeMap::new(), &BTreeMap::new());
        assert_eq!(provider_abroad(&none, buyer_id(4), wayne), Ok(None));
        // `crossing_region` is the first location the rotation of a county buyer's candidates gives.
        assert_eq!(providers.regions(), &regions[..]);
        for first in 0..7 {
            let buyer = buyer_id(first);
            let rotated = providers
                .secondary_candidates(wayne, buyer)
                .expect("rotates")
                .next();
            assert_eq!(crossing_region(providers.regions(), buyer), rotated);
        }
    }
}
