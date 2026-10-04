//! Common workplace presentation; source jobs never supply runtime headcounts.
use super::{metadata::Metadata, ProductionProjectionError};
use crate::{
    economic_catalog::{EconomicSiteSource, RecipeTemplate},
    michigan_economy::digest_hex,
    production_observation::{
        ProductionInput, ProductionLabor, ProductionProcess, ProductionSite, ProductionSiteRole,
        ProductionStock,
    },
};
use babylon_material_circuit::{
    CommodityKind, GoodId, MaterialCircuitState, MerchantRole, ProcessId, SiteId, UnitId,
};
use babylon_tick::material_world::MaterialTickReceipts;
use std::collections::BTreeMap;
type Result<T> = std::result::Result<T, ProductionProjectionError>;
type StockKey = (SiteId, GoodId, UnitId);
pub(crate) struct Quantities<'a> {
    inventory: BTreeMap<StockKey, u64>,
    stocks: BTreeMap<SiteId, Vec<&'a babylon_material_circuit::InventoryRow>>,
    inputs: BTreeMap<ProcessId, BTreeMap<(GoodId, UnitId), u64>>,
    labor_requirements: BTreeMap<ProcessId, BTreeMap<UnitId, u64>>,
    outputs: BTreeMap<ProcessId, &'a babylon_material_circuit::ProcessOutput>,
    capacity: BTreeMap<ProcessId, u64>,
    labor: BTreeMap<(SiteId, UnitId), u64>,
    suppliers: BTreeMap<StockKey, Vec<SiteId>>,
    kinds: BTreeMap<(GoodId, UnitId), CommodityKind>,
    receipts: Option<BTreeMap<ProcessId, &'a babylon_material_circuit::ProductionReceipt>>,
}
impl<'a> Quantities<'a> {
    pub(crate) fn new(
        state: &'a MaterialCircuitState,
        receipt: Option<&'a MaterialTickReceipts>,
    ) -> Self {
        let mut inputs = BTreeMap::<_, BTreeMap<_, _>>::new();
        for row in &state.input_coefficients {
            inputs
                .entry(row.process_id)
                .or_default()
                .insert((row.good_id, row.unit_id), row.quantity_per_batch);
        }
        let mut labor_requirements = BTreeMap::<_, BTreeMap<_, _>>::new();
        for row in &state.labor_coefficients {
            labor_requirements
                .entry(row.process_id)
                .or_default()
                .insert(row.unit_id, row.quantity_per_batch);
        }
        let mut stocks = BTreeMap::<_, Vec<_>>::new();
        for row in &state.inventory {
            stocks.entry(row.site_id).or_default().push(row);
        }
        let mut suppliers = BTreeMap::<_, Vec<_>>::new();
        for row in &state.supplier_routes {
            suppliers
                .entry((row.buyer_site_id, row.good_id, row.unit_id))
                .or_default()
                .push(row.supplier_site_id);
        }
        for row in &state.service_connections {
            if let babylon_material_circuit::AccountId::Site(buyer) = row.buyer {
                suppliers
                    .entry((buyer, row.good_id, row.unit_id))
                    .or_default()
                    .push(row.provider_site_id);
            }
        }
        for rows in suppliers.values_mut() {
            rows.sort_unstable();
            rows.dedup();
        }
        Self {
            inputs,
            labor_requirements,
            stocks,
            suppliers,
            inventory: state
                .inventory
                .iter()
                .map(|r| ((r.site_id, r.good_id, r.unit_id), r.quantity))
                .collect(),
            outputs: state
                .process_outputs
                .iter()
                .map(|r| (r.process_id, r))
                .collect(),
            capacity: state
                .capacities
                .iter()
                .filter(|r| r.period == state.period)
                .map(|r| (r.process_id, r.available_batches))
                .collect(),
            labor: state
                .labor
                .iter()
                .filter(|r| r.period == state.period)
                .map(|r| ((r.site_id, r.unit_id), r.available))
                .collect(),
            kinds: state
                .commodities
                .iter()
                .map(|r| ((r.good_id, r.unit_id), r.kind))
                .collect(),
            receipts: receipt.map(|r| r.production.iter().map(|r| (r.process_id, r)).collect()),
        }
    }
}

