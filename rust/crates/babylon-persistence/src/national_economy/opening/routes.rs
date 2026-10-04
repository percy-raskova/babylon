//! Source-compatible directed paths, finite shared pools and coarse game journeys.
use super::{Builder, NationalOpeningError, Result};
use crate::national_transport::{CargoClass, NationalTransportReference};
use babylon_kernel::{content_digest::sha256_of, economic_location::EconomicLocation};
use babylon_material_circuit::{
    CorridorId, RouteId, RouteStage, RouteStageCapacity, SharedCapacitySupply, SupplierRoute,
    SupplierTransport,
};
use std::collections::{BTreeMap, BTreeSet, VecDeque};

struct PathTree {
    distance: Vec<u16>,
    next_link: Vec<Option<usize>>,
}

/// Initialization-only shortest compatible paths. No route or source is invented.
pub(super) struct Network<'a> {
    source: &'a NationalTransportReference,
    nodes: BTreeMap<&'a str, usize>,
    locations: BTreeMap<EconomicLocation, usize>,
    incoming: Vec<Vec<usize>>,
    trees: BTreeMap<(EconomicLocation, CargoClass), PathTree>,
}
impl<'a> Network<'a> {
    pub(super) fn new(source: &'a NationalTransportReference) -> Result<Self> {
        let nodes: BTreeMap<_, _> = source
            .nodes()
            .iter()
            .enumerate()
            .map(|(i, n)| (n.id(), i))
            .collect();
        let mut incoming = vec![vec![]; nodes.len()];
        for (i, link) in source.links().iter().enumerate() {
            let (_, to) = link.endpoints();
            let index = *nodes.get(to).ok_or(NationalOpeningError::Route)?;
            incoming[index].push(i);
        }
        let mut locations = BTreeMap::new();
        for node in source.nodes() {
            if matches!(
                node.kind(),
                crate::national_transport::TransportNodeKind::County
                    | crate::national_transport::TransportNodeKind::Foreign
                    | crate::national_transport::TransportNodeKind::Dependency
            ) {
                locations.insert(node.location(), nodes[node.id()]);
            }
        }
        Ok(Self {
            source,
            nodes,
            locations,
            incoming,
            trees: BTreeMap::new(),
        })
    }
    fn ensure_tree(&mut self, buyer: EconomicLocation, cargo: CargoClass) -> Result<()> {
        if !self.trees.contains_key(&(buyer, cargo)) {
            let destination = *self
                .locations
                .get(&buyer)
                .ok_or(NationalOpeningError::Route)?;
            let mut tree = PathTree {
                distance: vec![u16::MAX; self.nodes.len()],
                next_link: vec![None; self.nodes.len()],
            };
            tree.distance[destination] = 0;
            let mut queue = VecDeque::from([destination]);
            while let Some(to) = queue.pop_front() {
                for &edge in &self.incoming[to] {
                    let link = &self.source.links()[edge];
                    if !link.cargo().contains(&cargo) {
                        continue;
                    }
                    let from = self.nodes[link.endpoints().0];
                    if tree.distance[from] != u16::MAX {
                        continue;
                    }
                    tree.distance[from] = tree.distance[to]
                        .checked_add(1)
                        .ok_or(NationalOpeningError::Bounds)?;
                    tree.next_link[from] = Some(edge);
                    queue.push_back(from);
                }
            }
            self.trees.insert((buyer, cargo), tree);
        }
        Ok(())
    }
    pub(super) fn nearest(
        &mut self,
        buyer: EconomicLocation,
        cargo: CargoClass,
        candidates: impl Iterator<Item = EconomicLocation>,
    ) -> Result<Option<EconomicLocation>> {
        self.ensure_tree(buyer, cargo)?;
        let tree = self
            .trees
            .get(&(buyer, cargo))
            .ok_or(NationalOpeningError::Route)?;
        let mut best = None;
        for candidate in candidates {
            let index = *self
                .locations
                .get(&candidate)
                .ok_or(NationalOpeningError::Route)?;
            let distance = tree.distance[index];
            if distance != u16::MAX && best.is_none_or(|old| (distance, candidate) < old) {
                best = Some((distance, candidate));
            }
        }
        Ok(best.map(|(_, location)| location))
    }
    pub(super) fn path(
        &mut self,
        supplier: EconomicLocation,
        buyer: EconomicLocation,
        cargo: CargoClass,
    ) -> Result<Option<Vec<usize>>> {
        let mut from = *self
            .locations
            .get(&supplier)
            .ok_or(NationalOpeningError::Route)?;
        let destination = *self
            .locations
            .get(&buyer)
            .ok_or(NationalOpeningError::Route)?;
        self.ensure_tree(buyer, cargo)?;
        let tree = self
            .trees
            .get(&(buyer, cargo))
            .ok_or(NationalOpeningError::Route)?;
        if tree.distance[from] == u16::MAX {
            return Ok(None);
        }
        let next_link = &tree.next_link;
        let mut path = vec![];
        while from != destination {
            let edge = next_link[from].ok_or(NationalOpeningError::Route)?;
            path.push(edge);
            from = self.nodes[self.source.links()[edge].endpoints().1];
            if path.len() > self.nodes.len() {
                return Err(NationalOpeningError::Route);
            }
        }
        Ok(Some(path))
    }
}

