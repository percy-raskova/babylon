//! The table: the period's readings summed by workplace, by class or by place.
//!
//! A group's figures are the sums of its members' own figures. Hours and money are separate
//! columns with separate scales and are never added or compared.

use super::reading::{Party, PeriodReading, ReadingError};
use babylon_circuit_worlds::{Household, Place, Workplace};

/// What the "stored work got back" column shows: it has no figure yet.
pub const NOT_MEASURED: &str = "not measured yet";

const SHARED_LABEL: &str = "Shared: treasury and fund";
const OWNERS_WHO_EARN: &str = "Owners who earn";
const OWNERS_WHO_DO_NOT: &str = "Owners who do not earn";
const EARNERS: &str = "Earners who do not own";
const NEITHER: &str = "Neither owner nor earner";

/// How the rows are grouped.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum Grouping {
    #[default]
    Workplace,
    Class,
    Place,
}

/// One row of the table.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct TableRow {
    pub label: String,
    /// The number of parties the group holds: a workplace row counts itself (1), a class row its
    /// households, a place row its 4 workplaces and 6 households (10). A place row's hours are
    /// its workplaces' only, so they are not the sum of its member rows' hours.
    pub members: usize,
    /// Hours given.
    pub work_given: u64,
    /// Hours paid and not used.
    pub paid_not_used: u64,
    /// Millionths of a dollar taken in.
    pub money_in: i128,
    /// Millionths of a dollar paid out.
    pub money_out: i128,
}

/// The period's table.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Table {
    pub grouping: Grouping,
    pub period: u64,
    pub rows: Vec<TableRow>,
    /// The largest hours figure of the rows shown.
    pub hours_scale: u64,
    /// The largest money figure of the rows shown.
    pub money_scale: i128,
}

/// A group of parties, and whether its hours are those that reached its workplaces or those its
/// households gave. A place holds both ends of the same hours, so it counts the workplaces' only.
struct Group {
    label: String,
    parties: Vec<Party>,
    hours_of_households: bool,
}

fn add_hours(a: u64, b: u64) -> Result<u64, ReadingError> {
    a.checked_add(b).ok_or(ReadingError::Arithmetic)
}

fn add_money(a: i128, b: i128) -> Result<i128, ReadingError> {
    a.checked_add(b).ok_or(ReadingError::Arithmetic)
}

fn row(reading: &PeriodReading, group: &Group) -> Result<TableRow, ReadingError> {
    let mut row = TableRow {
        label: group.label.clone(),
        members: group.parties.len(),
        work_given: 0,
        paid_not_used: 0,
        money_in: 0,
        money_out: 0,
    };
    for flow in &reading.work {
        let counted = group.parties.iter().any(|party| match party {
            Party::Workplace(w) => !group.hours_of_households && *w == flow.workplace,
            Party::Household(h) => group.hours_of_households && *h == flow.household,
            Party::Treasury | Party::Fund => false,
        });
        if counted {
            row.work_given = add_hours(row.work_given, flow.given)?;
            row.paid_not_used = add_hours(row.paid_not_used, flow.idle)?;
        }
    }
    for payment in &reading.payments {
        if group.parties.contains(&payment.payee) {
            row.money_in = add_money(row.money_in, payment.amount)?;
        }
        if group.parties.contains(&payment.payer) {
            row.money_out = add_money(row.money_out, payment.amount)?;
        }
    }
    Ok(row)
}

fn workplace_groups() -> Vec<Group> {
    Workplace::ALL
        .iter()
        .map(|w| Group {
            label: w.label(),
            parties: vec![Party::Workplace(*w)],
            hours_of_households: false,
        })
        .collect()
}

fn class_groups() -> Vec<Group> {
    let households = |keep: fn(Household) -> bool| -> Vec<Party> {
        Household::ALL
            .iter()
            .copied()
            .filter(|h| keep(*h))
            .map(Party::Household)
            .collect()
    };
    let group = |label: &str, parties: Vec<Party>| Group {
        label: label.to_string(),
        parties,
        hours_of_households: true,
    };
    vec![
        // No household of this world is an owner who also earns a wage.
        group(OWNERS_WHO_EARN, Vec::new()),
        group(
            OWNERS_WHO_DO_NOT,
            households(|h| matches!(h, Household::Owner(_))),
        ),
        group(EARNERS, households(|h| matches!(h, Household::Workers(_)))),
        group(
            NEITHER,
            households(|h| matches!(h, Household::Supported(_))),
        ),
    ]
}

fn place_groups() -> Vec<Group> {
    let mut groups: Vec<Group> = Place::ALL
        .iter()
        .map(|place| {
            let mut parties: Vec<Party> = Workplace::ALL
                .iter()
                .filter(|w| w.place == *place)
                .map(|w| Party::Workplace(*w))
                .collect();
            parties.extend(
                Household::ALL
                    .iter()
                    .filter(|h| h.place() == *place)
                    .map(|h| Party::Household(*h)),
            );
            Group {
                label: place.label().to_string(),
                parties,
                hours_of_households: false,
            }
        })
        .collect();
    groups.push(Group {
        label: SHARED_LABEL.to_string(),
        parties: vec![Party::Treasury, Party::Fund],
        hours_of_households: false,
    });
    groups
}

