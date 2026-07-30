//! Binding declaration, resolution and free-variable checking
//! (`bsl-language.rst` §2.5 / §3.5 — "Bindings, not honest-null"): a rule
//! declares the variables it reads; a plain (non-`:optional`) binding that
//! cannot resolve is a **load-time** error, and the opt-in to absence is
//! content (`:optional` + `:default`), never a test list. No rule ever
//! observes absence — it observes a declared default — and there is
//! consequently no `bound?` predicate in the language.
//!
//! The evaluator's unbound-variable error (Task 14) remains as
//! defense-in-depth behind this gate; this module is the primary rejection
//! point the plan's M3 finding demanded.
//!
//! Deferred to the fold-aware typechecker (Task 16), recorded here so the
//! gap is named rather than silent: §2.5's cross-type `:field` scoping rule
//! (`E-TYPE-010` — a qname whose first segment names a different node type
//! is legal only inside a fold body over that type) and `E-TYPE-012` (`it`
//! outside a query context) both need query-context analysis this
//! rule-level pass does not have.
//!
//! One code-assignment ambiguity, flagged for the Phase-1 review: §3.5
//! item 1 lists the resolution codes as "`E-LOAD-010` / `E-LOAD-011` /
//! `E-LOAD-030`" without assigning them per source, while §2.5 explicitly
//! gives `:metric` → `E-LOAD-011`. This module uses `E-LOAD-010` for
//! unresolved `:field`/`:const` (matching §4.6's "unresolved bindings" row)
//! and `E-LOAD-011` for metrics; `E-LOAD-030` remains the enum-registry
//! code the reader documents.

use crate::reader::{Atom, SExpr};
use std::collections::HashSet;

/// The two reserved, always-in-scope symbols (§2.5) — never declared,
/// never shadowed (`E-PARSE-022`).
pub const RESERVED_NAMES: [&str; 2] = ["self", "it"];

/// A binding's declared source (§2.5 `<bind-src>`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum BindSource {
    /// `:field <qname>` — a declared field of `self`'s node type (or, in a
    /// fold body, the queried type's — the cross-type check is Task 16's).
    Field(String),
    /// `:const <qname>` — a coefficient from the defines environment; the
    /// successor of the doctrine DSL's `@snake_case` sigil.
    Const(String),
    /// `:metric <symbol>` — a registered graph-level metric.
    Metric(String),
    /// `:tick` — the current tick, as `Int`.
    Tick,
}

/// One parsed `(binding <symbol> <bind-src> <bind-opt>*)` declaration.
#[derive(Debug, Clone, PartialEq)]
pub struct BindingDecl {
    /// The rule-scoped variable name.
    pub name: String,
    /// Where the value comes from.
    pub source: BindSource,
    /// Declared `:optional` (which requires `default` to be `Some`, §3.5).
    pub optional: bool,
    /// The `:default` literal — only literals, never an expression (§2.2).
    pub default: Option<Atom>,
}

/// The closed vocabulary a rule's bindings resolve against (§3.6): declared
/// field qnames, defines keys, and registered metric names. Phase 1 takes
/// this as an opaque input; the registries themselves are Phase 2 content.
#[derive(Debug, Clone, Default)]
pub struct BindingVocabulary {
    /// Declared `deffield` qnames.
    pub fields: HashSet<String>,
    /// Defines-environment coefficient keys.
    pub consts: HashSet<String>,
    /// Registered graph-level metric names.
    pub metrics: HashSet<String>,
}

/// A binding-surface rejection. `code` follows the no-invented-codes
/// precedent: only where the reference names one.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum BindingError {
    /// `E-PARSE-013` — a keyword outside the closed §2.2 set where a
    /// `<bind-src>`/`<bind-opt>` is required; never ignored.
    UnknownKeyword {
        /// The offending keyword (without colon).
        keyword: String,
    },
    /// `E-PARSE-022` — declaring (or shadowing) a reserved symbol.
    ReservedName {
        /// `self` or `it`.
        name: String,
    },
    /// `E-PARSE-030` — a duplicate binding name within one rule.
    DuplicateName {
        /// The name declared twice.
        name: String,
    },
    /// `E-PARSE-031` — `:optional` without `:default` (§3.5: requiring the
    /// pair keeps every expression total; no rule observes absence).
    OptionalWithoutDefault {
        /// The offending binding.
        name: String,
    },
    /// `E-LOAD-010` — an unresolved `:field`/`:const` source, or a variable
    /// referenced in the rule body that no binding declares.
    Unresolved {
        /// The unresolved name.
        name: String,
        /// What kind of resolution failed, for the message.
        what: &'static str,
    },
    /// `E-LOAD-011` — an unregistered `:metric` name; never `0.0` (§6.3).
    UnregisteredMetric {
        /// The unregistered metric.
        name: String,
    },
    /// A form off the §2.5 grammar at a point this checker must
    /// destructure.
    Malformed {
        /// What was expected, and what was found.
        message: String,
    },
}

