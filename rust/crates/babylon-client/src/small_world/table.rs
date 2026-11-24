//! The table: the period's readings summed by workplace, by class or by place.
//!
//! A group's figures are the sums of its members' own figures. Hours and money are separate
//! columns with separate scales and are never added or compared.

use super::reading::{Party, PeriodReading, ReadingError};
use babylon_circuit_worlds::{Household, PeriodHours, PeriodResult, Place, Workplace};

/// Micro-hours in one hour.
const MICRO_HOURS: u128 = 1_000_000;

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

/// One row of the table's second set. `None` is a dash.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct HoursRow {
    pub label: String,
    /// Hours given.
    pub given: Option<u64>,
    /// Micro-hours in what reached the group's homes.
    pub back: Option<u128>,
    /// Of `back`, micro-hours that came through wages.
    pub for_work: Option<u128>,
    /// Of `back`, micro-hours that came through profit.
    pub by_owning: Option<u128>,
    /// Of `back`, micro-hours that came through benefits and public payments.
    pub support: Option<u128>,
}

/// The period's second set of columns. `scale`: the largest figure of the rows shown, in micro-hours (given
/// counted as micro-hours for the bars).
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct HoursTable {
    pub grouping: Grouping,
    pub period: u64,
    pub rows: Vec<HoursRow>,
    pub scale: u128,
}

fn add_micro(a: u128, b: u128) -> Result<u128, ReadingError> {
    a.checked_add(b).ok_or(ReadingError::Arithmetic)
}

fn unknown(what: impl std::fmt::Debug) -> ReadingError {
    ReadingError::UnknownParty(format!("{what:?} in the record of hours"))
}

fn hours_row(hours: &PeriodHours, group: &Group) -> Result<HoursRow, ReadingError> {
    let mut row = HoursRow {
        label: group.label.clone(),
        given: None,
        back: None,
        for_work: None,
        by_owning: None,
        support: None,
    };
    if group
        .parties
        .iter()
        .any(|party| matches!(party, Party::Treasury | Party::Fund))
    {
        return Ok(row);
    }
    let workplaces: Vec<Workplace> = group
        .parties
        .iter()
        .filter_map(|party| match party {
            Party::Workplace(w) => Some(*w),
            _ => None,
        })
        .collect();
    let households: Vec<Household> = group
        .parties
        .iter()
        .filter_map(|party| match party {
            Party::Household(h) => Some(*h),
            _ => None,
        })
        .collect();
    if households.is_empty() && !workplaces.is_empty() {
        let mut given = 0_u64;
        for workplace in workplaces {
            let held = hours
                .workplace(workplace)
                .ok_or_else(|| unknown(workplace))?;
            given = add_hours(given, held.given)?;
        }
        row.given = Some(given);
        return Ok(row);
    }
    let (mut given, mut back, mut work, mut owning, mut support) = (0_u64, 0, 0, 0, 0);
    for household in households {
        let held = hours
            .household(household)
            .ok_or_else(|| unknown(household))?;
        given = add_hours(given, held.given)?;
        back = add_micro(back, held.back_micro_hours)?;
        work = add_micro(work, held.claims.work)?;
        owning = add_micro(owning, held.claims.owning)?;
        support = add_micro(support, held.claims.support)?;
    }
    row.given = Some(given);
    row.back = Some(back);
    row.for_work = Some(work);
    row.by_owning = Some(owning);
    row.support = Some(support);
    Ok(row)
}

fn hours_scale_of(rows: &[HoursRow]) -> Result<u128, ReadingError> {
    let mut scale = 0_u128;
    for row in rows {
        let given = row
            .given
            .map(|g| {
                u128::from(g)
                    .checked_mul(MICRO_HOURS)
                    .ok_or(ReadingError::Arithmetic)
            })
            .transpose()?;
        for figure in [given, row.back, row.for_work, row.by_owning, row.support]
            .into_iter()
            .flatten()
        {
            scale = scale.max(figure);
        }
    }
    Ok(scale)
}

/// The second set of the period, grouped as the table's tabs; `None` without a record of hours.
///
/// # Errors
/// `ReadingError::Arithmetic` when a sum overflows; `ReadingError::UnknownParty` for a household or workplace
/// the record does not hold.
pub fn hours_table(
    result: &PeriodResult,
    grouping: Grouping,
) -> Result<Option<HoursTable>, ReadingError> {
    let Some(hours) = &result.hours else {
        return Ok(None);
    };
    let groups = match grouping {
        Grouping::Workplace => workplace_groups(),
        Grouping::Class => class_groups(),
        Grouping::Place => place_groups(),
    };
    let rows = groups
        .iter()
        .map(|group| hours_row(hours, group))
        .collect::<Result<Vec<HoursRow>, ReadingError>>()?;
    let scale = hours_scale_of(&rows)?;
    Ok(Some(HoursTable {
        grouping,
        period: result.period,
        rows,
        scale,
    }))
}

