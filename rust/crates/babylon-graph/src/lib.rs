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
//! This crate exposes the [`substrate::GraphSubstrate`] trait and
//! [`memory::MemoryGraph`], **the in-memory store production logic runs
//! against** (Director ruling 2026-07-31; P27 Phase 2 Slice 1). It was
//! promoted from the Phase-1 `PlaceholderGraph` compile-target because it
//! already honours every ruled invariant — first-class hyperedges with their
//! own id space, members as a sorted set, no pairwise expansion anywhere, the
//! §2.8 loud duplicate-add / absent-remove discipline, and the ADR185 R2
//! removal cascade.
//!
//! **The trait is the insulation, not this type.** The ADR179 T3 capability
//! delta (`docs/reference/graph-storage-capability-delta.md`) rules that
//! hypergraph-rs can back `GraphSubstrate` behind an adapter, *and not yet* —
//! five of its seven deltas are XGI-parity permissiveness where III.11
//! requires loud failure. That swap is DEFERRED, not cancelled, and the trait
//! boundary is what keeps it cheap. Depend on `GraphSubstrate`; construct a
//! `MemoryGraph`.
#![forbid(unsafe_code)]
#![warn(clippy::pedantic)]

pub mod backfire;
pub mod capacity;
pub mod conformance;
pub mod dossier;
pub mod exposure;
pub mod hypergraph_store;
pub mod induced;
pub mod memory;
pub mod state_hash;
pub mod substrate;