impl BindingError {
    /// The spec's error code, where the reference names one.
    #[must_use]
    pub fn spec_code(&self) -> Option<&'static str> {
        match self {
            Self::UnknownKeyword { .. } => Some("E-PARSE-013"),
            Self::ReservedName { .. } => Some("E-PARSE-022"),
            Self::DuplicateName { .. } => Some("E-PARSE-030"),
            Self::OptionalWithoutDefault { .. } => Some("E-PARSE-031"),
            Self::Unresolved { .. } => Some("E-LOAD-010"),
            Self::UnregisteredMetric { .. } => Some("E-LOAD-011"),
            Self::Malformed { .. } => None,
        }
    }
}

impl std::fmt::Display for BindingError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::UnknownKeyword { keyword } => write!(
                f,
                "E-PARSE-013: unrecognized keyword :{keyword} in a binding — \
                 the keyword set is closed and never ignored (§2.2)"
            ),
            Self::ReservedName { name } => write!(
                f,
                "E-PARSE-022: {name} is reserved and always in scope — it is \
                 never declared and never shadowed (§2.5)"
            ),
            Self::DuplicateName { name } => {
                write!(f, "E-PARSE-030: duplicate binding name {name} in one rule")
            }
            Self::OptionalWithoutDefault { name } => write!(
                f,
                "E-PARSE-031: binding {name} is :optional without :default — \
                 no rule observes absence, it observes a declared default (§3.5)"
            ),
            Self::Unresolved { name, what } => {
                write!(f, "E-LOAD-010: unresolved {what}: {name}")
            }
            Self::UnregisteredMetric { name } => write!(
                f,
                "E-LOAD-011: unregistered metric {name} — never 0.0 (§2.5)"
            ),
            Self::Malformed { message } => write!(f, "malformed binding form: {message}"),
        }
    }
}

impl std::error::Error for BindingError {}

fn malformed(message: impl Into<String>) -> BindingError {
    BindingError::Malformed {
        message: message.into(),
    }
}

fn is_literal(atom: &Atom) -> bool {
    matches!(
        atom,
        Atom::Int(_) | Atom::Currency(_) | Atom::Scaled(_) | Atom::Bool(_)
    )
}

/// Parse and validate a rule's `(bindings <binding>*)` form into declared
/// bindings, enforcing the §2.5/§3.5 declaration rules (`E-PARSE-013`,
/// `E-PARSE-022`, `E-PARSE-030`, `E-PARSE-031`).
///
/// # Errors
///
/// [`BindingError`] as above; [`BindingError::Malformed`] for shapes off
/// the `<binding>` production.
pub fn parse_bindings(rule: &SExpr) -> Result<Vec<BindingDecl>, BindingError> {
    let SExpr::List(items) = rule else {
        return Err(malformed(format!(
            "expected a (rule …) form, found {rule:?}"
        )));
    };
    let bindings_form = items.iter().find_map(|child| match child {
        SExpr::List(inner)
            if matches!(inner.first(), Some(SExpr::Atom(Atom::Symbol(h))) if h == "bindings") =>
        {
            Some(&inner[1..])
        }
        _ => None,
    });
    let Some(rows) = bindings_form else {
        return Err(malformed("a rule requires a (bindings …) form (§2.3)"));
    };
    let mut decls: Vec<BindingDecl> = Vec::with_capacity(rows.len());
    for row in rows {
        let decl = parse_binding(row)?;
        if RESERVED_NAMES.contains(&decl.name.as_str()) {
            return Err(BindingError::ReservedName { name: decl.name });
        }
        if decls.iter().any(|existing| existing.name == decl.name) {
            return Err(BindingError::DuplicateName { name: decl.name });
        }
        if decl.optional && decl.default.is_none() {
            return Err(BindingError::OptionalWithoutDefault { name: decl.name });
        }
        decls.push(decl);
    }
    Ok(decls)
}

