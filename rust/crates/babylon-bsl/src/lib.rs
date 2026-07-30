//! The Babylon Scripting Language (BSL): the reader, typechecker, load-time
//! bound checker, and fuel evaluator (spec §5). No `unsafe`.
#![forbid(unsafe_code)]
#![warn(clippy::pedantic)]

pub mod reader;

pub use reader::{
    read, read_all, Atom, LexCode, ReadError, ReadErrorKind, SExpr, ScaledKind, ScaledLit,
};
