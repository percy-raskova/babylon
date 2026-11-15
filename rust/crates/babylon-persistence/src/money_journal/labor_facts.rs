//! Deterministic native labor facts and their captured scopes, shared by publication and replay.
use super::JournalError;
use crate::economic_content::EconomicContentAdmission;
use crate::economic_flows::{self, FlowAccount};
use crate::money_journal::MoneyEndpoint;
use crate::qualification_audit::trade;
use crate::recorded_labor::{
    LaborDisposition, LaborId, LaborNode, LaborReceiptFamily, RecordedAssetIdentity,
    RecordedLaborPeriod,
};
use babylon_kernel::economic_identity::EconomicFunction;
use babylon_material_circuit::{AccountId, FinalDemandPrincipalId, SiteId};
use serde::{Serialize, Serializer};
use std::collections::{BTreeMap, BTreeSet};
use std::fmt::Display;

fn decimal<T: Display, S: Serializer>(v: &T, s: S) -> Result<S::Ok, S::Error> {
    s.collect_str(v)
}
#[expect(
    clippy::ref_option,
    reason = "serde passes a reference to the optional field to serialize_with"
)]
fn bytea<S: Serializer>(id: &Option<LaborId>, s: S) -> Result<S::Ok, S::Error> {
    match id {
        Some(id) => s.serialize_str(&format!("\\x{}", trade::hex(&id.0))),
        None => s.serialize_none(),
    }
}

#[derive(Debug, Clone, Serialize, Default)]
pub(crate) struct LaborNodeFact {
    pub node_ordinal: i64,
    pub kind: &'static str,
    #[serde(serialize_with = "bytea")]
    pub entity_id: Option<LaborId>,
    #[serde(serialize_with = "bytea")]
    pub good_id: Option<LaborId>,
    #[serde(serialize_with = "bytea")]
    pub unit_id: Option<LaborId>,
    pub purpose: Option<LaborDisposition>,
    pub scope_kind: Option<&'static str>,
    #[serde(serialize_with = "bytea")]
    pub scope_id: Option<LaborId>,
    #[serde(serialize_with = "bytea")]
    pub process_id: Option<LaborId>,
    #[serde(serialize_with = "bytea")]
    pub route_id: Option<LaborId>,
    #[serde(serialize_with = "bytea")]
    pub origin_id: Option<LaborId>,
    #[serde(serialize_with = "bytea")]
    pub destination_id: Option<LaborId>,
    pub location_key: Option<String>,
    pub catchment_key: Option<String>,
    pub industry_key: Option<String>,
    pub industry_label: Option<&'static str>,
    pub longitude: Option<String>,
    pub latitude: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
pub(crate) struct LaborMovementFact {
    pub ordinal: i64,
    pub source_node: i64,
    pub destination_node: i64,
    pub receipt_family: LaborReceiptFamily,
    pub receipt_ordinal: i64,
    #[serde(serialize_with = "decimal")]
    pub quantity: u64,
    #[serde(serialize_with = "decimal")]
    pub recorded_micro_hours: u128,
    pub unknown_opening: bool,
}
#[derive(Debug, Clone, Serialize)]
pub(crate) struct LaborPositionFact {
    pub side: &'static str,
    pub node_ordinal: i64,
    #[serde(serialize_with = "decimal")]
    pub quantity: u64,
    #[serde(serialize_with = "decimal")]
    pub recorded_micro_hours: u128,
    pub unknown_opening: bool,
}

pub(crate) struct LaborFacts {
    pub nodes: Vec<LaborNodeFact>,
    pub movements: Vec<LaborMovementFact>,
    pub positions: Vec<LaborPositionFact>,
    pub opening: u128,
    pub closing: u128,
    pub direct: u128,
    pub released: u128,
}

fn freight_details(
    fact: &mut LaborNodeFact,
    detail: &RecordedAssetIdentity,
) -> Result<&'static str, JournalError> {
    let (name, origin, destination, route, good, unit) = match *detail {
        RecordedAssetIdentity::CommercialFreight {
            source_site,
            destination_site,
            route,
            good,
            unit,
            ..
        } => (
            "commercial_freight",
            source_site,
            destination_site,
            route,
            good,
            unit,
        ),
        RecordedAssetIdentity::AidFreight {
            donor,
            recipient,
            route,
            good,
            unit,
            ..
        } => ("aid_freight", donor, recipient, route, good, unit),
        RecordedAssetIdentity::ProductiveEquipment { .. } => return Err(JournalError::Projection),
    };
    (
        fact.origin_id,
        fact.destination_id,
        fact.route_id,
        fact.good_id,
        fact.unit_id,
    ) = (
        Some(origin),
        Some(destination),
        Some(route),
        Some(good),
        Some(unit),
    );
    Ok(name)
}