/// The period's readings summed into rows.
///
/// # Errors
/// `ReadingError::Arithmetic` when a sum overflows.
pub fn table(reading: &PeriodReading, grouping: Grouping) -> Result<Table, ReadingError> {
    let groups = match grouping {
        Grouping::Workplace => workplace_groups(),
        Grouping::Class => class_groups(),
        Grouping::Place => place_groups(),
    };
    let rows = groups
        .iter()
        .map(|group| row(reading, group))
        .collect::<Result<Vec<TableRow>, ReadingError>>()?;
    let hours_scale = rows
        .iter()
        .flat_map(|r| [r.work_given, r.paid_not_used])
        .max()
        .unwrap_or(0);
    let money_scale = rows
        .iter()
        .flat_map(|r| [r.money_in, r.money_out])
        .max()
        .unwrap_or(0);
    Ok(Table {
        grouping,
        period: reading.period,
        rows,
        hours_scale,
        money_scale,
    })
}

#[cfg(test)]
mod tests {
    use super::super::reading;
    use super::*;
    use babylon_circuit_worlds::Runner;
    use std::error::Error;

    type TestResult = Result<(), Box<dyn Error>>;

    const DOLLAR: i128 = 1_000_000;

    fn quiet(grouping: Grouping) -> Result<Table, Box<dyn Error>> {
        let mut runner = Runner::open()?;
        let result = runner.step()?.clone();
        Ok(table(&reading::read_period(&result)?, grouping)?)
    }

    fn find<'a>(table: &'a Table, label: &str) -> Result<&'a TableRow, Box<dyn Error>> {
        table
            .rows
            .iter()
            .find(|r| r.label == label)
            .ok_or_else(|| format!("no row {label}").into())
    }

    #[test]
    fn a_workplace_pays_out_what_it_takes_in_a_still_world() -> TestResult {
        let table = quiet(Grouping::Workplace)?;
        assert_eq!(table.rows.len(), 8);
        let expected = [
            ("Place A utility", 120, 1_440),
            ("Place A farm", 40, 1_000),
            ("Place A clinic", 40, 1_200),
            ("Place A shop", 40, 1_520),
        ];
        for (label, work, money) in expected {
            let row = find(&table, label)?;
            assert_eq!(row.work_given, work, "{label}");
            assert_eq!(row.money_in, money * DOLLAR, "{label}");
            assert_eq!(row.money_out, money * DOLLAR, "{label}");
        }
        Ok(())
    }

    #[test]
    fn the_classes_and_places_sum_their_members() -> TestResult {
        let classes = quiet(Grouping::Class)?;
        let earners = find(&classes, EARNERS)?;
        assert_eq!(
            (
                earners.members,
                earners.work_given,
                earners.money_in,
                earners.money_out
            ),
            (8, 480, 4_800 * DOLLAR, 4_800 * DOLLAR)
        );
        for label in [OWNERS_WHO_DO_NOT, NEITHER] {
            let row = find(&classes, label)?;
            assert_eq!(row.members, 2, "{label}");
            assert_eq!(row.work_given, 0, "{label}");
            assert_eq!(
                (row.money_in, row.money_out),
                (1_280 * DOLLAR, 1_280 * DOLLAR)
            );
        }
        let owners_who_earn = find(&classes, OWNERS_WHO_EARN)?;
        assert_eq!(
            (
                owners_who_earn.members,
                owners_who_earn.work_given,
                owners_who_earn.money_in,
                owners_who_earn.money_out
            ),
            (0, 0, 0, 0)
        );

        let places = quiet(Grouping::Place)?;
        for label in ["Place A", "Place B"] {
            let row = find(&places, label)?;
            assert_eq!(row.work_given, 240, "{label}");
            assert_eq!(row.money_in, 8_840 * DOLLAR, "{label}");
            assert_eq!(row.money_out, 8_840 * DOLLAR, "{label}");
        }
        let shared = find(&places, SHARED_LABEL)?;
        assert_eq!(
            (shared.money_in, shared.money_out),
            (1_280 * DOLLAR, 1_280 * DOLLAR)
        );
        Ok(())
    }

    #[test]
    fn the_scales_are_the_largest_figure_of_each_kind() -> TestResult {
        let table = quiet(Grouping::Workplace)?;
        assert_eq!(table.hours_scale, 120);
        assert_eq!(table.money_scale, 1_520 * DOLLAR);
        assert_eq!(table.period, 1);
        assert_eq!(table.grouping, Grouping::Workplace);
        assert_eq!(Grouping::default(), Grouping::Workplace);
        Ok(())
    }
}
