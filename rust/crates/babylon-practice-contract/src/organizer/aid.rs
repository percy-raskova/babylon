//! Captured gift receiving consent and later independent mutual-aid practice.
use super::*;
use std::collections::BTreeSet;

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum OrganizerAidKind {
    Local,
    Remote,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum OrganizerGiftConsent {
    Accept,
    Refuse,
}

/// Identities only. Material host owns quantities, stock, money, routes and fulfillment time.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerAidBinding {
    pub kind: OrganizerAidKind,
    pub mandate_id: [u8; 32],
    pub source_hash: [u8; 32],
    pub donor_contributor_id: u64,
    pub recipient_contributor_id: u64,
    pub donor_principal_id: [u8; 32],
    pub recipient_principal_id: [u8; 32],
    pub social_class_target: [u8; 32],
    pub receiving_consent: OrganizerGiftConsent,
    pub partner: OrganizerPartner,
    /// Coordination practice after material close; not quantity fulfillment labor.
    pub coordination_hours: u64,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerAidOption {
    pub kind: OrganizerAidKind,
    pub partner_actor_id: u64,
    pub partner_label: String,
    pub coordination_hours: u64,
    pub receiving_consent: OrganizerGiftConsent,
}

/// Pre-material commitment. Receiving a gift does not authorize later partner practice.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerAidCommitment {
    pub commitment: OrganizerCommitment,
    pub kind: OrganizerAidKind,
    pub mandate_id: [u8; 32],
    pub source_hash: [u8; 32],
    pub donor_actor_id: u64,
    pub recipient_actor_id: u64,
    pub donor_contributor_id: u64,
    pub recipient_contributor_id: u64,
    pub donor_principal_id: [u8; 32],
    pub recipient_principal_id: [u8; 32],
}

