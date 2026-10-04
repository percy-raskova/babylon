//! Readings of authenticated shared freight capacity, separate from material arrivals.

use std::collections::{BTreeMap, BTreeSet};
use std::fmt::Write as _;

use babylon_persistence::{
    production_observation::ProductionFreightCapacityAccount,
    production_observation::ProductionFreightReservation,
    production_observation::ProductionRoute,
    production_observation::ProductionSite,
    production_observation::ProductionSnapshot,
    production_observation::{PhysicalRouteError, ProductionAidCapacityOrder},
    ProductionHouseholdAccount,
};

/// Capacity mass is displayed in kilograms without rounding away gram residuals.
pub(crate) fn format_freight_mass(grams: u64) -> String {
    let whole = grams / 1_000;
    let fraction = grams % 1_000;
    if fraction == 0 {
        format!("{whole} kg")
    } else {
        let fraction = format!("{fraction:03}");
        format!("{whole}.{} kg", fraction.trim_end_matches('0'))
    }
}

fn participating_routes<'a>(
    account: &ProductionFreightCapacityAccount,
    snapshot: &'a ProductionSnapshot,
    definitions: &babylon_persistence::production_observation::PhysicalRouteIndex<'a>,
) -> Vec<&'a ProductionRoute> {
    let disclosed: BTreeSet<_> = snapshot.sites.iter().map(|site| site.id.as_str()).collect();
    let physical: BTreeSet<_> = account.route_ids.iter().map(String::as_str).collect();
    let mut routes: Vec<_> = snapshot
        .routes
        .iter()
        .filter(|route| {
            physical.contains(route.physical_route_id.as_str())
                && definitions.get(route).is_some_and(|physical| {
                    physical
                        .stages
                        .iter()
                        .any(|leg| leg.capacity_ids.contains(&account.corridor_id))
                })
                && disclosed.contains(route.supplier_site_id.as_str())
                && disclosed.contains(route.buyer_site_id.as_str())
        })
        .collect();
    routes.sort_by(|a, b| a.id.cmp(&b.id));
    routes
}

fn capacity_routes<'a>(
    snapshot: &'a ProductionSnapshot,
    definitions: &babylon_persistence::production_observation::PhysicalRouteIndex<'a>,
) -> BTreeMap<&'a str, Vec<&'a ProductionRoute>> {
    let disclosed: BTreeSet<_> = snapshot.sites.iter().map(|site| site.id.as_str()).collect();
    let mut result = BTreeMap::<_, Vec<_>>::new();
    for route in &snapshot.routes {
        if !disclosed.contains(route.supplier_site_id.as_str())
            || !disclosed.contains(route.buyer_site_id.as_str())
        {
            continue;
        }
        let Some(physical) = definitions.get(route) else {
            continue;
        };
        let capacities: BTreeSet<_> = physical
            .stages
            .iter()
            .flat_map(|stage| stage.capacity_ids.iter().map(String::as_str))
            .collect();
        for capacity in capacities {
            result.entry(capacity).or_default().push(route);
        }
    }
    result
}

/// A shared principal is shown once, independent of how many routes use it.
/// Both endpoints must belong to this observation before a route is named.
pub(crate) fn shared_accounts<'a>(
    snapshot: &'a ProductionSnapshot,
    selected_site: Option<&str>,
) -> Result<Vec<&'a ProductionFreightCapacityAccount>, PhysicalRouteError> {
    let definitions =
        babylon_persistence::production_observation::PhysicalRouteIndex::try_new(snapshot)?;
    Ok(shared_accounts_with_index(
        snapshot,
        selected_site,
        &definitions,
    ))
}

pub(crate) fn shared_accounts_with_index<'a>(
    snapshot: &'a ProductionSnapshot,
    selected_site: Option<&str>,
    definitions: &babylon_persistence::production_observation::PhysicalRouteIndex<'a>,
) -> Vec<&'a ProductionFreightCapacityAccount> {
    let routes = capacity_routes(snapshot, definitions);
    let mut accounts: Vec<_> = snapshot
        .freight_capacity_accounts
        .iter()
        .filter(|account| {
            if account.kind
                != babylon_persistence::production_observation::ProductionCapacityKind::Transport
            {
                return false;
            }
            let participants = routes
                .get(account.corridor_id.as_str())
                .map_or(&[][..], Vec::as_slice);
            let physical: BTreeSet<_> = account.route_ids.iter().map(String::as_str).collect();
            let mut count = 0;
            let mut selected = selected_site.is_none();
            for route in participants
                .iter()
                .filter(|r| physical.contains(r.physical_route_id.as_str()))
            {
                count += 1;
                selected |= selected_site
                    .is_some_and(|id| route.supplier_site_id == id || route.buyer_site_id == id);
            }
            let support = account
                .completed
                .iter()
                .flat_map(|done| &done.reservations)
                .flat_map(|r| &r.support_orders)
                .filter_map(|order| support_participants(account, order, snapshot));
            let mut aid = false;
            for (donor, recipient) in support {
                aid = true;
                selected |= selected_site.is_some_and(|id| {
                    donor.retailer_site_id == id || recipient.retailer_site_id == id
                });
            }
            (count > 1 || aid) && selected
        })
        .collect();
    accounts.sort_by(|a, b| {
        (a.next_opening_available_grams, &a.corridor_id)
            .cmp(&(b.next_opening_available_grams, &b.corridor_id))
    });
    accounts
}

