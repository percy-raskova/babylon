//! Read every disclosed account, then retain only one county's direct relations.
use super::{
    disclosed_snapshot, node_caption, node_position, site_sector, CountyAnchors, ExternalPeer,
    NetworkLink, NetworkLinkKind, NetworkNode, NetworkProjection, NetworkSector, NodeKey,
};
use crate::observer::ObserverSession;
use crate::observer_ui::ObserverFrame;
use babylon_kernel::economic_location::EconomicLocation;
use babylon_persistence::production_observation::{
    ProductionSite, ProductionSiteRole, ProductionSnapshot,
};
use bevy::prelude::default;
use std::collections::{BTreeMap, BTreeSet};

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
enum Endpoint<'a> {
    Site(&'a str),
    Demand(EconomicLocation),
}
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
enum Kind<'a> {
    Commodity(&'a str, &'a str),
    Maintenance,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
struct Link<'a> {
    from: Endpoint<'a>,
    to: Endpoint<'a>,
    kind: Kind<'a>,
}
impl Endpoint<'_> {
    fn key(self) -> NodeKey {
        match self {
            Self::Site(id) => NodeKey::Site(id.to_owned()),
            Self::Demand(location) => NodeKey::EndBuyers(match location {
                EconomicLocation::County(county) => county.geoid().to_string(),
                _ => location.to_string(),
            }),
        }
    }
    fn location(self, sites: &BTreeMap<&str, &ProductionSite>) -> Option<EconomicLocation> {
        match self {
            Self::Site(id) => sites.get(id).map(|site| site.location),
            Self::Demand(location) => Some(location),
        }
    }
    fn in_county(self, sites: &BTreeMap<&str, &ProductionSite>, selected: &str) -> bool {
        matches!(self.location(sites), Some(EconomicLocation::County(county)) if county.geoid().as_str() == selected)
    }
}

fn declarations(snapshot: &ProductionSnapshot) -> BTreeSet<Link<'_>> {
    let mut links: BTreeSet<_> = crate::material_relations::declared_material_relations(snapshot)
        .map(|r| Link {
            from: Endpoint::Site(r.supplier),
            to: Endpoint::Site(r.buyer),
            kind: Kind::Commodity(r.good_id, r.unit_id),
        })
        .collect();
    if let Some(account) = &snapshot.maintenance_account {
        links.insert(Link {
            from: Endpoint::Site(&account.provider_site_id),
            to: Endpoint::Site(&account.consumer_site_id),
            kind: Kind::Maintenance,
        });
    }
    for account in &snapshot.final_demand_accounts {
        for seller in &account.retailer_site_ids {
            links.insert(Link {
                from: Endpoint::Site(seller),
                to: Endpoint::Demand(account.location),
                kind: Kind::Commodity(&account.good_id, &account.unit_id),
            });
        }
    }
    for account in &snapshot.household_accounts {
        links.insert(Link {
            from: Endpoint::Site(&account.retailer_site_id),
            to: Endpoint::Demand(account.location),
            kind: Kind::Commodity(&account.good_id, &account.unit_id),
        });
    }
    for account in &snapshot.household_service_accounts {
        for provider in &account.provider_site_ids {
            links.insert(Link {
                from: Endpoint::Site(provider),
                to: Endpoint::Demand(account.location),
                kind: Kind::Commodity(&account.good_id, &account.unit_id),
            });
        }
    }
    links
}
fn sector_matches(
    endpoint: Endpoint<'_>,
    sites: &BTreeMap<&str, &ProductionSite>,
    filter: NetworkSector,
) -> bool {
    if filter == NetworkSector::All {
        return true;
    }
    let Endpoint::Site(id) = endpoint else {
        return filter == NetworkSector::EndBuyers;
    };
    let Some(site) = sites.get(id) else {
        return false;
    };
    match filter {
        NetworkSector::Production => site.roles.contains(&ProductionSiteRole::Production),
        NetworkSector::Retail => site.roles.contains(&ProductionSiteRole::Retail),
        NetworkSector::Wholesale => site.roles.contains(&ProductionSiteRole::Wholesale),
        NetworkSector::Maintenance => site.roles.contains(&ProductionSiteRole::Maintenance),
        _ => site_sector(site) == filter,
    }
}
fn admitted_link(
    link: Link<'_>,
    sites: &BTreeMap<&str, &ProductionSite>,
    selected: &str,
    sector: NetworkSector,
    good: Option<&crate::map_economy_lens::MaterialGoodKey>,
) -> bool {
    (link.from.in_county(sites, selected) || link.to.in_county(sites, selected))
        && (sector_matches(link.from, sites, sector) || sector_matches(link.to, sites, sector))
        && good.is_none_or(|g| matches!(link.kind, Kind::Commodity(id, unit) if g.good_id == id && g.unit_id == unit))
}

