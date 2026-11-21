//! One named hearing appointment; each group controls its own delegation.
use super::{
    OrganizerChoice, OrganizerCommitment, OrganizerConfig, OrganizerError, OrganizerOutcome,
    OrganizerPartner, OrganizerPeriodJournalEntries, OrganizerPeriodTimeResources,
    OrganizerReceipt, OrganizerState, OrganizerTimeUse,
};
use crate::{
    ActorOrganizationId, InputAuthorityId, PracticeId, PracticeIntent, PracticeTargetIdentity,
    PracticeTargetTag, ProposalNonce,
};
use babylon_kernel::geography::CountyGeoid;
use serde::{Deserialize, Serialize};
use std::collections::BTreeSet;

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum OrganizerHearingOffer {
    ClaimantOnly,
    JointMinutes,
}

/// The members' authorization for this appointment, limited to one exact offer.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum OrganizerHearingMandate {
    Withhold,
    SpeakOnly,
    Settle(OrganizerHearingOffer),
    EitherProceduralOffer,
}

/// A named office authorized by a counted body for this hearing only.
#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerHearingDelegation {
    pub delegate_label: String,
    pub authorizing_households: u64,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerHearingConfig {
    pub county_geoid: String,
    pub period: u64,
    pub review_period: u64,
    pub claimant_actor_id: u64,
    pub claimant_authority_id: [u8; 16],
    pub claimant_label: String,
    pub claimant_claim: String,
    pub partner_claim: String,
    pub claimant_delegation: OrganizerHearingDelegation,
    pub partner_delegation: OrganizerHearingDelegation,
    pub attendance_hours: u64,
    pub claimant_mandate: OrganizerHearingMandate,
    pub partner_mandate: OrganizerHearingMandate,
}

/// Published appointment and proposed terms. Member deliberation stays private.
#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerHearingNotice {
    pub county_geoid: String,
    pub period: u64,
    pub review_period: u64,
    pub claimant_actor_id: u64,
    pub claimant_label: String,
    pub claimant_claim: String,
    pub partner_claim: String,
    pub claimant_delegation: OrganizerHearingDelegation,
    pub partner_delegation: OrganizerHearingDelegation,
    pub attendance_hours: u64,
}