fn support_participants<'a>(
    account: &ProductionFreightCapacityAccount,
    order: &ProductionAidCapacityOrder,
    snapshot: &'a ProductionSnapshot,
) -> Option<(
    &'a ProductionHouseholdAccount,
    &'a ProductionHouseholdAccount,
)> {
    if !account.route_ids.contains(&order.route_id) {
        return None;
    }
    let find = |id: &str| {
        snapshot.household_accounts.iter().find(|row| {
            row.demand_principal_id == id
                && row.good_id == order.good_id
                && row.unit_id == order.unit_id
        })
    };
    Some((
        find(&order.donor_principal_id)?,
        find(&order.recipient_principal_id)?,
    ))
}
fn describe_support(
    output: &mut String,
    account: &ProductionFreightCapacityAccount,
    reservation: &ProductionFreightReservation,
    snapshot: &ProductionSnapshot,
) {
    if reservation.support_orders.len() > 6 {
        writeln!(
            output,
            "{} household aid accounts; showing six.",
            reservation.support_orders.len()
        )
        .expect("String write");
    }
    for order in reservation.support_orders.iter().take(6) {
        let Some((donor, recipient)) = support_participants(account, order, snapshot) else {
            output.push_str("Household support detail unavailable in this observation.\n");
            continue;
        };
        writeln!(output,"HOUSEHOLD AID / {} -> {} / {}\nDispatched {} {} · reserved {}\nHouseholds can use this support after arrival.",
            donor.location,recipient.location,donor.good,order.dispatched,donor.unit,format_freight_mass(order.reserved_grams)).expect("String write");
    }
}
fn compare_support(
    output: &mut String,
    left: &ProductionFreightReservation,
    right: &ProductionFreightReservation,
    current: &ProductionSnapshot,
    compared: &ProductionSnapshot,
    a: &ProductionFreightCapacityAccount,
    b: &ProductionFreightCapacityAccount,
) {
    let ids: BTreeSet<_> = left
        .support_orders
        .iter()
        .chain(&right.support_orders)
        .map(|r| r.mandate_id.as_str())
        .collect();
    for id in ids.into_iter().take(6) {
        let (Some(l), Some(r)) = (
            left.support_orders.iter().find(|r| r.mandate_id == id),
            right.support_orders.iter().find(|r| r.mandate_id == id),
        ) else {
            output.push_str("Comparable household support unavailable.\n");
            continue;
        };
        let (Some((donor, recipient)), Some(_)) = (
            support_participants(a, l, current),
            support_participants(b, r, compared),
        ) else {
            output.push_str("Comparable household support unavailable.\n");
            continue;
        };
        if (
            l.donor_principal_id.as_str(),
            l.recipient_principal_id.as_str(),
            l.route_id.as_str(),
            l.good_id.as_str(),
            l.unit_id.as_str(),
        ) != (
            r.donor_principal_id.as_str(),
            r.recipient_principal_id.as_str(),
            r.route_id.as_str(),
            r.good_id.as_str(),
            r.unit_id.as_str(),
        ) {
            output.push_str("Comparable household support unavailable.\n");
            continue;
        }
        writeln!(
            output,
            "HOUSEHOLD AID / {} -> {} / {}",
            donor.location, recipient.location, donor.good
        )
        .expect("String write");
        pair(
            output,
            "Support dispatched",
            l.dispatched,
            r.dispatched,
            &donor.unit,
        );
        capacity_pair(
            output,
            "Support reserved",
            l.reserved_grams,
            r.reserved_grams,
        );
    }
}

fn route_label(route: &ProductionRoute, snapshot: &ProductionSnapshot) -> String {
    let name = |id: &str| {
        snapshot
            .sites
            .iter()
            .find(|site| site.id == id)
            .map(|site| site.name.as_str())
    };
    match (name(&route.supplier_site_id), name(&route.buyer_site_id)) {
        (Some(supplier), Some(buyer)) => format!(
            "{} -> {} / {}",
            supplier.trim_end_matches(" cohort"),
            buyer.trim_end_matches(" cohort"),
            route.good
        ),
        _ => "Route endpoints unavailable in this observation".into(),
    }
}

/// The relationship rail keeps the capacity principal visible; full route
/// accounts live in the Freight reading.
pub(crate) fn account_brief(account: &ProductionFreightCapacityAccount) -> String {
    let mut output = format!("{}\n", account.corridor_label);
    if let Some(completed) = &account.completed {
        for reservation in &completed.reservations {
            writeln!(
                output,
                "Reservation period {}\n{} opening · {} reserved · {} remaining",
                reservation.reservation_period,
                format_freight_mass(reservation.opening_available_grams),
                format_freight_mass(reservation.newly_reserved_grams),
                format_freight_mass(reservation.remaining_available_grams)
            )
            .expect("String write");
        }
        if completed.reservations.is_empty() {
            output.push_str("No new reservations this period.\n");
        }
    } else {
        output.push_str("Foundation; no completed reservations.\n");
    }
    writeln!(
        output,
        "Period {} opening: {}\nCapacity reservations; arrivals are separate.",
        account.next_opening_period,
        format_freight_mass(account.next_opening_available_grams)
    )
    .expect("String write");
    output
}

#[cfg(test)]
fn account_reading(
    account: &ProductionFreightCapacityAccount,
    snapshot: &ProductionSnapshot,
) -> String {
    let Ok(definitions) =
        babylon_persistence::production_observation::PhysicalRouteIndex::try_new(snapshot)
    else {
        return "Physical route details unavailable in this observation.\n".into();
    };
    let Ok(orders) =
        babylon_persistence::production_observation::FreightOrderIndex::try_new(snapshot)
    else {
        return "Freight order details unavailable in this observation.\n".into();
    };
    account_reading_with_index(account, snapshot, &definitions, &orders)
}

