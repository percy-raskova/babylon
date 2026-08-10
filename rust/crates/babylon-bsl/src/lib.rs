//! The Babylon Scripting Language (BSL): the reader, typechecker, load-time
//! bound checker, and fuel evaluator (spec §5). No `unsafe`.
#![forbid(unsafe_code)]
#![warn(clippy::pedantic)]

pub mod bindings;
pub mod bound_checker;
pub mod canonical_ast;
pub mod declarations;
pub mod default_lint;
pub mod domain;
pub mod evaluator;
pub mod exemptions;
pub mod fuel;
pub mod grammar;
pub mod intrinsic_host;
pub mod manifest;
pub mod material_basis;
pub mod metrics;
pub mod mod_anchors;
pub mod reader;
pub mod rule_pipeline;
pub mod scenario;
pub mod scope;
pub mod score_class;
pub mod structural_verbs;
pub mod tick;
pub mod typecheck;
pub mod types;
pub mod vocabulary;
pub mod write_log;

pub use bindings::{
    check_free_variables, parse_bindings, resolve_bindings, BindSource, BindingDecl, BindingError,
    BindingVocabulary,
};
pub use bound_checker::{check_rule, expr_cost, rule_bound, BoundError};
pub use canonical_ast::{canonical_bytes, rules_hash_of, CasError};
pub use declarations::{
    check_intrinsic_name, DeclError, FieldRegistry, OwnedFieldDecl, PROHIBITED_INTRINSIC_NAMES,
    RESERVED_FORM_TAGS,
};
pub use default_lint::{is_allowed, lint_defaults, DefaultAllowlistEntry, DEFAULT_ALLOWLIST};
pub use domain::{resolve_domain, DomainError, RuleDomain};
pub use evaluator::{evaluate, EvalCode, EvalEnv, EvalError, Value};
pub use exemptions::{IntensiveAggregationExemption, EXTENSIVE_INTENSIVE_EXEMPTIONS};
pub use fuel::{CardinalityCeilings, IntrinsicCosts};
pub use grammar::{
    check_arities_and_closed_sets, check_enum_ref_kinds, check_field_init_owners,
    check_graph_flag_placement, GrammarError,
};
pub use intrinsic_host::{EmptyIntrinsicHost, IntrinsicHost};
pub use manifest::{check_rule_against_manifest, CeilingRow, Manifest, ManifestError};
pub use material_basis::{check_rule_surface, SurfaceError, MAX_FUEL};
pub use metrics::{MetricDecl, MetricDomain, MetricError, MetricRegistry};
pub use mod_anchors::{check_anchor, AnchorDecl, AnchorError, AnchorPosition};
pub use reader::{
    read, read_all, Atom, LexCode, ReadError, ReadErrorKind, SExpr, ScaledKind, ScaledLit,
};
pub use rule_pipeline::{
    bind_environment, load_rule, resolve_expr_bindings, LoadContext, LoadError, LoadedRule,
};
pub use scope::{check_element_names, check_foreign_field_scoping, ElementNameError, ScopeError};
pub use score_class::{classify, ClassEnv, ScoreClass};
pub use structural_verbs::{CollectingSink, EffectExecutor, EventSink};
pub use typecheck::{check_selection_scores, typecheck_aggregation, TypeCode, TypeEnv, TypeError};
pub use types::{BslType, FieldDecl, FieldKind};
pub use vocabulary::{render_member, ClosedVocabulary, EnumKind, VocabularyError};
pub use write_log::{CollectingWriteLog, Write, WriteObserver, WriteRecord};