fn describe(
    node: LaborNode,
    assets: &BTreeMap<LaborNode, RecordedAssetIdentity>,
    processes: &BTreeMap<LaborId, LaborId>,
) -> Result<(LaborNodeFact, Option<AccountId>), JournalError> {
    let mut fact = LaborNodeFact::default();
    let site = |id: LaborId| Some(AccountId::Site(SiteId::from_bytes(id.0)));
    let household = |id: LaborId| {
        Some(AccountId::Household(FinalDemandPrincipalId::from_bytes(
            id.0,
        )))
    };
    let (kind, id, owner) = match node {
        LaborNode::SiteStock {
            site: id,
            good,
            unit,
        } => {
            fact.good_id = Some(good);
            fact.unit_id = Some(unit);
            ("site_stock", Some(id), site(id))
        }
        LaborNode::HouseholdStock {
            household: id,
            good,
            unit,
        } => {
            fact.good_id = Some(good);
            fact.unit_id = Some(unit);
            ("household_stock", Some(id), household(id))
        }
        LaborNode::Work { site: id, unit } => {
            fact.unit_id = Some(unit);
            ("work", Some(id), site(id))
        }
        LaborNode::HouseholdWork {
            household: id,
            unit,
        } => {
            fact.unit_id = Some(unit);
            ("household_work", Some(id), household(id))
        }
        LaborNode::Process { process } | LaborNode::Maintenance { process } => {
            fact.process_id = Some(process);
            let local = processes.get(&process).ok_or(JournalError::Projection)?;
            (
                if matches!(node, LaborNode::Process { .. }) {
                    "process"
                } else {
                    "maintenance"
                },
                Some(process),
                site(*local),
            )
        }
        LaborNode::Sink { purpose } => {
            fact.purpose = Some(purpose);
            ("sink", None, None)
        }
        LaborNode::Freight { lot } => {
            let detail = assets.get(&node).ok_or(JournalError::Projection)?;
            (freight_details(&mut fact, detail)?, Some(lot), None)
        }
        LaborNode::Equipment { cohort: id } | LaborNode::Installation { installation: id } => {
            let Some(RecordedAssetIdentity::ProductiveEquipment {
                site: local,
                process,
                good,
                unit,
                ..
            }) = assets.get(&node)
            else {
                return Err(JournalError::Projection);
            };
            fact.process_id = Some(*process);
            fact.good_id = Some(*good);
            fact.unit_id = Some(*unit);
            (
                if matches!(node, LaborNode::Equipment { .. }) {
                    "equipment"
                } else {
                    "installation"
                },
                Some(id),
                site(*local),
            )
        }
    };
    fact.kind = kind;
    fact.entity_id = id;
    Ok((fact, owner))
}