pub(crate) fn account_reading_with_index<'a>(
    account: &ProductionFreightCapacityAccount,
    snapshot: &'a ProductionSnapshot,
    definitions: &babylon_persistence::production_observation::PhysicalRouteIndex<'a>,
    orders: &babylon_persistence::production_observation::FreightOrderIndex<'a>,
) -> String {
    let mut output = format!("{}\n", account.corridor_label);
    let routes = participating_routes(account, snapshot, definitions);
    if let Some(completed) = &account.completed {
        writeln!(output, "COMMITTED DISPATCH / PERIOD {}", completed.period).expect("String write");
        for reservation in &completed.reservations {
            writeln!(
                output,
                "Reservation period {} / 28 days\nOpening {}\nNewly reserved {}\nRemaining {}\n",
                reservation.reservation_period,
                format_freight_mass(reservation.opening_available_grams),
                format_freight_mass(reservation.newly_reserved_grams),
                format_freight_mass(reservation.remaining_available_grams),
            )
            .expect("String write");
            if reservation.orders.len() > 6 {
                writeln!(output, "{} order accounts; showing six. Other participants are available in the circuit rail.", reservation.orders.len()).expect("String write");
            }
            for reference in reservation.orders.iter().take(6) {
                let Some(order) = orders.get(reference) else {
                    return "Freight order details unavailable in this observation.\n".into();
                };
                let Some(route) = routes.iter().find(|route| {
                    Some(route.id.as_str()) == order.supplier_relation_id.as_deref()
                        && Some(route.physical_route_id.as_str()) == order.route_id.as_deref()
                        && route.supplier_site_id == order.supplier_site_id
                        && route.good_id == order.good_id
                        && route.unit_id == order.unit_id
                }) else {
                    output.push_str("Reservation route detail unavailable in this observation.\n");
                    continue;
                };
                writeln!(
                    output,
                    "{}\nRequested {} {} | dispatched {} {}\nUnshipped {} {}\n",
                    route_label(route, snapshot),
                    order.requested,
                    route.unit,
                    order.dispatched,
                    route.unit,
                    order.remaining_unshipped,
                    route.unit,
                )
                .expect("String write");
            }
            describe_support(&mut output, account, reservation, snapshot);
        }
        if completed.reservations.is_empty() {
            output.push_str("No new capacity reservations in this completed period.\n");
        }
    } else {
        output.push_str("No completed freight reservations at foundation.\n");
    }
    // Keep membership visible even when a route has no new request this period.
    let named: BTreeSet<_> = account
        .completed
        .iter()
        .flat_map(|completed| &completed.reservations)
        .flat_map(|reservation| &reservation.orders)
        .filter_map(|reference| orders.get(reference))
        .filter_map(|order| order.supplier_relation_id.as_deref())
        .collect();
    for route in routes
        .iter()
        .filter(|route| !named.contains(route.id.as_str()))
        .take(6)
    {
        writeln!(output, "Participant: {}\n", route_label(route, snapshot)).expect("String write");
    }
    writeln!(output, "Next opening (period {}): {} available\nReservations use capacity; goods arrive after travel. Follow arrivals in Flow and staffing in Work.",
        account.next_opening_period, format_freight_mass(account.next_opening_available_grams),
    ).expect("String write");
    output
}

/// Competition links are separate from the supplier/buyer relation graph.
pub(crate) fn competitor_sites<'a>(
    site_id: &str,
    snapshot: &'a ProductionSnapshot,
) -> Result<Vec<&'a ProductionSite>, PhysicalRouteError> {
    let route_ids: BTreeSet<_> = shared_accounts(snapshot, Some(site_id))?
        .into_iter()
        .flat_map(|account| &account.route_ids)
        .collect();
    let disclosed: BTreeSet<_> = snapshot.sites.iter().map(|site| site.id.as_str()).collect();
    let ids: BTreeSet<_> = snapshot
        .routes
        .iter()
        .filter(|route| {
            route_ids.contains(&route.physical_route_id)
                && disclosed.contains(route.supplier_site_id.as_str())
                && disclosed.contains(route.buyer_site_id.as_str())
        })
        .filter(|route| route.supplier_site_id != site_id && route.buyer_site_id != site_id)
        .flat_map(|route| [&route.supplier_site_id, &route.buyer_site_id])
        .collect();
    let sites: BTreeMap<_, _> = snapshot
        .sites
        .iter()
        .map(|site| (site.id.as_str(), site))
        .collect();
    Ok(ids
        .into_iter()
        .filter_map(|id| sites.get(id.as_str()).copied())
        .collect())
}

fn grouped_orders<'a>(
    reservation: &ProductionFreightReservation,
    routes: &[&'a ProductionRoute],
    orders: &babylon_persistence::production_observation::FreightOrderIndex<'_>,
) -> (BTreeMap<&'a str, [u64; 3]>, bool) {
    let routes: BTreeMap<_, _> = routes.iter().map(|r| (r.id.as_str(), *r)).collect();
    let mut result = BTreeMap::<_, [u64; 3]>::new();
    let mut invalid = false;
    for reference in &reservation.orders {
        let Some(order) = orders.get(reference) else {
            invalid = true;
            continue;
        };
        let Some(route) = order
            .supplier_relation_id
            .as_deref()
            .and_then(|id| routes.get(id))
            .filter(|route| {
                Some(route.physical_route_id.as_str()) == order.route_id.as_deref()
                    && route.supplier_site_id == order.supplier_site_id
                    && route.good_id == order.good_id
                    && route.unit_id == order.unit_id
            })
        else {
            invalid = true;
            continue;
        };
        let total = result.entry(route.id.as_str()).or_default();
        for (sum, n) in
            total
                .iter_mut()
                .zip([order.requested, order.dispatched, order.remaining_unshipped])
        {
            let Some(next) = sum.checked_add(n) else {
                return (BTreeMap::new(), true);
            };
            *sum = next;
        }
    }
    (result, invalid)
}

fn pair(output: &mut String, label: &str, current: u64, compared: u64, unit: &str) {
    writeln!(output, "{label}: {current} / {compared} {unit}").expect("String write");
}

fn capacity_pair(output: &mut String, label: &str, current: u64, compared: u64) {
    writeln!(
        output,
        "{label}: {} / {}",
        format_freight_mass(current),
        format_freight_mass(compared)
    )
    .expect("String write");
}

