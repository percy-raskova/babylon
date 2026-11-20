//! The county review as the player reads it: ledger, roster, contact preview, session and food run.
//!
//! Every figure shown here comes from the projection the runtime already fogged: the order of the
//! list, the units paid and unpaid and the counts of who works in each band are public; a
//! position's dollar figures and reasons are earned by contact and arrive only for a position the
//! player has reached a household in. This module formats what it is given and invents nothing.
use super::ui::{self, ActionButton, DetailControls, OrganizerAction, TextPart};
use super::{OrganizerClient, OrganizerInspector};
use crate::human_numbers;
use crate::observer::ObserverSession;
use crate::observer_theme as theme;
use babylon_persistence::runtime_session::{
    Band, BandCount, ContactOutcome, ContactPreview, CountyReviewProjection, OrganizerAidKind,
    OrganizerChoice, OrganizerFoodDelivery, OrganizerPreview, PayMode, PositionEarned, PositionKey,
    PositionView,
};
use bevy::a11y::AccessibilityNode;
use bevy::prelude::*;
use std::fmt::Write as _;

/// Positions shown on one page of the roster.
pub(super) const ROSTER_PAGE_ROWS: usize = 8;

/// The slots of a page, by their index.
const SLOTS: [u8; ROSTER_PAGE_ROWS] = [0, 1, 2, 3, 4, 5, 6, 7];

/// The line every view of this slice carries.
pub(super) const STANDING_LINE: &str = "This slice has no nation, no solidarity and no consciousness. Households act on their own money only.";

const WAGE_READING: &str = "MIM reads wage and salary income inside U.S. borders as labor-aristocracy income or higher, unless the earner is undocumented. Legal status and the wage-against-value term are not in this slice.";
const OWNERSHIP_READING: &str = "\"What is important is not the literal ownership of means of production but access\" (MIM, on the bourgeoisie). The accounts hold only income received from ownership. They hold no access to credit and no net worth.";
const NO_WAGE_READING: &str = "No wage in this period. MIM's reading here turns on nation and legal status, which are not in this slice.";

/// Why a roster slot cannot be chosen.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) enum CountyUnavailable {
    /// The campaign has no county review.
    NoReview,
    /// A past period is open: reading only.
    PastPeriod,
    /// The county holds no session before this period.
    BeforeFirstSession { first_session_period: u64 },
    /// A ruling is already accepted for this period.
    AlreadyChosen,
}

/// The reason a slot is disabled, in the player's words.
pub(super) fn unavailable(reason: CountyUnavailable) -> String {
    match reason {
        CountyUnavailable::NoReview => "This campaign has no county review.".into(),
        CountyUnavailable::PastPeriod => "Past period: reading only. Return Live before changing the organization's commitments.".into(),
        CountyUnavailable::BeforeFirstSession { first_session_period } => format!(
            "The county holds its first session in period {first_session_period}. A contact can be made from period {}.",
            first_session_period.saturating_sub(1)
        ),
        CountyUnavailable::AlreadyChosen => "A ruling is already accepted for this period.".into(),
    }
}

/// What keeps the roster's slots from being chosen right now, if anything.
pub(super) fn why_unavailable(client: &OrganizerClient, period: u64) -> Option<CountyUnavailable> {
    let county = client.county_review.as_ref()?;
    let live = client.view.as_ref().map(|view| view.period);
    if live != Some(period) {
        return Some(CountyUnavailable::PastPeriod);
    }
    if live.and_then(|period| period.checked_add(1)) < Some(county.first_session_period) {
        return Some(CountyUnavailable::BeforeFirstSession {
            first_session_period: county.first_session_period,
        });
    }
    client
        .commitment
        .is_some()
        .then_some(CountyUnavailable::AlreadyChosen)
}

pub(super) const fn band_label(band: Band) -> &'static str {
    match band {
        Band::Top1 => "Top 1%",
        Band::Next9 => "Next 9%",
        Band::Next40 => "Next 40%",
        Band::Bottom50 => "Bottom 50%",
    }
}

