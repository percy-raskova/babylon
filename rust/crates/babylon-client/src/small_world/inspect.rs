//! What a pick shows: the figures of one body, one household group or person, or one set, for
//! the period shown. Every figure is read from the period's result and its reading; hours and
//! money are printed apart and never added together.

use super::frame::{self, FrameError, Picture};
use super::reading::{Party, PaymentKind};
use super::scene::SceneBody;
use crate::human_numbers;
use babylon_circuit_worlds::{Good, Household, PeriodResult, Place, Workplace};
use babylon_material_circuit::AccountId;
use bevy::picking::pointer::PointerButton;
use bevy::prelude::*;
use hypergraph_rs_bevy::{ParticleId, SetId};

/// What the player clicked.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Pick {
    /// A workplace, the treasury or the fund.
    Body(Party),
    /// A household group (`household:N`) or one person (`person:N:k`).
    Particle(String),
    /// A set (`workforce:a:farm`, `owner:a`, `fund`).
    Set(String),
}

/// The pick the inspector shows; none until the player clicks, and none after a click on empty
/// space.
#[derive(Resource, Clone, Debug, Default, PartialEq, Eq)]
pub struct ScenePick(pub Option<Pick>);

type Rows = Vec<(String, String)>;

fn row(label: &str, value: impl Into<String>) -> (String, String) {
    (label.to_owned(), value.into())
}

fn missing(what: &str) -> FrameError {
    FrameError::Edge(what.to_owned())
}

fn hours_text(hours: u64) -> String {
    human_numbers::grouped(u128::from(hours))
}

fn account_of(party: Party) -> AccountId {
    match party {
        Party::Workplace(w) => AccountId::Site(w.site_id()),
        Party::Household(h) => AccountId::Household(h.principal()),
        Party::Treasury => AccountId::Public(babylon_circuit_worlds::treasury()),
        Party::Fund => AccountId::Public(babylon_circuit_worlds::fund()),
    }
}

fn good_name(good: Good) -> &'static str {
    match good {
        Good::Food => "food",
        Good::Power => "power",
        Good::Care => "care",
    }
}

/// The household a group id names, and the person's number when the id is a person's.
fn household_of(id: &str) -> Option<(Household, Option<usize>)> {
    if let Some(rest) = id.strip_prefix("person:") {
        let (group, k) = rest.split_once(':')?;
        let k = k.parse::<usize>().ok()?;
        let found = Household::ALL
            .into_iter()
            .find(|h| frame::household_id(*h) == format!("household:{group}"))?;
        return Some((found, Some(k)));
    }
    Household::ALL
        .into_iter()
        .find(|h| frame::household_id(*h) == id)
        .map(|h| (h, None))
}

fn workplace_of(id: &str) -> Option<Workplace> {
    Workplace::ALL
        .into_iter()
        .find(|w| frame::workplace_id(*w) == id)
}

/// A member of a set, or a pick's own name, in words.
#[must_use]
pub fn label_of(id: &str) -> String {
    if let Some((household, person)) = household_of(id) {
        return match person {
            Some(_) => format!("one person of {}", household.label()),
            None => household.label(),
        };
    }
    workplace_of(id).map_or_else(|| id.to_owned(), Workplace::label)
}

/// The title of the inspector for a pick.
#[must_use]
pub fn pick_label(pick: &Pick) -> String {
    match pick {
        Pick::Body(party) => party.label(),
        Pick::Particle(id) => label_of(id),
        Pick::Set(id) => set_label(id),
    }
}

fn set_label(id: &str) -> String {
    if id == frame::FUND_EDGE {
        return "The fund's set".to_owned();
    }
    Workplace::ALL
        .into_iter()
        .find(|w| frame::workforce_edge(*w) == id)
        .map(|w| format!("The workforce of {}", w.label()))
        .or_else(|| {
            Place::ALL
                .into_iter()
                .find(|p| frame::owner_edge(*p) == id)
                .map(|p| format!("The owners of {}", p.label()))
        })
        .unwrap_or_else(|| id.to_owned())
}

fn money_sum(
    picture: &Picture,
    party: Party,
    kind: PaymentKind,
    incoming: bool,
) -> Result<i128, FrameError> {
    picture
        .reading
        .payments
        .iter()
        .filter(|p| p.kind == kind && (if incoming { p.payee } else { p.payer }) == party)
        .try_fold(0_i128, |sum, p| sum.checked_add(p.amount))
        .ok_or(FrameError::Arithmetic)
}