fn compare_orders(
    output: &mut String,
    r_a: &ProductionFreightReservation,
    r_b: &ProductionFreightReservation,
    current: &ProductionSnapshot,
    (current_routes, current_orders): (
        &[&ProductionRoute],
        &babylon_persistence::production_observation::FreightOrderIndex<'_>,
    ),
    (compared_routes, compared_orders): (
        &[&ProductionRoute],
        &babylon_persistence::production_observation::FreightOrderIndex<'_>,
    ),
) {
    let (left, bad_left) = grouped_orders(r_a, current_routes, current_orders);
    let (right, bad_right) = grouped_orders(r_b, compared_routes, compared_orders);
    if bad_left || bad_right {
        output.push_str("Comparable route endpoints unavailable.\n");
    }
    let keys: BTreeSet<_> = left.keys().chain(right.keys()).copied().collect();
    for key in keys.into_iter().take(6) {
        let (Some(route), Some(other)) = (
            current_routes.iter().find(|r| r.id == key),
            compared_routes.iter().find(|r| r.id == key),
        ) else {
            output.push_str("Comparable route endpoints unavailable.\n");
            continue;
        };
        if (
            route.supplier_site_id.as_str(),
            route.buyer_site_id.as_str(),
            route.good_id.as_str(),
            route.unit_id.as_str(),
        ) != (
            other.supplier_site_id.as_str(),
            other.buyer_site_id.as_str(),
            other.good_id.as_str(),
            other.unit_id.as_str(),
        ) {
            output.push_str("Comparable route endpoints unavailable.\n");
            continue;
        }
        let left = left.get(key).copied().unwrap_or([0; 3]);
        let right = right.get(key).copied().unwrap_or([0; 3]);
        writeln!(output, "{}", route_label(route, current)).expect("String write");
        for ((label, a), b) in ["Requested", "Dispatched", "Remaining unshipped"]
            .into_iter()
            .zip(left)
            .zip(right)
        {
            pair(output, label, a, b, &route.unit);
        }
        pair(
            output,
            "Arrived to date",
            route.delivered,
            other.delivered,
            &route.unit,
        );
    }
}

fn compare_reservation_capacity(
    output: &mut String,
    r_a: &ProductionFreightReservation,
    r_b: &ProductionFreightReservation,
) {
    for (label, current_value, compared_value) in [
        (
            "Opening capacity",
            r_a.opening_available_grams,
            r_b.opening_available_grams,
        ),
        (
            "Newly reserved",
            r_a.newly_reserved_grams,
            r_b.newly_reserved_grams,
        ),
        (
            "Remaining capacity",
            r_a.remaining_available_grams,
            r_b.remaining_available_grams,
        ),
    ] {
        capacity_pair(output, label, current_value, compared_value);
    }
}

fn compare_next_capacity(
    output: &mut String,
    current: &ProductionFreightCapacityAccount,
    compared: &ProductionFreightCapacityAccount,
) {
    if current.next_opening_period == compared.next_opening_period {
        capacity_pair(
            output,
            &format!(
                "Next opening capacity (period {})",
                current.next_opening_period
            ),
            current.next_opening_available_grams,
            compared.next_opening_available_grams,
        );
    } else {
        output.push_str("Next opening capacity periods do not match.\n");
    }
}

fn capacity_changed(
    period: u64,
    current: &ProductionFreightCapacityAccount,
    compared: &ProductionFreightCapacityAccount,
) -> bool {
    if current.next_opening_period == compared.next_opening_period
        && current.next_opening_available_grams != compared.next_opening_available_grams
    {
        return true;
    }
    let (Some(a), Some(b)) = (&current.completed, &compared.completed) else {
        return false;
    };
    period > 0
        && a.period == period
        && b.period == period
        && a.reservations.iter().any(|left| {
            b.reservations.iter().any(|right| {
                left.reservation_period == right.reservation_period
                    && (left.opening_available_grams != right.opening_available_grams
                        || left.support_orders.iter().collect::<BTreeSet<_>>()
                            != right.support_orders.iter().collect::<BTreeSet<_>>())
            })
        })
}

fn comparison_keys<'a>(
    period: u64,
    left: &[&'a ProductionFreightCapacityAccount],
    right: &[&'a ProductionFreightCapacityAccount],
) -> Vec<&'a str> {
    let left: BTreeMap<_, _> = left.iter().map(|a| (a.corridor_id.as_str(), *a)).collect();
    let right: BTreeMap<_, _> = right.iter().map(|a| (a.corridor_id.as_str(), *a)).collect();
    let mut keys: Vec<_> = left
        .keys()
        .chain(right.keys())
        .copied()
        .collect::<BTreeSet<_>>()
        .into_iter()
        .collect();
    keys.sort_by_key(|key| {
        let changed = left
            .get(key)
            .zip(right.get(key))
            .is_some_and(|(a, b)| capacity_changed(period, a, b));
        (!changed, *key)
    });
    keys
}

