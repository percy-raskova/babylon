//! The ignored test that prints every run's measures for the record.

use super::support::{self, Push, World};

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
        ("tiers quiet", World::plain().with_tiers()),
        ("tiers P1", World::less_demand().with_tiers()),
        ("tiers P2", World::less_supply().with_tiers()),
        ("tiers P3", World::less_money().with_tiers()),
        ("tiers P4", World::higher_pay().with_tiers()),
        ("fund quiet", World::benefits()),
        ("fund P1", World::benefits().pushed(Push::LessDemand)),
        ("fund P2", World::benefits().pushed(Push::LessSupply)),
        ("fund P3", World::benefits().pushed(Push::LessMoney)),
        ("fund P4", World::benefits().pushed(Push::HigherPay)),
        ("fund P5", World::benefits().pushed(Push::LowerFundTaxes)),
        ("fund tiers quiet", World::benefits().with_tiers()),
        (
            "fund tiers P1",
            World::benefits().with_tiers().pushed(Push::LessDemand),
        ),
        (
            "fund tiers P2",
            World::benefits().with_tiers().pushed(Push::LessSupply),
        ),
        (
            "fund tiers P3",
            World::benefits().with_tiers().pushed(Push::LessMoney),
        ),
        (
            "fund tiers P4",
            World::benefits().with_tiers().pushed(Push::HigherPay),
        ),
        (
            "fund tiers P5",
            World::benefits().with_tiers().pushed(Push::LowerFundTaxes),
        ),
        ("taxed tiers quiet", World::taxed().with_tiers()),
    ];
    for (name, world) in runs {
        println!("{}", support::describe(name, &support::run(&world)));
    }
}
