//! Immutable authored definitions shared by every period of one campaign.
//!
//! The catalog is canonicalized, validated and hashed once. Every period borrows
//! it; no definition is cloned into [`crate::MaterialCircuitState`].

use std::collections::BTreeSet;

use babylon_kernel::content_digest;

use crate::GoodId;
use crate::LogisticsNodeId;
use crate::RouteId;
use crate::SiteId;
use crate::UnitId;
use crate::{
    AidMandate, CapacitySupply, CommodityDefinition, CommodityKind, HouseholdNeed,
    HouseholdTimePolicy, InputOutputCoefficient, LaborCoefficient, MaintenanceBinding,
    MaterialCircuitError, MerchantHandling, MerchantHandlingCoefficient, ProcessOutput,
    ProductiveEquipment, RollingProcessSupply, RouteStage, ServiceInputPolicy, SiteLogisticsNode,
    SupplierRoute, SupplierTransport, MAX_HOUSEHOLD_NEEDS, MAX_INPUT_COEFFICIENTS,
    MAX_MATERIAL_CIRCUIT_ROWS, MAX_SUPPLIER_ROUTES,
};
use std::collections::BTreeMap;

/// Mutable authored input for admission as a campaign catalog.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MaterialCatalogDefinition {
    pub capacity_policy: CapacitySupply,
    pub site_logistics_nodes: Vec<SiteLogisticsNode>,
    pub process_outputs: Vec<ProcessOutput>,
    pub input_coefficients: Vec<InputOutputCoefficient>,
    pub labor_coefficients: Vec<LaborCoefficient>,
    pub commodities: Vec<CommodityDefinition>,
    pub supplier_routes: Vec<SupplierRoute>,
    pub route_stages: Vec<RouteStage>,
    pub merchants: Vec<MerchantHandling>,
    pub handling_coefficients: Vec<MerchantHandlingCoefficient>,
    pub maintenance_binding: Option<MaintenanceBinding>,
    pub aid_mandates: Vec<AidMandate>,
    pub household_time_policy: Vec<HouseholdTimePolicy>,
    pub service_inputs: Vec<ServiceInputPolicy>,
    pub household_needs: Vec<HouseholdNeed>,
}

/// Validated campaign definitions and their immutable identity.
///
/// An admitted catalog cannot be mutated while retaining its old identity:
///
/// ```compile_fail
/// use babylon_material_circuit::MaterialCatalog;
/// fn stale_identity(catalog: &mut MaterialCatalog) {
///     catalog.process_outputs[0].quantity_per_batch += 1;
/// }
/// ```
///
/// Changes require consuming it with [`MaterialCatalog::into_definition`] and
/// admitting the resulting definitions again with [`MaterialCatalog::try_new`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MaterialCatalog {
    definition: MaterialCatalogDefinition,
    catalog_digest: [u8; 32],
}

impl std::ops::Deref for MaterialCatalog {
    type Target = MaterialCatalogDefinition;
    fn deref(&self) -> &Self::Target {
        &self.definition
    }
}

impl MaterialCatalog {
    /// Canonicalize, validate and hash one authored definition set.
    ///
    /// # Errors
    /// Returns the first row-bound, duplicate, route, coefficient, or definition
    /// refusal without publishing a digest.
    pub fn try_new(
        mut definition: MaterialCatalogDefinition,
    ) -> Result<Self, MaterialCircuitError> {
        definition.canonicalize();
        definition.validate()?;
        let catalog_digest = digest(&definition)?;
        Ok(Self {
            definition,
            catalog_digest,
        })
    }

    /// Return the construction input, consuming the admitted catalog.
    #[must_use]
    pub fn into_definition(self) -> MaterialCatalogDefinition {
        self.definition
    }

    /// Digest of the canonical admitted definitions.
    #[must_use]
    pub const fn catalog_digest(&self) -> [u8; 32] {
        self.catalog_digest
    }
}

