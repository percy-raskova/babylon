//! Immutable shared opening joins. Runtime quantities remain in material registers.
use super::ProductionProjectionError;
use crate::economic_catalog::{
    CommodityLabel, EconomicOpening, EconomicProjectionView, EconomicSiteSeed, EconomicSourceView,
    ProcessInstallation, RecipeTemplate, RecipeTemplateId,
};
use babylon_material_circuit::{GoodId, ProcessId, SiteId, SupplierRoute, UnitId};
use std::collections::BTreeMap;

type Result<T> = std::result::Result<T, ProductionProjectionError>;
pub(super) type RelationKey = (SiteId, SiteId, GoodId, UnitId);

/// One borrowed index per projection, avoiding a source-table scan per actor.
pub(crate) struct Metadata<'a> {
    pub view: EconomicProjectionView<'a>,
    pub sites: BTreeMap<SiteId, &'a EconomicSiteSeed>,
    pub goods: BTreeMap<(GoodId, UnitId), &'a CommodityLabel>,
    pub processes: BTreeMap<
        ProcessId,
        (
            &'a EconomicSiteSeed,
            &'a ProcessInstallation,
            &'a RecipeTemplate,
        ),
    >,
    pub routes: BTreeMap<RelationKey, &'a SupplierRoute>,
    capacities: BTreeMap<babylon_material_circuit::CorridorId, String>,
}
impl<'a> Metadata<'a> {
    pub fn new(view: EconomicProjectionView<'a>) -> Result<Self> {
        let opening = view.opening;
        let sites = unique(opening.sites.iter().map(|row| (row.site_id, row)))?;
        let goods = unique(
            opening
                .commodity_labels
                .iter()
                .map(|row| ((row.good_id, row.unit_id), row)),
        )?;
        let recipes: BTreeMap<RecipeTemplateId, _> =
            unique(opening.recipes.iter().map(|row| (row.id, row)))?;
        let mut processes = BTreeMap::new();
        for site in &opening.sites {
            for installation in &site.processes {
                let recipe = *recipes
                    .get(&installation.recipe)
                    .ok_or(ProductionProjectionError::Content)?;
                if processes
                    .insert(installation.process_id, (site, installation, recipe))
                    .is_some()
                {
                    return Err(ProductionProjectionError::Content);
                }
            }
        }
        let routes = unique(opening.logistics.supplier_routes.iter().map(|row| {
            (
                (
                    row.buyer_site_id,
                    row.supplier_site_id,
                    row.good_id,
                    row.unit_id,
                ),
                row,
            )
        }))?;
        let mut capacities = BTreeMap::new();
        for row in &opening.logistics.shared_capacity {
            capacities.insert(
                row.corridor_id,
                format!(
                    "Shared freight capacity {}",
                    crate::michigan_economy::digest_hex(&row.corridor_id.as_bytes())
                ),
            );
        }
        for site in &opening.sites {
            if let Some(row) = &site.merchant {
                capacities.insert(row.capacity_id, format!("{} handling", site.label));
            }
        }
        if let EconomicSourceView::MichiganControl { catalog, .. } = view.sources {
            for (id, label) in &mut capacities {
                if let Some(captured) = catalog.corridor_label(*id) {
                    captured.clone_into(label);
                }
            }
        }
        Ok(Self {
            view,
            sites,
            goods,
            processes,
            routes,
            capacities,
        })
    }
    pub fn opening(&self) -> &'a EconomicOpening {
        self.view.opening
    }
    pub fn labels(&self, good: GoodId, unit: UnitId) -> Option<(String, String)> {
        self.goods
            .get(&(good, unit))
            .map(|row| (row.label.clone(), row.unit_label.clone()))
    }
    pub fn good(&self, good: GoodId, unit: UnitId) -> Result<&'a CommodityLabel> {
        self.goods
            .get(&(good, unit))
            .copied()
            .ok_or(ProductionProjectionError::Content)
    }
    pub fn site(&self, site: SiteId) -> Result<&'a EconomicSiteSeed> {
        self.sites
            .get(&site)
            .copied()
            .ok_or(ProductionProjectionError::Content)
    }
    pub fn capacity_label(&self, id: babylon_material_circuit::CorridorId) -> Option<String> {
        self.capacities.get(&id).cloned()
    }
    pub fn michigan(&self) -> Option<&'a crate::michigan_material::MichiganMaterialCatalog> {
        match self.view.sources {
            EconomicSourceView::MichiganControl { catalog, .. } => Some(catalog),
            EconomicSourceView::National { .. } => None,
        }
    }
}
fn unique<K: Ord, V>(rows: impl Iterator<Item = (K, V)>) -> Result<BTreeMap<K, V>> {
    let mut result = BTreeMap::new();
    for (key, value) in rows {
        if result.insert(key, value).is_some() {
            return Err(ProductionProjectionError::Content);
        }
    }
    Ok(result)
}
