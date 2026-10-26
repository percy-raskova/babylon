//! The load-bearing content audit: refusals, coefficient basis and effect coverage.

use std::collections::BTreeMap;
use std::collections::BTreeSet;
use std::collections::HashSet;

use babylon_bsl::bindings::BindSource;
use babylon_bsl::causal_contract::EffectSignature;
use babylon_bsl::reader::Atom;
use babylon_bsl::reader::SExpr;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_kernel::clock::WEEKS_PER_TICK;
use babylon_material_circuit::GoodId;
use babylon_material_circuit::HouseholdNeedBasis;
use babylon_material_circuit::MaterialCatalog;
use babylon_material_circuit::UnitId;
use babylon_tick::ContentRuleSource;
use babylon_tick::PrepareError;

use super::error::PackageError;
use super::manifest::SourceKind;
use super::resolver::ResolvedContentSet;

/// One cross-checked rule in the effective content set.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct AuditedRule {
    rule_id: String,
    anchor_system: String,
    fuel: u64,
    effects: Vec<EffectSignature>,
}

impl AuditedRule {
    /// Return the governed rule identity.
    #[must_use]
    pub fn rule_id(&self) -> &str {
        &self.rule_id
    }

    /// Return the phase-system home this rule resolves to.
    #[must_use]
    pub fn anchor_system(&self) -> &str {
        &self.anchor_system
    }

    /// Return the declared execution cost.
    #[must_use]
    pub const fn fuel(&self) -> u64 {
        self.fuel
    }

    /// Return every possible effect in source order.
    #[must_use]
    pub fn effects(&self) -> &[EffectSignature] {
        &self.effects
    }
}

/// The complete audit of one effective rule set.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ContentAudit {
    rules: Vec<AuditedRule>,
}

impl ContentAudit {
    /// Return the audited rules in source order.
    #[must_use]
    pub fn rules(&self) -> &[AuditedRule] {
        &self.rules
    }
}

/// One closed coefficient basis.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum CoefficientBasis {
    /// Quantity per produced batch.
    PerBatch,
    /// Quantity per native good unit.
    PerUnit,
    /// Quantity per resident person per period.
    PerPersonPeriod,
    /// Quantity per occupied household per period.
    PerHouseholdPeriod,
}

/// One closed coefficient unit.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum CoefficientUnit {
    /// A declared good unit.
    Good(UnitId),
    /// Labor time in hours.
    LaborHour,
}

/// One coefficient with its audited basis and unit.
///
/// A row the audit publishes always carries both dimensions;
/// [`audit_catalog_coefficients`] refuses a missing basis or unit before the row
/// exists. The accessors expose `Option` only because the audit checks the
/// compiled coefficient before publication, not because a published row may
/// lack a dimension.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CoefficientRow {
    name: String,
    basis: Option<CoefficientBasis>,
    unit: Option<CoefficientUnit>,
}

impl CoefficientRow {
    /// Return the diagnostic coefficient identity.
    #[must_use]
    pub fn name(&self) -> &str {
        &self.name
    }

    /// Return the audited basis.
    ///
    /// The audit never publishes a row without a basis; `None` is not a valid
    /// published-row state.
    #[must_use]
    pub const fn basis(&self) -> Option<CoefficientBasis> {
        self.basis
    }

    /// Return the audited unit.
    ///
    /// The audit never publishes a row without a unit; `None` is not a valid
    /// published-row state.
    #[must_use]
    pub const fn unit(&self) -> Option<CoefficientUnit> {
        self.unit
    }
}

/// The audit result for one compiled material catalog.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CoefficientAudit {
    rows: Vec<CoefficientRow>,
}

impl CoefficientAudit {
    /// Return every audited coefficient.
    #[must_use]
    pub fn rows(&self) -> &[CoefficientRow] {
        &self.rows
    }
}

/// The one catalog-wide labor-time normalizing constant.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct CoefficientNormalization {
    hours_per_person_period: u64,
}

