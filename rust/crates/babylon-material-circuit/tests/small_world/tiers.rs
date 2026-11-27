//! The small world with tiers: every household account also wants, per person, one household
//! service in tier 2 and one food and one utility in tier 3. The record is
//! `reports/economy-repair-2026-11-20/small-world.md`, section "Tiers".

use super::support::{self, Snapshot, World};
use babylon_material_circuit::HouseholdStandard;

fn at(rows: &[Snapshot], period: u64) -> &Snapshot {
    &rows[usize::try_from(period - 1).expect("a small period")]
}

/// The quiet run with tiers: each account's cash at its moments of sale is exactly its needs'
/// posted cost, so every want's room is 0 and nothing moves.
#[test]
fn the_balanced_opening_with_tiers_is_still_for_34_periods() {
    let mut planned_ok = 0;
    let rows = support::run_observed(&World::plain().with_tiers(), &mut |period, closed| {
        let clinic = closed
            .service_markets
            .iter()
            .filter(|row| row.process_id == support::clinic_process())
            .collect::<Vec<_>>();
        assert_eq!(clinic.len(), 1, "period {period}");
        assert_eq!(clinic[0].planned_quantity, 40, "period {period}");
        planned_ok += 1;
    });
    assert_eq!(planned_ok, support::PERIODS);
    let first = support::assert_still_rows(&World::plain().with_tiers(), &rows);
    let market = support::run(&World::plain().with_market());
    for (row, plain) in rows.iter().zip(&market) {
        let mut row = row.clone();
        row.want_bought = [0; 3];
        row.tier_values.clear();
        row.standards.clear();
        assert_eq!(&row, plain, "period {}", plain.period);
        assert_eq!(row.planned[0], 120);
        assert_eq!(row.planned[2], 40);
    }
    assert_eq!(first.want_bought, [0, 0, 0]);
    assert_eq!(first.standards.len(), 5);
    for (name, standard) in &first.standards {
        assert_eq!(*standard, HouseholdStandard::GettingBy, "{name}");
    }
    let expected = [
        ("w_utility", [(450, 0), (750, 0)]),
        ("w_farm", [(150, 0), (250, 0)]),
        ("w_clinic", [(150, 0), (250, 0)]),
        ("w_shop", [(150, 0), (250, 0)]),
        ("owner", [(300, 0), (500, 0)]),
    ];
    assert_eq!(first.tier_values.len(), expected.len());
    for (name, values) in expected {
        assert_eq!(first.tier_values[name], values, "{name}");
    }
}

/// What each pinned run says: the first period each site's output is 0 (none: every run), the unmet
/// need at period 34, the largest worker account's cash and the value bought for wants (comforts,
/// luxuries) at periods 1, 13 and 34, and the accounts at each standard
/// (going without, getting by, comfortable, affluent) at those periods.
struct Pinned {
    unmet: [u64; 3],
    worker_cash: [i128; 2],
    bought: [[i128; 2]; 3],
    standards: [[usize; 4]; 3],
}

fn assert_pinned(rows: &[Snapshot], pinned: &Pinned) {
    for site in 0..4 {
        let first_zero = rows.iter().find(|row| row.output[site] == 0);
        assert!(first_zero.is_none(), "site {site} stops");
    }
    assert_eq!(at(rows, 34).unmet, pinned.unmet);
    for (period, cash) in [13, 34].into_iter().zip(pinned.worker_cash) {
        let row = at(rows, period);
        let largest = ["w_utility", "w_farm", "w_clinic", "w_shop"]
            .into_iter()
            .map(|name| row.cash[name])
            .max()
            .expect("four workers");
        assert_eq!(largest, cash, "period {period}");
    }
    for (n, period) in [1, 13, 34].into_iter().enumerate() {
        let row = at(rows, period);
        let mut bought = [0, 0];
        for values in row.tier_values.values() {
            bought[0] += values[0].1;
            bought[1] += values[1].1;
        }
        assert_eq!(
            bought, pinned.bought[n],
            "period {period}: bought for wants"
        );
        let mut counts = [0; 4];
        for standard in row.standards.values() {
            let slot = match standard {
                HouseholdStandard::GoingWithout => 0,
                HouseholdStandard::GettingBy => 1,
                HouseholdStandard::Comfortable => 2,
                HouseholdStandard::Affluent => 3,
            };
            counts[slot] += 1;
        }
        assert_eq!(counts, pinned.standards[n], "period {period}: standards");
    }
}

