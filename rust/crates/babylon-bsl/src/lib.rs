//! The Babylon Scripting Language (BSL): the reader, typechecker, load-time
//! bound checker, and fuel evaluator (spec §5). No `unsafe`.
#![forbid(unsafe_code)]
#![warn(clippy::pedantic)]

pub mod bound_checker;
pub mod canonical_ast;
pub mod exemptions;
pub mod fuel;
pub mod reader;
pub mod typecheck;
pub mod types;

pub use bound_checker::{check_rule, expr_cost, rule_bound, BoundError};
pub use canonical_ast::{canonical_bytes, rules_hash_of, CasError};
pub use exemptions::{IntensiveAggregationExemption, EXTENSIVE_INTENSIVE_EXEMPTIONS};
pub use fuel::{CardinalityCeilings, IntrinsicCosts};
pub use reader::{
    read, read_all, Atom, LexCode, ReadError, ReadErrorKind, SExpr, ScaledKind, ScaledLit,
};
pub use typecheck::{typecheck_aggregation, TypeCode, TypeEnv, TypeError};
pub use types::{BslType, FieldDecl, FieldKind};