pub(super) fn aid_kind(choice: OrganizerChoice) -> Option<OrganizerAidKind> {
    match choice {
        OrganizerChoice::LocalAid => Some(OrganizerAidKind::Local),
        OrganizerChoice::RemoteAid => Some(OrganizerAidKind::Remote),
        _ => None,
    }
}
pub(super) fn aid_binding(
    config: &OrganizerConfig,
    choice: OrganizerChoice,
) -> Option<&OrganizerAidBinding> {
    let kind = aid_kind(choice)?;
    config.aid_bindings.iter().find(|row| row.kind == kind)
}
pub(super) fn validate_aid_bindings(config: &OrganizerConfig) -> Result<(), OrganizerError> {
    if config.aid_bindings.len() > 2 {
        return Err(OrganizerError::InvalidConfig);
    }
    if config.aid_bindings.is_empty() {
        return Ok(());
    }
    let OrganizerTimeBindingMode::Household { bindings } = &config.time_binding else {
        return Err(OrganizerError::TimeBindingMismatch);
    };
    let mut prior = None;
    let mut mandates = BTreeSet::new();
    for row in &config.aid_bindings {
        if prior.is_some_and(|kind| kind >= row.kind)
            || row.mandate_id == [0; 32]
            || row.source_hash == [0; 32]
            || !mandates.insert(row.mandate_id)
            || row.social_class_target == [0; 32]
            || row.coordination_hours == 0
            || row.donor_principal_id == row.recipient_principal_id
            || !bindings.iter().any(|b| {
                b.contributor_id == row.donor_contributor_id
                    && b.principal_id == row.donor_principal_id
            })
            || !bindings.iter().any(|b| {
                b.contributor_id == row.recipient_contributor_id
                    && b.principal_id == row.recipient_principal_id
            })
        {
            return Err(OrganizerError::InvalidConfig);
        }
        prior = Some(row.kind);
    }
    Ok(())
}
fn gift_commitment(
    config: &OrganizerConfig,
    commitment: &OrganizerCommitment,
) -> Result<OrganizerAidCommitment, OrganizerError> {
    let row = aid_binding(config, commitment.command.choice)
        .ok_or(OrganizerError::Refused(OrganizerRefusal::AidUnavailable))?;
    if row.receiving_consent != OrganizerGiftConsent::Accept {
        return Err(OrganizerError::Refused(
            OrganizerRefusal::AidReceivingRefused,
        ));
    }
    Ok(OrganizerAidCommitment {
        commitment: commitment.clone(),
        kind: row.kind,
        mandate_id: row.mandate_id,
        source_hash: row.source_hash,
        donor_actor_id: config.controlled_actor_id,
        recipient_actor_id: row.partner.actor_id,
        donor_contributor_id: row.donor_contributor_id,
        recipient_contributor_id: row.recipient_contributor_id,
        donor_principal_id: row.donor_principal_id,
        recipient_principal_id: row.recipient_principal_id,
    })
}
/// Authenticate an accepted next-period gift before material close. No actual stock,
/// cash or finite-time availability is inferred; those remain host admission.
/// # Errors
/// Refuses wrong/current bindings or captured receiving refusal.
pub fn organizer_aid_commitment(
    config: &OrganizerConfig,
    opening: &OrganizerState,
    accepted: &OrganizerCommitment,
) -> Result<OrganizerAidCommitment, OrganizerError> {
    if admit_organizer(config, opening, &accepted.command)? != *accepted {
        return Err(OrganizerError::InvalidCommitment);
    }
    gift_commitment(config, accepted)
}
/// Validate immutable exact-retry identity after its original period has resolved.
/// # Errors
/// Refuses changed capture, source, actors, identity or receiving consent.
pub fn validate_organizer_aid_commitment(
    config: &OrganizerConfig,
    gift: &OrganizerAidCommitment,
) -> Result<(), OrganizerError> {
    validate_organizer_config(config)?;
    validate_organizer_commitment(&gift.commitment)?;
    let command = &gift.commitment.command;
    if command.campaign_id != config.campaign_id
        || command.actor_id != config.controlled_actor_id
        || command.authority_id != config.input_authority_id
        || command.content_digest != config.content_digest
        || command.resource_digest != organizer_resource_digest()?
        || gift_commitment(config, &gift.commitment)? != *gift
    {
        return Err(OrganizerError::InvalidCommitment);
    }
    Ok(())
}
/// One pending gift admits an exact retry and refuses a conflicting replacement.
/// # Errors
/// Refuses ordinary command errors, malformed pending capture or a conflicting nonce/source.
pub fn admit_organizer_aid_pending(
    config: &OrganizerConfig,
    opening: &OrganizerState,
    command: &OrganizerCommand,
    pending: Option<&OrganizerAidCommitment>,
) -> Result<OrganizerAidCommitment, OrganizerError> {
    let accepted = admit_organizer(config, opening, command)?;
    let gift = organizer_aid_commitment(config, opening, &accepted)?;
    if let Some(pending) = pending {
        validate_organizer_aid_commitment(config, pending)?;
        if pending != &gift {
            return Err(OrganizerError::Refused(
                OrganizerRefusal::PendingAidConflict,
            ));
        }
    }
    Ok(gift)
}

/// Designed gate: delivered support and positive same-period recipient consumption,
/// not proof that donated units caused marginal consumption or additional time.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case", deny_unknown_fields)]
pub enum OrganizerAidSupportStatus {
    /// Some authenticated freight for this original commitment still survives.
    AwaitingDelivery,
    /// No grant and no surviving freight; includes unshipped or total loss.
    TerminalFailure,
    Granted {
        granted_quantity: u64,
        consumed_quantity: u64,
    },
}

/// Exact per-period movements selected from the admitted command's material close.
/// Cash belongs to the captured payer; fulfillment time belongs to the donor household.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerAidMaterialPostings {
    /// Actual food and donor household time in this support period, not the mandate maximum.
    pub dispatched_quantity: u64,
    pub fulfillment_hours: u64,
    /// Exact payer movements, separately from household time and later coordination.
    #[serde(with = "nonnegative_decimal_i128")]
    pub payer_cash_reserved_micros: i128,
    #[serde(with = "nonnegative_decimal_i128")]
    pub payer_cash_granted_micros: i128,
    #[serde(with = "nonnegative_decimal_i128")]
    pub payer_cash_refunded_micros: i128,
}

