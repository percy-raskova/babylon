//! The Babylon Scripting Language (BSL): the reader, typechecker, load-time
//! bound checker, and fuel evaluator (spec §5). No `unsafe`.
#![forbid(unsafe_code)]
#![warn(clippy::pedantic)]

pub mod reader;

pub use reader::{
    read, read_all, Atom, LexCode, ReadError, ReadErrorKind, SExpr, ScaledKind, ScaledLit,
};

pub mod exemptions;
pub mod typecheck;
pub mod types;

pub use exemptions::{IntensiveAggregationExemption, EXTENSIVE_INTENSIVE_EXEMPTIONS};
pub use typecheck::{typecheck_aggregation, TypeCode, TypeEnv, TypeError};
pub use types::{BslType, FieldDecl, FieldKind};
