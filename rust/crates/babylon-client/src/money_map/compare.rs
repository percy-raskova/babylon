//! Period windows and signed changes from the selected county's perspective.
use super::rail;
use super::state::{ConnectionKey, Page};
use babylon_persistence::money_journal::{FlowRow, LaborDirections, LaborFlowRow, PeriodWindow};
use std::fmt::Write as _;

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(super) enum Periods {
    #[default]
    Current,
    WithPrior,
}

impl Periods {
    pub(super) fn window(self, tick: u64) -> Option<PeriodWindow> {
        match self {
            Self::WithPrior if tick > 1 => Some(PeriodWindow {
                first: tick - 1,
                last: tick - 1,
            }),
            _ => None,
        }
    }

    pub(super) fn available(self, tick: u64) -> Self {
        if self.window(tick).is_some() {
            Self::WithPrior
        } else {
            Self::Current
        }
    }
}

// SQL location rows represent the counterparty. Its incoming minus outgoing
// is the negative of the selected county's received minus sent.
fn county_net(value: &str, units: fn(&str) -> String) -> String {
    if value == "0" {
        return units(value);
    }
    value.strip_prefix('-').map_or_else(
        || format!("-{}", units(value)),
        |magnitude| format!("+{}", units(magnitude)),
    )
}

pub(super) fn money_net(row: &FlowRow, tick: u64) -> String {
    let mut result = format!(
        "Net received\n{}",
        county_net(&row.current.net_micros, rail::amount)
    );
    if let (Some(previous), Some(delta), Some(prior)) =
        (&row.comparison, &row.net_change_micros, tick.checked_sub(1))
    {
        write!(
            result,
            "\nPeriod {prior} net\n{}\nChange in net\n{}",
            county_net(&previous.net_micros, rail::amount),
            county_net(delta, rail::amount)
        )
        .expect("String write");
    }
    result
}

fn unknown(d: &LaborDirections) -> Option<String> {
    let counts = [
        &d.outbound.unknown_basis_movements,
        &d.inbound.unknown_basis_movements,
        &d.within.unknown_basis_movements,
    ];
    counts.into_iter().any(|n| n != "0").then(|| {
        format!(
            "unknown prior labor in movements, received {}, sent {}, within {}",
            counts[0], counts[1], counts[2]
        )
    })
}

pub(super) fn labor_net(row: &LaborFlowRow, tick: u64) -> String {
    let mut result = format!(
        "Net recorded hours\n{}",
        county_net(&row.current.net_recorded_micro_hours, rail::labor_hours)
    );
    if let (Some(previous), Some(delta), Some(prior)) = (
        &row.comparison,
        &row.net_change_recorded_micro_hours,
        tick.checked_sub(1),
    ) {
        write!(
            result,
            "\nPeriod {prior} net\n{}\nChange in recorded net\n{}",
            county_net(&previous.net_recorded_micro_hours, rail::labor_hours),
            county_net(delta, rail::labor_hours)
        )
        .expect("String write");
        for (period, directions) in [(tick, &row.current), (prior, previous)] {
            if let Some(coverage) = unknown(directions) {
                write!(result, "\nPeriod {period} {coverage}").expect("String write");
            }
        }
    }
    result
}

pub(super) fn group_net(page: &Page, key: &ConnectionKey, tick: u64) -> Option<String> {
    match page {
        Page::Money(page) => page
            .groups
            .iter()
            .find(|group| group.key == key.peer)
            .map(|group| money_net(group, tick)),
        Page::Labor(page) => page
            .groups
            .iter()
            .find(|group| group.key == key.peer)
            .map(|group| labor_net(group, tick)),
    }
}