const fn band_words(band: Band) -> &'static str {
    match band {
        Band::Top1 => "Does not work. Lives entirely off investments.",
        Band::Next9 => "Some work. Some live off investments or are retired.",
        Band::Next40 => "Lives by selling wage labor. Must work. Can be out of work and looking.",
        Band::Bottom50 => {
            "Works, but is more likely to receive welfare and to need aid. Does not own a home."
        }
    }
}

const fn pay_mode_text(mode: PayMode) -> &'static str {
    match mode {
        PayMode::Wage => "wage",
        PayMode::WorkingOwner => "working owner",
        PayMode::UnpaidFamily => "unpaid family work",
    }
}

fn band_line(count: &BandCount) -> String {
    format!(
        "{} · Designed: {}\n  {} households · {} with someone at work · {} only looking for work · {} with nobody in the labor force · {} people at work · {} people looking for work · {} units",
        band_label(count.band),
        band_words(count.band),
        human_numbers::grouped(u128::from(count.households)),
        human_numbers::grouped(u128::from(count.with_work)),
        human_numbers::grouped(u128::from(count.seeking_only)),
        human_numbers::grouped(u128::from(count.outside_labor_force)),
        human_numbers::grouped(u128::from(count.people_at_work)),
        human_numbers::grouped(u128::from(count.people_seeking)),
        human_numbers::grouped(u128::from(count.units)),
    )
}

/// Who works in each band: county totals, public, worked out again every period.
pub(super) fn who_works(view: &CountyReviewProjection) -> String {
    let mut text = String::from("Who works");
    for count in &view.bands {
        let _ = write!(text, "\n{}", band_line(count));
    }
    text.push_str("\nBands are set at the opening. Homes and wealth are not in this slice.");
    text
}

fn workplace_text(position: &PositionView) -> String {
    match (&position.workplace_label, position.pay_mode) {
        (Some(label), Some(mode)) => format!("{label} ({})", pay_mode_text(mode)),
        (Some(label), None) => label.clone(),
        (None, _) => "no wage · no one in the labor force".into(),
    }
}

/// The structure that names a position: band, group and workplace.
fn position_name(position: &PositionView) -> String {
    format!(
        "{} · {} · {}",
        band_label(position.key.band),
        position.group_label,
        workplace_text(position)
    )
}

/// A position named from the projection, or by its key alone when the roster no longer holds it.
pub(super) fn name_of(view: &CountyReviewProjection, key: PositionKey) -> String {
    view.positions
        .iter()
        .find(|position| position.key == key)
        .map_or_else(
            || {
                format!(
                    "{} · budget group {} · {} at work · {} looking for work · {} units held",
                    band_label(key.band),
                    key.group,
                    key.at_work,
                    key.seeking,
                    key.units
                )
            },
            position_name,
        )
}

fn earned_wage(text: &mut String, earned: &PositionEarned) {
    let _ = write!(
        text,
        " · {} a household, wage tax {}",
        human_numbers::currency(earned.wage_micros_per_household),
        human_numbers::currency(earned.wage_tax_micros_per_household)
    );
}

fn income_lines(text: &mut String, position: &PositionView) {
    let earned = position.earned.as_ref();
    if position.has_wages {
        text.push_str("\n  Wages");
        if let Some(earned) = earned {
            earned_wage(text, earned);
        }
        let _ = write!(text, " · Designed: {WAGE_READING}");
    }
    if position.has_ownership_income {
        text.push_str("\n  Ownership income (the group's total, not a household's)");
        if let Some(earned) = earned {
            let _ = write!(
                text,
                " · {}",
                human_numbers::currency(earned.group_ownership_income_micros)
            );
        }
        let _ = write!(text, " · Designed: {OWNERSHIP_READING}");
    }
    if !position.has_wages && !position.has_ownership_income {
        let _ = write!(text, "\n  Designed: {NO_WAGE_READING}");
    }
    if position.has_support {
        text.push_str("\n  County support (the group's total)");
        if let Some(earned) = earned {
            let _ = write!(
                text,
                " · {}",
                human_numbers::currency(earned.group_support_income_micros)
            );
        }
    }
    if position.has_mutual_aid {
        text.push_str("\n  Mutual aid (the group's total)");
        if let Some(earned) = earned {
            let _ = write!(
                text,
                " · {}",
                human_numbers::currency(earned.group_aid_income_micros)
            );
        }
    }
    text.push_str("\n  Nation: pending.");
}

