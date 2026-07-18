//! XGI-mirror integration tests: each `tests/<dir>/` maps to XGI's own
//! `tests/<dir>/`, with `main.rs` registering one module per ported XGI
//! test file (cargo auto-discovers `tests/*/main.rs` as a test binary).

mod test_hypergraph;
