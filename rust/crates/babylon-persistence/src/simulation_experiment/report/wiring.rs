//! Captured selections and observed receipts, without inferring new mechanics.
use super::{ExperimentError, Result, StaffingEvidence};
use crate::material_runtime::MaterialRuntimeFoundation;
use babylon_bsl::causal_contract::{
    check_rule_contract, effect_footprint, EffectSignature, EvidenceClass, RuleRole, ShapeVerb,
    GOVERNED_RULE_ATTRIBUTIONS,
};
use babylon_bsl::rule_pipeline::split_content;
use babylon_graph::stable_element::StableElementKey;
use babylon_material_circuit::SupplierTransport;
use babylon_tick::{
    material_staffing::{STAFFING_COMPOSITION_ID, STAFFING_FIELDS},
    material_world::MaterialTickReceipts,
    TickReport,
};
use serde::Serialize;
use std::collections::BTreeMap;

#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct RuleAttribution {
    pub rule_id: String,
    pub role: &'static str,
    pub evidence: &'static str,
    pub effects: Vec<String>,
}
#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct BslFamily {
    pub family: String,
    pub selected: bool,
    pub rule_ids: Vec<String>,
}
#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct MaterialFamily {
    pub family: &'static str,
    pub selected: bool,
    pub captured_rows: u64,
}
#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct WiringManifest {
    pub rules: Vec<RuleAttribution>,
    /// Native child effects; these are not additional BSL invocations.
    pub native_compositions: Vec<RuleAttribution>,
    /// Selection against the governance roster, not an implementation inventory.
    pub bsl_families: Vec<BslFamily>,
    pub material_families: Vec<MaterialFamily>,
    pub staffing_subjects: Vec<String>,
}
#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct RuleExecution {
    pub rule_id: String,
    pub considered: u64,
    pub fired: u64,
    pub audit_receipts: u64,
}
#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct ReceiptCoverage {
    pub material_cycles: u64,
    pub staffing_events: u64,
    pub staffing_writes: u64,
    pub production: u64,
    pub dispatches: u64,
    pub losses: u64,
    pub arrivals: u64,
    pub deliveries: u64,
    pub realizations: u64,
    pub merchant_handling: u64,
    pub local_fulfillments: u64,
    pub local_transfers: u64,
    pub maintenance: u64,
}

fn count(value: usize) -> Result<u64> {
    u64::try_from(value).map_err(|_| ExperimentError::Arithmetic)
}
fn role_name(role: RuleRole) -> &'static str {
    match role {
        RuleRole::Mechanic => "mechanic",
        RuleRole::Recognizer => "recognizer",
        RuleRole::ExternalEvent => "external-event",
        RuleRole::Intent => "intent",
    }
}
fn evidence_name(evidence: EvidenceClass) -> &'static str {
    match evidence {
        EvidenceClass::Observed => "observed",
        EvidenceClass::Derived => "derived",
        EvidenceClass::Calibrated => "calibrated",
        EvidenceClass::Designed => "designed",
    }
}
fn effect_name(effect: &EffectSignature) -> String {
    match effect {
        EffectSignature::MaterialCycle => "material-cycle".to_owned(),
        EffectSignature::OrganizerProducts => "organizer-products".to_owned(),
        EffectSignature::OrganizerPractice => "organizer-practice".to_owned(),
        EffectSignature::NodeField(field) => format!("node-field:{field}"),
        EffectSignature::EdgeField(field) => format!("edge-field:{field}"),
        EffectSignature::HyperedgeField(field) => format!("hyperedge-field:{field}"),
        EffectSignature::Event(event) => format!("event:{event}"),
        EffectSignature::Shape(verb) => format!(
            "shape:{}",
            match verb {
                ShapeVerb::AddNode => "add-node",
                ShapeVerb::RemoveNode => "remove-node",
                ShapeVerb::AddEdge => "add-edge",
                ShapeVerb::RemoveEdge => "remove-edge",
                ShapeVerb::AddHyperedge => "add-hyperedge",
                ShapeVerb::RemoveHyperedge => "remove-hyperedge",
            }
        ),
    }
}
fn attribution(
    id: &str,
    role: RuleRole,
    evidence: EvidenceClass,
    effects: &[EffectSignature],
) -> RuleAttribution {
    let mut effects = effects.iter().map(effect_name).collect::<Vec<_>>();
    effects.sort();
    effects.dedup();
    RuleAttribution {
        rule_id: id.to_owned(),
        role: role_name(role),
        evidence: evidence_name(evidence),
        effects,
    }
}