pub(super) fn route_id(from: EconomicLocation, to: EconomicLocation, cargo: CargoClass) -> RouteId {
    let mut bytes = b"NationalSupplierRouteV1\0".to_vec();
    bytes.extend_from_slice(&from.canonical_bytes());
    bytes.extend_from_slice(&to.canonical_bytes());
    bytes.push(match cargo {
        CargoClass::General => 1,
        CargoClass::DryBulk => 2,
        CargoClass::CrudeOil => 3,
        CargoClass::RefinedLiquid => 4,
    });
    RouteId::from_bytes(sha256_of(&bytes))
}
fn corridor(key: &str) -> CorridorId {
    let mut bytes = b"NationalFreightPoolV1\0".to_vec();
    bytes.extend_from_slice(key.as_bytes());
    CorridorId::from_bytes(sha256_of(&bytes))
}

pub(super) fn finish(builder: &mut Builder<'_>) -> Result<()> {
    let mut network = Network::new(builder.transport)?;
    let mut routes = BTreeSet::new();
    let capacities = capacities(builder)?;
    add_replenishment_routes(builder)?;
    add_route_stages(builder, &mut network, &mut routes)?;
    let remote = builder
        .aid
        .mandates
        .iter()
        .find(|m| {
            matches!(
                m.transport,
                babylon_material_circuit::AidTransport::Routed { .. }
            )
        })
        .cloned()
        .ok_or(NationalOpeningError::Identity)?;
    if let babylon_material_circuit::AidTransport::Routed { route_id: id, .. } = remote.transport {
        if routes.insert(id) {
            let from = builder.aid.children[0].location;
            let to = builder.aid.children[2].location;
            add_stage(builder, &mut network, from, to, CargoClass::General, id)?;
        }
    }
    // Current capacity is defined only for principals used by a route or merchant.
    let used: BTreeSet<_> = builder
        .opening
        .logistics
        .memberships
        .iter()
        .map(|r| r.corridor_id)
        .chain(
            builder
                .opening
                .sites
                .iter()
                .filter_map(|s| s.merchant.as_ref().map(|m| m.capacity_id)),
        )
        .collect();
    builder.opening.logistics.shared_capacity = used
        .into_iter()
        .map(|id| {
            Ok(SharedCapacitySupply {
                corridor_id: id,
                grams_per_period: *capacities.get(&id).ok_or(NationalOpeningError::Route)?,
            })
        })
        .collect::<Result<Vec<_>>>()?;
    builder.opening.logistics.supplier_routes.sort_unstable();
    builder.opening.logistics.route_stages.sort_unstable();
    builder.opening.logistics.memberships.sort_unstable();
    Ok(())
}

fn capacities(builder: &Builder<'_>) -> Result<BTreeMap<CorridorId, u64>> {
    let mut capacities: BTreeMap<_, _> = builder
        .transport
        .pools()
        .iter()
        .map(|pool| (corridor(&pool.id), pool.capacity_grams))
        .collect();
    for site in &builder.opening.sites {
        if let Some(merchant) = &site.merchant {
            let actor = builder
                .actors
                .get(&site.site_id)
                .ok_or(NationalOpeningError::Identity)?;
            let hours = super::quantity(actor.force, builder.policy.work_hours_per_person)?;
            let grams = merchant.handling.iter().try_fold(0_u64, |largest, row| {
                let good = builder
                    .policy
                    .commodities
                    .values()
                    .find(|g| g.good_id == row.good_id && g.unit_id == row.unit_id)
                    .ok_or(NationalOpeningError::Policy)?;
                let babylon_material_circuit::CommodityKind::Storable { grams_per_unit } =
                    good.kind
                else {
                    return Err(NationalOpeningError::Policy);
                };
                Ok(largest.max(super::quantity(hours / row.hours_per_unit, grams_per_unit)?))
            })?;
            // A zero-workforce merchant remains unable to handle goods.
            capacities.insert(merchant.capacity_id, grams);
        }
    }

    Ok(capacities)
}