#[cfg(test)]
mod tests {
    use super::super::{reading, scene};
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

    fn hours_of_period(period: usize, grouping: Grouping) -> Result<HoursTable, Box<dyn Error>> {
        let mut runner = scene::open_runner()?;
        for _ in 0..period {
            runner.step()?;
        }
        let result = runner.history()[period - 1].clone();
        hours_table(&result, grouping)?.ok_or_else(|| "no record of hours".into())
    }

    fn hours_row<'a>(table: &'a HoursTable, label: &str) -> Result<&'a HoursRow, Box<dyn Error>> {
        table
            .rows
            .iter()
            .find(|r| r.label == label)
            .ok_or_else(|| format!("no row {label}").into())
    }

    #[test]
    fn the_hours_table_is_the_record_s() -> TestResult {
        let mut runner = scene::open_runner()?;
        for _ in 0..2 {
            runner.step()?;
        }
        let result = runner.history()[1].clone();
        let record = result.hours.clone().ok_or("no record of hours")?;
        let sum_of = |keep: fn(Household) -> bool| -> Result<HoursRow, Box<dyn Error>> {
            let mut row = HoursRow {
                label: String::new(),
                given: Some(0),
                back: Some(0),
                for_work: Some(0),
                by_owning: Some(0),
                support: Some(0),
            };
            for (household, hours) in record.households.iter().filter(|(h, _)| keep(*h)) {
                let _ = household;
                row.given = row.given.map(|g| g + hours.given);
                row.back = row.back.map(|b| b + hours.back_micro_hours);
                row.for_work = row.for_work.map(|b| b + hours.claims.work);
                row.by_owning = row.by_owning.map(|b| b + hours.claims.owning);
                row.support = row.support.map(|b| b + hours.claims.support);
            }
            Ok(row)
        };
        let class = hours_table(&result, Grouping::Class)?.ok_or("no table")?;
        assert_eq!(class.period, 2);
        for (label, keep) in [
            (
                OWNERS_WHO_DO_NOT,
                (|h| matches!(h, Household::Owner(_))) as fn(Household) -> bool,
            ),
            (EARNERS, |h| matches!(h, Household::Workers(_))),
            (NEITHER, |h| matches!(h, Household::Supported(_))),
        ] {
            let mut expected = sum_of(keep)?;
            expected.label = label.to_owned();
            assert_eq!(hours_row(&class, label)?, &expected, "{label}");
        }
        let workplaces = hours_table(&result, Grouping::Workplace)?.ok_or("no table")?;
        for workplace in Workplace::ALL {
            let row = hours_row(&workplaces, &workplace.label())?;
            let given = record.workplace(workplace).ok_or("no workplace")?.given;
            assert_eq!(row.given, Some(given));
            assert_eq!(
                (row.back, row.for_work, row.by_owning, row.support),
                (None, None, None, None)
            );
        }
        let places = hours_table(&result, Grouping::Place)?.ok_or("no table")?;
        let shared = hours_row(&places, SHARED_LABEL)?;
        assert_eq!(
            (
                shared.given,
                shared.back,
                shared.for_work,
                shared.by_owning,
                shared.support
            ),
            (None, None, None, None, None)
        );
        let place_a = hours_row(&places, "Place A")?;
        assert_eq!(
            (place_a.given, place_a.back),
            (Some(240), Some(200_000_000))
        );
        let largest = places
            .rows
            .iter()
            .flat_map(|r| [r.given.map(|g| u128::from(g) * 1_000_000), r.back])
            .flatten()
            .max()
            .unwrap_or(0);
        assert_eq!(places.scale, largest);
        Ok(())
    }

    #[test]
    fn the_second_set_has_no_column_for_not_recorded() -> TestResult {
        let classes = hours_of_period(1, Grouping::Class)?;
        let owners = hours_row(&classes, OWNERS_WHO_DO_NOT)?;
        assert_eq!(owners.by_owning, Some(0));
        assert_eq!(owners.back, Some(64_000_000));
        Ok(())
    }

    #[test]
    fn a_period_without_a_record_has_no_second_set() -> TestResult {
        let mut runner = Runner::open()?;
        let result = runner.step()?.clone();
        assert_eq!(hours_table(&result, Grouping::Class)?, None);
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
