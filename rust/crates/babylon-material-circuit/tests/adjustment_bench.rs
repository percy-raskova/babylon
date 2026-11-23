//! The bench of the restoring-forces rounds, in the repository: the doubled world of
//! `babylon-circuit-worlds` stepped by its `Runner`, its rows reduced to the prototype's columns and compared
//! by digest with the rows the prototype wrote.
//!
//! The quick test and the unit tests run by default. The long tests (`reproduces_*`) are ignored; run them
//! with `mise run rust:test:q -- -p babylon-material-circuit --test adjustment_bench -E
//! 'test(/^reproduces_/)' --run-ignored only`.

#[path = "adjustment_bench/compare.rs"]
mod compare;
#[path = "adjustment_bench/rows.rs"]
mod rows;
#[path = "adjustment_bench/runs.rs"]
mod runs;

include!("adjustment_bench/sets.rs");