pub(super) fn project_network(
    frame: &ObserverFrame,
    session: &ObserverSession,
    anchors: &CountyAnchors,
    selected: Option<usize>,
    sector: NetworkSector,
    good: Option<&crate::map_economy_lens::MaterialGoodKey>,
) -> NetworkProjection {
    let Some(snapshot) = disclosed_snapshot(frame, session) else {
        return NetworkProjection::default();
    };
    let sites: BTreeMap<_, _> = snapshot.sites.iter().map(|s| (s.id.as_str(), s)).collect();
    let declarations = declarations(snapshot);
    if sites.len() != snapshot.sites.len()
        || declarations
            .iter()
            .any(|r| r.from.location(&sites).is_none() || r.to.location(&sites).is_none())
    {
        return NetworkProjection::default();
    }
    let mut result = NetworkProjection {
        available: true,
        total_cohorts: sites.len(),
        total_links: declarations.len(),
        ..default()
    };
    let Some(county) = anchors.selected(selected) else {
        return result;
    };
    result.selected_county = anchors.0.get(county).map(|a| a.name.clone());
    let links: Vec<_> = declarations
        .into_iter()
        .filter(|r| admitted_link(*r, &sites, county, sector, good))
        .collect();
    let mut endpoints: BTreeSet<_> = links.iter().flat_map(|r| [r.from, r.to]).collect();
    if good.is_none() {
        endpoints.extend(
            sites
                .values()
                .filter(|s| {
                    s.is_in_county(county) && sector_matches(Endpoint::Site(&s.id), &sites, sector)
                })
                .map(|s| Endpoint::Site(s.id.as_str())),
        );
    }
    result.links = links
        .iter()
        .map(|r| NetworkLink {
            from: r.from.key(),
            to: r.to.key(),
            kind: match r.kind {
                Kind::Commodity(good, unit) => NetworkLinkKind::Commodity {
                    good: good.to_owned(),
                    unit: unit.to_owned(),
                },
                Kind::Maintenance => NetworkLinkKind::Maintenance,
            },
        })
        .collect();
    add_nodes(snapshot, anchors, &sites, &endpoints, &links, &mut result);
    result
}

