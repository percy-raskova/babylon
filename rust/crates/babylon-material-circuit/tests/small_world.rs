//! A small world that opens in balance, and what the engine's rules do to it over 34 periods.
//! The record is `reports/economy-repair-2026-11-20/small-world.md`.

#[path = "small_world/support.rs"]
mod support;

#[path = "small_world/quiet.rs"]
mod quiet;

#[path = "small_world/pushed.rs"]
mod pushed;

#[path = "small_world/tiers.rs"]
mod tiers;

#[path = "small_world/benefits.rs"]
mod benefits;

#[path = "small_world/spare_money.rs"]
mod spare_money;

#[path = "small_world/dump.rs"]
mod dump;