pub(super) fn project(
    metadata: &Metadata<'_>,
    state: &MaterialCircuitState,
    receipt: Option<&MaterialTickReceipts>,
) -> Result<Vec<ProductionSite>> {
    let q = Quantities::new(state, receipt);
    let merchants: BTreeMap<_, _> = state.merchants.iter().map(|r| (r.site_id, r)).collect();
    if merchants.len()
        != metadata
            .sites
            .values()
            .filter(|s| s.merchant.is_some())
            .count()
    {
        return Err(ProductionProjectionError::Content);
    }
    let mut result = Vec::with_capacity(metadata.sites.len());
    for site in &metadata.opening().sites {
        let processes = site
            .processes
            .iter()
            .map(|p| project_process(metadata, &q, p.process_id))
            .collect::<Result<Vec<_>>>()?;
        match (&site.merchant, merchants.get(&site.site_id)) {
            (None, None) => {}
            (Some(seed), Some(row))
                if (seed.role, seed.capacity_id, seed.labor_unit_id)
                    == (row.role, row.capacity_id, row.labor_unit_id) => {}
            _ => return Err(ProductionProjectionError::Content),
        }
        let mut roles = Vec::new();
        if !processes.is_empty() {
            roles.push(ProductionSiteRole::Production);
        }
        if let Some(merchant) = merchants.get(&site.site_id) {
            roles.push(match merchant.role {
                MerchantRole::Wholesale => ProductionSiteRole::Wholesale,
                MerchantRole::Retail => ProductionSiteRole::Retail,
            });
        }
        if state
            .maintenance_binding
            .as_ref()
            .is_some_and(|b| b.provider_site_id == site.site_id)
        {
            roles.push(ProductionSiteRole::Maintenance);
        }
        if roles.is_empty() {
            return Err(ProductionProjectionError::State);
        }
        let (industry_code, sector_code, observed_employment) = source_context(metadata, site)?;
        let inventory = q
            .stocks
            .get(&site.site_id)
            .into_iter()
            .flatten()
            .map(|row| {
                let good = metadata.good(row.good_id, row.unit_id)?;
                Ok(ProductionStock {
                    good_id: digest_hex(&row.good_id.as_bytes()),
                    unit_id: digest_hex(&row.unit_id.as_bytes()),
                    good: good.label.clone(),
                    unit: good.unit_label.clone(),
                    quantity: row.quantity,
                })
            })
            .collect::<Result<_>>()?;
        result.push(ProductionSite {
            id: digest_hex(&site.site_id.as_bytes()),
            location: site.location,
            name: site.label.clone(),
            industry_code,
            observed_employment,
            roles,
            sector_code,
            function: site.function.source_key().to_owned(),
            processes,
            inventory,
        });
    }
    if q.outputs.len() != metadata.processes.len()
        || result.iter().map(|r| r.processes.len()).sum::<usize>() != state.process_outputs.len()
    {
        return Err(ProductionProjectionError::Content);
    }
    Ok(result)
}

type SourceContext = (Option<String>, Option<String>, Option<u64>);
fn source_context(
    metadata: &Metadata<'_>,
    site: &crate::economic_catalog::EconomicSiteSeed,
) -> Result<SourceContext> {
    use crate::economic_catalog::EconomicSourceView;
    match (&site.source, metadata.view.sources) {
        (
            EconomicSiteSource::MichiganSector {
                county_geoid,
                sector_code,
            },
            EconomicSourceView::MichiganControl { catalog, .. },
        ) => {
            let authored = catalog
                .sites()
                .iter()
                .find(|r| r.id() == site.site_id)
                .ok_or(ProductionProjectionError::Content)?;
            if site.location
                != babylon_kernel::economic_location::EconomicLocation::domestic_county(
                    *county_geoid,
                )
                .map_err(|_| ProductionProjectionError::Content)?
                || authored.county_geoid != county_geoid.as_str()
                || authored.sector_code != sector_code.as_str()
            {
                return Err(ProductionProjectionError::Content);
            }
            let source = catalog
                .industry_for_site(authored)
                .ok_or(ProductionProjectionError::Content)?;
            Ok((
                Some(authored.naics.clone()),
                Some(authored.sector_code.clone()),
                source.annual_avg_emplvl,
            ))
        }
        (EconomicSiteSource::Qcew(key), EconomicSourceView::National { cohorts, .. }) => {
            if site.location
                != babylon_kernel::economic_location::EconomicLocation::domestic_county(key.county)
                    .map_err(|_| ProductionProjectionError::Content)?
                || key.function != Some(site.function)
            {
                return Err(ProductionProjectionError::Content);
            }
            let source = cohorts
                .group(*key)
                .filter(|r| r.is_admitted())
                .ok_or(ProductionProjectionError::Content)?;
            Ok((None, None, source.jobs().complete_total()))
        }
        (EconomicSiteSource::Designed { .. }, _) => Ok((None, None, None)),
        _ => Err(ProductionProjectionError::Content),
    }
}

