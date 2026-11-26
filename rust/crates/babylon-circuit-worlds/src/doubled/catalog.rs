//! The catalog of the doubled world: what each workplace makes, takes and handles.

use crate::doubled::figures::{self, Figures};
use crate::doubled::world::World;
use crate::ids;
use crate::{Good, Kind, Place, Workplace, WorldError};
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    AdjustmentRule, CapacitySupply, CommodityDefinition, CommodityKind, HouseholdNeed,
    HouseholdNeedBasis, HouseholdWant, InputOutputCoefficient, LaborCoefficient, LogisticsNodeId,
    MarketClearingPolicy, MaterialCatalog, MaterialCatalogDefinition, MerchantHandling,
    MerchantHandlingCoefficient, MerchantRole, ProcessOutput, ServiceInputPolicy, ServiceStage,
    SiteLogisticsNode, SupplierRoute, SupplierTransport, WantTier,
};

/// Units of power a farm batch takes, and the farm's hours a batch.
pub(crate) const FARM_BATCH_INPUT: u64 = 10;

/// What a farm of one place has planned at the opening: four batches.
pub(crate) const FARM_OPENING_BATCHES: u64 = 4;

/// The scene's catalog, with the given figures of production.
///
/// # Errors
/// As `catalog_of`.
pub fn catalog(figures: &Figures) -> Result<MaterialCatalog, WorldError> {
    catalog_of(&World::scene(), figures, &[])
}

/// The catalog of a world, with the given figures of production and the rules its market policy asks for.
///
/// # Errors
/// `WorldError::Engine` when the engine refuses the catalog or its rules, `WorldError::Location` when the
/// place does not parse, `WorldError::Arithmetic` when a figure overflows.
pub fn catalog_of(
    world: &World,
    figures: &Figures,
    rules: &[AdjustmentRule],
) -> Result<MaterialCatalog, WorldError> {
    Ok(MaterialCatalog::try_new(definition(
        world, figures, rules,
    )?)?)
}

fn commodities() -> Vec<CommodityDefinition> {
    let mut rows = vec![
        CommodityDefinition {
            good_id: Good::Food.good_id(),
            unit_id: ids::goods_unit(),
            kind: CommodityKind::Storable { grams_per_unit: 1 },
        },
        CommodityDefinition {
            good_id: Good::Power.good_id(),
            unit_id: ids::goods_unit(),
            kind: CommodityKind::PeriodService {
                stage: ServiceStage::UtilityProvision,
            },
        },
        CommodityDefinition {
            good_id: Good::Care.good_id(),
            unit_id: ids::goods_unit(),
            kind: CommodityKind::PeriodService {
                stage: ServiceStage::LocalServiceProvision,
            },
        },
    ];
    rows.sort_by_key(|row| (row.good_id, row.unit_id));
    rows
}

fn workplace(place: Place, kind: Kind) -> Workplace {
    Workplace { place, kind }
}

fn process_outputs(figures: &Figures) -> Vec<ProcessOutput> {
    let mut rows = Vec::new();
    for place in Place::ALL {
        let i = place.index();
        for (kind, good, quantity_per_batch) in [
            (
                Kind::Utility,
                Good::Power,
                figures.utility_output_per_batch[i],
            ),
            (Kind::Farm, Good::Food, figures.farm_yield[i]),
            (Kind::Clinic, Good::Care, 1),
        ] {
            let w = workplace(place, kind);
            if let Some(process_id) = w.process_id() {
                rows.push(ProcessOutput {
                    process_id,
                    site_id: w.site_id(),
                    good_id: good.good_id(),
                    unit_id: ids::goods_unit(),
                    quantity_per_batch,
                });
            }
        }
    }
    rows
}

fn input_coefficients() -> Vec<InputOutputCoefficient> {
    let mut rows = Vec::new();
    for place in Place::ALL {
        for (kind, quantity_per_batch) in [(Kind::Farm, FARM_BATCH_INPUT), (Kind::Clinic, 1)] {
            if let Some(process_id) = workplace(place, kind).process_id() {
                rows.push(InputOutputCoefficient {
                    process_id,
                    good_id: Good::Power.good_id(),
                    unit_id: ids::goods_unit(),
                    quantity_per_batch,
                });
            }
        }
    }
    rows
}

fn labor_coefficients(figures: &Figures) -> Vec<LaborCoefficient> {
    let mut rows = Vec::new();
    for place in Place::ALL {
        for (kind, quantity_per_batch) in [
            (
                Kind::Utility,
                figures.utility_hours_per_batch[place.index()],
            ),
            (Kind::Farm, FARM_BATCH_INPUT),
            (Kind::Clinic, 1),
        ] {
            if let Some(process_id) = workplace(place, kind).process_id() {
                rows.push(LaborCoefficient {
                    process_id,
                    unit_id: ids::hours_unit(),
                    quantity_per_batch,
                });
            }
        }
    }
    rows
}