fn position_line(view: &CountyReviewProjection, position: &PositionView) -> String {
    let key = position.key;
    let mut text = format!(
        "{} · {} at work · {} looking for work · {} units held",
        position_name(position),
        key.at_work,
        key.seeking,
        key.units
    );
    match (position.rank, view.session_period) {
        (Some(rank), _) => {
            let _ = write!(
                text,
                " · rank {rank} · {} units paid · {} unpaid",
                human_numbers::grouped(u128::from(position.units_paid)),
                human_numbers::grouped(u128::from(position.units_unpaid))
            );
        }
        (None, Some(_)) => text.push_str(
            "\n  Not on the last list: its households moved here since the last session.",
        ),
        (None, None) => {}
    }
    income_lines(&mut text, position);
    match &position.earned {
        Some(earned) => {
            let _ = write!(
                text,
                "\n  {} households, {} reached · a unit is worth {} to each",
                human_numbers::grouped(u128::from(earned.households)),
                human_numbers::grouped(u128::from(earned.reached)),
                human_numbers::currency(earned.stake_micros)
            );
        }
        None => text.push_str("\n  Amounts are earned by contact. Reach a household here."),
    }
    text
}

fn slot_position(view: &CountyReviewProjection, page: usize, slot: u8) -> Option<&PositionView> {
    let index = page
        .saturating_mul(ROSTER_PAGE_ROWS)
        .saturating_add(usize::from(slot));
    view.positions.get(index)
}

/// The key of the position in a slot of a page.
pub(super) fn slot_key(
    view: &CountyReviewProjection,
    page: usize,
    slot: u8,
) -> Option<PositionKey> {
    slot_position(view, page, slot).map(|position| position.key)
}

/// The positions of one page, in the order of the county's list.
pub(super) fn roster_page(view: &CountyReviewProjection, page: usize) -> Vec<String> {
    SLOTS
        .iter()
        .filter_map(|slot| slot_position(view, page, *slot))
        .map(|position| position_line(view, position))
        .collect()
}

/// How many pages the roster has; an empty roster has one.
pub(super) fn page_count(view: &CountyReviewProjection) -> usize {
    view.positions.len().div_ceil(ROSTER_PAGE_ROWS).max(1)
}

/// The page one step away from the current one, when it exists.
pub(super) fn page_after(client: &OrganizerClient, step: i8) -> Option<usize> {
    let view = client.county_review.as_ref()?;
    let next = i64::try_from(client.roster_page)
        .ok()?
        .checked_add(i64::from(step))?;
    usize::try_from(next)
        .ok()
        .filter(|page| *page < page_count(view))
}

/// Keeps the roster's page where the new projection still has it.
pub(super) fn keep_page(client: &mut OrganizerClient, next: Option<&CountyReviewProjection>) {
    let period = client.county_review.as_ref().map(|view| view.roster_period);
    client.roster_page = match next {
        Some(view) if Some(view.roster_period) == period => {
            client.roster_page.min(page_count(view).saturating_sub(1))
        }
        _ => 0,
    };
}

/// Whether a control of the roster is shown now, or `None` for a control that is not the roster's.
pub(super) fn control_visible(action: OrganizerAction, client: &OrganizerClient) -> Option<bool> {
    let open = client.inspector == OrganizerInspector::CountyRoster;
    match action {
        OrganizerAction::ChooseRosterSlot(slot) => Some(
            open && client
                .county_review
                .as_ref()
                .and_then(|view| slot_key(view, client.roster_page, slot))
                .is_some(),
        ),
        OrganizerAction::RosterPage(_) => Some(
            open && client
                .county_review
                .as_ref()
                .is_some_and(|view| page_count(view) > 1),
        ),
        _ => None,
    }
}

