//! Immutable authored definitions shared by every period of one campaign.
//!
//! The catalog is canonicalized, validated and hashed once. Every period borrows
//! it; no definition is cloned into [`crate::MaterialCircuitState`].

use crate::CompanyPortfolioPolicy;
use std::collections::BTreeSet;

use babylon_kernel::content_digest;

use crate::CompanyPayoutPolicy;
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
    SupplierRoute, SupplierTransport, MAX_HOUSEHOLD_NEEDS, MAX_HOUSEHOLD_WANTS,
    MAX_INPUT_COEFFICIENTS, MAX_MATERIAL_CIRCUIT_ROWS, MAX_SUPPLIER_ROUTES,
};
use std::collections::BTreeMap;

/// Mutable authored input for admission as a campaign catalog.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MaterialCatalogDefinition {
    pub company_portfolios: Option<CompanyPortfolioPolicy>,
    pub company_payouts: Vec<CompanyPayoutPolicy>,
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
    /// The products that clear by price, or `None` for the posted-price rules.
    pub market_clearing: Option<crate::MarketClearingPolicy>,
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
        crate::financial::validate_company_policy(&self.company_payouts)?;
        if let Some(policy) = self.company_portfolios {
            policy.validate()?;
            if self.company_payouts.is_empty() {
                return Err(MaterialCircuitError::FinancialInvariant);
            }
        }
        self.validate_unique()?;
        self.validate_routes()?;
        self.validate_processes()?;
        self.validate_definitions()?;
        self.validate_market_clearing()
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
                || row.units == 0
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
        let mut burden_count = 0_usize;
        for policy in &self.household_time_policy {
            policy
                .eligible_persons
                .checked_mul(policy.hours_per_eligible_person)
                .ok_or(MaterialCircuitError::Arithmetic)?;
            burden_count = burden_count
                .checked_add(policy.unmet_burdens.len())
                .ok_or(MaterialCircuitError::Arithmetic)?;
            if burden_count > MAX_MATERIAL_CIRCUIT_ROWS {
                return Err(MaterialCircuitError::RowLimit);
            }
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

    /// The order of paying names each product once, only declared ones, and every storable good
    /// a household buys.
    fn validate_market_clearing(&self) -> Result<(), MaterialCircuitError> {
        let Some(policy) = &self.market_clearing else {
            return Ok(());
        };
        crate::adjustment::admit(&policy.adjustments)?;
        let declared: BTreeMap<(GoodId, UnitId), bool> = self
            .commodities
            .iter()
            .map(|row| {
                (
                    (row.good_id, row.unit_id),
                    matches!(row.kind, CommodityKind::Storable { .. }),
                )
            })
            .collect();
        let named: BTreeSet<_> = policy.paying_order.iter().copied().collect();
        let mut want_keys = BTreeSet::new();
        if policy.household_wants.len() > MAX_HOUSEHOLD_WANTS
            || policy.household_wants.iter().any(|want| {
                want.units_per_basis == 0
                    || want.scale_bps == 0
                    || want.scale_bps > crate::MAX_WANT_SCALE_BPS
                    || !named.contains(&(want.good_id, want.unit_id))
                    || !want_keys.insert((want.principal_id, want.tier, want.good_id, want.unit_id))
            })
        {
            return Err(MaterialCircuitError::MarketClearingInvariant);
        }
        if policy.paying_order.is_empty()
            || named.len() != policy.paying_order.len()
            || policy
                .paying_order
                .iter()
                .any(|key| !declared.contains_key(key))
            || self.household_needs.iter().any(|need| {
                let key = (need.good_id, need.unit_id);
                declared.get(&key) == Some(&true) && !named.contains(&key)
            })
        {
            return Err(MaterialCircuitError::MarketClearingInvariant);
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
        self.company_payouts.sort_by_key(|r| r.company);
        for row in &mut self.company_payouts {
            row.claims.sort_unstable_by_key(|c| c.0);
        }
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
        for policy in &mut self.household_time_policy {
            policy
                .unmet_burdens
                .sort_by_key(|row| (row.good_id, row.unit_id));
        }
        self.service_inputs
            .sort_by_key(|row| (row.buyer_site_id, row.good_id, row.unit_id));
        self.household_needs
            .sort_by_key(|row| (row.principal_id, row.good_id, row.unit_id));
        if let Some(policy) = &mut self.market_clearing {
            policy
                .household_wants
                .sort_by_key(|row| (row.principal_id, row.tier, row.good_id, row.unit_id));
        }
        crate::capacity::canonicalize_policy(&mut self.capacity_policy);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{
        adjustment, AdjustmentRule, FinalDemandPrincipalId, HouseholdNeedBasis, HouseholdWant,
        MarketClearingPolicy, WantTier,
    };

    const PINNED_BASE_DIGEST: [u8; 32] = [
        45, 217, 79, 34, 238, 57, 4, 28, 215, 33, 7, 185, 21, 72, 34, 167, 59, 200, 187, 74, 130,
        172, 93, 155, 160, 7, 158, 178, 154, 209, 170, 125,
    ];

    /// The digest of a market policy with no wants, as it was before wants existed.
    const PINNED_POLICY_DIGEST: [u8; 32] = [
        79, 35, 61, 235, 96, 80, 116, 63, 67, 215, 134, 178, 2, 40, 152, 5, 119, 138, 172, 34, 5,
        117, 185, 146, 251, 13, 226, 77, 88, 99, 168, 184,
    ];

    fn good(n: u8) -> GoodId {
        GoodId::from_bytes([n; 32])
    }

    fn unit(n: u8) -> UnitId {
        UnitId::from_bytes([n; 32])
    }

    fn storable(n: u8) -> CommodityDefinition {
        CommodityDefinition {
            good_id: good(n),
            unit_id: unit(n),
            kind: CommodityKind::Storable { grams_per_unit: 1 },
        }
    }

    /// Two storable goods; a household needs the first.
    fn base() -> MaterialCatalogDefinition {
        MaterialCatalogDefinition {
            company_portfolios: None,
            company_payouts: vec![],
            capacity_policy: CapacitySupply::FiniteSchedule,
            site_logistics_nodes: vec![],
            process_outputs: vec![],
            input_coefficients: vec![],
            labor_coefficients: vec![],
            commodities: vec![storable(1), storable(2)],
            supplier_routes: vec![],
            route_stages: vec![],
            merchants: vec![],
            handling_coefficients: vec![],
            maintenance_binding: None,
            aid_mandates: vec![],
            household_time_policy: vec![],
            service_inputs: vec![],
            household_needs: vec![HouseholdNeed {
                principal_id: FinalDemandPrincipalId::from_bytes([9; 32]),
                good_id: good(1),
                unit_id: unit(1),
                basis: HouseholdNeedBasis::Persons,
                units_per_basis: 1,
            }],
            market_clearing: None,
        }
    }

    fn policy(order: &[u8]) -> MarketClearingPolicy {
        MarketClearingPolicy {
            paying_order: order.iter().map(|&n| (good(n), unit(n))).collect(),
            household_wants: vec![],
            plans_from_spare_money: false,
            adjustments: Vec::new(),
        }
    }

    fn refused(definition: MaterialCatalogDefinition) -> bool {
        matches!(
            MaterialCatalog::try_new(definition),
            Err(MaterialCircuitError::MarketClearingInvariant)
        )
    }

    fn shop(units: u64) -> MaterialCatalogDefinition {
        let mut definition = base();
        let site = crate::SiteId::from_bytes([5; 32]);
        definition.site_logistics_nodes = vec![crate::SiteLogisticsNode {
            site_id: site,
            node_id: crate::LogisticsNodeId::from_bytes([5; 32]),
        }];
        definition.merchants = vec![crate::MerchantHandling {
            site_id: site,
            location: "county:26163"
                .parse()
                .expect("the authored literal parses as the declared type"),
            role: crate::MerchantRole::Retail,
            capacity_id: crate::CorridorId::from_bytes([6; 32]),
            labor_unit_id: unit(7),
        }];
        definition.handling_coefficients = vec![MerchantHandlingCoefficient {
            site_id: site,
            good_id: good(1),
            unit_id: unit(1),
            hours_per_unit: 3,
            units,
        }];
        definition
    }

    #[test]
    fn a_block_of_units_takes_its_hours_rounded_up() {
        use crate::transition::merchant_admission;
        let catalog = MaterialCatalog::try_new(shop(40)).expect("the shop catalog is valid");
        let site = crate::SiteId::from_bytes([5; 32]);
        let hours = |quantity| {
            merchant_admission::handling_hours(&catalog, site, good(1), unit(1), quantity)
        };
        assert_eq!(
            [hours(1), hours(40), hours(41), hours(0)],
            [Ok(1), Ok(3), Ok(4), Ok(0)]
        );
        let units =
            |hours| merchant_admission::handled_units(&catalog, site, good(1), unit(1), hours);
        assert_eq!([units(1), units(3), units(4)], [Ok(13), Ok(40), Ok(53)]);
        assert_eq!(
            merchant_admission::handling_cost_per_unit(3, 40, 30_000_000),
            Ok(2_250_000)
        );
        assert_eq!(
            merchant_admission::handling_cost_per_unit(1, 3, 10_000_000),
            Ok(3_333_334)
        );
        assert_eq!(
            merchant_admission::handling_cost_per_unit(1, 3, -1),
            Err(MaterialCircuitError::Arithmetic)
        );
    }

    #[test]
    fn a_row_of_zero_units_is_refused() {
        assert!(matches!(
            MaterialCatalog::try_new(shop(0)),
            Err(MaterialCircuitError::MerchantInvariant)
        ));
    }

    #[test]
    fn blocks_change_the_catalog_bytes_only_when_used() {
        let blocks = crate::wire::catalog_bytes(&shop(40)).expect("bytes");
        let ones = crate::wire::catalog_bytes(&shop(1)).expect("bytes");
        let head = crate::wire::MATERIAL_CATALOG_DOMAIN_BYTES.len() + 1;
        assert_eq!(blocks[head..head + 2], 10_u16.to_be_bytes());
        // Right after the version comes every byte the same catalog writes without it, then the tail.
        let mut tail = 1_u32.to_be_bytes().to_vec();
        tail.extend_from_slice(&40_u64.to_be_bytes());
        assert!(blocks.ends_with(&tail));
        assert_eq!(blocks[head + 2..blocks.len() - tail.len()], ones[head..]);
        assert_ne!(ones[head..head + 2], 10_u16.to_be_bytes());
        assert!(!ones.ends_with(&tail));
    }

    #[test]
    fn a_catalog_without_a_market_policy_keeps_its_digest() {
        let catalog = MaterialCatalog::try_new(base()).expect("the base catalog is valid");
        assert_eq!(catalog.catalog_digest(), PINNED_BASE_DIGEST);
    }

    #[test]
    fn a_market_policy_without_wants_keeps_its_digest() {
        let mut with = base();
        with.market_clearing = Some(policy(&[1, 2]));
        let catalog = MaterialCatalog::try_new(with).expect("valid");
        assert_eq!(catalog.catalog_digest(), PINNED_POLICY_DIGEST);
    }

    #[test]
    fn a_market_policy_changes_the_digest_and_the_version() {
        let plain = MaterialCatalog::try_new(base()).expect("valid");
        let mut with = base();
        with.market_clearing = Some(policy(&[1, 2]));
        let with = MaterialCatalog::try_new(with).expect("valid");
        assert_ne!(plain.catalog_digest(), with.catalog_digest());
        let bytes = crate::wire::catalog_bytes(&with).expect("bytes");
        let head = b"babylon.material-catalog.v2".len() + 1;
        assert_eq!(bytes[head..head + 2], 6_u16.to_be_bytes());
        assert_eq!(bytes[head + 2..head + 4], 2_u16.to_be_bytes());
        let plain_bytes = crate::wire::catalog_bytes(&plain).expect("bytes");
        assert_eq!(plain_bytes[head..head + 2], 2_u16.to_be_bytes());
        // The body is the unchanged body, then the tail.
        let body = &plain_bytes[head + 2..];
        assert_eq!(&bytes[head + 4..head + 4 + body.len()], body);
        let mut tail = 2_u32.to_be_bytes().to_vec();
        for n in [1_u8, 2] {
            tail.extend_from_slice(&[n; 32]);
            tail.extend_from_slice(&[n; 32]);
        }
        assert_eq!(&bytes[head + 4 + body.len()..], tail.as_slice());
    }

    fn asking(rules: &[AdjustmentRule]) -> MaterialCatalogDefinition {
        let mut definition = base();
        let mut order = policy(&[1, 2]);
        order.adjustments = rules.to_vec();
        definition.market_clearing = Some(order);
        definition
    }

    #[test]
    fn adjustments_write_version_nine_before_the_bytes_without_them() {
        use crate::AdjustmentRule::HiringWithinMeans;
        let asking = asking(&[HiringWithinMeans]);
        let mut quiet = asking.clone();
        quiet
            .market_clearing
            .as_mut()
            .expect("a policy")
            .adjustments = vec![];
        let bytes = crate::wire::catalog_bytes(&asking).expect("bytes");
        let plain = crate::wire::catalog_bytes(&quiet).expect("bytes");
        let head = crate::wire::MATERIAL_CATALOG_DOMAIN_BYTES.len() + 1;
        assert_eq!(bytes[head..head + 2], 9_u16.to_be_bytes());
        assert_eq!(bytes[head + 2..head + 4], 1_u16.to_be_bytes());
        assert_eq!(bytes[head + 4], 1_u8);
        assert_eq!(&bytes[head + 5..], &plain[head..]);
        // Without A6's flag the list sits where A6's version would; with it, the list is first of the two.
        let mut spare = asking;
        spare
            .market_clearing
            .as_mut()
            .expect("a policy")
            .plans_from_spare_money = true;
        let bytes = crate::wire::catalog_bytes(&spare).expect("bytes");
        assert_eq!(bytes[head..head + 2], 9_u16.to_be_bytes());
        assert_eq!(bytes[head + 5..head + 7], 8_u16.to_be_bytes());
    }

    #[test]
    fn a_restart_writes_its_periods() {
        use crate::AdjustmentRule::{
            HiringWithinMeans, OwnerRestart, RestingPrice, SeekingInPlace, StopWithoutPay,
        };
        let rules = [
            HiringWithinMeans,
            SeekingInPlace,
            StopWithoutPay,
            RestingPrice,
            OwnerRestart { outlay_periods: 2 },
        ];
        let bytes = crate::wire::catalog_bytes(&asking(&rules)).expect("bytes");
        let head = crate::wire::MATERIAL_CATALOG_DOMAIN_BYTES.len() + 1;
        assert_eq!(bytes[head + 2..head + 4], 5_u16.to_be_bytes());
        // Four tags of one byte, then the fifth tag and its periods.
        assert_eq!(bytes[head + 4..head + 8], [1_u8, 2, 3, 4]);
        assert_eq!(bytes[head + 8], 5_u8);
        assert_eq!(bytes[head + 9..head + 17], 2_u64.to_be_bytes());
    }

    #[test]
    fn adjustments_change_the_digest() {
        use crate::AdjustmentRule::HiringWithinMeans;
        for spare in [false, true] {
            let mut plain = asking(&[]);
            let mut with = asking(&[HiringWithinMeans]);
            for definition in [&mut plain, &mut with] {
                definition
                    .market_clearing
                    .as_mut()
                    .expect("a policy")
                    .plans_from_spare_money = spare;
            }
            assert_ne!(
                digest(&plain).expect("digest"),
                digest(&with).expect("digest")
            );
        }
    }

    #[test]
    fn admission_refuses_a_list_out_of_order_or_twice() {
        use crate::AdjustmentRule::{HiringWithinMeans, RestingPrice, SeekingInPlace};
        assert!(adjustment::refuse_combinations(&[SeekingInPlace, HiringWithinMeans]).is_err());
        assert!(adjustment::refuse_combinations(&[HiringWithinMeans, HiringWithinMeans]).is_err());
        assert!(adjustment::refuse_combinations(&[RestingPrice, HiringWithinMeans]).is_err());
        assert!(adjustment::refuse_combinations(&[
            HiringWithinMeans,
            SeekingInPlace,
            RestingPrice
        ])
        .is_ok());
        assert!(adjustment::refuse_combinations(&[]).is_ok());
    }

    #[test]
    fn admission_refuses_the_stop_rule_without_seekers() {
        use crate::AdjustmentRule::{SeekingInPlace, StopWithoutPay};
        assert!(adjustment::refuse_combinations(&[StopWithoutPay]).is_err());
        assert!(adjustment::refuse_combinations(&[SeekingInPlace, StopWithoutPay]).is_ok());
    }

    #[test]
    fn admission_refuses_a_restart_without_its_rules() {
        use crate::AdjustmentRule::{
            HiringWithinMeans, OwnerRestart, RestingPrice, SeekingInPlace, StopWithoutPay,
        };
        let restart = OwnerRestart { outlay_periods: 1 };
        assert!(adjustment::refuse_combinations(&[restart]).is_err());
        assert!(adjustment::refuse_combinations(&[
            SeekingInPlace,
            StopWithoutPay,
            RestingPrice,
            restart
        ])
        .is_err());
        assert!(adjustment::refuse_combinations(&[
            HiringWithinMeans,
            SeekingInPlace,
            StopWithoutPay,
            restart
        ])
        .is_err());
        assert!(adjustment::refuse_combinations(&[
            HiringWithinMeans,
            SeekingInPlace,
            RestingPrice,
            restart
        ])
        .is_err());
        assert!(adjustment::refuse_combinations(&[
            HiringWithinMeans,
            SeekingInPlace,
            StopWithoutPay,
            RestingPrice,
            restart
        ])
        .is_ok());
    }

    #[test]
    fn admission_refuses_a_restart_of_zero_periods() {
        use crate::AdjustmentRule::{
            HiringWithinMeans, OwnerRestart, RestingPrice, SeekingInPlace, StopWithoutPay,
        };
        let with = |outlay_periods| {
            [
                HiringWithinMeans,
                SeekingInPlace,
                StopWithoutPay,
                RestingPrice,
                OwnerRestart { outlay_periods },
            ]
        };
        assert!(adjustment::refuse_combinations(&with(0)).is_err());
        assert!(adjustment::refuse_combinations(&with(1)).is_ok());
    }

    #[test]
    fn needs_is_the_table_of_the_refusals() {
        use crate::AdjustmentRule::{
            GoodsStepDown, HiringWithinMeans, OwnerRestart, RestingPrice, SeekingInPlace,
            StopWithoutPay,
        };
        let all = [
            HiringWithinMeans,
            SeekingInPlace,
            StopWithoutPay,
            RestingPrice,
            OwnerRestart { outlay_periods: 1 },
            GoodsStepDown,
        ];
        for rule in all {
            assert_eq!(
                adjustment::refuse_combinations(&[rule]).is_err(),
                !rule.needs().is_empty(),
                "{rule:?} alone"
            );
            // The rule with every rule it needs, and those rules' needs, in the order of the rules.
            let mut list = vec![rule];
            let mut index = 0;
            while index < list.len() {
                let needs = list[index].needs();
                for need in needs {
                    if !crate::adjustment::asks(&list, *need) {
                        list.push(*need);
                    }
                }
                index += 1;
            }
            list.sort();
            assert!(
                adjustment::refuse_combinations(&list).is_ok(),
                "{rule:?} with its needs"
            );
        }
    }

    #[test]
    fn admission_admits_all_six_rules_together() {
        use crate::AdjustmentRule::{
            GoodsStepDown, HiringWithinMeans, OwnerRestart, RestingPrice, SeekingInPlace,
            StopWithoutPay,
        };
        let all = [
            HiringWithinMeans,
            SeekingInPlace,
            StopWithoutPay,
            RestingPrice,
            OwnerRestart { outlay_periods: 1 },
            GoodsStepDown,
        ];
        assert!(!refused(asking(&all)), "every rule is built");
        assert!(
            !refused(asking(&[GoodsStepDown])),
            "the step down asks for no other rule"
        );
    }

    #[test]
    fn a_market_policy_is_refused_when_empty_duplicated_unknown_or_missing_a_household_good() {
        let mut empty = base();
        empty.market_clearing = Some(policy(&[]));
        assert!(refused(empty));
        let mut twice = base();
        twice.market_clearing = Some(policy(&[1, 1]));
        assert!(refused(twice));
        let mut unknown = base();
        unknown.market_clearing = Some(policy(&[1, 7]));
        assert!(refused(unknown));
        let mut missing = base();
        missing.market_clearing = Some(policy(&[2]));
        assert!(refused(missing));
    }

    #[test]
    fn place_follows_the_order_of_paying() {
        let order = policy(&[2, 1]);
        assert_eq!(order.place(good(2), unit(2)), Some(0));
        assert_eq!(order.place(good(1), unit(1)), Some(1));
        assert_eq!(order.place(good(1), unit(2)), None);
        assert_eq!(order.place(good(3), unit(3)), None);
    }

    #[test]
    fn a_market_policy_needs_no_company_portfolio() {
        let mut with = base();
        with.market_clearing = Some(policy(&[1]));
        assert!(with.company_portfolios.is_none() && with.company_payouts.is_empty());
        MaterialCatalog::try_new(with).expect("a policy alone is admitted");
    }

    fn want(principal: u8, tier: WantTier, n: u8, units: u64) -> HouseholdWant {
        HouseholdWant {
            principal_id: FinalDemandPrincipalId::from_bytes([principal; 32]),
            tier,
            good_id: good(n),
            unit_id: unit(n),
            basis: HouseholdNeedBasis::Persons,
            units_per_basis: units,
            scale_bps: crate::WANT_SCALE_ONE_BPS,
        }
    }

    fn with_wants(wants: Vec<HouseholdWant>) -> MaterialCatalogDefinition {
        let mut definition = base();
        let mut order = policy(&[1, 2]);
        order.household_wants = wants;
        definition.market_clearing = Some(order);
        definition
    }

    #[test]
    fn wants_write_version_seven_and_change_the_digest() {
        let plain = MaterialCatalog::try_new(with_wants(vec![])).expect("valid");
        let rows = vec![
            want(9, WantTier::Comfort, 2, 3),
            want(9, WantTier::Luxury, 2, 1),
        ];
        let wanting = MaterialCatalog::try_new(with_wants(rows)).expect("valid");
        assert_ne!(plain.catalog_digest(), wanting.catalog_digest());
        let bytes = crate::wire::catalog_bytes(&wanting).expect("bytes");
        let plain_bytes = crate::wire::catalog_bytes(&plain).expect("bytes");
        let head = b"babylon.material-catalog.v2".len() + 1;
        assert_eq!(bytes[head..head + 2], 7_u16.to_be_bytes());
        assert_eq!(bytes[head + 2..head + 4], 2_u16.to_be_bytes());
        // The body and the market tail are the bytes without wants; the wants tail follows.
        assert_eq!(
            &bytes[head + 2..plain_bytes.len()],
            &plain_bytes[head + 2..]
        );
        let mut tail = 2_u32.to_be_bytes().to_vec();
        for (tier, units) in [(2_u8, 3_u64), (3, 1)] {
            tail.extend_from_slice(&[9; 32]);
            tail.push(tier);
            tail.extend_from_slice(&[2; 32]);
            tail.extend_from_slice(&[2; 32]);
            tail.push(1);
            tail.extend_from_slice(&units.to_be_bytes());
        }
        assert_eq!(tail.len(), 4 + 2 * 106);
        assert_eq!(&bytes[plain_bytes.len()..], tail.as_slice());
    }

    fn asking_spare_money(mut definition: MaterialCatalogDefinition) -> MaterialCatalogDefinition {
        definition
            .market_clearing
            .as_mut()
            .expect("a market policy")
            .plans_from_spare_money = true;
        definition
    }

    #[test]
    fn spare_money_writes_version_eight_before_the_bytes_without_it() {
        let mut quiet = base();
        quiet.market_clearing = Some(policy(&[1, 2]));
        let asking = asking_spare_money(quiet.clone());
        let plain = MaterialCatalog::try_new(quiet).expect("valid");
        let asking = MaterialCatalog::try_new(asking).expect("valid");
        let plain_bytes = crate::wire::catalog_bytes(&plain).expect("bytes");
        let bytes = crate::wire::catalog_bytes(&asking).expect("bytes");
        let head = crate::wire::MATERIAL_CATALOG_DOMAIN_BYTES.len() + 1;
        assert_eq!(bytes[head..head + 2], 8_u16.to_be_bytes());
        assert_eq!(&bytes[head + 2..], &plain_bytes[head..]);
    }

    #[test]
    fn spare_money_changes_the_digest() {
        let mut quiet = base();
        quiet.market_clearing = Some(policy(&[1, 2]));
        let plain = MaterialCatalog::try_new(quiet.clone()).expect("valid");
        let asking = MaterialCatalog::try_new(asking_spare_money(quiet)).expect("valid");
        assert_ne!(plain.catalog_digest(), asking.catalog_digest());
        let rows = vec![want(9, WantTier::Comfort, 2, 3)];
        let plain = MaterialCatalog::try_new(with_wants(rows)).expect("valid");
        let asking = MaterialCatalog::try_new(asking_spare_money(with_wants(vec![want(
            9,
            WantTier::Comfort,
            2,
            3,
        )])))
        .expect("valid");
        assert_ne!(plain.catalog_digest(), asking.catalog_digest());
    }

    #[test]
    fn a_want_is_refused_when_zero_unlisted_twice_or_too_many() {
        assert!(refused(with_wants(vec![want(9, WantTier::Comfort, 2, 0)])));
        let mut unlisted = base();
        unlisted.commodities.push(storable(3));
        let mut order = policy(&[1, 2]);
        order.household_wants = vec![want(9, WantTier::Comfort, 3, 1)];
        unlisted.market_clearing = Some(order);
        assert!(refused(unlisted));
        assert!(refused(with_wants(vec![
            want(9, WantTier::Comfort, 2, 1),
            want(9, WantTier::Comfort, 2, 5),
        ])));
        // One more than the bound, every key distinct.
        let many = (0..=crate::MAX_HOUSEHOLD_WANTS as u64)
            .map(|k| {
                let mut row = want(9, WantTier::Comfort, 2, 1);
                let mut id = [9_u8; 32];
                id[..8].copy_from_slice(&k.to_be_bytes());
                row.principal_id = FinalDemandPrincipalId::from_bytes(id);
                row
            })
            .collect();
        assert!(refused(with_wants(many)));
    }

    fn scaled(bps: u32) -> HouseholdWant {
        let mut row = want(9, WantTier::Luxury, 2, 2);
        row.scale_bps = bps;
        row
    }

    #[test]
    fn a_scale_out_of_range_is_refused() {
        for bps in [0, 1_000_001] {
            assert!(
                matches!(
                    MaterialCatalog::try_new(with_wants(vec![scaled(bps)])),
                    Err(MaterialCircuitError::MarketClearingInvariant)
                ),
                "{bps}"
            );
        }
        for bps in [1, 1_000_000] {
            MaterialCatalog::try_new(with_wants(vec![scaled(bps)])).expect("the scale is admitted");
        }
    }

    #[test]
    fn a_scale_changes_the_catalog_bytes_only_when_used() {
        let bytes = |definition: &MaterialCatalogDefinition| {
            crate::wire::catalog_bytes(definition).expect("bytes")
        };
        let head = crate::wire::MATERIAL_CATALOG_DOMAIN_BYTES.len() + 1;
        let ones = with_wants(vec![scaled(10_000)]);
        let ones_bytes = bytes(&ones);
        // Wants at 10,000 write the bytes written before the scale existed: version 7 first.
        assert_eq!(ones_bytes[head..head + 2], 7_u16.to_be_bytes());
        let scaled_definition = with_wants(vec![scaled(12_500)]);
        let scaled_bytes = bytes(&scaled_definition);
        assert_eq!(scaled_bytes[head..head + 2], 11_u16.to_be_bytes());
        let mut tail = 1_u32.to_be_bytes().to_vec();
        tail.extend_from_slice(&12_500_u32.to_be_bytes());
        assert!(scaled_bytes.ends_with(&tail));
        assert_eq!(
            scaled_bytes[head + 2..scaled_bytes.len() - tail.len()],
            ones_bytes[head..]
        );
        let other = bytes(&with_wants(vec![scaled(12_501)]));
        assert_ne!(scaled_bytes, other);
        assert_eq!(scaled_bytes.len(), other.len());
        // A block above 1 and a scaled want: version 10, then 11, and the two tails in that order.
        let mut both = shop(40);
        both.market_clearing = scaled_definition.market_clearing.clone();
        let both_bytes = bytes(&both);
        assert_eq!(both_bytes[head..head + 2], 10_u16.to_be_bytes());
        assert_eq!(both_bytes[head + 2..head + 4], 11_u16.to_be_bytes());
        let mut tails = 1_u32.to_be_bytes().to_vec();
        tails.extend_from_slice(&40_u64.to_be_bytes());
        tails.extend_from_slice(&tail);
        assert!(both_bytes.ends_with(&tails));
    }

    #[test]
    fn wants_are_sorted_and_found_by_principal() {
        let catalog = MaterialCatalog::try_new(with_wants(vec![
            want(9, WantTier::Luxury, 2, 1),
            want(4, WantTier::Luxury, 1, 1),
            want(9, WantTier::Comfort, 2, 2),
            want(9, WantTier::Comfort, 1, 2),
        ]))
        .expect("valid");
        let order = catalog.market_clearing.as_ref().expect("a policy");
        let tiers: Vec<_> = order
            .household_wants
            .iter()
            .map(|row| (row.principal_id, row.tier, row.good_id))
            .collect();
        assert!(tiers.windows(2).all(|pair| pair[0] < pair[1]));
        let nine = order.wants_of(FinalDemandPrincipalId::from_bytes([9; 32]));
        assert_eq!(nine.len(), 3);
        assert_eq!(nine[0].tier, WantTier::Comfort);
        assert_eq!(nine[0].good_id, good(1));
        assert_eq!(nine[2].tier, WantTier::Luxury);
        assert_eq!(
            order
                .wants_of(FinalDemandPrincipalId::from_bytes([4; 32]))
                .len(),
            1
        );
        assert_eq!(
            order
                .wants_of(FinalDemandPrincipalId::from_bytes([5; 32]))
                .len(),
            0
        );
    }
}