pub(super) fn capture(foundation: &MaterialRuntimeFoundation) -> Result<WiringManifest> {
    let source = std::str::from_utf8(
        foundation
            .graph_foundation()
            .content_bundle()
            .rule_source_bytes(),
    )
    .map_err(|_| ExperimentError::Content)?;
    let (_, forms) = split_content(source).map_err(|_| ExperimentError::Content)?;
    let mut rules = forms
        .iter()
        .map(|form| {
            let contract = check_rule_contract(&form.form).map_err(|_| ExperimentError::Content)?;
            let effects = effect_footprint(&form.form).map_err(|_| ExperimentError::Content)?;
            Ok(attribution(
                &contract.rule_id,
                contract.role,
                contract.evidence,
                &effects,
            ))
        })
        .collect::<Result<Vec<_>>>()?;
    rules.sort_by(|a, b| a.rule_id.cmp(&b.rule_id));
    let mut families: BTreeMap<String, Vec<String>> = BTreeMap::new();
    for row in GOVERNED_RULE_ATTRIBUTIONS {
        if let Some((family, _)) = row.rule_id.split_once('/') {
            families.entry(family.to_owned()).or_default();
        }
    }
    for rule in &rules {
        let family = rule
            .rule_id
            .split_once('/')
            .map_or(rule.rule_id.as_str(), |(family, _)| family);
        families
            .entry(family.to_owned())
            .or_default()
            .push(rule.rule_id.clone());
    }
    let bsl_families = families
        .into_iter()
        .map(|(family, rule_ids)| BslFamily {
            family,
            selected: !rule_ids.is_empty(),
            rule_ids,
        })
        .collect();
    let mut staffing_subjects = foundation
        .labor()
        .bindings()
        .iter()
        .map(|binding| {
            let StableElementKey::Node { local_name, .. } = binding.subject() else {
                return Err(ExperimentError::Content);
            };
            Ok(local_name.clone())
        })
        .collect::<Result<Vec<_>>>()?;
    staffing_subjects.sort();
    if staffing_subjects.windows(2).any(|pair| pair[0] == pair[1]) {
        return Err(ExperimentError::Content);
    }
    let mut native_compositions = Vec::new();
    if !staffing_subjects.is_empty() {
        let governed = GOVERNED_RULE_ATTRIBUTIONS
            .iter()
            .find(|row| row.rule_id == STAFFING_COMPOSITION_ID)
            .ok_or(ExperimentError::Content)?;
        let effects = STAFFING_FIELDS
            .iter()
            .map(|field| EffectSignature::NodeField((*field).to_owned()))
            .chain(std::iter::once(EffectSignature::Event(
                "EventType/WORKFORCE_STAFFING".to_owned(),
            )))
            .collect::<Vec<_>>();
        native_compositions.push(attribution(
            governed.rule_id,
            governed.role,
            governed.evidence,
            &effects,
        ));
    }
    let material_families = material_families(foundation)?;
    Ok(WiringManifest {
        rules,
        native_compositions,
        bsl_families,
        material_families,
        staffing_subjects,
    })
}

fn material_families(foundation: &MaterialRuntimeFoundation) -> Result<Vec<MaterialFamily>> {
    let state = foundation.initial_register().state();
    [
        ("final_demand", state.final_demand_orders.len()),
        (
            "local_transfer",
            state
                .supplier_routes
                .iter()
                .filter(|r| r.transport_kind == SupplierTransport::Local)
                .count(),
        ),
        (
            "maintenance",
            usize::from(state.maintenance_binding.is_some()),
        ),
        ("merchant_handling", state.merchants.len()),
        ("production", state.process_outputs.len()),
        ("staffing", foundation.labor().bindings().len()),
        (
            "staged_freight",
            state
                .supplier_routes
                .iter()
                .filter(|r| r.transport_kind == SupplierTransport::Staged)
                .count(),
        ),
    ]
    .into_iter()
    .map(|(family, rows)| {
        Ok(MaterialFamily {
            family,
            selected: rows > 0,
            captured_rows: count(rows)?,
        })
    })
    .collect::<Result<Vec<_>>>()
}

fn counters(
    rows: &[(String, usize)],
    rules: &[RuleAttribution],
    total: usize,
) -> Result<BTreeMap<String, u64>> {
    let counters = rows
        .iter()
        .map(|(id, n)| Ok((id.clone(), count(*n)?)))
        .collect::<Result<BTreeMap<_, _>>>()?;
    if counters.len() != rows.len()
        || counters.len() != rules.len()
        || rules
            .iter()
            .any(|rule| !counters.contains_key(&rule.rule_id))
        || super::total(counters.values().copied())? != count(total)?
    {
        return Err(ExperimentError::Incomplete);
    }
    Ok(counters)
}