fn money_rows(picture: &Picture, party: Party, rows: &mut Rows) -> Result<(), FrameError> {
    for (word, incoming) in [("Money in", true), ("Money out", false)] {
        for kind in PaymentKind::ALL {
            let sum = money_sum(picture, party, kind, incoming)?;
            if sum != 0 {
                rows.push((
                    format!("{word} · {}", kind.label()),
                    human_numbers::currency(sum),
                ));
            }
        }
    }
    Ok(())
}

fn cash_row(result: &PeriodResult, party: Party, rows: &mut Rows) -> Result<(), FrameError> {
    let account = account_of(party);
    let cash = result
        .closing
        .cash
        .iter()
        .find(|(held, _)| *held == account)
        .map(|(_, amount)| amount.micro_units())
        .ok_or_else(|| missing(&format!("no cash for {}", party.label())))?;
    rows.push(row("Cash at the close", human_numbers::currency(cash)));
    Ok(())
}

fn hours_of_workplace(picture: &Picture, w: Workplace) -> Result<(u64, u64), FrameError> {
    let mut given = 0_u64;
    let mut idle = 0_u64;
    for flow in picture.reading.work.iter().filter(|f| f.workplace == w) {
        given = given
            .checked_add(flow.given)
            .ok_or(FrameError::Arithmetic)?;
        idle = idle.checked_add(flow.idle).ok_or(FrameError::Arithmetic)?;
    }
    Ok((given, idle))
}

fn workplace_rows(
    picture: &Picture,
    result: &PeriodResult,
    w: Workplace,
) -> Result<Rows, FrameError> {
    let (given, idle) = hours_of_workplace(picture, w)?;
    let at = w.index();
    let mut rows = vec![
        row("Hours given", hours_text(given)),
        row("Paid, not used", hours_text(idle)),
        row("Workers employed", hours_text(result.closing.employed[at])),
        row("Workers in reserve", hours_text(result.closing.reserve[at])),
        row("Made", hours_text(result.summary.made[at])),
    ];
    money_rows(picture, Party::Workplace(w), &mut rows)?;
    cash_row(result, Party::Workplace(w), &mut rows)?;
    for (site, good, price) in &result.summary.prices {
        if *site == w.site_id() {
            if let Some(good) = Good::from_good(*good) {
                rows.push((
                    format!("Posted price · {}", good_name(good)),
                    human_numbers::currency(*price),
                ));
            }
        }
    }
    Ok(rows)
}

fn shared_rows(picture: &Picture, result: &PeriodResult, party: Party) -> Result<Rows, FrameError> {
    let mut rows = Vec::new();
    money_rows(picture, party, &mut rows)?;
    cash_row(result, party, &mut rows)?;
    Ok(rows)
}

fn household_rows(
    picture: &Picture,
    result: &PeriodResult,
    h: Household,
) -> Result<Rows, FrameError> {
    let persons = result
        .closing
        .households
        .iter()
        .find(|c| c.principal_id == h.principal())
        .map(|c| u128::from(c.persons))
        .ok_or_else(|| missing(&format!("no cohort for {}", h.label())))?;
    let at_work = match h {
        Household::Workers(w) => result
            .members
            .iter()
            .find(|m| Workplace::from_site(m.site_id) == Some(w))
            .map_or(0, |m| u128::from(m.opening_employed).min(persons)),
        Household::Owner(_) | Household::Supported(_) => 0,
    };
    let given = picture
        .reading
        .work
        .iter()
        .filter(|f| f.household == h)
        .try_fold(0_u64, |sum, f| sum.checked_add(f.given))
        .ok_or(FrameError::Arithmetic)?;
    let mut rows = vec![
        row("Persons", human_numbers::grouped(persons)),
        row("At work", human_numbers::grouped(at_work)),
        row("Hours given", hours_text(given)),
    ];
    money_rows(picture, Party::Household(h), &mut rows)?;
    cash_row(result, Party::Household(h), &mut rows)?;
    Ok(rows)
}

fn member_value_rows(members: Option<Vec<(String, String)>>, id: &str) -> Result<Rows, FrameError> {
    let mut members = members.ok_or_else(|| missing(&format!("no set {id}")))?;
    members.sort();
    Ok(members
        .into_iter()
        .map(|(member, value)| (label_of(&member), value))
        .collect())
}