/// Whether a roster control can be used now.
pub(super) fn control_enabled(
    action: OrganizerAction,
    client: &OrganizerClient,
    session: &ObserverSession,
) -> bool {
    match action {
        OrganizerAction::RosterPage(step) => page_after(client, step).is_some(),
        OrganizerAction::ChooseRosterSlot(slot) => client
            .county_review
            .as_ref()
            .and_then(|view| slot_key(view, client.roster_page, slot))
            .is_some_and(|key| {
                super::workspace::reviewable(client, session, OrganizerChoice::ReviewContact(key))
            }),
        _ => false,
    }
}

/// Moves the roster's page or picks a slot's position; the choice goes through `choose`.
pub(super) fn perform_control(
    action: OrganizerAction,
    client: &mut OrganizerClient,
    choose: impl FnOnce(&mut OrganizerClient, OrganizerChoice),
) -> bool {
    match action {
        OrganizerAction::RosterPage(step) => {
            let Some(page) = page_after(client, step) else {
                return false;
            };
            client.roster_page = page;
            true
        }
        OrganizerAction::ChooseRosterSlot(slot) => {
            let Some(key) = client
                .county_review
                .as_ref()
                .and_then(|view| slot_key(view, client.roster_page, slot))
            else {
                return false;
            };
            choose(client, OrganizerChoice::ReviewContact(key));
            true
        }
        _ => false,
    }
}

/// Whether the slot's position is the one the draft has chosen.
pub(super) fn slot_selected(client: &OrganizerClient, slot: u8) -> bool {
    let OrganizerChoice::ReviewContact(chosen) = client.choice() else {
        return false;
    };
    client
        .county_review
        .as_ref()
        .and_then(|view| slot_key(view, client.roster_page, slot))
        == Some(chosen)
}

/// The lines the roster's slots show, one per position of the current page. Empty unless the
/// roster is open, so the painter formats nothing for a closed inspector.
pub(super) fn roster_lines(client: &OrganizerClient) -> Vec<String> {
    if client.inspector != OrganizerInspector::CountyRoster {
        return Vec::new();
    }
    client
        .county_review
        .as_ref()
        .map_or_else(Vec::new, |view| roster_page(view, client.roster_page))
}

/// The roster's header: the page, who works and why a slot cannot be chosen.
fn roster_header(client: &OrganizerClient, view: &CountyReviewProjection, period: u64) -> String {
    let mut text = who_works(view);
    let pages = page_count(view);
    let _ = write!(
        text,
        "\n\nHousehold positions · page {} of {pages} · {} positions, in the order of the county's list",
        client.roster_page.saturating_add(1),
        view.positions.len()
    );
    if view.session_period.is_none() {
        text.push_str("\nThe county has not held a session yet.");
    }
    if let Some(reason) = why_unavailable(client, period) {
        let _ = write!(text, "\n{}", unavailable(reason));
    }
    text
}

fn ledger_lines(text: &mut String, view: &CountyReviewProjection) {
    for (index, line) in view.ledger.iter().enumerate() {
        let class = if line.first_class {
            "paid before relief"
        } else {
            "relief"
        };
        let _ = write!(
            text,
            "\n {}. {} · {} · {class}",
            index.saturating_add(1),
            line.label,
            human_numbers::currency(line.amount_micros)
        );
    }
}

/// The county's lines in pay order, its cash, the money for relief and the roll.
pub(super) fn ledger(view: &CountyReviewProjection) -> String {
    let mut text = format!(
        "COUNTY LEDGER · period {}\n{}\nCash: {} · spending limit: {} · one unit of relief: {}\n\nLines in pay order",
        view.roster_period,
        view.administration_label,
        human_numbers::currency(view.cash_micros),
        human_numbers::currency(view.spending_limit_micros),
        human_numbers::currency(view.unit_price_micros),
    );
    ledger_lines(&mut text, view);
    let _ = write!(
        text,
        "\nPaid before relief: {}",
        human_numbers::currency(view.first_class_micros)
    );
    match view.relief_micros {
        Some(relief) => {
            let _ = write!(
                text,
                "\nMoney for relief at the last session: {}",
                human_numbers::currency(relief)
            );
        }
        None => {
            let _ = write!(
                text,
                "\nThe county has not held a session yet. Its first is in period {}.",
                view.first_session_period
            );
        }
    }
    text.push_str("\n\nThe roll by budget group");
    for (group, units) in &view.roll {
        let _ = write!(
            text,
            "\n {group} · {} units",
            human_numbers::grouped(u128::from(*units))
        );
    }
    text.push_str("\n\nThe order of the list is public. Read it in the household roster.");
    text
}

