use super::model::{
    CargoClass, FlowEvidence, TransportFacility, TransportFlows, TransportLink, TransportNodeKind,
    TransportPool, TransportService, TransportSource,
};
use serde::Deserialize;
use std::collections::BTreeMap;

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct Document {
    pub schema: String,
    pub policy: Policy,
    pub policy_sha256: String,
    pub nodes: Vec<Node>,
    pub links: Vec<TransportLink>,
    pub pools: Vec<TransportPool>,
    pub county_access: Vec<CountyAccess>,
    pub county_factors: Vec<[String; 7]>,
    pub facilities: Vec<TransportFacility>,
    pub border_inbound_2024: Vec<BTreeMap<String, String>>,
    pub audit: Audit,
    pub flows: TransportFlows,
    pub sources: Vec<TransportSource>,
}
#[derive(Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub(super) struct Policy {
    pub contract: String,
    pub issue: String,
    pub evidence_class: String,
    pub period_days: u16,
    pub bounds: BTreeMap<String, u64>,
    pub cargo_classes: Vec<CargoClass>,
    pub trunk_counties: Vec<String>,
    pub airport_overrides: BTreeMap<String, String>,
    pub anchor_airports: Vec<String>,
    pub marine_gateways: BTreeMap<String, u32>,
    pub counterpart_gateways: BTreeMap<String, Vec<String>>,
    pub dependency_airports: BTreeMap<String, String>,
    pub dependency_services: Vec<[String; 2]>,
    pub service_profiles: BTreeMap<String, TransportService>,
    pub semantics: BTreeMap<String, String>,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct Node {
    pub id: String,
    pub kind: TransportNodeKind,
    pub location: String,
    pub latitude: Option<String>,
    pub longitude: Option<String>,
    pub source_id: String,
    pub source_key: String,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct CountyAccess {
    pub county: String,
    pub zone: String,
    pub airport: Option<String>,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct Audit {
    pub general_diameter: usize,
    pub general_targets: usize,
    pub unavailable_bulk_counties: Vec<BulkAccess>,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct BulkAccess {
    pub county: String,
    pub cargo: CargoClass,
    pub can_receive: bool,
    pub can_supply: bool,
}

pub(super) fn flow_collections(flows: &TransportFlows) -> [(&[FlowEvidence], usize); 3] {
    [
        (&flows.domestic, 4),
        (&flows.foreign, 5),
        (&flows.controls, 3),
    ]
}
