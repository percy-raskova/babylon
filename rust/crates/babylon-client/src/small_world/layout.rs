//! Every number of the scene's plane, and where a household or a person stands in it.
//!
//! Plan units: x runs across, y runs from the workplaces (y 0) up to the treasury and the fund
//! (y 11.2). The scene's own point is `plan_to_scene(p, height)`. A position leans on money
//! only (dollars as `f64`): no hour enters a position.

use super::reading::{Party, PaymentKind};
use babylon_circuit_worlds::{Household, Place, Workplace};
use hypergraph_rs::geometry;
use hypergraph_rs::geometry::GeometryError;
use hypergraph_rs::geometry::Point;
use hypergraph_rs::geometry::Positions;
use hypergraph_rs::geometry::Rect;
use hypergraph_rs::geometry::SpreadParams;

/// Where each workplace stands across the plane, by `Workplace::index`; y is 0. They stand 2.8
/// apart: at 3 an owner's outline that held them all ran past the plane's edge.
pub const WORKPLACE_X: [f64; 8] = [-11.0, -8.2, -5.4, -2.6, 2.6, 5.4, 8.2, 11.0];
/// The treasury's body.
pub const TREASURY_AT: Point = (-2.2, 11.2);
/// The fund's body.
pub const FUND_AT: Point = (2.2, 11.2);
/// A particle paid wages by a workplace leans to `(x, WAGE_ANCHOR_Y)`: above it.
pub const WAGE_ANCHOR_Y: f64 = 3.3;
/// A particle paid profit by a workplace leans to `(x, PROFIT_ANCHOR_Y)`: below it.
pub const PROFIT_ANCHOR_Y: f64 = -2.4;
/// A particle paid benefits by the treasury leans here.
pub const TREASURY_ANCHOR: Point = (-2.2, 8.3);
/// A particle paid benefits by the fund leans here.
pub const FUND_ANCHOR: Point = (2.2, 8.3);
/// How far a household paid benefits leans to its own place's side, by `Place::index`. The two
/// places' households are paid alike, so without it they stand on one point and the spread parts
/// them on a slant; with it Place A's stands left of Place B's, 2 apart.
pub const BENEFIT_LEAN: [f64; 2] = [-1.0, 1.0];
/// How far behind its workplace's wage anchor a workers' group paid by nobody stands (plan units, up).
pub const UNPAID_BEHIND: f64 = 1.6;
/// The least distance between two groups, and the steps of the spread.
pub const GROUP_SPREAD: (f64, u32) = (1.6, 8);
/// The least distance between two persons, and the steps of the spread.
pub const PERSON_SPREAD: (f64, u32) = (0.4, 8);
/// What the spread keeps its points inside.
pub const SPREAD_BOUNDS: Rect = (-12.8, -4.2, 12.8, 12.6);
/// What the view is fitted to: 26.4 wide, 17.7 deep.
pub const PLANE: Rect = (-13.2, -4.6, 13.2, 13.1);
/// Persons across a cluster.
pub const PERSON_COLUMNS: usize = 4;
/// The distance between persons of a cluster.
pub const PERSON_STEP: f64 = 0.45;
/// `OutlineParams::new(reach, cell, share)` of a workforce, an owner and the fund. An owner's
/// workplaces stand 2.8 apart: at a reach of 1.0 its set drew as five separate loops; at 2.2,
/// with the workplaces 3 apart, it was one outline with a notch beside its weakest workplace; at
/// 2.3 the hills overlap, the notch is gone and the outline stays inside the plane. The fund's
/// reach is 1.3, so that its outline stays clear of the fund's label.
pub const OUTLINE: [(f64, f64, f64); 3] = [(1.0, 0.2, 0.92), (2.3, 0.2, 0.92), (1.3, 0.2, 0.92)];
/// The height of a particle.
pub const PARTICLE_Y: f32 = 0.10;
/// The height of a mark's ends.
pub const MARK_Y: f32 = 0.15;
/// The height of a body's hours ring.
pub const HOURS_RING_Y: f32 = 0.03;
/// The height of a body's money ring.
pub const MONEY_RING_Y: f32 = 0.035;
/// The height of the outlines of workforces, owners and the fund.
pub const SET_Y: [f32; 3] = [0.02, 0.04, 0.06];