pub(crate) fn comparison_reading(
    period: u64,
    current: &ProductionSnapshot,
    compared: &ProductionSnapshot,
    selected_site: Option<&str>,
) -> String {
    let (Ok(current_definitions), Ok(compared_definitions)) = (
        babylon_persistence::production_observation::PhysicalRouteIndex::try_new(current),
        babylon_persistence::production_observation::PhysicalRouteIndex::try_new(compared),
    ) else {
        return "Physical route comparison unavailable in this observation.\n".into();
    };
    let (Ok(current_orders), Ok(compared_orders)) = (
        babylon_persistence::production_observation::FreightOrderIndex::try_new(current),
        babylon_persistence::production_observation::FreightOrderIndex::try_new(compared),
    ) else {
        return "Freight order comparison unavailable in this observation.\n".into();
    };
    let left = shared_accounts_with_index(current, selected_site, &current_definitions);
    let right = shared_accounts_with_index(compared, selected_site, &compared_definitions);
    let keys = comparison_keys(period, &left, &right);
    let mut output = String::new();
    if keys.len() > 6 {
        output.push_str("Six shared capacity pools shown, with capacity changes first.\n");
    }
    for corridor_id in keys.into_iter().take(6) {
        let find = |accounts: &[&ProductionFreightCapacityAccount]| {
            accounts
                .iter()
                .position(|account| account.corridor_id == corridor_id)
        };
        let (Some(a), Some(b)) = (find(&left), find(&right)) else {
            output.push_str("Shared freight comparison unavailable: this capacity pool is not disclosed in both campaigns.\n\n");
            continue;
        };
        let (a, b) = (left[a], right[b]);
        writeln!(
            output,
            "{}\nCounts read current / compared; capacity reservations are separate from arrivals.",
            a.corridor_label
        )
        .expect("String write");
        compare_next_capacity(&mut output, a, b);
        let (Some(done_a), Some(done_b)) = (&a.completed, &b.completed) else {
            if period == 0 && a.completed.is_none() && b.completed.is_none() {
                output.push_str("No completed freight reservations at foundation.\n\n");
            } else {
                output.push_str("Freight receipt unavailable for the selected period.\n\n");
            }
            continue;
        };
        if period == 0 || done_a.period != period || done_b.period != period {
            output.push_str("Freight receipt does not match the selected period.\n\n");
            continue;
        }
        let reservations: BTreeSet<_> = done_a
            .reservations
            .iter()
            .chain(&done_b.reservations)
            .map(|reservation| reservation.reservation_period)
            .collect();
        if reservations.is_empty() {
            output.push_str("No new capacity reservations in this completed period.\n");
        }
        let current_routes = participating_routes(a, current, &current_definitions);
        let compared_routes = participating_routes(b, compared, &compared_definitions);
        for reservation_period in reservations {
            writeln!(output, "Reservation period {reservation_period} / 28 days")
                .expect("String write");
            let (Some(r_a), Some(r_b)) = (
                done_a
                    .reservations
                    .iter()
                    .find(|row| row.reservation_period == reservation_period),
                done_b
                    .reservations
                    .iter()
                    .find(|row| row.reservation_period == reservation_period),
            ) else {
                output.push_str("Comparable reservation account unavailable.\n");
                continue;
            };
            compare_reservation_capacity(&mut output, r_a, r_b);
            compare_orders(
                &mut output,
                r_a,
                r_b,
                current,
                (&current_routes, &current_orders),
                (&compared_routes, &compared_orders),
            );
            compare_support(&mut output, r_a, r_b, current, compared, a, b);
        }
        output.push('\n');
    }
    output
}

#[cfg(test)]
pub(crate) mod tests {
    use super::*;
    use babylon_persistence::{
        production_observation::CompletedProductionFreightCapacity,
        production_observation::ProductionFreightCapacityAccount,
        production_observation::ProductionFreightCapacityOrder,
        production_observation::ProductionFreightReservation,
        production_observation::ProductionRoute, production_observation::ProductionRouteStage,
        production_observation::ProductionSite, production_observation::ProductionSnapshot,
    };

    fn rekey(snapshot: &mut ProductionSnapshot) {
        for definition in &mut snapshot.freight_order_definitions {
            let prior = definition.id.clone();
            definition.id = babylon_persistence::production_observation::freight_order_identity(
                &definition.order,
            )
            .unwrap();
            for account in &mut snapshot.freight_capacity_accounts {
                if let Some(completed) = &mut account.completed {
                    for reservation in &mut completed.reservations {
                        for reference in &mut reservation.orders {
                            if *reference == prior {
                                *reference = definition.id.clone();
                            }
                        }
                    }
                }
            }
        }
    }

    pub(crate) fn fixture() -> ProductionSnapshot {
        let mut freight_order_definitions = Vec::new();
        let capacity = capacity_fixture(&mut freight_order_definitions);
        let sites = ["steel", "panels", "mill", "meals"]
            .into_iter()
            .map(|id| ProductionSite {
                function: "manufacturing".into(),
                id: id.into(),
                location: "county:26163".parse().unwrap(),
                name: id.into(),
                industry_code: Some("331".into()),
                observed_employment: None,
                inventory: Vec::new(),
                roles: vec![
                    babylon_persistence::production_observation::ProductionSiteRole::Production,
                ],
                sector_code: Some("31-33".into()),
                processes: vec![
                    babylon_persistence::production_observation::ProductionProcess {
                        id: "fixture-process".into(),
                        name: "Fixture process".into(),
                        output_good_id: id.into(),
                        output_unit_id: "kg".into(),
                        output_good: id.into(),
                        output_unit: "kg".into(),
                        output_per_batch: 1,
                        available_batches: 1,
                        planned_batches: Some(1),
                        produced_batches: Some(1),
                        inputs: Vec::new(),
                        labor: Vec::new(),
                    },
                ],
            })
            .collect();
        let routes = [
            ("sheets", "steel", "panels", 600, 120),
            ("meal", "mill", "meals", 200, 40),
        ]
        .into_iter()
        .map(|(id, supplier, buyer, ordered, shipped)| ProductionRoute {
            physical_route_id: id.into(),
            grams_per_unit: 1000,
            id: id.into(),
            supplier_site_id: supplier.into(),
            buyer_site_id: buyer.into(),
            good_id: id.into(),
            unit_id: "kg".into(),
            good: id.into(),
            unit: "kg".into(),
            ordered,
            shipped,
            delivered: 0,
            lost: 0,
            realized: 0,
            backlog: ordered - shipped,
        })
        .collect();
        ProductionSnapshot {
            physical_routes: ["sheets", "meal"].into_iter().map(|id| babylon_persistence::production_observation::PhysicalRouteDefinition {
                id: id.into(), physical_edge_ids: Vec::new(), distance_mm: None,
                transport_kind: babylon_persistence::production_observation::ProductionRouteTransport::Staged,
                travel_periods: 1, stages: vec![ProductionRouteStage {
                    stage_index: 0, capacity_ids: vec!["pool".into()], travel_periods: 1,
                }],
            }).collect(),

            household_accounts: Vec::new(),
            household_service_accounts: Vec::new(),
            goods_price_accounts: Vec::new(),
            maintenance_account: None,
            content_authority_sha256: "a".repeat(64),
            road_source: None,
            physical_edges: Vec::new(),
            merchant_handling_accounts: Vec::new(),
            final_demand_accounts: Vec::new(),
            scenario_label: "Shared freight — constrained".into(),
            duration: babylon_kernel::clock::CampaignDuration::Finite { final_period: 16 },
            sites,
            routes,
            freight: Vec::new(),
            events: Vec::new(),
            provenance: Vec::new(),
            material_balance: None,
            labor_accounts: Vec::new(),
            staffing_accounts: Vec::new(),
            observed_contexts: Vec::new(),
            national_observed_contexts: Vec::new(),
            process_attributions: Vec::new(),
            freight_capacity_accounts: vec![capacity],
            freight_order_definitions,
        }
    }