fn add_nodes(
    snapshot: &ProductionSnapshot,
    anchors: &CountyAnchors,
    sites: &BTreeMap<&str, &ProductionSite>,
    endpoints: &BTreeSet<Endpoint<'_>>,
    links: &[Link<'_>],
    result: &mut NetworkProjection,
) {
    let workforce: BTreeMap<_, _> = snapshot
        .staffing_accounts
        .iter()
        .map(|r| (r.site_id.as_str(), (r.employed, r.reserve)))
        .collect();
    let mut usage = BTreeMap::<Endpoint<'_>, Vec<Link<'_>>>::new();
    for &link in links {
        usage.entry(link.from).or_default().push(link);
        if link.from != link.to {
            usage.entry(link.to).or_default().push(link);
        }
    }
    let labels = commodity_labels(snapshot);
    let mut ranks = BTreeMap::<String, usize>::new();
    for &endpoint in endpoints {
        let (site_id, caption, sector) = match endpoint {
            Endpoint::Site(id) => {
                let site = sites[id];
                (
                    id,
                    node_caption(site, workforce.get(id).copied()),
                    site_sector(site),
                )
            }
            Endpoint::Demand(location) => {
                let Some(id) = usage.get(&endpoint).and_then(|rows| {
                    rows.iter().find_map(|row| {
                        if let Endpoint::Site(id) = row.from {
                            Some(id)
                        } else {
                            None
                        }
                    })
                }) else {
                    continue;
                };
                (id, format!("{location} · household demand\nPurchases and services; consumption is a separate account\nClick: trace provider · Circuit [P]: needs and fulfillment"), NetworkSector::EndBuyers)
            }
        };
        let location = endpoint.location(sites).expect("declarations were checked");
        let anchor = match location {
            EconomicLocation::County(county) => anchors.0.get(county.geoid().as_str()),
            _ => None,
        };
        let key = endpoint.key();
        if let Some(anchor) = anchor {
            let county = match location {
                EconomicLocation::County(county) => county.geoid().to_string(),
                _ => unreachable!(),
            };
            let rank = ranks.entry(county.clone()).or_default();
            result.nodes.insert(
                key.clone(),
                NetworkNode {
                    key,
                    site_id: site_id.to_owned(),
                    county,
                    sector,
                    position: node_position(anchor.position, *rank),
                    caption,
                },
            );
            *rank += 1;
        } else {
            let incident = usage.get(&endpoint).map_or(&[][..], Vec::as_slice);
            let relations = incident
                .iter()
                .map(|link| peer_relation(endpoint, *link, sites, &labels))
                .collect::<Vec<_>>()
                .join("\n");
            result.external.insert(
                key,
                ExternalPeer {
                    site_id: site_id.to_owned(),
                    caption: format!(
                        "{location}\n{caption}\n{relations}\n{} direct disclosed links · open circuit", incident.len()
                    ),
                },
            );
        }
    }
}

type CommodityLabels<'a> = BTreeMap<(&'a str, &'a str), (&'a str, &'a str)>;

fn commodity_labels(snapshot: &ProductionSnapshot) -> CommodityLabels<'_> {
    let mut labels: CommodityLabels<'_> =
        crate::material_relations::declared_material_relations(snapshot)
            .map(|row| ((row.good_id, row.unit_id), (row.good, row.unit)))
            .collect();
    for account in &snapshot.final_demand_accounts {
        labels.insert(
            (&account.good_id, &account.unit_id),
            (&account.good, &account.unit),
        );
    }
    for account in &snapshot.household_accounts {
        labels.insert(
            (&account.good_id, &account.unit_id),
            (&account.good, &account.unit),
        );
    }
    for account in &snapshot.household_service_accounts {
        labels.insert(
            (&account.good_id, &account.unit_id),
            (&account.good, &account.unit),
        );
    }
    labels
}

fn peer_relation(
    peer: Endpoint<'_>,
    link: Link<'_>,
    sites: &BTreeMap<&str, &ProductionSite>,
    labels: &CommodityLabels<'_>,
) -> String {
    let supplies = link.from == peer;
    let counterpart = if supplies { link.to } else { link.from };
    let name = match counterpart {
        Endpoint::Site(id) => sites[id].name.clone(),
        Endpoint::Demand(location) => format!("households at {location}"),
    };
    match link.kind {
        Kind::Commodity(good_id, unit_id) => {
            let (good, unit) = labels[&(good_id, unit_id)];
            let direction = if supplies { "Supplies" } else { "Buys from" };
            format!("{direction} {name}: {good} / {unit}")
        }
        Kind::Maintenance if supplies => format!("Maintains {name}"),
        Kind::Maintenance => format!("Maintenance from {name}"),
    }
}