impl LaborNodeFact {
    fn apply_scope(&mut self, source: &FlowAccount) -> Result<(), JournalError> {
        self.scope_kind = Some(source.account.kind.as_str());
        self.scope_id = Some(LaborId(source.account.id));
        self.location_key.clone_from(&source.location);
        self.catchment_key.clone_from(&source.catchment);
        self.industry_key.clone_from(&source.industry);
        self.industry_label = source
            .industry
            .as_deref()
            .map(|s| {
                EconomicFunction::from_source_key(s)
                    .map(EconomicFunction::label)
                    .ok_or(JournalError::Projection)
            })
            .transpose()?;
        if let Some(point) = &source.county_internal_point {
            self.longitude = Some(point.longitude.clone());
            self.latitude = Some(point.latitude.clone());
        }
        Ok(())
    }
}
fn ordinal(value: usize) -> Result<i64, JournalError> {
    i64::try_from(value).map_err(|_| JournalError::Range)
}

impl LaborFacts {
    pub(crate) fn from_report(
        foundation: &EconomicContentAdmission,
        report: &RecordedLaborPeriod,
    ) -> Result<Self, JournalError> {
        let keys: BTreeSet<_> = report
            .edges
            .iter()
            .flat_map(|r| [r.source, r.destination])
            .chain(
                report
                    .opening_positions
                    .iter()
                    .chain(&report.closing_positions)
                    .map(|p| p.node),
            )
            .collect();
        let assets = report.assets.iter().map(|r| (r.node, r.identity)).collect();
        let processes = foundation
            .material_catalog()
            .process_outputs
            .iter()
            .map(|r| {
                (
                    LaborId(r.process_id.as_bytes()),
                    LaborId(r.site_id.as_bytes()),
                )
            })
            .collect();
        let catalog = foundation
            .foundation()
            .graph_foundation()
            .content_bundle()
            .economic_catalog()
            .ok_or(JournalError::Projection)?;
        let mut ids = BTreeMap::new();
        let mut staged = Vec::with_capacity(keys.len());
        let mut principals = BTreeSet::new();
        for (idx, node) in keys.into_iter().enumerate() {
            let (mut fact, principal) = describe(node, &assets, &processes)?;
            fact.node_ordinal = ordinal(idx)?;
            ids.insert(node, fact.node_ordinal);
            if let Some(id) = principal {
                principals.insert(id);
            }
            staged.push((fact, principal));
        }
        let geographies = economic_flows::geographies(catalog, principals.into_iter())
            .map_err(|_| JournalError::Projection)?;
        let scopes: BTreeMap<_, _> = geographies
            .iter()
            .map(|r| ((r.account.kind.as_str(), r.account.id), r))
            .collect();
        let mut nodes = Vec::with_capacity(staged.len());
        for (mut fact, principal) in staged {
            if let Some(id) = principal {
                let scope = MoneyEndpoint::from(id);
                fact.apply_scope(
                    scopes
                        .get(&(scope.kind.as_str(), scope.id))
                        .ok_or(JournalError::Projection)?,
                )?;
            }
            nodes.push(fact);
        }
        let movements = report
            .edges
            .iter()
            .enumerate()
            .map(|(i, r)| {
                Ok(LaborMovementFact {
                    ordinal: ordinal(i)?,
                    source_node: ids[&r.source],
                    destination_node: ids[&r.destination],
                    receipt_family: r.receipt.family,
                    receipt_ordinal: ordinal(r.receipt.ordinal)?,
                    quantity: r.quantity,
                    recorded_micro_hours: r.basis.recorded_micro_hours,
                    unknown_opening: r.basis.unknown_opening,
                })
            })
            .collect::<Result<_, JournalError>>()?;
        let positions = [
            ("opening", &report.opening_positions),
            ("closing", &report.closing_positions),
        ]
        .into_iter()
        .flat_map(|(side, rows)| rows.iter().map(move |row| (side, row)))
        .map(|(side, r)| LaborPositionFact {
            side,
            node_ordinal: ids[&r.node],
            quantity: r.quantity,
            recorded_micro_hours: r.basis.recorded_micro_hours,
            unknown_opening: r.basis.unknown_opening,
        })
        .collect();
        Ok(Self {
            nodes,
            movements,
            positions,
            opening: report.opening_recorded_micro_hours,
            closing: report.closing_recorded_micro_hours,
            direct: report.direct_micro_hours,
            released: report.released_micro_hours,
        })
    }
}
