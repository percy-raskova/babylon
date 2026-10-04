//! Intentional Michigan physical controls import the common opening shape.
//! No normalized per-owner material states or observed-person inference are made.
use super::{
    CatalogAccounting, CatalogCapacity, CatalogLogistics, CatalogMaintenance, CatalogOpeningOrders,
    CatalogPolicies, CommodityAmount, CommodityLabel, EconomicCatalogError, EconomicOpening,
    EconomicSiteSeed, EconomicSiteSource, HandlingRequirement, LaborRequirement, MerchantSeed,
    OpeningCommodityStock, ProcessInstallation, RecipeTemplate, RecipeTemplateId,
    ResidentStaffingMemberSeed, ResidentStaffingPoolSeed,
};
use crate::{
    michigan_cohorts::MICHIGAN_COHORT_SCENARIO,
    michigan_material::{
        MichiganMaterialCatalog, MichiganMaterialPath, MichiganMaterialSite, MichiganSiteRole,
    },
};
use babylon_graph::stable_element::StableElementKey;
use babylon_kernel::{
    clock::CampaignDuration, content_digest::sha256_of, currency::Currency,
    economic_identity::EconomicFunction, economic_location::EconomicLocation,
};
use babylon_material_circuit::{
    CapacityRow, CommodityDefinition, CommodityKind, CorridorCapacity, CorridorId,
    FinalDemandOrder, FinalDemandPrincipal, FinalDemandPrincipalId, FinancialInstitutions,
    InstalledProcessCapacity, MaintenanceBinding, MerchantRole, OrderAccessMode, OrderRow,
    RollingProcessSupply, RouteStage, RouteStageCapacity, SharedCapacitySupply,
    StaffingMemberBinding, StaffingMemberId, StaffingPolicy, StaffingPoolBinding, StaffingPoolId,
    StaffingWorkSource, SupplierRoute, SupplierTransport, UnitId,
};
use std::collections::{BTreeMap, BTreeSet};
type Result<T> = std::result::Result<T, EconomicCatalogError>;
fn zero() -> Currency {
    Currency::from_micro_units(0)
}
fn labor_unit() -> UnitId {
    UnitId::from_bytes(sha256_of(b"babylon.michigan-material.v1\0unit\0labor-hour"))
}
fn subject(local_name: String) -> StableElementKey {
    StableElementKey::Node {
        scenario: MICHIGAN_COHORT_SCENARIO.to_owned(),
        local_name,
    }
}
fn location(county: &str) -> Result<EconomicLocation> {
    EconomicLocation::domestic_county(county.parse().map_err(|_| EconomicCatalogError::Identity)?)
        .map_err(|_| EconomicCatalogError::Identity)
}
fn good(catalog: &MichiganMaterialCatalog, key: &str, quantity: u64) -> Result<CommodityAmount> {
    let source = catalog
        .good(key)
        .ok_or(EconomicCatalogError::Opening("Michigan good"))?;
    Ok(CommodityAmount {
        good_id: source.id(),
        unit_id: source.unit_id(),
        quantity,
    })
}
/// Regenerate one explicitly simplified control from its admitted authored model.
/// # Errors
/// Refuses absent source identities, inconsistent quantities or checked overflow.
pub fn import_michigan_opening(catalog: &MichiganMaterialCatalog) -> Result<EconomicOpening> {
    let mut recipes = Vec::new();
    for (index, p) in catalog.processes().iter().enumerate() {
        recipes.push(RecipeTemplate {
            id: RecipeTemplateId(u16::try_from(index).map_err(|_| EconomicCatalogError::Bound)?),
            output: good(catalog, &p.output_good_key, p.output_quantity_per_batch)?,
            inputs: p
                .inputs
                .iter()
                .map(|r| good(catalog, &r.good_key, r.quantity_per_batch))
                .collect::<Result<_>>()?,
            labor: Some(LaborRequirement {
                unit_id: labor_unit(),
                hours_per_batch: p.labor_hours_per_batch,
            }),
        });
    }
    let sites = catalog
        .sites()
        .iter()
        .map(|site| import_site(catalog, site))
        .collect::<Result<_>>()?;
    let staffing = catalog
        .staffing()
        .pools
        .iter()
        .map(|seed| import_pool(catalog, seed))
        .collect::<Result<_>>()?;
    let (logistics, orders, capacity) = import_logistics(catalog)?;
    Ok(EconomicOpening {
        commodity_labels: catalog
            .goods()
            .iter()
            .map(|g| CommodityLabel {
                good_id: g.id(),
                unit_id: g.unit_id(),
                key: g.key.clone(),
                label: g.label.clone(),
                unit_label: g.unit_key.clone(),
            })
            .collect(),
        commodities: catalog
            .goods()
            .iter()
            .map(|g| CommodityDefinition {
                good_id: g.id(),
                unit_id: g.unit_id(),
                kind: CommodityKind::Storable {
                    grams_per_unit: g.grams_per_unit,
                },
            })
            .collect(),
        recipes,
        household_templates: vec![],
        sites,
        households: vec![],
        staffing,
        employment: vec![],
        accounting: CatalogAccounting::PhysicalControl,
        institutional_cash: vec![],
        institutions: FinancialInstitutions::empty(),
        equity: vec![],
        equipment: vec![],
        capacity,
        policies: CatalogPolicies {
            aid: babylon_material_circuit::AidBook::default(),
            household_time: babylon_material_circuit::HouseholdTimeAccounting::NotModeled,
            offers: vec![],
            replenishment: vec![],
            household_purchases: vec![],
            service_inputs: vec![],
            service_connections: vec![],
        },
        logistics,
        orders,
        maintenance: import_maintenance(catalog)?,
    })
}
fn import_site(
    catalog: &MichiganMaterialCatalog,
    site: &MichiganMaterialSite,
) -> Result<EconomicSiteSeed> {
    let mut quantities = BTreeMap::<String, u64>::new();
    let mut processes = Vec::new();
    for (index, p) in catalog
        .processes()
        .iter()
        .enumerate()
        .filter(|(_, p)| p.site_key == site.key)
    {
        quantities.entry(p.output_good_key.clone()).or_default();
        for input in &p.inputs {
            let amount = quantities.entry(input.good_key.clone()).or_default();
            *amount = amount
                .checked_add(input.opening_quantity)
                .ok_or(EconomicCatalogError::Arithmetic)?;
        }
        processes.push(ProcessInstallation {
            process_id: p.id(),
            recipe: RecipeTemplateId(
                u16::try_from(index).map_err(|_| EconomicCatalogError::Bound)?,
            ),
            planned_batches: p.opening_planned_batches,
            output_buffer: 0,
        });
    }
    for route in catalog
        .routes()
        .iter()
        .filter(|r| r.buyer_site_key == site.key || r.supplier_site_key == site.key)
    {
        quantities.entry(route.good_key.clone()).or_default();
    }
    let merchant = catalog
        .merchants()
        .iter()
        .find(|m| m.site_key == site.key)
        .map(|m| {
            let mut handling = Vec::new();
            for (key, hours) in &m.handling_hours_per_unit {
                quantities.entry(key.clone()).or_default();
                let amount = good(catalog, key, 0)?;
                handling.push(HandlingRequirement {
                    good_id: amount.good_id,
                    unit_id: amount.unit_id,
                    hours_per_unit: *hours,
                });
            }
            Ok(MerchantSeed {
                role: match site.role {
                    MichiganSiteRole::Wholesale => MerchantRole::Wholesale,
                    MichiganSiteRole::Retail => MerchantRole::Retail,
                    _ => return Err(EconomicCatalogError::Opening("Michigan merchant role")),
                },
                capacity_id: corridor(catalog, &m.capacity_key)?,
                labor_unit_id: labor_unit(),
                handling,
            })
        })
        .transpose()?;
    if let Some(m) = catalog
        .maintenance()
        .filter(|m| m.provider_site_key == site.key)
    {
        quantities.insert(m.spare_good_key.clone(), m.opening_spare_parts);
    }
    let opening_stock = quantities
        .into_iter()
        .map(|(key, quantity)| {
            Ok(OpeningCommodityStock {
                amount: good(catalog, &key, quantity)?,
                total_cost: zero(),
            })
        })
        .collect::<Result<_>>()?;
    Ok(EconomicSiteSeed {
        site_id: site.id(),
        label: site.label.clone(),
        subject: subject(format!("workplace-{}", site.key)),
        location: location(&site.county_geoid)?,
        logistics_node_id: site.node_id(),
        source: EconomicSiteSource::MichiganSector {
            county_geoid: site
                .county_geoid
                .parse()
                .map_err(|_| EconomicCatalogError::Identity)?,
            sector_code: crate::michigan_sectors::MichiganSectorCode::try_from(
                site.sector_code.as_str(),
            )
            .map_err(|_| EconomicCatalogError::Identity)?,
        },
        // Explicit coarse Designed role for these authored controls; no national
        // function mapping or political-class inference is asserted here.
        function: control_function(site.role),
        processes,
        merchant,
        opening_stock,
        opening_cash: zero(),
    })
}
fn control_function(role: MichiganSiteRole) -> EconomicFunction {
    match role {
        MichiganSiteRole::Production => EconomicFunction::Manufacturing,
        MichiganSiteRole::Wholesale | MichiganSiteRole::Retail => {
            EconomicFunction::DistributionTransport
        }
        MichiganSiteRole::Maintenance => EconomicFunction::BusinessServices,
    }
}

