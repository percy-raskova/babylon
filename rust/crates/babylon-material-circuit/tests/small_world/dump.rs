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
        (
            "spare tiers quiet",
            World::plain().with_tiers().with_spare_money(),
        ),
        (
            "spare tiers P4",
            World::higher_pay().with_tiers().with_spare_money(),
        ),
        (
            "spare fund quiet",
            World::benefits().with_tiers().with_spare_money(),
        ),
        (
            "spare fund P5",
            World::benefits()
                .with_tiers()
                .pushed(Push::LowerFundTaxes)
                .with_spare_money(),
        ),
        ("taxed tiers quiet", World::taxed().with_tiers()),
        ("taxed P1", World::taxed().pushed(Push::LessDemand)),
        ("taxed P2", World::taxed().pushed(Push::LessSupply)),
        ("taxed P3", World::taxed().pushed(Push::LessMoney)),
        ("taxed P4", World::taxed().pushed(Push::HigherPay)),
        (
            "taxed tiers P1",
            World::taxed().with_tiers().pushed(Push::LessDemand),
        ),
        (
            "taxed tiers P2",
            World::taxed().with_tiers().pushed(Push::LessSupply),
        ),
        (
            "taxed tiers P3",
            World::taxed().with_tiers().pushed(Push::LessMoney),
        ),
        (
            "taxed tiers P4",
            World::taxed().with_tiers().pushed(Push::HigherPay),
        ),
    ];
    for (name, world) in runs {
        println!("{}", support::describe(name, &support::run(&world)));
    }
}

/// Print the long runs of the spare-money record: hours attended and unmet need at periods 34, 100,
/// 200, 300 and 400, and at 400 every account's cash and unmet need.
#[test]
#[ignore = "prints the record's long-run table; it asserts nothing"]
fn dump_spare_money_long_runs() {
    let pushes = [
        ("plain P2", World::plain().with_tiers(), Push::LessSupply),
        ("plain P4", World::plain().with_tiers(), Push::HigherPay),
        ("fund P2", World::benefits().with_tiers(), Push::LessSupply),
        ("fund P4", World::benefits().with_tiers(), Push::HigherPay),
        (
            "fund P5",
            World::benefits().with_tiers(),
            Push::LowerFundTaxes,
        ),
    ];
    for (name, base, push) in pushes {
        for asking in [false, true] {
            let mut world = base.clone().pushed(push).for_periods(400);
            if asking {
                world = world.with_spare_money();
            }
            let rows = support::run(&world);
            println!("== {name}, rule {}", if asking { "yes" } else { "no" });
            for period in [34, 100, 200, 300, 400] {
                let row = &rows[period - 1];
                println!(
                    "p{period:>3} attended {} {:?} unmet {:?}",
                    row.hours_attended.iter().sum::<u64>(),
                    row.hours_attended,
                    row.unmet
                );
            }
            let last = &rows[399];
            println!("  cash {:?}", last.micro_cash);
            println!("  unmet_by_account {:?}", last.unmet_by_account);
            println!("  public {} {}", last.public_receipts, last.public_payments);
        }
    }
}