fn add_stage(
    builder: &mut Builder<'_>,
    network: &mut Network<'_>,
    from: EconomicLocation,
    to: EconomicLocation,
    cargo: CargoClass,
    id: RouteId,
) -> Result<()> {
    let path = network
        .path(from, to, cargo)?
        .ok_or(NationalOpeningError::Route)?;
    let mut periods = 0_u16;
    let mut loss = 0_u32;
    let mut pools = BTreeSet::new();
    for index in path {
        let link = &builder.transport.links()[index];
        let profile = builder
            .transport
            .services()
            .get(link.profile())
            .ok_or(NationalOpeningError::Route)?;
        periods = periods.max(profile.travel_periods);
        loss = loss.max(profile.loss_ppm);
        pools.extend(link.pools().iter().map(|p| corridor(p)));
    }
    if periods == 0 || pools.is_empty() {
        return Err(NationalOpeningError::Route);
    }
    let from_node = *builder
        .logistics_nodes
        .get(&from)
        .ok_or(NationalOpeningError::Route)?;
    let to_node = *builder
        .logistics_nodes
        .get(&to)
        .ok_or(NationalOpeningError::Route)?;
    builder.opening.logistics.route_stages.push(RouteStage {
        route_id: id,
        stage_index: 0,
        from_node_id: from_node,
        to_node_id: to_node,
        travel_periods: periods,
        loss_ppm: loss,
    });
    for pool in pools {
        builder
            .opening
            .logistics
            .memberships
            .push(RouteStageCapacity {
                route_id: id,
                stage_index: 0,
                corridor_id: pool,
            });
    }
    Ok(())
}

fn add_replenishment_routes(builder: &mut Builder<'_>) -> Result<()> {
    for row in builder.opening.policies.replenishment.clone() {
        let from = builder
            .actors
            .get(&row.supplier_site_id)
            .ok_or(NationalOpeningError::Identity)?
            .location;
        let to = builder
            .actors
            .get(&row.buyer_site_id)
            .ok_or(NationalOpeningError::Identity)?
            .location;
        let good = builder
            .policy
            .commodities
            .values()
            .find(|g| g.good_id == row.good_id && g.unit_id == row.unit_id)
            .ok_or(NationalOpeningError::Policy)?;
        let cargo = good.cargo.ok_or(NationalOpeningError::Policy)?;
        let id = route_id(from, to, cargo);
        builder
            .opening
            .logistics
            .supplier_routes
            .push(SupplierRoute {
                buyer_site_id: row.buyer_site_id,
                supplier_site_id: row.supplier_site_id,
                good_id: row.good_id,
                unit_id: row.unit_id,
                route_id: id,
                transport_kind: if from == to {
                    SupplierTransport::Local
                } else {
                    SupplierTransport::Staged
                },
            });
    }
    Ok(())
}

fn add_route_stages(
    builder: &mut Builder<'_>,
    network: &mut Network<'_>,
    routes: &mut BTreeSet<RouteId>,
) -> Result<()> {
    for row in builder.opening.logistics.supplier_routes.clone() {
        let from = builder
            .actors
            .get(&row.supplier_site_id)
            .ok_or(NationalOpeningError::Identity)?
            .location;
        let to = builder
            .actors
            .get(&row.buyer_site_id)
            .ok_or(NationalOpeningError::Identity)?
            .location;
        let cargo = builder
            .policy
            .commodities
            .values()
            .find(|g| g.good_id == row.good_id && g.unit_id == row.unit_id)
            .and_then(|g| g.cargo)
            .ok_or(NationalOpeningError::Policy)?;
        let id = route_id(from, to, cargo);
        if id != row.route_id {
            return Err(NationalOpeningError::Identity);
        }
        if from == to || !routes.insert(id) {
            continue;
        }
        add_stage(builder, network, from, to, cargo, id)?;
    }
    Ok(())
}
