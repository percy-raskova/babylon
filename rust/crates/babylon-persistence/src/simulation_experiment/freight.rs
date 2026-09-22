//! Explicit external inventory and Detroit port entry, without county attribution.
use super::{
    product, sum, ExperimentError, ExperimentProfile, Result, SimulationExperimentV1,
    StartingSnapshot,
};
use crate::material_runtime::{MaterialFoundationSpec, MaterialRuntimeFoundation};
use babylon_kernel::content_digest::sha256_of;
use babylon_material_circuit::{
    decode_material_circuit_state, encode_material_circuit_state, BacklogRow, CorridorCapacity,
    CorridorId, FreightMassCoefficient, GoodId, InventoryRow, LogisticsNodeId,
    MaterialCircuitState, OrderAccessMode, OrderId, OrderRow, RouteId, RouteStage,
    RouteStageCapacity, SiteId, SiteLogisticsNode, SupplierRoute, SupplierTransport, UnitId,
};
use babylon_tick::{material_staffing::StaffingComposition, material_world::MaterialWorldRegister};
use serde::{Deserialize, Serialize};

const SCENARIO: &str = "diagnostic/detroit-hs72-import-v1";
const RULES: &str = include_str!("../../../../../content/scenarios/michigan/material-cycle.bsl");
const BOUNDARY: &str =
    include_str!("../../../../../content/scenarios/michigan/diagnostic-freight-boundary.json");
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Boundary {
    schema: String,
    source_site: String,
    destination_site: String,
    commodity: String,
    unit: String,
    port_code: String,
    partner_code: String,
    mode_code: String,
    trade_type_code: String,
    hs_chapter: String,
    geographic_scope: String,
    inventory_evidence: String,
    order_evidence: String,
    capacity_evidence: String,
}
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct CapturedFreight {
    schema: String,
    experiment: SimulationExperimentV1,
    boundary: Boundary,
    travel_periods: u16,
    transport_defines_sha256: String,
    capacity_kg_per_period: u64,
    ordered_kg: u64,
    opening_inventory_kg: u64,
}
fn id(kind: &str) -> [u8; 32] {
    sha256_of(format!("babylon.diagnostic.detroit-hs72.v1\0{kind}").as_bytes())
}
pub(super) fn good_id() -> GoodId {
    GoodId::from_bytes(id("hs72-iron-and-steel-aggregate"))
}
pub(super) fn destination_id() -> SiteId {
    SiteId::from_bytes(id("detroit-port-3801-entry"))
}
fn source_id() -> SiteId {
    SiteId::from_bytes(id("canadian-inventory-boundary"))
}
fn new_capture(spec: &SimulationExperimentV1) -> Result<CapturedFreight> {
    let boundary: Boundary =
        serde_json::from_str(BOUNDARY).map_err(|_| ExperimentError::Content)?;
    let defines = crate::michigan_defines::MichiganDefines::parse(include_str!(
        "../../../../../content/scenarios/michigan/defines.toml"
    ))
    .map_err(|_| ExperimentError::Content)?;
    let travel_periods = defines.transport.road_travel_periods;
    let transport_defines_sha256 = super::hex(&sha256_of(
        &serde_json::to_vec(&defines.transport).map_err(|_| ExperimentError::Content)?,
    ));
    let Some(StartingSnapshot::Freight { arrived_kg, .. }) = &spec.starting_snapshot else {
        return Err(ExperimentError::StartingSnapshot);
    };
    let base = product(*arrived_kg, babylon_kernel::clock::DAYS_PER_TICK)? / 31;
    let captured = CapturedFreight {
        schema: "DiagnosticFreightContentV1".to_owned(),
        experiment: spec.clone(),
        travel_periods,
        transport_defines_sha256,
        capacity_kg_per_period: product(base, spec.transport_permille())? / 1000,
        ordered_kg: product(base, spec.horizon)?,
        opening_inventory_kg: product(base, sum(spec.horizon, u64::from(travel_periods))?)?,
        boundary,
    };
    captured.validate()?;
    Ok(captured)
}
impl CapturedFreight {
    fn bytes(&self) -> Result<Vec<u8>> {
        serde_json::to_vec(self).map_err(|_| ExperimentError::Content)
    }
    fn validate(&self) -> Result<()> {
        self.experiment.validate()?;
        let b = &self.boundary;
        if self.schema != "DiagnosticFreightContentV1"
            || self.experiment.profile != ExperimentProfile::HistoricalFreight
            || b.schema != "DiagnosticFreightBoundaryV1"
            || b.source_site != "canadian-inventory-boundary"
            || b.destination_site != "detroit-port-3801-entry"
            || b.commodity != "hs72-iron-and-steel-aggregate"
            || b.unit != "kg"
            || b.port_code != "3801"
            || b.partner_code != "1220"
            || b.mode_code != "5"
            || b.trade_type_code != "2"
            || b.hs_chapter != "72"
            || b.geographic_scope != "portwide-without-county-or-bridge-attribution"
            || b.inventory_evidence != "Designed"
            || b.order_evidence != "Designed"
            || b.capacity_evidence != "Derived"
            || self.travel_periods != 1
            || !super::digest_valid(&self.transport_defines_sha256)
        {
            return Err(ExperimentError::Content);
        }
        let Some(StartingSnapshot::Freight { arrived_kg, .. }) = &self.experiment.starting_snapshot
        else {
            return Err(ExperimentError::StartingSnapshot);
        };
        let base = product(*arrived_kg, babylon_kernel::clock::DAYS_PER_TICK)? / 31;
        if self.capacity_kg_per_period
            != product(base, self.experiment.transport_permille())? / 1000
            || self.ordered_kg != product(base, self.experiment.horizon)?
            || self.opening_inventory_kg != product(base, sum(self.experiment.horizon, 1)?)?
            || self.capacity_kg_per_period == 0
        {
            return Err(ExperimentError::Content);
        }
        Ok(())
    }
    #[allow(clippy::too_many_lines)] // Keep the complete closed inventory boundary visible together.
    fn state(&self) -> Result<MaterialCircuitState> {
        self.validate()?;
        let source = source_id();
        let destination = destination_id();
        let good = good_id();
        let unit = UnitId::from_bytes(id("kg"));
        let route = RouteId::from_bytes(id("canada-to-detroit-port"));
        let corridor = CorridorId::from_bytes(id("truck-import-capacity"));
        let order = OrderId::from_bytes(id("finite-import-order"));
        let from = LogisticsNodeId::from_bytes(id("canadian-inventory-terminal"));
        let to = LogisticsNodeId::from_bytes(id("detroit-port-entry-terminal"));
        let state = MaterialCircuitState {
            period: 1,
            site_logistics_nodes: vec![
                SiteLogisticsNode {
                    site_id: source,
                    node_id: from,
                },
                SiteLogisticsNode {
                    site_id: destination,
                    node_id: to,
                },
            ],
            process_outputs: vec![],
            input_coefficients: vec![],
            labor_coefficients: vec![],
            capacities: vec![],
            labor: vec![],
            production_commitments: vec![],
            merchants: vec![],
            handling_coefficients: vec![],
            final_demand_principals: vec![],
            final_demand_orders: vec![],
            accounting: babylon_material_circuit::CircuitAccounting::PhysicalControl,
            maintenance_binding: None,
            maintenance_service: None,
            freight_mass_coefficients: vec![FreightMassCoefficient {
                good_id: good,
                unit_id: unit,
                grams_per_unit: 1000,
            }],
            supplier_routes: vec![SupplierRoute {
                buyer_site_id: destination,
                supplier_site_id: source,
                good_id: good,
                unit_id: unit,
                route_id: route,
                transport_kind: SupplierTransport::Staged,
            }],
            route_stages: vec![RouteStage {
                route_id: route,
                stage_index: 0,
                from_node_id: from,
                to_node_id: to,
                travel_periods: self.travel_periods,
                loss_ppm: 0,
            }],
            route_stage_capacities: vec![RouteStageCapacity {
                route_id: route,
                stage_index: 0,
                corridor_id: corridor,
            }],
            inventory: vec![
                InventoryRow {
                    site_id: source,
                    good_id: good,
                    unit_id: unit,
                    quantity: self.opening_inventory_kg,
                },
                InventoryRow {
                    site_id: destination,
                    good_id: good,
                    unit_id: unit,
                    quantity: 0,
                },
            ],
            orders: vec![OrderRow {
                order_id: order,
                access_mode: OrderAccessMode::CommoditySale,
                buyer_site_id: destination,
                supplier_site_id: source,
                good_id: good,
                unit_id: unit,
                ordered: self.ordered_kg,
                shipped: 0,
                lost: 0,
                delivered: 0,
                realized: 0,
            }],
            backlog: vec![BacklogRow {
                order_id: order,
                quantity: self.ordered_kg,
            }],
            freight: vec![],
            corridor_capacities: (1..=self.experiment.horizon)
                .map(|period| {
                    Ok(CorridorCapacity {
                        corridor_id: corridor,
                        period,
                        available_grams: product(self.capacity_kg_per_period, 1000)?,
                    })
                })
                .collect::<Result<Vec<_>>>()?,
        };
        decode_material_circuit_state(
            &encode_material_circuit_state(&state).map_err(|_| ExperimentError::Content)?,
        )
        .map_err(|_| ExperimentError::Content)
    }
}
fn scenario() -> String {
    use std::fmt::Write;
    let mut text=format!("(scenario {SCENARIO}\n  (defvocabulary NodeType (INVENTORY_BOUNDARY PORT_ENTRY SOCIAL_CLASS))\n");
    for field in babylon_tick::material_staffing::STAFFING_FIELDS {
        writeln!(&mut text, "  (deffield {field} int extensive)").expect("String write");
    }
    text.push_str("  (node canadian-inventory-boundary NodeType/INVENTORY_BOUNDARY)\n  (node detroit-port-3801-entry NodeType/PORT_ENTRY)\n)\n");
    text
}
pub(super) fn foundation(spec: &SimulationExperimentV1) -> Result<MaterialRuntimeFoundation> {
    let captured = new_capture(spec)?;
    let defines = captured.bytes()?;
    let state = captured.state()?;
    let (graph, bundle) = crate::michigan_economy::foundation_from_sources_with_seed(
        &scenario(),
        RULES,
        "diagnostic/detroit-hs72-import-v1",
        &defines,
        spec.seed,
    )
    .map_err(|_| ExperimentError::Foundation)?;
    MaterialRuntimeFoundation::capture(
        graph,
        bundle,
        state,
        MaterialFoundationSpec {
            preset_id: spec.profile.foundation_id().to_owned(),
            horizon_ticks: spec.horizon,
            content_digest: sha256_of(&defines),
        },
    )
    .map_err(|_| ExperimentError::Foundation)
}
pub(super) fn validate_authority(
    graph: &crate::CampaignFoundation,
    register: &MaterialWorldRegister,
    spec: &MaterialFoundationSpec,
) -> Result<StaffingComposition> {
    let bytes = graph.content_bundle().defines_bytes();
    if bytes.len() > super::MAX_EXPERIMENT_INPUT_BYTES {
        return Err(ExperimentError::Content);
    }
    let captured: CapturedFreight =
        serde_json::from_slice(bytes).map_err(|_| ExperimentError::Content)?;
    captured.validate()?;
    if captured.bytes() != Ok(bytes.to_vec())
        || spec.preset_id != captured.experiment.profile.foundation_id()
        || spec.horizon_ticks != captured.experiment.horizon
        || spec.content_digest != sha256_of(bytes)
        || graph.rng_seed() != babylon_kernel::replay::ReplaySeed::new(captured.experiment.seed)
        || graph.content_bundle().scenario_source_bytes() != scenario().as_bytes()
        || graph.content_bundle().rule_source_bytes() != RULES.as_bytes()
        || register.organizer_config().is_some()
        || register.state() != &captured.state()?
    {
        return Err(ExperimentError::Foundation);
    }
    StaffingComposition::inventory_only(register.state()).map_err(|_| ExperimentError::Foundation)
}