/// Host joins actual material receipts, consumption and surviving freight before
/// supplying this closed fact. Missing facts never confer practice eligibility.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerAidSupport {
    pub original_commitment_id: [u8; 32],
    pub material_commitment_id: [u8; 32],
    pub mandate_id: [u8; 32],
    pub source_hash: [u8; 32],
    pub dispatch_period: u64,
    pub period: u64,
    pub recipient_principal_id: [u8; 32],
    pub good_id: [u8; 32],
    pub unit_id: [u8; 32],
    pub status: OrganizerAidSupportStatus,
    pub material_postings: OrganizerAidMaterialPostings,
}

/// Independent captured deterministic-policy authority for the later response.
/// Receiving consent is not consulted to create this authorization.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerAidPartnerAuthorization {
    pub actor_id: u64,
    pub authority_id: [u8; 16],
    pub authority_digest: [u8; 32],
    pub content_digest: [u8; 32],
    pub resource_digest: [u8; 32],
    pub target: [u8; 32],
}

/// Only unresolved practices survive. At most one per captured aid kind, two total.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerPendingAidPractice {
    pub gift: OrganizerAidCommitment,
    pub material_commitment_id: [u8; 32],
    pub dispatch_period: u64,
    pub good_id: [u8; 32],
    pub unit_id: [u8; 32],
    pub partner_authorization: OrganizerAidPartnerAuthorization,
}

/// Separate from ordinary once-per-period practice receipts. Original admission
/// and material dates persist; `practice.period` is the actual decision date.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerAidResolutionReceipt {
    pub authorization: OrganizerPendingAidPractice,
    pub support: OrganizerAidSupport,
    pub practice: OrganizerReceipt,
}

fn partner_authorization(
    config: &OrganizerConfig,
    gift: &OrganizerAidCommitment,
) -> Result<OrganizerAidPartnerAuthorization, OrganizerError> {
    let binding = aid_binding(config, gift.commitment.command.choice)
        .ok_or(OrganizerError::AidSupportMismatch)?;
    let ledger = organizer_input_authority_ledger(config)?;
    let row = ledger
        .rows
        .iter()
        .find(|row| {
            row.input_authority_id.as_bytes() == binding.partner.authority_id
                && row.actor_org_id.to_bytes() == binding.partner.actor_id.to_be_bytes()
        })
        .ok_or(OrganizerError::InvalidCommitment)?;
    Ok(OrganizerAidPartnerAuthorization {
        actor_id: binding.partner.actor_id,
        authority_id: binding.partner.authority_id,
        authority_digest: crate::input_authority_digest(row)
            .map_err(|_| OrganizerError::InvalidCommitment)?,
        content_digest: config.content_digest,
        resource_digest: organizer_resource_digest()?,
        target: binding.social_class_target,
    })
}

pub(super) fn validate_pending_shape(
    pending: &OrganizerPendingAidPractice,
) -> Result<(), OrganizerError> {
    validate_organizer_commitment(&pending.gift.commitment)?;
    let auth = &pending.partner_authorization;
    if pending.dispatch_period != pending.gift.commitment.resolves_period
        || pending.material_commitment_id == [0; 32]
        || pending.good_id == [0; 32]
        || pending.unit_id == [0; 32]
        || auth.actor_id != pending.gift.recipient_actor_id
        || auth.authority_id == [0; 16]
        || auth.authority_digest == [0; 32]
        || auth.content_digest != pending.gift.commitment.command.content_digest
        || auth.resource_digest != pending.gift.commitment.command.resource_digest
        || auth.target == [0; 32]
    {
        return Err(OrganizerError::AidSupportMismatch);
    }
    Ok(())
}

pub(super) fn validate_pending(
    config: &OrganizerConfig,
    pending: &OrganizerPendingAidPractice,
) -> Result<(), OrganizerError> {
    validate_pending_shape(pending)?;
    validate_organizer_aid_commitment(config, &pending.gift)?;
    if partner_authorization(config, &pending.gift)? != pending.partner_authorization {
        return Err(OrganizerError::AidSupportMismatch);
    }
    Ok(())
}

