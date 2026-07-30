//! The graph substrate crate (spec §6, crate table). **Amendment D ruled
//! NATIVE HYPEREDGE** (2026-07-29; Amendment AE clause (vi),
//! `ai/_inbox/amendment-d-analysis-p27.md` §9): hyperedges are first-class
//! objects in this crate's exposed model and type system — membership is one
//! typed hyperedge, never a clique expansion, and never *exposed* as a
//! bipartite incidence encoding. Levi/incidence is a permitted INTERNAL
//! storage strategy (what `hypergraph-rs` implements); nothing in the exposed
//! API reveals it. The strictly dyadic morphism API (II.9) lives alongside it
//! in the same trait, separated by type (D-2).
//!
//! This crate exposes ONLY the [`substrate::GraphSubstrate`] trait plus a
//! [`placeholder::PlaceholderGraph`] toy implementation sufficient to let
//! downstream crates (`babylon-bsl`'s typed structural verbs, the conformance
//! corpus) compile and typecheck against a real trait object today. The
//! concrete production storage type is Phase 2 work. Do not build production
//! logic against `PlaceholderGraph` — it is a compile-target, not a
//! foundation.
#![forbid(unsafe_code)]
#![warn(clippy::pedantic)]

pub mod induced;
pub mod placeholder;
pub mod substrate;