fn household_needs(world: &World) -> Vec<HouseholdNeed> {
    let mut rows = Vec::new();
    for household in world.households() {
        for good in Good::ALL {
            rows.push(HouseholdNeed {
                principal_id: household.principal(),
                good_id: good.good_id(),
                unit_id: ids::goods_unit(),
                basis: HouseholdNeedBasis::Persons,
                units_per_basis: 1,
            });
        }
    }
    rows.sort_by_key(|row| (row.principal_id, row.good_id, row.unit_id));
    rows
}

fn household_wants(world: &World) -> Vec<HouseholdWant> {
    let mut rows = Vec::new();
    for household in world.households() {
        for (tier, good) in [
            (WantTier::Comfort, Good::Care),
            (WantTier::Luxury, Good::Food),
            (WantTier::Luxury, Good::Power),
        ] {
            rows.push(HouseholdWant {
                principal_id: household.principal(),
                tier,
                good_id: good.good_id(),
                unit_id: ids::goods_unit(),
                basis: HouseholdNeedBasis::Persons,
                units_per_basis: 1,
                scale_bps: babylon_material_circuit::WANT_SCALE_ONE_BPS,
            });
        }
    }
    rows.sort_by_key(|row| (row.principal_id, row.tier, row.good_id, row.unit_id));
    rows
}

fn market_clearing(world: &World, rules: &[AdjustmentRule]) -> MarketClearingPolicy {
    MarketClearingPolicy {
        paying_order: Good::ALL
            .iter()
            .map(|g| (g.good_id(), ids::goods_unit()))
            .collect(),
        household_wants: household_wants(world),
        plans_from_spare_money: true,
        adjustments: rules.to_vec(),
    }
}

fn supplier_routes() -> Vec<SupplierRoute> {
    Place::ALL
        .iter()
        .map(|&place| SupplierRoute {
            buyer_site_id: workplace(place, Kind::Shop).site_id(),
            supplier_site_id: workplace(place, Kind::Farm).site_id(),
            good_id: Good::Food.good_id(),
            unit_id: ids::goods_unit(),
            route_id: ids::route(place),
            transport_kind: SupplierTransport::Local,
        })
        .collect()
}

fn merchants() -> Result<Vec<MerchantHandling>, WorldError> {
    let place = ids::location()?;
    Ok(Place::ALL
        .iter()
        .map(|&p| MerchantHandling {
            site_id: workplace(p, Kind::Shop).site_id(),
            location: place,
            role: MerchantRole::Retail,
            capacity_id: ids::corridor(p),
            labor_unit_id: ids::hours_unit(),
        })
        .collect())
}

fn handling_coefficients() -> Vec<MerchantHandlingCoefficient> {
    Place::ALL
        .iter()
        .map(|&p| MerchantHandlingCoefficient {
            site_id: workplace(p, Kind::Shop).site_id(),
            good_id: Good::Food.good_id(),
            unit_id: ids::goods_unit(),
            hours_per_unit: 1,
            units: 1,
        })
        .collect()
}

/// The farm and the clinic of a place buy power from its utility; the caps are twice the
/// opening requirement (the farm's 40 units, the clinic's 40), so they never bind.
fn service_inputs(world: &World) -> Result<Vec<ServiceInputPolicy>, WorldError> {
    let farm_need = FARM_OPENING_BATCHES
        .checked_mul(FARM_BATCH_INPUT)
        .ok_or(WorldError::Arithmetic)?;
    let mut rows = Vec::new();
    for place in Place::ALL {
        let clinic_need = figures::place_persons(world, place)?;
        for (kind, need) in [(Kind::Farm, farm_need), (Kind::Clinic, clinic_need)] {
            let cap = need.checked_mul(2).ok_or(WorldError::Arithmetic)?;
            rows.push(ServiceInputPolicy {
                buyer_site_id: workplace(place, kind).site_id(),
                provider_site_id: workplace(place, Kind::Utility).site_id(),
                good_id: Good::Power.good_id(),
                unit_id: ids::goods_unit(),
                quantity_per_period: cap,
                maximum_purchase: cap,
                cash_floor: Currency::from_micro_units(0),
            });
        }
    }
    Ok(rows)
}

fn definition(
    world: &World,
    figures: &Figures,
    rules: &[AdjustmentRule],
) -> Result<MaterialCatalogDefinition, WorldError> {
    Ok(MaterialCatalogDefinition {
        market_clearing: Some(market_clearing(world, rules)),
        capacity_policy: CapacitySupply::FiniteSchedule,
        site_logistics_nodes: Workplace::ALL
            .iter()
            .map(|w| SiteLogisticsNode {
                site_id: w.site_id(),
                node_id: LogisticsNodeId::from_bytes(w.site_id().as_bytes()),
            })
            .collect(),
        process_outputs: process_outputs(figures),
        input_coefficients: input_coefficients(),
        labor_coefficients: labor_coefficients(figures),
        commodities: commodities(),
        supplier_routes: supplier_routes(),
        route_stages: vec![],
        merchants: merchants()?,
        handling_coefficients: handling_coefficients(),
        company_portfolios: None,
        company_payouts: vec![],
        maintenance_binding: None,
        aid_mandates: vec![],
        household_time_policy: vec![],
        service_inputs: service_inputs(world)?,
        household_needs: household_needs(world),
    })
}