pub(super) fn validate_support(
    pending: &OrganizerPendingAidPractice,
    support: &OrganizerAidSupport,
    period: u64,
) -> Result<(), OrganizerError> {
    let postings = &support.material_postings;
    let current = support.period == support.dispatch_period;
    let settled = postings
        .payer_cash_granted_micros
        .checked_add(postings.payer_cash_refunded_micros)
        .ok_or(OrganizerError::AidSupportMismatch)?;
    if postings.payer_cash_reserved_micros < 0
        || postings.payer_cash_granted_micros < 0
        || postings.payer_cash_refunded_micros < 0
        || (current && settled > postings.payer_cash_reserved_micros)
        || (!current
            && (postings.dispatched_quantity != 0
                || postings.fulfillment_hours != 0
                || postings.payer_cash_reserved_micros != 0))
        || (postings.dispatched_quantity == 0 && postings.fulfillment_hours != 0)
        || (!matches!(support.status, OrganizerAidSupportStatus::Granted { .. })
            && postings.payer_cash_granted_micros != 0)
        || (pending.gift.kind == OrganizerAidKind::Local
            && matches!(support.status, OrganizerAidSupportStatus::Granted { granted_quantity, .. }
                if postings.dispatched_quantity != granted_quantity))
    {
        return Err(OrganizerError::AidSupportMismatch);
    }
    if (pending.gift.kind == OrganizerAidKind::Local
        && (support.period != pending.dispatch_period
            || matches!(support.status, OrganizerAidSupportStatus::AwaitingDelivery)))
        || (pending.gift.kind == OrganizerAidKind::Remote
            && matches!(support.status, OrganizerAidSupportStatus::Granted { .. })
            && support.period <= pending.dispatch_period)
        || support.original_commitment_id != pending.gift.commitment.commitment_id
        || support.material_commitment_id != pending.material_commitment_id
        || support.mandate_id != pending.gift.mandate_id
        || support.source_hash != pending.gift.source_hash
        || support.dispatch_period != pending.dispatch_period
        || support.recipient_principal_id != pending.gift.recipient_principal_id
        || support.good_id != pending.good_id
        || support.unit_id != pending.unit_id
        || support.period != period
        || support.period < support.dispatch_period
        || matches!(
            support.status,
            OrganizerAidSupportStatus::Granted {
                granted_quantity: 0,
                ..
            }
        )
    {
        return Err(OrganizerError::AidSupportMismatch);
    }
    Ok(())
}

pub(super) fn pending_from_support(
    config: &OrganizerConfig,
    opening: &OrganizerState,
    accepted: &OrganizerCommitment,
    support: &OrganizerAidSupport,
) -> Result<OrganizerPendingAidPractice, OrganizerError> {
    let gift = organizer_aid_commitment(config, opening, accepted)?;
    let pending = OrganizerPendingAidPractice {
        partner_authorization: partner_authorization(config, &gift)?,
        gift,
        material_commitment_id: support.material_commitment_id,
        dispatch_period: accepted.resolves_period,
        good_id: support.good_id,
        unit_id: support.unit_id,
    };
    validate_pending(config, &pending)?;
    validate_support(&pending, support, accepted.resolves_period)?;
    Ok(pending)
}