fn reasons(text: &mut String, earned: &PositionEarned) {
    let rows = [
        (earned.asked_no_place, "asked, and no place was open"),
        (earned.asked_no_time, "wanted to ask and had no hours"),
        (
            earned.roll_no_time,
            "would have come from the roll and had no hours",
        ),
        (earned.nothing_at_stake, "hold a unit and lose none"),
        (
            earned.not_worth_time,
            "a unit was worth less than their time",
        ),
    ];
    for (count, reason) in rows {
        if count > 0 {
            let _ = write!(
                text,
                "\n     {} households {reason}",
                human_numbers::grouped(u128::from(count))
            );
        }
    }
}

fn session_row(text: &mut String, view: &CountyReviewProjection, position: &PositionView) {
    let rank = position
        .rank
        .map_or_else(|| "unranked".to_owned(), |rank| format!("rank {rank}"));
    let _ = write!(
        text,
        "\n {rank} · {} · {} units listed · {} paid · {} unpaid · {} asked and were paid · {} came from the roll",
        position_name(position),
        human_numbers::grouped(u128::from(position.units_listed)),
        human_numbers::grouped(u128::from(position.units_paid)),
        human_numbers::grouped(u128::from(position.units_unpaid)),
        human_numbers::grouped(u128::from(position.asked_paid)),
        human_numbers::grouped(u128::from(position.came_from_roll)),
    );
    if let Some(earned) = &position.earned {
        reasons(text, earned);
    } else if view.contact.is_some_and(|(key, _)| key == position.key) {
        text.push_str("\n     Amounts and reasons are earned by contact.");
    }
}

const fn contact_outcome_text(outcome: ContactOutcome) -> &'static str {
    match outcome {
        ContactOutcome::Reached => "a household was reached",
        ContactOutcome::NobodyLeft => "nobody was left to reach",
        ContactOutcome::NoSuchPosition => "the position was no longer on the roster",
    }
}

/// The last session: its money, its list in rank order, each body's roll and, for a position the
/// player has contacted, why its reached households stayed home.
pub(super) fn session(view: &CountyReviewProjection, viewed_tick: u64) -> String {
    let Some(held) = view.session_period.filter(|held| *held <= viewed_tick) else {
        return format!(
            "No county session has been held as of period {viewed_tick}. The first is in period {}.",
            view.first_session_period
        );
    };
    let mut text = format!(
        "COUNTY SESSION · period {held}\nMoney for relief: {} · units payable: {} · kept back by an exact tie: {}",
        view.relief_micros.map_or_else(|| "none".into(), human_numbers::currency),
        human_numbers::grouped(u128::from(view.household_units_payable.unwrap_or(0))),
        human_numbers::grouped(u128::from(view.kept_back_units.unwrap_or(0))),
    );
    let _ = write!(
        text,
        "\n{} roll: {} households came from the roll\n{} roll: {} households asked and were paid",
        view.claimants_body_label,
        human_numbers::grouped(u128::from(view.claimants_roll_households.unwrap_or(0))),
        view.aid_body_label,
        human_numbers::grouped(u128::from(view.aid_roll_households.unwrap_or(0))),
    );
    if let Some((key, outcome)) = view.contact {
        let _ = write!(
            text,
            "\nYour contact at the session: {} · {}",
            name_of(view, key),
            contact_outcome_text(outcome)
        );
    }
    text.push_str("\n\nThe list, in rank order");
    for position in view.positions.iter().filter(|p| p.rank.is_some()) {
        session_row(&mut text, view, position);
    }
    text
}