/// Parse one `(binding <symbol> <bind-src> <bind-opt>*)` row.
fn parse_binding(row: &SExpr) -> Result<BindingDecl, BindingError> {
    let SExpr::List(items) = row else {
        return Err(malformed(format!(
            "expected a (binding …) form, found {row:?}"
        )));
    };
    let [SExpr::Atom(Atom::Symbol(head)), SExpr::Atom(Atom::Symbol(name)), rest @ ..] =
        items.as_slice()
    else {
        return Err(malformed(format!(
            "(binding <symbol> <bind-src> <bind-opt>*) — unrecognized shape {items:?}"
        )));
    };
    if head != "binding" {
        return Err(malformed(format!("expected (binding …), found ({head} …)")));
    }
    let mut source: Option<BindSource> = None;
    let mut optional = false;
    let mut default: Option<Atom> = None;
    let mut cursor = rest;
    while let [SExpr::Atom(Atom::Keyword(kw)), tail @ ..] = cursor {
        let (consumed, next_tail) = parse_binding_keyword(kw, tail, &mut source, &mut optional)?;
        if let Some(value) = consumed {
            default = Some(value);
        }
        cursor = next_tail;
    }
    if !cursor.is_empty() {
        return Err(malformed(format!(
            "unexpected trailing items in a binding: {cursor:?}"
        )));
    }
    let Some(source) = source else {
        return Err(malformed(format!(
            "binding {name} declares no <bind-src> (:field | :const | :metric | :tick)"
        )));
    };
    Ok(BindingDecl {
        name: name.clone(),
        source,
        optional,
        default,
    })
}

/// Consume one keyword and its operand (if any) from a binding row's tail.
/// Returns the `:default` literal when that keyword was the one consumed.
fn parse_binding_keyword<'a>(
    kw: &str,
    tail: &'a [SExpr],
    source: &mut Option<BindSource>,
    optional: &mut bool,
) -> Result<(Option<Atom>, &'a [SExpr]), BindingError> {
    let take_qname = |tail: &'a [SExpr]| -> Result<(String, &'a [SExpr]), BindingError> {
        match tail {
            [SExpr::Atom(Atom::QName(q)), rest @ ..] => Ok((q.clone(), rest)),
            other => Err(malformed(format!(
                ":{kw} takes a qualified name, found {:?}",
                other.first()
            ))),
        }
    };
    match kw {
        "field" => {
            let (qname, rest) = take_qname(tail)?;
            *source = Some(BindSource::Field(qname));
            Ok((None, rest))
        }
        "const" => {
            let (qname, rest) = take_qname(tail)?;
            *source = Some(BindSource::Const(qname));
            Ok((None, rest))
        }
        "metric" => match tail {
            [SExpr::Atom(Atom::Symbol(name)), rest @ ..] => {
                *source = Some(BindSource::Metric(name.clone()));
                Ok((None, rest))
            }
            other => Err(malformed(format!(
                ":metric takes a symbol, found {:?}",
                other.first()
            ))),
        },
        "tick" => {
            *source = Some(BindSource::Tick);
            Ok((None, tail))
        }
        "optional" => {
            *optional = true;
            Ok((None, tail))
        }
        "default" => match tail {
            [SExpr::Atom(literal), rest @ ..] if is_literal(literal) => {
                Ok((Some(literal.clone()), rest))
            }
            other => Err(malformed(format!(
                ":default takes a literal — never an expression (§2.2), found {:?}",
                other.first()
            ))),
        },
        other => Err(BindingError::UnknownKeyword {
            keyword: other.to_owned(),
        }),
    }
}

/// Resolve every declared binding against the closed vocabulary (§3.5 item
/// 1: the source must resolve for EVERY binding — `:optional` licenses
/// per-node absence of a value, never an unknown name).
///
/// # Errors
///
/// [`BindingError::Unresolved`] (`E-LOAD-010`) for an unknown field/const;
/// [`BindingError::UnregisteredMetric`] (`E-LOAD-011`) for an unknown
/// metric. `:tick` always resolves.
pub fn resolve_bindings(
    decls: &[BindingDecl],
    vocabulary: &BindingVocabulary,
) -> Result<(), BindingError> {
    for decl in decls {
        match &decl.source {
            BindSource::Field(qname) => {
                if !vocabulary.fields.contains(qname) {
                    return Err(BindingError::Unresolved {
                        name: qname.clone(),
                        what: ":field",
                    });
                }
            }
            BindSource::Const(qname) => {
                if !vocabulary.consts.contains(qname) {
                    return Err(BindingError::Unresolved {
                        name: qname.clone(),
                        what: ":const",
                    });
                }
            }
            BindSource::Metric(name) => {
                if !vocabulary.metrics.contains(name) {
                    return Err(BindingError::UnregisteredMetric { name: name.clone() });
                }
            }
            BindSource::Tick => {}
        }
    }
    Ok(())
}

