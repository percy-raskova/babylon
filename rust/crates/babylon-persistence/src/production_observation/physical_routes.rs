//! Checked borrowed joins from supplier relationships to shared physical paths.
use super::{
    PhysicalRouteDefinition, ProductionRoute, ProductionRouteTransport, ProductionSnapshot,
};
use std::collections::{BTreeMap, BTreeSet};

/// A malformed physical definition or supplier reference cannot become a view.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum PhysicalRouteError {
    /// A source-derived collection or membership bound was exceeded.
    Bound,
    /// A definition identity occurs more than once, including conflicting data.
    Duplicate,
    /// A supplier relationship names an absent physical route.
    Missing,
    /// A stage sequence, membership or transport declaration is inconsistent.
    Invalid,
}

/// One validated per-view index; joins borrow definitions without expanding paths.
pub struct PhysicalRouteIndex<'a> {
    definitions: BTreeMap<&'a str, &'a PhysicalRouteDefinition>,
}
impl<'a> PhysicalRouteIndex<'a> {
    /// Validate every definition, including unused rows, and every supplier reference.
    ///
    /// # Errors
    /// Refuses bounds, duplicates, missing definitions and inconsistent route time.
    pub fn try_new(snapshot: &'a ProductionSnapshot) -> Result<Self, PhysicalRouteError> {
        if snapshot.physical_routes.len() > babylon_material_circuit::MAX_SUPPLIER_ROUTES
            || snapshot.routes.len() > babylon_material_circuit::MAX_SUPPLIER_ROUTES
        {
            return Err(PhysicalRouteError::Bound);
        }
        let mut definitions = BTreeMap::new();
        let mut memberships = 0_usize;
        for definition in &snapshot.physical_routes {
            if definition.stages.len() > babylon_material_circuit::MAX_ROUTE_STAGES_PER_ROUTE {
                return Err(PhysicalRouteError::Bound);
            }
            for stage in &definition.stages {
                memberships = memberships
                    .checked_add(stage.capacity_ids.len())
                    .ok_or(PhysicalRouteError::Bound)?;
                if memberships > babylon_material_circuit::MAX_ROUTE_CAPACITY_MEMBERSHIPS {
                    return Err(PhysicalRouteError::Bound);
                }
            }
            validate_definition(definition)?;
            if definitions
                .insert(definition.id.as_str(), definition)
                .is_some()
            {
                return Err(PhysicalRouteError::Duplicate);
            }
        }
        if memberships > babylon_material_circuit::MAX_ROUTE_CAPACITY_MEMBERSHIPS {
            return Err(PhysicalRouteError::Bound);
        }
        for relation in &snapshot.routes {
            if !definitions.contains_key(relation.physical_route_id.as_str()) {
                return Err(PhysicalRouteError::Missing);
            }
        }
        Ok(Self { definitions })
    }

    /// Borrow the exact definition referenced by this disclosed supplier relation.
    #[must_use]
    pub fn get(&self, relation: &ProductionRoute) -> Option<&'a PhysicalRouteDefinition> {
        self.definitions
            .get(relation.physical_route_id.as_str())
            .copied()
    }
}

fn validate_definition(route: &PhysicalRouteDefinition) -> Result<(), PhysicalRouteError> {
    if route.stages.len() > babylon_material_circuit::MAX_ROUTE_STAGES_PER_ROUTE
        || route.physical_edge_ids.len() > 1_114_112
    {
        return Err(PhysicalRouteError::Bound);
    }
    let mut indices = BTreeSet::new();
    let mut travel = 0_u64;
    for stage in &route.stages {
        if stage.travel_periods == 0
            || stage.capacity_ids.is_empty()
            || !indices.insert(stage.stage_index)
        {
            return Err(PhysicalRouteError::Invalid);
        }
        let capacities: BTreeSet<_> = stage.capacity_ids.iter().collect();
        if capacities.len() != stage.capacity_ids.len() {
            return Err(PhysicalRouteError::Duplicate);
        }
        travel = travel
            .checked_add(stage.travel_periods)
            .ok_or(PhysicalRouteError::Invalid)?;
    }
    if indices
        .iter()
        .enumerate()
        .any(|(index, value)| usize::from(*value) != index)
        || travel != route.travel_periods
    {
        return Err(PhysicalRouteError::Invalid);
    }
    match route.transport_kind {
        ProductionRouteTransport::Local if route.stages.is_empty() => Ok(()),
        ProductionRouteTransport::Staged if !route.stages.is_empty() => Ok(()),
        _ => Err(PhysicalRouteError::Invalid),
    }
}