impl CoefficientNormalization {
    /// Validate the one shared hours-per-person-per-period normalization.
    ///
    /// # Errors
    ///
    /// Refuses a zero constant or one that is not a whole number of
    /// [`WEEKS_PER_TICK`] weeks.
    pub fn new(hours_per_person_period: u64) -> Result<Self, PackageError> {
        if hours_per_person_period == 0 {
            return Err(PackageError::InconsistentNormalizingConstant {
                reason: "the shared hours-per-person-period constant is zero".to_owned(),
            });
        }
        if !hours_per_person_period.is_multiple_of(WEEKS_PER_TICK) {
            return Err(PackageError::InconsistentNormalizingConstant {
                reason: format!(
                    "{hours_per_person_period} hours per period is not a whole number of {WEEKS_PER_TICK}-week periods"
                ),
            });
        }
        Ok(Self {
            hours_per_person_period,
        })
    }

    /// Return the exact shared constant.
    #[must_use]
    pub const fn hours_per_person_period(self) -> u64 {
        self.hours_per_person_period
    }
}

/// Audit one effective rule set for the load-bearing refusal gates.
///
/// # Errors
///
/// Refuses an unreadable scenario or rule source, duplicate rule identities, an
/// anchor naming no registered phase system, a `defconst` no rule reads, a rule
/// write to state the scenario never listed, a second cost for one state/action
/// pair, or any refusal from the existing BSL loader and composition gates.
pub fn audit_rule_set(
    scenario: &str,
    prelude: Option<&str>,
    rules: &[&str],
) -> Result<ContentAudit, PackageError> {
    let mut graph = HypergraphStore::new();
    let loaded = match prelude {
        Some(prelude) => {
            babylon_bsl::scenario::load_scenario_with_prelude(prelude, scenario, &mut graph)
        }
        None => babylon_bsl::scenario::load_scenario(scenario, &mut graph),
    }
    .map_err(|error| PackageError::RuleSetRefused {
        reason: error.to_string(),
    })?;
    let forms = split_rules(rules)?;
    let ids = forms
        .iter()
        .map(|(rule_id, form)| (rule_id.clone(), form.clone()))
        .collect::<Vec<_>>();
    babylon_bsl::rule_pipeline::check_unique_rule_ids(&ids).map_err(|error| {
        PackageError::RuleSetRefused {
            reason: error.to_string(),
        }
    })?;
    let referenced = referenced_consts(&forms)?;
    for name in loaded.consts.keys() {
        if !referenced.contains(name) {
            return Err(PackageError::UnconsumedDial { name: name.clone() });
        }
    }
    let mut audited = Vec::with_capacity(forms.len());
    let mut costs: BTreeMap<String, String> = BTreeMap::new();
    for (rule_id, form) in &forms {
        let fuel = declared_fuel(form).ok_or_else(|| PackageError::RuleSetRefused {
            reason: format!("rule {rule_id} declares no readable :fuel cost"),
        })?;
        let anchor_system = anchor_system(form, rule_id);
        let effects = babylon_bsl::causal_contract::effect_footprint(form).map_err(|error| {
            PackageError::RuleSetRefused {
                reason: error.to_string(),
            }
        })?;
        let mut seen_pairs = BTreeSet::new();
        for effect in &effects {
            if let Some(field) = written_field(effect) {
                if !loaded.fields.contains_key(field) {
                    return Err(PackageError::UnlistedStateActionPair {
                        rule_id: rule_id.clone(),
                        field: field.to_owned(),
                    });
                }
            }
            // The valuation belongs to the written state target and action verb,
            // not to the phase an author happened to anchor the rule in. Two
            // phases that advance one field are still one pair with one cost.
            let pair = cost_pair(effect);
            if !seen_pairs.insert(pair.clone()) {
                continue;
            }
            if let Some(first_rule) = costs.insert(pair.clone(), rule_id.clone()) {
                return Err(PackageError::DuplicateCost {
                    pair,
                    first_rule,
                    second_rule: rule_id.clone(),
                });
            }
        }
        audited.push(AuditedRule {
            rule_id: rule_id.clone(),
            anchor_system,
            fuel,
            effects,
        });
    }
    validate_with_existing_loader(scenario, prelude, rules)?;
    Ok(ContentAudit { rules: audited })
}