impl MaterialCatalogDefinition {
    /// Authored equipment definitions, when the rolling policy is equipment-owned.
    #[must_use]
    pub fn equipment_content(&self) -> Option<&ProductiveEquipment> {
        match &self.capacity_policy {
            CapacitySupply::Rolling(rows) => match &rows.processes {
                RollingProcessSupply::Equipment(content) => Some(content),
                RollingProcessSupply::CapturedNameplate(_) => None,
            },
            CapacitySupply::FiniteSchedule => None,
        }
    }

    /// Exact grams per native unit for one declared commodity.
    ///
    /// # Errors
    /// Refuses an undeclared commodity or unit.
    pub fn grams_per_unit(&self, good: GoodId, unit: UnitId) -> Result<u64, MaterialCircuitError> {
        let index = self
            .commodities
            .binary_search_by_key(&(good, unit), |row| (row.good_id, row.unit_id))
            .map_err(|_| MaterialCircuitError::MassInvariant)?;
        self.commodities[index].grams_per_unit()
    }

    pub(crate) fn validate(&self) -> Result<(), MaterialCircuitError> {
        let limits = [
            (self.site_logistics_nodes.len(), MAX_MATERIAL_CIRCUIT_ROWS),
            (self.process_outputs.len(), MAX_MATERIAL_CIRCUIT_ROWS),
            (self.input_coefficients.len(), MAX_INPUT_COEFFICIENTS),
            (self.labor_coefficients.len(), MAX_MATERIAL_CIRCUIT_ROWS),
            (self.commodities.len(), MAX_MATERIAL_CIRCUIT_ROWS),
            (self.supplier_routes.len(), MAX_SUPPLIER_ROUTES),
            (self.route_stages.len(), MAX_MATERIAL_CIRCUIT_ROWS),
            (self.merchants.len(), MAX_MATERIAL_CIRCUIT_ROWS),
            (self.handling_coefficients.len(), MAX_MATERIAL_CIRCUIT_ROWS),
            (self.aid_mandates.len(), MAX_MATERIAL_CIRCUIT_ROWS),
            (self.household_time_policy.len(), MAX_MATERIAL_CIRCUIT_ROWS),
            (self.service_inputs.len(), MAX_MATERIAL_CIRCUIT_ROWS),
            (self.household_needs.len(), MAX_HOUSEHOLD_NEEDS),
        ];
        if limits.iter().any(|(length, limit)| length > limit) {
            return Err(MaterialCircuitError::RowLimit);
        }
        if let CapacitySupply::Rolling(rows) = &self.capacity_policy {
            let process_rows = match &rows.processes {
                RollingProcessSupply::CapturedNameplate(rows) => rows.len(),
                RollingProcessSupply::Equipment(content) => content.bindings.len(),
            };
            if process_rows > MAX_MATERIAL_CIRCUIT_ROWS
                || rows.shared.len() > MAX_MATERIAL_CIRCUIT_ROWS
            {
                return Err(MaterialCircuitError::RowLimit);
            }
        }
        self.validate_unique()?;
        self.validate_routes()?;
        self.validate_processes()?;
        self.validate_definitions()
    }