pub(crate) fn project_process(
    metadata: &Metadata<'_>,
    q: &Quantities<'_>,
    id: ProcessId,
) -> Result<ProductionProcess> {
    let (site, _, recipe) = metadata
        .processes
        .get(&id)
        .ok_or(ProductionProjectionError::Content)?;
    let output = q.outputs.get(&id).ok_or(ProductionProjectionError::State)?;
    if (
        output.site_id,
        output.good_id,
        output.unit_id,
        output.quantity_per_batch,
    ) != (
        site.site_id,
        recipe.output.good_id,
        recipe.output.unit_id,
        recipe.output.quantity,
    ) {
        return Err(ProductionProjectionError::Content);
    }
    let expected_inputs: BTreeMap<_, _> = recipe
        .inputs
        .iter()
        .map(|r| ((r.good_id, r.unit_id), r.quantity))
        .collect();
    let expected_labor: BTreeMap<_, _> = recipe
        .labor
        .iter()
        .map(|r| (r.unit_id, r.hours_per_batch))
        .collect();
    if q.inputs.get(&id).cloned().unwrap_or_default() != expected_inputs
        || q.labor_requirements.get(&id).cloned().unwrap_or_default() != expected_labor
    {
        return Err(ProductionProjectionError::Content);
    }
    let good = metadata.good(output.good_id, output.unit_id)?;
    let latest = q.receipts.as_ref().and_then(|rows| rows.get(&id).copied());
    let labor = recipe
        .labor
        .iter()
        .map(|r| ProductionLabor {
            unit: "labor-hours".to_owned(),
            available: q
                .labor
                .get(&(site.site_id, r.unit_id))
                .copied()
                .unwrap_or(0),
            quantity_per_batch: r.hours_per_batch,
        })
        .collect();
    Ok(ProductionProcess {
        id: digest_hex(&id.as_bytes()),
        name: format!("{}: {}", site.label, good.label),
        output_good_id: digest_hex(&good.good_id.as_bytes()),
        output_unit_id: digest_hex(&good.unit_id.as_bytes()),
        output_good: good.label.clone(),
        output_unit: good.unit_label.clone(),
        output_per_batch: output.quantity_per_batch,
        available_batches: q.capacity.get(&id).copied().unwrap_or(0),
        planned_batches: q
            .receipts
            .as_ref()
            .map(|_| latest.map_or(0, |r| r.planned_batches)),
        produced_batches: q
            .receipts
            .as_ref()
            .map(|_| latest.map_or(0, |r| r.produced_batches)),
        inputs: inputs(metadata, q, site.site_id, recipe)?,
        labor,
    })
}
fn inputs(
    metadata: &Metadata<'_>,
    q: &Quantities<'_>,
    site: SiteId,
    recipe: &RecipeTemplate,
) -> Result<Vec<ProductionInput>> {
    recipe
        .inputs
        .iter()
        .map(|r| {
            let good = metadata.good(r.good_id, r.unit_id)?;
            let key = (site, r.good_id, r.unit_id);
            let on_hand = match q
                .kinds
                .get(&(r.good_id, r.unit_id))
                .ok_or(ProductionProjectionError::State)?
            {
                CommodityKind::Storable { .. } => Some(q.inventory.get(&key).copied().unwrap_or(0)),
                CommodityKind::PeriodService { .. } => None,
            };
            Ok(ProductionInput {
                good_id: digest_hex(&r.good_id.as_bytes()),
                unit_id: digest_hex(&r.unit_id.as_bytes()),
                good: good.label.clone(),
                unit: good.unit_label.clone(),
                quantity_per_batch: r.quantity,
                on_hand,
                supplier_site_ids: q
                    .suppliers
                    .get(&key)
                    .into_iter()
                    .flatten()
                    .map(|id| digest_hex(&id.as_bytes()))
                    .collect(),
            })
        })
        .collect()
}