/// Audit the effective scenario and rule units of one resolved content set.
///
/// A set with no scenario and no rules unit (the numeric Michigan profile) has
/// no rule surface to audit and returns an empty report.
///
/// # Errors
///
/// Refuses a rule set without exactly one scenario, more than one prelude, a
/// non-UTF-8 captured source, or any refusal of [`audit_rule_set`].
pub fn audit_resolved_rules(resolved: &ResolvedContentSet) -> Result<ContentAudit, PackageError> {
    let scenarios = resolved.units_of(SourceKind::Scenario).collect::<Vec<_>>();
    let preludes = resolved.units_of(SourceKind::Prelude).collect::<Vec<_>>();
    let rules = resolved.units_of(SourceKind::Rules).collect::<Vec<_>>();
    if rules.is_empty() && scenarios.is_empty() {
        return Ok(ContentAudit { rules: Vec::new() });
    }
    let [scenario] = scenarios.as_slice() else {
        return Err(PackageError::RuleSetRefused {
            reason: "a rule-bearing content set requires exactly one scenario unit".to_owned(),
        });
    };
    if preludes.len() > 1 {
        return Err(PackageError::RuleSetRefused {
            reason: "a content set accepts at most one declaration prelude".to_owned(),
        });
    }
    let scenario = utf8_source(scenario.source_id(), scenario.bytes())?;
    let prelude = preludes
        .first()
        .map(|unit| utf8_source(unit.source_id(), unit.bytes()))
        .transpose()?;
    let sources = rules
        .iter()
        .map(|unit| utf8_source(unit.source_id(), unit.bytes()))
        .collect::<Result<Vec<_>, PackageError>>()?;
    audit_rule_set(scenario, prelude, &sources)
}

fn utf8_source<'a>(source_id: &str, bytes: &'a [u8]) -> Result<&'a str, PackageError> {
    std::str::from_utf8(bytes).map_err(|_| PackageError::RuleSetRefused {
        reason: format!("source unit {source_id} is not UTF-8"),
    })
}

fn split_rules(rules: &[&str]) -> Result<Vec<(String, SExpr)>, PackageError> {
    let mut forms = Vec::new();
    for source in rules {
        let (_intrinsics, split) =
            babylon_bsl::rule_pipeline::split_content(source).map_err(|error| {
                PackageError::RuleSetRefused {
                    reason: error.to_string(),
                }
            })?;
        forms.extend(split.into_iter().map(|rule| (rule.rule_id, rule.form)));
    }
    Ok(forms)
}

fn referenced_consts(forms: &[(String, SExpr)]) -> Result<HashSet<String>, PackageError> {
    let mut referenced = HashSet::new();
    for (rule_id, form) in forms {
        if !has_bindings(form) {
            continue;
        }
        let bindings = babylon_bsl::bindings::parse_bindings(form).map_err(|error| {
            PackageError::RuleSetRefused {
                reason: format!("rule {rule_id} bindings refused: {error}"),
            }
        })?;
        for binding in bindings {
            match binding.source {
                BindSource::Const(name) => {
                    referenced.insert(name);
                }
                BindSource::Expr(expr) => collect_symbols(&expr, &mut referenced),
                _ => {}
            }
        }
    }
    Ok(referenced)
}

fn has_bindings(rule: &SExpr) -> bool {
    let SExpr::List(items) = rule else {
        return false;
    };
    items.iter().any(|item| {
        matches!(
            item,
            SExpr::List(inner)
                if matches!(inner.first(), Some(SExpr::Atom(Atom::Symbol(head))) if head == "bindings")
        )
    })
}

fn collect_symbols(expr: &SExpr, symbols: &mut HashSet<String>) {
    match expr {
        SExpr::Atom(Atom::Symbol(name)) => {
            symbols.insert(name.clone());
        }
        SExpr::List(items) => {
            for item in items {
                collect_symbols(item, symbols);
            }
        }
        SExpr::Atom(_) => {}
    }
}