fn corridor(catalog: &MichiganMaterialCatalog, key: &str) -> Result<CorridorId> {
    catalog
        .corridors()
        .iter()
        .find(|r| r.key == key)
        .map(crate::michigan_material::MichiganMaterialCorridor::id)
        .ok_or(EconomicCatalogError::Opening("Michigan corridor"))
}
fn import_pool(
    catalog: &MichiganMaterialCatalog,
    seed: &crate::michigan_material::MichiganWorkforceSeed,
) -> Result<ResidentStaffingPoolSeed> {
    let site = catalog
        .site(&seed.site_key)
        .ok_or(EconomicCatalogError::Opening("Michigan staffing site"))?;
    let force = seed
        .employed
        .checked_add(seed.reserve)
        .ok_or(EconomicCatalogError::Arithmetic)?;
    let pool_id = StaffingPoolId::from_bytes(sha256_of(
        format!("babylon.michigan-staffing.v1\0pool\0{}", seed.key).as_bytes(),
    ));
    let mut work_sources = seed
        .process_keys
        .iter()
        .map(|key| {
            catalog
                .processes()
                .iter()
                .find(|p| p.key == *key)
                .map(|p| StaffingWorkSource::Production(p.id()))
                .ok_or(EconomicCatalogError::Opening("Michigan staffing process"))
        })
        .collect::<Result<Vec<_>>>()?;
    if seed.merchant_handling {
        work_sources.push(StaffingWorkSource::MerchantHandling(site.id()));
    }
    if seed.maintenance {
        work_sources.push(StaffingWorkSource::Maintenance(site.id()));
    }
    let pool = StaffingPoolBinding::try_new(
        pool_id,
        site.id(),
        labor_unit(),
        force,
        StaffingPolicy::one_period(catalog.staffing().hours_per_worker_period)
            .map_err(|_| EconomicCatalogError::Opening("staffing policy"))?,
        work_sources,
    )
    .map_err(|_| EconomicCatalogError::Opening("staffing pool"))?;
    let mut members = Vec::new();
    if force > 0 {
        let id = |kind: &str| {
            let mut bytes = format!("babylon.michigan-control-resident.v1\0{kind}\0").into_bytes();
            bytes.extend_from_slice(&pool_id.as_bytes());
            sha256_of(&bytes)
        };
        let member = StaffingMemberBinding::try_new(
            StaffingMemberId::from_bytes(id("member")),
            FinalDemandPrincipalId::from_bytes(id("household")),
            location(&site.county_geoid)?,
            force,
        )
        .map_err(|_| EconomicCatalogError::Opening("staffing member"))?;
        members.push(ResidentStaffingMemberSeed {
            subject: subject(seed.local_name()),
            member,
            employed: seed.employed,
            reserve: seed.reserve,
        });
    }
    Ok(ResidentStaffingPoolSeed {
        workplace: subject(seed.workplace_local_name()),
        pool,
        previous_unretained_hours: seed.previous_unretained_hours,
        members,
    })
}
fn import_logistics(
    catalog: &MichiganMaterialCatalog,
) -> Result<(CatalogLogistics, CatalogOpeningOrders, CatalogCapacity)> {
    let mut logistics = CatalogLogistics {
        supplier_routes: vec![],
        route_stages: vec![],
        memberships: vec![],
        shared_capacity: vec![],
    };
    let mut orders = CatalogOpeningOrders {
        principals: vec![],
        goods: vec![],
        final_demand: vec![],
    };
    for route in catalog.routes() {
        let buyer = catalog
            .site(&route.buyer_site_key)
            .ok_or(EconomicCatalogError::Opening("route buyer"))?;
        let supplier = catalog
            .site(&route.supplier_site_key)
            .ok_or(EconomicCatalogError::Opening("route supplier"))?;
        let amount = good(catalog, &route.good_key, route.ordered_quantity)?;
        let transport_kind = match &route.path {
            MichiganMaterialPath::Local => SupplierTransport::Local,
            MichiganMaterialPath::Routed {
                travel_periods,
                capacity_keys,
                ..
            } => {
                logistics.route_stages.push(RouteStage {
                    route_id: route.id(),
                    stage_index: 0,
                    from_node_id: supplier.node_id(),
                    to_node_id: buyer.node_id(),
                    travel_periods: *travel_periods,
                    loss_ppm: 0,
                });
                for key in capacity_keys {
                    logistics.memberships.push(RouteStageCapacity {
                        route_id: route.id(),
                        stage_index: 0,
                        corridor_id: corridor(catalog, key)?,
                    });
                }
                SupplierTransport::Staged
            }
        };
        logistics.supplier_routes.push(SupplierRoute {
            buyer_site_id: buyer.id(),
            supplier_site_id: supplier.id(),
            good_id: amount.good_id,
            unit_id: amount.unit_id,
            route_id: route.id(),
            transport_kind,
        });
        orders.goods.push(OrderRow {
            order_id: route.order_id(),
            access_mode: OrderAccessMode::CommoditySale,
            buyer_site_id: buyer.id(),
            supplier_site_id: supplier.id(),
            good_id: amount.good_id,
            unit_id: amount.unit_id,
            ordered: amount.quantity,
            shipped: 0,
            lost: 0,
            delivered: 0,
            realized: 0,
        });
    }
    import_final_demands(catalog, &mut orders)?;
    let active: BTreeSet<_> = logistics
        .memberships
        .iter()
        .map(|r| r.corridor_id)
        .chain(
            catalog
                .merchants()
                .iter()
                .map(|m| corridor(catalog, &m.capacity_key))
                .collect::<Result<Vec<_>>>()?,
        )
        .collect();
    logistics.shared_capacity = catalog
        .corridors()
        .iter()
        .filter(|c| active.contains(&c.id()))
        .map(|c| SharedCapacitySupply {
            corridor_id: c.id(),
            grams_per_period: c.capacity_grams_per_period,
        })
        .collect();
    let capacity = import_capacity(catalog, &logistics);
    Ok((logistics, orders, capacity))
}
fn import_final_demands(
    catalog: &MichiganMaterialCatalog,
    orders: &mut CatalogOpeningOrders,
) -> Result<()> {
    let mut principals = BTreeSet::new();
    for demand in catalog.final_demands() {
        if principals.insert(demand.principal_id()) {
            orders.principals.push(FinalDemandPrincipal {
                id: demand.principal_id(),
                location: location(&demand.county_geoid)?,
            });
        }
        let site = catalog
            .site(&demand.retailer_site_key)
            .ok_or(EconomicCatalogError::Opening("final retailer"))?;
        let amount = good(catalog, &demand.good_key, demand.ordered_quantity)?;
        orders.final_demand.push(FinalDemandOrder {
            order_id: demand.order_id(),
            retailer_site_id: site.id(),
            demand_principal_id: demand.principal_id(),
            good_id: amount.good_id,
            unit_id: amount.unit_id,
            ordered: amount.quantity,
            fulfilled: 0,
        });
    }
    Ok(())
}

