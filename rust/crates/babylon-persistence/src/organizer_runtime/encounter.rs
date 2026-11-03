//! Actor-safe projection of admitted, published City PD visits.

use babylon_practice_contract::{CityPdDecision, CityPdOutcome, PublicVenueRecordKind};
use babylon_tick::material_world::MaterialWorldRegister;
use serde::{Deserialize, Serialize};
use std::collections::BTreeSet;

use crate::material_runtime::MaterialRuntimeError;

const DOMAIN: &[u8] = b"babylon.city-pd-encounter.v1\0";
// JSON object keys and punctuation plus the maximum decimal widths of every
// fixed-size byte array and integer, including the versioned domain prefix.
const FRAME: &[u8] = b"{\"schema_version\":,\"campaign_id\":,\"controlled_actor_id\":,\"authority_id\":,\"content_digest\":,\"resource_digest\":,\"subject_id\":,\"resolve_period\":,\"visitor_actor_id\":,\"receipt_id\":,\"venue_source_id\":,\"visit_core_id\":,\"access_evidence_id\":}";
pub(crate) const MAX_ENCOUNTER_BYTES: usize =
    DOMAIN.len() + FRAME.len() + 2 * (16 * 4 + 1) + 6 * (32 * 4 + 1) + 4 * 20 + 10;
/// Current strict actor-visible encounter schema.
pub const CITY_PD_ENCOUNTER_SCHEMA_VERSION: u32 = 1;

/// A published paid-visit check-in available to the controlled organizer.
/// This is a venue log, not evidence that the player attended the visit.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CityPdEncounter {
    pub schema_version: u32,
    pub campaign_id: [u8; 16],
    pub controlled_actor_id: u64,
    pub authority_id: [u8; 16],
    pub content_digest: [u8; 32],
    pub resource_digest: [u8; 32],
    /// Disclosed workplace identity and existing Archive page target.
    pub subject_id: u64,
    pub resolve_period: u64,
    pub visitor_actor_id: u64,
    pub receipt_id: [u8; 32],
    pub venue_source_id: [u8; 32],
    pub visit_core_id: [u8; 32],
    pub access_evidence_id: [u8; 32],
}

pub(crate) fn canonical_bytes(value: &CityPdEncounter) -> Result<Vec<u8>, MaterialRuntimeError> {
    if value.schema_version != CITY_PD_ENCOUNTER_SCHEMA_VERSION
        || value.campaign_id == [0; 16]
        || value.controlled_actor_id == 0
        || value.authority_id == [0; 16]
        || value.content_digest == [0; 32]
        || value.resource_digest == [0; 32]
        || value.subject_id == 0
        || value.resolve_period == 0
        || value.visitor_actor_id == 0
        || [
            value.receipt_id,
            value.venue_source_id,
            value.visit_core_id,
            value.access_evidence_id,
        ]
        .contains(&[0; 32])
    {
        return Err(MaterialRuntimeError::OrganizerStorage);
    }
    let mut bytes = DOMAIN.to_vec();
    serde_json::to_writer(&mut bytes, value).map_err(|_| MaterialRuntimeError::OrganizerStorage)?;
    if bytes.len() > MAX_ENCOUNTER_BYTES {
        return Err(MaterialRuntimeError::Bounds);
    }
    Ok(bytes)
}

/// Derive only from an already authenticated retained register.
pub(crate) fn projections(
    register: &MaterialWorldRegister,
) -> Result<Vec<CityPdEncounter>, MaterialRuntimeError> {
    let Some(pd) = register.city_pd() else {
        return Ok(Vec::new());
    };
    let config = register
        .organizer_config()
        .ok_or(MaterialRuntimeError::OrganizerStorage)?;
    let history = register
        .public_venue()
        .ok_or(MaterialRuntimeError::OrganizerStorage)?;
    history
        .validate()
        .map_err(|_| MaterialRuntimeError::OrganizerStorage)?;
    if history.policy.campaign_id != config.campaign_id
        || history.policy.workplace_id != config.workplace_id
        || history.policy.controlled_actor_id != config.controlled_actor_id
        || history.policy.organizer_content_digest != config.content_digest
        || pd.config.campaign_id != config.campaign_id
    {
        return Err(MaterialRuntimeError::OrganizerStorage);
    }
    let resource_digest = babylon_practice_contract::organizer_resource_digest()
        .map_err(|_| MaterialRuntimeError::OrganizerStorage)?;
    let mut encounters = Vec::new();
    for attempt in &pd.attempts {
        let Some(access) = attempt.receipt.player_witness_evidence_id else {
            continue;
        };
        let CityPdDecision::Selected(intent) = &attempt.decision.decision else {
            return Err(MaterialRuntimeError::OrganizerStorage);
        };
        if attempt.receipt.outcome != CityPdOutcome::Completed
            || attempt.receipt.resolve_period != intent.resolve_period
            || intent.actor_id != pd.config.actor_id
            || intent.subject_id != config.workplace_id
            || history.policy.player_reader_actor_id != config.controlled_actor_id
        {
            return Err(MaterialRuntimeError::OrganizerStorage);
        }
        let mut matches = history.records.iter().filter_map(|record| {
            let PublicVenueRecordKind::PaidVisit { visit_core_id } = &record.kind else {
                return None;
            };
            (record.period == intent.resolve_period
                && babylon_tick::public_venue::public_visit_access_identity(
                    *visit_core_id,
                    record.source_id,
                    config.controlled_actor_id,
                ) == access)
                .then_some((record, *visit_core_id))
        });
        let (record, visit_core_id) = matches
            .next()
            .ok_or(MaterialRuntimeError::OrganizerStorage)?;
        if matches.next().is_some() {
            return Err(MaterialRuntimeError::OrganizerStorage);
        }
        let encounter = CityPdEncounter {
            schema_version: CITY_PD_ENCOUNTER_SCHEMA_VERSION,
            campaign_id: config.campaign_id,
            controlled_actor_id: config.controlled_actor_id,
            authority_id: config.input_authority_id,
            content_digest: config.content_digest,
            resource_digest,
            subject_id: intent.subject_id,
            resolve_period: intent.resolve_period,
            visitor_actor_id: intent.actor_id,
            receipt_id: attempt.receipt.receipt_id,
            venue_source_id: record.source_id,
            visit_core_id,
            access_evidence_id: access,
        };
        canonical_bytes(&encounter)?;
        encounters.push(encounter);
    }
    encounters.sort_by_key(|row| (row.resolve_period, row.receipt_id));
    let mut receipts = BTreeSet::new();
    if encounters.len() > babylon_practice_contract::CITY_PD_MAX_ROWS
        || encounters.windows(2).any(|pair| {
            (pair[0].resolve_period, pair[0].receipt_id)
                >= (pair[1].resolve_period, pair[1].receipt_id)
        })
        || encounters
            .iter()
            .any(|row| !receipts.insert(row.receipt_id))
    {
        return Err(MaterialRuntimeError::OrganizerStorage);
    }
    Ok(encounters)
}