fn declared_fuel(rule: &SExpr) -> Option<u64> {
    let SExpr::List(items) = rule else {
        return None;
    };
    let mut cursor = items.iter();
    while let Some(item) = cursor.next() {
        if matches!(item, SExpr::Atom(Atom::Keyword(keyword)) if keyword == "fuel") {
            return match cursor.next() {
                Some(SExpr::Atom(Atom::Int(value))) => u64::try_from(*value).ok(),
                _ => None,
            };
        }
    }
    None
}

fn anchor_system(rule: &SExpr, rule_id: &str) -> String {
    let SExpr::List(items) = rule else {
        return first_segment(rule_id).to_owned();
    };
    for item in items {
        let SExpr::List(inner) = item else {
            continue;
        };
        let [SExpr::Atom(Atom::Symbol(head)), SExpr::Atom(Atom::Keyword(_position)), SExpr::Atom(Atom::Symbol(system))] =
            inner.as_slice()
        else {
            continue;
        };
        if head == "anchor" {
            return system.clone();
        }
    }
    first_segment(rule_id).to_owned()
}

fn first_segment(rule_id: &str) -> &str {
    rule_id.split('/').next().unwrap_or(rule_id)
}

fn written_field(effect: &EffectSignature) -> Option<&str> {
    match effect {
        EffectSignature::NodeField(field)
        | EffectSignature::EdgeField(field)
        | EffectSignature::HyperedgeField(field) => Some(field),
        EffectSignature::MaterialCycle
        | EffectSignature::OrganizerProducts
        | EffectSignature::OrganizerPractice
        | EffectSignature::Event(_)
        | EffectSignature::Shape(_) => None,
    }
}

/// Name the `(state target, action verb)` pair one effect writes.
///
/// The anchor is deliberately absent: the pair is the content law, so the same
/// write from two phases still shares one valuation.
fn cost_pair(effect: &EffectSignature) -> String {
    match effect {
        EffectSignature::MaterialCycle => "material-cycle".to_owned(),
        EffectSignature::OrganizerProducts => "organizer-products".to_owned(),
        EffectSignature::OrganizerPractice => "organizer-practice".to_owned(),
        EffectSignature::NodeField(field) => format!("node-field:{field}"),
        EffectSignature::EdgeField(field) => format!("edge-field:{field}"),
        EffectSignature::HyperedgeField(field) => format!("hyperedge-field:{field}"),
        EffectSignature::Event(event) => format!("event:{event}"),
        EffectSignature::Shape(verb) => format!("shape:{verb:?}"),
    }
}

fn validate_with_existing_loader(
    scenario: &str,
    prelude: Option<&str>,
    rules: &[&str],
) -> Result<(), PackageError> {
    let scenario = ContentRuleSource {
        source_id: "package/scenario",
        source: scenario,
    };
    let preludes = prelude
        .map(|prelude| ContentRuleSource {
            source_id: "package/prelude",
            source: prelude,
        })
        .into_iter()
        .collect::<Vec<_>>();
    let sources = rules
        .iter()
        .map(|source| ContentRuleSource {
            source_id: "package/rules",
            source,
        })
        .collect::<Vec<_>>();
    babylon_tick::analyze_content_set_sources(scenario, &preludes, &sources)
        .map_err(|error| match error {
            PrepareError::Rule {
                rule_id: Some(rule_id),
                error: babylon_bsl::rule_pipeline::LoadError::Anchor(_),
            } => PackageError::UnknownRuleId { rule_id },
            other => PackageError::RuleSetRefused {
                reason: other.to_string(),
            },
        })
        .map(|_| ())
}

