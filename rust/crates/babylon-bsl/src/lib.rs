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
pub mod error_identity;
pub mod evaluator;
pub mod exemptions;
pub mod fuel;
pub mod grammar;
pub mod intrinsic_host;
pub mod manifest;
pub mod material_basis;
pub mod metrics;
pub mod mod_anchors;
pub mod query;
pub mod reader;
pub mod rule_pipeline;
pub mod same_tick_order;
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
    check_intrinsic_cap, check_intrinsic_name, DeclError, FieldRegistry, OwnedFieldDecl,
    DECLARABLE_INTRINSICS, PROHIBITED_INTRINSIC_NAMES, RESERVED_FORM_TAGS,
};
pub use default_lint::{is_allowed, lint_defaults, DefaultAllowlistEntry, DEFAULT_ALLOWLIST};
pub use domain::{resolve_domain, DomainError, RuleDomain};
pub use error_identity::{identity_of, ErrorIdentity};
pub use evaluator::{evaluate, EvalCode, EvalEnv, EvalError, Value};
pub use exemptions::{IntensiveAggregationExemption, EXTENSIVE_INTENSIVE_EXEMPTIONS};
pub use fuel::{CardinalityCeilings, IntrinsicCosts};
pub use grammar::{
    check_arities_and_closed_sets, check_enum_ref_kinds, check_field_init_owners,
    check_graph_flag_placement, check_string_positions, GrammarError,
};
pub use intrinsic_host::{EmptyIntrinsicHost, IntrinsicHost, KernelIntrinsicHost};
pub use manifest::{check_rule_against_manifest, CeilingRow, Manifest, ManifestError};
pub use material_basis::{check_rule_surface, SurfaceError, MAX_FUEL};
pub use metrics::{MetricDecl, MetricDomain, MetricError, MetricRegistry};
pub use mod_anchors::{check_anchor, AnchorDecl, AnchorError, AnchorPosition};
pub use query::Element;
pub use reader::{
    read, read_all, read_all_spanned, read_spanned, Atom, FormPath, LexCode, ReadError,
    ReadErrorKind, SExpr, ScaledKind, ScaledLit, Span, SpanTable,
};
pub use rule_pipeline::{
    bind_environment, check_unique_rule_ids, load_rule, load_rule_form, resolve_expr_bindings,
    split_content, LoadContext, LoadError, LoadedRule,
};
// `diagnose` re-exported under a qualified name (W2 fix round 1, review
// Minor 4): `babylon_bsl::diagnose` unqualified reads as "diagnose
// anything" at the crate root, alongside dozens of other checkers this
// crate could plausibly want the bare name for later. No caller outside
// `same_tick_order`'s own module uses the unqualified re-export today
// (checked: `rg -n 'babylon_bsl::diagnose\b'` across `rust/`, zero hits
// besides this file), so the rename is free.
pub use same_tick_order::{
    diagnose as diagnose_same_tick_order, Diagnosis, SameTickOrderError, StaleDefaultRead,
    UnresetFanIn, ENFORCE_SAME_TICK_ORDERING,
};
pub use scope::{
    check_element_names, check_foreign_field_scoping, declared_element_names, ElementNameError,
    ScopeError,
};
pub use score_class::{classify, ClassEnv, ScoreClass};
pub use structural_verbs::{CollectingSink, EffectExecutor, EventSink};
pub use typecheck::{check_selection_scores, typecheck_aggregation, TypeCode, TypeEnv, TypeError};
pub use types::{BslType, FieldDecl, FieldKind};
pub use vocabulary::{render_member, ClosedVocabulary, EnumKind, VocabularyError};
pub use write_log::{CollectingWriteLog, Write, WriteObserver, WriteRecord};
