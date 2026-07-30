//! The Babylon Scripting Language (BSL): the reader, typechecker, load-time
//! bound checker, and fuel evaluator (spec §5). No `unsafe`.
#![forbid(unsafe_code)]
#![warn(clippy::pedantic)]

pub mod bindings;
pub mod bound_checker;
pub mod canonical_ast;
pub mod default_lint;
pub mod evaluator;
pub mod exemptions;
pub mod fuel;
pub mod intrinsic_host;
pub mod material_basis;
pub mod mod_anchors;
pub mod reader;
pub mod rule_pipeline;
pub mod structural_verbs;
pub mod typecheck;
pub mod types;

pub use bindings::{
    check_free_variables, parse_bindings, resolve_bindings, BindSource, BindingDecl, BindingError,
    BindingVocabulary,
};
pub use bound_checker::{check_rule, expr_cost, rule_bound, BoundError};
pub use canonical_ast::{canonical_bytes, rules_hash_of, CasError};
pub use default_lint::{is_allowed, lint_defaults, DefaultAllowlistEntry, DEFAULT_ALLOWLIST};
pub use evaluator::{evaluate, EvalCode, EvalEnv, EvalError, Value};
pub use exemptions::{IntensiveAggregationExemption, EXTENSIVE_INTENSIVE_EXEMPTIONS};
pub use fuel::{CardinalityCeilings, IntrinsicCosts};
pub use intrinsic_host::{EmptyIntrinsicHost, IntrinsicHost};
pub use material_basis::{check_rule_surface, SurfaceError, MAX_FUEL};
pub use mod_anchors::{check_anchor, AnchorDecl, AnchorError, AnchorPosition};
pub use reader::{
    read, read_all, Atom, LexCode, ReadError, ReadErrorKind, SExpr, ScaledKind, ScaledLit,
};
pub use rule_pipeline::{bind_environment, load_rule, LoadContext, LoadError, LoadedRule};
pub use structural_verbs::{CollectingSink, EffectExecutor, EventSink};
pub use typecheck::{typecheck_aggregation, TypeCode, TypeEnv, TypeError};
pub use types::{BslType, FieldDecl, FieldKind};