    fn capacity_fixture(
        definitions: &mut Vec<
            babylon_persistence::production_observation::ProductionFreightOrderDefinition,
        >,
    ) -> ProductionFreightCapacityAccount {
        ProductionFreightCapacityAccount {
            corridor_id: "pool".into(),
            corridor_label: "Designed regional freight pool".into(),
            kind: babylon_persistence::production_observation::ProductionCapacityKind::Transport,
            merchant_site_ids: Vec::new(),
            route_ids: vec!["sheets".into(), "meal".into()],
            next_opening_period: 2,
            next_opening_available_grams: 160_000,
            completed: Some(CompletedProductionFreightCapacity {
                period: 1,
                reservations: vec![ProductionFreightReservation {
                    support_orders: Vec::new(),
                    reservation_period: 1,
                    opening_available_grams: 160_000,
                    newly_reserved_grams: 160_000,
                    remaining_available_grams: 0,
                    orders: [("sheets", 600, 120), ("meal", 200, 40)]
                        .into_iter()
                        .map(
                            |(id, requested, dispatched)| { let order = ProductionFreightCapacityOrder {
                                supplier_relation_id: Some(id.into()),
                                order_id: format!("order-{id}"),
                                route_id: Some(id.into()),
                                kind: babylon_persistence::production_observation::ProductionOutboundKind::Delivery,
                                supplier_site_id: if id == "sheets" {
                                    "steel".into()
                                } else {
                                    "mill".into()
                                },
                                grams_per_unit: 1000,
                                requested_grams: u128::from(requested) * 1000,
                                reserved_grams: dispatched * 1000,
                                good_id: id.into(),
                                unit_id: "kg".into(),
                                requested,
                                dispatched,
                                remaining_unshipped: requested - dispatched,
                            };
                            let id = babylon_persistence::production_observation::freight_order_identity(&order).unwrap();
                            definitions.push(babylon_persistence::production_observation::ProductionFreightOrderDefinition { id: id.clone(), order }); id },
                        )
                        .collect(),
                }],
            }),
        }
    }

    pub(crate) fn aid_fixture() -> ProductionSnapshot {
        let mut snapshot = fixture();
        snapshot.household_accounts = [
            ("donor", "county:26163", "panels"),
            ("recipient", "county:17031", "meals"),
        ]
        .into_iter()
        .map(|(id, location, retailer)| ProductionHouseholdAccount {
            kind: babylon_persistence::ProductionHouseholdKind::Ordinary,
            demand_principal_id: id.into(),
            location: location.parse().unwrap(),
            good_id: "food".into(),
            unit_id: "food-unit".into(),
            good: "food".into(),
            unit: "food units".into(),
            household_count: 4,
            person_count: 4,
            retailer_site_id: retailer.into(),
            stock_on_hand: 0,
            required_per_period: 4,
            completed: None,
        })
        .collect();
        let account = &mut snapshot.freight_capacity_accounts[0];
        account.route_ids.push("aid-route".into());
        let reservation = &mut account.completed.as_mut().unwrap().reservations[0];
        reservation.opening_available_grams = 188_000;
        reservation.newly_reserved_grams = 188_000;
        reservation.support_orders.push(ProductionAidCapacityOrder {
            commitment_id: "aid-commitment".into(),
            mandate_id: "aid-mandate".into(),
            donor_principal_id: "donor".into(),
            recipient_principal_id: "recipient".into(),
            route_id: "aid-route".into(),
            good_id: "food".into(),
            unit_id: "food-unit".into(),
            dispatched: 2,
            grams_per_unit: 14_000,
            reserved_grams: 28_000,
        });
        snapshot
    }
    #[test]
    fn household_aid_capacity_has_its_own_disclosed_parties_and_mass() {
        let mut snapshot = aid_fixture();
        snapshot.routes.retain(|r| r.id == "sheets");
        assert_eq!(shared_accounts(&snapshot, Some("meals")).unwrap().len(), 1);
        let text = account_reading(&snapshot.freight_capacity_accounts[0], &snapshot);
        assert!(text.contains("HOUSEHOLD AID / county:26163 -> county:17031 / food"));
        assert!(text.contains("Dispatched 2 food units · reserved 28 kg"));
        assert!(!text.contains("Requested 2"));
        let mut other = snapshot.clone();
        let row = &mut other.freight_capacity_accounts[0]
            .completed
            .as_mut()
            .unwrap()
            .reservations[0]
            .support_orders[0];
        row.dispatched = 1;
        row.reserved_grams = 14_000;
        other.freight_capacity_accounts[0]
            .completed
            .as_mut()
            .unwrap()
            .reservations[0]
            .newly_reserved_grams = 174_000;
        other.freight_capacity_accounts[0]
            .completed
            .as_mut()
            .unwrap()
            .reservations[0]
            .remaining_available_grams = 14_000;
        let comparison = comparison_reading(1, &snapshot, &other, Some("meals"));
        assert!(comparison.contains("Support dispatched: 2 / 1 food units"));
        assert!(comparison.contains("Support reserved: 28 kg / 14 kg"));
        snapshot
            .household_accounts
            .retain(|r| r.demand_principal_id != "recipient");
        assert!(shared_accounts(&snapshot, Some("meals"))
            .unwrap()
            .is_empty());
        let hidden = account_reading(&snapshot.freight_capacity_accounts[0], &snapshot);
        assert!(hidden.contains("Household support detail unavailable in this observation."));
        assert!(!hidden.contains("HOUSEHOLD AID"));
        assert!(!hidden.contains("Dispatched 2 food units"));
        assert!(!hidden.contains("aid-commitment"));
        assert!(!comparison_reading(1, &other, &snapshot, None).contains("Support dispatched:"));
    }