    fn validate_unique(&self) -> Result<(), MaterialCircuitError> {
        let duplicate =
            crate::transition::has_duplicate(&self.site_logistics_nodes, |row| row.site_id)
                || crate::transition::has_duplicate(&self.process_outputs, |row| row.process_id)
                || crate::transition::has_duplicate(&self.input_coefficients, |row| {
                    (row.process_id, row.good_id, row.unit_id)
                })
                || crate::transition::has_duplicate(&self.labor_coefficients, |row| row.process_id)
                || crate::transition::has_duplicate(&self.commodities, |row| {
                    (row.good_id, row.unit_id)
                })
                || crate::transition::has_duplicate(&self.supplier_routes, |row| {
                    (
                        row.buyer_site_id,
                        row.supplier_site_id,
                        row.good_id,
                        row.unit_id,
                    )
                })
                || crate::transition::has_duplicate(&self.route_stages, |row| {
                    (row.route_id, row.stage_index)
                })
                || crate::transition::has_duplicate(&self.merchants, |row| row.site_id)
                || crate::transition::has_duplicate(&self.handling_coefficients, |row| {
                    (row.site_id, row.good_id, row.unit_id)
                })
                || crate::transition::has_duplicate(&self.aid_mandates, |row| row.id)
                || crate::transition::has_duplicate(&self.household_time_policy, |row| {
                    row.principal_id
                })
                || crate::transition::has_duplicate(&self.service_inputs, |row| {
                    (row.buyer_site_id, row.good_id, row.unit_id)
                })
                || crate::transition::has_duplicate(&self.household_needs, |row| {
                    (row.principal_id, row.good_id, row.unit_id)
                });
        if duplicate {
            return Err(MaterialCircuitError::DuplicateRow);
        }
        Ok(())
    }

    fn validate_routes(&self) -> Result<(), MaterialCircuitError> {
        let route_ids: BTreeSet<_> = self.route_stages.iter().map(|row| row.route_id).collect();
        for route in route_ids {
            crate::transition::validate_route_stages(self.route_stages(route))?;
        }
        let mut modes = BTreeMap::new();
        for supplier in &self.supplier_routes {
            if modes
                .insert(supplier.route_id, supplier.transport_kind)
                .is_some_and(|previous| previous != supplier.transport_kind)
            {
                return Err(MaterialCircuitError::RouteInvariant);
            }
            let stages = self.route_stages(supplier.route_id);
            match supplier.transport_kind {
                SupplierTransport::Local => {
                    if !stages.is_empty()
                        || supplier.supplier_site_id == supplier.buyer_site_id
                        || self.site_node(supplier.supplier_site_id).is_none()
                        || self.site_node(supplier.buyer_site_id).is_none()
                    {
                        return Err(MaterialCircuitError::RouteInvariant);
                    }
                }
                SupplierTransport::Staged => {
                    if stages.is_empty()
                        || self.site_node(supplier.supplier_site_id) != Some(stages[0].from_node_id)
                        || self.site_node(supplier.buyer_site_id)
                            != Some(stages[stages.len() - 1].to_node_id)
                    {
                        return Err(MaterialCircuitError::RouteInvariant);
                    }
                }
            }
            self.grams_per_unit(supplier.good_id, supplier.unit_id)?;
        }
        if self
            .commodities
            .iter()
            .any(|row| matches!(row.kind, CommodityKind::Storable { grams_per_unit: 0 }))
        {
            return Err(MaterialCircuitError::MassInvariant);
        }
        for row in &self.merchants {
            if self.site_node(row.site_id).is_none() {
                return Err(MaterialCircuitError::MerchantInvariant);
            }
        }
        Ok(())
    }

    fn validate_processes(&self) -> Result<(), MaterialCircuitError> {
        let process_ids: BTreeSet<_> = self
            .process_outputs
            .iter()
            .map(|row| row.process_id)
            .collect();
        if self
            .process_outputs
            .iter()
            .any(|row| row.quantity_per_batch == 0)
        {
            return Err(MaterialCircuitError::ZeroQuantity);
        }
        if self
            .input_coefficients
            .iter()
            .any(|row| row.quantity_per_batch == 0 || !process_ids.contains(&row.process_id))
        {
            return Err(MaterialCircuitError::ProcessInvariant);
        }
        if self
            .labor_coefficients
            .iter()
            .any(|row| row.quantity_per_batch == 0 || !process_ids.contains(&row.process_id))
        {
            return Err(MaterialCircuitError::ProcessInvariant);
        }
        if self.process_outputs.len() != self.labor_coefficients.len() {
            return Err(MaterialCircuitError::ProcessInvariant);
        }
        for row in &self.handling_coefficients {
            if row.hours_per_unit == 0
                || !self
                    .merchants
                    .iter()
                    .any(|merchant| merchant.site_id == row.site_id)
            {
                return Err(MaterialCircuitError::MerchantInvariant);
            }
            self.grams_per_unit(row.good_id, row.unit_id)?;
        }
        Ok(())
    }

