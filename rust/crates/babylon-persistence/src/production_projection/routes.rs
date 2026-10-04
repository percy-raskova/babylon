//! Supplier relations are distinct even when they share a physical route.
use super::{
    history::{Delivery, OrderHistory},
    metadata::{Metadata, RelationKey},
    outbound, ProductionProjectionError,
};
use crate::{
    michigan_economy::digest_hex,
    production_observation::{
        PhysicalRouteDefinition, ProductionRoute, ProductionRouteStage, ProductionRouteTransport,
    },
};
use babylon_kernel::content_digest::sha256_of;
use babylon_material_circuit::{MaterialCircuitState, RouteId, SupplierRoute, SupplierTransport};
use std::collections::BTreeMap;
type Result<T> = std::result::Result<T, ProductionProjectionError>;

pub(super) fn relation_id(key: RelationKey) -> String {
    let mut bytes = b"babylon.production-supplier-relation.v1\0".to_vec();
    for id in [
        key.0.as_bytes(),
        key.1.as_bytes(),
        key.2.as_bytes(),
        key.3.as_bytes(),
    ] {
        bytes.extend_from_slice(&id);
    }
    digest_hex(&sha256_of(&bytes))
}
fn key(row: &SupplierRoute) -> RelationKey {
    (
        row.buyer_site_id,
        row.supplier_site_id,
        row.good_id,
        row.unit_id,
    )
}

pub(super) fn project(
    metadata: &Metadata<'_>,
    state: &MaterialCircuitState,
    history: &OrderHistory,
) -> Result<(Vec<ProductionRoute>, Vec<PhysicalRouteDefinition>)> {
    let stages = stage_index(state)?;
    let totals = relation_totals(history)?;
    let mut result = Vec::with_capacity(state.supplier_routes.len());
    let mut definitions = BTreeMap::<RouteId, PhysicalRouteDefinition>::new();
    for relation in &state.supplier_routes {
        if metadata.routes.get(&key(relation)).copied() != Some(relation) {
            return Err(ProductionProjectionError::Content);
        }
        let good = metadata.good(relation.good_id, relation.unit_id)?;
        if let std::collections::btree_map::Entry::Vacant(entry) =
            definitions.entry(relation.route_id)
        {
            let route_stages = stages.get(&relation.route_id).cloned().unwrap_or_default();
            let travel_periods = route_stages
                .iter()
                .try_fold(0_u64, |n, r| n.checked_add(r.travel_periods))
                .ok_or(ProductionProjectionError::Arithmetic)?;
            let transport_kind = match relation.transport_kind {
                SupplierTransport::Local if route_stages.is_empty() => {
                    ProductionRouteTransport::Local
                }
                SupplierTransport::Staged if !route_stages.is_empty() => {
                    ProductionRouteTransport::Staged
                }
                _ => return Err(ProductionProjectionError::State),
            };
            let (physical_edge_ids, distance_mm) = geometry(metadata, relation.route_id);
            entry.insert(PhysicalRouteDefinition {
                id: digest_hex(&relation.route_id.as_bytes()),
                travel_periods,
                stages: route_stages,
                transport_kind,
                physical_edge_ids,
                distance_mm,
            });
        }
        let physical = definitions
            .get(&relation.route_id)
            .ok_or(ProductionProjectionError::State)?;
        if !matches!(
            (relation.transport_kind, physical.transport_kind),
            (SupplierTransport::Local, ProductionRouteTransport::Local)
                | (SupplierTransport::Staged, ProductionRouteTransport::Staged)
        ) {
            return Err(ProductionProjectionError::State);
        }
        let total = totals
            .get(&(relation.route_id, key(relation)))
            .copied()
            .unwrap_or([0; 5]);
        result.push(ProductionRoute {
            id: relation_id(key(relation)),
            physical_route_id: digest_hex(&relation.route_id.as_bytes()),
            supplier_site_id: digest_hex(&relation.supplier_site_id.as_bytes()),
            buyer_site_id: digest_hex(&relation.buyer_site_id.as_bytes()),
            good_id: digest_hex(&relation.good_id.as_bytes()),
            unit_id: digest_hex(&relation.unit_id.as_bytes()),
            good: good.label.clone(),
            unit: good.unit_label.clone(),
            grams_per_unit: outbound::mass(state, relation.good_id, relation.unit_id)?,
            ordered: total[0],
            shipped: total[1],
            delivered: total[2],
            lost: total[3],
            realized: total[4],
            backlog: total[0]
                .checked_sub(total[1])
                .ok_or(ProductionProjectionError::State)?,
        });
    }
    if result.len() != metadata.routes.len() {
        return Err(ProductionProjectionError::Content);
    }
    Ok((result, definitions.into_values().collect()))
}