/// The aid the organization's households can spare and what the last run did.
pub(super) fn food_run(client: &OrganizerClient) -> String {
    let mut text = String::from("FOOD RUN · local aid");
    match client
        .aid_preview(OrganizerChoice::LocalAid)
        .and_then(|terms| terms.food.as_ref())
    {
        Some(food) => {
            let spare = food.donor_stock.saturating_sub(food.own_need);
            let _ = write!(
                text,
                "\nParcels the organization's households can spare: {} ({} in stock, {} needed at home)",
                human_numbers::grouped(u128::from(spare)),
                human_numbers::grouped(u128::from(food.donor_stock)),
                human_numbers::grouped(u128::from(food.own_need)),
            );
        }
        None => text.push_str("\nNo local food terms are open this period."),
    }
    let last = client
        .aid_resolutions
        .iter()
        .filter(|row| row.pending.kind == OrganizerAidKind::Local)
        .max_by_key(|row| row.practice.period);
    let Some(run) = last else {
        text.push_str("\nNo local aid run has resolved yet.");
        return text;
    };
    let delivered = match run.support.status {
        OrganizerFoodDelivery::Granted { granted_quantity } => {
            format!(
                "{} parcels delivered",
                human_numbers::grouped(u128::from(granted_quantity))
            )
        }
        OrganizerFoodDelivery::NotRequested => "no food was selected".into(),
        OrganizerFoodDelivery::AwaitingDelivery => "the freight is still on its way".into(),
        OrganizerFoodDelivery::ReceivingRefused => "receiving was refused".into(),
        OrganizerFoodDelivery::TerminalFailure => "the delivery failed".into(),
    };
    let _ = write!(
        text,
        "\nLast run, period {}: {delivered}",
        run.practice.period
    );
    let eaten = client.view.as_ref().and_then(|view| {
        let actor = super::hearing::invitee(view)?.actor_id;
        super::partner_copy::latest_food_report(view, view.period, actor, |_| true)
    });
    match eaten.map(|reading| reading.measure) {
        Some(super::partner_copy::FoodMeasure::Completed {
            consumed, required, ..
        }) => {
            let _ = write!(
                text,
                "\nEaten: {} of {} parcels needed",
                human_numbers::grouped(u128::from(consumed)),
                human_numbers::grouped(u128::from(required))
            );
        }
        _ => text.push_str("\nEaten: no food report has reached you."),
    }
    let _ = write!(
        text,
        "\nHours charged: the donor households {} hours of fulfillment, the organizer {} hours of coordination",
        human_numbers::grouped(u128::from(run.support.material_postings.fulfillment_hours)),
        human_numbers::grouped(u128::from(run.practice.hours_spent)),
    );
    text
}

/// What a contact would do, in words.
pub(super) fn preview(preview: Option<&ContactPreview>, view: &CountyReviewProjection) -> String {
    let Some(preview) = preview else {
        return "No session has closed yet, so there is nothing to preview.".into();
    };
    let outcome = match preview.outcome {
        ContactOutcome::NobodyLeft => "Nobody is left to reach here.".to_owned(),
        ContactOutcome::NoSuchPosition => "This position is no longer on the roster.".to_owned(),
        ContactOutcome::Reached if !preview.asks => "A reached household here would not ask: it already holds its units or a unit is worth less than its time.".to_owned(),
        ContactOutcome::Reached if preview.place_open => {
            let source = preview.taken_from.first().map_or_else(
                || "no listed position".to_owned(),
                |key| name_of(view, *key),
            );
            format!("A place is open. The unit would come from: {source}.")
        }
        ContactOutcome::Reached => "No place is open: every unit below this household is held by a household that pays the same or more.".to_owned(),
    };
    let mut text = format!(
        "{outcome}\nThis preview is worked from period {}, the last close you have seen. The session itself uses the period that has just closed.",
        preview.basis_period
    );
    if preview.outcome == ContactOutcome::Reached && !preview.then_at_stake.is_empty() {
        text.push_str("\nHouseholds that would then have a unit at stake:");
        for key in &preview.then_at_stake {
            let _ = write!(text, "\n {}", name_of(view, *key));
        }
    }
    text
}