fn audit_coverage(manifest: &WiringManifest, report: &TickReport) -> Result<Vec<RuleExecution>> {
    let considered = counters(
        &report.per_rule_considered,
        &manifest.rules,
        report.considered,
    )?;
    let fired = counters(&report.per_rule_fired, &manifest.rules, report.fired)?;
    let mut audits: BTreeMap<(&str, String), u64> = BTreeMap::new();
    for receipt in &report.audit_receipts {
        let declared = manifest
            .rules
            .iter()
            .chain(&manifest.native_compositions)
            .find(|rule| rule.rule_id == receipt.rule_id)
            .ok_or(ExperimentError::Incomplete)?;
        let effect = effect_name(&receipt.effect);
        if declared.role != role_name(receipt.role)
            || declared.evidence != evidence_name(receipt.evidence)
            || !declared.effects.contains(&effect)
        {
            return Err(ExperimentError::Incomplete);
        }
        let n = audits.entry((&receipt.rule_id, effect)).or_default();
        *n = super::sum(*n, 1)?;
    }
    let execution = manifest
        .rules
        .iter()
        .map(|rule| {
            Ok(RuleExecution {
                rule_id: rule.rule_id.clone(),
                considered: considered[&rule.rule_id],
                fired: fired[&rule.rule_id],
                audit_receipts: count(
                    report
                        .audit_receipts
                        .iter()
                        .filter(|r| r.rule_id == rule.rule_id)
                        .count(),
                )?,
            })
        })
        .collect::<Result<Vec<_>>>()?;
    let mut material_rules = 0;
    for rule in &manifest.rules {
        if rule.effects.iter().any(|effect| effect == "material-cycle") {
            material_rules += 1;
            // Every admitted material invocation closes exactly one period.
            // The number of selected rules comes from captured source.
            if considered[&rule.rule_id] != 1
                || fired[&rule.rule_id] != 1
                || audits.get(&(rule.rule_id.as_str(), "material-cycle".to_owned())) != Some(&1)
            {
                return Err(ExperimentError::Incomplete);
            }
        }
    }
    if material_rules == 0 {
        return Err(ExperimentError::Incomplete);
    }
    for composition in &manifest.native_compositions {
        for effect in &composition.effects {
            if audits
                .get(&(composition.rule_id.as_str(), effect.clone()))
                .copied()
                .unwrap_or(0)
                != count(manifest.staffing_subjects.len())?
            {
                return Err(ExperimentError::Incomplete);
            }
        }
    }
    Ok(execution)
}

fn selected_families(manifest: &WiringManifest, coverage: &ReceiptCoverage) -> Result<()> {
    for (family, observed) in [
        ("final_demand", coverage.local_fulfillments),
        ("local_transfer", coverage.local_transfers),
        ("maintenance", coverage.maintenance),
        ("merchant_handling", coverage.merchant_handling),
        ("production", coverage.production),
        ("staffing", coverage.staffing_events),
        (
            "staged_freight",
            super::total(
                [
                    coverage.dispatches,
                    coverage.losses,
                    coverage.arrivals,
                    coverage.deliveries,
                    coverage.realizations,
                ]
                .into_iter(),
            )?,
        ),
    ] {
        let captured = manifest
            .material_families
            .iter()
            .find(|row| row.family == family)
            .ok_or(ExperimentError::Incomplete)?;
        if captured.selected != (captured.captured_rows > 0)
            || (!captured.selected && observed > 0)
            || (family == "maintenance" && observed != captured.captured_rows)
        {
            return Err(ExperimentError::Incomplete);
        }
    }
    Ok(())
}

pub(super) fn verify(
    manifest: &WiringManifest,
    report: &TickReport,
    receipts: &MaterialTickReceipts,
    staffing: &[StaffingEvidence],
) -> Result<(ReceiptCoverage, Vec<RuleExecution>)> {
    let execution = audit_coverage(manifest, report)?;
    if !staffing
        .iter()
        .map(|row| &row.subject)
        .eq(manifest.staffing_subjects.iter())
    {
        return Err(ExperimentError::Observation);
    }
    let events = report
        .committed_events
        .iter()
        .filter(|event| event.event_type() == "WORKFORCE_STAFFING")
        .collect::<Vec<_>>();
    if events.len() != staffing.len()
        || events
            .iter()
            .any(|event| event.emitting_rule() != STAFFING_COMPOSITION_ID)
    {
        return Err(ExperimentError::Observation);
    }
    let coverage = ReceiptCoverage {
        material_cycles: count(
            report
                .audit_receipts
                .iter()
                .filter(|r| r.effect == EffectSignature::MaterialCycle)
                .count(),
        )?,
        staffing_events: count(staffing.len())?,
        staffing_writes: count(
            report
                .audit_receipts
                .iter()
                .filter(|r| {
                    r.rule_id == STAFFING_COMPOSITION_ID
                        && matches!(r.effect, EffectSignature::NodeField(_))
                })
                .count(),
        )?,
        production: count(receipts.production.len())?,
        dispatches: count(receipts.dispatches.len())?,
        losses: count(receipts.losses.len())?,
        arrivals: count(receipts.arrivals.len())?,
        deliveries: count(receipts.deliveries.len())?,
        realizations: count(receipts.realizations.len())?,
        merchant_handling: count(receipts.handling.len())?,
        local_fulfillments: count(receipts.local_fulfillments.len())?,
        local_transfers: count(receipts.local_transfers.len())?,
        maintenance: u64::from(receipts.maintenance.is_some()),
    };
    selected_families(manifest, &coverage)?;
    Ok((coverage, execution))
}

#[cfg(test)]
mod tests;