fn import_capacity(
    catalog: &MichiganMaterialCatalog,
    logistics: &CatalogLogistics,
) -> CatalogCapacity {
    if catalog.duration() == CampaignDuration::Continuous {
        CatalogCapacity::Rolling(RollingProcessSupply::CapturedNameplate(
            catalog
                .processes()
                .iter()
                .map(|p| InstalledProcessCapacity {
                    process_id: p.id(),
                    site_id: p.site_id(),
                    batches_per_period: p.capacity_batches_per_period,
                })
                .collect(),
        ))
    } else {
        let periods = catalog.duration().final_period().unwrap_or(0);
        CatalogCapacity::Finite {
            process: catalog
                .processes()
                .iter()
                .flat_map(|p| {
                    (1..=periods).map(move |period| CapacityRow {
                        process_id: p.id(),
                        site_id: p.site_id(),
                        period,
                        available_batches: p.capacity_batches_per_period,
                    })
                })
                .collect(),
            freight: logistics
                .shared_capacity
                .iter()
                .flat_map(|c| {
                    (1..=periods).map(move |period| CorridorCapacity {
                        corridor_id: c.corridor_id,
                        period,
                        available_grams: c.grams_per_period,
                    })
                })
                .collect(),
        }
    }
}
fn import_maintenance(catalog: &MichiganMaterialCatalog) -> Result<Option<CatalogMaintenance>> {
    catalog
        .maintenance()
        .map(|m| {
            let site = catalog
                .site(&m.provider_site_key)
                .ok_or(EconomicCatalogError::Opening("maintenance provider"))?;
            let process = catalog
                .processes()
                .iter()
                .find(|p| p.key == m.consumer_process_key)
                .ok_or(EconomicCatalogError::Opening("maintenance consumer"))?;
            let spare = good(catalog, &m.spare_good_key, 0)?;
            Ok(CatalogMaintenance {
                binding: MaintenanceBinding {
                    provider_site_id: site.id(),
                    consumer_process_id: process.id(),
                    spare_good_id: spare.good_id,
                    spare_unit_id: spare.unit_id,
                    labor_unit_id: labor_unit(),
                    spare_units_per_job: m.spare_units_per_job,
                    labor_units_per_job: m.labor_units_per_job,
                    enabled_batches_per_job: m.enabled_batches_per_job,
                    maximum_jobs_per_period: m.maximum_jobs_per_period,
                },
                opening_enabled_batches: m.opening_service_batches,
            })
        })
        .transpose()
}
