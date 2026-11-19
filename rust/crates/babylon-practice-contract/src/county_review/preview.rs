//! What the next session would do if the organizer reached one more household in a position.
//!
//! The preview is the player's, never the turn's. It runs the session twice on the stored roster,
//! without and with the contact, and reports only what the public record shows: whether a place is
//! open, whose units would be taken and who would then have a unit at stake.
use serde::{Deserialize, Serialize};

use super::codec;
use super::codec::CountyReviewState;
use super::session;
use super::session::{ContactOutcome, SessionRecord, SessionRow};
use super::types::{CountyReviewConfig, CountyReviewError, PositionKey};

/// The difference one contact would make to the next session.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ContactPreview {
    /// The position the contact would reach.
    pub key: PositionKey,
    /// The period of the last close the preview is worked from.
    pub basis_period: u64,
    /// What would come of the contact.
    pub outcome: ContactOutcome,
    /// Whether the household reached would ask for a unit: it holds none, the unit is worth its
    /// hours, and its group has hours left to give the session.
    pub asks: bool,
    /// Whether the county's list would pay the household that asks.
    pub place_open: bool,
    /// Positions that would have a unit left unpaid that the list pays without the contact.
    pub taken_from: Vec<PositionKey>,
    /// Positions that would have more households losing a unit than without the contact.
    pub then_at_stake: Vec<PositionKey>,
}

fn rows_that_rose(
    without: &SessionRecord,
    with: &SessionRecord,
    figure: impl Fn(&SessionRow) -> u64,
) -> Vec<PositionKey> {
    without
        .rows
        .iter()
        .zip(&with.rows)
        .filter(|(before, after)| figure(after) > figure(before))
        .map(|(_, after)| after.key)
        .collect()
}

/// Previews a review contact in `key`, on the last close the player has seen.
///
/// The session runs on a copy of the last facts whose crews' opening counts are the roster's own,
/// because the stored roster has been rolled forward to the next opening. The wages, taxes, cash
/// and hours stay those of the last close. `None` before any close has been seen.
///
/// # Errors
///
/// The refusals of `validate_county_review_state` and of `hold_session`.
pub fn preview_contact(
    config: &CountyReviewConfig,
    state: &CountyReviewState,
    key: PositionKey,
) -> Result<Option<ContactPreview>, CountyReviewError> {
    codec::validate_county_review_state(config, state)?;
    let Some(last) = &state.last_facts else {
        return Ok(None);
    };
    let mut facts = last.clone();
    for crew in &mut facts.crews {
        crew.opening_at_work = state.roster.crew_at_work(crew.crew);
        crew.opening_seeking = state.roster.crew_seeking(crew.crew);
    }
    let without = session::hold_session(config, &state.roster, &facts, None)?;
    let with = session::hold_session(config, &state.roster, &facts, Some(key))?;
    let outcome = with
        .record
        .contact
        .map(|(_, outcome)| outcome)
        .ok_or(CountyReviewError::RosterShape)?;
    let rose = |figure: fn(&SessionRow) -> u64| {
        rows_that_rose(&without.record, &with.record, figure).contains(&key)
    };
    let asks = rose(|row| row.asked);
    let place_open = rose(|row| row.asked_paid);
    Ok(Some(ContactPreview {
        key,
        basis_period: facts.period,
        outcome,
        asks,
        place_open,
        taken_from: rows_that_rose(&without.record, &with.record, |row| row.units_unpaid),
        then_at_stake: rows_that_rose(&without.record, &with.record, |row| row.losers),
    }))
}