/// Explicit delayed authorization, not admission of a stale player command.
/// # Errors
/// Refuses altered capture/authority or a decision before original dispatch.
pub(super) fn delayed_aid_intents(
    config: &OrganizerConfig,
    pending: &OrganizerPendingAidPractice,
    period: u64,
) -> Result<(crate::PracticeIntent, crate::PracticeIntent), OrganizerError> {
    validate_pending(config, pending)?;
    if period < pending.dispatch_period {
        return Err(OrganizerError::PeriodMismatch);
    }
    let mut intent = super::transition::intent_for_authorized_commitment(
        config,
        pending.gift.commitment.command.expected_period,
        &pending.gift.commitment,
        false,
    )?;
    // Initial-period execution is exactly the original projected human input.
    // Later-period execution is explicitly derived from the persisted authority.
    if period > pending.dispatch_period {
        intent.submit_after_tick = period.checked_sub(1).ok_or(OrganizerError::Arithmetic)?;
        intent.resolve_tick = period;
        let digest = super::contract::identity(
            b"babylon.organizer-delayed-aid-nonce.v1",
            &(pending.gift.commitment.commitment_id, period),
        )?;
        intent.proposal_nonce = crate::ProposalNonce::from_bytes(
            digest[..16]
                .try_into()
                .map_err(|_| OrganizerError::InvalidCommitment)?,
        );
        intent.evidence_digests.extend([
            pending.gift.commitment.commitment_id,
            pending.material_commitment_id,
            super::contract::identity(b"babylon.organizer-pending-aid-authorization.v1", pending)?,
        ]);
        intent.evidence_digests.sort_unstable();
        intent.evidence_digests.dedup();
    }
    crate::validate_practice_intent(&intent).map_err(|_| OrganizerError::InvalidCommitment)?;
    let partner = &aid_binding(config, pending.gift.commitment.command.choice)
        .ok_or(OrganizerError::AidSupportMismatch)?
        .partner;
    let response = super::transition::response_intent(&intent, config, partner)?;
    let ledger = organizer_input_authority_ledger(config)?;
    let batch = crate::ResolvedPracticeBatch {
        schema_version: 2,
        campaign_id: crate::CampaignId::from_bytes(config.campaign_id),
        resolve_tick: period,
        authority_ledger_digest: crate::input_authority_ledger_digest(&ledger)
            .map_err(|_| OrganizerError::InvalidConfig)?,
        resource_allocation_contract_digest: organizer_resource_digest()?,
        content_digest: config.content_digest,
        items: {
            let mut items = vec![];
            for value in [&intent, &response] {
                let authority = ledger
                    .rows
                    .iter()
                    .find(|row| row.input_authority_id == value.input_authority_id)
                    .ok_or(OrganizerError::InvalidCommitment)?
                    .clone();
                items.push(crate::ResolvedPracticeBatchItem {
                    authority,
                    intent: value.clone(),
                });
            }
            items.sort_by_key(|row| crate::practice_proposal_key(&row.intent));
            items
        },
    };
    crate::validate_resolved_practice_batch(&batch, &ledger)
        .map_err(|_| OrganizerError::InvalidCommitment)?;
    Ok((intent, response))
}

pub(super) fn validate_resolution_shape(
    row: &OrganizerAidResolutionReceipt,
) -> Result<(), OrganizerError> {
    validate_pending_shape(&row.authorization)?;
    validate_support(&row.authorization, &row.support, row.practice.period)?;
    validate_organizer_receipt(&row.practice)?;
    let expected = super::contract::identity(
        b"babylon.organizer-aid-resolution.v1",
        &(
            row.authorization.gift.commitment.commitment_id,
            row.practice.period,
        ),
    )?;
    let outcome = row.practice.outcome;
    let allowed = match row.support.status {
        OrganizerAidSupportStatus::AwaitingDelivery => {
            outcome == OrganizerOutcome::AidAwaitingSupport
        }
        OrganizerAidSupportStatus::TerminalFailure => {
            outcome == OrganizerOutcome::AidNotProvisioned
        }
        OrganizerAidSupportStatus::Granted {
            consumed_quantity: 0,
            ..
        } => outcome == OrganizerOutcome::AidNotProvisioned,
        OrganizerAidSupportStatus::Granted { .. } => matches!(
            outcome,
            OrganizerOutcome::AidPracticeCompleted
                | OrganizerOutcome::AidPracticeUncompleted
                | OrganizerOutcome::InsufficientTime
        ),
    };
    if row.practice.receipt_id != expected
        || row.practice.commitment_id != Some(row.authorization.gift.commitment.commitment_id)
        || row.practice.choice != row.authorization.gift.commitment.command.choice
        || row.practice.actor_id != row.authorization.gift.donor_actor_id
        || !allowed
    {
        return Err(OrganizerError::AidSupportMismatch);
    }
    Ok(())
}

