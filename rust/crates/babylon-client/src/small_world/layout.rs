//! Every number of the scene's plane, and where a household or a person stands in it.
//!
//! Plan units: x runs across, y runs from the workplaces (y 0) up to the treasury and the fund
//! (y 11.2). The scene's own point is `plan_to_scene(p, height)`. A position leans on money
//! only (dollars as `f64`): no hour enters a position.

use super::reading::{Party, PaymentKind};
use babylon_circuit_worlds::Place;
use hypergraph_rs::geometry;
use hypergraph_rs::geometry::GeometryError;
use hypergraph_rs::geometry::Point;
use hypergraph_rs::geometry::Positions;
use hypergraph_rs::geometry::Rect;
use hypergraph_rs::geometry::SpreadParams;

/// Where each workplace stands across the plane, by `Workplace::index`; y is 0.
pub const WORKPLACE_X: [f64; 8] = [-11.5, -8.5, -5.5, -2.5, 2.5, 5.5, 8.5, 11.5];
/// The treasury's body.
pub const TREASURY_AT: Point = (-2.2, 11.2);
/// The fund's body.
pub const FUND_AT: Point = (2.2, 11.2);
/// A particle paid wages by a workplace leans to `(x, WAGE_ANCHOR_Y)`: above it.
pub const WAGE_ANCHOR_Y: f64 = 3.3;
/// A particle paid profit by a workplace leans to `(x, PROFIT_ANCHOR_Y)`: below it.
pub const PROFIT_ANCHOR_Y: f64 = -2.6;
/// A particle paid benefits by the treasury leans here.
pub const TREASURY_ANCHOR: Point = (-2.2, 8.3);
/// A particle paid benefits by the fund leans here.
pub const FUND_ANCHOR: Point = (2.2, 8.3);
/// Where a group paid by nobody this period stands, by `Place::index`.
pub const HOME: [Point; 2] = [(-7.0, 6.0), (7.0, 6.0)];
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
/// members stand 3 apart: at a reach of 1.0 its set drew as five separate loops; at 2.2 it is one
/// outline round its four workplaces.
pub const OUTLINE: [(f64, f64, f64); 3] = [(1.0, 0.2, 0.92), (2.2, 0.2, 0.92), (1.6, 0.2, 0.92)];
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

/// Where a body that paid a household anchors it, or `None` for a payment that places no one.
///
/// Wages lean above the workplace, profit below it, benefits to the treasury or the fund.
#[must_use]
pub fn anchor(kind: PaymentKind, payer: Party) -> Option<Point> {
    match (kind, payer) {
        (PaymentKind::Wages, Party::Workplace(w)) => Some((WORKPLACE_X[w.index()], WAGE_ANCHOR_Y)),
        (PaymentKind::Profit, Party::Workplace(w)) => {
            Some((WORKPLACE_X[w.index()], PROFIT_ANCHOR_Y))
        }
        (PaymentKind::Benefits, Party::Treasury) => Some(TREASURY_ANCHOR),
        (PaymentKind::Benefits, Party::Fund) => Some(FUND_ANCHOR),
        _ => None,
    }
}

/// The weighted mean of the anchors that paid a household, or the place's `HOME` when nobody did.
///
/// # Errors
/// `GeometryError` when a weight is negative or not finite.
pub fn stand_at(place: Place, paid: &[(Point, f64)]) -> Result<Point, GeometryError> {
    let anchors: Vec<Point> = paid.iter().map(|(at, _)| *at).collect();
    let weights: Vec<f64> = paid.iter().map(|(_, weight)| *weight).collect();
    Ok(geometry::barycentre(&anchors, &weights)?.unwrap_or(HOME[place.index()]))
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
        let wage = anchor(PaymentKind::Wages, Party::Workplace(CLINIC_A));
        let profit = anchor(PaymentKind::Profit, Party::Workplace(CLINIC_A));
        assert_eq!(wage, Some((-5.5, 3.3)));
        assert_eq!(profit, Some((-5.5, -2.6)));
        assert_eq!(anchor(PaymentKind::Purchases, Party::Fund), None);
        assert_eq!(
            anchor(PaymentKind::Benefits, Party::Treasury),
            Some(TREASURY_ANCHOR)
        );
    }

    #[test]
    fn a_group_paid_by_nobody_stands_at_home_and_one_paid_leans_to_the_larger_share() {
        assert_eq!(stand_at(Place::B, &[]), Ok(HOME[1]));
        let paid = [(TREASURY_ANCHOR, 1.0), (FUND_ANCHOR, 3.0)];
        let at = stand_at(Place::A, &paid).expect("finite weights");
        assert!((at.0 - 1.1).abs() < 1e-12 && (at.1 - 8.3).abs() < 1e-12);
        assert!(stand_at(Place::A, &[(FUND_ANCHOR, -1.0)]).is_err());
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