    fn validate_definitions(&self) -> Result<(), MaterialCircuitError> {
        for mandate in &self.aid_mandates {
            mandate.validate()?;
        }
        for policy in &self.household_time_policy {
            if policy.hours_per_eligible_person == 0 {
                return Err(MaterialCircuitError::HouseholdTimeInvariant);
            }
            let mut burdens = BTreeSet::new();
            for burden in &policy.unmet_burdens {
                if burden.hours_per_unmet_unit == 0
                    || !burdens.insert((burden.good_id, burden.unit_id))
                {
                    return Err(MaterialCircuitError::HouseholdTimeInvariant);
                }
            }
        }
        for policy in &self.service_inputs {
            if policy.quantity_per_period == 0 || policy.cash_floor.micro_units() < 0 {
                return Err(MaterialCircuitError::ServiceInvariant);
            }
        }
        for need in &self.household_needs {
            if need.units_per_basis == 0 {
                return Err(MaterialCircuitError::ZeroQuantity);
            }
        }
        if let Some(binding) = &self.maintenance_binding {
            if binding.spare_units_per_job == 0
                || binding.labor_units_per_job == 0
                || binding.enabled_batches_per_job == 0
                || binding.maximum_jobs_per_period == 0
                || binding.spare_unit_id == binding.labor_unit_id
            {
                return Err(MaterialCircuitError::MaintenanceInvariant);
            }
            binding
                .maximum_jobs_per_period
                .checked_mul(binding.enabled_batches_per_job)
                .ok_or(MaterialCircuitError::Arithmetic)?;
        }
        if let Some(content) = self.equipment_content() {
            crate::equipment::validate_content(content)?;
        }
        Ok(())
    }

    fn route_stages(&self, route: RouteId) -> &[RouteStage] {
        let start = self
            .route_stages
            .partition_point(|row| row.route_id < route);
        let end = self
            .route_stages
            .partition_point(|row| row.route_id <= route);
        &self.route_stages[start..end]
    }

    fn site_node(&self, site: SiteId) -> Option<LogisticsNodeId> {
        self.site_logistics_nodes
            .binary_search_by_key(&site, |row| row.site_id)
            .ok()
            .map(|index| self.site_logistics_nodes[index].node_id)
    }
}

/// Hash one canonical catalog.
///
/// # Errors
/// Returns the first encoding refusal without publishing a digest.
pub(crate) fn digest(
    catalog: &MaterialCatalogDefinition,
) -> Result<[u8; 32], MaterialCircuitError> {
    Ok(content_digest::sha256_of(&crate::wire::catalog_bytes(
        catalog,
    )?))
}

impl MaterialCatalogDefinition {
    fn canonicalize(&mut self) {
        self.site_logistics_nodes.sort();
        self.process_outputs.sort();
        self.input_coefficients.sort();
        self.labor_coefficients.sort();
        self.commodities
            .sort_by_key(|row| (row.good_id, row.unit_id));
        self.supplier_routes.sort();
        self.route_stages.sort();
        self.merchants.sort();
        self.handling_coefficients.sort();
        self.aid_mandates.sort_by_key(|row| row.id);
        self.household_time_policy
            .sort_by_key(|row| row.principal_id);
        self.service_inputs
            .sort_by_key(|row| (row.buyer_site_id, row.good_id, row.unit_id));
        self.household_needs
            .sort_by_key(|row| (row.principal_id, row.good_id, row.unit_id));
        crate::capacity::canonicalize_policy(&mut self.capacity_policy);
    }
}