    #[test]
    fn capacity_briefs_preserve_every_gram_as_exact_kilograms() {
        let mut account = capacity_fixture(&mut Vec::new());
        account.completed = None;
        for (grams, expected) in [
            (0, "0 kg"),
            (1, "0.001 kg"),
            (10, "0.01 kg"),
            (100, "0.1 kg"),
            (1_001, "1.001 kg"),
            (1_010, "1.01 kg"),
            (1_100, "1.1 kg"),
            (160_000, "160 kg"),
            (800_000, "800 kg"),
            (u64::MAX, "18446744073709551.615 kg"),
        ] {
            account.next_opening_available_grams = grams;
            assert!(account_brief(&account).contains(&format!("Period 2 opening: {expected}")));
        }
    }

    #[test]
    fn capacity_readings_preserve_small_residuals_and_native_commodity_units() {
        let mut snapshot = fixture();
        snapshot.routes[0].unit_id = "panel".into();
        snapshot.routes[0].unit = "panels".into();
        let account = &mut snapshot.freight_capacity_accounts[0];
        account.next_opening_available_grams = 1;
        let reservation = &mut account.completed.as_mut().unwrap().reservations[0];
        reservation.newly_reserved_grams = 159_999;
        reservation.remaining_available_grams = 1;

        let brief = account_brief(account);
        assert!(brief.contains("160 kg opening · 159.999 kg reserved · 0.001 kg remaining"));
        snapshot.freight_order_definitions[0].order.unit_id = "panel".into();
        rekey(&mut snapshot);
        let text = account_reading(&snapshot.freight_capacity_accounts[0], &snapshot);
        assert!(text.contains("Newly reserved 159.999 kg\nRemaining 0.001 kg"));
        assert!(text.contains("Next opening (period 2): 0.001 kg available"));
        assert!(text.contains("Requested 600 panels | dispatched 120 panels"));
        let comparison = comparison_reading(1, &snapshot, &snapshot, None);
        assert!(comparison.contains("Next opening capacity (period 2): 0.001 kg / 0.001 kg"));
        assert!(comparison.contains("Remaining capacity: 0.001 kg / 0.001 kg"));
        assert!(comparison.contains("Dispatched: 120 / 120 panels"));
    }

    #[test]
    fn shared_pool_is_counted_once_and_names_both_competing_chains() {
        let snapshot = fixture();
        let accounts = shared_accounts(&snapshot, Some("panels")).unwrap();
        assert_eq!(accounts.len(), 1);
        let text = account_reading(accounts[0], &snapshot);
        assert_eq!(text.matches("Designed regional freight pool").count(), 1);
        assert_eq!(text.lines().next(), Some("Designed regional freight pool"));
        assert!(text.contains("Opening 160 kg\nNewly reserved 160 kg\nRemaining 0 kg"));
        assert_eq!(text.matches("steel -> panels / sheets").count(), 1);
        assert_eq!(text.matches("mill -> meals / meal").count(), 1);
        assert!(text.contains("Requested 600 kg | dispatched 120 kg\nUnshipped 480 kg"));
        assert!(text.contains("Requested 200 kg | dispatched 40 kg\nUnshipped 160 kg"));
        assert!(text.contains("Reservations use capacity; goods arrive after travel"));
    }

    #[test]
    fn unmatched_reservation_reports_unavailable_detail_without_disclosing_order_data() {
        let mut snapshot = fixture();
        let mut unavailable = snapshot.freight_order_definitions[0].order.clone();
        unavailable.order_id = "private-order".into();
        unavailable.route_id = Some("private-route".into());
        unavailable.requested = 987_654;
        unavailable.remaining_unshipped = unavailable.requested - unavailable.dispatched;
        unavailable.requested_grams =
            u128::from(unavailable.requested) * u128::from(unavailable.grams_per_unit);
        let id = babylon_persistence::production_observation::freight_order_identity(&unavailable)
            .unwrap();
        snapshot.freight_order_definitions.push(
            babylon_persistence::production_observation::ProductionFreightOrderDefinition {
                id: id.clone(),
                order: unavailable,
            },
        );
        snapshot.freight_capacity_accounts[0]
            .completed
            .as_mut()
            .unwrap()
            .reservations[0]
            .orders
            .push(id);
        let reading = account_reading(&snapshot.freight_capacity_accounts[0], &snapshot);
        assert!(reading.contains("Reservation route detail unavailable in this observation."));
        let comparison = comparison_reading(1, &snapshot, &snapshot, None);
        assert!(comparison.contains("Comparable route endpoints unavailable."));
        for text in [reading, comparison] {
            assert!(!text.contains("private-"));
            assert!(!text.contains("987654"));
            assert!(text.contains("steel -> panels / sheets"));
            assert!(text.contains("mill -> meals / meal"));
        }
    }

    #[test]
    fn foundation_and_completed_zero_have_different_capacity_readings() {
        let mut snapshot = fixture();
        snapshot.freight_capacity_accounts[0].completed = None;
        snapshot.freight_order_definitions.clear();
        snapshot.freight_capacity_accounts[0].next_opening_period = 1;
        let text = account_reading(&snapshot.freight_capacity_accounts[0], &snapshot);
        assert!(text.contains("No completed freight reservations at foundation"));
        assert!(text.contains("Participant: steel -> panels / sheets"));
        assert!(text.contains("Participant: mill -> meals / meal"));
        assert!(!text.contains("Newly reserved 0"));
        let mut snapshot = fixture();
        let reservation = &mut snapshot.freight_capacity_accounts[0]
            .completed
            .as_mut()
            .unwrap()
            .reservations[0];
        reservation.newly_reserved_grams = 0;
        reservation.remaining_available_grams = 160_000;
        for definition in &mut snapshot.freight_order_definitions {
            definition.order.dispatched = 0;
            definition.order.reserved_grams = 0;
            definition.order.remaining_unshipped = definition.order.requested;
        }
        rekey(&mut snapshot);
        let text = account_reading(&snapshot.freight_capacity_accounts[0], &snapshot);
        assert!(text.contains("Newly reserved 0 kg\nRemaining 160 kg"));
        assert!(!text.contains("at foundation"));
    }