/// Audit every compiled catalog coefficient's basis and unit.
///
/// # Errors
///
/// Refuses a coefficient with no positive basis, a good unit the catalog never
/// declares, a zero labor/handling coefficient, or more than one labor-hour unit
/// under one shared normalization.
pub fn audit_catalog_coefficients(
    catalog: &MaterialCatalog,
    normalization: CoefficientNormalization,
) -> Result<CoefficientAudit, PackageError> {
    let mut rows = Vec::new();
    for (index, coefficient) in catalog.process_outputs.iter().enumerate() {
        let name = format!("process_outputs[{index}]");
        let basis = (coefficient.quantity_per_batch > 0).then_some(CoefficientBasis::PerBatch);
        let unit = good_unit(catalog, coefficient.good_id, coefficient.unit_id)
            .then_some(CoefficientUnit::Good(coefficient.unit_id));
        audit_row(&name, basis, unit, &mut rows)?;
    }
    for (index, coefficient) in catalog.input_coefficients.iter().enumerate() {
        let name = format!("input_coefficients[{index}]");
        let basis = (coefficient.quantity_per_batch > 0).then_some(CoefficientBasis::PerBatch);
        let unit = good_unit(catalog, coefficient.good_id, coefficient.unit_id)
            .then_some(CoefficientUnit::Good(coefficient.unit_id));
        audit_row(&name, basis, unit, &mut rows)?;
    }
    let mut labor_units = BTreeSet::new();
    for (index, coefficient) in catalog.labor_coefficients.iter().enumerate() {
        let name = format!("labor_coefficients[{index}]");
        let basis = (coefficient.quantity_per_batch > 0).then_some(CoefficientBasis::PerBatch);
        let unit = (coefficient.unit_id != UnitId::from_bytes([0; 32]))
            .then_some(CoefficientUnit::LaborHour);
        if unit.is_some() {
            labor_units.insert(coefficient.unit_id);
        }
        audit_row(&name, basis, unit, &mut rows)?;
    }
    for (index, coefficient) in catalog.handling_coefficients.iter().enumerate() {
        let name = format!("handling_coefficients[{index}]");
        let basis = (coefficient.hours_per_unit > 0).then_some(CoefficientBasis::PerUnit);
        let unit = (coefficient.unit_id != UnitId::from_bytes([0; 32]))
            .then_some(CoefficientUnit::LaborHour);
        if unit.is_some() {
            labor_units.insert(coefficient.unit_id);
        }
        audit_row(&name, basis, unit, &mut rows)?;
    }
    for (index, need) in catalog.household_needs.iter().enumerate() {
        let name = format!("household_needs[{index}]");
        let basis = (need.units_per_basis > 0).then_some(match need.basis {
            HouseholdNeedBasis::Persons => CoefficientBasis::PerPersonPeriod,
            HouseholdNeedBasis::Households => CoefficientBasis::PerHouseholdPeriod,
        });
        let unit = good_unit(catalog, need.good_id, need.unit_id)
            .then_some(CoefficientUnit::Good(need.unit_id));
        audit_row(&name, basis, unit, &mut rows)?;
    }
    if labor_units.len() > 1 {
        return Err(PackageError::InconsistentNormalizingConstant {
            reason: format!(
                "{} labor-hour units share one normalizing constant",
                labor_units.len()
            ),
        });
    }
    if normalization.hours_per_person_period() == 0 {
        return Err(PackageError::InconsistentNormalizingConstant {
            reason: "the shared hours-per-person-period constant is zero".to_owned(),
        });
    }
    Ok(CoefficientAudit { rows })
}

fn audit_row(
    name: &str,
    basis: Option<CoefficientBasis>,
    unit: Option<CoefficientUnit>,
    rows: &mut Vec<CoefficientRow>,
) -> Result<(), PackageError> {
    let Some(basis) = basis else {
        return Err(PackageError::MissingCoefficientBasis {
            coefficient: name.to_owned(),
        });
    };
    let Some(unit) = unit else {
        return Err(PackageError::MissingCoefficientUnit {
            coefficient: name.to_owned(),
        });
    };
    rows.push(CoefficientRow {
        name: name.to_owned(),
        basis: Some(basis),
        unit: Some(unit),
    });
    Ok(())
}

fn good_unit(catalog: &MaterialCatalog, good: GoodId, unit: UnitId) -> bool {
    catalog
        .commodities
        .binary_search_by_key(&(good, unit), |row| (row.good_id, row.unit_id))
        .is_ok()
}