/// Check that every variable the rule's `<when>` and `<effects>` read is a
/// declared binding or a reserved symbol — an undeclared reference is a
/// load error (`E-LOAD-010`, §4.6 "unresolved bindings"), never an
/// eval-time surprise. (`it`'s query-context validity — `E-TYPE-012` — is
/// the fold-aware pass's, Task 16.)
///
/// # Errors
///
/// [`BindingError::Unresolved`] for the first undeclared variable found;
/// [`BindingError::Malformed`] if the form is not a rule.
pub fn check_free_variables(rule: &SExpr, decls: &[BindingDecl]) -> Result<(), BindingError> {
    let SExpr::List(items) = rule else {
        return Err(malformed(format!(
            "expected a (rule …) form, found {rule:?}"
        )));
    };
    let declared: HashSet<&str> = decls.iter().map(|d| d.name.as_str()).collect();
    for child in items {
        if let SExpr::List(inner) = child {
            if matches!(inner.first(), Some(SExpr::Atom(Atom::Symbol(h))) if h == "when" || h == "effects")
            {
                for body in &inner[1..] {
                    check_expr_variables(body, &declared)?;
                }
            }
        }
    }
    Ok(())
}

/// Walk one expression: a `Symbol` in value position must be declared or
/// reserved. Head symbols (operators, structural forms, intrinsic names)
/// and the fold-op symbol are form structure, not variable references.
fn check_expr_variables(expr: &SExpr, declared: &HashSet<&str>) -> Result<(), BindingError> {
    match expr {
        SExpr::Atom(Atom::Symbol(name)) => {
            if declared.contains(name.as_str()) || RESERVED_NAMES.contains(&name.as_str()) {
                Ok(())
            } else {
                Err(BindingError::Unresolved {
                    name: name.clone(),
                    what: "variable (no binding declares it)",
                })
            }
        }
        SExpr::Atom(_) => Ok(()),
        SExpr::List(items) => {
            let value_positions = match items.first() {
                // The head names the form (§1.3) — never a variable. A fold
                // additionally carries its fold-op symbol at position 1.
                Some(SExpr::Atom(Atom::Symbol(h))) if h == "fold" => &items[2..],
                Some(SExpr::Atom(Atom::Symbol(_) | Atom::Operator(_))) => &items[1..],
                _ => items.as_slice(),
            };
            for item in value_positions {
                check_expr_variables(item, declared)?;
            }
            Ok(())
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::reader::read;

    /// The §5.6 worked example — one `:field` binding named `wealth`.
    const DEMO_RULE: &str = r#"
        (rule demo/hunger
          :material-basis "subsistence deficit at the point of reproduction"
          :fuel 64
          (bindings
            (binding wealth :field social-class/wealth))
          (when (< wealth 1000.5$))
          (effects
            (update-node self social-class/agitation (add 0.05i))))
    "#;

    fn parse(source: &str) -> SExpr {
        read(source).expect("test source must parse").0
    }

    fn rule_with_bindings(rows: &str) -> SExpr {
        parse(&format!(
            "(rule demo/binds :material-basis \"wage relation\" :fuel 8 \
             (bindings {rows}) \
             (effects (update-node self social-class/agitation (add 0.05i))))"
        ))
    }

    fn vocabulary() -> BindingVocabulary {
        BindingVocabulary {
            fields: HashSet::from(["social-class/wealth".to_owned()]),
            consts: HashSet::from(["survival/subsistence-floor".to_owned()]),
            metrics: HashSet::from(["mean-tension".to_owned()]),
        }
    }

    #[test]
    fn the_worked_example_parses_resolves_and_closes_its_variables() {
        let rule = parse(DEMO_RULE);
        let decls = parse_bindings(&rule).unwrap();
        assert_eq!(
            decls,
            vec![BindingDecl {
                name: "wealth".to_owned(),
                source: BindSource::Field("social-class/wealth".to_owned()),
                optional: false,
                default: None,
            }]
        );
        assert_eq!(resolve_bindings(&decls, &vocabulary()), Ok(()));
        assert_eq!(check_free_variables(&rule, &decls), Ok(()));
    }

    #[test]
    fn all_four_bind_sources_parse() {
        let rule = rule_with_bindings(
            "(binding wealth :field social-class/wealth) \
             (binding floor :const survival/subsistence-floor) \
             (binding tension :metric mean-tension) \
             (binding now :tick)",
        );
        let decls = parse_bindings(&rule).unwrap();
        assert_eq!(decls.len(), 4);
        assert_eq!(
            decls[1].source,
            BindSource::Const("survival/subsistence-floor".to_owned())
        );
        assert_eq!(
            decls[2].source,
            BindSource::Metric("mean-tension".to_owned())
        );
        assert_eq!(decls[3].source, BindSource::Tick);
        assert_eq!(resolve_bindings(&decls, &vocabulary()), Ok(()));
    }

    #[test]
    fn reserved_names_are_never_declared_e_parse_022() {
        for name in ["self", "it"] {
            let rule = rule_with_bindings(&format!("(binding {name} :tick)"));
            let err = parse_bindings(&rule).unwrap_err();
            assert_eq!(
                err,
                BindingError::ReservedName {
                    name: name.to_owned()
                }
            );
            assert_eq!(err.spec_code(), Some("E-PARSE-022"));
        }
    }

    #[test]
    fn a_duplicate_binding_name_is_e_parse_030() {
        let rule = rule_with_bindings(
            "(binding wealth :field social-class/wealth) (binding wealth :tick)",
        );
        let err = parse_bindings(&rule).unwrap_err();
        assert_eq!(err.spec_code(), Some("E-PARSE-030"));
    }

    #[test]
    fn bare_optional_without_default_is_e_parse_031() {
        let rule = rule_with_bindings("(binding wealth :field social-class/wealth :optional)");
        let err = parse_bindings(&rule).unwrap_err();
        assert_eq!(err.spec_code(), Some("E-PARSE-031"));
        // The pair is legal, and the default is captured as a literal atom.
        let ok =
            rule_with_bindings("(binding wealth :field social-class/wealth :optional :default 0$)");
        let decls = parse_bindings(&ok).unwrap();
        assert!(decls[0].optional);
        assert!(decls[0].default.is_some());
    }

    #[test]
    fn a_default_must_be_a_literal_never_an_expression() {
        let rule = rule_with_bindings(
            "(binding wealth :field social-class/wealth :optional :default (+ 1 2))",
        );
        assert!(matches!(
            parse_bindings(&rule),
            Err(BindingError::Malformed { .. })
        ));
    }

    #[test]
    fn an_unknown_binding_keyword_is_e_parse_013() {
        let rule = rule_with_bindings("(binding wealth :bogus social-class/wealth)");
        let err = parse_bindings(&rule).unwrap_err();
        assert_eq!(
            err,
            BindingError::UnknownKeyword {
                keyword: "bogus".to_owned()
            }
        );
        assert_eq!(err.spec_code(), Some("E-PARSE-013"));
    }

    #[test]
    fn unresolved_sources_are_load_errors_per_source_kind() {
        let field = rule_with_bindings("(binding x :field social-class/unknowable)");
        let err = resolve_bindings(&parse_bindings(&field).unwrap(), &vocabulary()).unwrap_err();
        assert_eq!(err.spec_code(), Some("E-LOAD-010"));

        let konst = rule_with_bindings("(binding x :const survival/unknowable)");
        let err = resolve_bindings(&parse_bindings(&konst).unwrap(), &vocabulary()).unwrap_err();
        assert_eq!(err.spec_code(), Some("E-LOAD-010"));

        let metric = rule_with_bindings("(binding x :metric unknowable)");
        let err = resolve_bindings(&parse_bindings(&metric).unwrap(), &vocabulary()).unwrap_err();
        assert_eq!(err.spec_code(), Some("E-LOAD-011"), "never 0.0 (§6.3)");
    }

    #[test]
    fn an_undeclared_variable_in_the_body_is_a_load_error_not_an_eval_surprise() {
        let rule = parse(
            "(rule demo/free :material-basis \"wage relation\" :fuel 8 \
             (bindings) \
             (when (< undeclared 5)) \
             (effects (update-node self social-class/agitation (add 0.05i))))",
        );
        let decls = parse_bindings(&rule).unwrap();
        let err = check_free_variables(&rule, &decls).unwrap_err();
        assert_eq!(err.spec_code(), Some("E-LOAD-010"));
    }

    #[test]
    fn heads_fold_ops_and_reserved_symbols_are_not_variable_references() {
        // `sum` is a fold-op, `nodes` a query head, `it` reserved — none
        // may be flagged; only genuinely free value-position symbols are.
        let rule = parse(
            "(rule demo/fold :material-basis \"wage relation\" :fuel 512 \
             (bindings) \
             (when (< (fold sum (nodes NodeType/SOCIAL_CLASS) it) 5)) \
             (effects (update-node self social-class/agitation (add 0.05i))))",
        );
        let decls = parse_bindings(&rule).unwrap();
        assert_eq!(check_free_variables(&rule, &decls), Ok(()));
    }
}