/// P1 with tiers: returns to the opening state. The owner counts half its persons, so it needs
/// half as much and its cash does not run out: it spends the rest on its comforts and luxuries
/// (5 persons' worth, $150 and $250), so no site's sales fall, no price falls and nothing moves
/// from period 1. Without tiers P1 runs away slowly.
#[test]
fn less_demand_with_tiers_returns_to_the_opening_state() {
    let rows = support::run(&World::less_demand().with_tiers());
    let first = at(&rows, 1);
    assert_eq!(first.price_cents, [1_200, 2_500, 3_000, 3_800]);
    assert_eq!(first.planned, [120, 4, 40, 40]);
    assert_eq!(first.want_bought, [5, 5, 5]);
    assert_eq!((first.cash["owner"], first.cash["clinic"]), (800, 880));
    assert_eq!(first.unmet, [0, 0, 0]);
    for row in &rows {
        let mut same = row.clone();
        same.period = first.period;
        assert_eq!(&same, first, "period {} moved", row.period);
    }
    assert_pinned(
        &rows,
        &Pinned {
            unmet: [0, 0, 0],
            worker_cash: [0, 0],
            bought: [[150, 250]; 3],
            standards: [[0, 4, 0, 1]; 3],
        },
    );
}

/// P2 with tiers: settles in the same depressed band as without them, no site stopping. The
/// households' money is spent on needs: wants are bought in 7 of the 34 periods and never for more
/// than $81, and from period 21 every account goes without.
#[test]
fn less_supply_with_tiers_settles_in_the_depressed_band_buying_almost_no_wants() {
    let rows = support::run(&World::less_supply().with_tiers());
    let bought: Vec<_> = rows
        .iter()
        .map(|row| {
            row.tier_values
                .values()
                .map(|v| v[0].1 + v[1].1)
                .sum::<i128>()
        })
        .collect();
    assert_eq!(bought.iter().filter(|&&value| value > 0).count(), 7);
    assert_eq!(bought.iter().max(), Some(&81));
    assert_pinned(
        &rows,
        &Pinned {
            unmet: [5, 18, 33],
            worker_cash: [20, 24],
            bought: [[0, 0], [0, 0], [0, 0]],
            standards: [[0, 5, 0, 0], [4, 1, 0, 0], [5, 0, 0, 0]],
        },
    );
}

/// P3 with tiers: settles at once, as the quiet run with tiers does, the shop holding half its
/// cash: nothing is short and no account has money beyond its needs.
#[test]
fn less_money_with_tiers_settles_at_once_with_the_shop_at_half_its_cash() {
    let world = World::less_money().with_tiers();
    let rows = support::run(&world);
    let first = at(&rows, 1).clone();
    assert_eq!(first.cash, support::opening_cash(&world));
    assert_eq!(first.cash["shop"], 700);
    for row in &rows {
        let mut same = row.clone();
        same.period = first.period;
        assert_eq!(same, first, "period {} moved", row.period);
    }
    assert_pinned(
        &rows,
        &Pinned {
            unmet: [0, 0, 0],
            worker_cash: [0, 0],
            bought: [[0, 0]; 3],
            standards: [[0, 5, 0, 0]; 3],
        },
    );
}

/// P4 with tiers: cycles in a depressed band, no site stopping. The workers' surplus wage buys a
/// comfort in 15 of the 34 periods ($62, $54 and $56 of care at periods 2, 8 and 13 among them,
/// none for luxuries), and by period 34 every account goes without; the clinic ends at 3 units
/// where it ended at 7. In period 1 the workers' care comfort rungs count in the demand at the $30
/// quote (O8, ADR312 P2 as amended, `clear_ladder_market`), which lifts it above the clinic's 36
/// units, so the short market clears at $31.66 while the need rung fills first and the comforts
/// get nothing; R12 plans the clinic from that demand at the quote (41).
#[test]
fn higher_pay_with_tiers_cycles_in_a_depressed_band_buying_a_few_comforts() {
    let rows = support::run(&World::higher_pay().with_tiers());
    assert_eq!(at(&rows, 1).cleared_cents[2], 3_166);
    let bought: Vec<_> = rows
        .iter()
        .map(|row| row.tier_values.values().map(|v| v[1].1).sum::<i128>())
        .collect();
    assert!(
        bought.iter().all(|&value| value == 0),
        "no luxury is bought"
    );
    assert_pinned(
        &rows,
        &Pinned {
            unmet: [4, 7, 37],
            worker_cash: [19, 12],
            bought: [[0, 0], [56, 0], [0, 0]],
            standards: [[4, 1, 0, 0], [3, 2, 0, 0], [5, 0, 0, 0]],
        },
    );
}