    #[test]
    fn invalid_route_definitions_are_not_empty_shared_membership() {
        let mut snapshot = fixture();
        assert!(shared_accounts(&snapshot, Some("undisclosed"))
            .unwrap()
            .is_empty());
        assert!(competitor_sites("undisclosed", &snapshot)
            .unwrap()
            .is_empty());
        snapshot.physical_routes.clear();
        assert!(matches!(
            shared_accounts(&snapshot, Some("panels")),
            Err(PhysicalRouteError::Missing)
        ));
        assert!(matches!(
            competitor_sites("panels", &snapshot),
            Err(PhysicalRouteError::Missing)
        ));
    }

    #[test]
    fn competitor_navigation_exposes_disclosed_peers_without_supplier_edges() {
        let mut snapshot = fixture();
        let peers: Vec<_> = competitor_sites("panels", &snapshot)
            .unwrap()
            .into_iter()
            .map(|site| site.id.as_str())
            .collect();
        assert_eq!(peers, ["meals", "mill"]);
        assert_eq!(
            crate::production_brief::dependency_sites(&snapshot.sites[1], &snapshot).len(),
            1
        );
        snapshot.sites.retain(|site| site.id != "mill");
        assert!(competitor_sites("panels", &snapshot).unwrap().is_empty());
        assert!(shared_accounts(&snapshot, Some("panels"))
            .unwrap()
            .is_empty());
    }

    #[test]
    fn comparison_joins_capacity_and_order_identity_and_preserves_reservation_period() {
        let current = fixture();
        let mut other = fixture();
        other.freight_capacity_accounts[0].corridor_label = "Different display label".into();
        let completed = other.freight_capacity_accounts[0]
            .completed
            .as_mut()
            .unwrap();
        let reservation = &mut completed.reservations[0];
        reservation.opening_available_grams = 800_000;
        reservation.newly_reserved_grams = 400_000;
        reservation.remaining_available_grams = 400_000;

        reservation.orders.reverse();
        other.freight_order_definitions[0].order.dispatched = 320;
        other.freight_order_definitions[0].order.reserved_grams = 320_000;
        other.freight_order_definitions[0].order.remaining_unshipped = 280;
        other.freight_order_definitions[1].order.dispatched = 80;
        other.freight_order_definitions[1].order.reserved_grams = 80_000;
        other.freight_order_definitions[1].order.remaining_unshipped = 120;
        rekey(&mut other);
        let text = comparison_reading(1, &current, &other, None);
        assert_eq!(text.matches("Designed regional freight pool").count(), 1);
        assert!(text.contains("Reservation period 1"));
        assert!(text.contains("Opening capacity: 160 kg / 800 kg"));
        assert!(text.contains("Dispatched: 120 / 320 kg"));
        assert!(text.contains("Dispatched: 40 / 80 kg"));
        other.freight_capacity_accounts[0]
            .completed
            .as_mut()
            .unwrap()
            .period = 2;
        let text = comparison_reading(1, &current, &other, None);
        assert!(text.contains("Freight receipt does not match the selected period"));
        assert!(!text.contains("Dispatched:"));
    }

    #[test]
    fn bounded_comparison_keeps_changed_capacity_visible_among_many_road_pools() {
        for period in [0, 1] {
            let mut current = fixture();
            current.freight_capacity_accounts = (0..8)
                .map(|index| {
                    let mut account = capacity_fixture(&mut Vec::new());
                    account.corridor_id = format!("pool-{index}");
                    account.corridor_label = format!("Road pool {index}");
                    if period == 0 {
                        account.completed = None;
                        account.next_opening_period = 1;
                    }
                    account
                })
                .collect();
            if period == 0 {
                current.freight_order_definitions.clear();
            }
            for route in &mut current.physical_routes {
                route.stages[0].capacity_ids = current
                    .freight_capacity_accounts
                    .iter()
                    .map(|account| account.corridor_id.clone())
                    .collect();
            }
            let mut other = current.clone();
            let changed = &mut other.freight_capacity_accounts[7];
            if period == 0 {
                changed.next_opening_available_grams = 800_000;
            } else {
                let reservation = &mut changed.completed.as_mut().unwrap().reservations[0];
                reservation.opening_available_grams = 800_000;
                reservation.remaining_available_grams = 640_000;
            }
            let text = comparison_reading(period, &current, &other, Some("panels"));
            assert!(text.contains("Road pool 7\n"));
            assert!(text.contains("160 kg / 800 kg"));
            assert_eq!(text.matches("Counts read current / compared").count(), 6);
            current.freight_capacity_accounts.reverse();
            other.freight_capacity_accounts.reverse();
            other.routes.reverse();
            assert_eq!(
                text,
                comparison_reading(period, &current, &other, Some("panels"))
            );
        }
    }
    #[test]
    fn comparisons_group_relations_when_recurring_order_ids_differ() {
        let left = fixture();
        let mut right = left.clone();
        for definition in &mut right.freight_order_definitions {
            definition.order.order_id = format!("renewed-{}", definition.order.order_id);
        }
        rekey(&mut right);
        let text = comparison_reading(1, &left, &right, None);
        assert!(text.contains("Dispatched: 120 / 120 kg"));
        assert!(!text.contains("Comparable route order unavailable"));
    }
    #[test]
    fn missing_or_forged_shared_order_facts_refuse_reading_and_comparison() {
        let original = fixture();
        for missing in [true, false] {
            let mut changed = original.clone();
            if missing {
                changed.freight_order_definitions.remove(0);
            } else {
                changed.freight_order_definitions[0].order.requested = 987_654;
            }
            let text = account_reading(&changed.freight_capacity_accounts[0], &changed);
            assert_eq!(
                text,
                "Freight order details unavailable in this observation.\n"
            );
            assert_eq!(
                comparison_reading(1, &original, &changed, None),
                "Freight order comparison unavailable in this observation.\n"
            );
            assert!(!text.contains("987654"));
        }
    }
}