pub(super) fn resolved_setup(bytes: &[u8]) -> Result<super::setup::FreightSetup> {
    let c: CapturedFreight = serde_json::from_slice(bytes).map_err(|_| ExperimentError::Content)?;
    c.validate()?;
    let Some(StartingSnapshot::Freight { arrived_kg, .. }) = c.experiment.starting_snapshot else {
        return Err(ExperimentError::StartingSnapshot);
    };
    let b = c.boundary;
    Ok(super::setup::FreightSetup{source_site:b.source_site,destination_site:b.destination_site,commodity:b.commodity,unit:b.unit,port_code:b.port_code,partner_code:b.partner_code,mode_code:b.mode_code,trade_type_code:b.trade_type_code,hs_chapter:b.hs_chapter,geographic_scope:b.geographic_scope,january_observed_kg:arrived_kg,capacity_derivation:"floor(January observed kg * 28 / 31); optional Designed transport permille is then multiplied and floored by /1000",capacity_kg_per_period:c.capacity_kg_per_period,ordered_kg:c.ordered_kg,opening_inventory_kg:c.opening_inventory_kg,travel_periods:c.travel_periods,inventory_evidence:b.inventory_evidence,order_evidence:b.order_evidence,capacity_evidence:b.capacity_evidence,inventory_derivation:"base period capacity * (horizon + travel periods), finite and Designed",order_derivation:"base period capacity * horizon, finite and Designed"})
}
