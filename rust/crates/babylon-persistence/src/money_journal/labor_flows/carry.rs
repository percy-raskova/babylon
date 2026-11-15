//! Period-bound county carry from actual located positions, regardless of movement on this page.
use super::model::{CountyLaborCarry, LaborCarryAmount};
use crate::identity::CampaignId;
use crate::money_journal::{FlowGroup, FlowQuery, JournalError, LaborFacts};
use babylon_kernel::geography::CountyGeoid;
use postgres::Transaction;

pub(super) fn county_focus(request: &FlowQuery) -> Option<&str> {
    if request.window.first != request.window.last
        || request.peer.is_some()
        || request.viewport_4269.is_some()
        || request.focus_group.unwrap_or(request.group) != FlowGroup::Location
    {
        return None;
    }
    let location = request.focus.as_deref()?;
    CountyGeoid::try_from(location.strip_prefix("county:")?).ok()?;
    Some(location)
}

fn side<'a>(
    carry: &'a mut CountyLaborCarry,
    key: &str,
) -> Result<&'a mut LaborCarryAmount, JournalError> {
    match key {
        "opening" => Ok(&mut carry.opening),
        "closing" => Ok(&mut carry.closing),
        _ => Err(JournalError::Projection),
    }
}

pub(super) fn retained(
    tx: &mut Transaction<'_>,
    campaign: CampaignId,
    tick: i64,
    location: &str,
) -> Result<CountyLaborCarry, JournalError> {
    let rows = tx
        .query(
            include_str!("carry.sql"),
            &[campaign.as_uuid(), &tick, &location],
        )
        .map_err(|_| JournalError::Database)?;
    if rows.is_empty() {
        return Err(JournalError::CoverageAbsent);
    }
    let mut carry = CountyLaborCarry::default();
    for row in rows {
        let get = |_| JournalError::Projection;
        if !row.try_get::<_, bool>("complete").map_err(get)? {
            return Err(JournalError::Projection);
        }
        let Some(key) = row.try_get::<_, Option<&str>>("side").map_err(get)? else {
            continue;
        };
        *side(&mut carry, key)? = LaborCarryAmount {
            recorded_micro_hours: row
                .try_get::<_, &str>("hours")
                .map_err(get)?
                .parse()
                .map_err(|_| JournalError::Range)?,
            positions: u64::try_from(row.try_get::<_, i64>("positions").map_err(get)?)
                .map_err(|_| JournalError::Range)?,
            unknown_positions: u64::try_from(
                row.try_get::<_, i64>("unknown_positions").map_err(get)?,
            )
            .map_err(|_| JournalError::Range)?,
        };
    }
    Ok(carry)
}

pub(super) fn reconstructed(
    facts: &LaborFacts,
    location: &str,
) -> Result<CountyLaborCarry, JournalError> {
    let mut carry = CountyLaborCarry::default();
    for p in &facts.positions {
        let index = usize::try_from(p.node_ordinal).map_err(|_| JournalError::Projection)?;
        let node = facts
            .nodes
            .get(index)
            .filter(|n| n.node_ordinal == p.node_ordinal)
            .ok_or(JournalError::Projection)?;
        if node.location_key.as_deref() != Some(location) {
            continue;
        }
        let amount = side(&mut carry, p.side)?;
        amount.recorded_micro_hours = amount
            .recorded_micro_hours
            .checked_add(p.recorded_micro_hours)
            .ok_or(JournalError::Range)?;
        amount.positions = amount.positions.checked_add(1).ok_or(JournalError::Range)?;
        amount.unknown_positions = amount
            .unknown_positions
            .checked_add(u64::from(p.unknown_opening))
            .ok_or(JournalError::Range)?;
    }
    Ok(carry)
}