/// Where a body that paid a household of `place` anchors it, or `None` for a payment that places
/// no one.
///
/// Wages lean above the workplace, profit below it, benefits to the treasury or the fund, on the
/// household's own side of it (`BENEFIT_LEAN`).
#[must_use]
pub fn anchor(kind: PaymentKind, payer: Party, place: Place) -> Option<Point> {
    let lean = BENEFIT_LEAN[place.index()];
    match (kind, payer) {
        (PaymentKind::Wages, Party::Workplace(w)) => Some((WORKPLACE_X[w.index()], WAGE_ANCHOR_Y)),
        (PaymentKind::Profit, Party::Workplace(w)) => {
            Some((WORKPLACE_X[w.index()], PROFIT_ANCHOR_Y))
        }
        (PaymentKind::Benefits, Party::Treasury) => {
            Some((TREASURY_ANCHOR.0 + lean, TREASURY_ANCHOR.1))
        }
        (PaymentKind::Benefits, Party::Fund) => Some((FUND_ANCHOR.0 + lean, FUND_ANCHOR.1)),
        _ => None,
    }
}

/// Where a group paid by nobody this period stands. A workers' group: behind its own workplace's
/// people, `(WORKPLACE_X[w.index()], WAGE_ANCHOR_Y + UNPAID_BEHIND)`. An owners' group: on the profit
/// row under the middle of its place's four workplaces. A supported group: at the fund's anchor on
/// its own side. No hour enters a home: it is a constant of the household.
#[must_use]
pub fn home_of(h: Household) -> Point {
    match h {
        Household::Workers(w) => (WORKPLACE_X[w.index()], WAGE_ANCHOR_Y + UNPAID_BEHIND),
        Household::Owner(place) => {
            let of_place: Vec<f64> = Workplace::ALL
                .into_iter()
                .filter(|w| w.place == place)
                .map(|w| WORKPLACE_X[w.index()])
                .collect();
            let n = f64::from(u8::try_from(of_place.len()).unwrap_or(u8::MAX));
            (of_place.iter().sum::<f64>() / n, PROFIT_ANCHOR_Y)
        }
        Household::Supported(place) => (FUND_ANCHOR.0 + BENEFIT_LEAN[place.index()], FUND_ANCHOR.1),
    }
}

/// The weighted mean of the anchors that paid a household, or `home` when nobody did.
///
/// # Errors
/// `GeometryError` when a weight is negative or not finite.
pub fn stand_at(home: Point, paid: &[(Point, f64)]) -> Result<Point, GeometryError> {
    let anchors: Vec<Point> = paid.iter().map(|(at, _)| *at).collect();
    let weights: Vec<f64> = paid.iter().map(|(_, weight)| *weight).collect();
    Ok(geometry::barycentre(&anchors, &weights)?.unwrap_or(home))
}

/// A cluster of `n` persons round a point: four across, rows going `+y`.
#[must_use]
pub fn cluster(at: Point, n: usize) -> Vec<Point> {
    (0..n)
        .map(|k| {
            let across = column(k) - column_offset(n);
            (at.0 + across * PERSON_STEP, at.1 + row(k) * PERSON_STEP)
        })
        .collect()
}

#[expect(
    clippy::cast_precision_loss,
    reason = "a column or row of a cluster is below 2^53"
)]
fn column(k: usize) -> f64 {
    (k % PERSON_COLUMNS) as f64
}

#[expect(
    clippy::cast_precision_loss,
    reason = "a column or row of a cluster is below 2^53"
)]
fn row(k: usize) -> f64 {
    (k / PERSON_COLUMNS) as f64
}

#[expect(
    clippy::cast_precision_loss,
    reason = "a count of persons is below 2^53"
)]
fn column_offset(n: usize) -> f64 {
    (n.min(PERSON_COLUMNS) as f64 - 1.0) / 2.0
}

/// Spread points apart by a fixed number of steps in a fixed order, keeping each id.
///
/// # Errors
/// `GeometryError` for a point that is not finite.
pub fn spread_apart(
    points: &[(String, Point)],
    (distance, steps): (f64, u32),
) -> Result<Positions, GeometryError> {
    let mut positions = Positions::new();
    for (id, at) in points {
        positions.insert(id.clone(), *at);
    }
    let mut params = SpreadParams::new(distance, steps);
    params.bounds = Some(SPREAD_BOUNDS);
    geometry::spread(&mut positions, &[], &params)?;
    Ok(positions)
}