/// Ordinary and aid-resolution receipts for this actual decision period.
/// Their stable receipt IDs let the host derive exact idempotent household uses.
/// Material gift fulfillment is already debited and is not part of this iterator.
pub fn organizer_period_receipts(
    state: &OrganizerState,
    period: u64,
) -> impl Iterator<Item = &OrganizerReceipt> {
    state
        .receipts
        .iter()
        .filter(move |row| row.period == period)
        .chain(
            state
                .aid_receipts
                .iter()
                .filter(move |row| row.practice.period == period)
                .map(|row| &row.practice),
        )
}

pub(super) fn require_support_rows(
    opening: &OrganizerState,
    fresh: Option<&OrganizerCommitment>,
    period: u64,
    supports: &[OrganizerAidSupport],
) -> Result<(), OrganizerError> {
    let expected = opening.pending_aid.len() + usize::from(fresh.is_some());
    if expected > 2 {
        return Err(OrganizerError::Refused(
            OrganizerRefusal::PendingAidConflict,
        ));
    }
    if supports.len() != expected {
        return Err(OrganizerError::AidSupportMissing);
    }
    let mut keys = BTreeSet::new();
    for row in supports {
        if row.period != period
            || !keys.insert(row.original_commitment_id)
            || !opening
                .pending_aid
                .iter()
                .any(|pending| pending.gift.commitment.commitment_id == row.original_commitment_id)
                && fresh.is_none_or(|value| value.commitment_id != row.original_commitment_id)
        {
            return Err(OrganizerError::AidSupportMismatch);
        }
    }
    Ok(())
}

pub(super) fn validate_aid_state(state: &OrganizerState) -> Result<(), OrganizerError> {
    let mut active_kinds = BTreeSet::new();
    let mut previous_kind = None;
    for pending in &state.pending_aid {
        validate_pending_shape(pending)?;
        if pending.dispatch_period > state.period
            || !active_kinds.insert(pending.gift.kind)
            || previous_kind.is_some_and(|kind| kind >= pending.gift.kind)
        {
            return Err(OrganizerError::InvalidState);
        }
        previous_kind = Some(pending.gift.kind);
    }
    let mut histories =
        std::collections::BTreeMap::<[u8; 32], (u64, bool, &OrganizerPendingAidPractice)>::new();
    let mut last_key = None;
    for row in &state.aid_receipts {
        validate_resolution_shape(row)?;
        if row.practice.period > state.period {
            return Err(OrganizerError::InvalidState);
        }
        let key = (row.practice.period, row.authorization.gift.kind);
        if last_key.is_some_and(|previous| previous >= key) {
            return Err(OrganizerError::InvalidState);
        }
        last_key = Some(key);
        let id = row.authorization.gift.commitment.commitment_id;
        let terminal = row.practice.outcome != OrganizerOutcome::AidAwaitingSupport;
        if let Some((previous, was_terminal, authorization)) = histories.get(&id) {
            if *was_terminal
                || previous.checked_add(1) != Some(row.practice.period)
                || *authorization != &row.authorization
            {
                return Err(OrganizerError::InvalidState);
            }
        } else if row.practice.period != row.authorization.dispatch_period
            || !state.receipts.iter().any(|ordinary| {
                ordinary.outcome == OrganizerOutcome::AidScheduled
                    && ordinary.commitment_id
                        == Some(row.authorization.gift.commitment.commitment_id)
                    && ordinary.period == row.authorization.dispatch_period
                    && ordinary.choice == row.authorization.gift.commitment.command.choice
                    && ordinary.actor_id == row.authorization.gift.donor_actor_id
            })
        {
            return Err(OrganizerError::InvalidState);
        }
        histories.insert(id, (row.practice.period, terminal, &row.authorization));
    }
    for pending in &state.pending_aid {
        let Some((period, terminal, authorization)) =
            histories.get(&pending.gift.commitment.commitment_id)
        else {
            return Err(OrganizerError::InvalidState);
        };
        let carried_reduction = period.checked_add(1) == Some(state.period)
            && state
                .receipts
                .last()
                .is_none_or(|row| row.period < state.period);
        if (*period != state.period && !carried_reduction) || *terminal || *authorization != pending
        {
            return Err(OrganizerError::InvalidState);
        }
    }
    for (period, terminal, authorization) in histories.values() {
        let carried_reduction = period.checked_add(1) == Some(state.period)
            && state
                .receipts
                .last()
                .is_none_or(|row| row.period < state.period);
        if !terminal
            && ((*period != state.period && !carried_reduction)
                || !state.pending_aid.contains(authorization))
        {
            return Err(OrganizerError::InvalidState);
        }
    }
    for ordinary in &state.receipts {
        if aid_kind(ordinary.choice).is_some()
            && (ordinary.outcome != OrganizerOutcome::AidScheduled
                || !state.aid_receipts.iter().any(|row| {
                    row.authorization.gift.commitment.commitment_id
                        == ordinary.commitment_id.unwrap_or([0; 32])
                        && row.authorization.dispatch_period == ordinary.period
                }))
        {
            return Err(OrganizerError::InvalidState);
        }
    }
    Ok(())
}

