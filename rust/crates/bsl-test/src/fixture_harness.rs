//! In-memory fixtures for `.bsl` rule snippets and `.bscn` scenario files.
//!
//! A `.bsl` fixture is a complete rule form: the harness runs the rule
//! pipeline's load-time gates, typechecking included, against an empty
//! declaration environment. A `.bscn` fixture is the scenario file's single
//! top-level form. Graph hydration is deliberately absent because it needs a
//! substrate; the parsed form stays available for an engine loader.

use babylon_bsl::bindings::BindingVocabulary;
use babylon_bsl::fuel::{CardinalityCeilings, IntrinsicCosts};
use babylon_bsl::reader;
use babylon_bsl::reader::Atom;
use babylon_bsl::reader::SExpr;
use babylon_bsl::rule_pipeline;
use babylon_bsl::rule_pipeline::LoadContext;
use babylon_bsl::typecheck::TypeEnv;
use babylon_bsl::types::EnumRegistry;
use std::collections::{HashMap, HashSet};
use std::path::Path;

/// The parsed fixtures a test has collected.
#[derive(Debug, Default)]
pub struct BslFixtureSet {
    rules: Vec<SExpr>,
    scenarios: Vec<SExpr>,
}

impl BslFixtureSet {
    /// An empty fixture set.
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    /// Parse and typecheck one `.bsl` rule, then retain its form.
    ///
    /// # Errors
    /// The first failing load stage's message when the rule does not read or
    /// fails a load-time gate.
    pub fn add_rule(&mut self, source: &str) -> Result<(), String> {
        let rule = parse_and_typecheck_bsl(source)?;
        self.rules.push(rule);
        Ok(())
    }

    /// Load one `.bscn` scenario file, then retain its form.
    ///
    /// # Errors
    /// The path, read, parse, or shape failure when the file is not exactly
    /// one `(scenario ...)` form.
    pub fn add_scenario(&mut self, path: &Path) -> Result<(), String> {
        let scenario = load_bscn_fixture(path)?;
        self.scenarios.push(scenario);
        Ok(())
    }

    /// The parsed rule forms, in insertion order.
    #[must_use]
    pub fn rules(&self) -> &[SExpr] {
        &self.rules
    }

    /// The parsed scenario forms, in insertion order.
    #[must_use]
    pub fn scenarios(&self) -> &[SExpr] {
        &self.scenarios
    }
}

/// Parse one `.bsl` rule and run the load-time pipeline, typechecking included.
///
/// The empty declaration environment is the point: a snippet that names a
/// field proves the name reaches the typechecker, and a snippet that reads no
/// declared field loads end to end. The rule id's leading segment is the one
/// registered system, so the anchor default resolves without a content
/// manifest. Rules that need real declarations belong to the engine loader,
/// which supplies the registries a scenario built.
///
/// # Errors
/// The first failing load stage's message.
pub fn parse_and_typecheck_bsl(source: &str) -> Result<SExpr, String> {
    let vocabulary = BindingVocabulary::default();
    let types = TypeEnv {
        fields: HashMap::new(),
        exemptions: &[],
    };
    let enums = EnumRegistry::default();
    let const_values = HashMap::new();
    let ceilings = CardinalityCeilings::default();
    let intrinsics = IntrinsicCosts::default();
    let systems = declared_system(source)
        .map(|system| HashSet::from([system]))
        .unwrap_or_default();
    let context = LoadContext {
        vocabulary: &vocabulary,
        types: &types,
        enums: &enums,
        const_values: &const_values,
        ceilings: &ceilings,
        intrinsics: &intrinsics,
        systems: &systems,
        vocabulary_registry: None,
        rule_file: "inline.bsl",
    };
    let loaded = rule_pipeline::load_rule(source, &context).map_err(|error| error.to_string())?;
    Ok(loaded.rule)
}

/// The leading system segment of a rule id, when the source reads far enough
/// to expose one.
fn declared_system(source: &str) -> Option<String> {
    let (rule, _) = reader::read(source).ok()?;
    let SExpr::List(items) = rule else {
        return None;
    };
    let Some(SExpr::Atom(Atom::QName(id))) = items.get(1) else {
        return None;
    };
    id.split('/').next().map(str::to_owned)
}

/// Read one `.bscn` scenario file and return its single top-level form.
///
/// The shape check mirrors the scenario loader's own gate: exactly one
/// `(scenario <qname> ...)` form. Graph hydration stays the engine's job
/// because it needs a substrate; this harness keeps the parsed fixture so a
/// test can inspect it or hand it on.
///
/// # Errors
/// The path, read, parse, or shape failure when the file is not exactly one
/// scenario form.
pub fn load_bscn_fixture(path: &Path) -> Result<SExpr, String> {
    let display = path.display();
    let source = std::fs::read_to_string(path).map_err(|error| format!("{display}: {error}"))?;
    let forms = reader::read_all(source.as_bytes())
        .map_err(|error| format!("{display}:{}: {}", error.position, error.message))?;
    let [scenario] = forms.as_slice() else {
        return Err(format!(
            "{display}: a .bscn fixture must hold exactly one form, found {}",
            forms.len()
        ));
    };
    let is_scenario = matches!(
        scenario,
        SExpr::List(items)
            if matches!(
                items.first(),
                Some(SExpr::Atom(Atom::Symbol(head))) if head == "scenario"
            )
    );
    if !is_scenario {
        return Err(format!("{display}: expected a (scenario <qname> ...) form"));
    }
    Ok(scenario.clone())
}