/// Each member of the set above zero with its own number, in the set's own unit.
fn set_members(picture: &Picture, id: &str) -> Option<Vec<(String, String)>> {
    if id.starts_with("workforce:") {
        let members = picture.sets.workforces.members_with_data(id)?;
        Some(
            members
                .into_iter()
                .filter(|(_, v)| **v > 0)
                .map(|(m, v)| {
                    (
                        m,
                        format!("{} hours", human_numbers::grouped(u128::from(*v))),
                    )
                })
                .collect(),
        )
    } else {
        let graph = if id == frame::FUND_EDGE {
            &picture.sets.fund
        } else {
            &picture.sets.owners
        };
        let members = graph.members_with_data(id)?;
        Some(
            members
                .into_iter()
                .filter(|(_, v)| **v > 0)
                .map(|(m, v)| (m, human_numbers::currency(*v)))
                .collect(),
        )
    }
}

fn set_rows(picture: &Picture, id: &str) -> Result<Rows, FrameError> {
    let frame_set = picture
        .frame
        .sets
        .iter()
        .find(|s| s.id == id)
        .ok_or_else(|| missing(&format!("no set {id}")))?;
    let kind = if id.starts_with("workforce:") {
        "Workforce: hours given"
    } else if id == frame::FUND_EDGE {
        "Fund: benefits paid"
    } else {
        "Owners: book capital"
    };
    let mut rows = vec![row("Kind", kind)];
    rows.extend(member_value_rows(set_members(picture, id), id)?);
    let held = frame_set.held_share.map_or_else(
        || "nothing to hold".to_owned(),
        |s| format!("{:.0} %", s * 100.0),
    );
    rows.push(row("Outline holds", held));
    Ok(rows)
}

/// The rows of the inspector for one pick, for the period `picture` and `result` are of.
///
/// # Errors
/// `FrameError::Edge` when the pick names a body, household or set the period does not hold,
/// `FrameError::Arithmetic` when a sum overflows.
pub fn inspect(
    picture: &Picture,
    result: &PeriodResult,
    pick: &Pick,
) -> Result<Vec<(String, String)>, FrameError> {
    match pick {
        Pick::Body(Party::Workplace(w)) => workplace_rows(picture, result, *w),
        Pick::Body(party @ (Party::Treasury | Party::Fund)) => shared_rows(picture, result, *party),
        Pick::Body(Party::Household(h)) => household_rows(picture, result, *h),
        Pick::Particle(id) => {
            let (household, person) =
                household_of(id).ok_or_else(|| missing(&format!("no household {id}")))?;
            let mut rows = Vec::new();
            if person.is_some() {
                rows.push(row("Who", format!("one person of {}", household.label())));
            }
            rows.extend(household_rows(picture, result, household)?);
            Ok(rows)
        }
        Pick::Set(id) => set_rows(picture, id),
    }
}

/// A click sets the pick from the entity it hit or its nearest ancestor that is a body, a
/// particle or a set; a click on empty space clears it, and a click on the scene's own buttons
/// leaves it as it is.
pub fn picked(
    event: On<PointerClick>,
    parents: Query<&ChildOf>,
    bodies: Query<&SceneBody>,
    particles: Query<&ParticleId>,
    sets: Query<&SetId>,
    interface: Query<(), With<Node>>,
    mut pick: ResMut<ScenePick>,
) {
    // A click bubbles up its parents: only its first visit decides.
    if event.button != PointerButton::Primary || event.entity != event.original_event_target() {
        return;
    }
    let mut at = Some(event.entity);
    while let Some(entity) = at {
        let found = if let Ok(body) = bodies.get(entity) {
            Some(Pick::Body(body.0))
        } else if let Ok(id) = particles.get(entity) {
            Some(Pick::Particle(id.0.clone()))
        } else if let Ok(id) = sets.get(entity) {
            Some(Pick::Set(id.0.clone()))
        } else {
            None
        };
        if let Some(found) = found {
            pick.set_if_neq(ScenePick(Some(found)));
            return;
        }
        if interface.contains(entity) {
            return;
        }
        at = parents.get(entity).ok().map(ChildOf::parent);
    }
    pick.set_if_neq(ScenePick(None));
}
