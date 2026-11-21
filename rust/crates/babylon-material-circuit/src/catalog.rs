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
        FinalDemandPrincipalId, HouseholdNeedBasis, HouseholdWant, MarketClearingPolicy, WantTier,
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
        }
    }

    fn refused(definition: MaterialCatalogDefinition) -> bool {
        matches!(
            MaterialCatalog::try_new(definition),
            Err(MaterialCircuitError::MarketClearingInvariant)
        )
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
        let head = b"babylon.material-catalog.v2".len() + 1;
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