fn relation_totals(history: &OrderHistory) -> Result<BTreeMap<(RouteId, RelationKey), [u64; 5]>> {
    let mut totals = BTreeMap::<_, [u64; 5]>::new();
    for row in history
        .deliveries
        .values()
        .chain(history.retired_deliveries.values())
    {
        let Delivery {
            route,
            supplier,
            buyer,
            good,
            unit,
            ordered,
            shipped,
            delivered,
            lost,
            realized,
        } = row;
        let total = totals
            .entry((*route, (*buyer, *supplier, *good, *unit)))
            .or_default();
        for (sum, n) in total
            .iter_mut()
            .zip([*ordered, *shipped, *delivered, *lost, *realized])
        {
            *sum = sum
                .checked_add(n)
                .ok_or(ProductionProjectionError::Arithmetic)?;
        }
    }
    Ok(totals)
}
fn geometry(metadata: &Metadata<'_>, route: RouteId) -> (Vec<String>, Option<u64>) {
    use crate::michigan_material::MichiganMaterialPath;
    metadata
        .michigan()
        .and_then(|catalog| catalog.routes().iter().find(|r| r.id() == route))
        .map_or_else(
            || (Vec::new(), None),
            |row| match &row.path {
                MichiganMaterialPath::Local => (Vec::new(), None),
                MichiganMaterialPath::Routed {
                    physical_edge_keys,
                    distance_mm,
                    ..
                } => (physical_edge_keys.clone(), *distance_mm),
            },
        )
}
pub(super) fn stage_index(
    state: &MaterialCircuitState,
) -> Result<BTreeMap<RouteId, Vec<ProductionRouteStage>>> {
    let mut memberships = BTreeMap::<_, Vec<String>>::new();
    for row in &state.route_stage_capacities {
        memberships
            .entry((row.route_id, row.stage_index))
            .or_default()
            .push(digest_hex(&row.corridor_id.as_bytes()));
    }
    let mut result = BTreeMap::<_, Vec<ProductionRouteStage>>::new();
    for row in &state.route_stages {
        let mut ids = memberships
            .remove(&(row.route_id, row.stage_index))
            .ok_or(ProductionProjectionError::State)?;
        ids.sort_unstable();
        if ids.is_empty() || ids.windows(2).any(|r| r[0] == r[1]) || row.travel_periods == 0 {
            return Err(ProductionProjectionError::State);
        }
        result
            .entry(row.route_id)
            .or_default()
            .push(ProductionRouteStage {
                stage_index: row.stage_index,
                travel_periods: u64::from(row.travel_periods),
                capacity_ids: ids,
            });
    }
    for rows in result.values_mut() {
        rows.sort_unstable_by_key(|r| r.stage_index);
        if rows
            .iter()
            .enumerate()
            .any(|(i, r)| usize::from(r.stage_index) != i)
        {
            return Err(ProductionProjectionError::State);
        }
    }
    if !memberships.is_empty() {
        return Err(ProductionProjectionError::State);
    }
    Ok(result)
}