#[cfg(test)]
mod tests {
    use super::*;
    use babylon_circuit_worlds::{Kind, Workplace};

    const CLINIC_A: Workplace = Workplace {
        place: Place::A,
        kind: Kind::Clinic,
    };

    #[test]
    fn wages_lean_above_a_workplace_and_profit_below_it() {
        let wage = anchor(PaymentKind::Wages, Party::Workplace(CLINIC_A), Place::A);
        let profit = anchor(PaymentKind::Profit, Party::Workplace(CLINIC_A), Place::B);
        assert_eq!(wage, Some((-5.4, 3.3)));
        assert_eq!(profit, Some((-5.4, -2.4)));
        assert_eq!(anchor(PaymentKind::Purchases, Party::Fund, Place::A), None);
        assert_eq!(
            anchor(PaymentKind::Benefits, Party::Treasury, Place::A),
            Some((-3.2, 8.3))
        );
        assert_eq!(
            anchor(PaymentKind::Benefits, Party::Fund, Place::B),
            Some((3.2, 8.3))
        );
    }

    #[test]
    fn a_group_paid_by_nobody_stands_at_its_own_home() {
        let near = |a: Point, b: Point| (a.0 - b.0).abs() < 1e-12 && (a.1 - b.1).abs() < 1e-12;
        assert!(near(home_of(Household::Workers(CLINIC_A)), (-5.4, 4.9)));
        assert!(near(home_of(Household::Owner(Place::A)), (-6.8, -2.4)));
        assert!(near(home_of(Household::Owner(Place::B)), (6.8, -2.4)));
        assert!(near(home_of(Household::Supported(Place::A)), (1.2, 8.3)));
        assert!(near(home_of(Household::Supported(Place::B)), (3.2, 8.3)));
        for (k, a) in Household::ALL.into_iter().enumerate() {
            assert_eq!(stand_at(home_of(a), &[]), Ok(home_of(a)));
            for b in Household::ALL.into_iter().skip(k + 1) {
                let (p, q) = (home_of(a), home_of(b));
                assert!(
                    (p.0 - q.0).hypot(p.1 - q.1) >= GROUP_SPREAD.0,
                    "{a:?} and {b:?}"
                );
            }
        }
        let paid = [(TREASURY_ANCHOR, 1.0), (FUND_ANCHOR, 3.0)];
        let at = stand_at(home_of(Household::Supported(Place::A)), &paid).expect("finite weights");
        assert!((at.0 - 1.1).abs() < 1e-12 && (at.1 - 8.3).abs() < 1e-12);
        let home = home_of(Household::Owner(Place::A));
        assert!(stand_at(home, &[(FUND_ANCHOR, -1.0)]).is_err());
    }

    #[test]
    fn a_cluster_is_four_across_with_rows_going_up() {
        let four = cluster((0.0, 0.0), 4);
        assert_eq!(four.len(), 4);
        assert!((four[0].0 + 0.675).abs() < 1e-12 && four[0].1 == 0.0);
        assert!((four[3].0 - 0.675).abs() < 1e-12);
        let five = cluster((1.0, 2.0), 5);
        assert!((five[4].0 - (1.0 - 0.675)).abs() < 1e-12);
        assert!((five[4].1 - 2.45).abs() < 1e-12);
        let two = cluster((0.0, 0.0), 2);
        assert!((two[0].0 + 0.225).abs() < 1e-12 && (two[1].0 - 0.225).abs() < 1e-12);
    }

    #[test]
    fn the_spread_keeps_two_stacked_points_apart_and_their_midpoint() {
        let points = vec![("a".to_string(), (1.1, 8.3)), ("b".to_string(), (1.1, 8.3))];
        let apart = spread_apart(&points, GROUP_SPREAD).expect("finite points");
        let a = apart.get("a").expect("a placed point");
        let b = apart.get("b").expect("a placed point");
        assert!((f64::midpoint(a.0, b.0) - 1.1).abs() < 1e-9);
        assert!((f64::midpoint(a.1, b.1) - 8.3).abs() < 1e-9);
        assert!((a.0 - b.0).hypot(a.1 - b.1) > 1.0);
    }
}