impl From<&OrganizerHearingConfig> for OrganizerHearingNotice {
    fn from(hearing: &OrganizerHearingConfig) -> Self {
        Self {
            county_geoid: hearing.county_geoid.clone(),
            period: hearing.period,
            review_period: hearing.review_period,
            claimant_actor_id: hearing.claimant_actor_id,
            claimant_label: hearing.claimant_label.clone(),
            claimant_claim: hearing.claimant_claim.clone(),
            partner_claim: hearing.partner_claim.clone(),
            claimant_delegation: hearing.claimant_delegation.clone(),
            partner_delegation: hearing.partner_delegation.clone(),
            attendance_hours: hearing.attendance_hours,
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum OrganizerHearingResponse {
    NotInvited,
    Withheld,
    NoTime,
    Attended,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerHearingSeat {
    pub actor_id: u64,
    pub authority_id: [u8; 16],
    pub label: String,
    pub claim: String,
    pub delegation: OrganizerHearingDelegation,
    pub response: OrganizerHearingResponse,
    pub mandate: Option<OrganizerHearingMandate>,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum OrganizerHearingOutcome {
    NoOffer,
    NoQuorum,
    ReferredToMembers,
    Settled,
}

/// A demand actually entered at the hearing by a paid, authorized delegate.
#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerHearingTestimony {
    pub actor_id: u64,
    pub period: u64,
    pub delegate_label: String,
    pub claim: String,
}

/// Exact hearing evidence, including the actors who gained access at review.
#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerHearingReceipt {
    pub county_geoid: String,
    pub receipt_id: [u8; 32],
    pub period: u64,
    pub review_period: u64,
    pub invitation_commitment_id: Option<[u8; 32]>,
    pub offer: Option<OrganizerHearingOffer>,
    pub claimant: OrganizerHearingSeat,
    pub partner: OrganizerHearingSeat,
    pub outcome: OrganizerHearingOutcome,
    pub testimony: Vec<OrganizerHearingTestimony>,
    /// Opening and reply speaking turns in this order. Empty if no settlement.
    pub review_access_actor_ids: Vec<u64>,
    pub time_use: Vec<OrganizerTimeUse>,
}

/// Authorized opening and reply turns at the dated county review.
#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerHearingReview {
    pub county_geoid: String,
    pub period: u64,
    pub hearing_receipt_id: [u8; 32],
    /// In order of opening and reply. Empty when there was no settlement.
    pub speaker_actor_ids: Vec<u64>,
}

impl From<&OrganizerHearingReceipt> for OrganizerHearingReview {
    fn from(receipt: &OrganizerHearingReceipt) -> Self {
        Self {
            county_geoid: receipt.county_geoid.clone(),
            period: receipt.review_period,
            hearing_receipt_id: receipt.receipt_id,
            speaker_actor_ids: receipt.review_access_actor_ids.clone(),
        }
    }
}

pub(super) fn advance_review(
    config: &OrganizerConfig,
    opening: &OrganizerState,
    next: &mut OrganizerState,
    entries: &mut OrganizerPeriodJournalEntries,
) -> Result<(), OrganizerError> {
    if opening.period.checked_add(1) != Some(entries.period) {
        return Err(OrganizerError::PeriodMismatch);
    }
    if config
        .hearing
        .as_ref()
        .is_some_and(|hearing| hearing.review_period == entries.period)
    {
        let review = next
            .pending_hearing_review
            .take()
            .ok_or(OrganizerError::InvalidState)?;
        if review.period != entries.period
            || Some(&review) != opening.pending_hearing_review.as_ref()
        {
            return Err(OrganizerError::InvalidState);
        }
        entries.hearing_review = Some(review);
    } else if let Some(receipt) = &entries.hearing {
        next.pending_hearing_review = Some(OrganizerHearingReview::from(receipt));
    }
    Ok(())
}

pub(super) fn validate_review_shape(
    config: &OrganizerConfig,
    review: &OrganizerHearingReview,
) -> Result<(), OrganizerError> {
    let hearing = config
        .hearing
        .as_ref()
        .ok_or(OrganizerError::InvalidState)?;
    let partner_id = partner(config)?.actor_id;
    let speakers_valid = match review.speaker_actor_ids.as_slice() {
        [] => true,
        [opening, reply] => {
            *opening == hearing.claimant_actor_id
                && [hearing.claimant_actor_id, partner_id].contains(reply)
        }
        _ => false,
    };
    if review.period != hearing.review_period
        || review.county_geoid != hearing.county_geoid
        || review.hearing_receipt_id == [0; 32]
        || !speakers_valid
    {
        return Err(OrganizerError::InvalidState);
    }
    Ok(())
}

pub(super) fn validate_review_history(
    periods: &[OrganizerPeriodJournalEntries],
) -> Result<(), OrganizerError> {
    let mut scheduled_review = None;
    for entries in periods {
        if let Some(hearing) = &entries.hearing {
            scheduled_review = Some(OrganizerHearingReview::from(hearing));
        }
        if let Some(review) = &entries.hearing_review {
            if Some(review) != scheduled_review.as_ref() {
                return Err(OrganizerError::InvalidState);
            }
        }
    }
    Ok(())
}

pub(super) fn validate_review_cursor(
    config: &OrganizerConfig,
    state: &OrganizerState,
    periods: &[OrganizerPeriodJournalEntries],
) -> Result<(), OrganizerError> {
    let mut pending = None;
    if let Some(hearing) = &config.hearing {
        if (hearing.period..hearing.review_period).contains(&state.period) {
            let receipt = periods
                .iter()
                .find_map(|entries| entries.hearing.as_ref())
                .ok_or(OrganizerError::InvalidState)?;
            pending = Some(OrganizerHearingReview::from(receipt));
        }
        if state.period >= hearing.review_period
            && !periods
                .iter()
                .any(|entries| entries.hearing_review.is_some())
        {
            return Err(OrganizerError::InvalidState);
        }
    }
    if state.pending_hearing_review != pending {
        return Err(OrganizerError::InvalidState);
    }
    Ok(())
}

fn testimony(period: u64, seats: [&OrganizerHearingSeat; 2]) -> Vec<OrganizerHearingTestimony> {
    seats
        .into_iter()
        .filter(|seat| seat.response == OrganizerHearingResponse::Attended)
        .map(|seat| OrganizerHearingTestimony {
            actor_id: seat.actor_id,
            period,
            delegate_label: seat.delegation.delegate_label.clone(),
            claim: seat.claim.clone(),
        })
        .collect()
}

impl OrganizerHearingOffer {
    pub(super) fn parameter(self) -> u8 {
        match self {
            Self::ClaimantOnly => 6,
            Self::JointMinutes => 7,
        }
    }
}

pub(super) fn partner(config: &OrganizerConfig) -> Result<&OrganizerPartner, OrganizerError> {
    super::aid::aid_binding(config, OrganizerChoice::LocalAid)
        .map(|row| &row.partner)
        .ok_or(OrganizerError::InvalidConfig)
}

fn seats(
    config: &OrganizerConfig,
    hearing: &OrganizerHearingConfig,
) -> Result<[OrganizerHearingSeat; 2], OrganizerError> {
    use OrganizerHearingResponse::{NotInvited, Withheld};
    let partner = partner(config)?;
    Ok([
        OrganizerHearingSeat {
            actor_id: hearing.claimant_actor_id,
            authority_id: hearing.claimant_authority_id,
            label: hearing.claimant_label.clone(),
            claim: hearing.claimant_claim.clone(),
            delegation: hearing.claimant_delegation.clone(),
            response: Withheld,
            mandate: Some(hearing.claimant_mandate),
        },
        OrganizerHearingSeat {
            actor_id: partner.actor_id,
            authority_id: partner.authority_id,
            label: partner.label.clone(),
            claim: hearing.partner_claim.clone(),
            delegation: hearing.partner_delegation.clone(),
            response: NotInvited,
            mandate: Some(hearing.partner_mandate),
        },
    ])
}

/// Proposals originate with the members of each group, even on a player Hold.
pub(super) fn attendance_intents(
    config: &OrganizerConfig,
    opening_period: u64,
    invitation: &OrganizerCommitment,
    base: &PracticeIntent,
    invitation_reaches_partner: bool,
) -> Result<Vec<PracticeIntent>, OrganizerError> {
    let Some(hearing) = config
        .hearing
        .as_ref()
        .filter(|hearing| opening_period.checked_add(1) == Some(hearing.period))
    else {
        return Ok(vec![]);
    };
    let invited = invitation_reaches_partner
        && matches!(
            invitation.command.choice,
            OrganizerChoice::InviteToHearing(_)
        );
    seats(config, hearing)?
        .into_iter()
        .take(if invited { 2 } else { 1 })
        .filter(|seat| seat.mandate != Some(OrganizerHearingMandate::Withhold))
        .map(|seat| {
            let digest = super::contract::identity(
                b"babylon.organizer-hearing-attendance.v1",
                &(
                    config.campaign_id,
                    hearing.period,
                    seat.actor_id,
                    seat.authority_id,
                ),
            )?;
            let mut nonce = [0; 16];
            nonce.copy_from_slice(&digest[..16]);
            let mut intent = base.clone();
            intent.actor_org_id = ActorOrganizationId::from_bytes(seat.actor_id.to_be_bytes());
            intent.input_authority_id = InputAuthorityId::from_bytes(seat.authority_id);
            intent.practice_id = PracticeId::Organize;
            intent.target.tag = PracticeTargetTag::Organization;
            intent.target.identity =
                PracticeTargetIdentity::from_bytes(super::transition::target_identity(
                    b"babylon.organizer-hearing-venue.v1",
                    hearing.claimant_actor_id,
                ));
            intent.proposal_nonce = ProposalNonce::from_bytes(nonce);
            intent.parameters = super::transition::control_parameter(8);
            intent.evidence_digests.clear();
            crate::validate_practice_intent(&intent)
                .map_err(|_| OrganizerError::InvalidCommitment)?;
            Ok(intent)
        })
        .collect()
}

fn decision(
    offer: Option<OrganizerHearingOffer>,
    claimant: &OrganizerHearingSeat,
    partner: &OrganizerHearingSeat,
) -> (OrganizerHearingOutcome, Vec<u64>) {
    use OrganizerHearingOutcome::{NoOffer, NoQuorum, ReferredToMembers, Settled};
    let Some(offer) = offer else {
        return (NoOffer, vec![]);
    };
    let parties = [claimant, partner];
    let parties = &parties[..if offer == OrganizerHearingOffer::JointMinutes {
        2
    } else {
        1
    }];
    if parties
        .iter()
        .any(|seat| seat.response != OrganizerHearingResponse::Attended)
    {
        return (NoQuorum, vec![]);
    }
    if parties.iter().any(|seat| {
        !matches!(
            seat.mandate,
            Some(OrganizerHearingMandate::EitherProceduralOffer)
        ) && seat.mandate != Some(OrganizerHearingMandate::Settle(offer))
    }) {
        return (ReferredToMembers, vec![]);
    }
    let reply_actor = match offer {
        OrganizerHearingOffer::ClaimantOnly => claimant.actor_id,
        OrganizerHearingOffer::JointMinutes => partner.actor_id,
    };
    (Settled, vec![claimant.actor_id, reply_actor])
}

fn receipt_id(
    config: &OrganizerConfig,
    period: u64,
    commitment_id: Option<[u8; 32]>,
) -> Result<[u8; 32], OrganizerError> {
    super::contract::identity(
        b"babylon.organizer-hearing-receipt.v1",
        &(
            config.campaign_id,
            config.content_digest,
            period,
            commitment_id,
        ),
    )
}

pub(super) fn resolve(
    config: &OrganizerConfig,
    commitment: &OrganizerCommitment,
    base: &PracticeIntent,
    resources: &OrganizerPeriodTimeResources,
    entries: &mut OrganizerPeriodJournalEntries,
) -> Result<(), OrganizerError> {
    use OrganizerHearingResponse::{Attended, NoTime, Withheld};
    let Some(hearing) = config
        .hearing
        .as_ref()
        .filter(|h| h.period == entries.period)
    else {
        return Ok(());
    };
    let invitation = entries.receipts.iter().find(|row| {
        row.commitment_id == Some(commitment.commitment_id)
            && matches!(row.choice, OrganizerChoice::InviteToHearing(_))
    });
    let invitation_commitment_id = invitation.and_then(|row| row.commitment_id);
    let offer = invitation.and_then(issued_offer);
    let [mut claimant, mut partner] = seats(config, hearing)?;
    let intents = attendance_intents(
        config,
        commitment.command.expected_period,
        commitment,
        base,
        offer.is_some(),
    )?;
    let mut used = entries
        .receipts()
        .filter(|receipt| receipt.choice != OrganizerChoice::Collect)
        .flat_map(|receipt| &receipt.time_use)
        .cloned()
        .collect::<Vec<_>>();
    let mut time_use = vec![];
    if offer.is_some() {
        partner.response = Withheld;
    }
    for seat in [&mut claimant, &mut partner] {
        let Some(intent) = intents
            .iter()
            .find(|intent| intent.actor_org_id.to_bytes() == seat.actor_id.to_be_bytes())
        else {
            continue;
        };
        let (remaining, supply) =
            super::time_resources::remaining_after_uses(config, resources, &used)?;
        let Some(debits) = super::time_resources::allocate_single_actor_hours(
            &remaining,
            intent,
            hearing.attendance_hours,
            &supply,
        )?
        else {
            seat.response = NoTime;
            continue;
        };
        seat.response = Attended;
        used.extend(debits.iter().cloned());
        time_use.extend(debits);
    }
    let (outcome, review_access_actor_ids) = decision(offer, &claimant, &partner);
    entries.hearing = Some(OrganizerHearingReceipt {
        county_geoid: hearing.county_geoid.clone(),
        receipt_id: receipt_id(config, hearing.period, invitation_commitment_id)?,
        period: hearing.period,
        review_period: hearing.review_period,
        invitation_commitment_id,
        offer,
        testimony: testimony(hearing.period, [&claimant, &partner]),
        claimant,
        partner,
        outcome,
        review_access_actor_ids,
        time_use,
    });
    Ok(())
}

pub(super) fn validate_config(
    config: &OrganizerConfig,
    hearing: &OrganizerHearingConfig,
) -> Result<(), OrganizerError> {
    if CountyGeoid::try_from(hearing.county_geoid.as_str()).is_err()
        || hearing.period == 0
        || hearing.period.checked_add(1) != Some(hearing.review_period)
        || hearing.attendance_hours == 0
        || !super::contract::label_valid(&hearing.claimant_label)
        || !super::contract::label_valid(&hearing.claimant_claim)
        || !super::contract::label_valid(&hearing.partner_claim)
        || [&hearing.claimant_delegation, &hearing.partner_delegation]
            .iter()
            .any(|group| {
                group.authorizing_households == 0
                    || !super::contract::label_valid(&group.delegate_label)
            })
        || matches!(
            hearing.partner_mandate,
            OrganizerHearingMandate::EitherProceduralOffer
                | OrganizerHearingMandate::Settle(OrganizerHearingOffer::ClaimantOnly)
        )
    {
        return Err(OrganizerError::InvalidConfig);
    }
    partner(config)?;
    Ok(())
}

fn issued_offer(row: &OrganizerReceipt) -> Option<OrganizerHearingOffer> {
    match (row.choice, row.outcome) {
        (OrganizerChoice::InviteToHearing(offer), OrganizerOutcome::HearingInvitationIssued) => {
            Some(offer)
        }
        _ => None,
    }
}

pub(super) fn validate_entries(
    config: &OrganizerConfig,
    entries: &OrganizerPeriodJournalEntries,
) -> Result<(), OrganizerError> {
    use OrganizerHearingResponse::{Attended, NoTime, NotInvited, Withheld};
    let review_due = config
        .hearing
        .as_ref()
        .is_some_and(|hearing| hearing.review_period == entries.period);
    if review_due != entries.hearing_review.is_some() {
        return Err(OrganizerError::InvalidState);
    }
    if let Some(review) = &entries.hearing_review {
        validate_review_shape(config, review)?;
    }
    let scheduled = config
        .hearing
        .as_ref()
        .filter(|h| h.period == entries.period);
    let mut invitations = entries
        .receipts
        .iter()
        .filter(|row| matches!(row.choice, OrganizerChoice::InviteToHearing(_)));
    let invitation = invitations.next();
    let (hearing, receipt) = match (scheduled, &entries.hearing) {
        (None, None) if invitation.is_none() => return Ok(()),
        (Some(hearing), Some(receipt)) => (hearing, receipt),
        _ => return Err(OrganizerError::InvalidState),
    };
    let expected_invitation = invitation.and_then(|row| row.commitment_id);
    if invitations.next().is_some()
        || invitation.is_some_and(|row| {
            row.actor_id != config.controlled_actor_id
                || row.standing_work
                || row.commitment_id.is_none()
                || match row.outcome {
                    OrganizerOutcome::HearingInvitationIssued => {
                        row.hours_spent != hearing.attendance_hours
                    }
                    OrganizerOutcome::InsufficientTime => !row.time_use.is_empty(),
                    _ => true,
                }
                || row
                    .time_use
                    .iter()
                    .any(|usage| usage.actor_id != row.actor_id)
        })
        || receipt.offer != invitation.and_then(issued_offer)
        || receipt.county_geoid != hearing.county_geoid
        || receipt.invitation_commitment_id != expected_invitation
        || receipt.receipt_id != receipt_id(config, hearing.period, expected_invitation)?
        || receipt.period != hearing.period
        || receipt.review_period != hearing.review_period
        || receipt.testimony != testimony(entries.period, [&receipt.claimant, &receipt.partner])
        || decision(receipt.offer, &receipt.claimant, &receipt.partner)
            != (receipt.outcome, receipt.review_access_actor_ids.clone())
    {
        return Err(OrganizerError::InvalidState);
    }
    let [expected_claimant, expected_partner] = seats(config, hearing)?;
    let mut seen = BTreeSet::new();
    if receipt.time_use.iter().any(|row| {
        row.hours == 0
            || ![expected_claimant.actor_id, expected_partner.actor_id].contains(&row.actor_id)
            || !seen.insert((row.contributor_id, row.actor_id))
    }) {
        return Err(OrganizerError::InvalidState);
    }
    for (invited, actual, mut expected) in [
        (true, &receipt.claimant, expected_claimant),
        (receipt.offer.is_some(), &receipt.partner, expected_partner),
    ] {
        let lawful_response = if !invited {
            actual.response == NotInvited
        } else if expected.mandate == Some(OrganizerHearingMandate::Withhold) {
            actual.response == Withheld
        } else {
            matches!(actual.response, Attended | NoTime)
        };
        expected.response = actual.response;
        let hours = receipt
            .time_use
            .iter()
            .filter(|row| row.actor_id == actual.actor_id)
            .try_fold(0_u64, |sum, row| {
                sum.checked_add(row.hours).ok_or(OrganizerError::Arithmetic)
            })?;
        if !lawful_response
            || *actual != expected
            || hours
                != if actual.response == Attended {
                    hearing.attendance_hours
                } else {
                    0
                }
        {
            return Err(OrganizerError::InvalidState);
        }
    }
    Ok(())
}