pub(super) fn validate_period_allocations(
    config: &OrganizerConfig,
    state: &OrganizerState,
) -> Result<(), OrganizerError> {
    let mut promised = std::collections::BTreeMap::<(u64, u64, u64), u64>::new();
    let mut total = std::collections::BTreeMap::<(u64, u64), u64>::new();
    for receipt in state
        .receipts
        .iter()
        .chain(state.aid_receipts.iter().map(|row| &row.practice))
    {
        for row in &receipt.time_use {
            let p = config
                .participants
                .iter()
                .find(|p| p.contributor_id == row.contributor_id)
                .ok_or(OrganizerError::InvalidState)?;
            let bound = p
                .commitments
                .iter()
                .find(|p| p.actor_id == row.actor_id)
                .ok_or(OrganizerError::InvalidState)?
                .hours;
            let spent = promised
                .entry((receipt.period, row.contributor_id, row.actor_id))
                .or_default();
            *spent = spent
                .checked_add(row.hours)
                .ok_or(OrganizerError::Arithmetic)?;
            let all = total
                .entry((receipt.period, row.contributor_id))
                .or_default();
            *all = all
                .checked_add(row.hours)
                .ok_or(OrganizerError::Arithmetic)?;
            if *spent > bound || *all > p.available_hours {
                return Err(OrganizerError::InvalidState);
            }
        }
    }
    Ok(())
}

pub(super) fn validate_completed_aid(state: &OrganizerState) -> Result<(), OrganizerError> {
    for pending in &state.pending_aid {
        if !state.aid_receipts.iter().any(|row| {
            row.authorization == *pending
                && row.practice.period == state.period
                && row.practice.outcome == OrganizerOutcome::AidAwaitingSupport
        }) {
            return Err(OrganizerError::InvalidState);
        }
    }
    Ok(())
}

pub(super) fn validate_resolution_allocation(
    config: &OrganizerConfig,
    row: &OrganizerAidResolutionReceipt,
) -> Result<(), OrganizerError> {
    let binding = aid_binding(config, row.practice.choice).ok_or(OrganizerError::InvalidState)?;
    match row.practice.outcome {
        OrganizerOutcome::AidPracticeCompleted | OrganizerOutcome::AidPracticeUncompleted => {
            let recipient = row
                .practice
                .time_use
                .iter()
                .filter(|r| r.actor_id == binding.partner.actor_id)
                .try_fold(0_u64, |n, r| {
                    n.checked_add(r.hours).ok_or(OrganizerError::Arithmetic)
                })?;
            let expected =
                if row.practice.partner_response == OrganizerPartnerResponse::Participated {
                    config.partner_response_hours
                } else {
                    0
                };
            if row.practice.hours_spent != binding.coordination_hours || recipient != expected {
                return Err(OrganizerError::InvalidState);
            }
        }
        OrganizerOutcome::InsufficientTime if !row.practice.time_use.is_empty() => {
            return Err(OrganizerError::InvalidState);
        }
        _ => {}
    }
    Ok(())
}