/// The review of a contact: its target, its cost, where it lands and what it would do.
pub(super) fn contact_review(
    client: &OrganizerClient,
    reviewed: &OrganizerPreview,
    key: PositionKey,
) -> String {
    let Some(view) = &client.county_review else {
        return unavailable(CountyUnavailable::NoReview);
    };
    format!(
        "Target: {}\nCost: {} of {} organizer-hours\nThe contact lands in period {}, the period of the county's next session.\n{}",
        name_of(view, key),
        human_numbers::grouped(u128::from(reviewed.required_hours)),
        human_numbers::grouped(u128::from(reviewed.available_hours)),
        reviewed.resolves_period,
        preview(reviewed.review.as_ref(), view),
    )
}

fn title(inspector: OrganizerInspector) -> &'static str {
    match inspector {
        OrganizerInspector::CountyLedger => "County ledger",
        OrganizerInspector::CountyRoster => "Household roster",
        OrganizerInspector::CountySession => "County session",
        OrganizerInspector::FoodRun => "Food run",
        _ => "",
    }
}

fn reading(client: &OrganizerClient, period: u64) -> String {
    let Some(view) = &client.county_review else {
        return unavailable(CountyUnavailable::NoReview);
    };
    match client.inspector {
        OrganizerInspector::CountyLedger => ledger(view),
        OrganizerInspector::CountyRoster => roster_header(client, view, period),
        OrganizerInspector::CountySession => session(view, period),
        _ => food_run(client),
    }
}

/// The title and body of one of the four county inspectors.
pub(super) fn inspector(client: &OrganizerClient, period: u64) -> (String, String) {
    let live = client
        .county_review
        .as_ref()
        .map(|view| view.roster_period)
        .or_else(|| client.view.as_ref().map(|view| view.period));
    let mut body = String::new();
    if let Some(live) = live.filter(|live| *live != period) {
        let _ = write!(
            body,
            "These figures are period {live}, the live period. Past sessions are in the Archive.\n\n"
        );
    }
    body.push_str(&reading(client, period));
    if client.inspector != OrganizerInspector::CountyRoster {
        let _ = write!(body, "\n\n{STANDING_LINE}");
    }
    (title(client.inspector).into(), body)
}

/// The roster's controls and slots, spawned once and painted each frame.
pub(super) fn spawn_roster(body: &mut ChildSpawnerCommands) {
    body.spawn((
        ui::column(),
        DetailControls(OrganizerInspector::CountyRoster),
    ))
    .with_children(|panel| {
        panel.spawn(ui::row()).with_children(|pages| {
            ui::button(pages, "Previous", OrganizerAction::RosterPage(-1));
            ui::button(pages, "Next", OrganizerAction::RosterPage(1));
        });
        for slot in SLOTS {
            panel.spawn(ui::column()).with_children(|entry| {
                entry.spawn((ui::text("", 15.0, theme::PAPER), TextPart::RosterLine(slot)));
                ui::button(
                    entry,
                    &format!("Reach a household here ({})", u16::from(slot) + 1),
                    OrganizerAction::ChooseRosterSlot(slot),
                );
            });
        }
        panel.spawn(ui::text(STANDING_LINE, 14.0, theme::GRAY));
    });
}

/// Names each slot's button for assistive technology after the position it would reach.
pub(super) fn paint_labels(
    client: Res<OrganizerClient>,
    mut buttons: Query<(&ActionButton, &mut AccessibilityNode)>,
) {
    if !client.is_changed() {
        return;
    }
    for (button, mut node) in &mut buttons {
        let OrganizerAction::ChooseRosterSlot(slot) = button.0 else {
            continue;
        };
        let number = u16::from(slot) + 1;
        let label = match client
            .county_review
            .as_ref()
            .and_then(|view| slot_position(view, client.roster_page, slot))
        {
            Some(position) => format!(
                "Reach a household here ({number}): {}",
                position_name(position)
            ),
            None => format!("Reach a household here ({number}): no position on this page"),
        };
        if node.label() != Some(label.as_str()) {
            node.set_label(label);
        }
    }
}
