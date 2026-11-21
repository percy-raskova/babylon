//! The ignored test that prints every run's measures for the record.

use super::support::{self, World};

/// Print every run's measures for the record: `cargo test --test small_world -- --ignored`.
#[test]
#[ignore = "prints the record's tables; it asserts nothing"]
fn dump_every_run() {
    let runs = [
        ("quiet", World::plain()),
        ("taxed quiet", World::taxed()),
        ("market quiet", World::plain().with_market()),
        ("P1 less demand", World::less_demand()),
        ("P2 less supply", World::less_supply()),
        ("P3 less money", World::less_money()),
        ("P4 higher pay", World::higher_pay()),
        ("market P1", World::less_demand().with_market()),
        ("market P2", World::less_supply().with_market()),
        ("market P3", World::less_money().with_market()),
        ("market P4", World::higher_pay().with_market()),
    ];
    for (name, world) in runs {
        println!("{}", support::describe(name, &support::run(&world)));
    }
}
